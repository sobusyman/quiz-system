#!/bin/bash
# Render 构建脚本

# 初始化数据库表结构
python3 -c "import database; database.init_db(); print('Database tables initialized')"

# 检查是否已有题目数据，如果没有则导入题库
python3 -c "
import database
count = database.get_question_count()
if count == 0:
    print('No questions found, importing question bank...')
    import import_questions
    # 这里只初始化表结构，题库需要通过本地脚本导入到Supabase
    print('Please run import_to_supabase.py locally to import questions')
else:
    print(f'Question bank already has {count} questions')
"

echo "Build completed!"
