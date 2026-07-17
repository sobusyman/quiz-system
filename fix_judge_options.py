#!/usr/bin/env python3
"""
修复判断题选项格式的脚本
将判断题的options从字符串数组转换为对象数组格式
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import database


def fix_judge_options():
    """修复所有判断题的选项格式"""
    conn = database.get_db()
    cursor = conn.cursor()

    # 获取所有判断题
    cursor.execute("SELECT id, options FROM questions WHERE type = 'judge'")
    questions = cursor.fetchall()

    fixed_count = 0
    for q in questions:
        options = q['options']
        if options:
            try:
                opt_list = json.loads(options)
                # 检查是否是字符串数组格式
                if isinstance(opt_list, list) and len(opt_list) > 0 and isinstance(opt_list[0], str):
                    # 转换为对象数组格式
                    new_options = []
                    for i, opt_text in enumerate(opt_list):
                        label = '对' if i == 0 else '错'
                        new_options.append({'label': label, 'text': opt_text})
                    # 更新数据库
                    new_options_json = json.dumps(new_options, ensure_ascii=False)
                    cursor.execute(
                        'UPDATE questions SET options = ? WHERE id = ?',
                        (new_options_json, q['id'])
                    )
                    fixed_count += 1
            except json.JSONDecodeError:
                pass

    conn.commit()
    conn.close()
    print(f'已修复 {fixed_count} 道判断题的选项格式')
    return fixed_count


if __name__ == '__main__':
    fix_judge_options()
