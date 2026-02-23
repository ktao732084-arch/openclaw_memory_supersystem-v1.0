#!/usr/bin/env python3
"""
下载所有账户的数据（基于项目列表）
"""
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
LOCAL_ACCOUNT_ID = 1835880409219083

def get_all_promotion_data(date_str):
    """获取指定日期的所有单元数据"""
    print(f"📥 下载 {date_str} 的数据...\n")
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    all_data = []
    page = 1
    
    while True:
        params = {
            "local_account_id": LOCAL_ACCOUNT_ID,
            "start_date": date_str,
            "end_date": date_str,
            "time_granularity": "TIME_GRANULARITY_DAILY",
            "metrics": json.dumps([
                "stat_cost",
                "show_cnt",
                "click_cnt",
                "convert_cnt",
                "clue_pay_order_cnt"
            ]),
            "page": page,
            "page_size": 100
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            data = resp.json()
            
            if data.get('code') != 0:
                print(f"❌ 错误: {data.get('message')}")
                break
            
            page_info = data.get('data', {}).get('page_info', {})
            promotions = data.get('data', {}).get('promotion_list', [])
            
            if not promotions:
                break
            
            all_data.extend(promotions)
            
            print(f"   第 {page} 页: {len(promotions)} 条")
            
            # 检查是否还有下一页
            if page >= page_info.get('total_page', 0):
                break
            
            page += 1
            
        except Exception as e:
            print(f"❌ 异常: {e}")
            break
    
    return all_data

def analyze_data(data_list):
    """分析数据统计"""
    print(f"\n📊 数据统计:")
    print(f"   总单元数: {len(data_list)}")
    
    # 按项目分组
    projects = defaultdict(list)
    for item in data_list:
        project_name = item.get('project_name', '未知')
        projects[project_name].append(item)
    
    print(f"   涉及项目: {len(projects)} 个")
    
    # 计算总消耗和转化
    total_cost = sum(item.get('stat_cost', 0) for item in data_list)
    total_convert = sum(item.get('convert_cnt', 0) for item in data_list)
    total_clue = sum(item.get('clue_pay_order_cnt', 0) for item in data_list)
    
    print(f"   总消耗: {total_cost:.2f} 元")
    print(f"   总转化: {total_convert}")
    print(f"   总团购线索: {total_clue}")
    
    if total_convert > 0:
        avg_cost = total_cost / total_convert
        print(f"   平均转化成本: {avg_cost:.2f} 元")
    
    # 显示前10个项目
    print(f"\n📋 项目列表（前10个）:")
    for i, (project_name, items) in enumerate(list(projects.items())[:10], 1):
        project_cost = sum(item.get('stat_cost', 0) for item in items)
        project_convert = sum(item.get('convert_cnt', 0) for item in items)
        print(f"   {i}. {project_name}")
        print(f"      单元数: {len(items)}, 消耗: {project_cost:.2f}, 转化: {project_convert}")
    
    if len(projects) > 10:
        print(f"   ... 还有 {len(projects) - 10} 个项目")
    
    return data_list

def save_to_json(data_list, filename):
    """保存为JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    print(f"\n💾 已保存到: {filename}")

if __name__ == '__main__':
    # 默认下载昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print("="*60)
    print(f"开始下载 {yesterday} 的所有数据")
    print("="*60 + "\n")
    
    # 获取数据
    all_data = get_all_promotion_data(yesterday)
    
    if all_data:
        # 分析数据
        analyze_data(all_data)
        
        # 保存到文件
        filename = f"data_{yesterday.replace('-', '')}.json"
        save_to_json(all_data, filename)
        
        print("\n" + "="*60)
        print("✅ 下载完成！")
        print("="*60)
    else:
        print("\n❌ 没有获取到数据")
