#!/usr/bin/env python3
"""
通过项目列表反推所有账户ID
"""
import requests
import json
from collections import defaultdict

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
KNOWN_ACCOUNT_ID = 1835880409219083

print("="*60)
print("通过项目列表查找所有账户")
print("="*60 + "\n")

print(f"📋 获取账户 {KNOWN_ACCOUNT_ID} 的项目列表...\n")

url = "https://api.oceanengine.com/open_api/v3.0/local/project/list/"

headers = {
    "Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

all_projects = []
page = 1

while True:
    params = {
        "local_account_id": KNOWN_ACCOUNT_ID,
        "page": page,
        "page_size": 100
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        
        if data.get('code') != 0:
            print(f"❌ 错误: {data.get('message')}")
            break
        
        page_info = data.get('data', {}).get('page_info', {})
        projects = data.get('data', {}).get('project_list', [])
        
        if not projects:
            break
        
        all_projects.extend(projects)
        print(f"   第 {page} 页: {len(projects)} 个项目")
        
        if page >= page_info.get('total_page', 0):
            break
        
        page += 1
        
    except Exception as e:
        print(f"❌ 异常: {e}")
        break

print(f"\n✅ 共获取 {len(all_projects)} 个项目\n")

# 统计账户ID
account_ids = set()
for proj in all_projects:
    acc_id = proj.get('local_account_id')
    if acc_id:
        account_ids.add(acc_id)

print(f"📊 发现的账户ID数量: {len(account_ids)}\n")

if len(account_ids) > 1:
    print("🎉 找到多个账户！")
    for acc_id in sorted(account_ids):
        # 统计每个账户的项目数
        count = sum(1 for p in all_projects if p.get('local_account_id') == acc_id)
        print(f"   - {acc_id}: {count} 个项目")
else:
    print("⚠️  只找到一个账户ID")
    print(f"   - {list(account_ids)[0]}: {len(all_projects)} 个项目")
    print("\n💡 可能的原因：")
    print("   1. 确实只有一个本地推账户")
    print("   2. 其他账户需要单独查询")
    print("   3. 需要使用不同的API接口")

print("\n" + "="*60)
print("💡 建议：")
print("1. 如果你确定有70多个账户，可能需要：")
print("   - 在巨量后台找到'账户列表'页面")
print("   - 手动复制所有账户ID")
print("   - 或者提供账户列表的截图")
print("2. 或者这70多个是'项目'而不是'账户'？")
print("="*60)
