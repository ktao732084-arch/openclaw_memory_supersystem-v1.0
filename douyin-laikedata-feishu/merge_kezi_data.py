#!/usr/bin/env python3
"""
客资数据统计脚本
按单元ID统计客资数量，计算获客成本和转化率，并生成客资详情链接
"""

import requests
from collections import defaultdict

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'  # 数据表（投放数据）
TABLE_KEZI = 'tbl3Oyi6JYt3ZUIP'   # Sheet2（客资数据）

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def get_all_records(token, table_id):
    """获取表格的所有记录（分页）"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records'
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

def normalize_unit_id(unit_id):
    """标准化单元ID格式，处理科学计数法问题
    
    注意：不使用 float 转换，因为会导致精度丢失
    客资数据中的单元ID末尾是000（科学计数法导致），需要模糊匹配
    """
    if not unit_id:
        return ''
    # 直接返回字符串，去除空格
    return str(unit_id).strip()

def fuzzy_match_unit_id(kezi_id, toufa_id):
    """模糊匹配单元ID
    
    客资数据：7600351168191611000（末尾000）
    投放数据：7600351168191610923（完整）
    
    匹配策略：比较前15位
    """
    if not kezi_id or not toufa_id:
        return False
    
    # 取前15位进行匹配
    return kezi_id[:15] == toufa_id[:15]

def count_kezi_by_unit_and_date(kezi_records):
    """按单元ID和日期统计客资数量（只统计有手机号的有效客资）"""
    # 使用嵌套字典：{日期: {单元ID: 数量}}
    kezi_count = defaultdict(lambda: defaultdict(int))
    kezi_details = defaultdict(lambda: defaultdict(list))
    
    for record in kezi_records:
        fields = record.get('fields', {})
        unit_id_raw = fields.get('单元ID', '').strip()
        create_time = fields.get('线索创建时间', '').strip()
        phone = fields.get('手机号', '').strip()
        
        # 只统计有单元ID、创建时间和手机号的有效客资
        if unit_id_raw and create_time and phone:
            # 标准化单元ID
            unit_id = normalize_unit_id(unit_id_raw)
            
            # 提取日期（格式：2026-01-21 14:57:05 → 2026-01-21）
            try:
                date = create_time.split(' ')[0]  # 取日期部分
            except:
                continue
            
            # 按日期和单元ID统计
            kezi_count[date][unit_id] += 1
            kezi_details[date][unit_id].append({
                'record_id': record.get('record_id'),
                '姓名': fields.get('姓名', ''),
                '手机号': phone,
                '线索创建时间': create_time,
                '营销类型': fields.get('营销类型', '')
            })
    
    return kezi_count, kezi_details

def create_kezi_link(unit_id):
    """生成客资详情链接（飞书多维表格筛选视图）"""
    # 飞书多维表格的筛选链接格式
    base_url = f"https://ocnbk46uzxq8.feishu.cn/base/{FEISHU_APP_TOKEN}"
    # 注意：这个链接需要在飞书中手动创建筛选视图，或者使用API创建
    # 这里先返回表格链接，后续可以优化
    return f"{base_url}?table={TABLE_KEZI}&view=单元ID筛选&filter=单元ID={unit_id}"

def update_toufa_records(token, toufa_records, kezi_count_by_date):
    """更新投放数据表，添加客资统计字段"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records/batch_update'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    updates = []
    
    for record in toufa_records:
        fields = record.get('fields', {})
        unit_id_raw = fields.get('单元ID', '').strip()
        date = fields.get('时间', '').strip()  # 获取投放日期
        
        if not unit_id_raw or not date:
            continue
        
        # 标准化单元ID
        unit_id = normalize_unit_id(unit_id_raw)
        
        # 获取该日期该单元的客资数量
        kezi_num = kezi_count_by_date.get(date, {}).get(unit_id, 0)
        
        # 计算获客成本
        try:
            cost = float(fields.get('消耗(元)', 0))
            actual_cost = round(cost / kezi_num, 2) if kezi_num > 0 else 0
        except:
            actual_cost = 0
        
        # 计算客资转化率（客资中有多少转化成功）
        try:
            convert = int(fields.get('转化数', 0))
            # 客资转化率 = 转化数 / 客资数量 × 100%
            # 表示客资中有多少比例转化成功
            kezi_rate = round(convert / kezi_num * 100, 2) if kezi_num > 0 else 0
        except:
            kezi_rate = 0
        
        # 生成客资详情链接
        kezi_link = create_kezi_link(unit_id)
        
        # 准备更新数据
        # 飞书URL字段格式: {"link": "url", "text": "显示文本"}
        update_fields = {
            '客资数量': str(kezi_num),
            '实际获客成本': str(actual_cost),
            '客资转化率(%)': str(kezi_rate),  # 转化数/客资数×100%
            '客资详情': {
                'link': kezi_link,
                'text': f'查看{kezi_num}条客资'
            }
        }
        
        updates.append({
            'record_id': record.get('record_id'),
            'fields': update_fields
        })
    
    # 批量更新（每次最多500条）
    batch_size = 500
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        payload = {'records': batch}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            print(f"✓ 更新 {len(batch)} 条记录")
        else:
            print(f"❌ 更新失败: {data}")

