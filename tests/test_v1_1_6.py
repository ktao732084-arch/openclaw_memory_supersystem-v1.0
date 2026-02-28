#!/usr/bin/env python3
"""
Memory System v1.1.6 测试
测试 Crabby 指出的三个问题的修复
"""

import sys
import os

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory import (
    extract_entities,
    deduplicate_facts,
    QUOTED_ENTITY_PATTERNS,
    OVERRIDE_SIGNALS_TIER1,
    OVERRIDE_SIGNALS_TIER2,
    DEDUP_CONFIG,
    now_iso
)

def test_quoted_entity_extraction():
    """测试引号实体提取（P0-1）"""
    print("\n📋 测试引号实体提取")
    
    test_cases = [
        # (输入, 期望包含的实体)
        ("张三负责'寒武纪'项目", ["寒武纪"]),
        ("李四在做「大灭绝」项目", ["大灭绝"]),
        ("王五接手了『奥陶纪』项目", ["奥陶纪"]),
        ('他说"这是个好项目"', ["这是个好项目"]),
        ("《红楼梦》是经典", ["红楼梦"]),
        ("系统和'项目B'都很重要", ["项目B", "系统"]),  # 引号内 + 固定词
        ("普通文本没有引号", []),  # 无引号
    ]
    
    passed = 0
    for content, expected in test_cases:
        entities = extract_entities(content, use_llm_fallback=False)
        
        # 检查期望的实体是否都被提取
        all_found = all(e in entities for e in expected)
        
        if all_found:
            print(f"✅ PASS: '{content[:30]}...'")
            print(f"       期望包含: {expected}, 实际: {entities}")
            passed += 1
        else:
            print(f"❌ FAIL: '{content[:30]}...'")
            print(f"       期望包含: {expected}, 实际: {entities}")
    
    return passed, len(test_cases)


def test_dedup_ratio_threshold():
    """测试去重阈值改用相对比例（P0-2）"""
    print("\n📋 测试去重阈值（相对比例）")
    
    # 测试用例：短句 vs 长句
    test_cases = [
        # 短句：3/10 = 30% 重叠，应该去重
        {
            "name": "短句高重叠",
            "new": {"id": "f_new", "content": "张三喜欢吃苹果", "entities": ["张三"], "importance": 0.8, "score": 0.8},
            "existing": [{"id": "f_old", "content": "张三喜欢吃香蕉", "entities": ["张三"], "importance": 0.5, "score": 0.5}],
            "expect_dedup": True,  # 重叠词：张三、喜欢、吃 = 3/5 = 60%
        },
        # 长句：3/50 = 6% 重叠，不应该去重
        {
            "name": "长句低重叠",
            "new": {"id": "f_new", "content": "张三今天去了北京参加了一个非常重要的会议讨论了很多关于人工智能的话题", "entities": ["张三"], "importance": 0.8, "score": 0.8},
            "existing": [{"id": "f_old", "content": "张三昨天在上海完成了一个关于机器学习的项目并且获得了很好的评价", "entities": ["张三"], "importance": 0.5, "score": 0.5}],
            "expect_dedup": False,  # 重叠词很少，比例低于 30%
        },
        # 包含关系：应该去重
        {
            "name": "包含关系",
            "new": {"id": "f_new", "content": "张三喜欢苹果", "entities": ["张三"], "importance": 0.8, "score": 0.8},
            "existing": [{"id": "f_old", "content": "张三喜欢苹果和香蕉", "entities": ["张三"], "importance": 0.5, "score": 0.5}],
            "expect_dedup": True,
        },
    ]
    
    passed = 0
    for case in test_cases:
        merged, dup_count, _ = deduplicate_facts([case["new"]], case["existing"])
        
        is_deduped = dup_count > 0
        
        if is_deduped == case["expect_dedup"]:
            print(f"✅ PASS: {case['name']}")
            print(f"       去重: {is_deduped}, 期望: {case['expect_dedup']}")
            passed += 1
        else:
            print(f"❌ FAIL: {case['name']}")
            print(f"       去重: {is_deduped}, 期望: {case['expect_dedup']}")
    
    return passed, len(test_cases)


