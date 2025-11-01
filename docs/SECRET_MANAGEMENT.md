# 密钥管理最佳实践 - Secret Management Best Practices

本文档介绍如何使用 Google Secret Manager 管理动态变化的服务 tokens 和敏感信息。

## 📋 目录

- [问题背景](#问题背景)
- [业界最佳实践](#业界最佳实践)
- [Google Secret Manager 方案](#google-secret-manager-方案)
- [实现方式](#实现方式)
- [使用指南](#使用指南)
- [最佳实践建议](#最佳实践建议)

## 🎯 问题背景

在管理多个服务时，我们经常遇到以下问题：

1. **动态变化的 Tokens**: 各种服务的 API tokens 需要定期轮换，难以手动管理
2. **安全存储**: 敏感信息不能硬编码在代码中或存储在版本控制系统中
3. **集中管理**: 多个服务需要访问相同的 tokens，需要统一管理
4. **访问控制**: 需要细粒度的权限控制，确保只有授权的服务可以访问

## 🌟 业界最佳实践

根据业界标准和云服务提供商的最佳实践，推荐以下方案：

### 1. 使用专门的密钥管理服务

**推荐服务:**
- **AWS**: AWS Secrets Manager
- **Google Cloud**: Google Secret Manager ✅ (本方案)
- **Azure**: Azure Key Vault
- **HashiCorp**: Vault

**优势:**
- ✅ 安全的加密存储
- ✅ 自动版本管理
- ✅ 细粒度访问控制（IAM）
- ✅ 审计日志和访问追踪
- ✅ 支持自动轮换（部分服务）

### 2. 自动轮换凭证

定期更换服务令牌可以：
- 🔒 降低凭证泄露风险
- 🔄 符合安全合规要求
- 🛡️ 减少长期凭证被滥用的风险

### 3. 细粒度访问控制

使用 IAM (Identity and Access Management) 策略：
- ✅ 只有授权的应用程序可以访问
- ✅ 支持基于角色的访问控制 (RBAC)
- ✅ 最小权限原则

### 4. 避免硬编码凭证

**❌ 不推荐:**
```python
API_TOKEN = "hardcoded-token-here"  # 危险！
```

**✅ 推荐:**
```python
# 从 Secret Manager 读取
token = get_token_from_manager("api-token")
```

### 5. 监控和审计

- 📊 记录所有对 secrets 的访问
- 🔍 检测异常访问模式
- 📝 保留审计日志

## 🔐 Google Secret Manager 方案

Google Secret Manager 是 Google Cloud 提供的密钥管理服务，完全满足上述最佳实践要求。

### 为什么选择 Google Secret Manager？

1. **✅ 安全存储**: 使用 Google 的加密基础设施
2. **✅ 版本管理**: 自动跟踪 secret 的版本历史
3. **✅ IAM 集成**: 与 Google Cloud IAM 无缝集成
4. **✅ 审计日志**: 记录所有访问和更改
5. **✅ Cloud Run 集成**: 与 Cloud Run 原生集成，无需额外配置
6. **✅ 成本效益**: 按使用量计费，价格合理

## 🛠️ 实现方式

本项目中已实现完整的 Secret Manager 集成：

### 1. 核心模块

**文件**: `core/secret_manager_utils.py`

提供以下功能：
- `SecretManagerHelper`: Secret Manager 客户端封装
- `get_secret_from_manager()`: 获取 secret 值
- `get_token_from_manager()`: 获取 token（便捷方法）
- 自动缓存机制（减少 API 调用）
- 降级支持（Secret Manager 不可用时使用环境变量）

### 2. 自动集成

**文件**: `mcp/mcp_server.py`

MCP Server 自动从 Secret Manager 读取 Bearer Token：

```python
# 优先从环境变量读取，如果没有则从 Secret Manager 读取
BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")
if not BEARER_TOKEN:
    BEARER_TOKEN = get_token_from_manager(
        token_name="mcp-bearer-token",
        fallback_env_var="MCP_BEARER_TOKEN"
    ) or ""
```

### 3. 使用示例

```python
from core.secret_manager_utils import get_token_from_manager

# 获取 MCP Bearer Token
token = get_token_from_manager(
    token_name="mcp-bearer-token",
    fallback_env_var="MCP_BEARER_TOKEN"
)

# 获取其他服务的 token
api_token = get_token_from_manager(
    token_name="external-api-token",
    fallback_env_var="EXTERNAL_API_TOKEN"
)
```

## 📖 使用指南

### 步骤 1: 创建 Secret

```bash
# 创建 secret（例如 MCP Bearer Token）
echo -n "your-token-value" | gcloud secrets create mcp-bearer-token \
  --data-file=- \
  --project=your-project-id

# 或者从文件创建
echo -n "your-token-value" > token.txt
gcloud secrets create mcp-bearer-token \
  --data-file=token.txt \
  --project=your-project-id
```

### 步骤 2: 授予访问权限

```bash
# 授予 Cloud Run 服务访问权限
gcloud secrets add-iam-policy-binding mcp-bearer-token \
  --member="serviceAccount:your-project-id@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=your-project-id

# 授予特定用户访问权限
gcloud secrets add-iam-policy-binding mcp-bearer-token \
  --member="user:user@example.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=your-project-id
```

### 步骤 3: 在 Cloud Run 中使用

```bash
# 方式 1: 使用 --set-secrets 参数（推荐）
gcloud run deploy your-service \
  --image gcr.io/your-project/your-image \
  --set-secrets MCP_BEARER_TOKEN=mcp-bearer-token:latest \
  --project=your-project-id

# 方式 2: 在代码中自动读取（当前实现）
# 代码会自动尝试从 Secret Manager 读取
```

### 步骤 4: 更新 Secret

```bash
# 添加新版本
echo -n "new-token-value" | gcloud secrets versions add mcp-bearer-token \
  --data-file=-

# 查看版本历史
gcloud secrets versions list mcp-bearer-token
```

### 步骤 5: 轮换 Token

```bash
# 1. 创建新 token
NEW_TOKEN=$(openssl rand -hex 32)

# 2. 添加到 Secret Manager（创建新版本）
echo -n "$NEW_TOKEN" | gcloud secrets versions add mcp-bearer-token --data-file=-

# 3. 验证新版本
gcloud secrets versions access latest --secret=mcp-bearer-token

# 4. 如果一切正常，删除旧版本（可选）
# gcloud secrets versions destroy <version-id> --secret=mcp-bearer-token
```

## 💡 最佳实践建议

### 1. 命名规范

使用清晰的命名规范：

```bash
# ✅ 推荐
mcp-bearer-token
api-service-credentials
database-password
smtp-password

# ❌ 不推荐
token
secret
password
```

### 2. 版本管理

- 每次更新都创建新版本（自动）
- 保留历史版本用于回滚
- 使用 `latest` 版本获取最新值
- 定期清理过旧版本

### 3. 访问控制

**最小权限原则:**
```bash
# 只授予必要的权限
gcloud secrets add-iam-policy-binding secret-name \
  --member="serviceAccount:service@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**不同环境使用不同的 secrets:**
```bash
# 开发环境
dev-mcp-bearer-token

# 生产环境
prod-mcp-bearer-token
```

### 4. 本地开发

本地开发时，可以：

**选项 1: 使用环境变量（推荐）**
```bash
export MCP_BEARER_TOKEN="your-local-token"
```

**选项 2: 从 Secret Manager 读取**
```bash
# 设置项目 ID
export GCP_PROJECT_ID="your-project-id"

# 代码会自动从 Secret Manager 读取
```

### 5. 错误处理

代码已实现优雅降级：
1. 首先尝试从 Secret Manager 读取
2. 如果失败，降级到环境变量
3. 如果都没有，记录警告并继续（如果允许）

### 6. 缓存策略

Secret Manager Helper 实现了缓存机制：
- **缓存时间**: 5 分钟
- **自动过期**: 缓存过期后自动刷新
- **手动清除**: 需要时手动清除缓存

```python
from core.secret_manager_utils import get_secret_helper

# 清除特定 secret 的缓存
helper = get_secret_helper()
helper.clear_cache("mcp-bearer-token")

# 清除所有缓存
helper.clear_cache()
```

### 7. 监控和告警

设置 Cloud Monitoring 告警：
- 监控 Secret Manager API 调用频率
- 检测异常访问模式
- 记录所有访问日志

### 8. 安全建议

1. **✅ 定期轮换**: 建议每 90 天轮换一次 token
2. **✅ 审计日志**: 定期检查访问日志
3. **✅ 最小权限**: 只授予必要的权限
4. **✅ 版本控制**: 不要将 secrets 提交到 Git
5. **✅ 加密传输**: 使用 HTTPS 访问 Secret Manager

## 🔄 与其他方案对比

| 方案 | 安全性 | 易用性 | 成本 | 适用场景 |
|------|--------|--------|------|----------|
| **Google Secret Manager** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中等 | 生产环境，GCP 项目 |
| **环境变量** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 低 | 本地开发，简单场景 |
| **配置文件** | ⭐⭐ | ⭐⭐⭐⭐ | 低 | 本地开发（不推荐生产） |
| **Kubernetes Secrets** | ⭐⭐⭐⭐ | ⭐⭐⭐ | 低 | Kubernetes 集群 |
| **HashiCorp Vault** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 中等 | 多云环境，复杂场景 |

## 🎯 当前项目集成情况

本项目已为所有服务集成 Secret Manager：

### ✅ 已集成的服务（3个 Cloud Run + 2个 Scheduler）

| 服务名称 | Secret Manager 集成 | Secrets |
|---------|-------------------|---------|
| **ministry-data-mcp** | ✅ 已集成 | `mcp-bearer-token` |
| **ministry-data-cleaning** | ✅ 已集成 | `api-scheduler-token` |
| **weekly-preview-scheduler** | ✅ 已集成 | `mcp-bearer-token`<br>`weekly-preview-scheduler-token`<br>`weekly-preview-smtp-password` |

**Scheduler 任务:**
- `ministry-data-cleaning-scheduler` → 使用 `api-scheduler-token`
- `weekly-preview-job` → 使用 `weekly-preview-scheduler-token`

详细清单请查看: [Secrets Inventory](SECRETS_INVENTORY.md)

## 📚 参考资源

- [Google Secret Manager 官方文档](https://cloud.google.com/secret-manager/docs)
- [Secret Manager Python 客户端文档](https://cloud.google.com/python/docs/reference/secretmanager/latest)
- [Cloud Run 使用 Secret Manager](https://cloud.google.com/run/docs/configuring/secrets)
- [安全最佳实践](https://cloud.google.com/secret-manager/docs/security)
- [项目 Secrets 清单](SECRETS_INVENTORY.md)

## ✅ 总结

使用 Google Secret Manager 存储和管理动态变化的 tokens 是业界最佳实践，具有以下优势：

1. ✅ **安全性**: 加密存储，访问控制
2. ✅ **可管理性**: 版本管理，审计日志
3. ✅ **易用性**: 与 Cloud Run 集成，自动读取
4. ✅ **可扩展性**: 支持多个 secrets，自动轮换
5. ✅ **成本效益**: 按使用量计费，价格合理

**推荐在生产环境中使用 Google Secret Manager，本地开发时使用环境变量作为降级方案。**

---

**文档版本**: 1.0  
**最后更新**: 2025-01-XX  
**维护者**: Grace Irvine Ministry Development Team

