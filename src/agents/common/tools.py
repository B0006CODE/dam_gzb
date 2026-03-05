import asyncio
import traceback
from typing import Annotated, Any

from langchain_core.tools import StructuredTool, tool
# 网页搜索功能已移除，不再需要 TavilySearch
from pydantic import BaseModel, Field

from src import config, graph_base, knowledge_base
from src.utils import logger


class GraphQueryModel(BaseModel):
    query: str = Field(description="要在知识图谱中检索的关键词。")


class GraphStatisticsModel(BaseModel):
    """知识图谱统计工具的参数模型"""
    keyword: str = Field(
        default="",
        description="可选的实体关键词，如'重力坝'、'土石坝'、'溢洪道'等。如果用户没有指定具体实体，留空则查询整个图谱。"
    )
    query_type: str = Field(
        default="病害",
        description="查询类型：'病害'(查询常见缺陷、病因等)、'解决方法'(查询处置措施、整改措施等)、'全部'(查询所有相关信息)"
    )


# 语义映射：用户术语 -> 实际关系类型
SEMANTIC_MAPPING = {
    "病害": ["常见缺陷", "COMMON_DEFECT", "典型病因", "TYPICAL_CAUSE", "主要病因", "MAIN_CAUSE", "存在隐患", "典型缺陷", "TYPICAL_DEFECT"],
    "缺陷": ["常见缺陷", "COMMON_DEFECT", "典型缺陷", "TYPICAL_DEFECT"],
    "病因": ["典型病因", "TYPICAL_CAUSE", "主要病因", "MAIN_CAUSE"],
    "原因": ["典型病因", "TYPICAL_CAUSE", "主要病因", "MAIN_CAUSE"],
    "隐患": ["存在隐患"],
    "风险": ["常见缺陷", "COMMON_DEFECT", "典型病因", "TYPICAL_CAUSE", "主要病因", "MAIN_CAUSE", "存在隐患", "典型缺陷", "TYPICAL_DEFECT"],
    "解决方法": ["处置措施", "TREATMENT_MEASURE", "整改措施"],
    "措施": ["处置措施", "TREATMENT_MEASURE", "整改措施"],
    "处理": ["处置措施", "TREATMENT_MEASURE", "整改措施"],
    "整改": ["整改措施"],
}


