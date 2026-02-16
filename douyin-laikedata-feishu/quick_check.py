#!/usr/bin/env python3
"""快速检查最近的数据"""

import requests
import os

# 读取配置
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            env_vars[key] = value.strip('"').strip("'")

def get_feishu_token():
    """获取飞书 token"""
    url = 'https://open.feishu.cn/open-api/auth/v3/tenant_access_token/internal'
    payload = {
        'app_id': env_vars['FEISHU_APP_ID'],
        'app_secret': env_vars['FEISHU_APP_SECRET']
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if 'tenant_access_token' in data:
        return data['tenant_access_token']
    else:
        print(f"获取token失败: {data}")
        return None

def check_recent_data():
    """检查最近的数据"""
    token = get_feishu_token()
    if not token:
        return
    
    app_token = env_vars['FEISHU_APP_TOKEN']
    table_id = env_vars['FEISHU_TABLE_ID']
    
    # 获取最近20条记录
    url = f'https://open.feishu.cn/open-api/bitable/v1/apps/{app_token}/tables/{table_id}/records'
    headers = {'Authorization': f'Bearer {token}'}
    params = {'page_size': 20}
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if 'data' not in data:
        print(f"获取数据失败: {data}")
        return
    
    records = data['data']['items']
    
    print(f"\n📊 最近20条记录:\n")
    print(f"{'日期':<12} {'单元名称':<30} {'消耗':<8} {'转化':<6} {'客资':<6} {'转化率':<8} {'获客成本':<10}")
    print("-" * 100)
    
    for r in records:
        fields = r['fields']
        date = fields.get('时间', '')
        unit_name = fields.get('单元名称', '')[:28]
        cost = fields.get('消耗(元)', '0')
        convert = fields.get('转化数', '0')
        kezi = fields.get('客资数量', '0')
        rate = fields.get('客资转化率(%)', '0')
        actual_cost = fields.get('实际获客成本', '0')
        
        print(f"{date:<12} {unit_name:<30} {cost:<8} {convert:<6} {kezi:<6} {rate:<8} {actual_cost:<10}")
    
    # 统计异常数据
    print("\n\n⚠️  数据检查:")
    abnormal = []
    for r in records:
        fields = r['fields']
        try:
            convert = int(fields.get('转化数', '0'))
            kezi = int(fields.get('客资数量', '0'))
            
            if kezi > 0 and convert > kezi:
                abnormal.append({
                    'date': fields.get('时间', ''),
                    'name': fields.get('单元名称', ''),
                    'convert': convert,
                    'kezi': kezi
                })
        except:
            pass
    
    if abnormal:
        print(f"\n发现 {len(abnormal)} 条异常数据（转化数 > 客资数）:")
        for item in abnormal:
            print(f"  {item['date']} | {item['name']}")
            print(f"    转化数:{item['convert']} > 客资数:{item['kezi']}")
    else:
        print("\n✅ 没有发现异常数据（所有记录的客资数 >= 转化数）")

if __name__ == '__main__':
    check_recent_data()
