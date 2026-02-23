#!/usr/bin/env python3
"""
获取本地推单元维度报表数据
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
LOCAL_ACCOUNT_ID = 1835880409219083

def get_promotion_report():
    """获取单元维度报表"""
    print("📊 获取本地推单元维度报表...\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 构建参数（按照文档示例）
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt"]),  # JSON字符串
        "page": 1,
        "page_size": 100
    }
    
    # URL编码
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    
    headers = {
        "Access-Token": ACCESS_TOKEN
    }
    
    print(f"请求URL: {url[:150]}...\n")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"响应:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
            
            if data.get('code') == 0:
                print("=" * 60)
                print("✅ 成功获取单元数据！")
                print("=" * 60)
                
                promotion_list = data.get('data', {}).get('promotion_list', [])
                print(f"\n共获取 {len(promotion_list)} 个单元\n")
                
                if promotion_list:
                    print("数据预览（前3条）：")
                    for i, item in enumerate(promotion_list[:3], 1):
                        print(f"\n{i}. 单元ID: {item.get('promotion_id')}")
                        print(f"   单元名称: {item.get('promotion_name')}")
                        print(f"   项目ID: {item.get('project_id')}")
                        print(f"   项目名称: {item.get('project_name')}")
                        print(f"   消耗: {item.get('stat_cost')} 元")
                        print(f"   展示: {item.get('show_cnt')}")
                        print(f"   点击: {item.get('click_cnt')}")
                
                return data
            else:
                print(f"❌ 错误: {data.get('message')}")
                print(f"   错误码: {data.get('code')}")
        else:
            print(f"原始响应: {resp.text[:500]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
    
    return None

if __name__ == '__main__':
    get_promotion_report()
