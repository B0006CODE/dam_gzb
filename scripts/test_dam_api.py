"""测试大坝异常问答接口"""
import requests
import json

# 1. 获取token
print("=== 1. SSO登录测试 ===")
login_resp = requests.post('http://localhost:5050/api/auth/sso-login', json={
    'userName': 'TEST_USER',
    'fullName': '测试用户',
    'token': 'test_token',
    'userId': 'TEST_USER',
    'sn': 'TEST_USER',
    'roles': ['浏览用户']
})
print(f"登录状态码: {login_resp.status_code}")
login_data = login_resp.json()
token = login_data['access_token']
print(f"角色: {login_data['role']}")

# 2. 直接传递异常数据进行问答
print("\n=== 2. 大坝异常问答测试（直接传递数据） ===")
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
    }
]

headers = {'Authorization': f'Bearer {token}'}
resp = requests.post(
    'http://localhost:5050/api/chat/dam-exception',
    json={
        'query': '分析这些异常测点并给出修复建议',
        'exception_data': exception_data,
        'include_repair_suggestions': True
    },
    headers=headers,
    stream=True
)

print(f"问答状态码: {resp.status_code}")
print("响应流:")
for i, line in enumerate(resp.iter_lines()):
    if line:
        data = json.loads(line)
        status = data.get('status', '')
        message = data.get('message', '')
        response = data.get('response', '')
        
        print(f"  [{i}] status={status}")
        if message:
            print(f"       message={message}")
        if response:
            print(f"       response={response[:200]}...")
        
        if i >= 5:  # 只显示前几条
            print("  ... (更多响应省略)")
            break

print("\n=== 测试完成 ===")
