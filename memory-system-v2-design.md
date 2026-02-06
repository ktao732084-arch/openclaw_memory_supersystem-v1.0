# Memory System v2.0 设计方案
## QMD + mem0 + Consolidation 混合架构

**设计日期**: 2026-02-05  
**目标**: 结合三者优势，打造轻量级但功能完整的记忆系统

---

## 🎯 核心理念

### 三层架构
```
┌─────────────────────────────────────────┐
│  Layer 3: 智能整理层 (Consolidation)     │
│  - 7 Phase 自动整理                      │
│  - Fact/Belief 分类                      │
│  - 自动衰减                              │
│  - 元认知                                │
└─────────────────────────────────────────┘
              ↓ 整理后的记忆
┌─────────────────────────────────────────┐
│  Layer 2: 管理层 (mem0-inspired)         │
│  - 记忆过期机制                          │
│  - 访问频率追踪                          │
│  - 自定义标签系统                        │
│  - 实体关系图                            │
└─────────────────────────────────────────┘
              ↓ 元数据 + 索引
┌─────────────────────────────────────────┐
│  Layer 1: 检索层 (QMD)                   │
│  - BM25 关键词搜索                       │
│  - 向量语义搜索                          │
│  - 混合搜索 + 重排序                     │
└─────────────────────────────────────────┘
```

---

## 📦 数据结构设计

### 1. 记忆条目 (Memory Entry)

```json
{
  "id": "mem_20260205_001",
  "type": "fact|belief|summary|event",
  "content": "Ktao 喜欢轻松互动风格，希望在生活各方面得到帮助",
  "source": "conversation|consolidation|manual",
  "created_at": "2026-02-05T13:00:00Z",
  "updated_at": "2026-02-05T13:00:00Z",
  "expires_at": null,  // mem0: 过期时间（null = 永不过期）
  "decay_rate": 0.95,  // v1.0: 衰减率
  "access_log": [      // mem0: 访问日志
    {
      "timestamp": "2026-02-05T14:00:00Z",
      "context": "回答关于交互风格的问题"
    }
  ],
  "access_count": 5,   // mem0: 访问次数
  "last_accessed": "2026-02-05T14:00:00Z",
  "tags": ["user_preference", "interaction_style"],  // mem0: 自定义标签
  "entities": ["Ktao"],  // mem0: 实体提取
  "relations": [         // mem0: 关系图
    {
      "type": "prefers",
      "target": "casual_interaction"
    }
  ],
  "confidence": 0.95,  // v1.0: 置信度
  "importance": 0.9,   // v1.0: 重要性
  "qmd_doc_id": "#8186ee"  // QMD 文档 ID
}
```

### 2. 访问日志 (Access Log)

```json
{
  "memory_id": "mem_20260205_001",
  "timestamp": "2026-02-05T14:00:00Z",
  "query": "Ktao的交互风格是什么？",
  "context": "用户询问交互偏好",
  "retrieval_score": 0.92,
  "used_in_response": true
}
```

### 3. 实体关系图 (Entity Graph)

```json
{
  "entities": {
    "Ktao": {
      "type": "person",
      "aliases": ["张玉魁", "Zhang Yukui"],
      "attributes": {
        "role": "human",
        "timezone": "GMT+8"
      }
    },
    "Tkao": {
      "type": "agent",
      "attributes": {
        "role": "digital_companion"
      }
    }
  },
  "relations": [
    {
      "from": "Tkao",
      "to": "Ktao",
      "type": "assists",
      "strength": 1.0
    },
    {
      "from": "Ktao",
      "to": "casual_interaction",
      "type": "prefers",
      "strength": 0.9
    }
  ]
}
```

---

## 🔄 工作流程

### A. 记忆写入流程

```
用户输入/对话
    ↓
[Phase 1] 实时提取
    ↓
创建 Memory Entry
    ↓
[mem0] 添加元数据（标签、实体、关系）
    ↓
[QMD] 写入 Markdown 文件 + 索引
    ↓
[mem0] 记录创建日志
```

### B. 记忆检索流程

```
用户查询
    ↓
[QMD] 混合搜索（BM25 + 向量 + 重排序）
    ↓
[mem0] 过滤过期记忆
    ↓
[mem0] 应用访问频率加成
    ↓
[v1.0] 应用衰减计算
    ↓
[mem0] 记录访问日志
    ↓
返回排序后的结果
```

### C. 记忆整理流程（Consolidation）

