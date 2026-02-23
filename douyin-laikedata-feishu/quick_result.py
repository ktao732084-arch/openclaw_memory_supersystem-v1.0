#!/usr/bin/env python3
"""
快速出结果 - 基于前面已搜索到的数据
"""
import requests
from collections import defaultdict
from datetime import datetime

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

TABLE_LAIKE = "tbl3Oyi6JYt3ZUIP"      # 来客抓取实际数据
TABLE_PROMOTION = "tbl1n1PC1aooYdKk"  # 数据表（投放）

# 前面28个已确认匹配到的手机号
TARGET_PHONES = [
    '13015518287', '13183009163', '13608490002', '13653973683',
    '13700529593', '13937380054', '15037856003', '15038654972',
    '15038984929', '15093347744', '15138665501', '15139131321',
    '15163102178', '15638278102', '15660079611', '15771672243',
    '15934358602', '15969592517', '16637857671', '17303829660',
    '17337885520', '17629365530', '17630340559', '17719947856',
    '18236920784', '18239988613', '18339807335', '18569941368',
    '18737175372'
]

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

def get_all_laike_records(token):
    """快速获取所有来客数据（不filter，直接取前10000条）"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_LAIKE}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    all_records = []
    page_token = None
    count = 0
    
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            records = result['data']['items']
            all_records.extend(records)
            count += len(records)
            print(f"   已获取 {count} 条...", end='\r', flush=True)
            
            if not result['data'].get('has_more') or count >= 20000:
                break
            page_token = result['data'].get('page_token')
        else:
            break
    
    print(f"   ✓ 共获取 {len(all_records)} 条")
    return all_records

def get_unit_account_map(token):
    """获取单元ID→账户名称映射"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_PROMOTION}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    unit_map = {}
    page_token = None
    
    while True:
        payload = {"page_size": 500}
        if page_token:
            payload["page_token"] = page_token
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            for r in result['data']['items']:
                fields = r['fields']
                unit_id = fields.get('单元ID', '')
                account_name = fields.get('文本', '')
                if unit_id and account_name:
                    unit_map[str(unit_id)] = account_name
            
            if not result['data'].get('has_more'):
                break
            page_token = result['data'].get('page_token')
        else:
            break
    
    return unit_map

def normalize_phone(phone):
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
    print("📊 到店人数计算（快速版）")
    print("="*80)
    
    # 1. 加载来客数据
    print("\n[1/3] 加载来客数据...")
    laike_records = get_all_laike_records(token)
    
    # 2. 匹配目标手机号
    print("\n[2/3] 匹配到店客户...")
    target_set = set(TARGET_PHONES)
    arrival_customers = []
    
    for r in laike_records:
        fields = r['fields']
        phone = fields.get('手机号')
        normalized = normalize_phone(phone)
        
        if normalized and normalized in target_set:
            unit_id = fields.get('单元ID', '')
            create_time = fields.get('线索创建时间', '')
            unit_name = fields.get('单元名称', [''])[0] if fields.get('单元名称') else ''
            
            date_str = None
            if create_time:
                try:
                    dt = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            if unit_id and date_str:
                arrival_customers.append({
                    'phone': normalized,
                    'unit_id': str(unit_id),
                    'unit_name': unit_name,
                    'date': date_str
                })
    
    print(f"   ✓ 匹配到店客户: {len(arrival_customers)} 条记录")
    
    # 3. 去重并统计
    print("\n[3/3] 去重并统计...")
    daily_unit_arrivals = defaultdict(set)
    unit_names = {}
    
    for customer in arrival_customers:
        key = (customer['date'], customer['unit_id'])
        daily_unit_arrivals[key].add(customer['phone'])
        if key not in unit_names and customer['unit_name']:
            unit_names[key] = customer['unit_name']
    
    # 4. 获取账户名称
    print("\n获取账户名称...")
    unit_account_map = get_unit_account_map(token)
    
    # 5. 输出结果
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
    
    # 6. 按天汇总
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
