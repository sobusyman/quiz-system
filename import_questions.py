#!/usr/bin/env python3
"""
题库导入脚本
从Markdown格式的题库文件中解析题目并导入到数据库
"""

import re
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import database


def parse_questions_from_md(md_content, category_id):
    """
    从Markdown内容中解析题目
    返回题目列表
    """
    questions = []

    # 按题目编号分割
    # 匹配 "数字.题干：" 或 "数字.题干;" 格式
    pattern = r'(\d+)\.题干[：;](.*?)(?=\n\d+\.题干[：;]|\Z)'
    matches = re.findall(pattern, md_content, re.DOTALL)

    for num, content in matches:
        # 提取题目内容和答案
        # 分离题干、选项和答案（兼容中文冒号和英文冒号）
        answer_match = re.search(r'答案[：:]\s*([A-Z,，\s正确错误]+)', content)
        if not answer_match:
            continue

        answer = answer_match.group(1).strip()
        # 清理答案中的空格和中文逗号
        answer = answer.replace('，', ',').replace(' ', '')

        # 提取题干（到选项之前）
        question_text = content[:answer_match.start()].strip()

        # 判断题型
        q_type = 'single'  # 默认单选
        options = []

        # 检查是否是判断题
        if answer in ('正确', '错误'):
            q_type = 'judge'
            options = [{'label': '对', 'text': '正确'}, {'label': '错', 'text': '错误'}]
        else:
            # 提取选项（支持A.和A、两种格式）
            option_pattern = r'([A-D])[.、]\s*(.*?)(?=\n[A-D][.、]|答案[：:]|\Z)'
            option_matches = re.findall(option_pattern, content, re.DOTALL)

            if option_matches:
                options = []
                for opt_letter, opt_text in option_matches:
                    # 清理选项文本
                    opt_text = opt_text.strip().replace('\n', '')
                    # 移除多余空格
                    opt_text = re.sub(r'\s+', '', opt_text)
                    options.append({'label': opt_letter, 'text': opt_text})

                # 判断是单选还是多选
                if ',' in answer or len(answer) > 1:
                    q_type = 'multiple'
                else:
                    q_type = 'single'

        # 清理题干文本
        # 移除选项部分（如果有的话）
        if q_type != 'judge' and options:
            # 找到第一个选项的位置
            first_option = options[0]['label'] + '.'
            opt_pos = question_text.find(first_option)
            if opt_pos > 0:
                question_text = question_text[:opt_pos].strip()

        # 清理题干中的换行和多余空格
        question_text = question_text.replace('\n', '')
        question_text = re.sub(r'\s+', '', question_text)
        # 移除末尾的"（）"或"()"
        question_text = re.sub(r'[（(][\s）)]*$', '', question_text)

        if question_text and (options or q_type == 'judge'):
            questions.append({
                'type': q_type,
                'question': question_text,
                'options': options,
                'answer': answer,
                'analysis': ''
            })

    return questions


def parse_questions_by_section(md_content, parent_category_id):
    """
    按章节解析题目
    """
    # 先找出所有的题型章节
    # 格式："一、单选题"、"二、多选题"等
    section_pattern = r'([一二三四五六七八九十]+)、(单选题|多选题|判断题|案例题)\n'
    sections = list(re.finditer(section_pattern, md_content))

    if not sections:
        # 没有明确的题型分节，尝试整体解析
        return parse_questions_from_md(md_content, parent_category_id)

    all_questions = []

    for i, section_match in enumerate(sections):
        section_name = section_match.group(2)
        start = section_match.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(md_content)
        section_content = md_content[start:end]

        # 根据题型创建子分类
        type_map = {
            '单选题': 'single',
            '多选题': 'multiple',
            '判断题': 'judge',
            '案例题': 'case'
        }
        q_type = type_map.get(section_name, 'single')

        # 解析该节的题目
        questions = parse_questions_from_md(section_content, parent_category_id)

        # 修正题型
        for q in questions:
            if section_name == '案例题':
                # 案例题可能是多选也可能是单选，根据答案判断
                q['type'] = 'case'
            else:
                q['type'] = q_type

        all_questions.extend(questions)

    return all_questions


