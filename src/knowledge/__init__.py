import os
import threading

from ..config import config
from .factory import KnowledgeBaseFactory
from .graph import GraphDatabase
from .implementations.lightrag import LightRagKB
from .implementations.milvus import MilvusKB
from .manager import KnowledgeBaseManager

# 注册知识库类型（只保留 Milvus 和 LightRAG）
KnowledgeBaseFactory.register("milvus", MilvusKB, {"description": "基于 Milvus 的生产级向量知识库，支持高性能向量检索"})
KnowledgeBaseFactory.register("lightrag", LightRagKB, {"description": "基于图检索的知识库，支持实体关系构建和复杂查询"})

class _LazyInstance:
    def __init__(self, factory):
        self._factory = factory
        self._instance = None
        self._lock = threading.Lock()

    def _get_instance(self):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance

    def __getattr__(self, item):
        return getattr(self._get_instance(), item)


def _build_knowledge_base() -> KnowledgeBaseManager:
    work_dir = os.path.join(config.save_dir, "knowledge_base_data")
    return KnowledgeBaseManager(work_dir)


def _build_graph_base() -> GraphDatabase:
    return GraphDatabase()


# 创建知识库管理器（延迟初始化，避免导入时阻塞服务启动）
knowledge_base = _LazyInstance(_build_knowledge_base)

# 创建图数据库实例（延迟初始化，避免导入时阻塞服务启动）
graph_base = _LazyInstance(_build_graph_base)

__all__ = ["GraphDatabase", "knowledge_base", "graph_base"]
