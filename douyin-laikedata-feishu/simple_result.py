#!/usr/bin/env python3
"""
最简单版本 - 直接输出结果
"""
import requests
from collections import defaultdict
from datetime import datetime

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

TABLE_LAIKE = "tbl3Oyi6JYt3ZUIP"

TARGET_PHONES = set([
    '13015518287', '13183009163', '13608490002', '13653973683',
    '13700529593', '13937380054', '15037856003', '15038654972',
    '15038984929', '15093347744', '15138665501', '15139131321',
    '15163102178', '15638278102', '15660079611', '15771672243',
    '15934358602', '15969592517', '16637857671', '17303829660',
    '17337885520', '17629365530', '17630340559', '17719947856',
    '18236920784', '18239988613', '18339807335', '18569941368',
    '18737175372'
])

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

def main():
    token = get_token()
    print("加载数据...")

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_LAIKE}/records"
    headers = {"Authorization": f"Bearer {token}"}

    all_records = []
    page_token = None

    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        result = resp.json()

        if result.get('code') == 0:
            all_records.extend(result['data']['items'])
            if not result['data'].get('has_more'):
                break
            page_token = result['data'].get('page_token')
        else:
            break

    print(f"共 {len(all_records)} 条数据\n")

    # 匹配并统计
    daily_unit_arrivals = defaultdict(set)
    unit_names = {}

    for r in all_records:
        phone = str(r['fields'].get('手机号', '')).strip()
        if phone in TARGET_PHONES:
            unit_id = str(r['fields'].get('单元ID', ''))
            create_time = r['fields'].get('线索创建时间', '')
            unit_name = r['fields'].get('单元名称', [''])[0] if r['fields'].get('单元名称') else ''

            date_str = None
            if create_time:
                try:
                    dt = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    pass

            if unit_id and date_str:
                key = (date_str, unit_id)
                daily_unit_arrivals[key].add(phone)
                if unit_name and key not in unit_names:
                    unit_names[key] = unit_name

    # 输出结果
    print("="*90)
    print(f"{'日期':<12} {'单元ID':<20} {'单元名称':<30} {'到店人数':<8}")
    print("-" * 90)

    total = 0
    for (date, unit_id) in sorted(daily_unit_arrivals.keys()):
        count = len(daily_unit_arrivals[(date, unit_id)])
        total += count
        unit_name = unit_names.get((date, unit_id), '')
        print(f"{date:<12} {unit_id:<20} {unit_name[:28]:<30} {count:<8}")

    print("-" * 90)
    print(f"{'总计':<12} {'':<20} {'':<30} {total:<8}")

    # 按天汇总
    print("\n按天汇总:")
    daily_total = defaultdict(int)
    for (date, _), phones in daily_unit_arrivals.items():
        daily_total[date] += len(phones)

    for date in sorted(daily_total.keys()):
        print(f"  {date}: {daily_total[date]} 人")

    print("\n✅ 完成")

if __name__ == "__main__":
    main()
