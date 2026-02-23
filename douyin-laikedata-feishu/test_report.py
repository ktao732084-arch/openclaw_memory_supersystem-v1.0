#!/usr/bin/env python3
"""
测试巨量引擎报表 API
"""
import requests
import json
import time

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
ADVERTISER_ID = 1769665409798152

def test_report():
    """测试获取报表数据"""
    print("📊 测试获取本地推投放数据...\n")
    
    # 巨量引擎报表 API
    url = "https://api.oceanengine.com/open_api/2/report/custom/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # 获取昨天的数据
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    
    payload = {
        "advertiser_id": ADVERTISER_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "group_by": ["STAT_GROUP_BY_FIELD_ID"],  # 按广告计划分组
        "fields": [
            "ad_id",      # 单元ID
            "ad_name",    # 单元名称
            "status"      # 状态
        ]
    }
    
    print(f"请求参数:\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"状态码: {resp.status_code}")
        print(f"原始响应:\n{resp.text[:500]}\n")
        
        try:
            data = resp.json()
            print(f"解析后:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
        except:
            print("❌ JSON 解析失败，可能是 HTML 错误页面")
            return False
        
        if data.get('code') == 0:
            items = data.get('data', {}).get('list', [])
            print("=" * 50)
            print(f"✅ 成功获取 {len(items)} 条数据")
            print("=" * 50)
            
            if items:
                print("\n数据预览（前 3 条）：")
                for i, item in enumerate(items[:3], 1):
                    print(f"\n{i}. 单元ID: {item.get('dimensions', {}).get('ad_id')}")
                    print(f"   单元名称: {item.get('dimensions', {}).get('ad_name')}")
                    print(f"   状态: {item.get('metrics', {}).get('status')}")
            else:
                print("\n⚠️  没有数据（可能昨天没有投放）")
            
            return True
        else:
            print(f"❌ 获取失败: {data.get('message')}")
            print(f"   错误码: {data.get('code')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_report()
