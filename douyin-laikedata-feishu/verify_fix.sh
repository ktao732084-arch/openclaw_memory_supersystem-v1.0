#!/bin/bash
# 快速验证 Token 自动刷新修复

echo "=========================================="
echo "Token 自动刷新修复验证"
echo "=========================================="
echo ""

echo "1️⃣ 检查 Token 状态..."
python3 token_manager.py status
echo ""

echo "2️⃣ 验证脚本是否使用自动刷新..."
echo ""
echo "   sync_data.py:"
grep -q "from token_manager import get_valid_token" sync_data.py && echo "   ✅ 使用 get_valid_token()" || echo "   ❌ 未使用"
echo ""
echo "   sync_stable.py:"
grep -q "from token_manager import get_valid_token" sync_stable.py && echo "   ✅ 使用 get_valid_token()" || echo "   ❌ 未使用"
echo ""

echo "3️⃣ 运行自动刷新测试..."
python3 test_token_auto_refresh.py
echo ""

echo "=========================================="
echo "验证完成！"
echo "=========================================="
