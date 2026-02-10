# Memory System + QMD 深度集成设计文档

> **版本**: v1.2.0 设计稿
> **日期**: 2026-02-10
> **状态**: 待实现
> **讨论参与者**: Ktao, Tkao

---

## 一、背景与动机

### 1.1 当前记忆系统的检索短板

记忆系统 v1.1.7 在记忆管理方面表现优秀（分类、衰减、冲突检测），但检索能力有限：

| 能力 | 当前实现 | 问题 |
|------|---------|------|
| 关键词检索 | `keywords.json` 索引 | 无法处理同义词、语义相似 |
| 实体检索 | `relations.json` 索引 | 依赖精确匹配 |
| 语义检索 | 无 | 缺失 |

### 1.2 QMD 的能力

QMD (Quick Memory Dump) 是 OpenClaw 内置的本地优先搜索引擎：

- **BM25 全文搜索**：关键词精确匹配
- **向量语义搜索**：理解同义词和语义相似
- **Reranking 重排序**：优化结果质量
- **本地运行**：无需 API，隐私保护

### 1.3 核心思想

**记忆系统负责"筛选和理解"，QMD 负责"存储和检索"**

形成闭环：
```
记忆系统筛选 → QMD 存储 → QMD 检索 → 记忆系统后处理
```

---