def get_static_tools(input_context: dict | None = None) -> list:
    """注册静态工具"""
    retrieval_mode = input_context.get("retrieval_mode", "mix") if input_context else "mix"
    # 知识库检索/大模型检索不暴露图谱工具
    if retrieval_mode in ("local", "llm"):
        return []

    graph_name = (input_context or {}).get("graph_name") or "neo4j"

    async def graph_search(query: str) -> Any:
        try:
            logger.debug(f"Querying knowledge graph [{graph_name}] with: {query}")
            if graph_name != "neo4j":
                lightrag_result = await knowledge_base.aquery(query, graph_name, mode="global")
                if isinstance(lightrag_result, list) and lightrag_result:
                    first_item = lightrag_result[0]
                    if isinstance(first_item, dict):
                        content = first_item.get("content", "") or str(first_item)
                    else:
                        content = str(first_item)
                else:
                    content = str(lightrag_result) if lightrag_result else ""
                return {
                    "query_type": "search",
                    "query": query,
                    "graph_type": "lightrag",
                    "content": content,
                    "triples": [],
                }

            result = graph_base.query_node(query, hops=2, kgdb_name=graph_name, return_format="triples")
            # 添加查询类型元数据，便于前端区分搜索和统计查询
            if isinstance(result, dict):
                result["query_type"] = "search"
                result["query"] = query
            return result
        except Exception as e:
            logger.error(f"Knowledge graph query error: {e}, {traceback.format_exc()}")
            return f"知识图谱查询失败: {str(e)}"

    async def graph_statistics(keyword: str = "", query_type: str = "病害") -> Any:
        """知识图谱统计工具 - 用于回答统计性问题"""
        try:
            logger.debug(f"统计知识图谱 [{graph_name}] 关键词: {keyword}, 查询类型: {query_type}")
            
            if graph_name != "neo4j":
                return f"当前图谱({graph_name})暂不支持统计查询，请切换到 Neo4j 图谱后重试。"

            if not graph_base.is_running():
                return "知识图谱数据库未连接，无法进行统计查询。"
            
            graph_base.use_database(graph_name)
            
            # 确定要查询的关系类型
            relation_types_to_query = []
            query_labels = []
            
            # 解析查询类型（支持多种类型如"病害和解决方法"）
            if "全部" in query_type or ("病害" in query_type and ("解决" in query_type or "措施" in query_type)):
                relation_types_to_query.extend(SEMANTIC_MAPPING.get("病害", []))
                relation_types_to_query.extend(SEMANTIC_MAPPING.get("解决方法", []))
                query_labels = ["病害", "解决方法"]
            elif "病害" in query_type or "缺陷" in query_type or "病因" in query_type or "隐患" in query_type:
                relation_types_to_query.extend(SEMANTIC_MAPPING.get("病害", []))
                query_labels = ["病害"]
            elif "解决" in query_type or "措施" in query_type or "处理" in query_type or "整改" in query_type:
                relation_types_to_query.extend(SEMANTIC_MAPPING.get("解决方法", []))
                query_labels = ["解决方法"]
            else:
                # 尝试从SEMANTIC_MAPPING中查找
                for key, values in SEMANTIC_MAPPING.items():
                    if key in query_type:
                        relation_types_to_query.extend(values)
                        query_labels.append(key)
                        break
                
                if not relation_types_to_query:
                    relation_types_to_query.extend(SEMANTIC_MAPPING.get("病害", []))
                    query_labels = ["病害"]
            
            # 去重
            relation_types_to_query = list(set(relation_types_to_query))
            
            with graph_base.driver.session() as session:
                results_by_type = {}
                total_count = 0
                
                for rel_type in relation_types_to_query:
                    if keyword:
                        # 有实体关键词：查询特定实体的相关信息
                        results = session.run("""
                            MATCH (n:Entity)-[r:RELATION]->(m:Entity)
                            WHERE toLower(n.name) CONTAINS toLower($keyword)
                              AND r.type = $rel_type
                            RETURN DISTINCT m.name as target_entity, r.type as relation_type
                            ORDER BY target_entity
                        """, keyword=keyword, rel_type=rel_type)
                    else:
                        # 无实体关键词：查询整个图谱
                        results = session.run("""
                            MATCH (n:Entity)-[r:RELATION]->(m:Entity)
                            WHERE r.type = $rel_type
                            RETURN DISTINCT m.name as target_entity, r.type as relation_type
                            ORDER BY target_entity
                        """, rel_type=rel_type)
                    
                    entities = []
                    for record in results:
                        entity = record["target_entity"]
                        if entity and entity not in entities:
                            entities.append(entity)
                    
                    if entities:
                        # 将中英文关系类型映射回中文
                        display_type = rel_type
                        if rel_type == "COMMON_DEFECT":
                            display_type = "常见缺陷"
                        elif rel_type == "TYPICAL_CAUSE":
                            display_type = "典型病因"
                        elif rel_type == "MAIN_CAUSE":
                            display_type = "主要病因"
                        elif rel_type == "TREATMENT_MEASURE":
                            display_type = "处置措施"
                        elif rel_type == "TYPICAL_DEFECT":
                            display_type = "典型缺陷"
                        
                        if display_type not in results_by_type:
                            results_by_type[display_type] = []
                        results_by_type[display_type].extend(entities)
                        total_count += len(entities)
                
                # 去重每个类型的结果
                for rel_type in results_by_type:
                    results_by_type[rel_type] = list(dict.fromkeys(results_by_type[rel_type]))
                
                if not results_by_type:
                    scope = f"'{keyword}'相关的" if keyword else "整个图谱中的"
                    return {
                        "query_type": "statistics",
                        "keyword": keyword,
                        "query_labels": query_labels,
                        "total_count": 0,
                        "results_by_type": {},
                        "message": f"未找到{scope}{'/'.join(query_labels)}数据。"
                    }
                
                # 构建结构化输出
                scope = f"'{keyword}'相关的" if keyword else "整个图谱中的"
                
                # 实体名称脱敏处理函数
                import re
                def desensitize_text(text):
                    if not text:
                        return text
                    # 1. 构件编号脱敏 (2# -> 某, 3号 -> 某)
                    text = re.sub(r'\d+#', '某', text)
                    text = re.sub(r'\d+号', '某', text)
                    # 2. 尺寸/数值泛化 (90m -> 一定长度)
                    text = re.sub(r'\d+(?:\.\d+)?[mM米]', '一定长度', text)
                    text = re.sub(r'\d+(?:\.\d+)?[kK]?[wW]瓦', '一定功率', text)
                    # 3. 桩号脱敏
                    text = re.sub(r'[kK]\d+\+\d+', '某桩号', text)
                    return text

                # 对结果进行脱敏处理
                desensitized_results = {}
                for k, v in results_by_type.items():
                    # 对每个实体名称进行脱敏
                    desensitized_entities = [desensitize_text(e) for e in v]
                    # 去重（因为脱敏后可能出现重复，如 "2#横梁" 和 "3#横梁" 都变成了 "某横梁"）
                    desensitized_entities = list(dict.fromkeys(desensitized_entities))
                    desensitized_results[k] = desensitized_entities

                # 计算各类型数量之和作为总数
                total_type_count = sum(len(v) for v in desensitized_results.values())

                # 同时生成文本摘要供大模型使用
                output_parts = [
                    f"【知识图谱统计结果】",
                    f"查询范围：{scope}{'/'.join(query_labels)}",
                    f"共找到 {total_type_count} 种不同的{'/'.join(query_labels)}类型",
                    "",
                    "按关系类型分类统计："
                ]
                
                for rel_type, entities in sorted(desensitized_results.items(), key=lambda x: len(x[1]), reverse=True):
                    count = len(entities)
                    preview = "、".join(entities[:8])
                    if len(entities) > 8:
                        preview += f"...等"
                    output_parts.append(f"  ▪ {rel_type}：{count} 种")
                    output_parts.append(f"    包括：{preview}")
                
                return {
                    "query_type": "statistics",
                    "keyword": keyword,
                    "query_labels": query_labels,
                    "scope": scope,
                    "total_count": total_type_count,
                    "results_by_type": {k: {"count": len(v), "entities": v} for k, v in desensitized_results.items()},
                    "text_summary": "\n".join(output_parts)
                }
                    
        except Exception as e:
            logger.error(f"知识图谱统计错误: {e}, {traceback.format_exc()}")
            return f"知识图谱统计查询失败: {str(e)}"

    graph_tool = StructuredTool.from_function(
        coroutine=graph_search,
        name="global_knowledge_graph_search",
        description=f"使用全局知识图谱（数据库：{graph_name}）进行检索，查询实体间的关联关系和知识信息。",
        args_schema=GraphQueryModel,
        metadata={"graph_name": graph_name, "tag": ["knowledge_graph"]},
    )

    statistics_tool = StructuredTool.from_function(
        coroutine=graph_statistics,
        name="knowledge_graph_statistics",
        description=(
            f"使用知识图谱（数据库：{graph_name}）进行统计查询。"
            "当用户询问'有多少'、'数量是多少'、'统计一下'、'有哪些'等统计性问题时，优先使用此工具。"
            "参数说明：keyword为可选的实体关键词（如'重力坝'），不指定则查询整个图谱；"
            "query_type可选'病害'(常见缺陷/病因)、'解决方法'(处置措施/整改措施)、'全部'、或'病害和解决方法'等组合。"
            "例如：'有多少种病害'→keyword='', query_type='病害'；'重力坝有多少种病害和解决方法'→keyword='重力坝', query_type='病害和解决方法'；'有哪些风险'→keyword='', query_type='风险'"
        ),
        args_schema=GraphStatisticsModel,
        metadata={"graph_name": graph_name, "tag": ["knowledge_graph", "statistics"]},
    )

    static_tools = [
        graph_tool,
        statistics_tool,
    ]

    # 网页搜索功能已移除，只保留知识库相关功能

    return static_tools


