# 第三阶段：数据获取测试

## 完成时间
2026-02-12

## 目标
测试巨量引擎 API 数据获取功能

---

## API 调用成功

### 请求参数
```python
{
  "local_account_id": 1835880409219083,
  "start_date": "2026-02-11",
  "end_date": "2026-02-11",
  "time_granularity": "TIME_GRANULARITY_DAILY",
  "metrics": ["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"],
  "page": 1,
  "page_size": 100
}
```

### 返回数据示例
```json
{
  "promotion_id": 7604686719380537359,
  "promotion_name": "抗衰超声炮法令纹_02_09",
  "project_id": 7604681945927499811,
  "project_name": "抗衰法令纹_02_09_01",
  "stat_cost": 118.36,
  "show_cnt": 1338,
  "click_cnt": 4,
  "convert_cnt": 1,
  "stat_time_day": "2026-02-11"
}
```

### 测试结果
✅ 成功获取 4 条单元数据

---

## 核心文件
- `test_promotion_api.py` - 单元维度接口测试（成功）

---

*创建时间: 2026-02-12*
