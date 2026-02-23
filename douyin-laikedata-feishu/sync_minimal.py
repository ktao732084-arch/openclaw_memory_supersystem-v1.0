#!/usr/bin/env python3
"""
最简化的同步脚本 - 硬编码所有配置
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys

# 强制刷新输出
sys.stdout.reconfigure(line_buffering=True)

# 读取 token
with open('/root/.openclaw/workspace/douyin-laikedata-feishu/.token_cache.json', 'r') as f:
    token_data = json.load(f)
    ACCESS_TOKEN = token_data['access_token']

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 有数据的账户（硬编码）
ACTIVE_ACCOUNTS = {
    1835880409219083: "郑州天后医疗美容医院有限公司-XL",
    1844477765429641: "DX-郑州天后医疗美容医院",
    1844577767982090: "本地推-ka-郑州天后医疗美容医院有限公司",
    1847370973597827: "菲象_郑州天后_10",
    1848003626326092: "菲象_郑州天后_27",
    1848660180442243: "菲象_郑州天后_新",
    1856270852478087: "郑州天后医疗美容-智慧本地推-1",
}

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始同步")

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"同步日期: {yesterday}")

all_data = []

for account_id, account_name in ACTIVE_ACCOUNTS.items():
    params = {
        "local_account_id": account_id,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
        "page": 1,
        "page_size": 100
    }
    
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    headers = {"Access-Token": ACCESS_TOKEN}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            if promotion_list:
                for item in promotion_list:
                    item['local_account_id'] = account_id
                    item['account_name'] = account_name
                all_data.extend(promotion_list)
                print(f"  ✓ {account_name}: {len(promotion_list)}条")
    except Exception as e:
        print(f"  ❌ {account_name}: {e}")

print(f"\n获取到 {len(all_data)} 条数据")

if all_data:
    # 获取飞书token
    auth_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    auth_resp = requests.post(auth_url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}, timeout=10)
    feishu_token = auth_resp.json()['tenant_access_token']
    
    # 构建记录
    records = []
    for item in all_data:
        cost = item.get('stat_cost', 0)
        convert = item.get('convert_cnt', 0)
        
        record = {
            "fields": {
                "账户名称": item['account_name'],
                "时间": item.get('stat_time_day', ''),
                "单元ID": str(item.get('promotion_id', '')),
                "单元名称": item.get('promotion_name', ''),
                "消耗(元)": str(cost),
                "转化数": str(convert),
                "转化成本(元)": str(round(cost / convert, 2)) if convert > 0 else "0",
                "团购线索数": str(item.get('clue_pay_order_cnt', 0))
                # 客资数量、实际获客成本、客资转化率由飞书公式自动计算
            }
        }
        records.append(record)
    
    # 写入飞书
    write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    write_headers = {"Authorization": f"Bearer {feishu_token}", "Content-Type": "application/json"}
    payload = {"records": records}
    
    write_resp = requests.post(write_url, headers=write_headers, json=payload, timeout=30)
    result = write_resp.json()
    
    if result.get('code') == 0:
        print(f"✅ 写入成功: {len(records)}条")
    else:
        print(f"❌ 写入失败: {result}")
        sys.exit(1)
else:
    print("⚠️  没有数据")

# 自动创建新账户视图
print(f"\n检查是否有新账户需要创建视图...")
try:
    import subprocess
    result = subprocess.run(
        ["python3", "/root/.openclaw/workspace/douyin-laikedata-feishu/auto_create_views.py"],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode == 0:
        print("✅ 视图检查完成")
    else:
        print(f"⚠️  视图检查失败: {result.stderr}")
except Exception as e:
    print(f"⚠️  视图检查出错: {e}")

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成")
