#!/usr/bin/env python3
"""
计算到店人数最终版
步骤：
1. 舜鼎虚拟数据 → 提取到店手机号
2. 来客抓取实际数据 → 匹配手机号，得到（手机号、单元ID、日期）
3. 按（日期、单元ID、手机号）去重
4. 按（日期、单元ID）统计到店人数
"""
import requests
from collections import defaultdict
from datetime import datetime

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

TABLE_SHUNDING = "tblbIHSjDvlobJ4a"  # 舜鼎虚拟数据
TABLE_LAIKE = "tbl3Oyi6JYt3ZUIP"      # 来客抓取实际数据
TABLE_PROMOTION = "tbl1n1PC1aooYdKk"  # 数据表（投放）

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

def get_all_records(token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    all_records = []
    page_token = None
    count = 0
    
    while True:
        payload = {"page_size": 500}
        if page_token:
            payload["page_token"] = page_token
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            records = result['data']['items']
            all_records.extend(records)
            count += len(records)
            print(f"   已获取 {count} 条...", end='\r', flush=True)
            
            if not result['data'].get('has_more'):
                break
            page_token = result['data'].get('page_token')
        else:
            print(f"\n❌ 获取数据失败: {result}")
            break
    
    print(f"   ✓ 完成，共 {len(all_records)} 条")
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

def extract_date(create_time_str):
    """从线索创建时间提取日期"""
    if not create_time_str:
        return None
    try:
        dt = datetime.strptime(create_time_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def main():
    token = get_token()
    print("="*80)
    print("📊 到店人数计算")
    print("="*80)
    
    # 1. 加载舜鼎数据（到店手机号）
    print("\n[1/4] 加载舜鼎虚拟数据...")
    shunding_records = get_all_records(token, TABLE_SHUNDING)
    shunding_phones = set()
    for r in shunding_records:
        phone = r['fields'].get('上门手机号')
        normalized = normalize_phone(phone)
        if normalized:
            shunding_phones.add(normalized)
    print(f"   ✓ 舜鼎到店手机号: {len(shunding_phones)} 个")
    
    # 2. 加载来客抓取实际数据
    print("\n[2/4] 加载来客抓取实际数据...")
    laike_records = get_all_records(token, TABLE_LAIKE)
    
    # 3. 匹配：舜鼎手机号 → 来客数据（到店客户）
    print("\n[3/4] 匹配到店客户...")
    arrival_customers = []  # (手机号, 单元ID, 日期)
    matched_count = 0
    
    for r in laike_records:
        fields = r['fields']
        phone = fields.get('手机号')
        normalized = normalize_phone(phone)
        
        if normalized and normalized in shunding_phones:
            unit_id = fields.get('单元ID', '')
            create_time = fields.get('线索创建时间', '')
            date_str = extract_date(create_time)
            unit_name = fields.get('单元名称', [''])[0] if fields.get('单元名称') else ''
            
            if unit_id and date_str:
                arrival_customers.append({
                    'phone': normalized,
                    'unit_id': str(unit_id),
                    'unit_name': unit_name,
                    'date': date_str
                })
                matched_count += 1
    
    print(f"   ✓ 匹配到店客户: {matched_count} 条记录")
    if arrival_customers[:5]:
        print("   示例:")
        for c in arrival_customers[:5]:
            print(f"     {c['date']} | {c['unit_id']} | {c['phone']} | {c['unit_name'][:15]}")
    
    # 4. 去重并统计
    print("\n[4/4] 去重并统计...")
    
    # key: (date, unit_id), value: set(phones)
    daily_unit_arrivals = defaultdict(set)
    # key: (date, unit_id), value: unit_name
    unit_names = {}
    
    for customer in arrival_customers:
        key = (customer['date'], customer['unit_id'])
        daily_unit_arrivals[key].add(customer['phone'])
        if key not in unit_names and customer['unit_name']:
            unit_names[key] = customer['unit_name']
    
    # 5. 加载投放数据，获取账户名称
    print("\n[额外] 加载投放数据，获取账户名称...")
    promotion_records = get_all_records(token, TABLE_PROMOTION)
    
    # 构建单元ID → 账户名称映射
    unit_account_map = {}
    for r in promotion_records:
        fields = r['fields']
        unit_id = fields.get('单元ID', '')
        account_name = fields.get('文本', '')
        if unit_id and account_name:
            unit_account_map[str(unit_id)] = account_name
    
    # 6. 输出结果
    print("\n" + "="*90)
    print(f"{'日期':<12} {'账户':<25} {'单元':<30} {'到店人数':<8}")
    print("-" * 90)
    
    total_arrivals = 0
    sorted_keys = sorted(daily_unit_arrivals.keys(), key=lambda x: (x[0], x[1]))
    
    for (date, unit_id) in sorted_keys:
        phones = daily_unit_arrivals[(date, unit_id)]
        count = len(phones)
        total_arrivals += count
        
        account_name = unit_account_map.get(unit_id, '未知账户')
        unit_name = unit_names.get((date, unit_id), '未知单元')
        
        print(f"{date:<12} {account_name[:23]:<25} {unit_name[:28]:<30} {count:<8}")
    
    print("-" * 90)
    print(f"{'总计':<12} {'':<25} {'':<30} {total_arrivals:<8}")
    
    # 7. 按天汇总
    print("\n" + "="*80)
    print("📅 按天汇总")
    print("="*80)
    daily_total = defaultdict(int)
    for (date, _), phones in daily_unit_arrivals.items():
        daily_total[date] += len(phones)
    
    for date in sorted(daily_total.keys()):
        print(f"  {date}: {daily_total[date]} 人")
    
    print("\n✅ 计算完成！")

if __name__ == "__main__":
    main()
