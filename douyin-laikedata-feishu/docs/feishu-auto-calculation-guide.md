# 飞书多维表格自动计算配置指南

## 目标
让飞书多维表格自动处理数据分类和客资统计，脚本只负责写入原始数据。

## 表格架构

### 表1：投放数据表（主表）
**字段列表**：
1. 账户名称（文本）
2. 日期（日期）
3. 单元ID（文本）
4. 单元名称（文本）
5. 消耗(元)（数字）
6. 转化数（数字）
7. 转化成本(元)（公式）
8. 团购线索数（数字）
9. **客资数量（公式）** ← 自动统计
10. **实际获客成本（公式）** ← 自动计算
11. **客资转化率(%)（公式）** ← 自动计算

### 表2：客资数据表（新建）
**字段列表**：
1. 手机号（文本）
2. 单元ID前15位（文本）
3. 日期（日期）
4. 客户姓名（文本）
5. 其他客资字段...

---

## 配置步骤

### 第一步：创建客资数据表

1. 在同一个多维表格中，点击左下角"+"创建新表格
2. 命名为"客资数据"
3. 创建以下字段：
   - **手机号**（文本，必填）
   - **单元ID前15位**（文本，必填）
   - **日期**（日期，必填）
   - **客户姓名**（文本）
   - 其他字段根据需要添加

### 第二步：配置投放数据表的公式字段

#### 1. 客资数量（公式字段）

**公式**：
```
COUNTIFS(
  客资数据.单元ID前15位, LEFT(单元ID, 15),
  客资数据.日期, 日期
)
```

**说明**：
- 统计客资数据表中，单元ID前15位匹配且日期相同的记录数
- `LEFT(单元ID, 15)` 取当前行单元ID的前15位
- 自动去重（按手机号）需要在客资数据表中预处理

#### 2. 实际获客成本（公式字段）

**公式**：
```
IF(客资数量 > 0, 消耗(元) / 客资数量, 0)
```

**说明**：
- 如果客资数量大于0，则计算消耗除以客资数量
- 否则返回0

#### 3. 客资转化率(%)（公式字段）

**公式**：
```
IF(客资数量 > 0, (转化数 / 客资数量) * 100, 0)
```

**说明**：
- 如果客资数量大于0，则计算转化数除以客资数量再乘以100
- 否则返回0

### 第三步：创建视图（按账户分组）

1. 在投放数据表中，点击右上角"视图"
2. 创建新视图，命名为"按账户分组"
3. 配置分组：
   - 分组字段：账户名称
   - 排序：日期（降序）
4. 配置筛选（可选）：
   - 日期：最近30天
   - 消耗(元) > 0

### 第四步：创建仪表盘（可选）

1. 点击多维表格右上角"仪表盘"
2. 添加图表：
   - **柱状图**：各账户消耗对比
   - **折线图**：每日消耗趋势
   - **数字卡片**：总消耗、总客资数、平均获客成本
   - **表格**：客资转化率排行

---

## 脚本修改

### 修改1：投放数据写入（简化）

**原来**：写入12个字段（包括客资数量、实际获客成本等）

**现在**：只写入8个基础字段
```python
record = {
    "fields": {
        "账户名称": account_name,
        "日期": date,
        "单元ID": unit_id,
        "单元名称": unit_name,
        "消耗(元)": cost,
        "转化数": convert,
        "转化成本(元)": cost_per_convert,
        "团购线索数": leads
    }
}
```

**说明**：
- 客资数量、实际获客成本、客资转化率由飞书公式自动计算
- 脚本不再需要统计客资数据

### 修改2：客资数据写入（新增）

**新建脚本**：`upload_kezi_data.py`

