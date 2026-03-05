"""完整测试大坝异常问答接口，获取完整回复"""
import requests
import json

# 1. 获取token
print("=== 1. SSO登录 ===")
login_resp = requests.post('http://localhost:5050/api/auth/sso-login', json={
    'userName': 'TEST_ADMIN',
    'fullName': '测试管理员',
    'token': 'test_token',
    'userId': 'TEST_ADMIN',
    'sn': 'TEST_ADMIN',
    'roles': ['开发用户']  # 管理员角色
})
print(f"登录状态码: {login_resp.status_code}")
login_data = login_resp.json()
token = login_data['access_token']
print(f"用户: {login_data['username']}, 角色: {login_data['role']}")

# 2. 直接传递异常数据进行问答
print("\n=== 2. 大坝异常问答测试 ===")
exception_data = [
    {
        'pointName': 'LA14X',
        'instrumentName': '水平位移',
        'area': '二江电站',
        'acomment': '轻微异常',
        'score': 8.7,
        'v': 0.922,
        'locationTypeName': '厂房坝段-机组5'
    },
    {
        'pointName': '9M21#',
        'instrumentName': '垂直位移',
        'area': '大江电站',
        'acomment': '未找到对应的指标数据',
        'score': 5,
        'v': -9.4,
        'locationTypeName': '厂房坝段-机组15'
    },
    {
        'pointName': 'LA22Y',
        'instrumentName': '水平位移',
        'area': '右岸重力坝',
        'acomment': '轻微异常',
        'score': 8.5,
        'v': 1.2,
        'locationTypeName': '坝顶'
    }
]

headers = {'Authorization': f'Bearer {token}'}
resp = requests.post(
    'http://localhost:5050/api/chat/dam-exception',
    json={
        'query': '请分析这些异常测点，说明可能的原因，并给出修复建议',
        'exception_data': exception_data,
        'include_repair_suggestions': True
    },
    headers=headers,
    stream=True
)

print(f"问答状态码: {resp.status_code}")
print("\n=== 系统回复 ===\n")

full_response = ""
for line in resp.iter_lines():
    if line:
        try:
            data = json.loads(line)
            status = data.get('status', '')
            response_text = data.get('response', '')
            message = data.get('message', '')
            
            if status in ['fetching_data', 'using_provided_data', 'parsing_data', 'reasoning', 'retrieving', 'generating']:
                print(f"[{status}] {message}")
            elif status == 'loading' and response_text:
                full_response += response_text
                print(response_text, end='', flush=True)
            elif status == 'finished':
                print(f"\n\n--- 回复完成 ---")
                print(f"耗时: {data.get('time_cost', 0):.2f}秒")
                if data.get('exception_stats'):
                    stats = data['exception_stats']
                    print(f"异常测点数: {stats.get('total_count', 0)}")
            elif status == 'error':
                print(f"\n[错误] {message}")
        except json.JSONDecodeError:
            continue

print("\n\n=== 完整回复 ===")
print(full_response if full_response else "(无回复内容)")
