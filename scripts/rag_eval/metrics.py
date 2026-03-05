"""
Metrics Calculator - 评估指标计算

计算 RAG 系统的各项评估指标
"""

from dataclasses import dataclass, field
from typing import Any
import statistics


@dataclass
class MetricScore:
    """单个指标的统计结果"""
    name: str
    mean: float
    median: float
    std: float
    min: float
    max: float
    count: int
    scores: list[float] = field(default_factory=list)


@dataclass
class EvaluationSummary:
    """评估结果汇总"""
    total_samples: int
    metrics: dict[str, MetricScore]
    avg_latency_ms: float
    failed_count: int
    raw_results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "total_samples": self.total_samples,
            "failed_count": self.failed_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "metrics": {
                name: {
                    "mean": round(score.mean, 4),
                    "median": round(score.median, 4),
                    "std": round(score.std, 4),
                    "min": round(score.min, 4),
                    "max": round(score.max, 4),
                    "count": score.count,
                }
                for name, score in self.metrics.items()
            },
        }


class MetricsCalculator:
    """评估指标计算器"""

    def __init__(self):
        self.results: list[dict] = []

    def add_result(
        self,
        question: str,
        context: str,
        answer: str,
        ground_truth: str,
        faithfulness_score: float,
        relevancy_score: float,
        precision_score: float,
        latency_ms: float,
        extra: dict | None = None,
    ):
        """添加单个评估结果"""
        self.results.append({
            "question": question,
            "context": context[:500] + "..." if len(context) > 500 else context,
            "answer": answer,
            "ground_truth": ground_truth,
            "scores": {
                "faithfulness": faithfulness_score,
                "answer_relevancy": relevancy_score,
                "context_precision": precision_score,
            },
            "latency_ms": latency_ms,
            "extra": extra or {},
        })

    def calculate_summary(self) -> EvaluationSummary:
        """计算汇总统计"""
        if not self.results:
            return EvaluationSummary(
                total_samples=0,
                metrics={},
                avg_latency_ms=0,
                failed_count=0,
            )

        # 收集各指标分数
        metric_scores: dict[str, list[float]] = {
            "faithfulness": [],
            "answer_relevancy": [],
            "context_precision": [],
        }
        latencies = []
        failed_count = 0

        for result in self.results:
            scores = result.get("scores", {})
            for metric_name in metric_scores:
                score = scores.get(metric_name)
                if score is not None:
                    metric_scores[metric_name].append(score)
            
            latency = result.get("latency_ms", 0)
            if latency > 0:
                latencies.append(latency)
            
            if not scores:
                failed_count += 1

        # 计算每个指标的统计值
        metrics = {}
        for name, scores in metric_scores.items():
            if scores:
                metrics[name] = MetricScore(
                    name=name,
                    mean=statistics.mean(scores),
                    median=statistics.median(scores),
                    std=statistics.stdev(scores) if len(scores) > 1 else 0,
                    min=min(scores),
                    max=max(scores),
                    count=len(scores),
                    scores=scores,
                )

        return EvaluationSummary(
            total_samples=len(self.results),
            metrics=metrics,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            failed_count=failed_count,
            raw_results=self.results,
        )

    def get_low_score_samples(
        self, metric: str, threshold: float = 0.5, limit: int = 10
    ) -> list[dict]:
        """获取低分样本用于分析"""
        low_scores = []
        for result in self.results:
            score = result.get("scores", {}).get(metric, 1.0)
            if score < threshold:
                low_scores.append({
                    "question": result["question"],
                    "score": score,
                    "context": result.get("context", "")[:200],
                    "answer": result.get("answer", "")[:200],
                })
        
        # 按分数排序
        low_scores.sort(key=lambda x: x["score"])
        return low_scores[:limit]

    def export_results(self, path: str):
        """导出原始结果为 JSON"""
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
