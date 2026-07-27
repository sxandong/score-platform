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

## 功能概览

- 用户管理 (RBAC 5角色14权限)
- 年级/班级/学生管理
- 考试管理 + 成绩录入/导入
- 排名计算 (总分/语数外/7选3)
- 成绩查询 (按班级/学生/年级)
- 统计分析 (班级统计/班级对比/分数段/趋势图)
- 分数线设置
- 报表导出 (Excel/HTML)
