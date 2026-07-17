from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
import database

app = Flask(__name__)
app.secret_key = 'quiz-system-secret-key-2024'
app.config['JSON_AS_ASCII'] = False

# 初始化数据库
database.init_db()


# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': '请先登录'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 页面路由
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/home')
@login_required
def home():
    user = database.get_user(session['user_id'])
    stats = database.get_user_stats(session['user_id'])
    categories = database.get_categories()
    return render_template('home.html', user=user, stats=stats, categories=categories)


@app.route('/quiz/<int:category_id>')
@login_required
def quiz(category_id):
    user = database.get_user(session['user_id'])
    category = None
    for cat in database.get_all_categories():
        if cat['id'] == category_id:
            category = cat
            break
    return render_template('quiz.html', user=user, category_id=category_id, category=category)


@app.route('/wrong')
@login_required
def wrong():
    user = database.get_user(session['user_id'])
    wrong_count = database.get_wrong_count(session['user_id'])
    return render_template('wrong.html', user=user, wrong_count=wrong_count)


@app.route('/wrong-quiz/<int:category_id>')
@login_required
def wrong_quiz(category_id):
    user = database.get_user(session['user_id'])
    return render_template('wrong_quiz.html', user=user, category_id=category_id)


# API接口
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '').strip()

    if not phone or not password:
        return jsonify({'success': False, 'message': '手机号和密码不能为空'})

    if len(phone) != 11 or not phone.isdigit():
        return jsonify({'success': False, 'message': '请输入正确的手机号'})

    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码长度不能少于6位'})

    success, result = database.register_user(phone, password, nickname)
    if success:
        return jsonify({'success': True, 'message': '注册成功', 'user_id': result})
    else:
        return jsonify({'success': False, 'message': result})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    if not phone or not password:
        return jsonify({'success': False, 'message': '手机号和密码不能为空'})

    success, result = database.login_user(phone, password)
    if success:
        session['user_id'] = result['id']
        session['nickname'] = result.get('nickname', result['phone'])
        return jsonify({'success': True, 'message': '登录成功', 'user': result})
    else:
        return jsonify({'success': False, 'message': result})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})


@app.route('/api/user/info')
@login_required
def api_user_info():
    user = database.get_user(session['user_id'])
    stats = database.get_user_stats(session['user_id'])
    return jsonify({'success': True, 'user': user, 'stats': stats})


@app.route('/api/categories')
def api_categories():
    categories = database.get_categories()
    result = []
    for cat in categories:
        sub_cats = database.get_categories(parent_id=cat['id'])
        for sub in sub_cats:
            sub['question_count'] = database.get_question_count(sub['id'])
        cat['children'] = sub_cats
        result.append(cat)
    return jsonify({'success': True, 'categories': result})


@app.route('/api/questions/<int:category_id>')
@login_required
def api_questions(category_id):
    mode = request.args.get('mode', 'random')
    count = int(request.args.get('count', 20))

    if mode == 'random':
        questions = database.get_random_questions(category_id, count)
    else:
        questions = database.get_questions_by_category(category_id, limit=count)

    # 不返回答案
    for q in questions:
        q.pop('answer', None)
        q.pop('analysis', None)

    return jsonify({'success': True, 'questions': questions})


@app.route('/api/question/<int:question_id>/submit', methods=['POST'])
@login_required
def api_submit_answer(question_id):
    data = request.get_json()
    user_answer = data.get('answer', '')

    question = database.get_question(question_id)
    if not question:
        return jsonify({'success': False, 'message': '题目不存在'})

    correct_answer = question['answer']

    # 判断答案是否正确
    is_correct = False
    if question['type'] == 'judge':
        # 判断题
        is_correct = user_answer.strip() == correct_answer.strip()
    elif question['type'] in ('single', 'case'):
        # 单选题和案例题（单选形式）
        is_correct = user_answer.strip().upper() == correct_answer.strip().upper()
    elif question['type'] == 'multiple':
        # 多选题，比较排序后的选项
        user_list = sorted([a.strip().upper() for a in user_answer.split(',') if a.strip()])
        correct_list = sorted([a.strip().upper() for a in correct_answer.split(',') if a.strip()])
        is_correct = user_list == correct_list

    # 记录答题
    database.record_answer(session['user_id'], question_id, user_answer, is_correct)

    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'analysis': question.get('analysis', ''),
        'question': question
    })


@app.route('/api/wrong-questions')
@login_required
def api_wrong_questions():
    category_id = request.args.get('category_id', type=int)
    mastered = request.args.get('mastered', 0, type=int)
    questions = database.get_wrong_questions(session['user_id'], category_id, mastered)

    # 不返回答案
    for q in questions:
        q.pop('answer', None)
        q.pop('analysis', None)

    return jsonify({'success': True, 'questions': questions})


@app.route('/api/wrong-count')
@login_required
def api_wrong_count():
    category_id = request.args.get('category_id', type=int)
    count = database.get_wrong_count(session['user_id'], category_id)
    return jsonify({'success': True, 'count': count})


@app.route('/api/wrong/<int:question_id>/mastered', methods=['POST'])
@login_required
def api_mark_mastered(question_id):
    database.mark_mastered(session['user_id'], question_id)
    return jsonify({'success': True, 'message': '已标记为掌握'})


@app.route('/api/progress')
@login_required
def api_progress():
    progress = database.get_category_progress(session['user_id'])
    return jsonify({'success': True, 'progress': progress})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
