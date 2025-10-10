# API Service - 数据清洗和管理API

FastAPI应用，提供数据清洗、服务层生成和数据查询的RESTful API。

## 🎯 功能

### 核心功能
- **数据清洗API**: 从Google Sheets读取原始数据并清洗
- **服务层生成**: 转换为sermon和volunteer领域模型
- **数据查询**: RESTful API查询证道和同工数据
- **统计分析**: 讲员统计、同工统计、排班分析
- **变化检测**: 智能检测数据变化，避免重复处理

### API端点

#### 核心端点
- `GET /` - 健康检查和服务信息
- `GET /health` - 健康状态
- `POST /api/v1/clean` - 触发数据清洗
- `POST /api/v1/service-layer/generate` - 生成服务层数据

#### 数据查询
- `GET /api/v1/sermon` - 获取证道数据
- `GET /api/v1/volunteer` - 获取同工数据
- `GET /api/v1/sermon/by-preacher/{name}` - 按讲员查询
- `GET /api/v1/volunteer/by-person/{id}` - 按人员查询

#### 统计分析
- `GET /api/v1/stats/preachers` - 讲员统计
- `GET /api/v1/stats/volunteers` - 同工统计
- `GET /api/v1/volunteer/availability/{year_month}` - 排班空缺

完整API文档: `/docs` (Swagger UI)

## 🚀 本地开发

### 前置要求
- Python 3.11+
- Google Cloud服务账号（用于访问Google Sheets）

### 安装依赖
```bash
# 从项目根目录
pip install -r requirements.txt
```

### 配置
1. 将服务账号JSON放在 `config/service-account.json`
2. 编辑 `config/config.json` 配置数据源

### 运行
```bash
# 从项目根目录
python api/app.py
```

服务将在 http://localhost:8080 启动

### 测试API
```bash
# 健康检查
curl http://localhost:8080/health

# 触发清洗（dry-run）
curl -X POST http://localhost:8080/api/v1/clean \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 查看API文档
open http://localhost:8080/docs
```

## 📦 Docker部署

### 构建镜像
```bash
# 从项目根目录
docker build -f api/Dockerfile -t ministry-data-api .
```

### 运行容器
```bash
docker run -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -e PORT=8080 \
  ministry-data-api
```

## ☁️ Cloud Run部署

### 快速部署
```bash
# 设置环境变量
export GCP_PROJECT_ID=your-project-id

# 部署
cd deploy
./deploy-api.sh
```

### 环境变量
- `PORT`: 服务端口（默认8080）
- `SCHEDULER_TOKEN`: Cloud Scheduler认证令牌
- `GOOGLE_APPLICATION_CREDENTIALS`: 服务账号路径

## 🔧 架构

### 目录结构
```
api/
├── app.py           # FastAPI应用主文件
├── Dockerfile       # Docker构建文件
└── README.md        # 本文档
```

### 依赖
- **FastAPI**: Web框架
- **Uvicorn**: ASGI服务器
- **Pandas**: 数据处理
- **core/***: 共享业务逻辑

### 数据流
```
Google Sheets → 清洗 → 服务层 → Cloud Storage
                ↓
              API端点
```

## 📊 监控

### 日志
```bash
# Cloud Run日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ministry-data-api" --limit 50
```

### 健康检查
```bash
curl https://ministry-data-api-xxx.run.app/health
```

## 🔗 相关文档
- [部署指南](../docs/DEPLOYMENT.md)
- [API端点文档](../docs/API_ENDPOINTS.md)
- [服务层架构](../docs/SERVICE_LAYER.md)
- [主README](../README.md)

