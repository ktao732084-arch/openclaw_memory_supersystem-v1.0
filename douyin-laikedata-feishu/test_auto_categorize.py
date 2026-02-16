#!/usr/bin/env python3
"""
测试新增数据是否自动归类到对应视图
"""

import requests
from datetime import datetime

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=5)
    return response.json()['tenant_access_token']

def add_test_record():
    """添加一条测试记录"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试数据
    test_data = {
        "fields": {
            "文本": "郑州天后医疗美容医院有限公司-XL",  # 账户名称
            "时间": "2026-02-14",  # 今天
            "单元ID": "9999999999999999999",  # 测试ID
            "单元名称": "【测试】自动归类测试",
            "消耗(元)": "100.00",
            "转化数": "5",
            "转化成本(元)": "20.00",
            "团购线索数": "3"
        }
    }
    
    response = requests.post(url, headers=headers, json=test_data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        record_id = result['data']['record']['record_id']
        print(f"✅ 测试记录已添加")
        print(f"   记录ID: {record_id}")
        print(f"   账户: 郑州天后医疗美容医院有限公司-XL")
        print(f"   日期: 2026-02-14")
        print(f"   单元名称: 【测试】自动归类测试")
        return record_id
    else:
        print(f"❌ 添加失败: {result}")
        return None

def check_record_in_view(record_id, view_id, view_name):
    """检查记录是否在指定视图中"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "view_id": view_id,
        "page_size": 500
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=10)
    records = response.json()['data']['items']
    
    for record in records:
        if record['record_id'] == record_id:
            return True
    return False

def delete_test_record(record_id):
    """删除测试记录"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/{record_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(url, headers=headers, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 测试记录已删除")
        return True
    else:
        print(f"❌ 删除失败: {result}")
        return False

def main():
    print("=" * 80)
    print("测试新增数据自动归类")
    print("=" * 80)
    
    print("\n步骤1: 添加测试记录...")
    record_id = add_test_record()
    
    if not record_id:
        print("❌ 测试失败：无法添加记录")
        return
    
    print("\n步骤2: 检查记录是否在对应视图中...")
    
    # 检查"郑州天后医疗美容医院有限公司-XL"视图
    view_id = "vewZyjDkMa"
    view_name = "郑州天后医疗美容医院有限公司-XL"
    
    print(f"   检查视图: {view_name}")
    
    import time
    time.sleep(2)  # 等待2秒让飞书处理
    
    if check_record_in_view(record_id, view_id, view_name):
        print(f"   ✅ 记录已出现在视图中")
        print(f"   结论: 自动归类功能正常")
    else:
        print(f"   ❌ 记录未出现在视图中")
        print(f"   结论: 需要手动配置视图筛选条件")
    
    print("\n步骤3: 清理测试数据...")
    delete_test_record(record_id)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    print("\n如果自动归类不正常，请手动配置视图筛选条件:")
    print("1. 打开飞书多维表格")
    print("2. 点击视图右上角的'筛选'按钮")
    print("3. 添加筛选条件: 文本 = 对应账户名称")
    print("4. 保存")

if __name__ == "__main__":
    main()
