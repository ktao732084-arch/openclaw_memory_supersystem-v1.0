#!/usr/bin/env python3
"""
尝试通过项目接口反推账户列表
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
ADVERTISER_ID = 1769665409798152
LOCAL_ACCOUNT_ID = 1835880409219083  # 已知的一个账户

def get_project_list():
    """获取项目列表（可能包含账户信息）"""
    print("🔍 尝试获取项目列表...\n")
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/project/list/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "page": 1,
        "page_size": 100
    }
    
    print(f"请求: {url}")
    print(f"参数: {json.dumps(params, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        data = resp.json()
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
        
        if data.get('code') == 0:
            projects = data.get('data', {}).get('list', [])
            print(f"✅ 找到 {len(projects)} 个项目")
            return projects
        else:
            print(f"❌ 错误: {data.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

def try_report_with_filtering():
    """尝试用过滤条件获取数据"""
    print("\n" + "="*60)
    print("🔍 尝试用过滤条件获取报表数据...\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # 尝试用 filtering 参数
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps([
            "stat_cost",
            "show_cnt",
            "click_cnt",
            "convert_cnt",
            "clue_pay_order_cnt"
        ]),
        "page": 1,
        "page_size": 100
    }
    
    print(f"请求: {url}")
    print(f"参数: {json.dumps(params, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        data = resp.json()
        
        if data.get('code') == 0:
            page_info = data.get('data', {}).get('page_info', {})
            print(f"✅ 总数据量: {page_info.get('total_number', 0)}")
            print(f"   总页数: {page_info.get('total_page', 0)}")
            
            promotions = data.get('data', {}).get('list', [])
            print(f"   当前页: {len(promotions)} 条\n")
            
            # 检查是否有账户信息
            if promotions:
                first = promotions[0]
                print("第一条数据字段:")
                for key in first.keys():
                    print(f"  - {key}: {first[key]}")
            
            return data
        else:
            print(f"❌ 错误: {data.get('message')}")
            print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return None
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

if __name__ == '__main__':
    # 方法1: 获取项目列表
    projects = get_project_list()
    
    # 方法2: 查看报表数据结构
    report = try_report_with_filtering()
    
    print("\n" + "="*60)
    print("💡 建议:")
    print("1. 在巨量引擎后台手动查看有多少个本地推账户")
    print("2. 提供所有账户的ID，我可以批量下载")
    print("3. 或者告诉我账户的命名规则，我可以尝试遍历")
    print("="*60)