class KnowledgeRetrieverModel(BaseModel):
    query_text: str = Field(
        description=(
            "查询的关键词，查询的时候，应该尽量以可能帮助回答这个问题的关键词进行查询，不要直接使用用户的原始输入去查询。"
        )
    )


def get_kb_based_tools(input_context: dict = None) -> list:
    """获取所有知识库基于的工具"""
    retrieval_mode = input_context.get("retrieval_mode", "mix") if input_context else "mix"
    if retrieval_mode in ("global", "llm"):
        return []

    # 获取所有知识库
    kb_tools = []
    retrievers = knowledge_base.get_retrievers()

    # 从输入上下文中获取检索模式，默认为 "mix"
    raw_whitelist = input_context.get("kb_whitelist") if input_context else []
    if isinstance(raw_whitelist, str):
        raw_whitelist = [raw_whitelist]
    kb_whitelist = set(raw_whitelist or [])

    def _create_retriever_wrapper(db_id: str, retriever_info: dict[str, Any]):
        """创建检索器包装函数的工厂函数，避免闭包变量捕获问题"""

        async def async_retriever_wrapper(query_text: str) -> Any:
            """异步检索器包装函数"""
            retriever = retriever_info["retriever"]
            try:
                logger.debug(f"Retrieving from database {db_id} with query: {query_text}, mode: {retrieval_mode}")
                if asyncio.iscoroutinefunction(retriever):
                    result = await retriever(query_text, mode=retrieval_mode)
                else:
                    result = retriever(query_text, mode=retrieval_mode)
                logger.debug(f"Retrieved {len(result) if isinstance(result, list) else 'N/A'} results from {db_id}")
                return result
            except Exception as e:
                logger.error(f"Error in retriever {db_id}: {e}")
                return f"检索失败: {str(e)}"

        return async_retriever_wrapper

    for db_id, retrieve_info in retrievers.items():
        if kb_whitelist and db_id not in kb_whitelist:
            continue
        try:
            # 使用改进的工具ID生成策略
            tool_id = f"query_{db_id[:8]}"

            # 构建工具描述
            description = (
                f"使用 {retrieve_info['name']} 知识库进行检索。\n"
                f"下面是这个知识库的描述：\n{retrieve_info['description'] or '没有描述。'} "
            )

            # 使用工厂函数创建检索器包装函数，避免闭包问题
            retriever_wrapper = _create_retriever_wrapper(db_id, retrieve_info)

            # 使用 StructuredTool.from_function 创建异步工具
            tool = StructuredTool.from_function(
                coroutine=retriever_wrapper,
                name=tool_id,
                description=description,
                args_schema=KnowledgeRetrieverModel,
                metadata=retrieve_info["metadata"] | {"tag": ["knowledgebase"]},
            )

            kb_tools.append(tool)
            # logger.debug(f"Successfully created tool {tool_id} for database {db_id}")

        except Exception as e:
            logger.error(f"Failed to create tool for database {db_id}: {e}, \n{traceback.format_exc()}")
            continue

    return kb_tools