def main():
    print("🔄 开始统计客资数据（按日期+模糊匹配）...\n")
    
    # 获取token
    token = get_token()
    
    # 读取投放数据（先读取，建立映射表）
    print("📥 读取投放数据...")
    toufa_records = get_all_records(token, TABLE_TOUFA)
    print(f"   找到 {len(toufa_records)} 条投放记录")
    
    # 建立单元ID映射表（前15位 -> 完整ID）
    print("\n🔗 建立单元ID映射表...")
    unit_id_map = {}  # {前15位: 完整ID}
    for record in toufa_records:
        unit_id = record['fields'].get('单元ID', '').strip()
        if unit_id and len(unit_id) >= 15:
            prefix = unit_id[:15]
            unit_id_map[prefix] = unit_id
    print(f"   映射表包含 {len(unit_id_map)} 个单元ID")
    
    # 读取客资数据
    print("\n📥 读取客资数据...")
    kezi_records = get_all_records(token, TABLE_KEZI)
    print(f"   找到 {len(kezi_records)} 条客资记录")
    
    # 按日期和单元ID统计（使用映射表转换）
    print("\n📊 按日期和单元ID统计（模糊匹配）...")
    kezi_count_by_date = defaultdict(lambda: defaultdict(int))
    matched_count = 0
    unmatched_count = 0
    
    for record in kezi_records:
        fields = record.get('fields', {})
        unit_id_raw = fields.get('单元ID', '').strip()
        create_time = fields.get('线索创建时间', '').strip()
        phone = fields.get('手机号', '').strip()
        
        # 只统计有单元ID、创建时间和手机号的有效客资
        if unit_id_raw and create_time and phone:
            # 提取日期
            try:
                date = create_time.split(' ')[0]
            except:
                continue
            
            # 模糊匹配：用前15位查找完整单元ID
            if len(unit_id_raw) >= 15:
                prefix = unit_id_raw[:15]
                matched_unit_id = unit_id_map.get(prefix)
                
                if matched_unit_id:
                    # 匹配成功，使用投放数据中的完整ID
                    kezi_count_by_date[date][matched_unit_id] += 1
                    matched_count += 1
                else:
                    # 未匹配到，可能是老单元或其他账户的
                    unmatched_count += 1
    
    print(f"   匹配成功: {matched_count} 条")
    print(f"   未匹配: {unmatched_count} 条（可能是老单元或其他账户）")
    
    # 统计涉及的日期和单元
    total_dates = len(kezi_count_by_date)
    total_units = sum(len(units) for units in kezi_count_by_date.values())
    print(f"   涉及 {total_dates} 个日期，{total_units} 个单元ID")
    
    # 显示统计结果（按日期）
    print("\n📈 客资统计（最近3天）:")
    print("-" * 80)
    for date in sorted(kezi_count_by_date.keys(), reverse=True)[:3]:
        units = kezi_count_by_date[date]
        total = sum(units.values())
        print(f"   {date}: {total} 条客资，涉及 {len(units)} 个单元")
        # 显示该日期客资最多的3个单元
        for unit_id, count in sorted(units.items(), key=lambda x: -x[1])[:3]:
            # 查找单元名称
            unit_name = ''
            for r in toufa_records:
                if r['fields'].get('单元ID') == unit_id:
                    unit_name = r['fields'].get('单元名称', '')
                    break
            print(f"      - {unit_name[:20]}: {count} 条")
    
    # 更新投放数据表
    print("\n📝 更新投放数据表...")
    update_toufa_records(token, toufa_records, kezi_count_by_date)
    
    print("\n✅ 客资数据统计完成！")

if __name__ == '__main__':
    main()
