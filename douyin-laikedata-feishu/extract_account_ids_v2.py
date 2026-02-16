#!/usr/bin/env python3
"""
从 Excel 文件提取账户ID（无需额外依赖）
"""
import zipfile
import xml.etree.ElementTree as ET
import re

file_path = '/root/单元投放_账户列表_64763_2026_02_13 00_57_23.xlsx'

print("="*60)
print("读取账户列表 Excel")
print("="*60 + "\n")

try:
    # xlsx 文件本质是 zip 压缩包
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        # 读取共享字符串表
        shared_strings = []
        try:
            with zip_ref.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('.//t', ns):
                    shared_strings.append(si.text if si.text else '')
        except KeyError:
            print("⚠️  没有共享字符串表")
        
        # 读取第一个工作表
        with zip_ref.open('xl/worksheets/sheet1.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # 获取所有行
            rows = root.findall('.//row', ns)
            
            print(f"总行数: {len(rows)}\n")
            
            # 读取前几行查看结构
            print("前5行数据:")
            print("-"*60)
            
            all_data = []
            for i, row in enumerate(rows[:5], 1):
                cells = row.findall('.//c', ns)
                row_data = []
                
                for cell in cells:
                    cell_type = cell.get('t')
                    value_elem = cell.find('.//v', ns)
                    
                    if value_elem is not None:
                        value = value_elem.text
                        
                        # 如果是共享字符串类型
                        if cell_type == 's':
                            try:
                                idx = int(value)
                                value = shared_strings[idx]
                            except (ValueError, IndexError):
                                pass
                        
                        row_data.append(value)
                    else:
                        row_data.append('')
                
                print(f"第{i}行: {row_data}")
                all_data.append(row_data)
            
            print("\n" + "="*60)
            
            # 提取所有数据
            print("提取所有行数据...")
            all_data = []
            
            for row in rows:
                cells = row.findall('.//c', ns)
                row_data = []
                
                for cell in cells:
                    cell_type = cell.get('t')
                    value_elem = cell.find('.//v', ns)
                    
                    if value_elem is not None:
                        value = value_elem.text
                        
                        if cell_type == 's':
                            try:
                                idx = int(value)
                                value = shared_strings[idx]
                            except (ValueError, IndexError):
                                pass
                        
                        row_data.append(value)
                    else:
                        row_data.append('')
                
                all_data.append(row_data)
            
            # 查找包含数字ID的列
            print(f"\n分析 {len(all_data)} 行数据...")
            
            if len(all_data) > 0:
                headers = all_data[0]
                print(f"表头: {headers}\n")
                
                # 查找ID列
                id_col_index = None
                for i, header in enumerate(headers):
                    if header and ('账户id' in str(header) or 'account_id' in str(header).lower() or 'accountid' in str(header).lower()):
                        id_col_index = i
                        print(f"找到ID列: 第{i+1}列 ({header})")
                        break
                
                # 如果没找到，尝试查找包含长数字的列
                if id_col_index is None:
                    print("未找到明确的ID列，尝试查找包含长数字的列...")
                    
                    for col_idx in range(len(headers)):
                        # 检查这一列是否大部分是长数字
                        long_numbers = 0
                        for row in all_data[1:11]:  # 检查前10行
                            if col_idx < len(row):
                                value = row[col_idx]
                                if value and re.match(r'^\d{10,}$', str(value)):
                                    long_numbers += 1
                        
                        if long_numbers >= 5:  # 如果至少5行是长数字
                            id_col_index = col_idx
                            print(f"找到数字列: 第{col_idx+1}列")
                            break
                
                if id_col_index is not None:
                    # 提取账户ID
                    account_ids = []
                    for row in all_data[1:]:  # 跳过表头
                        if id_col_index < len(row):
                            value = row[id_col_index]
                            if value:
                                try:
                                    # 尝试转换为整数
                                    account_id = int(float(value))
                                    if account_id > 1000000:  # 过滤掉太小的数字
                                        account_ids.append(account_id)
                                except (ValueError, TypeError):
                                    pass
                    
                    # 去重
                    account_ids = sorted(set(account_ids))
                    
                    print(f"\n✅ 提取到 {len(account_ids)} 个唯一账户ID\n")
                    
                    print("账户ID列表:")
                    for i, acc_id in enumerate(account_ids[:30], 1):
                        print(f"  {i}. {acc_id}")
                    
                    if len(account_ids) > 30:
                        print(f"  ... 还有 {len(account_ids) - 30} 个")
                    
                    # 保存到文件
                    output_file = '/root/.openclaw/workspace/douyin-laikedata-feishu/account_ids.txt'
                    with open(output_file, 'w') as f:
                        for acc_id in account_ids:
                            f.write(f"{acc_id}\n")
                    
                    print(f"\n💾 已保存到: {output_file}")
                    
                    # 同时保存为 Python 列表格式
                    output_py = '/root/.openclaw/workspace/douyin-laikedata-feishu/account_ids.py'
                    with open(output_py, 'w') as f:
                        f.write("# 账户ID列表\n")
                        f.write("ACCOUNT_IDS = [\n")
                        for acc_id in account_ids:
                            f.write(f"    {acc_id},\n")
                        f.write("]\n")
                    
                    print(f"💾 已保存为 Python 格式: {output_py}")
                else:
                    print("\n❌ 未找到ID列")
                    print("请手动查看 Excel 文件，确认ID在哪一列")
            
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