## 二、架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     数据源层                                 │
├─────────────────────────────────────────────────────────────┤
│  Session 历史 (22MB)    日常笔记 (*.md)    手动输入          │
│       ↓                      ↓                  ↓           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              记忆系统 Consolidation（筛选层）                 │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: 读取原始数据                                       │
│  Phase 2: 重要性筛选（过滤闲聊/情绪/临时内容）                │
│  Phase 3: 结构化提取（facts/beliefs/summaries）              │
│  Phase 4: 去重、冲突检测、实体识别                           │
│                                                             │
│  输出：精选记忆 → layer2/active/*.jsonl                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              转换层（新增）                                   │
├─────────────────────────────────────────────────────────────┤
│  JSONL → Markdown 转换                                       │
│                                                             │
│  输入：layer2/active/facts.jsonl                            │
│  输出：layer2/qmd-index/facts.md                            │
│                                                             │
│  格式示例：                                                  │
│  # Facts                                                    │
│  ## f_20260207_a6b928 [importance=1.0]                      │
│  用户名字是张玉魁，称呼Ktao，河南中医药大学临床医学大三学生    │
│  entities: Ktao, 用户                                       │
│  ---                                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    QMD 索引层                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Collection: curated (Tier 1) - 精选记忆                     │
│  ├── layer2/qmd-index/facts.md                              │
│  ├── layer2/qmd-index/beliefs.md                            │
│  └── layer2/qmd-index/summaries.md                          │
│                                                             │
│  Collection: sessions (Tier 2, 可选) - 历史对话兜底          │
│  └── sessions/*.jsonl                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    检索层                                    │
├─────────────────────────────────────────────────────────────┤
│  用户查询                                                    │
│      │                                                      │
│      ▼                                                      │
│  QMD query (BM25 + 向量 + Reranking)                        │
│      │                                                      │
│      ▼                                                      │
│  提取 memory_id → 加载元数据 → 计算综合分数                   │
│      │                                                      │
│      ▼                                                      │
│  格式化注入（Fact 直接用，Belief 带标记）                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流详解

#### 写入流程（Consolidation 时）

```
1. 原始对话 → Phase 1-4 筛选提取
2. 输出 facts.jsonl, beliefs.jsonl, summaries.jsonl
3. 【新增】转换为 QMD 友好的 Markdown 格式
4. 【新增】触发 QMD 更新索引
```

#### 读取流程（检索时）

```
1. 用户查询 → QMD 检索（BM25 + 向量）
2. 返回候选集（Top 30-50）
3. 从 snippet 中提取 memory_id
4. 加载记忆系统元数据（score, importance, type, confidence）
5. 计算综合分数：
   final_score = qmd_score * 0.4 + memory_score * 0.35 + importance * 0.25
6. 按综合分数排序，取 Top 15
7. 格式化注入（Fact 直接用，Belief 带"可能"标记）
```

---

## 三、各系统职责划分

### 3.1 记忆系统职责

| 职责 | 说明 |
|------|------|
| **筛选** | 决定什么值得记（Phase 2 重要性筛选） |
| **分类** | 区分 Fact / Belief / Summary |
| **元数据管理** | 维护 score, importance, confidence, entities |
| **衰减** | 自动降权旧记忆 |
| **冲突检测** | 新旧信息冲突时降权旧记忆 |
| **后处理** | 检索结果的元数据融合和格式化 |

### 3.2 QMD 职责

| 职责 | 说明 |
|------|------|
| **存储** | 索引记忆系统输出的精选内容 |
| **检索** | BM25 + 向量 + Reranking 混合检索 |
| **召回** | 快速返回相关候选集 |

### 3.3 职责边界

```
记忆系统：决定"什么重要"、"什么是确定的"
QMD：决定"什么相关"、"怎么快速找到"
```

---

## 四、实现细节

### 4.1 新增：JSONL → Markdown 转换函数

```python
def export_for_qmd(memory_dir):
    """
    将 JSONL 转换为 QMD 友好的 Markdown 格式
    
    为什么需要转换？
    - QMD 索引整行内容，JSONL 格式会导致 id、score 等字段被索引
    - Markdown 格式更适合 QMD 的分块和检索
    - 可以在 Markdown 中嵌入 memory_id，方便检索后提取
    """
    qmd_index_dir = memory_dir / 'layer2/qmd-index'
    qmd_index_dir.mkdir(parents=True, exist_ok=True)
    
    for mem_type in ['facts', 'beliefs', 'summaries']:
        records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
        
        md_content = f"# {mem_type.title()}\n\n"
        md_content += f"> Generated: {now_iso()} | Count: {len(records)}\n\n"
        
        for r in records:
            # 嵌入 memory_id 和关键元数据，方便检索后提取
            md_content += f"## {r['id']} [score={r.get('score', 0):.2f}, imp={r.get('importance', 0.5):.1f}]\n\n"
            md_content += f"{r['content']}\n\n"
            
            if r.get('entities'):
                md_content += f"**Entities**: {', '.join(r['entities'])}\n\n"
            
            if mem_type == 'beliefs' and r.get('confidence'):
                md_content += f"**Confidence**: {r['confidence']:.2f}\n\n"
            
            md_content += "---\n\n"
        
        output_path = qmd_index_dir / f'{mem_type}.md'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    return qmd_index_dir
```

### 4.2 新增：QMD 检索函数

```python
import subprocess
import os

def qmd_available():
    """检查 QMD 是否可用"""
    try:
        env = _get_qmd_env()
        result = subprocess.run(
            ['qmd', '--version'],
            capture_output=True, timeout=2, env=env
        )
        return result.returncode == 0
    except:
        return False

def _get_qmd_env():
    """获取 QMD 运行环境"""
    home = os.path.expanduser('~')
    return {
        **os.environ,
        'PATH': f"{home}/.bun/bin:{os.environ.get('PATH', '')}",
        'XDG_CONFIG_HOME': f"{home}/.openclaw/agents/main/qmd/xdg-config",
        'XDG_CACHE_HOME': f"{home}/.openclaw/agents/main/qmd/xdg-cache",
        'NO_COLOR': '1',
    }

def qmd_search(query, collection="curated", limit=30):
    """
    使用 QMD 进行混合检索
    
    参数:
        query: 查询字符串
        collection: QMD 集合名称
        limit: 返回结果数量
    
    返回:
        [{"docid": ..., "score": ..., "snippet": ..., "file": ...}, ...]
        或 None（如果 QMD 不可用）
    """
    try:
        env = _get_qmd_env()
        
        # 优先使用 query（混合检索），如果向量未就绪则回退到 search（BM25）
        result = subprocess.run(
            ['qmd', 'query', query, '-c', collection, '--json', '-n', str(limit)],
            capture_output=True, text=True, timeout=5, env=env
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        
        # 回退到 BM25 搜索
        result = subprocess.run(
            ['qmd', 'search', query, '-c', collection, '--json', '-n', str(limit)],
            capture_output=True, text=True, timeout=5, env=env
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
            
    except subprocess.TimeoutExpired:
        print("⚠️ QMD 检索超时")
    except json.JSONDecodeError:
        print("⚠️ QMD 返回格式错误")
    except Exception as e:
        print(f"⚠️ QMD 检索失败: {e}")
    
    return None

def extract_memory_id_from_snippet(snippet):
    """
    从 QMD 返回的 snippet 中提取 memory_id
    
    QMD 返回的 snippet 格式：
    ## f_20260207_a6b928 [score=0.99, imp=1.0]
    用户名字是张玉魁...
    """
    import re
    match = re.search(r'## ([fbs]_\d{8}_[a-f0-9]+)', snippet)
    return match.group(1) if match else None
```

### 4.3 修改：router_search() 集成 QMD

```python
def router_search(query, memory_dir=None, use_qmd=True):
    """
    Router 主入口：智能检索记忆（QMD 增强版）
    
    检索策略：
    1. 优先使用 QMD 检索（如果可用）
    2. QMD 结果与记忆系统元数据融合
    3. 如果 QMD 不可用，回退到原有的关键词检索
    """
    if memory_dir is None:
        memory_dir = get_memory_dir()
    
    # ===== 尝试 QMD 检索 =====
    if use_qmd and qmd_available():
        qmd_results = qmd_search(query, collection="curated", limit=30)
        
        if qmd_results:
            # 加载记忆系统元数据
            metadata = load_all_memory_metadata(memory_dir)
            
            # 融合 QMD 分数 + 记忆系统权重
            enriched = []
            for r in qmd_results:
                snippet = r.get('snippet', '')
                mem_id = extract_memory_id_from_snippet(snippet)
                
                if mem_id and mem_id in metadata:
                    meta = metadata[mem_id]
                    
                    # 计算综合分数
                    qmd_score = r.get('score', 0.5)
                    memory_score = meta.get('score', 0.5)
                    importance = meta.get('importance', 0.5)
                    
                    final_score = (
                        qmd_score * 0.4 +
                        memory_score * 0.35 +
                        importance * 0.25
                    )
                    
                    enriched.append({
                        'id': mem_id,
                        'content': meta.get('content', snippet),
                        'final_score': final_score,
                        'qmd_score': qmd_score,
                        'memory_score': memory_score,
                        'importance': importance,
                        'type': 'fact' if mem_id.startswith('f_') else ('belief' if mem_id.startswith('b_') else 'summary'),
                        'confidence': meta.get('confidence', 1.0),
                        'entities': meta.get('entities', []),
                    })
            
            if enriched:
                # 按综合分数排序
                enriched.sort(key=lambda x: x['final_score'], reverse=True)
                
                # 格式化返回
                return {
                    'method': 'qmd',
                    'results': enriched[:15],
                    'stats': {
                        'qmd_hits': len(qmd_results),
                        'enriched': len(enriched),
                        'final': min(15, len(enriched)),
                    }
                }
    
    # ===== 回退到原有检索 =====
    return legacy_router_search(query, memory_dir)


def load_all_memory_metadata(memory_dir):
    """
    加载所有记忆的元数据（用于与 QMD 结果融合）
    """
    metadata = {}
    
    for mem_type in ['facts', 'beliefs', 'summaries']:
        records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
        for r in records:
            metadata[r['id']] = r
    
    return metadata
```

### 4.4 修改：Consolidation 后触发 QMD 更新

在 `cmd_consolidate()` 的 Phase 7 之后添加：

```python
# Phase 8: 导出 QMD 索引并更新（新增）
if not args.phase or args.phase == 8:
    print("\n🔄 Phase 8: QMD 索引更新")
    
    # 8a: 导出 Markdown 格式
    try:
        qmd_index_dir = export_for_qmd(memory_dir)
        print(f"   导出到: {qmd_index_dir}")
    except Exception as e:
        print(f"   ⚠️ 导出失败: {e}")
    
    # 8b: 触发 QMD 更新（如果可用）
    if qmd_available():
        try:
            env = _get_qmd_env()
            subprocess.run(['qmd', 'update'], timeout=30, env=env, capture_output=True)
            print("   ✅ QMD 索引已更新")
        except Exception as e:
            print(f"   ⚠️ QMD 更新失败: {e}")
    else:
        print("   ⏭️ QMD 不可用，跳过")
    
    print("   ✅ 完成")
```

### 4.5 改进：Phase 2 闲聊/情绪过滤

```python
# 新增：闲聊/情绪过滤规则
CHAT_NOISE_PATTERNS = [
    # 简单回应
    r'^(哈哈|嗯|好的|ok|OK|行|可以|懂了|明白|嗯嗯|好|对|是的|没问题)$',
    # 纯标点/表情
    r'^[？!。，…～~\s😀-🙏]+$',
    # 临时情绪表达（短句）
    r'^(我去|卧槽|靠|艹|天哪|妈呀|完蛋|糟糕|太好了|不错).{0,5}$',
    # 困/累/饿等临时状态（除非有具体上下文）
    r'^.{0,5}(困死|累死|饿死|烦死|气死).{0,5}$',
]

def is_chat_noise(content):
    """
    判断是否为闲聊噪音
    
    返回 True 表示应该过滤掉
    """
    import re
    
    content = content.strip()
    
    # 太短的内容（少于 10 字符）
    if len(content) < 10:
        return True
    
    # 匹配噪音模式
    for pattern in CHAT_NOISE_PATTERNS:
        if re.match(pattern, content, re.IGNORECASE):
            return True
    
    return False

# 在 rule_filter() 中使用
def rule_filter(segments, threshold=0.3, use_llm_fallback=True):
    """Phase 2: 重要性筛选（增加闲聊过滤）"""
    
    filtered = []
    
    for segment in segments:
        content = segment.get("content", "") if isinstance(segment, dict) else segment
        
        # 【新增】闲聊噪音过滤
        if is_chat_noise(content):
            continue
        
        # ... 原有逻辑 ...
```

---

## 五、OpenClaw 配置

### 5.1 启用 QMD 后端

```json5
// ~/.openclaw/openclaw.json
{
  "memory": {
    "backend": "qmd",
    "qmd": {
      "includeDefaultMemory": false,  // 不索引原始 MEMORY.md（由记忆系统管理）
      "paths": [
        {
          "name": "curated",
          "path": "memory/layer2/qmd-index",
          "pattern": "*.md"
        }
      ],
      "update": {
        "interval": "5m",
        "onBoot": true,
        "debounceMs": 15000
      },
      "limits": {
        "maxResults": 30,
        "timeoutMs": 4000
      }
    }
  }
}
```

### 5.2 可选：启用 Session 历史索引（Tier 2）

```json5
{
  "memory": {
    "qmd": {
      "sessions": {
        "enabled": true,
        "retentionDays": 30
      }
    }
  }
}
```

---

## 六、文件结构变化

### 6.1 新增目录

```
memory/
├── layer2/
│   ├── active/
│   │   ├── facts.jsonl      # 原有
│   │   ├── beliefs.jsonl    # 原有
│   │   └── summaries.jsonl  # 原有
│   ├── qmd-index/           # 【新增】QMD 索引目录
│   │   ├── facts.md         # 转换后的 Markdown
│   │   ├── beliefs.md
│   │   └── summaries.md
│   └── ...
└── ...
```

### 6.2 QMD 状态目录（OpenClaw 管理）

```
~/.openclaw/agents/main/qmd/
├── xdg-config/
├── xdg-cache/
│   └── qmd/
│       └── index.sqlite     # QMD 索引数据库
└── sessions/                # Session 导出（如果启用）
```

---

## 七、预期收益

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 检索召回率 | ~70%（关键词） | ~95%（BM25+向量） | +35% |
| 检索精确率 | ~60% | ~85%（元数据过滤） | +42% |
| 检索延迟 | ~100ms | ~60ms | -40% |
| Token 效率 | 一般 | 高（置信度分层） | +30% |
| 闲聊噪音 | 有 | 过滤 | ⬆️ |
| 元认知能力 | ✅ 保留 | ✅ 保留 | 不变 |

---

## 八、实现清单

### 8.1 代码改动

| # | 任务 | 文件 | 复杂度 | 状态 |
|---|------|------|--------|------|
| 1 | 新增 `export_for_qmd()` 函数 | `memory.py` | ⭐⭐ | 待实现 |
| 2 | 新增 `qmd_search()` 函数 | `memory.py` | ⭐⭐ | 待实现 |
| 3 | 新增 `qmd_available()` 函数 | `memory.py` | ⭐ | 待实现 |
| 4 | 新增 `extract_memory_id_from_snippet()` | `memory.py` | ⭐ | 待实现 |
| 5 | 修改 `router_search()` 集成 QMD | `memory.py` | ⭐⭐⭐ | 待实现 |
| 6 | 新增 Phase 8: QMD 索引更新 | `memory.py` | ⭐⭐ | 待实现 |
| 7 | 新增 `is_chat_noise()` 过滤函数 | `memory.py` | ⭐ | 待实现 |
| 8 | 修改 `rule_filter()` 增加噪音过滤 | `memory.py` | ⭐ | 待实现 |

### 8.2 配置改动

| # | 任务 | 说明 | 状态 |
|---|------|------|------|
| 1 | 更新 OpenClaw 配置 | 启用 QMD 后端 | 待实现 |
| 2 | 创建 QMD 集合 | `qmd collection add` | 待实现 |
| 3 | 完成向量嵌入 | `qmd embed` | 待实现 |

### 8.3 测试清单

| # | 测试项 | 说明 |
|---|--------|------|
| 1 | JSONL → Markdown 转换 | 验证格式正确 |
| 2 | QMD 检索功能 | 验证能返回结果 |
| 3 | memory_id 提取 | 验证能正确提取 |
| 4 | 元数据融合 | 验证分数计算正确 |
| 5 | 闲聊过滤 | 验证噪音被过滤 |
| 6 | 回退机制 | 验证 QMD 不可用时回退正常 |
| 7 | 端到端测试 | 完整流程测试 |

---

## 九、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| QMD 不可用 | 检索失败 | 自动回退到原有检索 |
| 向量嵌入未完成 | 只有 BM25 | BM25 也能工作，只是精度略低 |
| 转换格式错误 | ID 提取失败 | 单元测试覆盖 |
| 性能问题 | 检索变慢 | 设置超时，超时则回退 |

---

## 十、后续优化方向

1. **Tier 2 Session 索引**：索引历史对话作为兜底
2. **增量更新**：只更新变化的记忆，而非全量导出
3. **缓存机制**：缓存热门查询结果
4. **向量嵌入优化**：使用更小的模型或远程 API

---

## 附录 A：QMD 命令参考

```bash
# 查看状态
qmd status

# 列出集合
qmd collection list

# 创建集合
qmd collection add <path> --name <name> --mask "*.md"

# 更新索引
qmd update

# 向量嵌入
qmd embed

# BM25 搜索
qmd search "query" -c <collection> --json

# 混合搜索（BM25 + 向量 + Reranking）
qmd query "query" -c <collection> --json

# 获取文档
qmd get qmd://<collection>/<path>
```

---

## 附录 B：当前环境状态（2026-02-10）

```
QMD 安装位置: /root/.bun/bin/qmd
QMD 集合: workspace (108 files, 4d ago)
向量嵌入: 0/108 (未完成)
记忆系统: 106 条活跃记忆 (81 facts, 9 beliefs, 16 summaries)
Session 历史: 22MB (~40 files)
```

---

**文档结束**
