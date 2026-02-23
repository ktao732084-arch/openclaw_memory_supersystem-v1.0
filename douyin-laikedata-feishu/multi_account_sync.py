#!/usr/bin/env python3
"""
多账户数据批量获取工具

如果你有多个本地推账户ID，可以使用这个脚本批量获取数据。

使用方法：
1. 编辑 ACCOUNT_IDS 列表，添加所有账户ID
2. 运行脚本：python3 multi_account_sync.py
3. 数据会自动合并并上传到飞书
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token

# ============================================================
# 配置区域：从 Excel 自动提取的账户ID
# ============================================================

# 使用所有77个账户（推荐）
# 会自动跳过无数据的账户，不影响性能
from account_ids import ACCOUNT_IDS
from account_names import ACCOUNT_NAMES

# 如果只想同步有数据的账户（更快，但需要定期重新扫描）
# from active_account_ids import ACTIVE_ACCOUNT_IDS as ACCOUNT_IDS

# 手动指定账户
# ACCOUNT_IDS = [
#     1835880409219083,
#     # 添加更多...
# ]

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_account_data(account_id, start_date, end_date):
    """获取单个账户的数据"""
    # print(f"  📊 获取账户 {account_id} 的数据...")  # 注释掉，避免输出太多
    
    access_token = get_valid_token()
    if not access_token:
        print(f"    ❌ 账户 {account_id}: 无法获取 Access Token")
        return []
    
    params = {
        "local_account_id": account_id,
        "start_date": start_date,
        "end_date": end_date,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
        "page": 1,
        "page_size": 100
    }
    
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    
    headers = {"Access-Token": access_token}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            if promotion_list:
                print(f"    ✓ 账户 {account_id}: {len(promotion_list)} 条数据")
                # 给每条数据添加账户ID字段
                for item in promotion_list:
                    item['local_account_id'] = account_id
            # 无数据时不输出，避免刷屏
            return promotion_list
        else:
            error_msg = data.get('message', '未知错误')
            # 只在非"无数据"错误时输出
            if 'no data' not in error_msg.lower():
                print(f"    ❌ 账户 {account_id}: {error_msg}")
            return []
    except Exception as e:
        print(f"    ❌ 账户 {account_id}: 异常 {e}")
        return []

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            return data['tenant_access_token']
        else:
            print(f"❌ 获取飞书 Token 失败: {data.get('msg')}")
            return None
    except Exception as e:
        print(f"❌ 获取飞书 Token 异常: {e}")
        return None

def write_to_feishu(data_list):
    """写入数据到飞书"""
    if not data_list:
        print("⚠️  没有数据需要写入")
        return False
    
    print(f"\n📤 写入 {len(data_list)} 条数据到飞书...")
    
    token = get_feishu_token()
    if not token:
        return False
    
    # 构建记录
    records = []
    for item in data_list:
        cost = item.get('stat_cost', 0)
        convert = item.get('convert_cnt', 0)
        account_id = item.get('local_account_id')
        
        # 获取账户名称
        account_name = ACCOUNT_NAMES.get(account_id, f"账户{account_id}")
        
        record = {
            "fields": {
                "文本": account_name,  # 账户名称
                "时间": item.get('stat_time_day', ''),
                "单元ID": str(item.get('promotion_id', '')),
                "单元名称": item.get('promotion_name', ''),
                "消耗(元)": str(cost),
                "转化数": str(convert),
                "转化成本(元)": str(round(cost / convert, 2)) if convert > 0 else "0",
                "团购线索数": str(item.get('clue_pay_order_cnt', 0))
            }
        }
        records.append(record)
    
    # 批量写入
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
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
                print(f"  ✓ 第 {i//batch_size + 1} 批写入成功: {len(batch)} 条")
            else:
                print(f"  ❌ 第 {i//batch_size + 1} 批失败: {result.get('msg')}")
        except Exception as e:
            print(f"  ❌ 写入失败: {e}")
    
    print(f"\n✅ 写入完成！成功 {success_count}/{len(records)} 条\n")
    return success_count > 0

def main():
    """主流程"""
    print("="*60)
    print("多账户数据批量获取")
    print("="*60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 检查账户列表
    if len(ACCOUNT_IDS) == 0:
        print("❌ 错误: 未配置账户ID")
        print("\n请编辑脚本，在 ACCOUNT_IDS 列表中添加账户ID")
        return
    
    # 获取昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"📋 配置的账户数量: {len(ACCOUNT_IDS)}")
    print(f"📅 获取日期: {yesterday}\n")
    
    print("🔄 开始获取数据...")
    print("   (只显示有数据的账户)\n")
    
    # 批量获取数据
    all_data = []
    success_accounts = 0
    
    for account_id in ACCOUNT_IDS:
        data = get_account_data(account_id, yesterday, yesterday)
        if data:
            all_data.extend(data)
            success_accounts += 1
    
    print(f"\n📊 汇总:")
    print(f"  成功账户: {success_accounts}/{len(ACCOUNT_IDS)}")
    print(f"  总记录数: {len(all_data)} 条")
    
    # 写入飞书
    if all_data:
        write_to_feishu(all_data)
    else:
        print("\n⚠️  没有数据，跳过写入")
    
    print("="*60)
    print("任务完成")
    print("="*60)

if __name__ == '__main__':
    main()