class HybridSearchModel(BaseModel):
    """混合检索工具的参数模型"""
    query_text: str = Field(
        description="要检索的关键词或问题，应该是能够帮助回答用户问题的关键信息"
    )


def get_hybrid_search_tool(input_context: dict = None) -> list:
    """获取混合检索工具（仅在 mix 模式下使用）"""
    retrieval_mode = input_context.get("retrieval_mode", "mix") if input_context else "mix"
    if retrieval_mode != "mix":
        return []

    # 获取配置
    raw_whitelist = input_context.get("kb_whitelist") if input_context else []
    if isinstance(raw_whitelist, str):
        raw_whitelist = [raw_whitelist]
    kb_whitelist = set(raw_whitelist or [])
    graph_name = (input_context or {}).get("graph_name") or "neo4j"

    async def hybrid_search(query_text: str) -> dict:
        """同时查询知识库和知识图谱，合并结果"""
        results = {
            "query": query_text,
            "knowledge_base_results": [],
            "knowledge_graph_results": [],
            "summary": "",
        }
        
        # 1. 查询所有选中的知识库
        kb_results = []
        retrievers = knowledge_base.get_retrievers()
        for db_id, retriever_info in retrievers.items():
            if kb_whitelist and db_id not in kb_whitelist:
                continue
            try:
                retriever = retriever_info["retriever"]
                if asyncio.iscoroutinefunction(retriever):
                    result = await retriever(query_text, mode="mix")
                else:
                    result = retriever(query_text, mode="mix")
                
                if isinstance(result, list):
                    for item in result:
                        item["source_db"] = retriever_info["name"]
                        item["source_db_id"] = db_id
                    kb_results.extend(result)
                elif isinstance(result, str) and result:
                    kb_results.append({
                        "content": result,
                        "source_db": retriever_info["name"],
                        "source_db_id": db_id,
                        "score": 1.0,
                    })
                logger.debug(f"Hybrid search: Retrieved {len(result) if isinstance(result, list) else 1} results from {db_id}")
            except Exception as e:
                logger.error(f"Hybrid search: Error querying {db_id}: {e}")
        
        results["knowledge_base_results"] = kb_results
        
        # 2. 查询知识图谱
        try:
            if graph_name == "neo4j":
                # 使用 Neo4j 原生图谱查询（用户上传的图谱）
                if graph_base.is_running():
                    graph_base.use_database(graph_name)
                    graph_result = graph_base.query_node(query_text, hops=2, kgdb_name=graph_name, return_format="triples")
                    if isinstance(graph_result, dict):
                        graph_result["query_type"] = "search"
                        graph_result["query"] = query_text
                        graph_result["graph_type"] = "neo4j"
                    results["knowledge_graph_results"] = graph_result
                    logger.debug(f"Hybrid search: Neo4j graph query completed for '{query_text}'")
            else:
                # 使用 LightRAG 图谱查询
                # LightRAG 知识库同时包含向量检索和图谱，通过 mode='global' 进行图谱检索
                try:
                    lightrag_result = await knowledge_base.aquery(query_text, graph_name, mode="global")
                    if lightrag_result:
                        # 将 LightRAG 的图谱结果格式化
                        if isinstance(lightrag_result, list) and len(lightrag_result) > 0:
                            content = lightrag_result[0].get("content", "") if isinstance(lightrag_result[0], dict) else str(lightrag_result[0])
                        else:
                            content = str(lightrag_result)
                        
                        results["knowledge_graph_results"] = {
                            "query_type": "search",
                            "query": query_text,
                            "graph_type": "lightrag",
                            "content": content,
                            "triples": [],  # LightRAG 返回的是文本，不是三元组
                        }
                    logger.debug(f"Hybrid search: LightRAG graph query completed for '{query_text}' in {graph_name}")
                except Exception as e:
                    logger.error(f"Hybrid search: Error querying LightRAG graph {graph_name}: {e}")
                    results["knowledge_graph_results"] = {"error": str(e)}
        except Exception as e:
            logger.error(f"Hybrid search: Error querying knowledge graph: {e}")
            results["knowledge_graph_results"] = {"error": str(e)}
        
        # 3. 生成摘要
        kb_count = len(kb_results)
        kg_result = results["knowledge_graph_results"]
        if isinstance(kg_result, dict):
            if kg_result.get("graph_type") == "lightrag":
                kg_count = 1 if kg_result.get("content") else 0
                kg_desc = f"从 LightRAG 图谱检索到相关内容"
            else:
                kg_count = len(kg_result.get("triples", []))
                kg_desc = f"从知识图谱检索到 {kg_count} 条相关三元组"
        else:
            kg_count = 0
            kg_desc = "图谱查询未返回结果"
        
        results["summary"] = f"从知识库检索到 {kb_count} 条相关内容，{kg_desc}。"
        
        return results

    # 构建工具描述
    kb_names = []
    retrievers = knowledge_base.get_retrievers()
    for db_id, retriever_info in retrievers.items():
        if kb_whitelist and db_id not in kb_whitelist:
            continue
        kb_names.append(retriever_info["name"])
    
    description = (
        "混合检索工具：同时查询知识库和知识图谱，返回综合结果。\n"
        f"将检索的知识库：{', '.join(kb_names) if kb_names else '全部知识库'}\n"
        f"将检索的知识图谱：{graph_name}\n"
        "使用此工具可以获得最全面的信息，综合向量语义检索和实体关系检索的结果。"
    )

    hybrid_tool = StructuredTool.from_function(
        coroutine=hybrid_search,
        name="hybrid_knowledge_search",
        description=description,
        args_schema=HybridSearchModel,
        metadata={"tag": ["hybrid", "knowledgebase", "knowledge_graph"]},
    )

    return [hybrid_tool]


