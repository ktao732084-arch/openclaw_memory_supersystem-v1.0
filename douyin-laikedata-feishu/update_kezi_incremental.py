#!/usr/bin/env python3
"""
增量更新客资统计
1. 自动找到最新的Sheet表格
2. 只处理今天新增的客资数据
3. 更新"数据表"中的统计字段
"""

import requests
from datetime import datetime, timedelta
from collections import defaultdict

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'  # 数据表（投放数据）

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def find_latest_sheet(token):
    """找到最新的Sheet表格"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables'
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    tables = resp.json()['data']['items']
    
    # 筛选出Sheet开头的表格
    sheet_tables = [t for t in tables if t['name'].startswith('Sheet')]
    
    if not sheet_tables:
        print("❌ 没有找到Sheet表格")
        return None
    
    # 取最后一个（最新的）
    latest_sheet = sheet_tables[-1]
    print(f"✓ 找到最新Sheet: {latest_sheet['name']} (ID: {latest_sheet['table_id']})")
    return latest_sheet

def get_today_kezi(token, table_id, target_date=None):
    """获取指定日期的客资数据（默认今天）"""
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"📅 筛选日期: {target_date}")
    
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records'
    headers = {'Authorization': f'Bearer {token}'}
    
    all_records = []
    page_token = None
    page_num = 0
    
    while True:
        params = {'page_size': 500}
        if page_token:
            params['page_token'] = page_token
        
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        
        if data.get('code') != 0:
            print(f"❌ 获取记录失败: {data}")
            break
        
        items = data.get('data', {}).get('items', [])
        
        # 筛选今天的数据
        for item in items:
            fields = item.get('fields', {})
            create_time = fields.get('线索创建时间', '')
            
            # 检查日期是否匹配
            if create_time.startswith(target_date):
                all_records.append(item)
        
        page_num += 1
        print(f"  处理第 {page_num} 页，已找到 {len(all_records)} 条今日客资")
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    return all_records

def count_kezi_by_unit(kezi_records):
    """按单元ID统计客资数量"""
    kezi_count = defaultdict(int)
    
    for record in kezi_records:
        fields = record.get('fields', {})
        unit_id = fields.get('单元ID', '').strip()
        
        if unit_id:  # 只统计有单元ID的客资
            kezi_count[unit_id] += 1
    
    return kezi_count

def get_all_toufa_records(token):
    """获取所有投放数据"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records'
    headers = {'Authorization': f'Bearer {token}'}
    
    all_records = []
    page_token = None
    
    while True:
        params = {'page_size': 500}
        if page_token:
            params['page_token'] = page_token
        
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        
        if data.get('code') != 0:
            print(f"❌ 获取记录失败: {data}")
            break
        
        items = data.get('data', {}).get('items', [])
        all_records.extend(items)
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    return all_records

def update_toufa_stats(token, toufa_records, today_kezi_count):
    """更新投放数据的客资统计（增量）"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records/batch_update'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    updates = []
    
    for record in toufa_records:
        fields = record.get('fields', {})
        unit_id = fields.get('单元ID', '').strip()
        
        if not unit_id:
            continue
        
        # 如果今天这个单元ID有新客资，才更新
        if unit_id not in today_kezi_count:
            continue
        
        # 获取当前的客资数量
        current_kezi = int(fields.get('客资数量', 0) or 0)
        
        # 加上今天新增的
        new_kezi = current_kezi + today_kezi_count[unit_id]
        
        # 重新计算获客成本
        try:
            cost = float(fields.get('消耗(元)', 0))
            actual_cost = round(cost / new_kezi, 2) if new_kezi > 0 else 0
        except:
            actual_cost = 0
        
        # 重新计算客资转化率
        try:
            convert = int(fields.get('转化数', 0))
            kezi_rate = round(new_kezi / convert * 100, 2) if convert > 0 else 0
        except:
            kezi_rate = 0
        
        # 生成客资详情链接
        kezi_link = f"https://ocnbk46uzxq8.feishu.cn/base/{FEISHU_APP_TOKEN}?table=Sheet&filter=单元ID={unit_id}"
        
        # 准备更新数据
        update_fields = {
            '客资数量': str(new_kezi),
            '实际获客成本': str(actual_cost),
            '客资转化率(%)': str(kezi_rate),
            '客资详情': {
                'link': kezi_link,
                'text': f'查看{new_kezi}条客资'
            }
        }
        
        updates.append({
            'record_id': record.get('record_id'),
            'fields': update_fields
        })
    
    if not updates:
        print("  没有需要更新的记录")
        return
    
    # 批量更新（每次最多500条）
    batch_size = 500
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        payload = {'records': batch}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            print(f"  ✓ 更新 {len(batch)} 条记录")
        else:
            print(f"  ❌ 更新失败: {data}")

def main():
    print("🔄 开始增量更新客资统计...\n")
    
    # 获取token
    token = get_token()
    
    # 1. 找到最新的Sheet
    latest_sheet = find_latest_sheet(token)
    if not latest_sheet:
        return
    
    # 2. 获取今天的客资数据
    print("\n📥 读取今天的客资数据...")
    today_kezi = get_today_kezi(token, latest_sheet['table_id'])
    print(f"   找到 {len(today_kezi)} 条今日客资")
    
    if not today_kezi:
        print("\n⚠️  今天没有新客资，无需更新")
        return
    
    # 3. 按单元ID统计
    print("\n📊 按单元ID统计...")
    today_kezi_count = count_kezi_by_unit(today_kezi)
    print(f"   涉及 {len(today_kezi_count)} 个单元ID")
    
    # 显示统计结果
    print("\n📈 今日客资统计（前10个单元）:")
    print("-" * 80)
    for unit_id, count in sorted(today_kezi_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   单元ID {unit_id}: +{count} 条客资")
    
    # 4. 读取投放数据
    print("\n📥 读取投放数据...")
    toufa_records = get_all_toufa_records(token)
    print(f"   找到 {len(toufa_records)} 条投放记录")
    
    # 5. 更新投放数据表
    print("\n📝 更新投放数据表...")
    update_toufa_stats(token, toufa_records, today_kezi_count)
    
    print("\n✅ 客资统计更新完成！")

if __name__ == '__main__':
    main()
