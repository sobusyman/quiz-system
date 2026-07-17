import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

# 数据库类型：sqlite 或 postgresql
DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')

# SQLite配置
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'quiz.db')

# PostgreSQL配置
DB_HOST = os.environ.get('DB_HOST', '')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', '')
DB_USER = os.environ.get('DB_USER', '')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

# 全局PostgreSQL连接池（用于psycopg2）
_pg_conn = None


def get_db():
    """获取数据库连接"""
    if DB_TYPE == 'postgresql':
        return _get_postgres_conn()
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _get_postgres_conn():
    """获取PostgreSQL连接"""
    global _pg_conn
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    if _pg_conn is None or _pg_conn.closed:
        _pg_conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    return _pg_conn


def execute_query(query, params=None, fetch=True):
    """执行查询，返回结果列表（字典形式）"""
    conn = get_db()
    
    if DB_TYPE == 'postgresql':
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    try:
        cursor.execute(query, params or ())
        conn.commit()
        
        if fetch:
            rows = cursor.fetchall()
            if DB_TYPE == 'postgresql':
                return [dict(row) for row in rows]
            else:
                return [dict(row) for row in rows]
        else:
            # 对于INSERT，返回lastrowid
            if DB_TYPE == 'postgresql':
                # PostgreSQL需要用RETURNING id来获取插入的ID
                return cursor.fetchone() if cursor.description else None
            else:
                return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


def execute_insert(query, params=None):
    """执行插入，返回新插入记录的ID"""
    conn = get_db()
    
    if DB_TYPE == 'postgresql':
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # PostgreSQL需要RETURNING子句
        if 'RETURNING' not in query.upper():
            query += ' RETURNING id'
    else:
        cursor = conn.cursor()
    
    try:
        cursor.execute(query, params or ())
        conn.commit()
        
        if DB_TYPE == 'postgresql':
            result = cursor.fetchone()
            return result['id'] if result else None
        else:
            return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


def init_db():
    """初始化数据库表"""
    if DB_TYPE == 'postgresql':
        _init_postgres()
    else:
        _init_sqlite()


