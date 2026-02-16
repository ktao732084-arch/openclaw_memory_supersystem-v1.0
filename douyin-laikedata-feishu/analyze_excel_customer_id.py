#!/usr/bin/env python3
"""
分析原始Excel中的客户ID
"""
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict

excel_file = '/root/客资中心（新）_2026-02-13 15_08_38.616.xlsx'

# 读取共享字符串
with zipfile.ZipFile(excel_file) as zf:
    with zf.open('xl/sharedStrings.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        
        # 提取所有字符串
        ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings = []
        for si in root.findall('.//t', ns):
            if si.text:
                strings.append(si.text)
        
        print(f"共享字符串总数: {len(strings)}\n")
        
        # 字段名（前20个）
        print("字段名（前20个）：")
        for i, s in enumerate(strings[:20]):
            print(f"  {i}: {s}")
        
        # 查找所有可能是客户ID的数字
        print("\n\n查找客户ID模式...")
        customer_ids = []
        for s in strings:
            # 15-17位纯数字
            if s.isdigit() and 15 <= len(s) <= 17:
                customer_ids.append(s)
        
        print(f"\n找到 {len(customer_ids)} 个可能的客户ID")
        
        # 统计
        counter = Counter(customer_ids)
        print(f"\n客户ID分布（前20）：")
        for cid, count in counter.most_common(20):
            print(f"  {cid}: {count}次")
        
        print(f"\n唯一客户ID数: {len(set(customer_ids))}")
        
        # 检查是否有重复
        if len(set(customer_ids)) < 20:
            print("\n⚠️ 客户ID种类太少！")
            print("这些ID可能不是真正的客户唯一标识")