```
定期触发（每日/每周）
    ↓
[Phase 1] 收集原始记忆
    ↓
[Phase 2] 规则过滤（去重、冲突检测）
    ↓
[Phase 3] 模板提取（结构化）
    ↓
[Phase 4a] LLM 分类（Fact/Belief）
    ↓
[Phase 4b] 代码验证（Belief 验证）
    ↓
[Phase 5] 排名（重要性 + 访问频率）
    ↓
[Phase 6] 衰减更新
    ↓
[Phase 7] 写回 MEMORY.md
    ↓
[QMD] 重新索引
    ↓
[mem0] 更新实体关系图
```

---

## 🛠️ 技术实现

### 文件结构

```
/root/.openclaw/workspace/
├── MEMORY.md                    # 主记忆文件（人类可读）
├── memory/
│   ├── YYYY-MM-DD.md           # 每日原始记忆
│   ├── .metadata/              # mem0 元数据
│   │   ├── access_log.jsonl   # 访问日志
│   │   ├── entities.json      # 实体库
│   │   ├── relations.json     # 关系图
│   │   └── tags.json          # 标签索引
│   └── .qmd/                   # QMD 索引（自动生成）
└── memory_system/
    ├── consolidation.py        # v1.0 整理脚本
    ├── mem0_manager.py         # mem0 管理器（新增）
    └── qmd_interface.py        # QMD 接口（新增）
```

### 核心模块

#### 1. mem0_manager.py

```python
class Mem0Manager:
    """mem0 风格的记忆管理器"""
    
    def add_memory(self, content, type, tags=[], entities=[], expires_at=None):
        """添加记忆"""
        pass
    
    def get_memory(self, memory_id):
        """获取记忆（记录访问）"""
        pass
    
    def search_by_tag(self, tag):
        """按标签搜索"""
        pass
    
    def search_by_entity(self, entity):
        """按实体搜索"""
        pass
    
    def get_related_memories(self, memory_id, max_hops=2):
        """图查询：获取相关记忆"""
        pass
    
    def update_access_log(self, memory_id, query, context):
        """更新访问日志"""
        pass
    
    def apply_access_boost(self, memories):
        """应用访问频率加成"""
        pass
    
    def expire_old_memories(self):
        """清理过期记忆"""
        pass
    
    def extract_entities(self, content):
        """提取实体（规则 + LLM）"""
        pass
    
    def build_relation_graph(self):
        """构建实体关系图"""
        pass
```

#### 2. qmd_interface.py

```python
class QMDInterface:
    """QMD 检索接口"""
    
    def index_memory(self, file_path):
        """索引记忆文件"""
        pass
    
    def search(self, query, mode="hybrid"):
        """搜索记忆
        mode: bm25 | vector | hybrid
        """
        pass
    
    def rerank(self, results, query):
        """重排序结果"""
        pass
    
    def get_document(self, doc_id):
        """获取文档内容"""
        pass
```

#### 3. 整合到 consolidation.py

```python
# 在 Phase 5 排名时，结合访问频率
def phase5_rank(memories, mem0_manager):
    for mem in memories:
        # 原有分数
        base_score = mem['importance'] * mem['confidence']
        
        # mem0 访问频率加成
        access_boost = mem0_manager.get_access_boost(mem['id'])
        
        # 最终分数
        mem['final_score'] = base_score * (1 + access_boost)
    
    return sorted(memories, key=lambda x: x['final_score'], reverse=True)

# 在 Phase 6 衰减时，考虑访问时间
def phase6_decay(memories, mem0_manager):
    for mem in memories:
        days_since_access = mem0_manager.days_since_last_access(mem['id'])
        
        # 最近访问过的记忆衰减慢
        if days_since_access < 7:
            decay_factor = 0.99  # 几乎不衰减
        else:
            decay_factor = mem['decay_rate']
        
        mem['confidence'] *= decay_factor
```

---

## 🎯 v2.0 新增功能

### 1. 记忆过期机制

```python
# 时间敏感记忆示例
{
  "content": "明天下午3点有会议",
  "type": "event",
  "expires_at": "2026-02-06T15:00:00Z"  # 会议结束后过期
}

# 定期清理
mem0_manager.expire_old_memories()
```

### 2. 访问频率追踪

```python
# 每次检索时记录
mem0_manager.update_access_log(
    memory_id="mem_001",
    query="Ktao的交互风格",
    context="用户询问"
)

# 检索时应用加成
results = qmd.search("交互风格")
boosted_results = mem0_manager.apply_access_boost(results)
```

