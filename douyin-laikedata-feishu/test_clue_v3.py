#!/usr/bin/env python3
"""
测试巨量引擎的线索接口（v3.0）
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
ADVERTISER_ID = 1769665409798152

def test_clue_endpoints():
    """测试多个可能的线索接口"""
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📊 测试巨量引擎线索接口")
    print(f"   日期: {yesterday}")
    print(f"   广告主ID: {ADVERTISER_ID}")
    print()
    
    # 测试的接口列表
    endpoints = [
        # v3.0 线索通API
        {
            "name": "线索通API (v3.0)",
            "url": "https://ad.oceanengine.com/open_api/v3.0/clue/get/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_time": f"{yesterday} 00:00:00",
                "end_time": f"{yesterday} 23:59:59",
                "page": 1,
                "page_size": 10
            }
        },
        
        # 本地推专用线索接口
        {
            "name": "本地推线索 (v3.0)",
            "url": "https://ad.oceanengine.com/open_api/v3.0/local/push/leads/get/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_date": yesterday,
                "end_date": yesterday,
                "delivery_mode": "STANDARD",
                "page": 1,
                "page_size": 10
            }
        },
        
        # 本地推线索列表
        {
            "name": "本地推线索列表",
            "url": "https://ad.oceanengine.com/open_api/v3.0/local/leads/list/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_time": f"{yesterday} 00:00:00",
                "end_time": f"{yesterday} 23:59:59",
                "page": 1,
                "page_size": 10
            }
        },
        
        # 线索管理
        {
            "name": "线索管理",
            "url": "https://ad.oceanengine.com/open_api/v3.0/leads/get/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_time": f"{yesterday} 00:00:00",
                "end_time": f"{yesterday} 23:59:59",
                "page": 1,
                "page_size": 10
            }
        }
    ]
    
    headers = {"Access-Token": ACCESS_TOKEN}
    
    for endpoint in endpoints:
        print(f"🔍 测试: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            resp = requests.get(
                endpoint['url'],
                params=endpoint['params'],
                headers=headers,
                timeout=10
            )
            
            print(f"   状态码: {resp.status_code}")
            
            if resp.status_code == 404:
                print(f"   ❌ 接口不存在\n")
                continue
            
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                
                # 尝试找到数据列表
                clues = None
                if isinstance(data, dict):
                    for key in ['list', 'clues', 'leads', 'items']:
                        if key in data and data[key]:
                            clues = data[key]
                            break
                elif isinstance(data, list):
                    clues = data
                
                if clues:
                    print(f"   ✅ 成功！获取到 {len(clues)} 条线索")
                    print()
                    print("=" * 60)
                    print("第一条线索数据:")
                    print("=" * 60)
                    print(json.dumps(clues[0], ensure_ascii=False, indent=2))
                    print()
                    
                    # 检查关键字段
                    first = clues[0]
                    print("关键字段:")
                    print(f"  - clue_id: {first.get('clue_id', '无')}")
                    print(f"  - ad_id: {first.get('ad_id', '无')}")
                    print(f"  - campaign_id: {first.get('campaign_id', '无')}")
                    print(f"  - telephone: {first.get('telephone', '无')}")
                    print(f"  - create_time: {first.get('create_time', '无')}")
                    print(f"  - clue_source: {first.get('clue_source', '无')}")
                    print(f"  - intention_poi_name: {first.get('intention_poi_name', '无')}")
                    print()
                    
                    return endpoint['url'], clues
                else:
                    print(f"   ⚠️  返回成功但数据为空")
                    print(f"   完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            else:
                print(f"   ❌ 失败: {result.get('message')}")
                print(f"   错误码: {result.get('code')}")
        
        except Exception as e:
            print(f"   ❌ 异常: {str(e)}")
        
        print()
    
    return None, None

if __name__ == '__main__':
    success_url, clues = test_clue_endpoints()
    
    if success_url:
        print("=" * 60)
        print("✅ 找到可用的线索接口！")
        print("=" * 60)
        print(f"接口: {success_url}")
        print(f"数据量: {len(clues)} 条")
    else:
        print("=" * 60)
        print("❌ 没有找到可用的线索接口")
        print("=" * 60)
        print("建议:")
        print("1. 检查是否有线索数据（在巨量后台查看）")
        print("2. 可能需要单独申请抖音来客开放平台")
