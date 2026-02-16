# 飞书多维表格自动化方案

## 方案概述

利用飞书多维表格的**自动化（Automation）**功能，实现：
1. 检测到新数据写入 → 自动触发
2. 自动匹配客资数据
3. 自动更新统计字段

---

## 方案一：使用飞书自动化（推荐）

### 架构设计

**表1：投放数据表**
- 基础字段（账户、日期、单元ID等）
- 统计字段（客资数量、获客成本等）

**表2：客资数据表**
- 客资明细（手机号、单元ID、日期等）

**自动化流程**：
```
触发器：投放数据表新增记录
↓
动作1：查询客资数据表（匹配单元ID + 日期）
↓
动作2：统计客资数量
↓
动作3：更新投放数据表的统计字段
```

### 配置步骤

#### 第一步：创建客资数据表

1. 在多维表格中创建新表格"客资数据"
2. 字段：
   - 手机号（文本）
   - 单元ID前15位（文本）
   - 日期（日期）
   - 客户姓名（文本）

#### 第二步：配置自动化

1. **打开自动化面板**
   - 点击多维表格右上角"自动化"按钮
   - 点击"创建自动化"

2. **设置触发器**
   - 触发器类型：**记录创建时**
   - 选择表格：投放数据表
   - 触发条件：无（所有新记录都触发）

3. **添加动作1：查询客资数据**
   - 动作类型：**查找记录**
   - 查找表格：客资数据表
   - 筛选条件：
     - `单元ID前15位` = `LEFT(触发记录.单元ID, 15)`
     - `日期` = `触发记录.日期`
   - 返回结果：所有匹配记录

4. **添加动作2：统计客资数量**
   - 动作类型：**更新记录**
   - 更新表格：投放数据表
   - 更新记录：触发记录
   - 更新字段：
     - `客资数量` = `COUNT(动作1.结果)`
     - `实际获客成本` = `触发记录.消耗(元) / 客资数量`（如果客资数量>0）
     - `客资转化率(%)` = `(触发记录.转化数 / 客资数量) * 100`（如果客资数量>0）

5. **保存并启用**
   - 命名：投放数据自动统计客资
   - 启用自动化

---

## 方案二：使用飞书机器人 + Webhook（更灵活）

### 架构设计

```
脚本写入数据 → 飞书多维表格
                    ↓
            触发 Webhook
                    ↓
            自定义服务器处理
                    ↓
            回写统计数据
```

### 配置步骤

#### 第一步：创建飞书机器人

1. 进入飞书开放平台
2. 创建自建应用
3. 添加权限：
   - `bitable:app`（多维表格读写）
4. 获取 App ID 和 App Secret

#### 第二步：配置 Webhook

1. 在多维表格中打开"自动化"
2. 创建自动化：
   - 触发器：记录创建时
   - 动作：发送 Webhook
   - Webhook URL：你的服务器地址
   - 请求体：
     ```json
     {
       "record_id": "{{触发记录.记录ID}}",
       "unit_id": "{{触发记录.单元ID}}",
       "date": "{{触发记录.日期}}",
       "cost": "{{触发记录.消耗(元)}}",
       "convert": "{{触发记录.转化数}}"
     }
     ```

#### 第三步：创建处理服务

