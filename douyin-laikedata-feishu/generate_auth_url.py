#!/usr/bin/env python3
"""
生成巨量引擎授权链接
"""
from urllib.parse import urlencode

APP_ID = 1856818099350592

# 需要的权限范围
scopes = [
    1,    # 广告主信息
    2,    # 广告计划
    3,    # 广告组
    4,    # 广告创意
    14,   # 报表数据
    110,  # 本地推
]

params = {
    "app_id": APP_ID,
    "state": "your_state",
    "scope": str(scopes),
    "redirect_uri": "https://httpbin.org/get"  # 回调地址
}

auth_url = f"https://ad.oceanengine.com/openapi/audit/oauth.html?{urlencode(params)}"

print("="*60)
print("巨量引擎授权链接")
print("="*60)
print(f"\n{auth_url}\n")
print("="*60)
print("操作步骤：")
print("1. 复制上面的链接，在浏览器打开")
print("2. 登录并勾选所有权限（特别是广告管理、报表数据）")
print("3. 点击授权")
print("4. 复制回调地址中的 auth_code 参数")
print("5. 把完整的回调地址发给我")
print("="*60)
