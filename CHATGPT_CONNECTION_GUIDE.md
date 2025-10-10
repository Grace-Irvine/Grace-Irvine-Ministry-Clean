# ChatGPT 连接指南

## 🎉 准备就绪（405 错误已修复）

您的 MCP 服务器已准备好连接到 ChatGPT！

**✅ 更新**: 已添加 GET /mcp 端点支持，修复了 "405 Method Not Allowed" 错误。

---

## 📊 当前状态

### ✅ 本地服务器

- **端口**: `8090`
- **状态**: 运行中
- **认证**: 已禁用（测试模式）
- **健康检查**: http://localhost:8090/health

### ✅ ngrok 隧道

- **公共 URL**: `https://2e3dfdd56609.ngrok-free.app`
- **转发到**: `http://localhost:8090`
- **状态**: 活动中

### ✅ 验证结果

```
✅ 找到 7 个工具
✅ 所有工具都有 meta 字段
✅ 响应格式符合 OpenAI 标准
✅ structuredContent 正确返回
```

---

## 🔗 连接到 ChatGPT

根据 [OpenAI Apps SDK 连接指南](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt)：

### 前置要求

在连接之前，您需要：

1. ✅ **开发者模式访问权限**
   - 联系您的 OpenAI 合作伙伴，将您添加到连接器开发者实验
   - 如果您使用 ChatGPT Enterprise，请让工作区管理员为您的账户启用连接器创建

2. ✅ **启用开发者模式**
   - 在 ChatGPT 客户端中：
   - 进入 **Settings → Connectors → Advanced → Developer mode**
   - 开启开发者模式

### 步骤 1: 创建连接器

1. 在 ChatGPT 中，进入 **Settings → Connectors → Create**

2. 填写连接器信息：

   **Connector name（连接器名称）**:
   ```
   Grace Irvine Ministry Data
   ```

   **Description（描述）**:
   ```
   教会主日事工数据管理系统 - 查询同工服侍安排、证道信息、统计分析等。
   
   功能包括：
   - 查询指定日期的同工服侍安排
   - 查询证道信息（讲员、题目、经文）
   - 分析讲道系列和同工统计
   - 数据清洗和验证
   ```

   **Connector URL（连接器 URL）**:
   ```
   https://2e3dfdd56609.ngrok-free.app/mcp
   ```

3. 点击 **Create**

4. 如果连接成功，您应该看到 7 个工具的列表：
   - query_volunteers_by_date
   - query_sermon_by_date
   - query_date_range
   - clean_ministry_data
   - generate_service_layer
   - validate_raw_data
   - sync_from_gcs

### 步骤 2: 在对话中启用连接器

1. 打开 ChatGPT 新对话

2. 点击消息输入框附近的 **+** 按钮

3. 选择 **Developer mode**

4. 在可用工具列表中，开启 **Grace Irvine Ministry Data**

5. 现在可以开始测试了！

---

## 🧪 测试提示词

### 测试 1: 查询同工服侍

```
请查询 2025 年 10 月 12 日的同工服侍安排
```

**预期响应**:
- ChatGPT 会调用 `query_volunteers_by_date` 工具
- 显示"正在查询同工服侍安排..."
- 返回该日期的敬拜主领、司琴、技术同工等信息

### 测试 2: 查询证道信息

```
请告诉我 2025 年 10 月 12 日的证道信息
```

**预期响应**:
- 调用 `query_sermon_by_date` 工具
- 返回讲员、题目、经文、诗歌等信息

### 测试 3: 日期范围查询

```
请查询 2025 年 10 月 1 日到 10 月 31 日的所有服侍安排
```

**预期响应**:
- 调用 `query_date_range` 工具
- 返回该月的 sermon 和 volunteer 数据

### 测试 4: 管理员操作

```
帮我验证一下原始数据的质量
```

**预期响应**:
- 调用 `validate_raw_data` 工具
- 返回验证报告摘要

---

## 🔍 调试工具

### 查看工具列表

```bash
curl -X POST https://2e3dfdd56609.ngrok-free.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 手动调用工具

```bash
curl -X POST https://2e3dfdd56609.ngrok-free.app/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "query_volunteers_by_date",
      "arguments": {"date": "2025-10-12"}
    }
  }'
