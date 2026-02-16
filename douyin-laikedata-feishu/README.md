# 抖音来客 - 巨量本地推数据自动同步

## 项目状态
✅ **已完成并运行中**

## 核心功能
- ✅ 每天自动从巨量引擎获取本地推投放数据
- ✅ 自动上传到飞书多维表格
- ✅ **Access Token 自动续期（无需人工干预）** ⭐ 已修复
- ✅ 数据去重机制（避免重复写入）
- ✅ 失败通知（飞书机器人推送）
- ✅ 批量数据下载和导出

## 最近更新
- **2026-02-16**: 🔧 修复 Token 自动刷新问题
  - 问题：定时任务使用的 `sync_stable.py` 没有调用自动刷新逻辑
  - 解决：统一使用 `token_manager.py` 的 `get_valid_token()` 函数
  - 增强：Token 保存验证、详细日志、原子性写入
  - 测试：通过自动刷新测试（`test_token_auto_refresh.py`）

## 配置信息
- **巨量账户ID**: 1835880409219083
- **飞书表格**: FEiCbGEDHarzyUsPG8QcoLxwn7d / tbl1n1PC1aooYdKk
- **执行时间**: 每天早上 7:00（北京时间）
- **数据范围**: 前一天的投放数据

## 获取的数据
- 时间
- 单元ID
- 单元名称
- 消耗(元)
- 转化数
- 转化成本(元)（自动计算）
- 团购线索数

## 快速开始

### 1. 配置飞书通知（可选，5分钟）

**强烈推荐配置！** 同步失败时会自动通知你。

详细步骤见：[失败通知快速配置指南](NOTIFICATION_SETUP.md)

简要步骤：
1. 飞书群聊 → 添加自定义机器人
2. 复制 Webhook URL
3. 添加到 `.env`:
   ```bash
   FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
   ```
4. 测试：`python3 notifier.py`

### 2. 手动执行同步

```bash
cd /root/.openclaw/workspace/douyin-laikedata-feishu
python3 sync_data.py
```

或使用脚本：
```bash
./run.sh
```

### 3. 查看定时任务

已通过 OpenClaw cron 设置，每天早上 7:00 自动执行。

```bash
# 查看任务状态
openclaw cron list

# 手动触发
openclaw cron run <job_id>
```

## 核心工具

### Token 管理
```bash
# 查看 Token 状态
python3 token_manager.py status

# 手动刷新 Token
python3 token_manager.py refresh

# 获取有效 Token
python3 token_manager.py get
```

### 数据去重
```bash
# 检查重复数据
python3 dedup.py check 2026-02-11

# 清理重复数据
python3 dedup.py clean 2026-02-11

# 强制同步（先删除再写入）
python3 force_sync.py 2026-02-11
```

### 批量下载
```bash
# 下载昨天的数据
python3 download_all_data.py

# 批量下载多日数据
python3 batch_download.py 2026-02-01 2026-02-12

# 导出整月数据
python3 export_month.py 2026 2
```

### 通知测试
```bash
# 测试飞书通知
python3 notifier.py
```

## 通知功能

### 你会收到的通知

✅ **同步成功**（每天早上7点后）
- 日期、记录数
- 总消耗、总转化
- 平均转化成本

❌ **同步失败**（出错时）
- 日期、错误信息
- 详细原因、建议操作

⚠️ **Token 刷新失败**（Token 过期时）
- 错误信息
- 需要重新授权提醒

### 配置方法

详见：
- [失败通知快速配置指南](NOTIFICATION_SETUP.md)（5分钟配置）
- [飞书机器人配置教程](飞书机器人配置教程.md)（详细教程）

## 文件说明
- `sync_data.py` - 主同步脚本（已集成Token续期、去重、通知）
- `token_manager.py` - Token 自动续期管理器
- `notifier.py` - 飞书通知模块 ⭐ NEW!
- `dedup.py` - 数据去重工具
- `batch_download.py` - 批量数据下载
- `export_month.py` - 月度数据导出
- `.env` - 配置文件（包含敏感信息，已加入 .gitignore）

## Token 续期

✅ **已实现自动续期（2026-02-16 修复）**

- Access Token 有效期：24 小时
- Refresh Token 有效期：30 天
- 自动检测过期（< 1小时触发刷新）
- 刷新失败会发送飞书通知
- **所有脚本统一使用 `token_manager.get_valid_token()`**

### 工作原理

1. **检测过期**：每次获取 token 时自动检查剩余时间
2. **自动刷新**：剩余时间 < 1小时时自动调用刷新接口
3. **原子保存**：使用临时文件 + 原子重命名，避免写入冲突
4. **保存验证**：写入后立即读取验证，确保数据完整

### 测试自动刷新

```bash
# 运行自动刷新测试
python3 test_token_auto_refresh.py
```

详见：[Token 自动续期说明](TOKEN_AUTO_REFRESH.md)

## 数据去重

✅ **已实现智能去重**

- 同步前自动检测重复数据
- 自动跳过已同步的日期
- 支持强制替换模式
- 提供手动清理工具

详见：[去重功能说明](DEDUP_COMPLETE.md)

## 故障排查

### 1. 同步失败
- 检查是否收到飞书通知（如果已配置）
- 查看控制台错误信息
- 运行 `python3 token_manager.py status` 检查 Token 状态

### 2. Token 过期
- 自动续期失败会收到飞书通知
- 手动刷新：`python3 token_manager.py refresh`
- 如果 Refresh Token 也过期，需要重新授权

### 3. 数据重复
- 运行 `python3 dedup.py check <日期>` 检查
- 运行 `python3 dedup.py clean <日期>` 清理
- 或使用 `python3 force_sync.py <日期>` 强制同步

### 4. 收不到通知
- 检查 `.env` 中的 `FEISHU_WEBHOOK_URL` 是否配置
- 运行 `python3 notifier.py` 测试
- 检查机器人是否在群里

## 文档

- [项目开发日志](PROJECT_LOG.md) - 完整开发过程
- [飞书应用创建教程](飞书应用创建教程.md) - 飞书应用配置
- [飞书机器人配置教程](飞书机器人配置教程.md) - 机器人详细配置
- [失败通知快速配置指南](NOTIFICATION_SETUP.md) - 5分钟快速配置
- [Token 自动续期说明](TOKEN_AUTO_REFRESH.md) - Token 管理机制
- [去重功能说明](DEDUP_COMPLETE.md) - 去重机制说明

## 更新记录
- 2026-02-16: 🔧 修复 Token 自动刷新机制（统一使用 token_manager）⭐
- 2026-02-13: 实现失败通知机制（飞书机器人）
- 2026-02-12: 实现批量下载和月度导出
- 2026-02-12: 实现数据去重机制
- 2026-02-12: 实现 Token 自动续期
- 2026-02-12: 项目创建并完成首次同步

## 技术栈
- Python 3
- 巨量引擎 API v3.0
- 飞书开放平台 API
- OpenClaw Cron

## 联系方式
如有问题，请查看 [PROJECT_LOG.md](PROJECT_LOG.md) 中的详细说明。
