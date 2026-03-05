import traceback
import math
import os
import time
import asyncio

from neo4j import GraphDatabase as Neo4jDriver

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.storage.db.models import User
from server.utils.auth_middleware import get_admin_user, get_required_user
from src import graph_base, knowledge_base
from src.utils.logging_config import logger

graph = APIRouter(prefix="/graph", tags=["graph"])

_STATS_CACHE_TTL_SECONDS = 300
_stats_cache: dict[str, dict] = {}
_stats_cache_lock = asyncio.Lock()
_stats_locks: dict[str, asyncio.Lock] = {}


def _get_stats_lock(db_id: str) -> asyncio.Lock:
    lock = _stats_locks.get(db_id)
    if lock is None:
        lock = asyncio.Lock()
        _stats_locks[db_id] = lock
    return lock


def _read_stats_cache(db_id: str) -> dict | None:
    entry = _stats_cache.get(db_id)
    if not entry:
        return None
    if time.monotonic() - entry["ts"] > _STATS_CACHE_TTL_SECONDS:
        _stats_cache.pop(db_id, None)
        return None
    return entry["data"]


def _write_stats_cache(db_id: str, data: dict) -> None:
    _stats_cache[db_id] = {"ts": time.monotonic(), "data": data}


def _get_neo4j_labels() -> set[str]:
    """获取 Neo4j 当前存在的所有标签，用于判断某个 LightRAG workspace 是否有图谱数据。"""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    username = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "0123456789")

    driver = Neo4jDriver.driver(uri, auth=(username, password))
    try:
        with driver.session() as session:
            records = session.run("CALL db.labels() YIELD label RETURN label")
            return {r["label"] for r in records if r and r.get("label")}
    finally:
        driver.close()


# =============================================================================
# === 子图查询分组 ===
# =============================================================================