```

### 查看 ngrok 请求日志

访问 http://localhost:4040 查看 ngrok Web 界面

---

## ⚙️ 服务器管理

### 查看服务器日志

```bash
tail -f /tmp/mcp_8090.log
```

### 重启服务器

```bash
# 停止服务器
pkill -f mcp_http_server.py

# 启动服务器（无认证，测试模式）
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
MCP_REQUIRE_AUTH=false PORT=8090 python3 mcp_http_server.py > /tmp/mcp_8090.log 2>&1 &
```

### 重启 ngrok

```bash
# 停止 ngrok
pkill ngrok

# 启动 ngrok
ngrok http 8090 --log=stdout > /tmp/ngrok_8090.log 2>&1 &

# 获取新 URL
sleep 3
curl -s http://localhost:4040/api/tunnels | python3 -c "import json, sys; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```

---

## 🔒 生产环境部署

### 启用认证

对于生产环境，**必须启用认证**：

```bash
# 生成安全的 Bearer Token
export MCP_BEARER_TOKEN=$(openssl rand -hex 32)
echo "保存此 Token: $MCP_BEARER_TOKEN"

# 启动带认证的服务器
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
MCP_REQUIRE_AUTH=true PORT=8090 python3 mcp_http_server.py > /tmp/mcp_8090.log 2>&1 &
```

### 部署到 Cloud Run

推荐使用 Cloud Run 进行生产部署：

```bash
./deploy-mcp-cloud-run.sh
```

**优势**:
- ✅ 稳定的 HTTPS 端点
- ✅ 自动扩展
- ✅ 免费额度充足
- ✅ 无需 ngrok

---

## 📝 验证清单

### 连接前检查

- [x] MCP 服务器运行在 port 8090
- [x] ngrok 隧道已创建
- [x] 工具列表可访问（7 个工具）
- [x] 所有工具都有 `meta` 字段
- [x] 响应格式符合 OpenAI 标准
- [ ] 在 ChatGPT 中创建连接器
- [ ] 测试工具调用
- [ ] 验证响应显示

---

## 🎯 连接信息摘要

### MCP 端点 URL

```
https://2e3dfdd56609.ngrok-free.app/mcp
```

### 连接器名称

```
Grace Irvine Ministry Data
```

### 描述

```
教会主日事工数据管理系统 - 查询同工服侍安排、证道信息、统计分析等
```

### 可用工具数量

```
7 个工具
```

---

## 📚 相关资源

- [OpenAI Apps SDK - Deploy](https://developers.openai.com/apps-sdk/deploy)
- [OpenAI Apps SDK - Connect ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt)
- [OpenAI 对齐报告](docs/OPENAI_ALIGNMENT.md)
- [实施完成报告](IMPLEMENTATION_COMPLETE.md)

---

## 🆘 故障排除

### 问题: ChatGPT 无法连接

**检查**:
1. ngrok 隧道是否仍在运行？
   ```bash
   curl https://2e3dfdd56609.ngrok-free.app/health
   ```

2. MCP 服务器是否正常？
   ```bash
   curl http://localhost:8090/health
   ```

### 问题: 工具调用失败

**检查**:
1. 查看服务器日志
   ```bash
   tail -f /tmp/mcp_8090.log
   ```

2. 查看 ngrok 请求日志
   - 访问 http://localhost:4040

### 问题: ngrok URL 变化

ngrok 免费版每次重启会生成新的 URL。需要：
1. 获取新 URL
2. 在 ChatGPT 中刷新连接器（**Refresh** 按钮）

---

## ⚡ 快速命令

### 一键启动（测试模式）

```bash
# 启动服务器
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
MCP_REQUIRE_AUTH=false PORT=8090 python3 mcp_http_server.py > /tmp/mcp_8090.log 2>&1 &

# 启动 ngrok
ngrok http 8090 --log=stdout > /tmp/ngrok_8090.log 2>&1 &

# 等待并获取 URL
sleep 5
curl -s http://localhost:4040/api/tunnels | python3 -c "import json, sys; print('MCP URL:', json.load(sys.stdin)['tunnels'][0]['public_url'] + '/mcp')"
```

### 一键停止

```bash
pkill -f mcp_http_server.py
pkill ngrok
```

---

**创建日期**: 2025-10-10  
**ngrok URL 有效期**: 直到进程重启  
**下次更新**: URL 变化时