def _init_sqlite():
    """初始化SQLite数据库"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 题库分类表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            parent_id INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # 题目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            question TEXT NOT NULL,
            options TEXT,
            answer TEXT NOT NULL,
            analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')

    # 答题记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            user_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')

    # 错题库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wrong_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            wrong_count INTEGER DEFAULT 1,
            last_wrong_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mastered INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (question_id) REFERENCES questions (id),
            UNIQUE(user_id, question_id)
        )
    ''')

    # 学习进度表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            total_questions INTEGER DEFAULT 0,
            answered_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id),
            UNIQUE(user_id, category_id)
        )
    ''')

    conn.commit()
    conn.close()


def _init_postgres():
    """初始化PostgreSQL数据库"""
    conn = get_db()
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor()

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            phone VARCHAR(20) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            nickname VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 题库分类表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            parent_id INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # 题目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            type VARCHAR(20) NOT NULL,
            question TEXT NOT NULL,
            options TEXT,
            answer VARCHAR(100) NOT NULL,
            analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 答题记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            question_id INTEGER NOT NULL REFERENCES questions(id),
            user_answer VARCHAR(100),
            is_correct INTEGER DEFAULT 0,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 错题库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wrong_questions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            question_id INTEGER NOT NULL REFERENCES questions(id),
            wrong_count INTEGER DEFAULT 1,
            last_wrong_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mastered INTEGER DEFAULT 0,
            UNIQUE(user_id, question_id)
        )
    ''')

    # 学习进度表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            category_id INTEGER NOT NULL REFERENCES categories(id),
            total_questions INTEGER DEFAULT 0,
            answered_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            UNIQUE(user_id, category_id)
        )
    ''')

    conn.commit()
    cursor.close()


# ==================== 用户相关操作 ====================

def register_user(phone, password, nickname=None):
    """注册用户"""
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    try:
        if DB_TYPE == 'postgresql':
            user_id = execute_insert(
                'INSERT INTO users (phone, password, nickname) VALUES (%s, %s, %s)',
                (phone, hashed_password, nickname or phone)
            )
        else:
            import sqlite3
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (phone, password, nickname) VALUES (?, ?, ?)',
                (phone, hashed_password, nickname or phone)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
        return True, user_id
    except Exception as e:
        if 'UNIQUE' in str(e).upper() or 'unique' in str(e):
            return False, '该手机号已注册'
        return False, str(e)


def login_user(phone, password):
    """用户登录"""
    if DB_TYPE == 'postgresql':
        users = execute_query(
            'SELECT * FROM users WHERE phone = %s',
            (phone,)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        conn.close()
        users = [dict(row)] if row else []
    
    if users:
        user = users[0]
        if check_password_hash(user['password'], password):
            return True, user
    return False, '手机号或密码错误'


def get_user(user_id):
    """获取用户信息"""
    if DB_TYPE == 'postgresql':
        users = execute_query(
            'SELECT id, phone, nickname, created_at FROM users WHERE id = %s',
            (user_id,)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, phone, nickname, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        users = [dict(row)] if row else []
    
    return users[0] if users else None


# ==================== 题库分类相关操作 ====================

def add_category(name, description='', parent_id=0, sort_order=0):
    """添加分类"""
    if DB_TYPE == 'postgresql':
        return execute_insert(
            'INSERT INTO categories (name, description, parent_id, sort_order) VALUES (%s, %s, %s, %s)',
            (name, description, parent_id, sort_order)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO categories (name, description, parent_id, sort_order) VALUES (?, ?, ?, ?)',
            (name, description, parent_id, sort_order)
        )
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        return category_id


def get_categories(parent_id=0):
    """获取分类列表"""
    if DB_TYPE == 'postgresql':
        return execute_query(
            'SELECT * FROM categories WHERE parent_id = %s ORDER BY sort_order, id',
            (parent_id,)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM categories WHERE parent_id = ? ORDER BY sort_order, id',
            (parent_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


def get_all_categories():
    """获取所有分类"""
    if DB_TYPE == 'postgresql':
        return execute_query('SELECT * FROM categories ORDER BY sort_order, id')
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories ORDER BY sort_order, id')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# ==================== 题目相关操作 ====================

def add_question(category_id, q_type, question, options, answer, analysis=''):
    """添加题目"""
    options_json = json.dumps(options, ensure_ascii=False) if options else None
    
    if DB_TYPE == 'postgresql':
        return execute_insert(
            'INSERT INTO questions (category_id, type, question, options, answer, analysis) VALUES (%s, %s, %s, %s, %s, %s)',
            (category_id, q_type, question, options_json, answer, analysis)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO questions (category_id, type, question, options, answer, analysis) VALUES (?, ?, ?, ?, ?, ?)',
            (category_id, q_type, question, options_json, answer, analysis)
        )
        conn.commit()
        question_id = cursor.lastrowid
        conn.close()
        return question_id


def _parse_options(question_dict):
    """解析选项JSON"""
    if question_dict.get('options'):
        question_dict['options'] = json.loads(question_dict['options'])
    else:
        question_dict['options'] = []
    return question_dict


def get_questions_by_category(category_id, limit=None, offset=0):
    """按分类获取题目"""
    if DB_TYPE == 'postgresql':
        query = 'SELECT * FROM questions WHERE category_id = %s ORDER BY id'
        params = [category_id]
        if limit:
            query += ' LIMIT %s OFFSET %s'
            params.extend([limit, offset])
        questions = execute_query(query, tuple(params))
    else:
        conn = get_db()
        cursor = conn.cursor()
        query = 'SELECT * FROM questions WHERE category_id = ? ORDER BY id'
        params = [category_id]
        if limit:
            query += ' LIMIT ? OFFSET ?'
            params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        questions = [dict(row) for row in rows]
    
    return [_parse_options(q) for q in questions]


def get_question_count(category_id=None):
    """获取题目数量"""
    if DB_TYPE == 'postgresql':
        if category_id:
            result = execute_query(
                'SELECT COUNT(*) as count FROM questions WHERE category_id = %s',
                (category_id,)
            )
        else:
            result = execute_query('SELECT COUNT(*) as count FROM questions')
    else:
        conn = get_db()
        cursor = conn.cursor()
        if category_id:
            cursor.execute('SELECT COUNT(*) as count FROM questions WHERE category_id = ?', (category_id,))
        else:
            cursor.execute('SELECT COUNT(*) as count FROM questions')
        row = cursor.fetchone()
        conn.close()
        result = [dict(row)]
    
    return result[0]['count'] if result else 0


def get_random_questions(category_id, count=10):
    """随机获取题目"""
    if DB_TYPE == 'postgresql':
        questions = execute_query(
            'SELECT * FROM questions WHERE category_id = %s ORDER BY RANDOM() LIMIT %s',
            (category_id, count)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM questions WHERE category_id = ? ORDER BY RANDOM() LIMIT ?',
            (category_id, count)
        )
        rows = cursor.fetchall()
        conn.close()
        questions = [dict(row) for row in rows]
    
    return [_parse_options(q) for q in questions]


def get_question(question_id):
    """获取单道题目"""
    if DB_TYPE == 'postgresql':
        questions = execute_query(
            'SELECT * FROM questions WHERE id = %s',
            (question_id,)
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
        row = cursor.fetchone()
        conn.close()
        questions = [dict(row)] if row else []
    
    if questions:
        return _parse_options(questions[0])
    return None


# ==================== 答题记录相关操作 ====================

def record_answer(user_id, question_id, user_answer, is_correct):
    """记录答题结果"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if DB_TYPE == 'postgresql':
            placeholder = '%s'
        else:
            placeholder = '?'
        
        # 记录答题记录
        cursor.execute(
            f'INSERT INTO answer_records (user_id, question_id, user_answer, is_correct) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})',
            (user_id, question_id, user_answer, 1 if is_correct else 0)
        )

        # 获取题目分类
        cursor.execute(
            f'SELECT category_id FROM questions WHERE id = {placeholder}',
            (question_id,)
        )
        category_id = cursor.fetchone()['category_id']

        # 更新学习进度 - 插入或忽略
        if DB_TYPE == 'postgresql':
            cursor.execute(
                'INSERT INTO user_progress (user_id, category_id) VALUES (%s, %s) ON CONFLICT (user_id, category_id) DO NOTHING',
                (user_id, category_id)
            )
            cursor.execute(
                'UPDATE user_progress SET answered_count = answered_count + 1, correct_count = correct_count + %s WHERE user_id = %s AND category_id = %s',
                (1 if is_correct else 0, user_id, category_id)
            )
            cursor.execute(
                'UPDATE user_progress SET total_questions = (SELECT COUNT(*) FROM questions WHERE category_id = %s) WHERE user_id = %s AND category_id = %s',
                (category_id, user_id, category_id)
            )
        else:
            cursor.execute(
                'INSERT OR IGNORE INTO user_progress (user_id, category_id) VALUES (?, ?)',
                (user_id, category_id)
            )
            cursor.execute(
                'UPDATE user_progress SET answered_count = answered_count + 1, correct_count = correct_count + ? WHERE user_id = ? AND category_id = ?',
                (1 if is_correct else 0, user_id, category_id)
            )
            cursor.execute(
                'UPDATE user_progress SET total_questions = (SELECT COUNT(*) FROM questions WHERE category_id = ?) WHERE user_id = ? AND category_id = ?',
                (category_id, user_id, category_id)
            )

        # 错题库处理
        if not is_correct:
            if DB_TYPE == 'postgresql':
                cursor.execute(
                    '''INSERT INTO wrong_questions (user_id, question_id, wrong_count, last_wrong_at)
                       VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                       ON CONFLICT (user_id, question_id)
                       DO UPDATE SET wrong_count = wrong_questions.wrong_count + 1, last_wrong_at = CURRENT_TIMESTAMP, mastered = 0''',
                    (user_id, question_id)
                )
            else:
                cursor.execute(
                    '''INSERT INTO wrong_questions (user_id, question_id, wrong_count, last_wrong_at)
                       VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                       ON CONFLICT(user_id, question_id)
                       DO UPDATE SET wrong_count = wrong_count + 1, last_wrong_at = CURRENT_TIMESTAMP, mastered = 0''',
                    (user_id, question_id)
                )
        else:
            cursor.execute(
                f'UPDATE wrong_questions SET mastered = 1 WHERE user_id = {placeholder} AND question_id = {placeholder}',
                (user_id, question_id)
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        # PostgreSQL连接不关闭，复用
        if DB_TYPE != 'postgresql':
            conn.close()


# ==================== 错题库相关操作 ====================

def get_wrong_questions(user_id, category_id=None, mastered=0):
    """获取错题库"""
    if DB_TYPE == 'postgresql':
        query = '''SELECT q.*, w.wrong_count, w.last_wrong_at, w.mastered
                   FROM wrong_questions w
                   JOIN questions q ON w.question_id = q.id
                   WHERE w.user_id = %s AND w.mastered = %s'''
        params = [user_id, mastered]
        if category_id:
            query += ' AND q.category_id = %s'
            params.append(category_id)
        query += ' ORDER BY w.last_wrong_at DESC'
        questions = execute_query(query, tuple(params))
    else:
        conn = get_db()
        cursor = conn.cursor()
        query = '''SELECT q.*, w.wrong_count, w.last_wrong_at, w.mastered
                   FROM wrong_questions w
                   JOIN questions q ON w.question_id = q.id
                   WHERE w.user_id = ? AND w.mastered = ?'''
        params = [user_id, mastered]
        if category_id:
            query += ' AND q.category_id = ?'
            params.append(category_id)
        query += ' ORDER BY w.last_wrong_at DESC'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        questions = [dict(row) for row in rows]
    
    return [_parse_options(q) for q in questions]


def get_wrong_count(user_id, category_id=None):
    """获取错题数量"""
    if DB_TYPE == 'postgresql':
        query = 'SELECT COUNT(*) as count FROM wrong_questions WHERE user_id = %s AND mastered = 0'
        params = [user_id]
        if category_id:
            query += ' AND question_id IN (SELECT id FROM questions WHERE category_id = %s)'
            params.append(category_id)
        result = execute_query(query, tuple(params))
    else:
        conn = get_db()
        cursor = conn.cursor()
        query = 'SELECT COUNT(*) as count FROM wrong_questions WHERE user_id = ? AND mastered = 0'
        params = [user_id]
        if category_id:
            query += ' AND question_id IN (SELECT id FROM questions WHERE category_id = ?)'
            params.append(category_id)
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        result = [dict(row)]
    
    return result[0]['count'] if result else 0


def mark_mastered(user_id, question_id):
    """标记为已掌握"""
    if DB_TYPE == 'postgresql':
        execute_query(
            'UPDATE wrong_questions SET mastered = 1 WHERE user_id = %s AND question_id = %s',
            (user_id, question_id),
            fetch=False
        )
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE wrong_questions SET mastered = 1 WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )
        conn.commit()
        conn.close()


