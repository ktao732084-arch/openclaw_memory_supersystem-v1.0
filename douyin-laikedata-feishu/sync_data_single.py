#!/usr/bin/env python3
"""
巨量本地推数据自动同步到飞书
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys
import os

# 导入 token 管理器和通知器
sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token
from notifier import Notifier

# 配置
LOCAL_ACCOUNT_ID = 1835880409219083

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 通知配置（从环境变量读取）
FEISHU_WEBHOOK_URL = os.getenv('FEISHU_WEBHOOK_URL', '')

# 初始化通知器
notifier = Notifier(FEISHU_WEBHOOK_URL) if FEISHU_WEBHOOK_URL else None

def get_juliang_data(start_date, end_date):
    """获取巨量本地推数据"""
    print(f"📊 获取巨量数据 ({start_date} ~ {end_date})...")
    
    # 获取有效的 access token（自动续期）
    try:
        access_token = get_valid_token()
        if not access_token:
            error_msg = "无法获取有效的 Access Token"
            print(f"❌ {error_msg}")
            if notifier:
                notifier.notify_sync_failed(start_date, error_msg)
            return []
    except Exception as e:
        error_msg = f"Token 获取异常: {str(e)}"
        print(f"❌ {error_msg}")
        if notifier:
            notifier.notify_sync_failed(start_date, error_msg)
        return []
    
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
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
            print(f"✓ 获取到 {len(promotion_list)} 条数据\n")
            return promotion_list
        else:
            error_msg = f"API 返回错误: {data.get('message')}"
            print(f"❌ {error_msg}")
            if notifier:
                notifier.notify_sync_failed(start_date, error_msg, [
                    f"错误码: {data.get('code')}",
                    f"请求ID: {data.get('request_id', 'N/A')}"
                ])
            return []
    except requests.Timeout:
        error_msg = "API 请求超时"
        print(f"❌ {error_msg}")
        if notifier:
            notifier.notify_sync_failed(start_date, error_msg, ["建议检查网络连接"])
        return []
    except Exception as e:
        error_msg = f"请求异常: {str(e)}"
        print(f"❌ {error_msg}")
        if notifier:
            notifier.notify_sync_failed(start_date, error_msg)
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
            error_msg = f"获取飞书 Token 失败: {data.get('msg')}"
            print(f"❌ {error_msg}")
            if notifier:
                notifier.notify_sync_failed("N/A", error_msg, ["请检查飞书应用配置"])
            return None
    except Exception as e:
        error_msg = f"获取飞书 Token 异常: {str(e)}"
        print(f"❌ {error_msg}")
        if notifier:
            notifier.notify_sync_failed("N/A", error_msg)
        return None

def get_existing_records(token, date_str):
    """获取飞书中指定日期的现有记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "page_size": 500,
        "filter": {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "时间",
                    "operator": "is",
                    "value": [date_str]
                }
            ]
        }
    }
    
    all_records = []
    page_token = None
    
    while True:
        if page_token:
            payload["page_token"] = page_token
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                all_records.extend(items)
                
                if not data.get('has_more'):
                    break
                
                page_token = data.get('page_token')
            else:
                break
                
        except Exception as e:
            print(f"⚠️  查询现有记录失败: {e}")
            break
    
    return all_records

def filter_duplicates(new_data, existing_records):
    """过滤重复数据"""
    if not existing_records:
        return new_data
    
    # 构建已存在记录的键集合（日期_单元ID）
    existing_keys = set()
    for record in existing_records:
        fields = record.get('fields', {})
        
        # 处理字段值（可能是字典或字符串）
        date_field = fields.get('时间', '')
        unit_id_field = fields.get('单元ID', '')
        
        if isinstance(date_field, dict):
            date = date_field.get('text', '')
        else:
            date = str(date_field)
        
        if isinstance(unit_id_field, dict):
            unit_id = unit_id_field.get('text', '')
        else:
            unit_id = str(unit_id_field)
        
        if date and unit_id:
            existing_keys.add(f"{date}_{unit_id}")
    
    # 过滤新数据
    unique_data = []
    duplicate_count = 0
    
    for item in new_data:
        date = item.get('stat_time_day', '')
        unit_id = str(item.get('promotion_id', ''))
        key = f"{date}_{unit_id}"
        
        if key not in existing_keys:
            unique_data.append(item)
        else:
            duplicate_count += 1
    
    if duplicate_count > 0:
        print(f"🔍 去重: 过滤掉 {duplicate_count} 条重复数据")
    
    return unique_data

