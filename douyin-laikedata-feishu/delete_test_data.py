#!/usr/bin/env python3
"""
删除测试数据
"""

import requests

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=5)
    return response.json()['tenant_access_token']

def get_test_records():
    """获取所有测试记录"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    test_records = []
    page_token = None
    
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()
        
        for record in result['data']['items']:
            account = record['fields'].get('文本', '')
            # 查找包含【测试】的记录
            if '【测试】' in account or '测试' in record['fields'].get('单元名称', ''):
                test_records.append({
                    'record_id': record['record_id'],
                    'account': account,
                    'unit_name': record['fields'].get('单元名称', ''),
                    'date': record['fields'].get('时间', '')
                })
        
        if not result['data'].get('has_more'):
            break
        page_token = result['data'].get('page_token')
    
    return test_records

def delete_records(record_ids):
    """批量删除记录"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {"records": record_ids}
    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        return True
    else:
        print(f"❌ 删除失败: {result}")
        return False

def delete_test_views():
    """删除测试视图"""
    token = get_token()
    
    # 获取所有视图
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    views = response.json()['data']['items']
    
    deleted_count = 0
    for view in views:
        view_name = view['view_name']
        if '【测试】' in view_name:
            view_id = view['view_id']
            # 删除视图
            delete_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views/{view_id}"
            response = requests.delete(delete_url, headers=headers, timeout=10)
            if response.json().get('code') == 0:
                print(f"✅ 已删除视图: {view_name}")
                deleted_count += 1
            else:
                print(f"❌ 删除视图失败: {view_name}")
    
    return deleted_count

def main():
    print("=" * 80)
    print("删除测试数据")
    print("=" * 80)
    
    print("\n步骤1: 查找测试记录...")
    test_records = get_test_records()
    
    if not test_records:
        print("  ✅ 没有找到测试记录")
    else:
        print(f"  找到 {len(test_records)} 条测试记录:")
        for i, record in enumerate(test_records[:10], 1):
            print(f"    [{i}] {record['account']} - {record['unit_name']} - {record['date']}")
        if len(test_records) > 10:
            print(f"    ... 还有 {len(test_records) - 10} 条")
        
        print("\n步骤2: 删除测试记录...")
        record_ids = [r['record_id'] for r in test_records]
        
        # 批量删除（每次最多500条）
        batch_size = 500
        deleted_count = 0
        for i in range(0, len(record_ids), batch_size):
            batch = record_ids[i:i+batch_size]
            if delete_records(batch):
                deleted_count += len(batch)
                print(f"  ✅ 已删除 {len(batch)} 条记录")
        
        print(f"\n  总共删除: {deleted_count} 条记录")
    
    print("\n步骤3: 删除测试视图...")
    deleted_views = delete_test_views()
    print(f"  总共删除: {deleted_views} 个视图")
    
    print("\n" + "=" * 80)
    print("✅ 清理完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