# ==================== 学习统计相关操作 ====================

def get_user_stats(user_id):
    """获取用户统计数据"""
    if DB_TYPE == 'postgresql':
        result = execute_query('''
            SELECT
                (SELECT COUNT(*) FROM answer_records WHERE user_id = %s) as total_answered,
                (SELECT COUNT(*) FROM answer_records WHERE user_id = %s AND is_correct = 1) as total_correct,
                (SELECT COUNT(*) FROM wrong_questions WHERE user_id = %s AND mastered = 0) as wrong_count
        ''', (user_id, user_id, user_id))
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                (SELECT COUNT(*) FROM answer_records WHERE user_id = ?) as total_answered,
                (SELECT COUNT(*) FROM answer_records WHERE user_id = ? AND is_correct = 1) as total_correct,
                (SELECT COUNT(*) FROM wrong_questions WHERE user_id = ? AND mastered = 0) as wrong_count
        ''', (user_id, user_id, user_id))
        row = cursor.fetchone()
        conn.close()
        result = [dict(row)]
    
    return result[0] if result else {'total_answered': 0, 'total_correct': 0, 'wrong_count': 0}


def get_category_progress(user_id):
    """获取分类学习进度"""
    if DB_TYPE == 'postgresql':
        return execute_query('''
            SELECT c.id, c.name, up.answered_count, up.correct_count, up.total_questions
            FROM categories c
            LEFT JOIN user_progress up ON c.id = up.category_id AND up.user_id = %s
            WHERE c.parent_id != 0
            ORDER BY c.sort_order, c.id
        ''', (user_id,))
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, up.answered_count, up.correct_count, up.total_questions
            FROM categories c
            LEFT JOIN user_progress up ON c.id = up.category_id AND up.user_id = ?
            WHERE c.parent_id != 0
            ORDER BY c.sort_order, c.id
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
