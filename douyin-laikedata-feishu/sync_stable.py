#!/usr/bin/env python3
"""
稳定版同步脚本 - 增强错误处理和重试机制
"""
import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os

# 强制刷新输出
sys.stdout.reconfigure(line_buffering=True)

# 导入 token_manager 的自动刷新功能
sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token

# 配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 有数据的账户
ACTIVE_ACCOUNTS = {
    1835880409219083: "郑州天后医疗美容医院有限公司-XL",
    1844477765429641: "DX-郑州天后医疗美容医院",
    1844577767982090: "本地推-ka-郑州天后医疗美容医院有限公司",
    1847370973597827: "菲象_郑州天后_10",
    1848003626326092: "菲象_郑州天后_27",
    1848660180442243: "菲象_郑州天后_新",
    1856270852478087: "郑州天后医疗美容-智慧本地推-1",
}

MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

def log(message):
    """带时间戳的日志"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

def retry_on_failure(func, *args, **kwargs):
    """重试装饰器"""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                log(f"⚠️  尝试 {attempt + 1}/{MAX_RETRIES} 失败: {e}")
                log(f"   等待 {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                log(f"❌ 所有重试失败: {e}")
                raise

def load_access_token():
    """加载 Access Token（自动刷新）"""
    try:
        log("🔑 获取 Access Token（自动检测过期并刷新）...")
        token = get_valid_token()
        if not token:
            log("❌ 无法获取有效 Token，请检查 token_manager.py")
            sys.exit(1)
        log("✅ Token 获取成功")
        return token
    except Exception as e:
        log(f"❌ 无法加载 Token: {e}")
        sys.exit(1)

def get_feishu_token():
    """获取飞书 Token"""
    def _get():
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get('code') == 0:
            return result['tenant_access_token']
        else:
            raise Exception(f"获取飞书 Token 失败: {result}")
    
    return retry_on_failure(_get)

def fetch_promotion_data(account_id, date_str, access_token):
    """获取投放数据"""
    def _fetch():
        params = {
            "local_account_id": account_id,
            "start_date": date_str,
            "end_date": date_str,
            "time_granularity": "TIME_GRANULARITY_DAILY",
            "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
            "page": 1,
            "page_size": 100
        }
        
        url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{requests.compat.urlencode(params)}"
        headers = {"Access-Token": access_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        result = response.json()
        
        if result.get('code') == 0:
            return result['data']['promotion_list']
        else:
            raise Exception(f"获取数据失败: {result}")
    
    return retry_on_failure(_fetch)

def write_to_feishu(records, feishu_token):
    """写入飞书"""
    def _write():
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
        headers = {"Authorization": f"Bearer {feishu_token}", "Content-Type": "application/json"}
        payload = {"records": records}
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if result.get('code') == 0:
            return True
        else:
            raise Exception(f"写入失败: {result}")
    
    return retry_on_failure(_write)

def delete_old_records(date_str, feishu_token):
    """删除指定日期的旧记录"""
    def _delete():
        # 1. 查询指定日期的记录
        search_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
        headers = {"Authorization": f"Bearer {feishu_token}", "Content-Type": "application/json"}
        
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "时间",
                        "operator": "is",
                        "value": [date_str]
                    }
                ]
            },
            "page_size": 500
        }
        
        response = requests.post(search_url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"查询失败: {result}")
        
        records = result.get('data', {}).get('items', [])
        
        if not records:
            log(f"   没有找到 {date_str} 的旧记录")
            return True
        
        log(f"   找到 {len(records)} 条旧记录，准备删除...")
        
        # 2. 删除记录
        record_ids = [r['record_id'] for r in records]
        delete_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete"
        
        # 分批删除（每次最多500条）
        batch_size = 500
        for i in range(0, len(record_ids), batch_size):
            batch = record_ids[i:i+batch_size]
            delete_payload = {"records": batch}
            
            delete_response = requests.post(delete_url, headers=headers, json=delete_payload, timeout=30)
            delete_result = delete_response.json()
            
            if delete_result.get('code') != 0:
                raise Exception(f"删除失败: {delete_result}")
            
            log(f"   已删除 {len(batch)} 条")
        
        return True
    
    return retry_on_failure(_delete)

def run_auto_create_views():
    """运行自动创建视图脚本"""
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "/root/.openclaw/workspace/douyin-laikedata-feishu/auto_create_views.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            log("✅ 视图检查完成")
            return True
        else:
            log(f"⚠️  视图检查失败: {result.stderr}")
            return False
    except Exception as e:
        log(f"⚠️  视图检查出错: {e}")
        return False

def main():
    log("=" * 60)
    log("开始同步 - 稳定版")
    log("=" * 60)
    
    # 1. 加载 Token
    log("步骤1: 加载巨量引擎 Token...")
    access_token = load_access_token()
    log("✅ Token 加载成功")
    
    # 2. 获取飞书 Token
    log("\n步骤2: 获取飞书 Token...")
    feishu_token = get_feishu_token()
    log("✅ 飞书 Token 获取成功")
    
    # 3. 确定同步日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    log(f"\n步骤3: 同步日期 = {yesterday}")
    
    # 4. 获取数据
    log(f"\n步骤4: 获取投放数据（{len(ACTIVE_ACCOUNTS)} 个账户）...")
    all_data = []
    success_count = 0
    
    for account_id, account_name in ACTIVE_ACCOUNTS.items():
        try:
            log(f"  获取: {account_name}")
            data_list = fetch_promotion_data(account_id, yesterday, access_token)
            
            if data_list:
                log(f"    ✅ {len(data_list)} 条")
                for item in data_list:
                    all_data.append({
                        "account_id": account_id,
                        "account_name": account_name,
                        "data": item
                    })
                success_count += 1
            else:
                log(f"    ⚠️  无数据")
        except Exception as e:
            log(f"    ❌ 失败: {e}")
    
    log(f"\n✅ 成功获取 {success_count}/{len(ACTIVE_ACCOUNTS)} 个账户的数据")
    log(f"   总记录数: {len(all_data)}")
    
    # 5. 删除当天的旧数据（避免重复）
    if all_data:
        log(f"\n步骤5: 检查并删除当天的旧数据...")
        try:
            delete_old_records(yesterday, feishu_token)
            log(f"✅ 旧数据清理完成")
        except Exception as e:
            log(f"⚠️  清理旧数据失败: {e}")
    
    # 6. 写入飞书
    if all_data:
        log(f"\n步骤6: 写入飞书...")
        records = []
        for item in all_data:
            data = item['data']
            records.append({
                "fields": {
                    "账户名称": item['account_name'],
                    "时间": yesterday,
                    "单元ID": str(data.get('promotion_id', '')),
                    "单元名称": data.get('promotion_name', ''),
                    "消耗(元)": str(data.get('stat_cost', 0)),
                    "转化数": str(data.get('convert_cnt', 0)),
                    "转化成本(元)": str(data.get('convert_cost', 0)),
                    "团购线索数": str(data.get('clue_pay_order_cnt', 0))
                }
            })
        
        try:
            write_to_feishu(records, feishu_token)
            log(f"✅ 写入成功: {len(records)} 条")
        except Exception as e:
            log(f"❌ 写入失败: {e}")
            sys.exit(1)
    else:
        log("\n⚠️  没有数据需要写入")
    
    # 7. 自动创建视图
    log(f"\n步骤7: 检查新账户视图...")
    run_auto_create_views()
    
    log("\n" + "=" * 60)
    log("✅ 同步完成")
    log("=" * 60)

if __name__ == "__main__":
    try:
        # 记录开始
        try:
            from monitor import log_execution
            log_execution("info", "开始执行定时同步任务")
        except:
            pass
        
        main()
        
        # 记录成功
        try:
            from monitor import log_execution
            log_execution("success", "定时同步任务执行成功")
        except:
            pass
    except Exception as e:
        log(f"❌ 同步失败: {e}")
        
        # 记录失败
        try:
            from monitor import log_execution
            log_execution("error", f"定时同步任务执行失败: {e}")
        except:
            pass
        
        sys.exit(1)