### 3. 自定义标签

```python
# 添加记忆时打标签
mem0_manager.add_memory(
    content="Ktao喜欢轻松互动",
    tags=["user_preference", "interaction_style", "high_priority"]
)

# 按标签检索
prefs = mem0_manager.search_by_tag("user_preference")
```

### 4. 实体关系图

```python
# 查询相关记忆（图遍历）
related = mem0_manager.get_related_memories(
    memory_id="mem_001",
    max_hops=2  # 最多2跳
)

# 示例：
# mem_001: "Ktao喜欢轻松互动"
#   → 关系: Ktao prefers casual_interaction
#     → 相关: "Tkao应该使用轻松风格"
#       → 相关: "避免正式用语"
```

---

## 📊 性能优化

### 1. 分层缓存

```python
# L1: 内存缓存（最近访问的记忆）
recent_cache = LRUCache(maxsize=100)

# L2: QMD 索引（快速检索）
qmd_index = QMDInterface()

# L3: 文件系统（完整记忆）
memory_files = "/root/.openclaw/workspace/memory/"
```

### 2. 增量索引

```python
# 只索引新增/修改的记忆
def incremental_index():
    last_indexed = load_checkpoint()
    new_memories = get_memories_since(last_indexed)
    qmd.index_memory(new_memories)
    save_checkpoint(now())
```

### 3. 异步整理

```python
# Consolidation 在后台运行，不阻塞检索
import asyncio

async def consolidate_async():
    await asyncio.sleep(3600)  # 每小时一次
    consolidation.run()
```

---

## 🚀 实施计划

### Phase 1: 基础设施（1-2天）
- [ ] 实现 `mem0_manager.py`（基础功能）
- [ ] 实现 `qmd_interface.py`
- [ ] 设计元数据文件格式

### Phase 2: 核心功能（2-3天）
- [ ] 记忆过期机制
- [ ] 访问日志追踪
- [ ] 自定义标签系统

### Phase 3: 高级功能（3-5天）
- [ ] 实体提取（规则 + LLM）
- [ ] 关系图构建
- [ ] 图查询实现

### Phase 4: 整合（2-3天）
- [ ] 整合到 consolidation.py
- [ ] 整合到 OpenClaw memory_search
- [ ] 测试完整流程

### Phase 5: 优化（持续）
- [ ] 性能优化
- [ ] 文档完善
- [ ] 社区反馈迭代

---

## 💡 关键设计决策

### 1. 为什么不直接用 mem0？

**mem0 的问题：**
- 依赖向量数据库（Qdrant/Chroma/Pinecone）
- 需要额外服务运行
- 配置复杂

**我们的方案：**
- QMD 提供本地向量搜索（无需额外服务）
- 文件系统存储（轻量级）
- 保留 mem0 的优秀设计理念

### 2. 为什么保留 Consolidation？

**mem0 没有的：**
- 自动整理和去重
- Fact/Belief 分类
- 元认知能力

**我们的优势：**
- 7 Phase 自动整理
- 规则优先 + LLM 兜底
- 自动衰减机制

### 3. 为什么用 QMD？

**优势：**
- 本地运行，无 API 成本
- 混合搜索（BM25 + 向量）
- 自带重排序
- 轻量级（Bun + SQLite）

---

## 📝 总结

**v2.0 = v1.0 + mem0 精华 + QMD 检索**

| 功能 | v1.0 | mem0 | v2.0 |
|------|------|------|------|
| 自动整理 | ✅ | ❌ | ✅ |
| Fact/Belief | ✅ | ❌ | ✅ |
| 自动衰减 | ✅ | ❌ | ✅ |
| 记忆过期 | ❌ | ✅ | ✅ |
| 访问追踪 | ❌ | ✅ | ✅ |
| 自定义标签 | ❌ | ✅ | ✅ |
| 实体关系 | ❌ | ✅ | ✅ |
| 混合搜索 | ❌ | ✅ | ✅ |
| 本地运行 | ✅ | ❌ | ✅ |
| 轻量级 | ✅ | ❌ | ✅ |

**核心优势：**
- 保留 v1.0 的智能整理能力
- 吸收 mem0 的工程化设计
- 使用 QMD 实现高效检索
- 完全本地运行，零 API 成本

---

**下一步：开始实现 Phase 1？**
