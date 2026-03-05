"""
Question Generator - 从文档自动生成测试问题

使用本地 LLM 从 markdown 文档中提取关键信息并生成测试问答对
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator

import httpx

QUESTION_GEN_PROMPT = """你是一个专业的测试问题生成专家。请根据以下文档内容生成{num_questions}个高质量的测试问题。

## 文档内容
{content}

## 要求
1. 问题应该能够用文档中的信息直接回答
2. 问题应该覆盖文档的关键信息点
3. 问题类型应该多样化（事实性问题、推理性问题）
4. 每个问题附带一个参考答案（基于文档内容）

## 输出格式
请以 JSON 数组格式输出，每个元素包含：
- question: 问题文本
- answer: 参考答案
- type: 问题类型 (factual/inferential)

示例：
[
  {{"question": "...", "answer": "...", "type": "factual"}},
  {{"question": "...", "answer": "...", "type": "inferential"}}
]

请直接输出 JSON 数组，不要添加其他内容："""


@dataclass
class QuestionAnswer:
    """问答对"""
    question: str
    answer: str
    question_type: str  # factual, inferential
    source_doc: str  # 来源文档路径
    doc_content: str = ""  # 文档内容（用于评估 ground truth）


@dataclass
class TestDataset:
    """测试数据集"""
    items: list[QuestionAnswer] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add(self, qa: QuestionAnswer):
        self.items.append(qa)

    def __len__(self):
        return len(self.items)

    def save(self, path: str):
        """保存为 JSONL 格式"""
        with open(path, "w", encoding="utf-8") as f:
            # 写入元数据
            f.write(json.dumps({"_metadata": self.metadata}, ensure_ascii=False) + "\n")
            # 写入问答对
            for item in self.items:
                f.write(json.dumps({
                    "question": item.question,
                    "answer": item.answer,
                    "type": item.question_type,
                    "source_doc": item.source_doc,
                }, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, path: str) -> "TestDataset":
        """从 JSONL 加载"""
        dataset = cls()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                if "_metadata" in data:
                    dataset.metadata = data["_metadata"]
                else:
                    dataset.add(QuestionAnswer(
                        question=data["question"],
                        answer=data["answer"],
                        question_type=data.get("type", "factual"),
                        source_doc=data["source_doc"],
                    ))
        return dataset


class QuestionGenerator:
    """问题生成器"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen3-32B",
        api_key: str | None = None,
        questions_per_doc: int = 3,
        max_doc_length: int = 8000,
        timeout: float = 180.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.questions_per_doc = questions_per_doc
        self.max_doc_length = max_doc_length
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        
        # 自动检测 API Key
        if api_key:
            self.api_key = api_key
        else:
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

    def _truncate_content(self, content: str) -> str:
        """截断过长的文档内容"""
        if len(content) <= self.max_doc_length:
            return content
        # 保留前半部分和后半部分
        half = self.max_doc_length // 2
        return content[:half] + "\n\n...[内容已截断]...\n\n" + content[-half:]

    async def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """调用 LLM API，支持自动重试"""
        import asyncio
        
        client = await self._get_client()
        
        # 构建请求体
        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2048,
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
                    error_detail = e.response.text if e.response else "No response body"
                    print(f"   API 错误详情: {error_detail}")
                    raise
        
        # 重试次数用尽
        raise last_error

    def _parse_questions(self, response: str, source_doc: str, doc_content: str) -> list[QuestionAnswer]:
        """解析 LLM 生成的问题"""
        # 尝试提取 JSON 数组
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            return []
        
        try:
            items = json.loads(json_match.group())
            questions = []
            for item in items:
                if isinstance(item, dict) and "question" in item:
                    questions.append(QuestionAnswer(
                        question=item["question"],
                        answer=item.get("answer", ""),
                        question_type=item.get("type", "factual"),
                        source_doc=source_doc,
                        doc_content=doc_content,
                    ))
            return questions
        except json.JSONDecodeError:
            return []

    async def generate_from_doc(self, doc_path: str) -> list[QuestionAnswer]:
        """从单个文档生成问题"""
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        truncated_content = self._truncate_content(content)
        prompt = QUESTION_GEN_PROMPT.format(
            num_questions=self.questions_per_doc,
            content=truncated_content,
        )
        
        response = await self._call_llm(prompt)
        return self._parse_questions(response, doc_path, content)

    async def generate_from_directory(
        self,
        docs_dir: str,
        max_docs: int | None = None,
        concurrency: int = 4,
    ) -> TestDataset:
        """从目录批量生成问题"""
        dataset = TestDataset(metadata={
            "source_dir": docs_dir,
            "questions_per_doc": self.questions_per_doc,
        })
        
        # 收集所有 markdown 文件
        doc_paths = []
        for ext in ["*.md", "*.markdown", "*.txt"]:
            doc_paths.extend(Path(docs_dir).rglob(ext))
        
        if max_docs:
            doc_paths = doc_paths[:max_docs]
        
        print(f"找到 {len(doc_paths)} 个文档，开始生成问题...")
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_doc(doc_path: Path) -> list[QuestionAnswer]:
            async with semaphore:
                try:
                    return await self.generate_from_doc(str(doc_path))
                except Exception as e:
                    print(f"处理文档 {doc_path} 失败: {e}")
                    return []
        
        # 并发处理所有文档
        tasks = [process_doc(p) for p in doc_paths]
        results = await asyncio.gather(*tasks)
        
        for questions in results:
            for q in questions:
                dataset.add(q)
        
        print(f"生成完成，共 {len(dataset)} 个问题")
        return dataset
