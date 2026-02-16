#!/usr/bin/env python3
"""
全面测试巨量引擎客资相关API
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from token_manager import get_valid_token

LOCAL_ACCOUNT_ID = 1835880409219083
ADVERTISER_ID = 1769665409798152

def test_api(name, url, params, use_header_token=True):
    """统一的API测试函数"""
    print(f"🔍 测试: {name}")
    print(f"   URL: {url}")
    
    access_token = get_valid_token()
    
    try:
        if use_header_token:
            # v3.0 接口：Header传token
            headers = {"Access-Token": access_token}
            query_string = urlencode(params)
            full_url = f"{url}?{query_string}"
            response = requests.get(full_url, headers=headers, timeout=30)
        else:
            # v2 接口：参数传token
            params['access_token'] = access_token
            response = requests.get(url, params=params, timeout=30)
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 404:
            print(f"   ❌ 接口不存在")
            return None
        
        try:
            result = response.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                
                # 尝试找到数据列表
                data_list = None
                if isinstance(data, list):
                    data_list = data
                elif isinstance(data, dict):
                    for key in ['list', 'clues', 'clue_list', 'promotion_list', 'items']:
                        if key in data and data[key]:
                            data_list = data[key]
                            break
                
                if data_list:
                    print(f"   ✅ 成功！获取到 {len(data_list)} 条数据")
                    print(f"   数据示例:")
                    print(json.dumps(data_list[0], ensure_ascii=False, indent=6))
                    return data_list
                else:
                    print(f"   ⚠️  返回成功但数据为空")
                    print(f"   完整响应: {json.dumps(result, ensure_ascii=False, indent=6)}")
            else:
                print(f"   ❌ 失败: {result.get('message', '未知错误')}")
                print(f"   错误码: {result.get('code')}")
        except:
            print(f"   ⚠️  无法解析JSON")
            print(f"   原始响应: {response.text[:300]}")
    
    except Exception as e:
        print(f"   ❌ 异常: {str(e)}")
    
    print()
    return None

def main():
    """测试所有可能的客资接口"""
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_time = f"{yesterday} 00:00:00"
    today_time = f"{yesterday} 23:59:59"
    
    print(f"📊 测试客资数据接口")
    print(f"   日期: {yesterday}")
    print(f"   本地推账户ID: {LOCAL_ACCOUNT_ID}")
    print(f"   广告主ID: {ADVERTISER_ID}")
    print()
    
    # 测试列表
    tests = [
        # 1. 通用客资接口（v2）
        {
            "name": "客资列表（v2通用）",
            "url": "https://api.oceanengine.com/open_api/2/tools/clue/get/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_time": yesterday_time,
                "end_time": today_time,
                "page": 1,
                "page_size": 100
            },
            "use_header": False
        },
        
        # 2. 客资详情接口（v2）
        {
            "name": "客资详情（v2）",
            "url": "https://api.oceanengine.com/open_api/2/tools/clue/form/get/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_time": yesterday_time,
                "end_time": today_time,
                "page": 1,
                "page_size": 100
            },
            "use_header": False
        },
        
        # 3. 本地推客资报表（v3）
        {
            "name": "本地推客资报表（v3）",
            "url": "https://api.oceanengine.com/open_api/v3.0/local/report/clue/get/",
            "params": {
                "local_account_id": LOCAL_ACCOUNT_ID,
                "start_date": yesterday,
                "end_date": yesterday,
                "time_granularity": "TIME_GRANULARITY_DAILY",
                "page": 1,
                "page_size": 100
            },
            "use_header": True
        },
        
        # 4. 本地推客资列表（v3）
        {
            "name": "本地推客资列表（v3）",
            "url": "https://api.oceanengine.com/open_api/v3.0/local/clue/list/",
            "params": {
                "local_account_id": LOCAL_ACCOUNT_ID,
                "start_time": yesterday_time,
                "end_time": today_time,
                "page": 1,
                "page_size": 100
            },
            "use_header": True
        },
        
        # 5. 本地推客资详情（v3）
        {
            "name": "本地推客资详情（v3）",
            "url": "https://api.oceanengine.com/open_api/v3.0/local/clue/detail/",
            "params": {
                "local_account_id": LOCAL_ACCOUNT_ID,
                "start_time": yesterday_time,
                "end_time": today_time,
                "page": 1,
                "page_size": 100
            },
            "use_header": True
        },
        
        # 6. 线索管理接口（v1.3）
        {
            "name": "线索管理（v1.3）",
            "url": "https://api.oceanengine.com/open_api/v1.3/qianchuan/clue/get/",
            "params": {
                "advertiser_id": ADVERTISER_ID,
                "start_time": yesterday_time,
                "end_time": today_time,
                "page": 1,
                "page_size": 100
            },
            "use_header": False
        }
    ]
    
    # 执行测试
    results = {}
    for test in tests:
        result = test_api(
            test['name'],
            test['url'],
            test['params'],
            test.get('use_header', True)
        )
        if result:
            results[test['name']] = result
    
    # 总结
    print("=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    if results:
        print(f"✅ 成功的接口: {len(results)} 个")
        for name in results.keys():
            print(f"   - {name}")
    else:
        print("❌ 没有找到可用的客资接口")
        print()
        print("💡 建议:")
        print("   1. 检查是否有客资管理权限")
        print("   2. 在巨量后台查看是否有客资数据")
        print("   3. 联系巨量引擎技术支持确认接口")

if __name__ == '__main__':
    main()
