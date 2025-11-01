# Secrets 清单 - Secrets Inventory

本文档列出了所有 Cloud Run 服务和 Scheduler 需要的 secrets，以及它们在 Google Secret Manager 中的配置。

## 📋 服务概览

### Cloud Run 服务（3个）

1. **ministry-data-mcp** (MCP Server)
   - 用途: AI 助手集成（MCP 协议）
   - Secrets: 1个

2. **ministry-data-cleaning** (API Service)
   - 用途: 数据清洗 API
   - Secrets: 1个

3. **weekly-preview-scheduler** (Weekly Preview Service)
   - 用途: 每周事工预览生成和邮件发送
   - Secrets: 3个

### Cloud Scheduler（2个）

1. **ministry-data-cleaning-scheduler**
   - 用途: 定时触发 API 服务的清洗任务
   - 使用 Secret: `api-scheduler-token`

2. **weekly-preview-job**
   - 用途: 定时触发每周预览生成（每周一早上9点）
   - 使用 Secret: `weekly-preview-scheduler-token`

## 🔐 Secrets 清单

### 1. mcp-bearer-token

**服务**: ministry-data-mcp (MCP Server)  
**用途**: MCP HTTP/SSE 端点的 Bearer Token 认证  
**类型**: Token  
**环境变量**: `MCP_BEARER_TOKEN`  
**Secret Manager 名称**: `mcp-bearer-token`

**创建方式**:
```bash
# 生成 token
TOKEN=$(openssl rand -hex 32)

# 创建 secret
echo -n "$TOKEN" | gcloud secrets create mcp-bearer-token --data-file=-

# 或更新现有 secret
echo -n "$TOKEN" | gcloud secrets versions add mcp-bearer-token --data-file=-
```

**授权访问**:
```bash
gcloud secrets add-iam-policy-binding mcp-bearer-token \
  --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

### 2. api-scheduler-token

**服务**: ministry-data-cleaning (API Service)  
**用途**: Cloud Scheduler 调用 API 服务的认证令牌  
**类型**: Token  
**环境变量**: `SCHEDULER_TOKEN`  
**Secret Manager 名称**: `api-scheduler-token`

**创建方式**:
```bash
# 生成 token
TOKEN=$(openssl rand -hex 32)

# 创建 secret
echo -n "$TOKEN" | gcloud secrets create api-scheduler-token --data-file=-

# 或更新现有 secret
echo -n "$TOKEN" | gcloud secrets versions add api-scheduler-token --data-file=-
```

**授权访问**:
```bash
gcloud secrets add-iam-policy-binding api-scheduler-token \
  --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**使用场景**:
- Cloud Scheduler 任务: `ministry-data-cleaning-scheduler`
- 调用端点: `POST /trigger-cleaning`

---

### 3. weekly-preview-scheduler-token

**服务**: weekly-preview-scheduler  
**用途**: Cloud Scheduler 调用 weekly-preview-scheduler 服务的认证令牌  
**类型**: Token  
**环境变量**: `SCHEDULER_TOKEN`  
**Secret Manager 名称**: `weekly-preview-scheduler-token`

**创建方式**:
```bash
# 生成 token
TOKEN=$(openssl rand -hex 32)

# 创建 secret
echo -n "$TOKEN" | gcloud secrets create weekly-preview-scheduler-token --data-file=-

# 或更新现有 secret
echo -n "$TOKEN" | gcloud secrets versions add weekly-preview-scheduler-token --data-file=-
```

**授权访问**:
```bash
gcloud secrets add-iam-policy-binding weekly-preview-scheduler-token \
  --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**使用场景**:
- Cloud Scheduler 任务: `weekly-preview-job`
- 调用端点: `POST /trigger`

---

### 4. weekly-preview-smtp-password

**服务**: weekly-preview-scheduler  
**用途**: Gmail 应用专用密码（用于发送邮件）  
**类型**: Password  
**环境变量**: `SMTP_PASSWORD`  
**Secret Manager 名称**: `weekly-preview-smtp-password`

**创建方式**:
```bash
# 创建 secret（从环境变量）
echo -n "$SMTP_PASSWORD" | gcloud secrets create weekly-preview-smtp-password --data-file=-

# 或从文件创建
echo -n "your-app-password" | gcloud secrets create weekly-preview-smtp-password --data-file=-

# 更新现有 secret
echo -n "new-password" | gcloud secrets versions add weekly-preview-smtp-password --data-file=-
```

**授权访问**:
```bash
gcloud secrets add-iam-policy-binding weekly-preview-smtp-password \
  --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**获取方式**:
1. 访问: https://myaccount.google.com/apppasswords
2. 生成应用专用密码
3. 保存到 Secret Manager

---

## 📊 Secrets 使用映射

| Secret 名称 | 使用服务 | 环境变量 | 用途 |
|------------|---------|---------|------|
| `mcp-bearer-token` | ministry-data-mcp | `MCP_BEARER_TOKEN` | MCP 服务认证 |
| `api-scheduler-token` | ministry-data-cleaning | `SCHEDULER_TOKEN` | API 服务调度器认证 |
| `weekly-preview-scheduler-token` | weekly-preview-scheduler | `SCHEDULER_TOKEN` | 预览服务调度器认证 |
| `weekly-preview-smtp-password` | weekly-preview-scheduler | `SMTP_PASSWORD` | 邮件发送密码 |

## 🔄 服务自动读取机制

