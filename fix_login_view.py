# -*- coding: utf-8 -*-
"""Script to fix encoding issues in LoginView.vue"""

import os

file_path = r'd:\大坝最新项目\Yuxi-Know-main\web\src\views\LoginView.vue'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Dictionary of all replacements - broken Chinese to correct Chinese
replacements = {
    # Form validation messages
    '璇疯緭鍏ョ敤鎴稩D': '请输入用户ID',
    '鐢ㄦ埛ID鍙兘鍖呭惈瀛楁瘝銆佹暟瀛楀拰涓嬪垝绾?': '用户ID只能包含字母、数字和下划线\'',
    '鐢ㄦ埛ID闀垮害蹇呴』鍦?-20涓瓧绗︿箣闂?': '用户ID长度必须在3-20个字符之间\'',
    '璇疯緭鍏ュ瘑鐮?': '请输入密码\'',
    "璇风'璁ゅ瘑鐮?": "请确认密码\'",
    
    # Brand texts
    'AI 椹卞姩鐨勬櫤鑳芥按鍒╅棶绛斿钩鍙?': 'AI 驱动的智能水利问答平台\'',
    '澶фā鍨嬮┍鍔ㄧ殑鐭ヨ瘑搴撶鐞嗗伐鍏?': '大模型驱动的知识库管理工具\'',
    "缁撳悎鐭ヨ瘑搴撲笌鐭ヨ瘑鍥捐氨锛屾彁渚涙洿鍑嗙'銆佹洿鍏ㄩ潰鐨勫洖绛?": "结合知识库与知识图谱，提供更准确、更全面的回答\'",
    
    # Time format strings
    '绉抈': '秒`',
    '鍒?{remainingSeconds}': '分${remainingSeconds}',
    '灏忔椂': '小时',
    '澶?{hours}': '天${hours}',
    
    # Error messages
    "涓ゆ杈撳叆鐨勫瘑鐮佷笉涓€鑷?": "两次输入的密码不一致\'",
    '璐︽埛琚攣瀹氾紝璇风◢鍚庡啀璇?': '账户被锁定，请稍后再试\'',
    '鐧诲綍澶辫触锛岃妫€鏌ョ敤鎴峰悕鍜屽瘑鐮?': '登录失败，请检查用户名和密码\'',
    '鍒濆鍖栧け璐ワ紝璇烽噸璇?': '初始化失败，请重试\'',
    
    # Copyright
    '鐗堟潈鎵€鏈?': '版权所有\'',
}

# Apply all replacements
for old, new in replacements.items():
    content = content.replace(old, new)

# Write the fixed content back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('LoginView.vue fixed successfully!')