def get_buildin_tools(input_context: dict = None) -> list:
    """获取所有可运行的工具（给大模型使用）"""
    tools = []
    retrieval_mode = input_context.get("retrieval_mode", "mix") if input_context else "mix"

    try:
        if retrieval_mode == "mix":
            # 混合检索模式：使用专门的混合检索工具
            tools.extend(get_hybrid_search_tool(input_context))
            # 同时保留单独的知识库和图谱工具，供大模型选择使用
            tools.extend(get_kb_based_tools(input_context))
            tools.extend(get_static_tools(input_context))
        else:
            # 其他模式：使用原有逻辑
            tools.extend(get_kb_based_tools(input_context))
            tools.extend(get_static_tools(input_context))

    except Exception as e:
        logger.error(f"Failed to get knowledge base retrievers: {e}")

    return tools


def gen_tool_info(tools) -> list[dict[str, Any]]:
    """获取所有工具的信息（用于前端展示）"""
    tools_info = []

    try:
        # 获取注册的工具信息
        for tool_obj in tools:
            try:
                metadata = getattr(tool_obj, "metadata", {}) or {}
                info = {
                    "id": tool_obj.name,
                    "name": metadata.get("name", tool_obj.name),
                    "description": tool_obj.description,
                    "metadata": metadata,
                    "args": [],
                    # "is_async": is_async  # Include async information
                }

                if hasattr(tool_obj, "args_schema") and tool_obj.args_schema:
                    schema = tool_obj.args_schema.schema()
                    for arg_name, arg_info in schema.get("properties", {}).items():
                        info["args"].append(
                            {
                                "name": arg_name,
                                "type": arg_info.get("type", ""),
                                "description": arg_info.get("description", ""),
                            }
                        )

                tools_info.append(info)
                # logger.debug(f"Successfully processed tool info for {tool_obj.name}")

            except Exception as e:
                logger.error(
                    f"Failed to process tool {getattr(tool_obj, 'name', 'unknown')}: {e}\n{traceback.format_exc()}"
                )
                continue

    except Exception as e:
        logger.error(f"Failed to get tools info: {e}\n{traceback.format_exc()}")
        return []

    logger.info(f"Successfully extracted info for {len(tools_info)} tools")
    return tools_info
