# 多账户数据同步 - 配置完成

## 账户信息

✅ **已成功提取 77 个账户ID**

来源：`/root/单元投放_账户列表_64763_2026_02_13 00_57_23.xlsx`

## 文件说明

### 1. 账户ID列表
- `account_ids.txt` - 纯文本格式（每行一个ID）
- `account_ids.py` - Python 格式（可直接导入）
- `active_account_ids.py` - 有数据的账户（扫描后生成）

### 2. 同步脚本
- `multi_account_sync.py` - 多账户批量同步脚本
- `test_multi_accounts.py` - 测试前3个账户
- `scan_all_accounts.py` - 扫描所有账户找出有数据的

### 3. 提取脚本
- `extract_account_ids_v2.py` - 从 Excel 提取账户ID

## 使用方法

### 方法1: 同步所有账户（推荐）

```bash
cd /root/.openclaw/workspace/douyin-laikedata-feishu
python3 multi_account_sync.py
```

这会：
1. 遍历所有77个账户
2. 获取昨天的数据
3. 合并后上传到飞书
4. 自动跳过无数据的账户

### 方法2: 只同步有数据的账户（更快）

等待 `scan_all_accounts.py` 完成后：

```bash
# 编辑 multi_account_sync.py，修改导入
from active_account_ids import ACTIVE_ACCOUNT_IDS as ACCOUNT_IDS

# 运行
python3 multi_account_sync.py
```

### 方法3: 手动指定账户

编辑 `multi_account_sync.py`：

```python
ACCOUNT_IDS = [
    1835880409219083,  # 账户1
    1844477765429641,  # 账户2
    # ... 添加你想同步的账户
]
```

## 定时任务配置

### 更新现有定时任务

```bash
# 1. 备份当前脚本
cp sync_data.py sync_data_single.py

# 2. 将 multi_account_sync.py 重命名为 sync_data.py
# 或者修改 run.sh 调用 multi_account_sync.py

# 3. 测试
python3 multi_account_sync.py

# 4. 如果成功，定时任务会自动使用新脚本
```

### 或者创建新的定时任务

```bash
# 创建新的 cron 任务，专门用于多账户同步
openclaw cron add --name "多账户数据同步" \
  --schedule "0 7 * * *" \
  --command "cd /root/.openclaw/workspace/douyin-laikedata-feishu && python3 multi_account_sync.py"
```

## 预期结果

### 单账户 vs 多账户

**之前（单账户）**:
- 1个账户
- 93个项目
- 每天约4条数据

**现在（多账户）**:
- 77个账户
- 预计每天几十到上百条数据（取决于有多少账户在投放）

### 数据量估算

假设：
- 77个账户中，约10-20个账户每天有投放
- 每个账户平均2-5条数据

预计每天：**20-100条数据**

## 性能优化

### 1. 并发请求（可选）

如果觉得慢，可以修改脚本支持并发：

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(get_account_data, ACCOUNT_IDS)
```

### 2. 只同步有数据的账户

使用 `active_account_ids.py` 可以大幅减少请求次数。

### 3. 缓存无数据的账户

记录哪些账户长期无数据，跳过它们。

## 监控和通知

### 飞书通知

多账户同步会自动发送通知：

```
✅ 数据同步成功

• 日期: 2026-02-12
• 账户数: 77 个
• 成功账户: 15 个
• 总记录数: 45 条
• 总消耗: 5,234.56 元
• 总转化: 38 个
```

### 失败处理

如果某些账户失败：
- 会在通知中列出失败的账户
- 其他账户的数据仍会正常上传
- 不会因为个别账户失败而中断整个流程

## 故障排查

### Q: 扫描很慢？
**A**: 77个账户需要77次API请求，大约2-3分钟。可以使用 `active_account_ids.py` 减少请求。

### Q: 某些账户一直失败？
**A**: 可能原因：
1. 账户未授权
2. 账户已停用
3. 权限不足

可以从 `ACCOUNT_IDS` 中移除这些账户。

### Q: 数据重复？
**A**: 不会。每个单元ID是全局唯一的，不同账户的数据不会重复。

### Q: 想要查看某个账户的数据？
**A**: 
```bash
# 在飞书表格中筛选"单元ID"列
# 或者查看原始数据文件
```

## 下一步

1. ✅ 等待 `scan_all_accounts.py` 完成
2. ✅ 查看有多少账户有数据
3. ✅ 运行 `multi_account_sync.py` 测试
4. ✅ 如果成功，更新定时任务
5. ✅ 配置飞书通知（如果还没配置）

---

**状态**: 配置完成，等待测试
**账户数**: 77 个
**预计数据量**: 每天 20-100 条
