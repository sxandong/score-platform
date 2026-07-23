# 成绩管理与分析平台

高中成绩管理与分析平台，支持多角色（管理员/教学主管/教师/学生/家长）的成绩录入、查询、排名、统计分析和可视化。

## 技术栈

- **后端:** FastAPI + SQLAlchemy 2.0 (async) + Celery + MySQL + Redis
- **前端:** Vue 3 + Element Plus + ECharts + Pinia + TypeScript
- **部署:** Docker Compose + Nginx

## 功能概览

| 模块 | 功能 |
|------|------|
| 认证鉴权 | JWT 登录/刷新, RBAC 5角色14权限 |
| 用户管理 | CRUD + 角色分配 |
| 考试管理 | 创建/编辑/锁定考试, 科目配置 |
| 成绩录入 | 单条录入 + Excel批量导入 + 校验 |
| 成绩查询 | 班级成绩单, 学生成绩, 多维度筛选 |
| 排名计算 | Celery异步任务, 总分/单科排名 |
| 统计分析 | 班级横向对比, 学生纵向趋势, 年级总览 |
| 报表导出 | Excel成绩单导出 |

## 快速启动

```bash
docker compose up -d
# 访问 http://localhost
# 默认管理员: admin / admin123
```

## 项目结构

```
score-platform/
├── app/
│   ├── core/           # 基础设施 (DB, JWT, Celery)
│   ├── models/         # 15个SQLAlchemy模型
│   └── modules/        # 业务模块 (auth/users/exams/scores/analysis/reports)
├── frontend/           # Vue3前端
├── tests/              # 测试
└── docker-compose.yml  # 编排配置
```
