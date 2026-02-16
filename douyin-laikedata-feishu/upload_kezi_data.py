#!/usr/bin/env python3
"""
上传客资数据到飞书多维表格
"""
import pandas as pd
import requests
import json
import sys
import os

# 读取配置
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value.strip('"').strip("'")

# 飞书配置
FEISHU_APP_ID = env_vars['FEISHU_APP_ID']
FEISHU_APP_SECRET = env_vars['FEISHU_APP_SECRET']
FEISHU_APP_TOKEN = env_vars['FEISHU_APP_TOKEN']
FEISHU_KEZI_TABLE_ID = env_vars['FEISHU_KEZI_TABLE_ID']

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def upload_kezi_data(excel_path):
    """上传客资数据"""
    print("="*60)
    print("上传客资数据到飞书")
    print("="*60)
    print()
    
    # 读取Excel
    print(f"1. 读取Excel文件: {excel_path}")
    
    # 尝试读取所有Sheet
    excel_file = pd.ExcelFile(excel_path)
    print(f"   找到 {len(excel_file.sheet_names)} 个Sheet")
    
    # 找到最新的Sheet（按日期排序）
    sheet_names = sorted(excel_file.sheet_names, reverse=True)
    latest_sheet = sheet_names[0]
    print(f"   使用最新Sheet: {latest_sheet}")
    
    df = pd.read_excel(excel_path, sheet_name=latest_sheet)
    print(f"   原始数据: {len(df)} 条")
    print()
    
    # 数据清洗
    print("2. 数据清洗...")
    
    # 只保留有手机号的
    df = df[df['手机号'].notna()]
    print(f"   有手机号: {len(df)} 条")
    
    # 只保留有单元ID的
    df = df[df['单元ID'].notna()]
    print(f"   有单元ID: {len(df)} 条")
    
    # 提取单元ID前15位
    df['单元ID前15位'] = df['单元ID'].astype(str).str[:15]
    
    # 按手机号+单元ID+日期去重
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['手机号', '单元ID前15位', '日期'])
    print(f"   去重后: {len(df)} 条（去除 {before_dedup - len(df)} 条重复）")
    print()
    
    # 构建记录
    print("3. 构建飞书记录...")
    records = []
    for _, row in df.iterrows():
        # 处理日期格式
        date_str = ''
        if pd.notna(row['日期']):
            if isinstance(row['日期'], str):
                date_str = row['日期']
            else:
                date_str = row['日期'].strftime('%Y-%m-%d')
        
        record = {
            "fields": {
                "手机号": str(row['手机号']),
                "单元ID前15位": row['单元ID前15位'],
                "日期": date_str,
                "客户姓名": str(row.get('客户姓名', ''))
            }
        }
        records.append(record)
    
    print(f"   构建完成: {len(records)} 条记录")
    print()
    
    # 写入飞书
    print("4. 写入飞书多维表格...")
    token = get_feishu_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_KEZI_TABLE_ID}/records/batch_create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 分批写入（每批500条）
    batch_size = 500
    success_count = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                success_count += len(batch)
                print(f"   ✓ 第 {i//batch_size + 1} 批写入成功: {len(batch)} 条")
            else:
                print(f"   ✗ 第 {i//batch_size + 1} 批失败: {result.get('msg')}")
        except Exception as e:
            print(f"   ✗ 写入失败: {e}")
    
    print()
    print("="*60)
    print(f"完成！成功写入 {success_count}/{len(records)} 条")
    print("="*60)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python3 upload_kezi_data.py <Excel文件路径>")
        print("示例: python3 upload_kezi_data.py /path/to/客资数据.xlsx")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    
    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在: {excel_path}")
        sys.exit(1)
    
    upload_kezi_data(excel_path)
