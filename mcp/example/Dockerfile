# Weekly Preview Scheduler Dockerfile
# 用于定时生成每周事工预览并发送邮件的服务

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（从项目根目录）
COPY requirements.txt /app/requirements.txt

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制项目文件
COPY mcp/example/weekly_preview_scheduler.py /app/weekly_preview_scheduler.py

# 复制配置文件（如果需要）
COPY config/ /app/config/

# 设置服务账号凭证环境变量（如果使用）
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service-account.json

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["python", "weekly_preview_scheduler.py"]
