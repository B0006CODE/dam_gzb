import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from src import graph_base, knowledge_base
from src.agents.common.base import BaseAgent
from src.agents.common.mcp import get_mcp_tools
from src.agents.common.models import load_chat_model
from src.utils import logger

from .context import Context
from .state import State
from .tools import get_tools


def _get_runtime_input_context(runtime: Runtime[Context] | None) -> dict | None:
    if not runtime:
        return None
    config = getattr(runtime, "config", None)
    if not config:
        config_context = None
    elif isinstance(config, dict):
        config_context = config.get("configurable")
    else:
        config_context = getattr(config, "configurable", None)
    if config_context:
        return config_context

    runtime_context = getattr(runtime, "context", None)
    if not runtime_context:
        return None
    fallback = {}
    for key in ("retrieval_mode", "kb_whitelist", "graph_name", "thread_id", "user_id"):
        if hasattr(runtime_context, key):
            value = getattr(runtime_context, key)
            if value not in (None, "", []):
                fallback[key] = value
    return fallback or None


_STAT_QUERY_PATTERN = re.compile(
    r"(统计|总数|数量|数目|多少|几种|多少种|占比|比例|分布|排名|排行|top\s*\d*|top|rank|ranking|ratio|percentage|"
    r"count|how many|number of|list|列表|清单|有哪些)",
    re.IGNORECASE,
)

_DAM_TYPE_PATTERN = re.compile(
    r"(重力坝|土石坝|拱坝|混凝土坝|堆石坝|心墙坝|斜墙坝|均质坝|面板坝|支墩坝|浆砌石坝|土坝)"
)

_RESERVOIR_COUNT_HINT_PATTERN = re.compile(r"(多少座|几座|有多少座|数量|总数|有多少)")

_REGION_PROVINCE_MAP = {
    "华北": {"北京", "天津", "河北", "山西", "内蒙古"},
    "东北": {"辽宁", "吉林", "黑龙江"},
    "华东": {"上海", "江苏", "浙江", "安徽", "福建", "江西", "山东"},
    "华中": {"河南", "湖北", "湖南"},
    "华南": {"广东", "广西", "海南"},
    "西南": {"重庆", "四川", "贵州", "云南", "西藏"},
    "西北": {"陕西", "甘肃", "青海", "宁夏", "新疆"},
}
_REGION_PATTERN = re.compile(r"(华北|东北|华东|华中|华南|西南|西北)(?:地区)?")
_EXCLUDED_COUNT_QUERY_TERMS = ("病害", "缺陷", "风险", "隐患", "病因", "处置", "整改", "措施", "多少种", "几种")


def _extract_message_text(message: Any) -> str:
    if message is None:
        return ""
    if isinstance(message, dict):
        return str(message.get("content") or "").strip()
    return str(getattr(message, "content", "") or "").strip()


