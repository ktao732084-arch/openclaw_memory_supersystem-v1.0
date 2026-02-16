#!/usr/bin/env python3
"""
获取今天的数据并上传到飞书
"""
import requests
import json
from datetime import datetime
from urllib.parse import urlencode

# 巨量引擎配置
JULIANG_ACCESS_TOKEN = "REDACTED"
LOCAL_ACCOUNT_ID = 1835880409219083

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    
    # 检查响应
    if resp.status_code != 200:
        print(f"❌ 飞书token获取失败: HTTP {resp.status_code}")
        print(f"响应: {resp.text}")
        return None
    
    try:
        data = resp.json()
        if data.get('code') == 0:
            return data.get('tenant_access_token')
        else:
            print(f"❌ 飞书token获取失败: {data.get('msg')}")
            return None
    except Exception as e:
        print(f"❌ 解析响应失败: {e}")
        print(f"响应内容: {resp.text[:200]}")
        return None

def get_juliang_data(date_str):
    """获取巨量本地推数据"""
    print(f"📊 获取巨量数据 ({date_str})...")
    
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": date_str,
        "end_date": date_str,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
        "page": 1,
        "page_size": 100
    }
    
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    
    headers = {"Access-Token": JULIANG_ACCESS_TOKEN}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            print(f"✓ 获取到 {len(promotion_list)} 条数据\n")
            
            # 显示数据详情
            if promotion_list:
                print("数据详情:")
                total_cost = 0
                for i, item in enumerate(promotion_list, 1):
                    cost = item.get('stat_cost', 0)
                    convert = item.get('convert_cnt', 0)
                    total_cost += cost
                    print(f"  {i}. {item.get('promotion_name', '未知')}")
                    print(f"     消耗: {cost:.2f}, 转化: {convert}")
                print(f"\n总消耗: {total_cost:.2f} 元\n")
            
            return promotion_list
        else:
            print(f"❌ 获取失败: {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []

def upload_to_feishu(data_list, token):
    """上传数据到飞书"""
    if not data_list:
        print("⚠️  没有数据需要上传")
        return
    
    print(f"📤 同步 {len(data_list)} 条数据到飞书...")
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    records = []
    for item in data_list:
        cost = item.get('stat_cost', 0)
        convert = item.get('convert_cnt', 0)
        convert_cost = round(cost / convert, 2) if convert > 0 else 0
        
        record = {
            "fields": {
                "时间": item.get('stat_time_day', ''),
                "单元ID": str(item.get('promotion_id', '')),
                "单元名称": item.get('promotion_name', ''),
                "消耗(元)": str(cost),
                "转化数": str(convert),
                "转化成本(元)": str(convert_cost),
                "团购线索数": str(item.get('clue_pay_order_cnt', 0))
            }
        }
        records.append(record)
    
    # 分批上传（每批最多500条）
    batch_size = 500
    success_count = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                success_count += len(batch)
                print(f"✓ 第 {i//batch_size + 1} 批写入成功: {len(batch)} 条")
            else:
                print(f"❌ 第 {i//batch_size + 1} 批写入失败: {result.get('msg')}")
        except Exception as e:
            print(f"❌ 第 {i//batch_size + 1} 批异常: {e}")
    
    print(f"\n✅ 同步完成！成功写入 {success_count}/{len(records)} 条")

if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    
    print("="*60)
    print("抖音来客 - 今日数据同步")
    print("="*60)
    print(f"日期: {today}")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 获取数据
    data = get_juliang_data(today)
    
    if data:
        # 获取飞书token
        token = get_feishu_token()
        
        # 上传到飞书
        upload_to_feishu(data, token)
    else:
        print("⚠️  今天暂无数据")
    
    print("\n" + "="*60)
    print("任务完成")
    print("="*60)
