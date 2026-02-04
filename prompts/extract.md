# Phase 3: 深度提取 Prompt

你是一个信息提取器。请将以下片段转换为结构化记忆。

## 待提取片段
{{selected_fragments}}

## 提取规则

1. **fact** = 用户明确陈述的事实（confidence = 1.0）
2. **belief** = 需要推断的信息（标注 confidence 0.3-0.9）
3. 保持简洁，删除冗余词汇
4. 识别涉及的实体（人名、地名、组织、项目等）
5. 每个片段最多提取 1-2 条记忆

## 实体类型

- person: 人物
- location: 地点
- organization: 组织
- project: 项目
- other: 其他

## 输出格式（JSON）

```json
{
  "facts": [
    {
      "id": "f_20260204_001",
      "content": "用户名字是张三",
      "importance": 1.0,
      "entities": [{"name": "张三", "type": "person"}],
      "source": "fragment_1"
    }
  ],
  "beliefs": [
    {
      "id": "b_20260204_001",
      "content": "用户可能在科技公司工作",
      "confidence": 0.6,
      "importance": 0.5,
      "basis": "提到在北京工作，经常开会",
      "entities": [{"name": "用户", "type": "person"}],
      "source": "fragment_2,fragment_3"
    }
  ]
}
```

只输出 JSON，不要解释。
