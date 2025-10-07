# 使用 Python 3.11 官方镜像作为基础镜像
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

# 复制所有项目文件
COPY . /app/

# 创建日志目录
RUN mkdir -p /app/logs /app/logs/service_layer

# 设置服务账号凭证环境变量
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service-account.json

# 暴露端口（Cloud Run 会自动设置 PORT 环境变量）
EXPOSE 8080

# 启动脚本：根据 MCP_MODE 环境变量选择启动模式
# MCP_MODE=http -> 启动 MCP HTTP Server (mcp_http_server.py)
# 默认 -> 启动原有 FastAPI 应用 (app.py)
CMD if [ "$MCP_MODE" = "http" ]; then \
        echo "Starting MCP HTTP Server..."; \
        python mcp_http_server.py; \
    else \
        echo "Starting FastAPI Application..."; \
        python app.py; \
    fi