def test_tiered_conflict_signals():
    """测试分层冲突信号（P1）"""
    print("\n📋 测试分层冲突信号")
    
    test_cases = [
        # Tier 1: 强降权
        {
            "name": "Tier 1 - '其实是'",
            "new": {"id": "f_new", "content": "张三其实是喜欢吃苹果", "entities": ["张三"], "importance": 0.8, "score": 0.8},
            "existing": [{"id": "f_old", "content": "张三喜欢吃香蕉", "entities": ["张三"], "importance": 0.5, "score": 0.5}],
            "expect_tier": 1,
            "expect_penalty": DEDUP_CONFIG["tier1_penalty"],
        },
        # Tier 2: 弱降权
        {
            "name": "Tier 2 - '逗你的'",
            "new": {"id": "f_new", "content": "逗你的张三喜欢吃苹果", "entities": ["张三"], "importance": 0.8, "score": 0.8},
            "existing": [{"id": "f_old", "content": "张三喜欢吃香蕉", "entities": ["张三"], "importance": 0.5, "score": 0.5}],
            "expect_tier": 2,
            "expect_penalty": DEDUP_CONFIG["tier2_penalty"],
        },
        # Tier 2: 弱降权
        {
            "name": "Tier 2 - '开玩笑'",
            "new": {"id": "f_new", "content": "开玩笑张三喜欢吃苹果", "entities": ["张三"], "importance": 0.8, "score": 0.8},
            "existing": [{"id": "f_old", "content": "张三喜欢吃香蕉", "entities": ["张三"], "importance": 0.5, "score": 0.5}],
            "expect_tier": 2,
            "expect_penalty": DEDUP_CONFIG["tier2_penalty"],
        },
    ]
    
    passed = 0
    for case in test_cases:
        _, _, downgrade_count = deduplicate_facts([case["new"]], case["existing"])
        
        # 检查是否触发降权
        if downgrade_count > 0:
            existing = case["existing"][0]
            actual_tier = existing.get("override_tier")
            actual_score = existing.get("score", 0)
            expected_score = 0.5 * case["expect_penalty"]
            
            tier_match = actual_tier == case["expect_tier"]
            score_match = abs(actual_score - expected_score) < 0.01
            
            if tier_match and score_match:
                print(f"✅ PASS: {case['name']}")
                print(f"       Tier: {actual_tier}, Score: {actual_score:.2f}")
                passed += 1
            else:
                print(f"❌ FAIL: {case['name']}")
                print(f"       期望 Tier: {case['expect_tier']}, 实际: {actual_tier}")
                print(f"       期望 Score: {expected_score:.2f}, 实际: {actual_score:.2f}")
        else:
            print(f"❌ FAIL: {case['name']} - 未触发降权")
    
    return passed, len(test_cases)


def test_peanut_conflict():
    """测试花生过敏 vs 花生狂魔场景（Crabby 的测试用例）"""
    print("\n📋 测试花生冲突场景（Crabby 用例）")
    
    # 场景：先说"我最喜欢吃花生"，后说"逗你的，我吃花生会死"
    existing = [
        {"id": "f_peanut_love", "content": "我最喜欢吃花生", "entities": ["我"], "importance": 0.8, "score": 0.8}
    ]
    
    new_fact = {
        "id": "f_peanut_allergy",
        "content": "逗你的我吃花生会过敏会死",
        "entities": ["我"],
        "importance": 1.0,
        "score": 1.0
    }
    
    merged, dup_count, downgrade_count = deduplicate_facts([new_fact], existing)
    
    # 期望：
    # 1. 新记忆被添加（不是重复）
    # 2. 旧记忆被 Tier 2 降权（因为"逗你的"是 Tier 2 信号）
    
    new_added = len(merged) > 0
    old_downgraded = downgrade_count > 0
    
    if old_downgraded:
        old_tier = existing[0].get("override_tier")
        old_score = existing[0].get("score", 0)
        
        if new_added and old_tier == 2:
            print(f"✅ PASS: 花生冲突场景")
            print(f"       新记忆已添加: {new_added}")
            print(f"       旧记忆降权: Tier {old_tier}, Score {old_score:.2f}")
            return 1, 1
        else:
            print(f"❌ FAIL: 花生冲突场景")
            print(f"       新记忆已添加: {new_added}, 期望: True")
            print(f"       旧记忆 Tier: {old_tier}, 期望: 2")
            return 0, 1
    else:
        print(f"❌ FAIL: 花生冲突场景 - 未触发降权")
        return 0, 1


def test_project_entity_extraction():
    """测试项目实体提取（Crabby 的测试用例）"""
    print("\n📋 测试项目实体提取（Crabby 用例）")
    
    test_cases = [
        ("张三负责'寒武纪'项目", ["寒武纪"]),
        ("李四在做「大灭绝」项目", ["大灭绝"]),
        ("王五接手了『奥陶纪』项目", ["奥陶纪"]),
    ]
    
    passed = 0
    for content, expected in test_cases:
        entities = extract_entities(content, use_llm_fallback=False)
        
        # 检查引号内的项目名是否被提取
        all_found = all(e in entities for e in expected)
        
        if all_found:
            print(f"✅ PASS: '{content}'")
            print(f"       提取到: {entities}")
            passed += 1
        else:
            print(f"❌ FAIL: '{content}'")
            print(f"       期望包含: {expected}, 实际: {entities}")
    
    return passed, len(test_cases)


def main():
    print("=" * 60)
    print("Memory System v1.1.6 - Crabby 问题修复测试")
    print("=" * 60)
    
    total_passed = 0
    total_tests = 0
    
    # P0-1: 引号实体提取
    p, t = test_quoted_entity_extraction()
    total_passed += p
    total_tests += t
    
    # P0-2: 去重阈值
    p, t = test_dedup_ratio_threshold()
    total_passed += p
    total_tests += t
    
    # P1: 分层冲突信号
    p, t = test_tiered_conflict_signals()
    total_passed += p
    total_tests += t
    
    # Crabby 用例：花生冲突
    p, t = test_peanut_conflict()
    total_passed += p
    total_tests += t
    
    # Crabby 用例：项目实体
    p, t = test_project_entity_extraction()
    total_passed += p
    total_tests += t
    
    print("\n" + "=" * 60)
    print(f"总计: {total_passed}/{total_tests} 通过")
    if total_passed == total_tests:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️ {total_tests - total_passed} 个测试失败")
    print("=" * 60)
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