def _last_message_is_user(messages: list[Any]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    if isinstance(last, HumanMessage):
        return True
    msg_type = getattr(last, "type", None)
    if msg_type == "human":
        return True
    if isinstance(last, dict):
        return last.get("role") in {"user", "human"}
    return False


def _get_latest_user_text(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return _extract_message_text(msg)
        if getattr(msg, "type", None) == "human":
            return _extract_message_text(msg)
        if isinstance(msg, dict) and msg.get("role") in {"user", "human"}:
            return _extract_message_text(msg)
    return ""


def _is_statistical_query(text: str) -> bool:
    if not text:
        return False
    return bool(_STAT_QUERY_PATTERN.search(text))


def _is_reservoir_count_query(text: str) -> bool:
    """是否是“按地区/坝型统计多少座”这类数量查询。"""
    if not text:
        return False
    if not ("坝" in text or "水库" in text):
        return False
    if any(term in text for term in _EXCLUDED_COUNT_QUERY_TERMS):
        return False
    if not _RESERVOIR_COUNT_HINT_PATTERN.search(text):
        return False
    if _DAM_TYPE_PATTERN.search(text):
        return True
    if _REGION_PATTERN.search(text):
        return True
    return "水库" in text


def _extract_reservoir_count_params(text: str) -> tuple[str, str, set[str]]:
    """提取坝型、区域和省份过滤条件。"""
    dam_type = ""
    region = ""
    provinces: set[str] = set()

    dam_type_match = _DAM_TYPE_PATTERN.search(text)
    if dam_type_match:
        dam_type = dam_type_match.group(1)

    region_match = _REGION_PATTERN.search(text)
    if region_match:
        region = region_match.group(1)
        provinces.update(_REGION_PROVINCE_MAP.get(region, set()))

    all_known_provinces = set().union(*_REGION_PROVINCE_MAP.values())
    for province in all_known_provinces:
        if province in text:
            provinces.add(province)

    return dam_type, region, provinces


@lru_cache(maxsize=1)
def _load_reservoir_records() -> tuple[list[dict[str, Any]], str]:
    """加载用于计数的水库结构化数据。"""
    project_root = Path(__file__).resolve().parents[3]
    candidate_files = [
        project_root / "web" / "public" / "data" / "reservoirs.json",
        project_root / "web" / "src" / "data" / "reservoirs.json",
    ]

    for file_path in candidate_files:
        if not file_path.exists():
            continue
        try:
            with file_path.open(encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, list):
                return payload, str(file_path)
        except Exception as e:
            logger.error(f"Failed to load reservoir records from {file_path}: {e}")

    return [], ""


def _direct_reservoir_count_statistics(query_text: str) -> dict[str, Any] | None:
    """直接基于结构化水库数据统计“多少座”。"""
    if not _is_reservoir_count_query(query_text):
        return None

    records, source_path = _load_reservoir_records()
    if not records:
        logger.warning("Reservoir structured data not found, skip direct count statistics")
        return None

    dam_type, region, provinces = _extract_reservoir_count_params(query_text)

    filtered: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        row_dam_type = str(row.get("damType") or "").strip()
        row_province = str(row.get("province") or "").strip()

        if dam_type and row_dam_type != dam_type:
            continue
        if provinces and row_province not in provinces:
            continue
        filtered.append(row)

    province_counts: dict[str, int] = {}
    for row in filtered:
        province = str(row.get("province") or "未知")
        province_counts[province] = province_counts.get(province, 0) + 1

    scope_items = []
    if region:
        scope_items.append(f"{region}地区")
    elif provinces:
        scope_items.append("指定省份")
    if dam_type:
        scope_items.append(dam_type)
    if not scope_items:
        scope_items.append("全部水库")
    scope_text = "、".join(scope_items)

    output_parts = [
        "【结构化水库统计结果】",
        f"统计范围：{scope_text}",
        f"统计口径：按数据记录条目计数",
        f"结果：共 {len(filtered)} 座",
    ]
    if province_counts:
        sorted_counts = sorted(province_counts.items(), key=lambda x: (-x[1], x[0]))
        breakdown = "、".join(f"{province}{count}座" for province, count in sorted_counts)
        output_parts.append(f"分省结果：{breakdown}")
    output_parts.append("说明：该结果来自当前系统内置样本数据，仅代表已入库记录。")

    return {
        "query_type": "reservoir_count",
        "dam_type": dam_type,
        "region": region,
        "provinces": sorted(list(provinces)),
        "count": len(filtered),
        "province_counts": province_counts,
        "source_path": source_path,
        "text_summary": "\n".join(output_parts),
    }


def _extract_stat_params(text: str) -> tuple[str, str]:
    """从用户查询中提取统计参数：关键词和查询类型"""
    keyword = ""
    query_type = "病害"
    
    # 提取实体关键词（常见大坝类型）
    entity_patterns = [
        r"(重力坝|土石坝|拱坝|溢洪道|闸门|坝基|坝体|廊道|混凝土坝|堆石坝|水库)",
        r"(西南地区|华南地区|华北地区|华东地区|东北地区|西北地区)",
    ]
    for pattern in entity_patterns:
        match = re.search(pattern, text)
        if match:
            keyword = match.group(1)
            break
    
    # 判断查询类型
    if any(kw in text for kw in ["解决", "措施", "处理", "整改", "方法", "怎么办"]):
        if any(kw in text for kw in ["病害", "缺陷", "风险", "隐患", "问题"]):
            query_type = "病害和解决方法"
        else:
            query_type = "解决方法"
    elif any(kw in text for kw in ["病害", "缺陷", "风险", "隐患", "病因", "原因", "问题"]):
        query_type = "病害"
    elif "全部" in text or ("所有" in text and any(kw in text for kw in ["信息", "数据", "内容"])):
        query_type = "全部"
    
    return keyword, query_type


async def _direct_graph_statistics(query_text: str, graph_name: str = "neo4j") -> dict | None:
    """直接调用知识图谱统计（不依赖工具调用机制）"""
    # 导入语义映射
    from src.agents.common.tools import SEMANTIC_MAPPING
    
    try:
        if graph_name != "neo4j":
            logger.debug(f"Direct statistics not supported for non-neo4j graph: {graph_name}")
            return None
            
        if not graph_base.is_running():
            logger.warning("Neo4j database not connected")
            return None
        
        keyword, query_type = _extract_stat_params(query_text)
        logger.info(f"Direct statistics: keyword='{keyword}', query_type='{query_type}'")
        
        graph_base.use_database(graph_name)
        
        # 确定要查询的关系类型
        relation_types_to_query = []
        query_labels = []
        
        if "全部" in query_type or ("病害" in query_type and ("解决" in query_type or "措施" in query_type)):
            relation_types_to_query.extend(SEMANTIC_MAPPING.get("病害", []))
            relation_types_to_query.extend(SEMANTIC_MAPPING.get("解决方法", []))
            query_labels = ["病害", "解决方法"]
        elif "病害" in query_type or "缺陷" in query_type or "风险" in query_type:
            relation_types_to_query.extend(SEMANTIC_MAPPING.get("病害", []))
            query_labels = ["病害"]
        elif "解决" in query_type or "措施" in query_type:
            relation_types_to_query.extend(SEMANTIC_MAPPING.get("解决方法", []))
            query_labels = ["解决方法"]
        else:
            relation_types_to_query.extend(SEMANTIC_MAPPING.get("病害", []))
            query_labels = ["病害"]
        
        relation_types_to_query = list(set(relation_types_to_query))
        
        with graph_base.driver.session() as session:
            results_by_type = {}
            
            for rel_type in relation_types_to_query:
                if keyword:
                    results = session.run("""
                        MATCH (n:Entity)-[r:RELATION]->(m:Entity)
                        WHERE toLower(n.name) CONTAINS toLower($keyword)
                          AND r.type = $rel_type
                        RETURN DISTINCT m.name as target_entity, r.type as relation_type
                        ORDER BY target_entity
                    """, keyword=keyword, rel_type=rel_type)
                else:
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
            
            # 去重
            for rel_type in results_by_type:
                results_by_type[rel_type] = list(dict.fromkeys(results_by_type[rel_type]))
            
            if not results_by_type:
                return None
            
            # 脱敏处理
            def desensitize_text(text):
                if not text:
                    return text
                text = re.sub(r'\d+#', '某', text)
                text = re.sub(r'\d+号', '某', text)
                text = re.sub(r'\d+(?:\.\d+)?[mM米]', '一定长度', text)
                text = re.sub(r'[kK]\d+\+\d+', '某桩号', text)
                return text
            
            desensitized_results = {}
            for k, v in results_by_type.items():
                desensitized_entities = [desensitize_text(e) for e in v]
                desensitized_entities = list(dict.fromkeys(desensitized_entities))
                desensitized_results[k] = desensitized_entities
            
            total_count = sum(len(v) for v in desensitized_results.values())
            scope = f"'{keyword}'相关的" if keyword else "整个图谱中的"
            
            # 生成文本摘要
            output_parts = [
                f"【知识图谱统计结果】",
                f"查询范围：{scope}{'/'.join(query_labels)}",
                f"共找到 {total_count} 种不同的{'/'.join(query_labels)}类型",
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
                "total_count": total_count,
                "results_by_type": {k: {"count": len(v), "entities": v} for k, v in desensitized_results.items()},
                "text_summary": "\n".join(output_parts)
            }
                
    except Exception as e:
        logger.error(f"Direct graph statistics error: {e}")
        return None


def _trim_text(text: str, max_chars: int = 800) -> str:
    content = str(text or "").strip()
    if len(content) <= max_chars:
        return content
    return f"{content[:max_chars].rstrip()}..."


def _extract_kb_text(item: Any) -> tuple[str, str]:
    if isinstance(item, dict):
        content = item.get("content") or item.get("text") or item.get("chunk") or ""
        metadata = item.get("metadata") or {}
        source = (
            metadata.get("source")
            or metadata.get("file_name")
            or metadata.get("filename")
            or metadata.get("path")
            or metadata.get("db_id")
            or ""
        )
    else:
        content = item
        source = ""
    return str(content or "").strip(), str(source or "").strip()


def _format_kb_results(kb_results: list[Any], max_items: int = 8) -> list[str]:
    lines: list[str] = []
    for item in kb_results:
        content, source = _extract_kb_text(item)
        if not content:
            continue
        content = _trim_text(content)
        if source:
            lines.append(f"- ({source}) {content}")
        else:
            lines.append(f"- {content}")
        if len(lines) >= max_items:
            break
    return lines


def _format_graph_results(graph_results: Any, max_items: int = 12) -> list[str]:
    lines: list[str] = []
    if isinstance(graph_results, dict):
        triples = graph_results.get("triples") or []
        for triple in triples[:max_items]:
            if isinstance(triple, (list, tuple)) and len(triple) >= 3:
                h, r, t = triple[:3]
                lines.append(f"- {h} -[{r}]-> {t}")
            else:
                lines.append(f"- {_trim_text(triple)}")
        if not lines:
            content = graph_results.get("content") or ""
            if content:
                lines.append(f"- {_trim_text(content)}")
    elif isinstance(graph_results, list):
        lines.extend(_format_kb_results(graph_results, max_items=max_items))
    elif isinstance(graph_results, str) and graph_results.strip():
        lines.append(f"- {_trim_text(graph_results)}")
    return lines


def _has_retrieval_results(kb_results: list[Any], graph_results: Any) -> bool:
    for item in kb_results:
        content, _ = _extract_kb_text(item)
        if content:
            return True
    if not graph_results:
        return False
    if isinstance(graph_results, dict):
        if graph_results.get("triples"):
            return True
        if graph_results.get("content"):
            return True
        if graph_results.get("nodes") or graph_results.get("edges"):
            return True
        return False
    if isinstance(graph_results, list):
        return any(_extract_kb_text(item)[0] for item in graph_results)
    if isinstance(graph_results, str):
        return bool(graph_results.strip())
    return False


def _build_retrieval_context(kb_results: list[Any], graph_results: Any) -> str:
    kb_lines = _format_kb_results(kb_results)
    graph_lines = _format_graph_results(graph_results)
    if not kb_lines and not graph_lines:
        return ""
    sections = ["以下是检索到的资料，仅供回答使用："]
    if kb_lines:
        sections.append("【知识库】")
        sections.extend(kb_lines)
    if graph_lines:
        sections.append("【知识图谱】")
        sections.extend(graph_lines)
    return "\n".join(sections)


def _build_retrieval_citations(
    kb_results: list[Any],
    graph_results: Any,
    max_items: int = 12,
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    def _add_citation(
        *,
        title: str = "",
        path: str = "",
        snippet: str = "",
        source_type: str = "document",
        score: Any = None,
        reference_id: Any = None,
    ) -> None:
        key = str(path or title or reference_id or "").strip()
        if not key or key in seen_keys:
            return
        seen_keys.add(key)

        normalized_title = str(title or "").strip()
        normalized_path = str(path or "").strip()
        citation = {
            "title": normalized_title or (normalized_path.split("/")[-1] if normalized_path else "未知来源"),
            "path": normalized_path,
            "snippet": _trim_text(snippet, max_chars=160),
            "sourceType": source_type,
        }
        if score is not None:
            citation["score"] = score
        if reference_id is not None:
            citation["referenceId"] = str(reference_id)
        citations.append(citation)

    for item in kb_results:
        if isinstance(item, dict):
            content = item.get("content") or item.get("text") or item.get("chunk") or ""
            metadata = item.get("metadata") or {}
            path = (
                metadata.get("source")
                or metadata.get("file_name")
                or metadata.get("filename")
                or metadata.get("path")
                or metadata.get("db_id")
                or item.get("source_db")
                or item.get("source")
                or ""
            )
            title = item.get("title") or (str(path).split("/")[-1] if path else "")
            _add_citation(
                title=str(title or ""),
                path=str(path or ""),
                snippet=str(content or ""),
                source_type="knowledge_base",
                score=item.get("score"),
                reference_id=item.get("reference_id") or item.get("referenceId"),
            )
        elif isinstance(item, str):
            text = item.strip()
            if text:
                _add_citation(
                    title="知识库检索结果",
                    path="",
                    snippet=text,
                    source_type="knowledge_base",
                )

    if isinstance(graph_results, dict):
        graph_type = str(graph_results.get("graph_type") or "neo4j")
        triples = graph_results.get("triples") or []
        if isinstance(triples, list) and triples:
            preview_lines: list[str] = []
            for triple in triples[:3]:
                if isinstance(triple, (list, tuple)) and len(triple) >= 3:
                    h, r, t = triple[:3]
                    preview_lines.append(f"{h} -[{r}]-> {t}")
            if preview_lines:
                _add_citation(
                    title=f"知识图谱({graph_type})",
                    path=f"graph://{graph_type}",
                    snippet="；".join(preview_lines),
                    source_type="knowledge_graph",
                )

        content = graph_results.get("content") or ""
        if isinstance(content, str) and content.strip():
            _add_citation(
                title=f"知识图谱({graph_type})",
                path=f"graph://{graph_type}",
                snippet=content,
                source_type="knowledge_graph",
            )
    elif isinstance(graph_results, list):
        for item in graph_results:
            if isinstance(item, dict):
                content = item.get("content") or item.get("text") or item.get("chunk") or ""
                metadata = item.get("metadata") or {}
                path = (
                    metadata.get("source")
                    or metadata.get("file_name")
                    or metadata.get("filename")
                    or metadata.get("path")
                    or metadata.get("db_id")
                    or item.get("source")
                    or "graph://global"
                )
                title = item.get("title") or (str(path).split("/")[-1] if path else "知识图谱")
                _add_citation(
                    title=str(title or ""),
                    path=str(path or ""),
                    snippet=str(content or ""),
                    source_type="knowledge_graph",
                    score=item.get("score"),
                    reference_id=item.get("reference_id") or item.get("referenceId"),
                )
            elif isinstance(item, str) and item.strip():
                _add_citation(
                    title="知识图谱检索结果",
                    path="graph://global",
                    snippet=item,
                    source_type="knowledge_graph",
                )
    elif isinstance(graph_results, str) and graph_results.strip():
        _add_citation(
            title="知识图谱检索结果",
            path="graph://global",
            snippet=graph_results,
            source_type="knowledge_graph",
        )

    return citations[:max_items]


async def _prefetch_retrieval(
    query_text: str,
    input_context: dict | None,
    retrieval_mode: str,
) -> tuple[list[Any], Any]:
    kb_results: list[Any] = []
    graph_results: Any = None
    context = input_context or {}

    if retrieval_mode in {"mix", "local"}:
        raw_whitelist = context.get("kb_whitelist") or []
        if isinstance(raw_whitelist, str):
            raw_whitelist = [raw_whitelist]
        kb_whitelist = {kb for kb in raw_whitelist if kb}
        try:
            retrievers = knowledge_base.get_retrievers()
        except Exception as e:
            logger.error(f"Failed to get knowledge base retrievers: {e}")
            retrievers = {}

        for db_id, retriever_info in retrievers.items():
            if kb_whitelist and db_id not in kb_whitelist:
                continue
            retriever = retriever_info.get("retriever")
            if not retriever:
                continue
            try:
                result = await retriever(query_text, mode=retrieval_mode)
            except Exception as e:
                logger.error(f"Prefetch KB query failed ({db_id}): {e}")
                continue
            if isinstance(result, list):
                kb_results.extend(result)
            elif result:
                kb_results.append(result)

    if retrieval_mode in {"mix", "global"}:
        graph_name = context.get("graph_name") or "neo4j"
        try:
            if graph_name != "neo4j":
                graph_results = await knowledge_base.aquery(query_text, graph_name, mode="global")
            else:
                graph_results = graph_base.query_node(
                    query_text,
                    hops=2,
                    kgdb_name=graph_name,
                    return_format="triples",
                )
        except Exception as e:
            logger.error(f"Prefetch graph query failed ({graph_name}): {e}")
            graph_results = None

    return kb_results, graph_results


class ChatbotAgent(BaseAgent):
    name = "智能体助手"
    description = "基础的对话机器人，可以回答问题，默认不使用任何工具，可在配置中启用需要的工具。"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graph = None
        self.checkpointer = None
        self.context_schema = Context

    def get_tools(self, runtime: Runtime[Context] = None):
        input_context = _get_runtime_input_context(runtime)
        return get_tools(input_context)

    async def _get_invoke_tools(self, selected_tools: list[str], selected_mcps: list[str], runtime: Runtime[Context] = None):
        """根据配置获取工具。
        工具注入根据 retrieval_mode 进行过滤：
        - llm: 不注入任何工具（纯大模型回答）
        - local: 只注入知识库相关工具（不包括图谱工具）
        - global: 只注入知识图谱相关工具（不包括知识库工具）
        - mix: 注入所有工具
        """
        # 获取 retrieval_mode - 添加详细调试日志
        input_context = None
        retrieval_mode = "mix"
        
        try:
            # 调试：打印 runtime 的结构
            logger.info(f"DEBUG runtime: {runtime}")
            if runtime:
                logger.info(f"DEBUG runtime.config: {getattr(runtime, 'config', 'NO CONFIG')}")
            input_context = _get_runtime_input_context(runtime)
            logger.info(f"DEBUG input_context from runtime.configurable: {input_context}")
            retrieval_mode = input_context.get("retrieval_mode", "mix") if input_context else "mix"
        except Exception as e:
            logger.error(f"Error getting retrieval_mode: {e}")
            retrieval_mode = "mix"
        
        # 在 llm 模式下，不注入任何工具（包括 MCP）
        if retrieval_mode == "llm":
            logger.info("LLM mode: returning empty tools")
            return []
        
        # 每次都重新获取工具，不使用缓存，以确保根据当前 retrieval_mode 获取正确的工具
        # get_tools 内部会调用 get_buildin_tools，它会根据 retrieval_mode 过滤工具
        all_tools = self.get_tools(runtime)
        
        # 图谱相关工具名称
        core_graph_tool_names = {"global_knowledge_graph_search", "knowledge_graph_statistics"}
        
        enabled_tools = []
        
        if retrieval_mode == "local":
            # local 模式：只使用知识库工具，排除所有图谱工具
            enabled_tools = [tool for tool in all_tools if tool.name not in core_graph_tool_names]
            logger.info(f"Local mode: filtered out graph tools, remaining: {[t.name for t in enabled_tools]}")
        elif retrieval_mode == "global":
            # global 模式：只使用图谱工具
            enabled_tools = [tool for tool in all_tools if tool.name in core_graph_tool_names]
            logger.info(f"Global mode: only graph tools: {[t.name for t in enabled_tools]}")
        else:
            # mix 模式：使用所有工具
            enabled_tools = all_tools
            logger.info(f"Mix mode: using all tools: {[t.name for t in enabled_tools]}")
        
        # 如果有 selected_tools 配置，进一步过滤
        if selected_tools and isinstance(selected_tools, list) and len(selected_tools) > 0:
            # 只保留在 selected_tools 中的工具，但仍需遵守 retrieval_mode 的限制
            if retrieval_mode == "local":
                enabled_tools = [tool for tool in enabled_tools 
                                if tool.name in selected_tools and tool.name not in core_graph_tool_names]
            elif retrieval_mode == "global":
                enabled_tools = [tool for tool in enabled_tools 
                                if tool.name in selected_tools or tool.name in core_graph_tool_names]
            else:
                enabled_tools = [tool for tool in enabled_tools if tool.name in selected_tools]
            
            # mix 和 global 模式确保核心图谱工具始终可用
            if retrieval_mode in ("mix", "global"):
                existing_names = {t.name for t in enabled_tools}
                for tool in all_tools:
                    if tool.name in core_graph_tool_names and tool.name not in existing_names:
                        enabled_tools.append(tool)
        
        # 处理 MCP 工具
        if selected_mcps and isinstance(selected_mcps, list) and len(selected_mcps) > 0:
            for mcp in selected_mcps:
                enabled_tools.extend(await get_mcp_tools(mcp))

        logger.info(f"Final enabled tools for {retrieval_mode} mode: {[t.name for t in enabled_tools]}")
        return enabled_tools

    async def _classify_retrieval_policy(self, query_text: str, runtime_context: Context) -> str:
        model_name = (runtime_context.retrieval_classifier_model or runtime_context.model or "").strip()
        if not model_name:
            return "inject"

        model = load_chat_model(model_name)
        system_prompt = (
            "你是检索策略分类器，只能输出 enforce 或 inject。\n"
            "enforce 表示必须先检索，没结果就直接返回资料不足。\n"
            "inject 表示先检索并注入结果，再由模型回答。"
        )
        try:
            response = await model.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query_text},
                ]
            )
        except Exception as e:
            logger.error(f"Retrieval policy classification failed: {e}")
            return "inject"

        content = str(getattr(response, "content", "") or "").strip().lower()
        if "enforce" in content:
            return "enforce"
        if "inject" in content:
            return "inject"
        return "inject"

    async def _decide_retrieval_policy(
        self,
        query_text: str,
        runtime_context: Context,
        retrieval_mode: str,
    ) -> str:
        policy = (getattr(runtime_context, "retrieval_policy", "auto") or "auto").strip().lower()
        if retrieval_mode == "llm":
            return "llm"
        if policy in {"inject", "enforce"}:
            return policy
        if _is_statistical_query(query_text):
            return "enforce"
        if getattr(runtime_context, "retrieval_classifier_enabled", False):
            return await self._classify_retrieval_policy(query_text, runtime_context)
        return "inject"

    async def llm_call(self, state: State, runtime: Runtime[Context] = None) -> dict[str, Any]:
        """调用 llm 模型 - 异步版本以支持异步工具"""
        model = load_chat_model(runtime.context.model)

        input_context = _get_runtime_input_context(runtime) or {}
        retrieval_mode = input_context.get("retrieval_mode", "mix")
        retrieval_context = ""
        statistics_context = ""  # 新增：统计结果上下文
        retrieval_citations: list[dict[str, Any]] = []
        system_prompt = runtime.context.system_prompt
        if retrieval_mode == "llm":
            llm_prompt = getattr(runtime.context, "llm_system_prompt", "") or ""
            system_prompt = llm_prompt or system_prompt

        if _last_message_is_user(state.messages) and retrieval_mode != "llm":
            query_text = _get_latest_user_text(state.messages)
            if query_text:
                has_direct_structured_stats = False
                # 新增：对于统计性问题，直接调用统计函数（无需工具调用）
                if _is_statistical_query(query_text):
                    reservoir_stat_result = _direct_reservoir_count_statistics(query_text)
                    if reservoir_stat_result and reservoir_stat_result.get("text_summary"):
                        has_direct_structured_stats = True
                        statistics_context = reservoir_stat_result["text_summary"]
                        retrieval_citations.append(
                            {
                                "title": "结构化水库统计",
                                "path": reservoir_stat_result.get("source_path") or "dataset://reservoirs",
                                "snippet": statistics_context,
                                "sourceType": "structured_data",
                            }
                        )

                if _is_statistical_query(query_text) and not has_direct_structured_stats and retrieval_mode in {"mix", "global"}:
                    graph_name = input_context.get("graph_name") or "neo4j"
                    stat_result = await _direct_graph_statistics(query_text, graph_name)
                    if stat_result and stat_result.get("text_summary"):
                        statistics_context = stat_result["text_summary"]
                        logger.info(f"Direct statistics injected: {stat_result.get('total_count', 0)} results")
                        retrieval_citations.append(
                            {
                                "title": f"知识图谱统计({graph_name})",
                                "path": f"graph://{graph_name}",
                                "snippet": statistics_context,
                                "sourceType": "knowledge_graph",
                            }
                        )
                
                policy = await self._decide_retrieval_policy(query_text, runtime.context, retrieval_mode)
                if policy in {"inject", "enforce"} and not has_direct_structured_stats:
                    kb_results, graph_results = await _prefetch_retrieval(query_text, input_context, retrieval_mode)
                    has_results = _has_retrieval_results(kb_results, graph_results) or bool(statistics_context)
                    if policy == "enforce" and not has_results:
                        no_result_reply = getattr(runtime.context, "retrieval_no_result_reply", "资料不足") or "资料不足"
                        return {"messages": [AIMessage(content=no_result_reply)]}
                    retrieval_context = _build_retrieval_context(kb_results, graph_results)
                    retrieval_citations.extend(_build_retrieval_citations(kb_results, graph_results))

        # 工具调用功能已禁用，使用预取检索机制代替

        # 使用异步调用
        messages = [{"role": "system", "content": system_prompt}]
        # 新增：先注入统计结果（如果有）
        if statistics_context:
            messages.append({"role": "system", "content": statistics_context})
        if retrieval_context:
            messages.append({"role": "system", "content": retrieval_context})
        messages.extend(state.messages)
        response = cast(
            AIMessage,
            await model.ainvoke(messages),
        )
        if retrieval_citations:
            deduped: list[dict[str, Any]] = []
            seen_citation_keys: set[str] = set()
            for citation in retrieval_citations:
                key = str(citation.get("path") or citation.get("title") or citation.get("referenceId") or "").strip()
                if not key or key in seen_citation_keys:
                    continue
                seen_citation_keys.add(key)
                deduped.append(citation)
            if deduped:
                current_kwargs = dict(getattr(response, "additional_kwargs", {}) or {})
                current_kwargs["citations"] = deduped[:12]
                response = cast(AIMessage, response.model_copy(update={"additional_kwargs": current_kwargs}))
        return {"messages": [response]}

    async def dynamic_tools_node(self, state: State, runtime: Runtime[Context]) -> dict[str, list[ToolMessage]]:
        """Execute tools dynamically based on configuration.

        This function gets the available tools based on the current configuration
        and executes the requested tool calls from the last message.
        """
        # Get available tools based on configuration
        available_tools = await self._get_invoke_tools(runtime.context.tools, runtime.context.mcps, runtime)

        # Create a ToolNode with the available tools
        tool_node = ToolNode(available_tools)

        # Execute the tool node
        result = await tool_node.ainvoke(state)

        return cast(dict[str, list[ToolMessage]], result)

    async def get_graph(self, **kwargs):
        """构建图 - 已禁用工具调用，仅保留对话节点"""
        if self.graph:
            return self.graph

        builder = StateGraph(State, context_schema=self.context_schema)
        builder.add_node("chatbot", self.llm_call)
        builder.add_edge(START, "chatbot")
        builder.add_edge("chatbot", END)

        self.checkpointer = await self._get_checkpointer()
        graph = builder.compile(checkpointer=self.checkpointer, name=self.name)
        self.graph = graph
        return graph


def main():
    pass


if __name__ == "__main__":
    main()
    # asyncio.run(main())
