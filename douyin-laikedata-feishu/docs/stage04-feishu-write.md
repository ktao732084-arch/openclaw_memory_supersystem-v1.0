# 第四阶段：飞书写入

## 完成时间
2026-02-12

## 目标
将巨量引擎数据写入飞书多维表格

---

## 实施过程

### 1. 字段映射问题

#### 初始尝试
使用中文字段名（"日期"、"单元ID"等）→ **失败**（FieldNameNotFound）

#### 第一次调整
使用默认"文本"字段，拼接所有数据 → **成功**

#### 第二次调整
用户手动创建 12 个字段 → **匹配成功**

### 2. 用户创建的字段
```
- 文本 (ID: fld5umiPEI)
- 时间 (ID: fldkyA76nq)
- 单元ID (ID: fldydAOWwz)
- 单元名称 (ID: fldFoTlBuj)
- 项目状态 (ID: fldEstSEEU)
- 投放目的 (ID: fld44NDqTH)
- 项目预算 (ID: fldr28nNNx)
- 单元出价 (ID: fldDhPq9NJ)
- 消耗(元) (ID: fldTeFO3Px)
- 转化数 (ID: flda2u6QRj)
- 转化成本(元) (ID: fldyWapRzm)
- 团购线索数 (ID: fldnOkEnF1)
```

### 3. 字段类型处理
- 所有字段类型都是 `1`（文本类型）
- 需要将所有数据转换为字符串
- 转化成本需要计算：`消耗 / 转化数`

### 4. 最终写入逻辑
```python
record = {
    "fields": {
        "时间": item.get('stat_time_day', ''),
        "单元ID": str(item.get('promotion_id', '')),
        "单元名称": item.get('promotion_name', ''),
        "消耗(元)": str(item.get('stat_cost', 0)),
        "转化数": str(item.get('convert_cnt', 0)),
        "转化成本(元)": str(round(cost / convert, 2)) if convert > 0 else "0",
        "团购线索数": str(item.get('clue_pay_order_cnt', 0))
    }
}
```

### 5. 测试结果
✅ 成功写入 4 条数据

---

## 核心文件
- `check_fields.py` - 查看飞书字段结构
- `sync_data.py` - 主同步脚本（包含写入逻辑）

---

*创建时间: 2026-02-12*
