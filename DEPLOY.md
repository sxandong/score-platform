# 成绩管理与分析平台 — 部署文档

## 环境要求

- Docker 24+ & Docker Compose v2
- Python 3.11+ (本地开发)
- Node.js 18+ (前端开发)

## 快速启动 (Docker)

```bash
# 1. 克隆项目
cd score-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env：修改 JWT_SECRET 为随机字符串，配置 DB_PASSWORD

# 3. 启动所有服务
docker compose up -d

# 4. 初始化数据库（首次启动自动建表+种子数据）
# 默认管理员: admin / admin123

# 5. 访问
#   - 前端: http://localhost
#   - API文档: http://localhost:8000/api/docs
```

## 服务架构

| 服务 | 端口 | 说明 |
|------|------|------|
| nginx | 80 | 反向代理 + 前端静态资源 |
| app | 8000 | FastAPI 后端 |
| mysql | 3306 | MySQL 8.0 主库 |
| redis | 6379 | Redis 7 缓存 |
| celery | - | 异步任务 worker |

## 本地开发

```bash
# 后端
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 前端 (新终端)
cd frontend
npm install
npm run dev    # 访问 http://localhost:5173

# Celery (新终端，需要先启动 Redis)
celery -A app.core.celery_app worker --loglevel=info
```

## 生产部署检查清单

1. [ ] 修改 `.env` 中 JWT_SECRET 为强随机字符串 (>32字符)
2. [ ] 修改 MySQL root 密码
3. [ ] 配置 HTTPS (Certbot + Let's Encrypt)
4. [ ] 配置数据库定期备份 (mysqldump + cron)
5. [ ] 设置防火墙规则 (仅开放 80/443)
6. [ ] 配置日志采集 (ELK 或 Loki)
7. [ ] 首次登录后修改 admin 密码
