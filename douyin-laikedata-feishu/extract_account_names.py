#!/usr/bin/env python3
"""
从 Excel 提取账户ID和名称的映射关系
"""
import zipfile
import xml.etree.ElementTree as ET

file_path = '/root/单元投放_账户列表_64763_2026_02_13 00_57_23.xlsx'

print("="*60)
print("提取账户ID和名称映射")
print("="*60 + "\n")

try:
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
            
            rows = root.findall('.//row', ns)
            
            # 提取所有数据
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
            
            # 跳过表头，提取账户名称和ID
            account_map = {}
            for row in all_data[1:]:  # 跳过表头
                if len(row) >= 2:
                    account_name = row[0]  # 第1列：账户名称
                    account_id = row[1]    # 第2列：账户ID
                    
                    if account_id:
                        try:
                            account_id_int = int(float(account_id))
                            if account_id_int > 1000000:
                                account_map[account_id_int] = account_name
                        except (ValueError, TypeError):
                            pass
            
            print(f"✅ 提取到 {len(account_map)} 个账户映射\n")
            
            # 显示前10个
            print("账户映射示例:")
            for i, (acc_id, acc_name) in enumerate(list(account_map.items())[:10], 1):
                print(f"  {i}. {acc_id} → {acc_name}")
            
            if len(account_map) > 10:
                print(f"  ... 还有 {len(account_map) - 10} 个")
            
            # 保存为 Python 字典
            output_py = '/root/.openclaw/workspace/douyin-laikedata-feishu/account_names.py'
            with open(output_py, 'w', encoding='utf-8') as f:
                f.write("# 账户ID到名称的映射\n")
                f.write("# 从 Excel 自动提取\n")
                f.write("ACCOUNT_NAMES = {\n")
                for acc_id, acc_name in sorted(account_map.items()):
                    # 转义单引号
                    acc_name_escaped = acc_name.replace("'", "\\'")
                    f.write(f"    {acc_id}: '{acc_name_escaped}',\n")
                f.write("}\n")
            
            print(f"\n💾 已保存到: {output_py}")
            
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
