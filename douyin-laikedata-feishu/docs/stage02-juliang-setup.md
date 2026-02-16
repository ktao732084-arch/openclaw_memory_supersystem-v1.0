# 第二阶段：巨量引擎配置

## 完成时间
2026-02-12

## 目标
配置巨量引擎 API 访问权限，确定可用的 API 端点

---

## 实施过程

### 1. 基础配置
- **App ID**: `1856818099350592`
- **App Secret**: `REDACTED`（注意：最初提供的少了最后一个字符 'f'）
- **广告主 ID**: `1769665409798152`
- **本地推账户 ID**: `1835880409219083`

### 2. OAuth 授权流程

#### 第一次授权（失败）
- **auth_code**: `87d690fa5a05042a4861a6c2869719e241dbbb0d`
- **结果**: 权限不足，无法访问 `/campaign/get/` 和 `/ad/get/`

#### 第二次授权（成功）
- **auth_code**: `REDACTED`
- **权限码**: 增加了 `4` 和 `100000014`
- **Access Token**: `REDACTED`
- **Refresh Token**: `REDACTED`
- **有效期**: 24 小时

### 3. API 端点确定

#### 测试过的端点
| 端点 | 状态 | 原因 |
|------|------|------|
| `/open_api/2/campaign/get/` | ❌ | 权限不足 |
| `/open_api/2/ad/get/` | ❌ | 权限不足 |
| `/open_api/v3.0/local/report/account/get/` | ❌ | 账户ID错误 |
| `/open_api/v3.0/local/report/promotion/get/` | ✅ | **成功！** |

### 4. 成功的 API 调用
```python
url = "https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/"
params = {
    "local_account_id": 1835880409219083,
    "start_date": "2026-02-11",
    "end_date": "2026-02-11",
    "time_granularity": "TIME_GRANULARITY_DAILY",
    "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
    "page": 1,
    "page_size": 100
}
```

### 5. 返回数据示例
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

**测试结果**: 成功获取 4 条单元数据

---

## 关键技术点

### 1. metrics 参数格式
```python
# ❌ 错误：直接传列表
"metrics": ["stat_cost", "show_cnt"]

# ✅ 正确：使用 json.dumps() 转成字符串
"metrics": json.dumps(["stat_cost", "show_cnt"])

# 然后 URL 编码
params = urllib.parse.urlencode(params)
```

### 2. 广告主ID vs 本地推账户ID
- **广告主ID**: `1769665409798152`（公司级别）
- **本地推账户ID**: `1835880409219083`（本地推账户）
- 这两个ID不同，不能混淆

### 3. GET 请求参数编码
```python
import urllib.parse

# 使用 urlencode 自动处理特殊字符
url = f"{base_url}?{urllib.parse.urlencode(params)}"
```

---

## 核心文件
- `get_token.py` - 获取 Access Token
- `get_local_accounts.py` - 获取本地推账户列表
- `test_juliang.py` - 巨量引擎测试（早期版本）
- `test_endpoints.py` - API 端点测试
- `test_local_api.py` - 本地推账户接口测试
- `test_local_post.py` - POST 方法测试
- `test_promotion_api.py` - 单元维度接口测试（成功）✅
- `test_report.py` - 报表接口测试

---

*创建时间: 2026-02-12*
