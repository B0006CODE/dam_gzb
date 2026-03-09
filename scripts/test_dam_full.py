"""完整打印异常问答结果，并验证记录接口中的最新一条。"""

from __future__ import annotations

import json
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT_DIR / "异常接口信息示例.json"
BASE_URL = "http://localhost:5050"


def load_sample_payload() -> object:
    with open(SAMPLE_FILE, encoding="utf-8") as f:
        return json.load(f)


def sso_login() -> str:
    response = requests.post(
        f"{BASE_URL}/api/auth/sso-login",
        json={
            "userName": "CLI_TEST_ADMIN",
            "fullName": "命令行测试管理员",
            "token": "cli_test_admin_token",
            "userId": "CLI_TEST_ADMIN",
            "sn": "CLI_TEST_ADMIN",
            "roles": ["开发用户"],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> None:
    sample_payload = load_sample_payload()

    print("=== 1. 提交异常问答 ===")
    qa_response = requests.post(
        f"{BASE_URL}/api/system/dam-exception/qa",
        json={
            "question": "请分析这些异常测点的风险等级、优先排查区域，并给出分阶段处置建议。",
            "source_system": "cli-full-test",
            "exception_data": sample_payload,
            "include_repair_suggestions": True,
        },
        timeout=120,
    )
    qa_response.raise_for_status()
    qa_result = qa_response.json()

    print(f"record_id: {qa_result['record_id']}")
    print(f"asked_at: {qa_result['asked_at']}")
    print(f"总异常测点: {qa_result['stats'].get('total_count', 0)}")
    print("\n=== 2. 完整回复 ===")
    print(qa_result["answer"])

    print("\n=== 3. 校验记录接口 ===")
    token = sso_login()
    records_response = requests.get(
        f"{BASE_URL}/api/system/dam-exception/qa/records",
        params={"limit": 3},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    records_response.raise_for_status()
    latest_record = records_response.json()["records"][0]

    print(f"latest_record_id: {latest_record.get('record_id')}")
    print(f"latest_question: {latest_record.get('question')}")
    print(f"latest_source_system: {latest_record.get('source_system')}")

    if latest_record.get("record_id") != qa_result["record_id"]:
        raise SystemExit("记录接口最新项不是本次测试结果")

    print("\n=== 完成 ===")
    print("前端异常问答页刷新后即可看到该问答记录。")


if __name__ == "__main__":
    main()