@graph.get("/lightrag/subgraph")
async def get_lightrag_subgraph(
    db_id: str = Query(..., description="数据库ID"),
    node_label: str = Query(..., description="节点标签或实体名称"),
    max_depth: int = Query(2, description="最大深度", ge=1, le=5),
    max_nodes: int = Query(100, description="最大节点数", ge=1, le=1000),
    current_user: User = Depends(get_required_user),
):
    """
    使用 LightRAG 原生方法获取知识图谱子图

    Args:
        db_id: LightRAG 数据库实例ID
        node_label: 节点标签，用于查找起始节点，使用 "*" 获取全图
        max_depth: 子图的最大深度
        max_nodes: 返回的最大节点数量

    Returns:
        包含节点和边的知识图谱数据
    """
    try:
        logger.info(
            f"获取子图数据 - db_id: {db_id}, node_label: {node_label}, max_depth: {max_depth}, max_nodes: {max_nodes}"
        )

        # 检查是否是 LightRAG 数据库
        if not knowledge_base.is_lightrag_database(db_id):
            raise HTTPException(
                status_code=400, detail=f"数据库 {db_id} 不是 LightRAG 类型，图谱功能仅支持 LightRAG 知识库"
            )

        # 获取 LightRAG 实例
        rag_instance = await knowledge_base._get_lightrag_instance(db_id)
        if not rag_instance:
            raise HTTPException(status_code=404, detail=f"LightRAG 数据库 {db_id} 不存在或无法访问")

        # 使用 LightRAG 的原生 get_knowledge_graph 方法
        knowledge_graph = await rag_instance.get_knowledge_graph(
            node_label=node_label, max_depth=max_depth, max_nodes=max_nodes
        )

        # 将 LightRAG 的 KnowledgeGraph 格式转换为前端需要的格式
        nodes = []
        for node in knowledge_graph.nodes:
            nodes.append(
                {
                    "id": node.id,
                    "labels": node.labels,
                    "entity_type": node.properties.get("entity_type", "unknown"),
                    "properties": node.properties,
                }
            )

        edges = []
        for edge in knowledge_graph.edges:
            edges.append(
                {
                    "id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "properties": edge.properties,
                }
            )

        result = {
            "success": True,
            "data": {
                "nodes": nodes,
                "edges": edges,
                "is_truncated": knowledge_graph.is_truncated,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        }

        logger.info(f"成功获取子图 - 节点数: {len(nodes)}, 边数: {len(edges)}")
        return result

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        logger.error(f"获取子图数据失败: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取子图数据失败: {str(e)}")


# =============================================================================
# === 通用子图（分页 + 紧凑字段） ===
# =============================================================================


@graph.get("/subgraph")
async def get_subgraph(
    db_id: str = Query(..., description="数据库ID"),
    center: str = Query("*", description="中心节点标识或 '*' 代表全图"),
    depth: int = Query(2, description="最大深度", ge=1, le=5),
    limit: int = Query(200, description="每页节点数", ge=1, le=1000),
    page: int = Query(1, description="页码(从1开始)", ge=1),
    fields: str = Query("compact", description="字段模式: compact | full"),
    current_user: User = Depends(get_required_user),
):
    """
    通用子图接口，支持分页与紧凑字段返回。

    注意：当前实现基于 LightRAG 子图结果进行分页切片，
    后续可根据真实存储添加更高效的分页与过滤。
    """
    try:
        # 仅支持 LightRAG 知识库
        if not knowledge_base.is_lightrag_database(db_id):
            raise HTTPException(status_code=400, detail="当前仅支持 LightRAG 知识库的通用子图查询")

        # 计算需要获取的最大节点数以满足分页
        fetch_max = min(limit * page, 5000)

        rag_instance = await knowledge_base._get_lightrag_instance(db_id)
        if not rag_instance:
            raise HTTPException(status_code=404, detail=f"LightRAG 数据库 {db_id} 不存在或无法访问")

        # 拉取子图（可能超出本页大小），随后在内存中切片
        kg = await rag_instance.get_knowledge_graph(
            node_label=center, max_depth=depth, max_nodes=fetch_max
        )

        total_nodes_all = len(kg.nodes)
        total_edges_all = len(kg.edges)

        # ====== 诊断日志：检查 LightRAG 返回的原始数据 ======
        logger.info(f"[诊断] LightRAG 原始数据 - 节点数: {total_nodes_all}, 边数: {total_edges_all}")
        if total_nodes_all > 0:
            sample_node = kg.nodes[0]
            logger.info(f"[诊断] 节点样本 - id: {sample_node.id}, type(id): {type(sample_node.id)}, "
                        f"labels: {getattr(sample_node, 'labels', 'N/A')}, "
                        f"properties: {getattr(sample_node, 'properties', {})}")
        if total_edges_all > 0:
            sample_edge = kg.edges[0]
            logger.info(f"[诊断] 边样本 - source: {getattr(sample_edge, 'source', 'N/A')}, "
                        f"target: {getattr(sample_edge, 'target', 'N/A')}, "
                        f"type: {getattr(sample_edge, 'type', 'N/A')}, "
                        f"所有属性: {dir(sample_edge)}")
        else:
            logger.warning(f"[诊断] LightRAG 返回了 0 条边！这是问题的根源。")
        # ====== 诊断日志结束 ======

        # 计算分页窗口
        start = (page - 1) * limit
        end = min(start + limit, total_nodes_all)
        if start >= total_nodes_all:
            paged_nodes_raw = []
        else:
            paged_nodes_raw = kg.nodes[start:end]

        included_ids = {str(n.id) for n in paged_nodes_raw}

        # 过滤边：仅保留两端都在当前页节点集合内的边
        paged_edges_raw = [
            e for e in kg.edges if str(e.source) in included_ids and str(e.target) in included_ids
        ]

        # ====== 诊断日志：检查边过滤结果 ======
        logger.info(f"[诊断] 节点ID集合样本(前5个): {list(included_ids)[:5]}")
        logger.info(f"[诊断] 过滤后边数: {len(paged_edges_raw)} (原始: {total_edges_all})")
        if total_edges_all > 0 and len(paged_edges_raw) == 0:
            # 边过滤导致全部边丢失，输出边的source/target看看为什么不匹配
            sample_sources = [str(e.source) for e in kg.edges[:5]]
            sample_targets = [str(e.target) for e in kg.edges[:5]]
            logger.warning(f"[诊断] 边被过滤掉了！边的source样本: {sample_sources}, target样本: {sample_targets}")
        # ====== 诊断日志结束 ======

        # 计算度（当前页内的度）
        degree_map: dict[str, int] = {}
        for e in paged_edges_raw:
            s = str(e.source)
            t = str(e.target)
            degree_map[s] = degree_map.get(s, 0) + 1
            degree_map[t] = degree_map.get(t, 0) + 1

        def _node_label(n) -> str:
            props = getattr(n, "properties", {}) or {}
            if isinstance(props, dict) and props.get("entity_id"):
                return str(props.get("entity_id"))
            labels = getattr(n, "labels", []) or []
            if labels:
                return str(labels[0])
            return str(getattr(n, "id", ""))

        # 构造节点返回
        nodes = []
        for n in paged_nodes_raw:
            nid = str(n.id)
            if fields == "compact":
                nodes.append(
                    {
                        "id": nid,
                        "label": _node_label(n),
                        "type": (getattr(n, "properties", {}) or {}).get("entity_type", "unknown"),
                        "degree": degree_map.get(nid, 0),
                    }
                )
            else:
                nodes.append(
                    {
                        "id": nid,
                        "labels": list(getattr(n, "labels", []) or []),
                        "entity_type": (getattr(n, "properties", {}) or {}).get("entity_type", "unknown"),
                        "properties": getattr(n, "properties", {}) or {},
                        "degree": degree_map.get(nid, 0),
                    }
                )

        # 构造边返回（紧凑：不含 properties）
        edges = []
        for e in paged_edges_raw:
            ed = {
                "id": str(e.id),
                "source": str(e.source),
                "target": str(e.target),
                "type": getattr(e, "type", "DIRECTED"),
            }
            if fields != "compact":
                ed["properties"] = getattr(e, "properties", {}) or {}
            edges.append(ed)

        total_pages = max(1, math.ceil(total_nodes_all / limit)) if limit else 1

        return {
            "success": True,
            "data": {
                "nodes": nodes,
                "edges": edges,
                "paging": {
                    "page": page,
                    "limit": limit,
                    "total_nodes": total_nodes_all,
                    "total_edges": total_edges_all,
                    "total_pages": total_pages,
                },
                "is_truncated": total_nodes_all > end,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"通用子图查询失败: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"通用子图查询失败: {str(e)}")


@graph.get("/lightrag/databases")
async def get_lightrag_databases(current_user: User = Depends(get_required_user)):
    """
    获取所有可用的 LightRAG 知识库列表

    Returns:
        可用的 LightRAG 知识库列表
    """
    try:
        databases = knowledge_base.get_lightrag_databases()
        # 仅返回在 Neo4j 中已存在图谱数据的知识库，避免前端加载到空图谱库
        try:
            neo4j_labels = _get_neo4j_labels()
            databases = [db for db in databases if (db.get("db_id") or "") in neo4j_labels]
        except Exception as e:
            logger.warning(f"按 Neo4j 标签过滤 LightRAG 知识库失败，将回退为按文件数过滤: {e}")
            databases = [db for db in databases if (db.get("row_count") or 0) > 0]
        return {"success": True, "data": {"databases": databases}}

    except Exception as e:
        logger.error(f"获取图数据库列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图数据库列表失败: {str(e)}")


# =============================================================================
# === 节点管理分组 ===
# =============================================================================


@graph.get("/lightrag/labels")
async def get_lightrag_labels(
    db_id: str = Query(..., description="数据库ID"), current_user: User = Depends(get_required_user)
):
    """
    获取知识图谱中的所有标签

    Args:
        db_id: LightRAG 数据库实例ID

    Returns:
        图谱中所有可用的标签列表
    """
    try:
        logger.info(f"获取图谱标签 - db_id: {db_id}")

        # 检查是否是 LightRAG 数据库
        if not knowledge_base.is_lightrag_database(db_id):
            raise HTTPException(
                status_code=400, detail=f"数据库 {db_id} 不是 LightRAG 类型，图谱功能仅支持 LightRAG 知识库"
            )

        # 获取 LightRAG 实例
        rag_instance = await knowledge_base._get_lightrag_instance(db_id)
        if not rag_instance:
            raise HTTPException(status_code=404, detail=f"LightRAG 数据库 {db_id} 不存在或无法访问")

        # 使用 LightRAG 的原生方法获取所有标签
        labels = await rag_instance.get_graph_labels()

        return {"success": True, "data": {"labels": labels}}

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        logger.error(f"获取图谱标签失败: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取图谱标签失败: {str(e)}")


@graph.get("/neo4j/nodes")
async def get_neo4j_nodes(
    kgdb_name: str = Query(..., description="知识图谱数据库名称"),
    num: int = Query(100, description="节点数量", ge=1, le=1000),
    current_user: User = Depends(get_required_user),
):
    """
    获取图谱节点样本数据
    """
    try:
        logger.debug(f"Get graph nodes in {kgdb_name} with {num} nodes")

        if not graph_base.is_running():
            raise HTTPException(status_code=400, detail="图数据库未启动")

        result = graph_base.get_sample_nodes(kgdb_name, num)

        return {"success": True, "result": result, "message": "success"}

    except Exception as e:
        logger.error(f"获取图节点数据失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取图节点数据失败: {str(e)}")


@graph.get("/neo4j/node")
async def get_neo4j_node(
    entity_name: str = Query(..., description="实体名称"), current_user: User = Depends(get_required_user)
):
    """
    根据实体名称查询图节点
    """
    try:
        if not graph_base.is_running():
            raise HTTPException(status_code=400, detail="图数据库未启动")

        result = graph_base.query_node(keyword=entity_name)

        return {"success": True, "result": result, "message": "success"}

    except Exception as e:
        logger.error(f"查询图节点失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"查询图节点失败: {str(e)}")


@graph.get("/neo4j/expand")
async def expand_neo4j_node(
    node_id: str = Query(..., description="Neo4j elementId"),
    limit: int = Query(80, description="最大边数量", ge=1, le=500),
    current_user: User = Depends(get_required_user),
):
    """
    通过 Neo4j elementId 展开一个节点的 1-hop 邻居子图
    """
    try:
        if not graph_base.is_running():
            raise HTTPException(status_code=400, detail="图数据库未启动")

        result = graph_base.expand_node_by_id(node_id=node_id, limit=limit)
        return {"success": True, "result": result, "message": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"展开节点失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"展开节点失败: {str(e)}")


# =============================================================================
# === 边管理分组 ===
# =============================================================================

# 可以在这里添加边相关的管理功能

# =============================================================================
# === 图谱分析分组 ===
# =============================================================================


@graph.get("/lightrag/stats")
async def get_lightrag_stats(
    db_id: str = Query(..., description="数据库ID"), current_user: User = Depends(get_required_user)
):
    """
    获取知识图谱统计信息
    """
    try:
        logger.info(f"获取图谱统计信息 - db_id: {db_id}")

        # 检查是否是 LightRAG 数据库
        if not knowledge_base.is_lightrag_database(db_id):
            raise HTTPException(
                status_code=400, detail=f"数据库 {db_id} 不是 LightRAG 类型，图谱功能仅支持 LightRAG 知识库"
            )

        async with _stats_cache_lock:
            cached = _read_stats_cache(db_id)
        if cached is not None:
            return {"success": True, "data": cached, "cached": True}

        async with _get_stats_lock(db_id):
            async with _stats_cache_lock:
                cached = _read_stats_cache(db_id)
            if cached is not None:
                return {"success": True, "data": cached, "cached": True}

            # 获取 LightRAG 实例
            rag_instance = await knowledge_base._get_lightrag_instance(db_id)
            if not rag_instance:
                raise HTTPException(status_code=404, detail=f"LightRAG 数据库 {db_id} 不存在或无法访问")

            # 通过获取全图来统计节点和边的数量
            knowledge_graph = await rag_instance.get_knowledge_graph(
                node_label="*",
                max_depth=1,
                max_nodes=10000,  # 设置较大值以获取完整统计
            )

            # 统计实体类型分布
            entity_types = {}
            for node in knowledge_graph.nodes:
                entity_type = node.properties.get("entity_type", "unknown")
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

            entity_types_list = [
                {"type": k, "count": v} for k, v in sorted(entity_types.items(), key=lambda x: x[1], reverse=True)
            ]

            payload = {
                "total_nodes": len(knowledge_graph.nodes),
                "total_edges": len(knowledge_graph.edges),
                "entity_types": entity_types_list,
                "is_truncated": knowledge_graph.is_truncated,
            }

            async with _stats_cache_lock:
                _write_stats_cache(db_id, payload)

            return {"success": True, "data": payload, "cached": False}

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        logger.error(f"获取图谱统计信息失败: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取图谱统计信息失败: {str(e)}")


@graph.get("/neo4j/info")
async def get_neo4j_info(current_user: User = Depends(get_required_user)):
    """获取Neo4j图数据库信息"""
    try:
        graph_info = graph_base.get_graph_info()
        if graph_info is None:
            raise HTTPException(status_code=400, detail="图数据库获取出错")
        return {"success": True, "data": graph_info}
    except Exception as e:
        logger.error(f"获取图数据库信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图数据库信息失败: {str(e)}")


@graph.post("/neo4j/index-entities")
async def index_neo4j_entities(data: dict = Body(default={}), current_user: User = Depends(get_admin_user)):
    """为Neo4j图谱节点添加嵌入向量索引"""
    try:
        if not graph_base.is_running():
            raise HTTPException(status_code=400, detail="图数据库未启动")

        # 获取参数或使用默认值
        kgdb_name = data.get("kgdb_name", "neo4j")

        # 调用GraphDatabase的add_embedding_to_nodes方法
        count = graph_base.add_embedding_to_nodes(kgdb_name=kgdb_name)

        return {
            "success": True,
            "status": "success",
            "message": f"已成功为{count}个节点添加嵌入向量",
            "indexed_count": count,
        }
    except Exception as e:
        logger.error(f"索引节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"索引节点失败: {str(e)}")


@graph.post("/neo4j/add-entities")
async def add_neo4j_entities(
    file_path: str = Body(...), kgdb_name: str | None = Body(None), current_user: User = Depends(get_admin_user)
):
    """通过JSONL文件添加图谱实体到Neo4j"""
    from pathlib import Path
    import os

    # 定义允许的上传目录（相对于项目根目录）
    ALLOWED_DIRS = [
        Path("saves").resolve(),
        Path("uploads").resolve(),
    ]

    try:
        # 验证文件扩展名
        if not file_path.endswith(".jsonl"):
            raise HTTPException(status_code=400, detail="文件格式错误，请上传jsonl文件")

        # 路径安全验证：解析绝对路径并检查是否在允许的目录内
        requested_path = Path(file_path).resolve()

        # 检查文件是否在允许的目录中
        is_safe = False
        for allowed_dir in ALLOWED_DIRS:
            try:
                requested_path.relative_to(allowed_dir)
                is_safe = True
                break
            except ValueError:
                continue

        if not is_safe:
            logger.warning(f"路径遍历尝试被阻止: {file_path} -> {requested_path}")
            raise HTTPException(status_code=400, detail="无效的文件路径：文件必须位于允许的目录中")

        # 检查文件是否存在
        if not requested_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        if not requested_path.is_file():
            raise HTTPException(status_code=400, detail="路径不是有效的文件")

        await graph_base.jsonl_file_add_entity(str(requested_path), kgdb_name)
        return {"success": True, "message": "实体添加成功", "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加实体失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"添加实体失败: {e}")
