# 抖音来客API接入指南

## 现状分析

**已确认：客资数据在独立的"抖音来客"系统，不在巨量引擎**

- ✅ 巨量引擎：投放数据（消耗、曝光、点击）
- ❌ 巨量引擎：无法获取客资详情（电话等）
- ✅ 抖音来客：客资数据（电话、表单、私信）

## 抖音来客API接入步骤

### 第一步：确认账号权限

**在抖音来客商家后台检查：**

1. 访问：https://life.douyin.com （抖音来客商家后台）
2. 用你的抖音账号登录
3. 检查是否能看到"客资管理"菜单
4. 如果能看到，说明有权限；看不到则需要申请

### 第二步：申请开放平台权限

**访问抖音来客开放平台：**

1. 地址：https://open-life.douyin.com
2. 用抖音来客商家账号登录
3. 创建应用
4. 申请权限：
   - `goodlife.leads` - 线索管理
   - `goodlife.data` - 经营数据

**审核时间：** 1-3个工作日

### 第三步：获取配置信息

**审核通过后，获取：**

```
LIFE_APP_ID=你的来客AppID
LIFE_APP_SECRET=你的来客AppSecret
LIFE_ACCOUNT_ID=你的来客账户ID（后台右上角查看）
```

### 第四步：OAuth授权

**授权流程：**

```python
# 1. 生成授权URL
auth_url = f"https://open.douyin.com/platform/oauth/connect/?client_key={LIFE_APP_ID}&response_type=code&scope=goodlife.leads,goodlife.data&redirect_uri={REDIRECT_URI}"

# 2. 用户访问授权URL，同意后获取code

# 3. 用code换取access_token
token_url = "https://open.douyin.com/oauth/access_token/"
payload = {
    "client_key": LIFE_APP_ID,
    "client_secret": LIFE_APP_SECRET,
    "code": auth_code,
    "grant_type": "authorization_code"
}
```

### 第五步：获取客资数据

**核心接口：**

```python
# 获取客资列表
url = "https://open.douyin.com/goodlife/v1/leads/list"

headers = {"access-token": access_token}

params = {
    "account_id": LIFE_ACCOUNT_ID,
    "start_time": "2026-02-11 00:00:00",
    "end_time": "2026-02-11 23:59:59",
    "page": 1,
    "page_size": 100
}

resp = requests.get(url, headers=headers, params=params)
```

**返回数据示例：**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "leads_id": "线索ID",
      "ad_id": "7604686719380537359",  // ← 关联字段：与巨量的单元ID匹配
      "campaign_id": "计划ID",
      "create_time": "2026-02-11 10:30:00",
      "telephone": "13800138000",
      "clue_type": "FORM",  // FORM/PHONE/PRIVATE_MSG
      "clue_status": 0,     // 0:新线索, 1:跟进中, 2:已转化
      "intention_poi_name": "门店名称",
      "user_name": "客户姓名",
      "remark": "客户留言"
    }
  ]
}
```

## 数据关联方案

**通过 ad_id（单元ID）关联：**

```
巨量本地推数据                抖音来客客资数据
├─ ad_id: 7604686719380537359  ←→  ad_id: 7604686719380537359
├─ 单元名称: 抗衰超声炮法令纹      ├─ 客户电话: 13800138000
├─ 消耗: 118.36元                ├─ 客户姓名: 张三
├─ 转化数: 1                     └─ 线索状态: 新线索
└─ 转化成本: 118.36元
```

## 快速验证方案

**在正式接入前，先确认：**

1. 你能否登录 https://life.douyin.com
2. 能否看到"客资管理"菜单
3. 客资数据里是否有 ad_id 字段

**验证方法：**
- 在抖音来客后台手动导出一份客资数据
- 检查是否包含广告单元ID
- 确认能否与巨量数据匹配

## 当前建议

**优先级1：** 确认你是否有抖音来客商家后台访问权限
**优先级2：** 如果有，申请开放平台API权限
**优先级3：** 等待审核通过后，我帮你实现完整的数据关联

---

**需要你提供的信息：**

1. 能否访问 https://life.douyin.com ？
2. 能否看到"客资管理"菜单？
3. 是否愿意申请开放平台权限（需要1-3天审核）？

如果以上都不行，我们可以考虑其他方案（比如手动导出客资数据，定期上传）。
