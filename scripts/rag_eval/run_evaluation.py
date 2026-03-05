#!/usr/bin/env python3
"""
RAG 自动化测评工具 - 命令行入口

使用示例:
    # 从文档目录生成测试问题并评估
    uv run python scripts/rag_eval/run_evaluation.py \
        --docs-path /path/to/docs \
        --db-id your_kb_id

    # 使用已有测试集评估
    uv run python scripts/rag_eval/run_evaluation.py \
        --testset ./testset.jsonl \
        --db-id your_kb_id

    # 快速测试（仅使用 10 个样本）
    uv run python scripts/rag_eval/run_evaluation.py \
        --docs-path /path/to/docs \
        --db-id your_kb_id \
        --sample 10
"""

import argparse
import asyncio
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from scripts.rag_eval.rag_evaluator import run_full_evaluation


def parse_args():
    parser = argparse.ArgumentParser(
        description="RAG 自动化测评工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整评估
  %(prog)s --docs-path ./docs --db-id my_kb
  
  # 快速测试
  %(prog)s --docs-path ./docs --db-id my_kb --sample 10
  
  # 使用配置文件
  %(prog)s --config ./config.yaml
        """,
    )
    
    # 数据源
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--docs-path",
        type=str,
        help="文档目录路径（用于生成测试问题）",
    )
    source_group.add_argument(
        "--testset",
        type=str,
        help="已有的测试集文件路径 (.jsonl)",
    )
    
    # 知识库配置
    parser.add_argument(
        "--db-id",
        type=str,
        help="知识库 ID",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:5050",
        help="API 服务地址 (默认: http://localhost:5050)",
    )
    
    # LLM 配置
    parser.add_argument(
        "--llm-url",
        type=str,
        default="http://localhost:8000/v1",
        help="本地 LLM 服务地址 (默认: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="Qwen/Qwen3-32B",
        help="LLM 模型名称 (默认: Qwen/Qwen3-32B)",
    )
    
    # 评估参数
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="采样数量（用于快速测试）",
    )
    parser.add_argument(
        "--questions-per-doc",
        type=int,
        default=3,
        help="每个文档生成的问题数 (默认: 3)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="LLM API 并发数 (默认: 2，减少以避免限流)",
    )
    
    # 输出配置
    parser.add_argument(
        "--output",
        type=str,
        default="./eval_results",
        help="输出目录 (默认: ./eval_results)",
    )
    
    # 配置文件
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径 (YAML)",
    )
    
    # 认证
    parser.add_argument(
        "--username",
        type=str,
        help="API 用户名",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="API 密码",
    )
    
    return parser.parse_args()


async def main():
    args = parse_args()
    
    # 检查必要参数
    if not args.docs_path and not args.testset:
        if not args.config:
            print("❌ 错误: 必须指定 --docs-path 或 --testset 或 --config")
            sys.exit(1)
    
    if not args.db_id and not args.config:
        print("❌ 错误: 必须指定 --db-id 或在 --config 中配置")
        sys.exit(1)
    
    print("=" * 50)
    print("🔍 RAG 自动化测评工具")
    print("=" * 50)
    print(f"  文档路径: {args.docs_path or '(使用测试集)'}")
    print(f"  测试集: {args.testset or '(自动生成)'}")
    print(f"  知识库 ID: {args.db_id}")
    print(f"  LLM 服务: {args.llm_url}")
    print(f"  LLM 模型: {args.llm_model}")
    print(f"  采样数量: {args.sample or '全部'}")
    print(f"  输出目录: {args.output}")
    print("=" * 50)
    print()
    
    try:
        report_path = await run_full_evaluation(
            docs_path=args.docs_path,
            testset_path=args.testset,
            config_path=args.config,
            db_id=args.db_id,
            output_dir=args.output,
            sample_size=args.sample,
            questions_per_doc=args.questions_per_doc,
            llm_url=args.llm_url,
            llm_model=args.llm_model,
            username=args.username,
            password=args.password,
            concurrency=args.concurrency,
        )
        
        print()
        print("✅ 评估完成!")
        print(f"📄 报告: {report_path}")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 评估失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
