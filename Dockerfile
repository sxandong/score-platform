# Stage 1: 依赖安装
FROM python:3.11-slim AS builder

WORKDIR /app

# 利用缓存: 先复制依赖文件
COPY requirements.txt .

# 安装依赖到独立目录
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: 运行环境
FROM python:3.11-slim

WORKDIR /app

# 从 builder 复制依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 创建非root用户运行应用
RUN useradd -m -u 1000 appuser && \
    mkdir -p uploads && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 使用 gunicorn 或 uvicorn 多 worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop"]