def sync_to_feishu(data_list, enable_dedup=True, force_replace=False):
    """同步数据到飞书多维表格
    
    Args:
        data_list: 要同步的数据列表
        enable_dedup: 是否启用去重（默认True）
        force_replace: 是否强制替换（先删除旧数据再写入，默认False）
    """
    if not data_list:
        print("⚠️  没有数据需要同步")
        return False
    
    print(f"📤 同步 {len(data_list)} 条数据到飞书...")
    
    # 获取飞书token
    token = get_feishu_token()
    if not token:
        return False
    
    # 获取日期（用于通知）
    sync_date = data_list[0].get('stat_time_day', 'N/A') if data_list else 'N/A'
    
    # 强制替换模式：先删除旧数据
    if force_replace and data_list:
        first_date = data_list[0].get('stat_time_day', '')
        if first_date:
            print(f"🗑️  删除 {first_date} 的旧数据...")
            existing_records = get_existing_records(token, first_date)
            if existing_records:
                # 删除旧记录
                delete_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete"
                delete_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                record_ids = [r.get('record_id') for r in existing_records if r.get('record_id')]
                
                if record_ids:
                    # 分批删除
                    batch_size = 500
                    for i in range(0, len(record_ids), batch_size):
                        batch = record_ids[i:i+batch_size]
                        payload = {"records": batch}
                        
                        try:
                            resp = requests.post(delete_url, headers=delete_headers, json=payload, timeout=30)
                            result = resp.json()
                            
                            if result.get('code') == 0:
                                print(f"   ✓ 删除 {len(batch)} 条旧记录")
                            else:
                                print(f"   ⚠️  删除失败: {result.get('msg')}")
                        except Exception as e:
                            print(f"   ⚠️  删除异常: {e}")
    
    # 去重检查（非强制替换模式）
    elif enable_dedup and data_list:
        first_date = data_list[0].get('stat_time_day', '')
        if first_date:
            existing_records = get_existing_records(token, first_date)
            if existing_records:
                existing_count = len(existing_records)
                print(f"⚠️  {first_date} 已有 {existing_count} 条记录")
                print(f"   建议使用 force_replace=True 模式重新同步")
                return False
    
    print(f"📝 准备写入 {len(data_list)} 条数据...")
    
    # 构建记录（所有字段都是文本类型）
    records = []
    total_cost = 0
    total_convert = 0
    
    for item in data_list:
        cost = item.get('stat_cost', 0)
        convert = item.get('convert_cnt', 0)
        
        total_cost += cost
        total_convert += convert
        
        record = {
            "fields": {
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
    
    # 分批写入（每次最多500条）
    batch_size = 500
    success_count = 0
    failed_batches = []
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                success_count += len(batch)
                print(f"✓ 第 {i//batch_size + 1} 批写入成功: {len(batch)} 条")
            else:
                error_msg = result.get('msg', '未知错误')
                print(f"❌ 第 {i//batch_size + 1} 批失败: {error_msg}")
                failed_batches.append(f"第 {i//batch_size + 1} 批: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 写入失败: {error_msg}")
            failed_batches.append(f"第 {i//batch_size + 1} 批: {error_msg}")
    
    print(f"\n✅ 同步完成！成功写入 {success_count}/{len(records)} 条\n")
    
    # 发送通知
    if notifier:
        if success_count == len(records):
            # 全部成功
            avg_cost = round(total_cost / total_convert, 2) if total_convert > 0 else 0
            notifier.notify_sync_success(
                date=sync_date,
                record_count=success_count,
                summary={
                    "总消耗": f"{total_cost:.2f} 元",
                    "总转化": f"{total_convert} 个",
                    "平均转化成本": f"{avg_cost} 元"
                }
            )
        elif success_count > 0:
            # 部分成功
            notifier.notify_sync_failed(
                date=sync_date,
                error_msg=f"部分写入失败 ({success_count}/{len(records)})",
                details=failed_batches[:5]  # 最多显示5个错误
            )
        else:
            # 全部失败
            notifier.notify_sync_failed(
                date=sync_date,
                error_msg="写入飞书失败",
                details=failed_batches[:5]
            )
    
    return success_count > 0

def main():
    """主流程"""
    print("=" * 60)
    print("抖音来客 - 巨量本地推数据自动同步")
    print("=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 获取昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 1. 获取巨量数据
    data = get_juliang_data(yesterday, yesterday)
    
    # 2. 同步到飞书
    if data:
        sync_to_feishu(data)
    else:
        print("⚠️  没有数据，跳过同步")
    
    print("=" * 60)
    print("任务完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
