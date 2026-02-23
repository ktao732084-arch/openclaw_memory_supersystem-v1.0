#!/usr/bin/env python3
"""查看历史数据，确认之前是不是有非0的消耗"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载配置
load_dotenv()

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载token_manager
import sys
sys.path.insert(0, BASE_DIR)
from token_manager import get_valid_token

# 有数据的账户
ACTIVE_ACCOUNTS = {
    1835880409219083: "郑州天后医疗美容医院有限公司-XL",
}

def get_raw_data(account_id, date):
    """获取原始数据"""
    token = get_valid_token()
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/"
    
    params = {
        "local_account_id": account_id,
        "start_date": date,
        "end_date": date,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
        "page": 1,
        "page_size": 100
    }
    
    headers = {"Access-Token": token}
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        return None
    
    return response.json()

def main():
    # 看看过去7天的数据
    print("📅 检查过去7天的数据")
    print("=" * 80)
    
    account_id = 1835880409219083
    account_name = "郑州天后医疗美容医院有限公司-XL"
    
    for i in range(7, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"\n🔍 {date}")
        print("-" * 80)
        
        raw_data = get_raw_data(account_id, date)
        
        if raw_data:
            data_list = raw_data.get("data", {}).get("promotion_list", [])
            
            if data_list:
                total_cost = sum(item.get('stat_cost', 0) for item in data_list)
                total_show = sum(item.get('show_cnt', 0) for item in data_list)
                total_click = sum(item.get('click_cnt', 0) for item in data_list)
                total_convert = sum(item.get('convert_cnt', 0) for item in data_list)
                
                print(f"  记录数: {len(data_list)}")
                print(f"  总消耗: {total_cost}")
                print(f"  总展示: {total_show}")
                print(f"  总点击: {total_click}")
                print(f"  总转化: {total_convert}")
                
                if total_cost > 0:
                    print(f"  ✅ 有消耗数据！")
                    for item in data_list:
                        if item.get('stat_cost', 0) > 0:
                            print(f"    - {item.get('promotion_name')}: {item.get('stat_cost')}")
            else:
                print("  ⚠️  无数据")
        else:
            print("  ❌ 获取数据失败")

if __name__ == "__main__":
    main()
