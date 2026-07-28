# 成绩管理与分析平台

普通高中教学质量分析系统，支持多角色（管理员/教学主管/教师/学生/家长）的成绩录入、查询、排名、统计分析和可视化。

## 技术栈

- **后端**: FastAPI + SQLAlchemy 2.0 (async) + Celery + MySQL/SQLite + Redis
- **前端**: Vue 3 + Element Plus + ECharts + Pinia + TypeScript
- **部署**: Docker Compose + Nginx

## 快速启动 (Docker)

```bash
# 1. 克隆项目
git clone https://github.com/your-username/score-platform.git
cd score-platform

# 2. 配置环境变量
cp .env.example .env

# 3. 启动所有服务
docker compose up -d

# 4. 访问
#   前端: http://localhost
#   API文档: http://localhost:8000/api/docs
# 默认管理员: admin / admin123
```

## 本地开发

```bash
# 后端
pip install -r requirements.txt
cp .env.example .env
python init_db.py
uvicorn app.main:app --reload --port 8000

# 前端 (新终端)
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

# Windows 部署

# 1. 安装 Python 3.11+ 和 Node.js 18+
# 下载: https://python.org  |  https://nodejs.org

# 2. 克隆项目
cd d:\
git clone https://github.com/你的用户名/score-platform.git
cd score-platform

# 3. 启动后端
pip install -r requirements.txt
copy .env.example .env
python init_db.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. 启动前端（新终端）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
Linux 部署 (Ubuntu)

# 1. 安装依赖
sudo apt update
sudo apt install -y python3.11 python3-pip nodejs npm

# 2. 克隆并启动
git clone https://github.com/用户名/score-platform.git
cd score-platform
pip install -r requirements.txt
cp .env.example .env
python init_db.py
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 3. 前端
cd frontend && npm install && npm run build

# 4. Nginx 反向代理（可选）
sudo cp nginx.conf /etc/nginx/sites-available/score
sudo ln -s /etc/nginx/sites-available/score /etc/nginx/sites-enabled/
sudo nginx -s reload
macOS 部署

# 1. 安装依赖
brew install python@3.11 node

# 2. 启动后端
git clone https://github.com/用户名/score-platform.git
cd score-platform
pip3 install -r requirements.txt
cp .env.example .env
python3 init_db.py
python3 -m uvicorn app.main:app --port 8000

# 3. 启动前端
cd frontend && npm install && npm run dev
Docker 通用部署（三系统通用）：


cd score-platform
cp .env.example .env
docker compose up -d
# 访问 http://localhost
默认管理员：admin / admin123

## 功能概览

- 用户管理 (RBAC 5角色14权限)
- 年级/班级/学生管理
- 考试管理 + 成绩录入/导入
- 排名计算 (总分/语数外/7选3)
- 成绩查询 (按班级/学生/年级)
- 统计分析 (班级统计/班级对比/分数段/趋势图)
- 分数线设置
- 报表导出 (Excel/HTML)
