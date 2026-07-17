# 答题系统 - 云端部署指南

## 概述

本系统可以部署到公网，支持5人同时使用。采用以下免费方案：

- **后端托管**: Render (免费层，750小时/月)
- **云数据库**: Supabase (免费层，500MB PostgreSQL)

---

## 第一步：注册账号

### 1.1 注册 Supabase（云数据库）

1. 访问 https://supabase.com
2. 点击 "Start your project" 注册账号（可用GitHub登录）
3. 登录后点击 "New Project" 创建新项目
4. 填写项目信息：
   - Name: `quiz-system` (或你喜欢的名字)
   - Database Password: 设置一个强密码（记下来，后面要用）
   - Region: 选一个离你近的区域（如 `Southeast Asia (Singapore)`）
   - Pricing Plan: Free
5. 点击 "Create new project"，等待数据库创建完成（约2分钟）

### 1.2 注册 Render（后端托管）

1. 访问 https://render.com
2. 点击 "Get Started" 注册账号（可用GitHub登录）
3. 完成注册

---

## 第二步：准备代码仓库

### 2.1 准备GitHub仓库

Render需要从GitHub拉取代码，所以你需要：

1. 注册一个GitHub账号（如果没有）
2. 创建一个新的私有仓库，比如叫 `quiz-system`
3. 将 `quiz-system` 文件夹中的所有文件上传到GitHub仓库

**文件结构应该是这样的：**
```
quiz-system/
├── app.py
├── database.py
├── import_questions.py
├── import_to_cloud.py
├── build.sh
├── requirements.txt
├── .gitignore
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── templates/
│   ├── login.html
│   ├── home.html
│   ├── quiz.html
│   ├── wrong.html
│   └── wrong_quiz.html
└── data/
    └── (数据库文件，不会上传到git)
```

---

## 第三步：获取Supabase数据库连接信息

1. 进入你的Supabase项目
2. 点击左侧菜单的 "Settings" (齿轮图标)
3. 点击 "Database"
4. 在 "Connection string" 部分，选择 "URI" 标签
5. 复制那个连接字符串，格式类似：
   ```
   postgresql://postgres:你的密码@db.xxxxxx.supabase.co:5432/postgres
   ```

6. 从这个连接字符串中提取以下信息：
   - **Host**: `db.xxxxxx.supabase.co`
   - **Port**: `5432`
   - **Database Name**: `postgres`
   - **User**: `postgres`
   - **Password**: 你设置的数据库密码

---

## 第四步：将题库导入到云端数据库

在本地电脑上执行以下步骤：

### 4.1 安装PostgreSQL驱动

```bash
pip3 install psycopg2-binary
```

### 4.2 设置环境变量并运行导入脚本

```bash
# 设置数据库连接信息（替换为你自己的信息）
export DB_TYPE=postgresql
export DB_HOST=db.xxxxxx.supabase.co
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=你的数据库密码

# 运行导入脚本
cd quiz-system
python3 import_to_cloud.py
```

等待导入完成，你会看到：
```
成功导入 921 道题目
云端题库总数：921 题
```

---

## 第五步：部署后端到Render

### 5.1 创建Web Service

1. 登录Render
2. 点击 "New" -> "Web Service"
3. 选择 "Public Git repository" 或连接你的GitHub账号
4. 选择你刚才创建的 `quiz-system` 仓库
5. 填写配置：
   - **Name**: `quiz-system` (或你喜欢的名字)
   - **Region**: 选一个近的区域
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && bash build.sh`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
   - **Instance Type**: Free (免费)

### 5.2 添加环境变量

在 "Environment Variables" 部分，添加以下变量：

| Key | Value |
|-----|-------|
| `DB_TYPE` | `postgresql` |
| `DB_HOST` | `db.xxxxxx.supabase.co` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `postgres` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `你的数据库密码` |

### 5.3 部署

点击 "Create Web Service"，等待部署完成（约3-5分钟）。

部署成功后，你会看到一个类似 `https://quiz-system-xxxx.onrender.com` 的网址，这就是你的公网访问地址。

---

## 第六步：测试访问

1. 用浏览器打开你的Render网址
2. 注册一个账号测试
3. 试试答题功能
4. 用手机浏览器也打开试试（响应式设计，适配手机）

---

## 免费层限制说明

### Supabase 免费层
- 500MB 数据库空间（存题库和用户数据完全够用）
- 5GB 带宽/月（5人使用完全够用）
- 项目7天不活跃可能暂停（需要手动恢复）

### Render 免费层
- 750小时/月运行时间（一个月30天=720小时，所以可以24小时运行）
- 512MB 内存（5人使用完全够用）
- 100秒无请求会冷启动（第一次访问可能慢几秒）
- 每月有100GB带宽

### 注意事项
- 两个平台都是免费的，不需要绑定信用卡也可以用
- 如果使用人数增加或需要更高可用性，可以随时升级付费层
- 记得定期备份数据库（Supabase后台有备份功能）

---

## 常见问题

### Q: 部署后第一次访问很慢？
A: Render免费层100秒无请求会休眠，第一次访问需要唤醒（约5-10秒），之后就正常了。

### Q: 数据库连接失败怎么办？
A: 检查环境变量是否正确，特别是DB_HOST和DB_PASSWORD。可以在本地用import_to_cloud.py测试连接。

### Q: 可以用其他数据库吗？
A: 可以，代码支持SQLite和PostgreSQL。如果你想用其他免费数据库（如Neon、PlanetScale等），只要是PostgreSQL兼容的都可以。

### Q: 可以用其他托管平台吗？
A: 可以，比如Railway、Fly.io、PythonAnywhere等，只要支持Python就行。配置方法类似。

### Q: 手机怎么访问？
A: 手机浏览器直接输入你的Render网址就可以用，界面是自适应的。

---

## 本地运行

如果只是想在本地电脑上运行，不需要部署到云端：

```bash
cd quiz-system
python3 app.py
```

然后访问 http://localhost:8080

本地运行使用SQLite数据库，数据存在 `data/quiz.db` 文件中。
