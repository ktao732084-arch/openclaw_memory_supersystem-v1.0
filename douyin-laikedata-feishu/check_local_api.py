#!/usr/bin/env python3
"""直接查看 local/report/promotion/get API 返回的原始数据"""

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
    1844477765429641: "DX-郑州天后医疗美容医院",
    1844577767982090: "本地推-ka-郑州天后医疗美容医院有限公司",
    1847370973597827: "菲象_郑州天后_10",
    1848003626326092: "菲象_郑州天后_27",
    1848660180442243: "菲象_郑州天后_新",
    1856270852478087: "郑州天后医疗美容-智慧本地推-1",
}

def get_raw_data(account_id, date):
    """获取原始数据（使用正确的 local API）"""
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
        print(f"❌ API请求失败: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def main():
    # 昨天
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"📅 检查日期: {yesterday}")
    print("=" * 80)
    
    for account_id, account_name in list(ACTIVE_ACCOUNTS.items())[:2]:  # 先看前2个
        print(f"\n🔍 账户: {account_name} (ID: {account_id})")
        print("-" * 80)
        
        raw_data = get_raw_data(account_id, yesterday)
        
        if raw_data:
            print(f"✅ API响应: {json.dumps(raw_data, indent=2, ensure_ascii=False)}")
            
            # 提取数据列表
            data_list = raw_data.get("data", {}).get("promotion_list", [])
            
            if data_list:
                print(f"\n📊 找到 {len(data_list)} 条数据:")
                for i, item in enumerate(data_list):
                    print(f"\n  记录 {i+1}:")
                    print(f"    单元ID: {item.get('promotion_id')}")
                    print(f"    单元名称: {item.get('promotion_name')}")
                    print(f"    stat_cost: {item.get('stat_cost')} (类型: {type(item.get('stat_cost'))})")
                    print(f"    show_cnt: {item.get('show_cnt')}")
                    print(f"    click_cnt: {item.get('click_cnt')}")
                    print(f"    convert_cnt: {item.get('convert_cnt')}")
                    print(f"    clue_pay_order_cnt: {item.get('clue_pay_order_cnt')}")
                    print(f"    完整数据: {json.dumps(item, indent=6, ensure_ascii=False)}")
            else:
                print("⚠️  无数据")
        else:
            print("❌ 获取数据失败")

if __name__ == "__main__":
    main()
