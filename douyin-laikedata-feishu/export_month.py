#!/usr/bin/env python3
"""
导出月度数据到飞书
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import time

# 巨量引擎配置
JULIANG_ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
LOCAL_ACCOUNT_ID = 1835880409219083

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
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
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get('code') == 0:
            return data.get('tenant_access_token')
    return None

def get_juliang_data(start_date, end_date):
    """获取巨量本地推数据"""
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": start_date,
        "end_date": end_date,
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
            return data.get('data', {}).get('promotion_list', [])
        else:
            print(f"❌ 错误: {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []

def download_month_data(year, month):
    """下载整月数据"""
    print(f"📥 下载 {year}年{month}月 的数据...\n")
    
    # 计算月份的第一天和最后一天
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    all_data = []
    current_date = first_day
    
    while current_date <= last_day:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"   {date_str}...", end=" ", flush=True)
        
        data = get_juliang_data(date_str, date_str)
        
        if data:
            all_data.extend(data)
            print(f"✓ {len(data)} 条")
        else:
            print("✓ 0 条")
        
        current_date += timedelta(days=1)
        time.sleep(0.3)  # 避免请求过快
    
    return all_data

def analyze_data(data_list):
    """分析数据"""
    print(f"\n📊 数据统计:")
    print(f"   总记录数: {len(data_list)}")
    
    # 按日期分组
    by_date = {}
    for item in data_list:
        date = item.get('stat_time_day', '未知')
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(item)
    
    print(f"   有数据天数: {len(by_date)} 天")
    
    # 计算总计
    total_cost = sum(item.get('stat_cost', 0) for item in data_list)
    total_convert = sum(item.get('convert_cnt', 0) for item in data_list)
    total_clue = sum(item.get('clue_pay_order_cnt', 0) for item in data_list)
    
    print(f"   总消耗: {total_cost:.2f} 元")
    print(f"   总转化: {total_convert}")
    print(f"   总团购线索: {total_clue}")
    
    if total_convert > 0:
        avg_cost = total_cost / total_convert
        print(f"   平均转化成本: {avg_cost:.2f} 元")
    
    # 显示每日汇总
    print(f"\n📅 每日汇总:")
    for date in sorted(by_date.keys()):
        items = by_date[date]
        day_cost = sum(i.get('stat_cost', 0) for i in items)
        day_convert = sum(i.get('convert_cnt', 0) for i in items)
        print(f"   {date}: {len(items)} 条, 消耗 {day_cost:.2f}, 转化 {day_convert}")

def upload_to_feishu(data_list, token):
    """上传数据到飞书"""
    if not data_list:
        print("\n⚠️  没有数据需要上传")
        return
    
    print(f"\n📤 上传 {len(data_list)} 条数据到飞书...")
    
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
                print(f"   ✓ 第 {i//batch_size + 1} 批: {len(batch)} 条")
            else:
                print(f"   ❌ 第 {i//batch_size + 1} 批失败: {result.get('msg')}")
        except Exception as e:
            print(f"   ❌ 第 {i//batch_size + 1} 批异常: {e}")
    
    print(f"\n✅ 上传完成！成功 {success_count}/{len(records)} 条")

if __name__ == '__main__':
    import sys
    
    # 默认导出本月
    now = datetime.now()
    
    if len(sys.argv) == 3:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    else:
        year = now.year
        month = now.month
        print(f"💡 默认导出本月数据: {year}年{month}月")
        print(f"   提示: 可指定月份 python3 export_month.py 2026 1\n")
    
    print("="*60)
    print(f"导出月度数据: {year}年{month}月")
    print("="*60 + "\n")
    
    # 下载数据
    data = download_month_data(year, month)
    
    if data:
        # 分析数据
        analyze_data(data)
        
        # 获取飞书token
        print("\n🔑 获取飞书访问令牌...")
        token = get_feishu_token()
        
        if token:
            # 上传到飞书
            upload_to_feishu(data, token)
        else:
            print("❌ 无法获取飞书token")
    else:
        print("\n⚠️  本月暂无数据")
    
    print("\n" + "="*60)
    print("任务完成")
    print("="*60)
