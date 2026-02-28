#!/bin/bash
# Memory System v1.1 验证脚本

echo "🧪 Memory System v1.1 验证"
echo "=" | tr '=' '=' | head -c 60; echo

# 1. 检查文件完整性
echo -e "\n📂 检查文件完整性..."
files=(
    "scripts/v1_1_config.py"
    "scripts/v1_1_helpers.py"
    "scripts/v1_1_commands.py"
    "scripts/test_v1.1.py"
    "scripts/memory.py"
    "docs/v1.1-changelog.md"
    "docs/v1.1-usage-guide.md"
    "SKILL.md"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo -e "\n❌ 文件检查失败"
    exit 1
fi

# 2. 运行功能测试
echo -e "\n🧪 运行功能测试..."
cd scripts
python3 test_v1.1.py > /tmp/test_output.txt 2>&1

if grep -q "✅ 所有测试完成" /tmp/test_output.txt; then
    echo "  ✅ 功能测试通过"
else
    echo "  ❌ 功能测试失败"
    cat /tmp/test_output.txt
    exit 1
fi

# 3. 检查版本号
echo -e "\n📌 检查版本号..."
if grep -q '"version": "1.1' memory.py; then
    echo "  ✅ memory.py 版本号正确"
else
    echo "  ❌ memory.py 版本号错误"
    exit 1
fi

if grep -q 'version: 1.1.0' ../SKILL.md; then
    echo "  ✅ SKILL.md 版本号正确"
else
    echo "  ❌ SKILL.md 版本号错误"
    exit 1
fi

# 4. 检查导入
echo -e "\n🔗 检查模块导入..."
python3 -c "from v1_1_config import *; from v1_1_helpers import *; from v1_1_commands import *" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ 模块导入成功"
else
    echo "  ❌ 模块导入失败"
    exit 1
fi

# 5. 检查命令行接口
echo -e "\n⚙️ 检查命令行接口..."
python3 memory.py --help | grep -q "record-access"
if [ $? -eq 0 ]; then
    echo "  ✅ record-access 命令存在"
else
    echo "  ❌ record-access 命令缺失"
    exit 1
fi

python3 memory.py --help | grep -q "view-access-log"
if [ $? -eq 0 ]; then
    echo "  ✅ view-access-log 命令存在"
else
    echo "  ❌ view-access-log 命令缺失"
    exit 1
fi

python3 memory.py --help | grep -q "view-expired-log"
if [ $? -eq 0 ]; then
    echo "  ✅ view-expired-log 命令存在"
else
    echo "  ❌ view-expired-log 命令缺失"
    exit 1
fi

# 6. 统计代码量
echo -e "\n📊 代码统计..."
total_lines=$(wc -l v1_1_*.py test_v1.1.py | tail -1 | awk '{print $1}')
echo "  新增代码: $total_lines 行"

doc_size=$(du -sh ../docs/v1.1-*.md | awk '{sum+=$1} END {print sum}')
echo "  新增文档: $(du -ch ../docs/v1.1-*.md | tail -1 | awk '{print $1}')"

# 7. 最终总结
echo -e "\n" | tr '\n' '=' | head -c 60; echo
echo "✅ Memory System v1.1 验证通过"
echo "=" | tr '=' '=' | head -c 60; echo
echo ""
echo "📦 实现完成："
echo "  - 核心模块: 3 个文件"
echo "  - 测试脚本: 1 个文件"
echo "  - 文档: 2 个文件"
echo "  - 总代码量: $total_lines 行"
echo ""
echo "🚀 可以开始使用 v1.1 功能！"
echo ""
