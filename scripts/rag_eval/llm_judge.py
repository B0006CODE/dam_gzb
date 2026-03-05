"""
LLM Judge - 使用本地 Qwen3-32B 进行 RAG 评估打分

支持 vLLM 和 Ollama 两种本地模型服务
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Literal

import httpx

# 评估 Prompt 模板
FAITHFULNESS_PROMPT = """你是一位 RAG 系统评估专家。请评估以下回答的**忠实度**（答案是否完全基于检索到的上下文，无任何幻觉）。

## 问题
{question}

## 检索到的上下文
{context}

## 系统回答
{answer}

## 评分标准
- 10分：答案完全基于上下文，无任何幻觉或编造
- 7-9分：答案主要基于上下文，有少量合理推断
- 4-6分：答案部分基于上下文，存在一些未经证实的内容
- 1-3分：答案大部分与上下文无关，存在明显幻觉
- 0分：答案完全脱离上下文，严重幻觉

请以 JSON 格式输出：
{{"score": <0-10的整数>, "reason": "<简要理由>"}}"""

RELEVANCY_PROMPT = """你是一位 RAG 系统评估专家。请评估以下回答与问题的**相关性**（答案是否正确回答了用户的问题）。

## 问题
{question}

## 系统回答
{answer}

## 评分标准
- 10分：答案完美回答了问题，信息完整准确
- 7-9分：答案基本回答了问题，信息较完整
- 4-6分：答案部分回答了问题，遗漏了一些关键信息
- 1-3分：答案与问题相关但未正确回答
- 0分：答案与问题完全无关

请以 JSON 格式输出：
{{"score": <0-10的整数>, "reason": "<简要理由>"}}"""

CONTEXT_PRECISION_PROMPT = """你是一位 RAG 系统评估专家。请评估以下检索结果的**精确度**（检索到的内容有多少是与问题真正相关的）。

## 问题
{question}

## 检索到的上下文片段
{context}

## 评分标准
- 10分：所有检索内容都与问题高度相关
- 7-9分：大部分检索内容与问题相关
- 4-6分：约一半检索内容与问题相关
- 1-3分：仅少量检索内容与问题相关
- 0分：检索内容与问题完全无关

请以 JSON 格式输出：
{{"score": <0-10的整数>, "reason": "<简要理由>", "relevant_count": <相关片段数量>}}"""


@dataclass
class EvalResult:
    """评估结果"""
    metric: str
    score: float  # 0-1 归一化分数
    raw_score: int  # 0-10 原始分数
    reason: str
    extra: dict | None = None


class LLMJudge:
    """使用 LLM 进行评估打分，支持本地和在线 API"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen3-32B",
        api_key: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        
        # 自动检测 API Key
        if api_key:
            self.api_key = api_key
        else:
            # 根据 base_url 自动检测对应的环境变量
            self.api_key = self._auto_detect_api_key()

    def _auto_detect_api_key(self) -> str | None:
        """根据 base_url 自动检测对应的 API Key"""
        url_to_env = {
            "siliconflow": "SILICONFLOW_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "dashscope": "DASHSCOPE_API_KEY",
            "bigmodel": "ZHIPUAI_API_KEY",
            "together": "TOGETHER_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "ark": "ARK_API_KEY",
            "host.docker.internal": "VLLM_API_KEY",
            "vllm": "VLLM_API_KEY",
        }
        for keyword, env_var in url_to_env.items():
            if keyword in self.base_url.lower():
                key = os.getenv(env_var)
                if key:
                    print(f"✓ 使用 {env_var} 进行认证")
                    return key
        return None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """调用 LLM API，支持自动重试"""
        import asyncio
        
        client = await self._get_client()
        
        # 构建请求体
        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # 对于 qwen3 模型，需要关闭 thinking 模式（非流式调用时必须）
        if "qwen3" in self.model.lower():
            request_body["enable_thinking"] = False
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=request_body,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # 限流，等待后重试
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    print(f"   ⏳ 限流，等待 {wait_time}s 后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        # 重试次数用尽
        raise last_error

    def _parse_json_response(self, response: str) -> dict:
        """解析 LLM 的 JSON 响应"""
        import json
        import re

        # 尝试提取 JSON 块
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # 如果解析失败，返回默认值
        return {"score": 5, "reason": "无法解析评估结果"}

    async def evaluate_faithfulness(
        self, question: str, context: str, answer: str
    ) -> EvalResult:
        """评估答案忠实度"""
        prompt = FAITHFULNESS_PROMPT.format(
            question=question, context=context, answer=answer
        )
        response = await self._call_llm(prompt)
        parsed = self._parse_json_response(response)
        
        raw_score = max(0, min(10, int(parsed.get("score", 5))))
        return EvalResult(
            metric="faithfulness",
            score=raw_score / 10.0,
            raw_score=raw_score,
            reason=parsed.get("reason", ""),
        )

    async def evaluate_relevancy(self, question: str, answer: str) -> EvalResult:
        """评估答案相关性"""
        prompt = RELEVANCY_PROMPT.format(question=question, answer=answer)
        response = await self._call_llm(prompt)
        parsed = self._parse_json_response(response)
        
        raw_score = max(0, min(10, int(parsed.get("score", 5))))
        return EvalResult(
            metric="answer_relevancy",
            score=raw_score / 10.0,
            raw_score=raw_score,
            reason=parsed.get("reason", ""),
        )

    async def evaluate_context_precision(
        self, question: str, context: str
    ) -> EvalResult:
        """评估检索精确度"""
        prompt = CONTEXT_PRECISION_PROMPT.format(question=question, context=context)
        response = await self._call_llm(prompt)
        parsed = self._parse_json_response(response)
        
        raw_score = max(0, min(10, int(parsed.get("score", 5))))
        return EvalResult(
            metric="context_precision",
            score=raw_score / 10.0,
            raw_score=raw_score,
            reason=parsed.get("reason", ""),
            extra={"relevant_count": parsed.get("relevant_count")},
        )

    async def evaluate_all(
        self, question: str, context: str, answer: str
    ) -> list[EvalResult]:
        """并行执行所有评估"""
        results = await asyncio.gather(
            self.evaluate_faithfulness(question, context, answer),
            self.evaluate_relevancy(question, answer),
            self.evaluate_context_precision(question, context),
            return_exceptions=True,
        )
        
        # 过滤异常结果
        valid_results = []
        for r in results:
            if isinstance(r, EvalResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                print(f"评估异常: {r}")
        
        return valid_results
