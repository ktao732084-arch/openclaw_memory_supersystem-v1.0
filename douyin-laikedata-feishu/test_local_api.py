#!/usr/bin/env python3
"""
测试本地推账户维度数据接口
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = "REDACTED"
LOCAL_ACCOUNT_ID = 1835880409219083  # 本地推账户ID

def test_local_report():
    """测试本地推报表接口"""
    print("📊 测试本地推账户维度数据接口...\n")
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/account/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # 获取昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 参数（metrics 用逗号分隔的字符串）
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": "stat_cost,show_cnt,click_cnt,convert_cnt,form_cnt,phone_confirm_cnt,valid_leads_cnt"
    }
    
    print(f"请求参数:\n{json.dumps(params, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"状态码: {resp.status_code}")
        print(f"原始响应:\n{resp.text[:1000]}\n")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"解析后:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
                
                if data.get('code') == 0:
                    print("=" * 60)
                    print("✅ 成功获取本地推数据！")
                    print("=" * 60)
                    
                    # 显示数据结构
                    if data.get('data'):
                        print(f"\n数据结构:\n{json.dumps(data['data'], indent=2, ensure_ascii=False)[:500]}")
                    
                    return data
                else:
                    print(f"❌ 错误: {data.get('message')}")
                    print(f"   错误码: {data.get('code')}")
            except Exception as e:
                print(f"❌ JSON 解析失败: {e}")
        else:
            print(f"❌ HTTP 错误")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
    
    return None

if __name__ == '__main__':
    test_local_report()
