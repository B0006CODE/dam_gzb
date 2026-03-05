"""
Report Generator - 生成评估报告

支持 HTML 和 Markdown 两种格式
"""

import json
import os
from datetime import datetime
from pathlib import Path

from .metrics import EvaluationSummary


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG 评估报告 - {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .card h2 {{
            color: #00d4ff;
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}
        .metric-card {{
            background: rgba(0, 212, 255, 0.1);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        }}
        .metric-name {{ color: #888; font-size: 0.9rem; margin-bottom: 0.5rem; }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #00d4ff;
        }}
        .metric-value.good {{ color: #10b981; }}
        .metric-value.medium {{ color: #f59e0b; }}
        .metric-value.bad {{ color: #ef4444; }}
        .metric-details {{ color: #666; font-size: 0.8rem; margin-top: 0.5rem; }}
        .stats-row {{
            display: flex;
            justify-content: space-around;
            text-align: center;
            padding: 1rem 0;
        }}
        .stat {{ }}
        .stat-value {{ font-size: 1.5rem; font-weight: bold; color: #7c3aed; }}
        .stat-label {{ color: #888; font-size: 0.85rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        th {{ color: #00d4ff; font-weight: 600; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.05); }}
        .score-bar {{
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }}
        .score-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 2rem;
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 RAG 评估报告</h1>
        <p class="subtitle">生成时间: {timestamp}</p>
        
        <div class="card">
            <h2>📊 总体概览</h2>
            <div class="stats-row">
                <div class="stat">
                    <div class="stat-value">{total_samples}</div>
                    <div class="stat-label">测试样本数</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{failed_count}</div>
                    <div class="stat-label">失败数量</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{avg_latency}ms</div>
                    <div class="stat-label">平均延迟</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📈 评估指标</h2>
            <div class="metrics-grid">
                {metrics_cards}
            </div>
        </div>
        
        <div class="card">
            <h2>📋 指标详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>均值</th>
                        <th>中位数</th>
                        <th>标准差</th>
                        <th>最小值</th>
                        <th>最大值</th>
                        <th>分布</th>
                    </tr>
                </thead>
                <tbody>
                    {metrics_table_rows}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>⚠️ 低分样本分析</h2>
            <p style="color: #888; margin-bottom: 1rem;">以下是各指标得分较低的样本，供调试参考：</p>
            {low_score_samples}
        </div>
        
        <div class="footer">
            <p>Powered by Yuxi-Know RAG Evaluation Framework</p>
        </div>
    </div>
</body>
</html>
"""


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "./eval_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_score_class(self, score: float) -> str:
        """根据分数返回 CSS 类名"""
        if score >= 0.8:
            return "good"
        elif score >= 0.6:
            return "medium"
        return "bad"

    def _get_score_color(self, score: float) -> str:
        """根据分数返回颜色"""
        if score >= 0.8:
            return "#10b981"
        elif score >= 0.6:
            return "#f59e0b"
        return "#ef4444"

    def _format_metric_name(self, name: str) -> str:
        """格式化指标名称"""
        names = {
            "faithfulness": "忠实度",
            "answer_relevancy": "答案相关性",
            "context_precision": "检索精确度",
            "context_recall": "检索召回率",
        }
        return names.get(name, name)

    def generate_html(
        self,
        summary: EvaluationSummary,
        low_score_samples: dict[str, list[dict]] | None = None,
    ) -> str:
        """生成 HTML 报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 生成指标卡片
        metrics_cards = ""
        for name, score in summary.metrics.items():
            score_class = self._get_score_class(score.mean)
            metrics_cards += f"""
                <div class="metric-card">
                    <div class="metric-name">{self._format_metric_name(name)}</div>
                    <div class="metric-value {score_class}">{score.mean:.1%}</div>
                    <div class="metric-details">样本数: {score.count}</div>
                </div>
            """
        
        # 生成指标表格行
        metrics_table_rows = ""
        for name, score in summary.metrics.items():
            color = self._get_score_color(score.mean)
            metrics_table_rows += f"""
                <tr>
                    <td>{self._format_metric_name(name)}</td>
                    <td>{score.mean:.4f}</td>
                    <td>{score.median:.4f}</td>
                    <td>{score.std:.4f}</td>
                    <td>{score.min:.4f}</td>
                    <td>{score.max:.4f}</td>
                    <td>
                        <div class="score-bar">
                            <div class="score-bar-fill" style="width: {score.mean*100}%; background: {color};"></div>
                        </div>
                    </td>
                </tr>
            """
        
        # 生成低分样本部分
        low_score_html = ""
        if low_score_samples:
            for metric, samples in low_score_samples.items():
                if samples:
                    low_score_html += f"<h4 style='color: #f59e0b; margin: 1rem 0 0.5rem;'>{self._format_metric_name(metric)}</h4>"
                    low_score_html += "<ul style='color: #888; font-size: 0.9rem;'>"
                    for sample in samples[:3]:
                        low_score_html += f"""
                            <li style="margin-bottom: 0.5rem;">
                                <strong>问题:</strong> {sample['question'][:100]}... <br>
                                <strong>得分:</strong> {sample['score']:.2f}
                            </li>
                        """
                    low_score_html += "</ul>"
        else:
            low_score_html = "<p style='color: #888;'>暂无低分样本数据</p>"
        
        # 填充模板
        html = HTML_TEMPLATE.format(
            timestamp=timestamp,
            total_samples=summary.total_samples,
            failed_count=summary.failed_count,
            avg_latency=round(summary.avg_latency_ms, 2),
            metrics_cards=metrics_cards,
            metrics_table_rows=metrics_table_rows,
            low_score_samples=low_score_html,
        )
        
        return html

    def save_report(
        self,
        summary: EvaluationSummary,
        low_score_samples: dict[str, list[dict]] | None = None,
        filename: str | None = None,
    ) -> str:
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rag_eval_report_{timestamp}.html"
        
        html = self.generate_html(summary, low_score_samples)
        
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        
        # 同时保存 JSON 格式的原始数据
        json_path = self.output_dir / filename.replace(".html", ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2)
        
        return str(filepath)
