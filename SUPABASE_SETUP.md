# Supabase 数据库初始化指南

## 方法一：使用 SQL 编辑器（最简单，推荐）

### 步骤

1. **打开你的 Supabase 项目**
   - 登录 https://supabase.com
   - 进入 `quiz-system` 项目

2. **打开 SQL 编辑器**
   - 点击左侧菜单的 **SQL Editor**（图标像 "< >" 的那个）
   - 点击 **New query** 或 **+** 新建一个查询

3. **导入 SQL 文件**
   - 有两种方式：
     
     **方式A：直接复制粘贴（推荐，文件449KB，完全可以粘贴）**
     - 打开 `quiz-system/data/supabase_init.sql` 文件
     - 全选复制所有内容
     - 粘贴到 Supabase 的 SQL 编辑器里
     
     **方式B：上传文件**
     - 点击 SQL 编辑器里的上传按钮（如果有的话）
     - 选择 `quiz-system/data/supabase_init.sql` 文件

4. **运行 SQL**
   - 点击右下角的 **Run** 或 **▶ Execute** 按钮
   - 等待执行完成（大约 10-30 秒）
   - 你会看到 "Success. No rows returned" 之类的成功提示

5. **验证数据**
   - 点击左侧菜单的 **Table Editor**（表格图标）
   - 应该能看到以下几张表：
     - `users` — 用户表
     - `categories` — 分类表（6条数据）
     - `questions` — 题目表（921条数据）
     - `answer_records` — 答题记录表
     - `wrong_questions` — 错题库表
     - `user_progress` — 学习进度表
   - 点开 `questions` 表，确认有921条数据

---

## 方法二：如果方法一不行，用这个

如果SQL编辑器执行报错（比如文件太大），可以分步执行：

### 第一步：先建表

在SQL编辑器中运行以下SQL：

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    parent_id INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    type VARCHAR(20) NOT NULL,
    question TEXT NOT NULL,
    options TEXT,
    answer VARCHAR(100) NOT NULL,
    analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE answer_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    user_answer VARCHAR(100),
    is_correct INTEGER DEFAULT 0,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wrong_questions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    wrong_count INTEGER DEFAULT 1,
    last_wrong_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mastered INTEGER DEFAULT 0,
    UNIQUE(user_id, question_id)
);

CREATE TABLE user_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    total_questions INTEGER DEFAULT 0,
    answered_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    UNIQUE(user_id, category_id)
);
```

点击 Run 执行。

### 第二步：导入分类数据

接着运行：

```sql
INSERT INTO categories (id, name, description, parent_id, sort_order) VALUES
(1, '公共部分题库', '安全生产公共基础知识', 0, 1),
(2, '危险货物运输专业题库', '危险货物运输专业知识', 0, 2),
(3, '法律法规', '安全生产相关法律法规', 1, 1),
(4, '安全管理', '安全生产管理知识', 1, 2),
(5, '基础知识', '危险货物运输基础知识', 2, 1),
(6, '专业知识', '危险货物运输专业知识', 2, 2);

SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));
```

点击 Run 执行。

### 第三步：导入题目数据

这部分数据比较多，还是直接打开 `supabase_init.sql` 文件，从 `-- 导入题目数据` 那一行开始复制到末尾，粘贴到SQL编辑器里运行。

---

## 常见问题

### Q: 执行报错说表已经存在？
A: 说明你之前创建过表。可以先运行以下SQL删除所有表，再重新执行：
```sql
DROP TABLE IF EXISTS user_progress;
DROP TABLE IF EXISTS wrong_questions;
DROP TABLE IF EXISTS answer_records;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
```

### Q: 执行超时？
A: Supabase免费版有执行时间限制。可以把题目数据分成几次导入，每次导入200题左右。

### Q: 怎么确认数据导入成功了？
A: 在 Table Editor 里看：
- categories 表应该有 6 条记录
- questions 表应该有 921 条记录

---

## 下一步

数据库初始化完成后，继续部署后端到 Render。详见 `DEPLOY.md`。
