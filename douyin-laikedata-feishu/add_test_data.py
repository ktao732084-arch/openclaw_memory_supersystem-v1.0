#!/usr/bin/env python3
"""
添加测试数据 - 模拟新账户
"""

import requests
from datetime import datetime

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=5)
    return response.json()['tenant_access_token']

def add_test_data():
    """添加测试数据"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试数据：3个新账户，每个账户2条记录
    test_records = [
        # 新账户1：测试医院A
        {
            "fields": {
                "文本": "【测试】郑州测试医院A",
                "时间": "2026-02-13",
                "单元ID": "8888888888888880001",
                "单元名称": "测试单元A-1",
                "消耗(元)": "150.50",
                "转化数": "3",
                "转化成本(元)": "50.17",
                "团购线索数": "2"
            }
        },
        {
            "fields": {
                "文本": "【测试】郑州测试医院A",
                "时间": "2026-02-14",
                "单元ID": "8888888888888880002",
                "单元名称": "测试单元A-2",
                "消耗(元)": "200.00",
                "转化数": "5",
                "转化成本(元)": "40.00",
                "团购线索数": "3"
            }
        },
        # 新账户2：测试医院B
        {
            "fields": {
                "文本": "【测试】郑州测试医院B",
                "时间": "2026-02-13",
                "单元ID": "8888888888888880003",
                "单元名称": "测试单元B-1",
                "消耗(元)": "300.00",
                "转化数": "8",
                "转化成本(元)": "37.50",
                "团购线索数": "5"
            }
        },
        {
            "fields": {
                "文本": "【测试】郑州测试医院B",
                "时间": "2026-02-14",
                "单元ID": "8888888888888880004",
                "单元名称": "测试单元B-2",
                "消耗(元)": "250.00",
                "转化数": "6",
                "转化成本(元)": "41.67",
                "团购线索数": "4"
            }
        },
        # 新账户3：测试医院C
        {
            "fields": {
                "文本": "【测试】郑州测试医院C",
                "时间": "2026-02-13",
                "单元ID": "8888888888888880005",
                "单元名称": "测试单元C-1",
                "消耗(元)": "180.00",
                "转化数": "4",
                "转化成本(元)": "45.00",
                "团购线索数": "3"
            }
        },
        {
            "fields": {
                "文本": "【测试】郑州测试医院C",
                "时间": "2026-02-14",
                "单元ID": "8888888888888880006",
                "单元名称": "测试单元C-2",
                "消耗(元)": "220.00",
                "转化数": "7",
                "转化成本(元)": "31.43",
                "团购线索数": "5"
            }
        }
    ]
    
    data = {"records": test_records}
    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 测试数据已添加")
        print(f"   总共: {len(test_records)} 条记录")
        print(f"   新账户: 3 个")
        print(f"     - 【测试】郑州测试医院A (2条)")
        print(f"     - 【测试】郑州测试医院B (2条)")
        print(f"     - 【测试】郑州测试医院C (2条)")
        return True
    else:
        print(f"❌ 添加失败: {result}")
        return False

def main():
    print("=" * 80)
    print("添加测试数据")
    print("=" * 80)
    
    print("\n正在添加测试数据...")
    if add_test_data():
        print("\n" + "=" * 80)
        print("✅ 测试数据添加完成")
        print("=" * 80)
        
        print("\n下一步:")
        print("1. 运行自动创建视图脚本:")
        print("   python3 auto_create_views.py")
        print("\n2. 检查飞书多维表格:")
        print("   https://ocnbk46uzxq8.feishu.cn/base/FEiCbGEDHarzyUsPG8QcoLxwn7d")
        print("\n3. 验证:")
        print("   - 是否自动创建了3个新视图")
        print("   - 每个视图是否只显示对应账户的数据")
        print("   - 数据是否按日期降序排列")

if __name__ == "__main__":
    main()