```python
#!/usr/bin/env python3
"""
上传客资数据到飞书多维表格
"""
import pandas as pd
import requests
import json

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "YOUR_APP_SECRET_HERE"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_KEZI_TABLE_ID = "tblXXXXXXXXXXXXXX"  # 客资数据表ID

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def upload_kezi_data(excel_path):
    """上传客资数据"""
    # 读取Excel
    df = pd.read_excel(excel_path)
    
    # 数据清洗
    df = df[df['手机号'].notna()]  # 只保留有手机号的
    df = df[df['单元ID'].notna()]  # 只保留有单元ID的
    df['单元ID前15位'] = df['单元ID'].astype(str).str[:15]
    
    # 按手机号去重
    df = df.drop_duplicates(subset=['手机号', '单元ID前15位', '日期'])
    
    # 构建记录
    records = []
    for _, row in df.iterrows():
        record = {
            "fields": {
                "手机号": str(row['手机号']),
                "单元ID前15位": row['单元ID前15位'],
                "日期": row['日期'].strftime('%Y-%m-%d'),
                "客户姓名": str(row.get('客户姓名', ''))
            }
        }
        records.append(record)
    
    # 写入飞书
    token = get_feishu_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_KEZI_TABLE_ID}/records/batch_create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 分批写入（每批500条）
    for i in range(0, len(records), 500):
        batch = records[i:i+500]
        payload = {"records": batch}
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            print(f"✓ 第 {i//500 + 1} 批写入成功: {len(batch)} 条")
        else:
            print(f"✗ 第 {i//500 + 1} 批失败: {result}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("用法: python3 upload_kezi_data.py <Excel文件路径>")
        sys.exit(1)
    
    upload_kezi_data(sys.argv[1])
```

---

## 优势

### 1. 数据分离
- **投放数据**：每天自动同步
- **客资数据**：手动或定期上传
- 互不干扰，易于维护

### 2. 自动计算
- 客资数量、实际获客成本、客资转化率全部自动计算
- 无需脚本处理，减少出错

### 3. 灵活查询
- 通过视图按账户、日期、单元等维度查看
- 通过筛选快速定位问题数据

### 4. 实时更新
- 客资数据更新后，投放数据表的统计字段自动更新
- 无需重新运行脚本

---

## 注意事项

### 1. 客资数据去重
飞书公式的`COUNTIFS`不会自动去重，需要在上传客资数据时预先去重：
```python
df = df.drop_duplicates(subset=['手机号', '单元ID前15位', '日期'])
```

### 2. 单元ID匹配
使用前15位匹配，避免科学计数法问题：
```
LEFT(单元ID, 15)
```

### 3. 性能优化
- 客资数据表建议添加索引（单元ID前15位 + 日期）
- 投放数据表不要超过10000条记录
- 定期归档历史数据

### 4. 公式字段限制
- 飞书公式字段不能跨多维表格引用
- 只能在同一个多维表格的不同表格之间引用
- 确保客资数据表和投放数据表在同一个多维表格中

---

## 测试步骤

### 1. 创建测试数据
在客资数据表中手动添加几条测试数据：
- 手机号：13800138000
- 单元ID前15位：760035116819161
- 日期：2026-02-13
- 客户姓名：测试客户

### 2. 验证公式
在投放数据表中找到对应的记录（单元ID前15位匹配，日期相同），查看：
- 客资数量是否自动更新为1
- 实际获客成本是否自动计算
- 客资转化率是否自动计算

### 3. 批量测试
上传完整的客资数据，验证所有记录的统计字段是否正确。

---

## 常见问题

### Q1: 公式字段显示0或空白？
**A**: 检查以下几点：
1. 客资数据表中是否有匹配的记录
2. 单元ID前15位是否一致
3. 日期格式是否正确
4. 公式语法是否正确

### Q2: 客资数量不准确？
**A**: 可能原因：
1. 客资数据表中有重复记录（需要去重）
2. 单元ID格式不一致（检查是否有空格、换行等）
3. 日期格式不一致

### Q3: 性能问题？
**A**: 优化方案：
1. 减少公式字段的数量
2. 使用视图筛选，只显示需要的数据
3. 定期归档历史数据
4. 考虑使用飞书的"数据同步"功能

---

## 下一步

1. 创建客资数据表
2. 配置公式字段
3. 修改同步脚本（简化字段）
4. 创建客资数据上传脚本
5. 测试验证

需要我帮你实现哪一步？
