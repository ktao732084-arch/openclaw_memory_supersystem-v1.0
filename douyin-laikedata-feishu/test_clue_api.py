#!/usr/bin/env python3
"""
测试巨量引擎客资数据API
"""
import requests
import json
from datetime import datetime, timedelta
from token_manager import get_valid_token

# 配置
LOCAL_ACCOUNT_ID = 1835880409219083

def test_clue_api():
    """测试客资数据接口"""
    
    # 获取有效的 access_token
    access_token = get_valid_token()
    
    # 计算日期（昨天）
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📊 测试客资数据接口")
    print(f"   日期: {yesterday}")
    print(f"   账户ID: {LOCAL_ACCOUNT_ID}")
    print()
    
    # 尝试不同的客资接口
    endpoints = [
        # 本地推客资接口
        {
            "name": "本地推客资列表",
            "url": "https://api.oceanengine.com/open_api/v3.0/local/clue/list/",
            "method": "GET",
            "params": {
                "local_account_id": LOCAL_ACCOUNT_ID,
                "start_time": f"{yesterday} 00:00:00",
                "end_time": f"{yesterday} 23:59:59",
                "page": 1,
                "page_size": 100
            }
        },
        # 通用客资接口
        {
            "name": "客资列表（通用）",
            "url": "https://api.oceanengine.com/open_api/2/tools/clue/get/",
            "method": "GET",
            "params": {
                "advertiser_id": LOCAL_ACCOUNT_ID,
                "start_time": f"{yesterday} 00:00:00",
                "end_time": f"{yesterday} 23:59:59",
                "page": 1,
                "page_size": 100
            }
        },
        # 客资报表接口
        {
            "name": "客资报表",
            "url": "https://api.oceanengine.com/open_api/v3.0/local/report/clue/get/",
            "method": "GET",
            "params": {
                "local_account_id": LOCAL_ACCOUNT_ID,
                "start_date": yesterday,
                "end_date": yesterday,
                "time_granularity": "TIME_GRANULARITY_DAILY",
                "page": 1,
                "page_size": 100
            }
        }
    ]
    
    for endpoint in endpoints:
        print(f"🔍 测试: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            if endpoint['method'] == 'GET':
                # 添加 access_token
                params = endpoint['params'].copy()
                params['access_token'] = access_token
                
                response = requests.get(
                    endpoint['url'],
                    params=params,
                    timeout=30
                )
            else:
                # POST 请求
                headers = {
                    'Content-Type': 'application/json',
                    'Access-Token': access_token
                }
                response = requests.post(
                    endpoint['url'],
                    json=endpoint['params'],
                    headers=headers,
                    timeout=30
                )
            
            print(f"   状态码: {response.status_code}")
            print(f"   原始响应: {response.text[:500]}")
            
            try:
                result = response.json()
                print(f"   JSON响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except:
                print(f"   ⚠️  无法解析JSON")
                continue
            
            # 如果成功，显示数据结构
            if result.get('code') == 0 and result.get('data'):
                data = result['data']
                if isinstance(data, dict):
                    if 'list' in data and data['list']:
                        print(f"   ✅ 成功！获取到 {len(data['list'])} 条客资数据")
                        print(f"   数据示例: {json.dumps(data['list'][0], ensure_ascii=False, indent=2)}")
                    elif 'clues' in data and data['clues']:
                        print(f"   ✅ 成功！获取到 {len(data['clues'])} 条客资数据")
                        print(f"   数据示例: {json.dumps(data['clues'][0], ensure_ascii=False, indent=2)}")
                    else:
                        print(f"   ⚠️  返回成功但数据为空")
                elif isinstance(data, list) and data:
                    print(f"   ✅ 成功！获取到 {len(data)} 条客资数据")
                    print(f"   数据示例: {json.dumps(data[0], ensure_ascii=False, indent=2)}")
            else:
                print(f"   ❌ 失败: {result.get('message', '未知错误')}")
            
        except Exception as e:
            print(f"   ❌ 异常: {str(e)}")
        
        print()

if __name__ == '__main__':
    test_clue_api()