**webhook_handler.py**（部署在服务器上）
```python
#!/usr/bin/env python3
"""
Webhook 处理服务
"""
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# 飞书配置
FEISHU_APP_ID = "your_app_id"
FEISHU_APP_SECRET = "your_app_secret"
FEISHU_APP_TOKEN = "your_app_token"
FEISHU_TABLE_ID = "your_table_id"
FEISHU_KEZI_TABLE_ID = "your_kezi_table_id"

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload)
    return resp.json()['tenant_access_token']

def count_kezi(unit_id, date):
    """统计客资数量"""
    token = get_feishu_token()
    
    # 查询客资数据
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_KEZI_TABLE_ID}/records/search"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 构建筛选条件
    filter_conditions = {
        "conjunction": "and",
        "conditions": [
            {
                "field_name": "单元ID前15位",
                "operator": "is",
                "value": [unit_id[:15]]
            },
            {
                "field_name": "日期",
                "operator": "is",
                "value": [date]
            }
        ]
    }
    
    payload = {
        "filter": filter_conditions,
        "page_size": 500
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    result = resp.json()
    
    if result.get('code') == 0:
        return len(result['data']['items'])
    else:
        return 0

def update_record(record_id, kezi_count, cost, convert):
    """更新记录的统计字段"""
    token = get_feishu_token()
    
    # 计算统计指标
    actual_cost = cost / kezi_count if kezi_count > 0 else 0
    conversion_rate = (convert / kezi_count * 100) if kezi_count > 0 else 0
    
    # 更新记录
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/{record_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "fields": {
            "客资数量": str(kezi_count),
            "实际获客成本": str(round(actual_cost, 2)),
            "客资转化率(%)": str(round(conversion_rate, 2))
        }
    }
    
    resp = requests.put(url, headers=headers, json=payload)
    return resp.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    """处理 Webhook 请求"""
    data = request.json
    
    # 提取数据
    record_id = data.get('record_id')
    unit_id = data.get('unit_id')
    date = data.get('date')
    cost = float(data.get('cost', 0))
    convert = int(data.get('convert', 0))
    
    # 统计客资数量
    kezi_count = count_kezi(unit_id, date)
    
    # 更新记录
    result = update_record(record_id, kezi_count, cost, convert)
    
    return jsonify({
        "success": True,
        "kezi_count": kezi_count,
        "result": result
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## 方案三：使用飞书公式字段（最简单）

### 原理

飞书多维表格的**公式字段**会自动计算，无需手动触发。

### 配置步骤

#### 1. 在投放数据表中添加公式字段

**客资数量**（公式字段）：
```
COUNTIFS(
  客资数据.单元ID前15位, 
  LEFT(单元ID, 15),
  客资数据.日期, 
  日期
)
```

**实际获客成本**（公式字段）：
```
IF(客资数量 > 0, 消耗(元) / 客资数量, 0)
```

**客资转化率(%)**（公式字段）：
```
IF(客资数量 > 0, (转化数 / 客资数量) * 100, 0)
```

#### 2. 工作原理

- 当投放数据表新增记录时，公式字段**自动计算**
- 当客资数据表更新时，投放数据表的公式字段**自动重新计算**
- 无需任何手动操作或自动化流程

#### 3. 优势

✅ **零配置**：只需添加公式字段
✅ **实时更新**：数据变动立即生效
✅ **无需服务器**：完全在飞书内部完成
✅ **性能好**：飞书内部优化

---

## 三种方案对比

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **方案一：飞书自动化** | 可视化配置，易于理解 | 功能有限，复杂逻辑难实现 | 简单的统计计算 |
| **方案二：Webhook** | 灵活性高，可自定义逻辑 | 需要服务器，维护成本高 | 复杂业务逻辑 |
| **方案三：公式字段** | 最简单，零配置，实时更新 | 只能做简单计算 | 大部分统计场景 |

---

## 推荐方案：方案三（公式字段）

### 理由

1. ✅ **最简单**：只需添加3个公式字段
2. ✅ **最稳定**：飞书内置功能，不依赖外部服务
3. ✅ **最快速**：实时计算，无延迟
4. ✅ **零成本**：无需服务器，无需维护

### 实施步骤

1. **创建客资数据表**（5分钟）
2. **添加公式字段**（10分钟）
3. **修改同步脚本**（15分钟）
4. **测试验证**（10分钟）

**总计：40分钟完成**

---

## 下一步

需要我帮你：
1. ✅ 创建客资数据表？
2. ✅ 配置公式字段？
3. ✅ 修改同步脚本？

选择哪个方案？我推荐**方案三（公式字段）**，最简单高效。
