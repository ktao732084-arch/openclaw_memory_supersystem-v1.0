# Phase 4b: Belief 验证 Prompt

判断新事实对已有推断的影响。

## 已有推断
{{belief.content}}
置信度：{{belief.confidence}}

## 新事实
{{new_fact.content}}

## 判断标准

- **confirm** = 新事实证实了推断
- **deny** = 新事实否定了推断
- **irrelevant** = 新事实与推断无关

## 输出

只输出一个词：confirm / deny / irrelevant