def import_public_questions(md_file_path):
    """
    导入公共部分题库
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 创建一级分类
    parent_id = database.add_category(
        name='公共部分题库',
        description='安全生产公共知识题库',
        sort_order=1
    )

    # 找出所有章节
    # 格式："第一部分 XXX" 或 "一、XXX"
    chapter_pattern = r'第[一二三四五六七八九十]+部分\s*(.*?)\n'
    chapters = list(re.finditer(chapter_pattern, content))

    if not chapters:
        # 尝试另一种格式
        chapter_pattern = r'^##\s+(.*?)$'
        chapters = list(re.finditer(chapter_pattern, content, re.MULTILINE))

    if not chapters:
        # 如果没有分章节，整体导入
        questions = parse_questions_by_section(content, parent_id)
        # 创建一个默认子分类
        sub_id = database.add_category(
            name='全部题目',
            description='公共部分全部题目',
            parent_id=parent_id,
            sort_order=1
        )
        for q in questions:
            database.add_question(
                category_id=sub_id,
                q_type=q['type'],
                question=q['question'],
                options=q['options'],
                answer=q['answer'],
                analysis=q.get('analysis', '')
            )
        return len(questions)

    total = 0
    for i, chapter_match in enumerate(chapters):
        chapter_name = chapter_match.group(1).strip()
        start = chapter_match.end()
        end = chapters[i + 1].start() if i + 1 < len(chapters) else len(content)
        chapter_content = content[start:end]

        # 创建子分类
        sub_id = database.add_category(
            name=chapter_name,
            description=chapter_name,
            parent_id=parent_id,
            sort_order=i + 1
        )

        # 解析题目
        questions = parse_questions_by_section(chapter_content, parent_id)

        for q in questions:
            database.add_question(
                category_id=sub_id,
                q_type=q['type'],
                question=q['question'],
                options=q['options'],
                answer=q['answer'],
                analysis=q.get('analysis', '')
            )

        total += len(questions)
        print(f'  导入章节 "{chapter_name}": {len(questions)} 题')

    return total


def import_dangerous_questions(md_file_path):
    """
    导入危险货物运输专业题库
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 创建一级分类
    parent_id = database.add_category(
        name='危险货物运输专业题库',
        description='道路危险货物运输专业知识题库',
        sort_order=2
    )

    # 找出业务类型章节
    # 格式："业务类型3：道路危险货物运输"
    biz_pattern = r'业务类型\d+：(.*?)\n'
    biz_sections = list(re.finditer(biz_pattern, content))

    if not biz_sections:
        biz_pattern = r'^##\s+(.*?)$'
        biz_sections = list(re.finditer(biz_pattern, content, re.MULTILINE))

    if not biz_sections:
        # 整体导入
        questions = parse_questions_by_section(content, parent_id)
        sub_id = database.add_category(
            name='全部题目',
            description='专业部分全部题目',
            parent_id=parent_id,
            sort_order=1
        )
        for q in questions:
            database.add_question(
                category_id=sub_id,
                q_type=q['type'],
                question=q['question'],
                options=q['options'],
                answer=q['answer'],
                analysis=q.get('analysis', '')
            )
        return len(questions)

    total = 0
    for i, biz_match in enumerate(biz_sections):
        biz_name = biz_match.group(1).strip()
        start = biz_match.end()
        end = biz_sections[i + 1].start() if i + 1 < len(biz_sections) else len(content)
        biz_content = content[start:end]

        # 创建子分类
        sub_id = database.add_category(
            name=biz_name,
            description=biz_name,
            parent_id=parent_id,
            sort_order=i + 1
        )

        # 解析题目
        questions = parse_questions_by_section(biz_content, parent_id)

        for q in questions:
            database.add_question(
                category_id=sub_id,
                q_type=q['type'],
                question=q['question'],
                options=q['options'],
                answer=q['answer'],
                analysis=q.get('analysis', '')
            )

        total += len(questions)
        print(f'  导入章节 "{biz_name}": {len(questions)} 题')

    return total


def main():
    # 初始化数据库
    database.init_db()

    print('=' * 50)
    print('开始导入题库...')
    print('=' * 50)

    # 公共题库路径
    public_md = '/tmp/public_questions.md'
    dangerous_md = '/tmp/dangerous_questions.md'

    # 检查文件是否存在
    if not os.path.exists(public_md):
        print(f'错误：找不到文件 {public_md}')
        return

    if not os.path.exists(dangerous_md):
        print(f'错误：找不到文件 {dangerous_md}')
        return

    print('\n1. 导入公共部分题库...')
    public_count = import_public_questions(public_md)
    print(f'   公共题库共导入 {public_count} 题')

    print('\n2. 导入危险货物运输专业题库...')
    dangerous_count = import_dangerous_questions(dangerous_md)
    print(f'   专业题库共导入 {dangerous_count} 题')

    print('\n' + '=' * 50)
    print(f'导入完成！总计 {public_count + dangerous_count} 题')
    print(f'数据库文件: {database.DB_PATH}')
    print('=' * 50)

    # 打印分类统计
    print('\n题库分类统计：')
    categories = database.get_categories()
    for cat in categories:
        print(f'\n  {cat["name"]}:')
        sub_cats = database.get_categories(parent_id=cat['id'])
        for sub in sub_cats:
            count = database.get_question_count(sub['id'])
            print(f'    - {sub["name"]}: {count} 题')


if __name__ == '__main__':
    main()
