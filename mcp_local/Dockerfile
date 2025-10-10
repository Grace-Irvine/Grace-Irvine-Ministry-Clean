# MCP Service Dockerfile
# 用于AI助手集成的MCP HTTP/SSE服务器

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    MCP_REQUIRE_AUTH=true

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY mcp/ /app/mcp/
COPY core/ /app/core/
COPY config/ /app/config/

# 创建日志目录
RUN mkdir -p /app/logs /app/logs/service_layer

# 设置服务账号凭证环境变量
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service-account.json

# 暴露端口
EXPOSE 8080

# 启动MCP HTTP服务器
CMD ["python", "mcp/mcp_http_server.py"]