所有服务都实现了自动从 Secret Manager 读取 secrets 的机制：

### 读取优先级

1. **环境变量**（优先）- 用于本地开发或手动覆盖
2. **Secret Manager**（自动）- 生产环境自动读取
3. **默认值**（降级）- 某些服务有默认值作为最后备选

### 代码实现

```python
# 示例：从 Secret Manager 读取 token
from core.secret_manager_utils import get_token_from_manager

token = get_token_from_manager(
    token_name="mcp-bearer-token",
    fallback_env_var="MCP_BEARER_TOKEN"
)
```

## 🚀 快速设置指南

### 1. 创建所有 Secrets

```bash
# 设置项目
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 1. MCP Bearer Token
echo -n "$(openssl rand -hex 32)" | gcloud secrets create mcp-bearer-token --data-file=-

# 2. API Scheduler Token
echo -n "$(openssl rand -hex 32)" | gcloud secrets create api-scheduler-token --data-file=-

# 3. Weekly Preview Scheduler Token
echo -n "$(openssl rand -hex 32)" | gcloud secrets create weekly-preview-scheduler-token --data-file=-

# 4. SMTP Password
echo -n "your-gmail-app-password" | gcloud secrets create weekly-preview-smtp-password --data-file=-
```

### 2. 授权所有服务访问

```bash
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

for secret in mcp-bearer-token api-scheduler-token weekly-preview-scheduler-token weekly-preview-smtp-password; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

### 3. 验证 Secrets

```bash
# 查看所有 secrets
gcloud secrets list

# 查看 secret 版本
gcloud secrets versions list mcp-bearer-token

# 读取 secret（测试）
gcloud secrets versions access latest --secret=mcp-bearer-token
```

## 🔐 安全最佳实践

### 1. 定期轮换

建议每 90 天轮换一次 tokens：

```bash
# 轮换 MCP Bearer Token
NEW_TOKEN=$(openssl rand -hex 32)
echo -n "$NEW_TOKEN" | gcloud secrets versions add mcp-bearer-token --data-file=-

# 验证新版本
gcloud secrets versions access latest --secret=mcp-bearer-token

# 服务会自动使用最新版本（latest）
```

### 2. 版本管理

- 每次更新创建新版本（自动）
- 保留历史版本用于回滚
- 使用 `latest` 标签获取最新版本

### 3. 访问控制

- 只授予必要的权限
- 使用最小权限原则
- 定期审查访问权限

### 4. 审计日志

```bash
# 查看 secret 访问日志
gcloud logging read "resource.type=secretmanager.googleapis.com/Secret" \
  --limit 50 \
  --format json
```

## 📝 更新 Secrets

### 更新单个 Secret

```bash
# 更新 MCP Bearer Token
NEW_TOKEN=$(openssl rand -hex 32)
echo -n "$NEW_TOKEN" | gcloud secrets versions add mcp-bearer-token --data-file=-

# 服务会自动使用新版本（下次请求时）
# 如需立即生效，重启服务
gcloud run services update ministry-data-mcp \
  --region us-central1 \
  --update-secrets MCP_BEARER_TOKEN=mcp-bearer-token:latest
```

### 批量更新所有 Tokens

```bash
#!/bin/bash
# 批量轮换所有 tokens

PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 轮换 tokens
for secret in mcp-bearer-token api-scheduler-token weekly-preview-scheduler-token; do
  echo "Rotating $secret..."
  NEW_TOKEN=$(openssl rand -hex 32)
  echo -n "$NEW_TOKEN" | gcloud secrets versions add $secret --data-file=-
  echo "✅ $secret rotated"
done

echo "⚠️  注意：需要更新 Cloud Scheduler 任务的 headers"
```

## 🔍 故障排除

### Secret 读取失败

**症状**: 服务日志显示 "Failed to load X from Secret Manager"

**检查清单**:
1. ✅ Secret 是否存在
   ```bash
   gcloud secrets describe secret-name
   ```

2. ✅ 服务账号是否有访问权限
   ```bash
   gcloud secrets get-iam-policy secret-name
   ```

3. ✅ 项目 ID 是否正确设置
   ```bash
   echo $GCP_PROJECT_ID
   ```

4. ✅ Secret Manager API 是否启用
   ```bash
   gcloud services enable secretmanager.googleapis.com
   ```

### Token 不匹配

**症状**: 401/403 错误

**解决方案**:
1. 检查 Secret Manager 中的 token 是否最新
2. 确认 Cloud Scheduler 任务的 headers 使用正确的 token
3. 重启相关服务以刷新缓存

## 📚 相关文档

- [Secret Management Best Practices](SECRET_MANAGEMENT.md) - Secret Manager 最佳实践
- [Cloud Run Deployment](DEPLOYMENT.md) - 部署指南
- [MCP Deployment](MCP_DEPLOYMENT.md) - MCP 服务部署

## ✅ 检查清单

部署前请确认：

- [ ] 所有 4 个 secrets 已创建
- [ ] 所有服务账号已授权访问对应 secrets
- [ ] Secret Manager API 已启用
- [ ] Cloud Scheduler 任务使用正确的 tokens
- [ ] 服务配置为使用 Secret Manager（或环境变量）
- [ ] 本地开发使用环境变量
- [ ] 生产环境使用 Secret Manager

---

**文档版本**: 1.0  
**最后更新**: 2025-01-XX  
**维护者**: Grace Irvine Ministry Development Team

