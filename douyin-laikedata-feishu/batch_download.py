#!/usr/bin/env python3
"""
批量下载多天的数据
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import time

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
LOCAL_ACCOUNT_ID = 1835880409219083

def get_promotion_data(start_date, end_date):
    """获取指定日期范围的单元数据"""
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": start_date,
        "end_date": end_date,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps([
            "stat_cost",
            "show_cnt",
            "click_cnt",
            "convert_cnt",
            "clue_pay_order_cnt"
        ]),
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
            return data.get('data', {}).get('promotion_list', [])
        else:
            print(f"❌ 错误: {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []

def download_date_range(start_date_str, end_date_str):
    """下载日期范围内的所有数据"""
    print("="*60)
    print(f"批量下载: {start_date_str} ~ {end_date_str}")
    print("="*60 + "\n")
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    all_data = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"📥 {date_str}...", end=" ")
        
        data = get_promotion_data(date_str, date_str)
        
        if data:
            all_data.extend(data)
            print(f"✓ {len(data)} 条")
        else:
            print("✓ 0 条")
        
        current_date += timedelta(days=1)
        time.sleep(0.5)  # 避免请求过快
    
    print(f"\n📊 总计: {len(all_data)} 条数据")
    
    # 按日期分组统计
    by_date = {}
    for item in all_data:
        date = item.get('stat_time_day', '未知')
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(item)
    
    print(f"\n📅 日期分布:")
    for date in sorted(by_date.keys()):
        items = by_date[date]
        total_cost = sum(i.get('stat_cost', 0) for i in items)
        total_convert = sum(i.get('convert_cnt', 0) for i in items)
        print(f"   {date}: {len(items)} 条, 消耗 {total_cost:.2f}, 转化 {total_convert}")
    
    # 保存到文件
    filename = f"data_{start_date_str.replace('-', '')}_{end_date_str.replace('-', '')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 已保存到: {filename}")
    print("="*60)
    
    return all_data

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 3:
        # 命令行参数: python3 batch_download.py 2026-02-01 2026-02-11
        start = sys.argv[1]
        end = sys.argv[2]
    else:
        # 默认下载最近7天
        end = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        print(f"💡 使用默认日期范围: {start} ~ {end}")
        print(f"   提示: 可以指定日期 python3 batch_download.py 2026-02-01 2026-02-11\n")
    
    download_date_range(start, end)
