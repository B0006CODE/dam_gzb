"""命令行测试异常问答接口，并校验前端记录接口可见。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_FILE = ROOT_DIR / "异常接口信息示例.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="测试异常问答接口并读取问答记录")
    parser.add_argument("--base-url", default="http://localhost:5050", help="服务地址")
    parser.add_argument("--sample-file", default=str(DEFAULT_SAMPLE_FILE), help="异常数据样例文件")
    parser.add_argument("--question", default="请结合异常数据给出处置建议，并指出最需要优先排查的区域。", help="提问内容")
    parser.add_argument("--source-system", default="cli-test", help="来源系统标识")
    parser.add_argument("--records-limit", type=int, default=5, help="读取最近几条记录")
    return parser.parse_args()


def load_sample_payload(sample_file: str) -> object:
    with open(sample_file, encoding="utf-8") as f:
        return json.load(f)


def sso_login(base_url: str) -> str:
    response = requests.post(
        f"{base_url}/api/auth/sso-login",
        json={
            "userName": "CLI_TEST_USER",
            "fullName": "命令行测试用户",
            "token": "cli_test_token",
            "userId": "CLI_TEST_USER",
            "sn": "CLI_TEST_USER",
            "roles": ["浏览用户"],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def ask_exception_qa(base_url: str, sample_payload: object, question: str, source_system: str) -> dict:
    response = requests.post(
        f"{base_url}/api/system/dam-exception/qa",
        json={
            "question": question,
            "source_system": source_system,
            "exception_data": sample_payload,
            "include_repair_suggestions": True,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def fetch_records(base_url: str, token: str, limit: int) -> dict:
    response = requests.get(
        f"{base_url}/api/system/dam-exception/qa/records",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    args = parse_args()
    sample_payload = load_sample_payload(args.sample_file)

    print("=== 1. 调用异常问答接口 ===")
    qa_result = ask_exception_qa(args.base_url, sample_payload, args.question, args.source_system)
    print(f"record_id: {qa_result['record_id']}")
    print(f"asked_at: {qa_result['asked_at']}")
    print(f"source_system: {qa_result['source_system']}")
    print(f"is_fallback: {qa_result['is_fallback']}")
    print(f"异常测点数: {qa_result['stats'].get('total_count', 0)}")
    print("answer:")
    print(qa_result["answer"])

    print("\n=== 2. 登录并读取问答记录 ===")
    token = sso_login(args.base_url)
    records_result = fetch_records(args.base_url, token, args.records_limit)
    records = records_result.get("records", [])
    print(f"返回记录数: {records_result.get('count', 0)}")
    if not records:
        raise SystemExit("未读取到问答记录")

    latest = records[0]
    print("最新记录:")
    print(f"  record_id: {latest.get('record_id')}")
    print(f"  asked_at: {latest.get('asked_at')}")
    print(f"  source_system: {latest.get('source_system')}")
    print(f"  question: {latest.get('question')}")
    print(f"  answer: {latest.get('answer', '')[:120]}")

    if latest.get("record_id") != qa_result["record_id"]:
        raise SystemExit("最新记录不是本次命令行测试生成，前端刷新后可能看不到最新结果")

    print("\n=== 完成 ===")
    print("前端进入“异常问答”页面后点击“刷新”，应能看到这条最新记录。")


if __name__ == "__main__":
    main()
