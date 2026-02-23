#!/usr/bin/env python3
"""直接查看巨量API返回的原始数据"""

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

# 账户ID映射
ACCOUNT_IDS = {
    "郑州天后医疗美容医院有限公司-XL": "1768837915434004582",
    "DX-郑州天后医疗美容医院": "1760037709363585025",
    "本地推-ka-郑州天后医疗美容医院有限公司": "1751193180199317570",
    "菲象_郑州天后_10": "1835880409219083",
    "菲象_郑州天后_27": "1768839983739707398",
    "菲象_郑州天后_新": "1776106617313198081",
    "郑州天后医疗美容-智慧本地推-1": "1833214809353388034",
}

def get_raw_data(account_id, date):
    """获取原始数据"""
    token = get_valid_token()
    
    url = "https://api.oceanengine.com/open_api/v3.0/report/promotion/get/"
    
    # 转换日期格式
    dt = datetime.strptime(date, "%Y-%m-%d")
    start_date = dt.strftime("%Y-%m-%d")
    end_date = dt.strftime("%Y-%m-%d")
    
    params = {
        "advertiser_id": account_id,
        "start_date": start_date,
        "end_date": end_date,
        "metrics": "stat_cost,convert_cnt,convert_cost,impression,cnt,click,ctr,pc_cost_pc_show,pc_cost_pc_click,package_name,game_package_name,app_name",
        "dimensions": "promotion_id,promotion_name",
        "order_type": "desc",
        "order_field": "stat_cost",
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
    
    for account_name, account_id in ACCOUNT_IDS.items():
        print(f"\n🔍 账户: {account_name} (ID: {account_id})")
        print("-" * 80)
        
        raw_data = get_raw_data(account_id, yesterday)
        
        if raw_data:
            print(f"✅ API响应: {json.dumps(raw_data, indent=2, ensure_ascii=False)}")
            
            # 提取数据列表
            data_list = raw_data.get("data", {}).get("list", [])
            
            if data_list:
                print(f"\n📊 找到 {len(data_list)} 条数据:")
                for i, item in enumerate(data_list):
                    print(f"\n  记录 {i+1}:")
                    print(f"    单元ID: {item.get('promotion_id')}")
                    print(f"    单元名称: {item.get('promotion_name')}")
                    print(f"    消耗(stat_cost): {item.get('stat_cost')}")
                    print(f"    转化数(convert_cnt): {item.get('convert_cnt')}")
                    print(f"    转化成本(convert_cost): {item.get('convert_cost')}")
                    print(f"    完整数据: {json.dumps(item, indent=6, ensure_ascii=False)}")
            else:
                print("⚠️  无数据")
        else:
            print("❌ 获取数据失败")

if __name__ == "__main__":
    main()
