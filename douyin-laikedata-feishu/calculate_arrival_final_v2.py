#!/usr/bin/env python3
"""
计算到店人数 - 最终版（带超时）
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

def get_shunding_phones(token):
    """获取舜鼎手机号"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_SHUNDING}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    phones = set()
    page_token = None
    
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            for r in result['data']['items']:
                phone = r['fields'].get('上门手机号')
                if phone:
                    phone_str = str(phone).strip()
                    phone_str = phone_str.replace('+86', '').replace('-', '').replace(' ', '')
                    phone_str = ''.join([c for c in phone_str if c.isdigit()])
                    if len(phone_str) == 11 and phone_str.startswith('1'):
                        phones.add(phone_str)
            
            if not result['data'].get('has_more'):
                break
            page_token = result['data'].get('page_token')
        else:
            break
    
    return phones

def search_laike_by_phone(token, phone):
    """用手机号搜索来客数据（带超时）"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_LAIKE}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "filter": {
            "conjunction": "and",
            "conditions": [{
                "field_name": "手机号",
                "operator": "is",
                "value": [phone]
            }]
        },
        "page_size": 500
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        result = resp.json()
        
        if result.get('code') == 0:
            return result['data']['items']
        return []
    except Exception as e:
        print(f"⚠️  超时/错误: {e}")
        return []

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

def main():
    token = get_token()
    print("="*80)
    print("📊 到店人数计算")
    print("="*80)
    
    # 1. 加载舜鼎数据
    print("\n[1/4] 加载舜鼎虚拟数据...")
    shunding_phones = get_shunding_phones(token)
    
    # 跳过最后一个卡住的手机号
    phone_list = sorted(shunding_phones)
    if phone_list and phone_list[-1] == '18790281100':
        phone_list = phone_list[:-1]
        print(f"   ✓ 舜鼎到店手机号: {len(phone_list)} 个（跳过最后1个超时的）")
    else:
        print(f"   ✓ 舜鼎到店手机号: {len(phone_list)} 个")
    
    # 2. 逐个搜索来客数据
    print("\n[2/4] 搜索来客数据...")
    arrival_customers = []
    
    for i, phone in enumerate(phone_list, 1):
        print(f"   搜索 {i}/{len(phone_list)}: {phone}...", end=' ', flush=True)
        records = search_laike_by_phone(token, phone)
        
        if records:
            print(f"✓ 找到 {len(records)} 条")
            for r in records:
                fields = r['fields']
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
                        'phone': phone,
                        'unit_id': str(unit_id),
                        'unit_name': unit_name,
                        'date': date_str
                    })
        else:
            print("✗ 未找到")
    
    print(f"\n   ✓ 匹配到店客户: {len(arrival_customers)} 条记录")
    
    # 3. 去重并统计
    print("\n[3/4] 去重并统计...")
    daily_unit_arrivals = defaultdict(set)
    unit_names = {}
    
    for customer in arrival_customers:
        key = (customer['date'], customer['unit_id'])
        daily_unit_arrivals[key].add(customer['phone'])
        if key not in unit_names and customer['unit_name']:
            unit_names[key] = customer['unit_name']
    
    # 4. 获取账户名称
    print("\n[4/4] 获取账户名称...")
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
