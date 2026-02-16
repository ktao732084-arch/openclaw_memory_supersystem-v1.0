#!/usr/bin/env python3
"""
测试单元报表接口能获取哪些客资相关字段
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from token_manager import get_valid_token

LOCAL_ACCOUNT_ID = 1835880409219083

def test_clue_metrics():
    """测试客资相关指标"""
    
    access_token = get_valid_token()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 尝试获取所有可能的客资相关指标
    metrics_to_test = [
        # 基础指标
        "stat_cost", "show_cnt", "click_cnt", "convert_cnt",
        
        # 客资相关
        "clue_pay_order_cnt",  # 团购线索数（已知可用）
        "clue_cnt",            # 线索数
        "clue_cost",           # 线索成本
        "valid_clue_cnt",      # 有效线索数
        "valid_clue_cost",     # 有效线索成本
        "form_cnt",            # 表单提交数
        "form_cost",           # 表单成本
        
        # 转化相关
        "convert_cost",        # 转化成本
        "deep_convert_cnt",    # 深度转化数
        "deep_convert_cost",   # 深度转化成本
        
        # 其他
        "attribution_convert_cnt",  # 归因转化数
        "attribution_convert_cost", # 归因转化成本
    ]
    
    print(f"📊 测试客资相关指标")
    print(f"   日期: {yesterday}")
    print(f"   测试指标数: {len(metrics_to_test)}")
    print()
    
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(metrics_to_test),
        "page": 1,
        "page_size": 10
    }
    
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    
    headers = {"Access-Token": access_token}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if data.get('code') == 0:
                promotion_list = data.get('data', {}).get('promotion_list', [])
                
                if promotion_list:
                    print(f"✅ 成功获取 {len(promotion_list)} 条数据")
                    print()
                    print("=" * 60)
                    print("📋 可用的客资相关字段:")
                    print("=" * 60)
                    
                    # 分析第一条数据，看哪些字段有值
                    first_item = promotion_list[0]
                    
                    clue_fields = {}
                    for key, value in first_item.items():
                        if any(keyword in key.lower() for keyword in ['clue', 'form', 'convert', 'lead']):
                            clue_fields[key] = value
                    
                    if clue_fields:
                        print("\n找到的客资相关字段:")
                        for key, value in clue_fields.items():
                            print(f"   ✓ {key}: {value}")
                    else:
                        print("\n⚠️  没有找到客资相关字段")
                    
                    print()
                    print("=" * 60)
                    print("完整数据示例:")
                    print("=" * 60)
                    print(json.dumps(first_item, ensure_ascii=False, indent=2))
                else:
                    print("⚠️  没有数据")
            else:
                print(f"❌ 失败: {data.get('message')}")
                print(f"   错误码: {data.get('code')}")
                
                # 如果是字段错误，显示错误信息
                if 'invalid' in data.get('message', '').lower():
                    print()
                    print("💡 可能是某些指标不可用，尝试使用基础指标...")
        else:
            print(f"❌ HTTP错误: {resp.status_code}")
            print(f"   响应: {resp.text[:500]}")
    
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_clue_metrics()
