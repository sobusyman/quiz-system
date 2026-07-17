#!/usr/bin/env python3
"""
将本地SQLite题库数据导入到云端PostgreSQL数据库（Supabase）

使用方法：
    设置环境变量后运行：
    export DB_TYPE=postgresql
    export DB_HOST=你的数据库主机
    export DB_PORT=5432
    export DB_NAME=你的数据库名
    export DB_USER=你的用户名
    export DB_PASSWORD=你的密码
    python3 import_to_cloud.py
"""

import os
import sys
import json
import sqlite3

# 设置为postgresql模式
os.environ['DB_TYPE'] = os.environ.get('DB_TYPE', 'postgresql')

sys.path.insert(0, os.path.dirname(__file__))
import database

# 本地SQLite数据库路径
LOCAL_DB = os.path.join(os.path.dirname(__file__), 'data', 'quiz.db')


def get_local_db():
    """连接本地SQLite数据库"""
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    return conn


def import_categories():
    """导入分类数据"""
    local_conn = get_local_db()
    cursor = local_conn.cursor()
    
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = [dict(row) for row in cursor.fetchall()]
    local_conn.close()
    
    print(f"找到 {len(categories)} 个分类")
    
    # 检查云端是否已有数据
    cloud_categories = database.get_all_categories()
    if len(cloud_categories) > 0:
        print("云端已有分类数据，跳过分类导入")
        return
    
    # 导入分类
    id_map = {}  # 本地ID -> 云端ID
    
    # 先导入父分类
    for cat in categories:
        if cat['parent_id'] == 0:
            new_id = database.add_category(
                name=cat['name'],
                description=cat['description'] or '',
                parent_id=0,
                sort_order=cat['sort_order']
            )
            id_map[cat['id']] = new_id
            print(f"  导入分类: {cat['name']} (新ID: {new_id})")
    
    # 再导入子分类
    for cat in categories:
        if cat['parent_id'] != 0:
            new_parent_id = id_map.get(cat['parent_id'], 0)
            new_id = database.add_category(
                name=cat['name'],
                description=cat['description'] or '',
                parent_id=new_parent_id,
                sort_order=cat['sort_order']
            )
            id_map[cat['id']] = new_id
            print(f"  导入子分类: {cat['name']} (新ID: {new_id})")
    
    return id_map


def import_questions(id_map):
    """导入题目数据"""
    local_conn = get_local_db()
    cursor = local_conn.cursor()
    
    cursor.execute('SELECT * FROM questions ORDER BY id')
    questions = [dict(row) for row in cursor.fetchall()]
    local_conn.close()
    
    print(f"\n找到 {len(questions)} 道题目")
    
    # 检查云端是否已有题目
    cloud_count = database.get_question_count()
    if cloud_count > 0:
        print("云端已有题目数据，跳过题目导入")
        return
    
    # 导入题目
    success_count = 0
    for q in questions:
        try:
            new_category_id = id_map.get(q['category_id'], q['category_id'])
            
            # 解析选项
            options = json.loads(q['options']) if q['options'] else []
            
            database.add_question(
                category_id=new_category_id,
                q_type=q['type'],
                question=q['question'],
                options=options,
                answer=q['answer'],
                analysis=q['analysis'] or ''
            )
            success_count += 1
            
            if success_count % 100 == 0:
                print(f"  已导入 {success_count} 题...")
        except Exception as e:
            print(f"  导入题目失败 (ID={q['id']}): {e}")
    
    print(f"成功导入 {success_count} 道题目")


def main():
    print("=" * 60)
    print("题库数据导入工具（本地SQLite -> 云端PostgreSQL）")
    print("=" * 60)
    
    # 检查环境变量
    if not os.environ.get('DB_HOST'):
        print("\n错误：请先设置数据库连接环境变量：")
        print("  export DB_HOST=你的数据库主机地址")
        print("  export DB_PORT=5432")
        print("  export DB_NAME=你的数据库名")
        print("  export DB_USER=你的用户名")
        print("  export DB_PASSWORD=你的密码")
        print()
        print("然后运行: python3 import_to_cloud.py")
        return
    
    # 检查本地数据库
    if not os.path.exists(LOCAL_DB):
        print(f"\n错误：找不到本地数据库文件 {LOCAL_DB}")
        print("请先在本地运行导入脚本：python3 import_questions.py")
        return
    
    try:
        # 初始化云端数据库表
        print("\n正在初始化云端数据库表...")
        database.init_db()
        print("数据库表初始化完成")
        
        # 导入分类
        print("\n正在导入分类...")
        id_map = import_categories()
        
        if not id_map:
            # 云端已有数据，获取ID映射
            cloud_cats = database.get_all_categories()
            id_map = {}
            # 简单映射：假设分类名称相同
            local_conn = get_local_db()
            cursor = local_conn.cursor()
            cursor.execute('SELECT * FROM categories ORDER BY id')
            local_cats = [dict(row) for row in cursor.fetchall()]
            local_conn.close()
            
            for lcat in local_cats:
                for ccat in cloud_cats:
                    if lcat['name'] == ccat['name']:
                        id_map[lcat['id']] = ccat['id']
                        break
        
        # 导入题目
        print("\n正在导入题目...")
        import_questions(id_map)
        
        print("\n" + "=" * 60)
        print("导入完成！")
        print("=" * 60)
        
        # 统计
        total = database.get_question_count()
        print(f"\n云端题库总数：{total} 题")
        
        cats = database.get_categories()
        for cat in cats:
            sub_cats = database.get_categories(parent_id=cat['id'])
            for sub in sub_cats:
                count = database.get_question_count(sub['id'])
                print(f"  {cat['name']} - {sub['name']}: {count} 题")
        
    except Exception as e:
        print(f"\n导入失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
