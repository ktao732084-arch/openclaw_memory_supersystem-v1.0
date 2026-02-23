#!/usr/bin/env python3
"""
更新表2「上门标记」字段
逻辑：表2的真实手机号在舜鼎虚拟数据中存在 → 标记为 "1"，否则清空
"""
import requests
import sys
import os
from datetime import datetime

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
TABLE2_ID = "tbl3Oyi6JYt3ZUIP"  # 来客抓取实际数据
TABLE3_ID = "tblbIHSjDvlobJ4a"  # 舜鼎虚拟数据

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

def fetch_all_records(token, table_id):
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records",
            headers=headers, params=params, timeout=30
        )
        data = resp.json()['data']
        records.extend(data['items'])
        if not data.get('has_more'):
            break
        page_token = data.get('page_token')
    return records

def main():
    log("开始更新上门标记...")

    token = get_feishu_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. 读取舜鼎所有手机号
    log("读取舜鼎手机号...")
    shunding_records = fetch_all_records(token, TABLE3_ID)
    shunding_phones = set()
    for item in shunding_records:
        phone = item['fields'].get('上门手机号', '').strip()
        if phone:
            shunding_phones.add(phone)
    log(f"舜鼎共 {len(shunding_phones)} 个唯一手机号")

    # 2. 读取表2所有记录
    log("读取表2记录...")
    all_records = fetch_all_records(token, TABLE2_ID)
    log(f"表2共 {len(all_records)} 条记录")

    # 3. 匹配
    update_mark = []
    clear_mark = []
    for item in all_records:
        real_phone = item['fields'].get('真实手机号', '')
        if isinstance(real_phone, list):
            real_phone = real_phone[0].get('text', '') if real_phone else ''
        real_phone = str(real_phone).strip()

        existing = item['fields'].get('上门标记', '')
        if isinstance(existing, list):
            existing = existing[0].get('text', '') if existing else ''

        if real_phone and real_phone in shunding_phones:
            if existing != '1':
                update_mark.append({"record_id": item['record_id'], "fields": {"上门标记": "1"}})
        else:
            if existing == '1':
                clear_mark.append({"record_id": item['record_id'], "fields": {"上门标记": ""}})

    log(f"需写入上门标记: {len(update_mark)} 条，需清除: {len(clear_mark)} 条")

    # 4. 批量写入
    for batch_list, label in [(update_mark, "写入上门标记"), (clear_mark, "清除错误标记")]:
        for i in range(0, len(batch_list), 500):
            batch = batch_list[i:i+500]
            resp = requests.post(
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE2_ID}/records/batch_update",
                headers=headers, json={"records": batch}, timeout=30
            )
            result = resp.json()
            if result.get('code') == 0:
                log(f"✅ {label} {len(batch)} 条成功")
            else:
                log(f"❌ {label} 失败: {result}")
                sys.exit(1)

    log("✅ 上门标记更新完成")

if __name__ == "__main__":
    main()
