#!/usr/bin/env python3
"""
诊断客资匹配问题
检查为什么投放数据表中的客资数量是0
"""

import requests

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
TABLE_ID_DATA = "tbl1n1PC1aooYdKk"  # 投放数据表
TABLE_ID_SHEET2 = "tbl3Oyi6JYt3ZUIP"  # Sheet2
TABLE_ID_KEZI = "tblYgY0c0PRVqoqe"  # 客资数据

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=5)
    return response.json()['tenant_access_token']

def get_records(table_id, limit=10):
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": limit}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    return response.json()['data']['items']

print("=" * 80)
print("诊断客资匹配问题")
print("=" * 80)

# 1. 获取投放数据表的第一条记录
print("\n1. 投放数据表（第一条记录）:")
data_records = get_records(TABLE_ID_DATA, 1)
if data_records:
    record = data_records[0]
    fields = record['fields']
    print(f"   账户名称: {fields.get('文本', 'N/A')}")
    print(f"   日期: {fields.get('时间', 'N/A')}")
    print(f"   单元ID: {fields.get('单元ID', 'N/A')}")
    print(f"   单元名称: {fields.get('单元名称', 'N/A')}")
    
    unit_id = fields.get('单元ID', '')
    date = fields.get('时间', '')
    unit_id_prefix = unit_id[:15] if unit_id else ''
    
    print(f"\n   匹配条件:")
    print(f"   - 单元ID前15位: {unit_id_prefix}")
    print(f"   - 日期: {date}")

# 2. 在Sheet2中查找匹配的客资
print("\n2. Sheet2（前10条记录）:")
sheet2_records = get_records(TABLE_ID_SHEET2, 10)
matched_count = 0
for i, record in enumerate(sheet2_records, 1):
    fields = record['fields']
    phone = fields.get('手机号', 'N/A')
    unit_id_sheet2 = str(fields.get('单元ID', ''))
    create_time = fields.get('线索创建时间', 'N/A')
    
    # 提取日期部分
    date_sheet2 = create_time.split(' ')[0] if ' ' in create_time else create_time
    unit_id_prefix_sheet2 = unit_id_sheet2[:15] if unit_id_sheet2 else ''
    
    is_match = (unit_id_prefix_sheet2 == unit_id_prefix and date_sheet2 == date)
    
    print(f"   [{i}] 手机号: {phone}")
    print(f"       单元ID: {unit_id_sheet2}")
    print(f"       单元ID前15位: {unit_id_prefix_sheet2}")
    print(f"       线索创建时间: {create_time}")
    print(f"       日期: {date_sheet2}")
    print(f"       是否匹配: {'✅ 是' if is_match else '❌ 否'}")
    
    if is_match:
        matched_count += 1

print(f"\n   匹配数量: {matched_count}")

# 3. 在客资数据表中查找匹配的客资
print("\n3. 客资数据表（前10条记录）:")
kezi_records = get_records(TABLE_ID_KEZI, 10)
matched_count_kezi = 0
for i, record in enumerate(kezi_records, 1):
    fields = record['fields']
    phone = fields.get('手机号', 'N/A')
    unit_id_kezi = str(fields.get('单元ID前15位', ''))
    date_kezi = fields.get('日期', 'N/A')
    
    is_match = (unit_id_kezi == unit_id_prefix and date_kezi == date)
    
    print(f"   [{i}] 手机号: {phone}")
    print(f"       单元ID前15位: {unit_id_kezi}")
    print(f"       日期: {date_kezi}")
    print(f"       是否匹配: {'✅ 是' if is_match else '❌ 否'}")
    
    if is_match:
        matched_count_kezi += 1

print(f"\n   匹配数量: {matched_count_kezi}")

print("\n" + "=" * 80)
print("诊断结果:")
print("=" * 80)
print(f"Sheet2 匹配数量: {matched_count}")
print(f"客资数据表 匹配数量: {matched_count_kezi}")
print("\n建议:")
if matched_count > 0:
    print("✅ Sheet2 中有匹配的客资数据，建议使用 Sheet2")
elif matched_count_kezi > 0:
    print("✅ 客资数据表中有匹配的客资数据，当前公式应该正常工作")
else:
    print("❌ 两个表都没有匹配的客资数据，可能是:")
    print("   1. 单元ID格式不一致")
    print("   2. 日期格式不一致")
    print("   3. 数据确实不存在")
