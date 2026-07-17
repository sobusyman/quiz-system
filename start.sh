#!/bin/bash
# 答题系统启动脚本

# 清除可能干扰的Python环境变量
unset PYTHONHOME
unset PYTHONPATH

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  答题系统启动中..."
echo "=========================================="

# 检查数据库是否存在，不存在则初始化并导入题库
if [ ! -f "data/quiz.db" ]; then
    echo "首次启动，正在导入题库..."
    python3 import_questions.py
    echo ""
fi

echo "系统启动成功！"
echo ""
echo "访问地址："
echo "  本机访问: http://localhost:8080"
echo "  局域网访问: http://$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}'):8080"
echo ""
echo "手机端访问：确保手机和电脑在同一WiFi下，使用上面的局域网地址访问"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

# 启动Flask服务
python3 app.py
