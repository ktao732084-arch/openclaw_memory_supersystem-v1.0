#!/usr/bin/env python3
"""
计算到店人数：顺鼎手机号 → 客资数据 → 投放数据 → 按项目/天统计
"""
import requests
from collections import defaultdict
from datetime import datetime

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

TABLE_SHUNDING = "tblbIHSjDvlobJ4a"  # 顺鼎
TABLE_KEZI = "tblYgY0c0PRVqoqe"     # 客资
TABLE_PROMOTION = "tbl1n1PC1aooYdKk" # 投放

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

def get_all_records(token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    all_records = []
    page_token = None
    
    while True:
        payload = {"page_size": 500}
        if page_token:
            payload["page_token"] = page_token
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            records = result['data']['items']
            all_records.extend(records)
            
            if not result['data'].get('has_more'):
                break
            page_token = result['data'].get('page_token')
        else:
            print(f"❌ 获取数据失败: {result}")
            break
    
    return all_records

def normalize_phone(phone):
    """标准化手机号"""
    if not phone:
        return None
    phone_str = str(phone).strip()
    phone_str = phone_str.replace('+86', '').replace('-', '').replace(' ', '')
    phone_str = ''.join([c for c in phone_str if c.isdigit()])
    if len(phone_str) == 11 and phone_str.startswith('1'):
        return phone_str
    return None

def main():
    token = get_token()
    print("="*80)
    print("📊 到店人数计算")
    print("="*80)
    
    # 1. 加载顺鼎数据（到店手机号）
    print("\n[1/4] 加载顺鼎数据...")
    shunding_records = get_all_records(token, TABLE_SHUNDING)
    shunding_phones = set()
    for r in shunding_records:
        phone = r['fields'].get('上门手机号')
        normalized = normalize_phone(phone)
        if normalized:
            shunding_phones.add(normalized)
    print(f"   ✓ 顺鼎到店手机号: {len(shunding_phones)} 个")
    
    # 2. 加载客资数据
    print("\n[2/4] 加载客资数据...")
    kezi_records = get_all_records(token, TABLE_KEZI)
    print(f"   ✓ 客资记录: {len(kezi_records)} 条")
    
    # 3. 匹配：顺鼎手机号 → 客资数据（到店客户）
    print("\n[3/4] 匹配到店客户...")
    arrival_customers = []  # (手机号, 单元ID前15位, 日期)
    for r in kezi_records:
        fields = r['fields']
        phone = fields.get('手机号')
        normalized = normalize_phone(phone)
        
        if normalized and normalized in shunding_phones:
            unit_id_15 = fields.get('单元ID前15位', '')
            date_ts = fields.get('日期')  # 毫秒时间戳
            
            date_str = None
            if date_ts:
                try:
                    dt = datetime.fromtimestamp(date_ts / 1000)
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            if unit_id_15 and date_str:
                arrival_customers.append({
                    'phone': normalized,
                    'unit_id_15': str(unit_id_15),
                    'date': date_str
                })
    
    print(f"   ✓ 匹配到店客户: {len(arrival_customers)} 条")
    if arrival_customers[:5]:
        print("   示例:")
        for c in arrival_customers[:5]:
            print(f"     {c['phone']} | {c['unit_id_15']} | {c['date']}")
    
    # 4. 加载投放数据，获取单元ID完整信息
    print("\n[4/4] 加载投放数据，关联单元信息...")
    promotion_records = get_all_records(token, TABLE_PROMOTION)
    print(f"   ✓ 投放记录: {len(promotion_records)} 条")
    
    # 构建单元ID映射：前15位 → 单元名称/账户名称
    unit_mapping = {}
    for r in promotion_records:
        fields = r['fields']
        unit_id = fields.get('单元ID', '')
        unit_name = fields.get('单元名称', '')
        account_name = fields.get('文本', '')
        
        if unit_id:
            unit_id_str = str(unit_id)
            unit_id_15 = unit_id_str[:15]
            unit_mapping[unit_id_15] = {
                'unit_name': unit_name,
                'account_name': account_name,
                'unit_id_full': unit_id_str
            }
    
    # 5. 统计：按(日期, 单元ID前15位, 手机号)去重后统计
    print("\n" + "="*80)
    print("📈 统计结果")
    print("="*80)
    
    # key: (date, unit_id_15), value: set(phones)
    daily_unit_arrivals = defaultdict(set)
    
    for customer in arrival_customers:
        key = (customer['date'], customer['unit_id_15'])
        daily_unit_arrivals[key].add(customer['phone'])
    
    # 输出结果
    print(f"\n{'日期':<12} {'账户':<30} {'单元':<30} {'到店人数':<8}")
    print("-" * 90)
    
    total_arrivals = 0
    for (date, unit_id_15), phones in sorted(daily_unit_arrivals.items()):
        unit_info = unit_mapping.get(unit_id_15, {})
        account_name = unit_info.get('account_name', '未知账户')
        unit_name = unit_info.get('unit_name', '未知单元')
        count = len(phones)
        total_arrivals += count
        
        print(f"{date:<12} {account_name[:28]:<30} {unit_name[:28]:<30} {count:<8}")
    
    print("-" * 90)
    print(f"{'总计':<12} {'':<30} {'':<30} {total_arrivals:<8}")
    
    # 详细统计（按天）
    print("\n" + "="*80)
    print("📅 按天汇总")
    print("="*80)
    daily_total = defaultdict(int)
    for (date, _), phones in daily_unit_arrivals.items():
        daily_total[date] += len(phones)
    
    for date in sorted(daily_total.keys()):
        print(f"  {date}: {daily_total[date]} 人")

if __name__ == "__main__":
    main()
