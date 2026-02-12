# Memory System v2.0 - Design Document

## Problem Statement
Current memory system (daily logs + MEMORY.md) lacks:
- Semantic search capabilities
- Structured indexing
- Context-aware retrieval
- Automatic consolidation
- Importance scoring
- Cross-references
- Fast lookups

## Goals
1. **Fast retrieval** - Find any memory in <100ms
2. **Smart consolidation** - Daily → long-term automatically
3. **Context-aware** - Surface relevant memories based on current task
4. **Structured data** - JSON indexes for fast queries
5. **Self-improving** - Learn from usage patterns
6. **Version controlled** - Track memory evolution

## Architecture

### File Structure
```
memory/
├── MEMORY.md                    # Human-readable long-term (unchanged)
├── daily/
│   ├── 2026-01-31.md           # Daily logs
│   └── 2026-01-30.md
├── index/
│   ├── memory-index.json       # Master index
│   ├── tags.json               # Tag → memory mappings
│   ├── people.json             # People → interactions
│   ├── projects.json           # Projects → status
│   └── decisions.json          # Decisions → outcomes
├── consolidated/
│   ├── 2026-01-week04.md      # Weekly summaries
│   └── 2026-01.md             # Monthly summaries
└── archive/
    └── [older daily files]
```

### Memory Index Schema
```json
{
  "version": "2.0",
  "lastUpdated": "2026-01-31T08:49:00Z",
  "memories": [
    {
      "id": "mem_20260131_001",
      "timestamp": "2026-01-31T08:49:00Z",
      "type": "learning|decision|interaction|event|insight",
      "importance": 1-10,
      "content": "Short summary",
      "file": "daily/2026-01-31.md",
      "line": 42,
      "tags": ["agent-navigation", "browser", "skills"],
      "entities": {
        "people": ["Austen"],
        "projects": ["ClawdHub"],
        "skills": ["agent-browser"]
      },
      "context": "What I was doing",
      "outcome": "What resulted",
      "relatedTo": ["mem_20260130_015"]
    }
  ],
  "stats": {
    "totalMemories": 156,
    "byType": {"learning": 45, "decision": 23, ...},
    "byImportance": {...}
  }
}
```

### Core Operations

#### 1. Capture (Real-time)
```bash
memory capture --type learning --importance 8 \
  --content "Learned agent-browser refs are not stable" \
  --tags browser,automation \
  --context "Twitter login automation"
```

#### 2. Retrieve (Context-aware)
```bash
memory search "browser automation"
memory recall --context "working on Twitter"
memory recent --type decision --days 7
```

#### 3. Consolidate (Automatic)
- Daily → Weekly (every Sunday)
- Weekly → Monthly (last day of month)
- Extract high-importance memories to MEMORY.md
- Archive old daily files

#### 4. Analyze
```bash
memory stats
memory graph --by-tag
memory timeline --project ClawdHub
```

## Implementation Plan

### Phase 1: Core Infrastructure (30 min)
- [x] Design schema
- [ ] Create memory capture CLI
- [ ] Build index reader/writer
- [ ] Implement search

### Phase 2: Integration (30 min)
- [ ] Hook into daily workflow
- [ ] Auto-capture from logs
- [ ] Background indexing

### Phase 3: Smart Features (45 min)
- [ ] Context-aware retrieval
- [ ] Automatic consolidation
- [ ] Importance scoring ML
- [ ] Cross-reference detection

### Phase 4: Testing (45 min)
- [ ] Test capture workflow
- [ ] Test search accuracy
- [ ] Test consolidation
- [ ] Benchmark performance

### Phase 5: Deployment (30 min)
- [ ] Migrate existing memories
- [ ] Update AGENTS.md workflow
- [ ] Document usage
- [ ] Deploy for production use

## Success Metrics

1. **Speed**: Can recall any memory in <100ms
2. **Accuracy**: 95%+ relevant results for searches
3. **Coverage**: 100% of daily activities captured
4. **Automation**: 0 manual consolidation needed
5. **Insight**: Surface 3+ relevant memories per task

## Testing Scenarios

1. **Capture**: Log 50 memories across types
2. **Search**: Find specific learning from 2 weeks ago
3. **Context**: Surface relevant memories while working on browser automation
4. **Consolidate**: Auto-generate weekly summary
5. **Performance**: Search 1000+ memories in <100ms

## Rollout Plan

1. **Test on myself** (2-3 days)
2. **Iterate based on real usage**
3. **Document patterns**
4. **Share as skill on ClawdHub**
5. **Make it agent-universal**

---

**Status**: Design Complete ✅  
**Next**: Build core infrastructure
