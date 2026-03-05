"""
RAG Evaluator - 主评估引擎

整合问题生成、RAG 查询、LLM 评估和报告生成的完整流程
"""

import asyncio
import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm_judge import LLMJudge
from .metrics import MetricsCalculator, EvaluationSummary
from .question_generator import QuestionGenerator, TestDataset, QuestionAnswer
from .rag_executor import RAGExecutor, RAGResult
from .report_generator import ReportGenerator


@dataclass
class EvalConfig:
    """评估配置"""
    # 知识库配置
    db_id: str
    api_base_url: str = "http://localhost:5050"
    query_mode: str = "mix"
    top_k: int = 10
    
    # LLM 配置
    llm_base_url: str = "http://localhost:8000/v1"
    llm_model: str = "Qwen/Qwen3-32B"
    
    # 并发配置
    query_concurrency: int = 8
    eval_concurrency: int = 4
    
    # 认证
    username: str = ""
    password: str = ""
    
    @classmethod
    def from_yaml(cls, path: str) -> "EvalConfig":
        """从 YAML 文件加载配置"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        kb = data.get("knowledge_base", {})
        llm = data.get("evaluator_llm", {})
        conc = data.get("concurrency", {})
        
        return cls(
            db_id=kb.get("db_id", ""),
            api_base_url=data.get("api_base_url", "http://localhost:5050"),
            query_mode=kb.get("query_mode", "mix"),
            top_k=kb.get("top_k", 10),
            llm_base_url=llm.get("base_url", "http://localhost:8000/v1"),
            llm_model=llm.get("model", "Qwen/Qwen3-32B"),
            query_concurrency=conc.get("max_concurrent_queries", 8),
            eval_concurrency=conc.get("max_concurrent_evals", 4),
            username=data.get("auth", {}).get("username", ""),
            password=data.get("auth", {}).get("password", ""),
        )


class RAGEvaluator:
    """RAG 评估引擎"""

    def __init__(self, config: EvalConfig):
        self.config = config
        self.rag_executor = RAGExecutor(
            api_base_url=config.api_base_url,
            db_id=config.db_id,
            query_mode=config.query_mode,
            top_k=config.top_k,
        )
        self.llm_judge = LLMJudge(
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        self.metrics_calc = MetricsCalculator()
        self.report_gen = ReportGenerator()

    async def authenticate(self):
        """认证（如果需要）"""
        if self.config.username and self.config.password:
            await self.rag_executor.login(
                self.config.username, 
                self.config.password
            )
            print(f"✅ 认证成功")

    async def run_evaluation(
        self,
        testset: TestDataset,
        progress_callback: callable = None,
    ) -> EvaluationSummary:
        """
        运行完整评估流程
        
        Args:
            testset: 测试数据集
            progress_callback: 进度回调函数 (current, total, message)
        
        Returns:
            评估结果汇总
        """
        total = len(testset)
        print(f"开始评估 {total} 个测试样本...")
        
        # 使用信号量控制并发
        eval_semaphore = asyncio.Semaphore(self.config.eval_concurrency)
        
        async def evaluate_single(idx: int, qa: QuestionAnswer):
            """评估单个样本"""
            async with eval_semaphore:
                try:
                    # 1. 执行 RAG 查询
                    rag_result = await self.rag_executor.query_with_answer(qa.question)
                    answer_for_eval = rag_result.answer or qa.answer
                    
                    # 2. 使用 LLM 评估
                    eval_results = await self.llm_judge.evaluate_all(
                        question=qa.question,
                        context=rag_result.context,
                        answer=answer_for_eval,
                    )
                    
                    # 3. 提取分数
                    scores = {r.metric: r.score for r in eval_results}
                    
                    # 4. 添加到计算器
                    self.metrics_calc.add_result(
                        question=qa.question,
                        context=rag_result.context,
                        answer=answer_for_eval,
                        ground_truth=qa.answer,
                        faithfulness_score=scores.get("faithfulness", 0),
                        relevancy_score=scores.get("answer_relevancy", 0),
                        precision_score=scores.get("context_precision", 0),
                        latency_ms=rag_result.latency_ms,
                    )
                    
                    if progress_callback:
                        progress_callback(idx + 1, total, f"评估中: {qa.question[:30]}...")
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ 评估样本失败: {qa.question[:50]}... - {e}")
                    return False
        
        # 并发评估所有样本
        tasks = [
            evaluate_single(idx, qa) 
            for idx, qa in enumerate(testset.items)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计成功率
        success_count = sum(1 for r in results if r is True)
        print(f"✅ 评估完成: {success_count}/{total} 成功")
        
        # 计算汇总
        return self.metrics_calc.calculate_summary()

    async def generate_report(
        self,
        summary: EvaluationSummary,
        output_path: str | None = None,
    ) -> str:
        """生成评估报告"""
        # 获取低分样本
        low_score_samples = {}
        for metric in ["faithfulness", "answer_relevancy", "context_precision"]:
            low_score_samples[metric] = self.metrics_calc.get_low_score_samples(
                metric, threshold=0.5, limit=5
            )
        
        # 生成并保存报告
        report_path = self.report_gen.save_report(
            summary, 
            low_score_samples,
            filename=output_path,
        )
        
        print(f"📄 报告已保存: {report_path}")
        return report_path

    async def close(self):
        """关闭所有连接"""
        await self.rag_executor.close()
        await self.llm_judge.close()


async def run_full_evaluation(
    docs_path: str | None = None,
    testset_path: str | None = None,
    config_path: str | None = None,
    db_id: str | None = None,
    output_dir: str = "./eval_results",
    sample_size: int | None = None,
    questions_per_doc: int = 3,
    llm_url: str | None = None,
    llm_model: str | None = None,
    username: str | None = None,
    password: str | None = None,
    concurrency: int | None = None,
) -> str:
    """
    运行完整的 RAG 评估流程
    
    Args:
        docs_path: 文档目录（用于生成测试问题）
        testset_path: 已有的测试集路径（二选一）
        config_path: 配置文件路径
        db_id: 知识库 ID
        output_dir: 输出目录
        sample_size: 采样数量（用于测试）
        questions_per_doc: 每个文档生成的问题数
        llm_url: LLM 服务 URL（在线 API 或本地服务）
        llm_model: LLM 模型名称
        username: API 用户名
        password: API 密码
        concurrency: LLM 评估并发数
    
    Returns:
        报告文件路径
    """
    # 加载配置
    if config_path and os.path.exists(config_path):
        config = EvalConfig.from_yaml(config_path)
    else:
        config = EvalConfig(db_id=db_id or "")
    
    # 命令行参数覆盖配置
    if db_id:
        config.db_id = db_id
    if llm_url:
        config.llm_base_url = llm_url
    if llm_model:
        config.llm_model = llm_model
    if username:
        config.username = username
    if password:
        config.password = password
    if concurrency:
        config.eval_concurrency = concurrency
    
    if not config.db_id:
        raise ValueError("必须指定知识库 ID (db_id)")
    
    # 初始化评估器
    evaluator = RAGEvaluator(config)
    
    try:
        # 认证
        await evaluator.authenticate()
        
        # 获取测试集
        if testset_path and os.path.exists(testset_path):
            print(f"加载测试集: {testset_path}")
            testset = TestDataset.load(testset_path)
        elif docs_path:
            print(f"从文档生成测试问题: {docs_path}")
            generator = QuestionGenerator(
                base_url=config.llm_base_url,
                model=config.llm_model,
                questions_per_doc=questions_per_doc,
            )
            testset = await generator.generate_from_directory(
                docs_path,
                max_docs=sample_size,
                concurrency=config.eval_concurrency,
            )
            await generator.close()
            
            # 保存生成的测试集
            testset_save_path = os.path.join(output_dir, "testset.jsonl")
            os.makedirs(output_dir, exist_ok=True)
            testset.save(testset_save_path)
            print(f"测试集已保存: {testset_save_path}")
        else:
            raise ValueError("必须指定 docs_path 或 testset_path")
        
        # 如果指定了采样
        if sample_size and len(testset) > sample_size:
            testset.items = testset.items[:sample_size]
            print(f"采样 {sample_size} 个测试样本")
        
        # 运行评估
        summary = await evaluator.run_evaluation(testset)
        
        # 生成报告
        report_path = await evaluator.generate_report(summary)
        
        # 打印摘要
        print("\n" + "=" * 50)
        print("📊 评估结果摘要")
        print("=" * 50)
        for name, score in summary.metrics.items():
            print(f"  {name}: {score.mean:.2%} (±{score.std:.2%})")
        print(f"  平均延迟: {summary.avg_latency_ms:.2f}ms")
        print("=" * 50)
        
        return report_path
        
    finally:
        await evaluator.close()
