# 数据去重功能说明

## ✅ 已实现功能

### 1. 去重检查工具 (`dedup.py`)

```bash
# 检查指定日期的重复数据
python3 dedup.py check 2026-02-12

# 清理指定日期的所有数据
python3 dedup.py clean 2026-02-12
```

### 2. 自动去重（集成到 sync_data.py）

同步脚本会自动：
1. 查询飞书中指定日期的现有记录
2. 过滤掉已存在的数据
3. 只写入新数据

## ⚠️ 当前问题

飞书 API 查询记录时，`fields` 字段返回为空，导致无法准确判断重复。

**临时解决方案**：
- 使用 `dedup.py clean` 手动清理重复数据
- 避免对同一天的数据多次运行同步

## 🔧 改进方案

### 方案1：基于记录数量判断
如果某天已有记录，跳过同步：

```python
existing_count = len(get_existing_records(token, date_str))
if existing_count > 0:
    print(f"⚠️  {date_str} 已有 {existing_count} 条记录，跳过同步")
    return True
```

### 方案2：先删除再写入
每次同步前，先删除该日期的所有旧数据：

```python
# 删除旧数据
delete_records_by_date(token, date_str)

# 写入新数据
sync_to_feishu(data_list)
```

### 方案3：使用本地缓存
记录已同步的日期，避免重复同步：

```json
{
  "synced_dates": [
    "2026-02-11",
    "2026-02-12"
  ]
}
```

## 📝 使用建议

### 日常使用
1. 定时任务每天自动运行一次
2. 如果需要重新同步某天的数据：
   ```bash
   # 先清理
   python3 dedup.py clean 2026-02-11
   
   # 再同步
   python3 sync_data.py
   ```

### 月度导出
月度导出会包含所有数据，可能产生重复：
```bash
# 导出前先清理整个月
for day in {01..12}; do
    echo "yes" | python3 dedup.py clean 2026-02-$day
done

# 然后导出
python3 export_month.py 2026 2
```

## ✅ 已测试场景

1. ✅ 检测重复数据
2. ✅ 清理指定日期的数据
3. ⚠️  自动去重（因API限制，暂时无法完全实现）

## 🎯 下一步

建议实现**方案2：先删除再写入**，这是最可靠的方案。
