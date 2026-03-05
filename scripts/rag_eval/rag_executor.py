"""
RAG Executor - 执行 RAG 查询

调用 Yuxi-Know 的知识库 API 进行检索查询
"""

import asyncio
from dataclasses import dataclass

import httpx


@dataclass
class RAGResult:
    """RAG 查询结果"""
    question: str
    context: str  # 检索到的上下文
    answer: str  # 生成的答案（如果有）
    raw_response: dict  # 原始响应
    latency_ms: float  # 响应时间


class RAGExecutor:
    """RAG 查询执行器"""

    def __init__(
        self,
        api_base_url: str = "http://localhost:5050",
        db_id: str = "",
        query_mode: str = "mix",
        top_k: int = 10,
        timeout: float = 60.0,
        auth_token: str | None = None,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.db_id = db_id
        self.query_mode = query_mode
        self.top_k = top_k
        self.timeout = timeout
        self.auth_token = auth_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    def _format_context(self, result) -> str:
        """Normalize retrieval result into a readable context string."""
        if result is None:
            return ""

        if isinstance(result, list):
            blocks = []
            for idx, item in enumerate(result, 1):
                if isinstance(item, dict):
                    content = item.get("content") or ""
                    if content:
                        blocks.append(f"[{idx}]\n{content}".strip())
                else:
                    blocks.append(str(item))
            return "\n\n".join(blocks).strip()

        if isinstance(result, dict):
            for key in ("context", "content", "result"):
                value = result.get(key)
                if value:
                    return str(value)
            return str(result)

        if isinstance(result, str):
            return result

        return str(result)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def login(self, username: str, password: str) -> str:
        """登录获取 token"""
        client = await self._get_client()
        response = await client.post(
            f"{self.api_base_url}/api/auth/token",
            data={"username": username, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        self.auth_token = data["access_token"]
        
        # 更新 client headers
        if self._client:
            self._client.headers["Authorization"] = f"Bearer {self.auth_token}"
        
        return self.auth_token

    async def query(self, question: str) -> RAGResult:
        """执行单次 RAG 查询"""
        import time
        
        client = await self._get_client()
        
        start_time = time.time()
        response = await client.post(
            f"{self.api_base_url}/api/knowledge/databases/{self.db_id}/query",
            json={
                "query": question,
                "meta": {
                    "mode": self.query_mode,
                    "top_k": self.top_k,
                    "only_need_context": True,  # 只需要检索结果
                },
            },
        )
        latency_ms = (time.time() - start_time) * 1000
        
        response.raise_for_status()
        data = response.json()
        
        # 解析结果
        result = data.get("result", "")
        context_text = self._format_context(result)
        
        return RAGResult(
            question=question,
            context=context_text,
            answer="",  # only_need_context 模式下没有答案
            raw_response=data,
            latency_ms=latency_ms,
        )

    async def query_with_answer(self, question: str) -> RAGResult:
        """执行 RAG 查询并生成答案"""
        import time
        
        client = await self._get_client()
        
        start_time = time.time()
        response = await client.post(
            f"{self.api_base_url}/api/knowledge/databases/{self.db_id}/query",
            json={
                "query": question,
                "meta": {
                    "mode": self.query_mode,
                    "top_k": self.top_k,
                    "only_need_context": False,  # 需要生成答案
                },
            },
        )
        latency_ms = (time.time() - start_time) * 1000
        
        response.raise_for_status()
        data = response.json()
        
        result = data.get("result", "")
        context_text = self._format_context(result)
        answer_text = ""
        if isinstance(result, dict):
            answer_text = result.get("answer") or result.get("response") or ""
        elif isinstance(result, str):
            answer_text = result
        
        return RAGResult(
            question=question,
            context=context_text,
            answer=answer_text,
            raw_response=data,
            latency_ms=latency_ms,
        )

    async def batch_query(
        self,
        questions: list[str],
        concurrency: int = 8,
        with_answer: bool = False,
    ) -> list[RAGResult]:
        """批量执行 RAG 查询"""
        semaphore = asyncio.Semaphore(concurrency)
        
        query_func = self.query_with_answer if with_answer else self.query
        
        async def query_with_semaphore(q: str) -> RAGResult | None:
            async with semaphore:
                try:
                    return await query_func(q)
                except Exception as e:
                    print(f"查询失败 '{q[:50]}...': {e}")
                    return None
        
        tasks = [query_with_semaphore(q) for q in questions]
        results = await asyncio.gather(*tasks)
        
        # 过滤失败的结果
        return [r for r in results if r is not None]

    async def get_databases(self) -> list[dict]:
        """获取所有知识库列表"""
        client = await self._get_client()
        response = await client.get(f"{self.api_base_url}/api/knowledge/databases")
        response.raise_for_status()
        data = response.json()
        return data.get("databases", [])
