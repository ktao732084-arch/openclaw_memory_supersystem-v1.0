#!/usr/bin/env python3
"""
测试账户名称映射
"""
from account_names import ACCOUNT_NAMES

# 测试数据
test_account_ids = [
    1835880409219083,
    1844477765429641,
    1844577767982090,
    1847370973597827,
    1848003626326092,
    1848660180442243,
    1856270852478087
]

print("测试账户ID → 账户名称映射:\n")
for account_id in test_account_ids:
    account_name = ACCOUNT_NAMES.get(account_id, f"未找到账户{account_id}")
    print(f"{account_id} → {account_name}")

print(f"\n总共有 {len(ACCOUNT_NAMES)} 个账户映射")
