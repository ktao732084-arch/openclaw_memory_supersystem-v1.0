#!/usr/bin/env python3
"""
直接读取Excel单元格中的客户ID
"""
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

excel_file = '/root/客资中心（新）_2026-02-13 15_08_38.616.xlsx'

# 读取worksheet
with zipfile.ZipFile(excel_file) as zf:
    with zf.open('xl/worksheets/sheet1.xml') as f:
        content = f.read().decode('utf-8')
        
        # 查找所有M列的单元格（客户ID在第13列，即M列）
        import re
        
        # 匹配 <c r="M数字"><v>值</v></c> 或 <c r="M数字" s="1"><v>值</v></c>
        pattern = r'<c r="M\d+"[^>]*><v>([^<]+)</v></c>'
        matches = re.findall(pattern, content)
        
        print(f"找到 {len(matches)} 个客户ID值\n")
        
        # 统计
        counter = Counter(matches)
        print(f"唯一客户ID数: {len(counter)}\n")
        
        print("客户ID分布（前20）：")
        for cid, count in counter.most_common(20):
            print(f"  {cid}: {count}次")
        
        # 判断
        if len(counter) < 20:
            print(f"\n⚠️ 警告：只有{len(counter)}个不同的客户ID")
            print("但有2900+条记录，平均每个客户ID有几百条记录")
            print("这明显不正常！")
        else:
            print(f"\n✅ 客户ID看起来正常，有{len(counter)}个不同的值")
