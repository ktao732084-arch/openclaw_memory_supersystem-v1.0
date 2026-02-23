#!/usr/bin/env python3
"""
测试新token的客资接口权限
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
ADVERTISER_ID = 1769665409798152

def test_clue_api():
    """测试客资接口"""
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_time = f"{yesterday} 00:00:00"
    end_time = f"{yesterday} 23:59:59"
    
    url = "https://api.oceanengine.com/open_api/2/tools/clue/get/"
    
    print(f"📊 测试客资接口")
    print(f"   日期: {yesterday}")
    print(f"   广告主ID: {ADVERTISER_ID}")
    print()
    
    # 使用Header传token
    params = {
        "advertiser_id": ADVERTISER_ID,
        "start_time": start_time,
        "end_time": end_time,
        "page": 1,
        "page_size": 10
    }
    
    headers = {"Access-Token": ACCESS_TOKEN}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        result = resp.json()
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print()
        
        if result.get('code') == 0:
            data = result.get('data', {})
            clues = data.get('list', [])
            
            print("=" * 60)
            print(f"✅ 成功！获取到 {len(clues)} 条客资数据")
            print("=" * 60)
            
            if clues:
                print("\n客资数据示例（第1条）:")
                print(json.dumps(clues[0], ensure_ascii=False, indent=2))
                
                print("\n关键字段:")
                first = clues[0]
                print(f"  - 客资ID: {first.get('clue_id')}")
                print(f"  - 广告ID (ad_id): {first.get('ad_id')}")
                print(f"  - 计划ID (campaign_id): {first.get('campaign_id')}")
                print(f"  - 创建时间: {first.get('create_time')}")
                print(f"  - 电话: {first.get('telephone', '无')}")
                print(f"  - 客资类型: {first.get('clue_source')}")
        else:
            print(f"❌ 失败: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_clue_api()
