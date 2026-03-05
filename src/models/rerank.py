import json
import os

import numpy as np
import requests

from src import config
from src.utils import get_docker_safe_url


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


class OnlineReranker:
    def __init__(self, model_name, api_key, base_url, **kwargs):
        self.url = get_docker_safe_url(base_url)
        self.model = model_name
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def compute_score(self, sentence_pairs, batch_size=256, max_length=512, normalize=False):
        # TODO 还没实现 batch_size
        query, sentences = sentence_pairs[0], sentence_pairs[1]
        payload = self.build_payload(query, sentences, max_length)
        response = requests.request("POST", self.url, json=payload, headers=self.headers)
        response = json.loads(response.text)
        # logger.debug(f"SiliconFlow Reranker response: {response}")

        results = sorted(response["results"], key=lambda x: x["index"])
        all_scores = [result["relevance_score"] for result in results]

        if normalize:
            all_scores = [sigmoid(score) for score in all_scores]

        return all_scores

    def build_payload(self, query, sentences, max_length=512):
        return {
            "model": self.model,
            "query": query,
            "documents": sentences,
            "max_chunks_per_doc": max_length,
        }


def get_reranker(model_id, **kwargs):
    support_rerankers = config.reranker_names.keys()
    assert model_id in support_rerankers, f"Unsupported Reranker: {model_id}, only support {support_rerankers}"

    model_info = config.reranker_names[model_id]
    base_url = model_info["base_url"]
    api_key = os.getenv(model_info["api_key"], model_info["api_key"])
    assert api_key, f"{model_info['name']} api_key is required"
    return OnlineReranker(model_name=model_info["name"], api_key=api_key, base_url=base_url, **kwargs)


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 10,
    reranker_id: str | None = None,
) -> list[dict]:
    """
    对知识库检索结果进行重排序

    Args:
        query: 查询文本
        chunks: 检索到的文档块列表，每个块需要包含 'content' 字段
        top_k: 返回的最大结果数量，默认 10
        reranker_id: reranker 模型 ID，为 None 时使用配置中的默认值

    Returns:
        重排序后的文档块列表，包含 rerank_score 字段
    """
    if not chunks:
        return []

    # 检查是否启用 reranker
    if not config.enable_reranker:
        return chunks[:top_k]

    try:
        # 获取 reranker
        model_id = reranker_id or config.reranker
        reranker = get_reranker(model_id)

        # 准备文档列表
        documents = [chunk.get("content", "") for chunk in chunks]
        
        # 计算重排序分数
        scores = reranker.compute_score([query, documents], normalize=True)
        
        # 将分数添加到 chunks 中
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = scores[i] if i < len(scores) else 0.0

        # 按 rerank_score 降序排序
        sorted_chunks = sorted(chunks, key=lambda x: x.get("rerank_score", 0), reverse=True)

        # 返回 top_k 结果
        return sorted_chunks[:top_k]

    except Exception as e:
        # 如果重排序失败，记录错误并返回原始结果（截取 top_k）
        import traceback
        print(f"Rerank failed: {e}\n{traceback.format_exc()}")
        return chunks[:top_k]
