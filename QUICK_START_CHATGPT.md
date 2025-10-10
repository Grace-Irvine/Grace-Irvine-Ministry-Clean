# 🚀 5 分钟连接 ChatGPT

## 当前运行状态

### ✅ 服务器已启动

```
MCP HTTP 服务器
端口: 8090
状态: ✅ 运行中
认证: 禁用（测试模式）
```

### ✅ ngrok 隧道已创建

```
公共 URL: https://2e3dfdd56609.ngrok-free.app
MCP 端点: https://2e3dfdd56609.ngrok-free.app/mcp
状态: ✅ 活动中
```

---

## 📋 ChatGPT 配置步骤

### 步骤 1: 打开 ChatGPT 设置

1. 访问 [ChatGPT](https://chat.openai.com)
2. 点击左下角您的头像
3. 选择 **Settings**（设置）

### 步骤 2: 进入连接器设置

1. 在设置菜单中，找到 **Connectors**（连接器）
2. 点击 **Advanced**（高级）
3. 开启 **Developer mode**（开发者模式）

### 步骤 3: 创建新连接器

点击 **Create** 按钮，填写以下信息：

#### 基本信息

**Connector name（连接器名称）**:
```
Grace Irvine Ministry Data
```

**Description（描述）**:
```
教会主日事工数据管理系统

功能：
• 查询同工服侍安排（敬拜、技术等）
• 查询证道信息（讲员、题目、经文）
• 统计分析讲道系列和同工服侍
• 数据清洗和验证
```

**Connector URL（连接器 URL）**:
```
https://2e3dfdd56609.ngrok-free.app/mcp
```

### 步骤 4: 保存并验证

1. 点击 **Create**
2. ChatGPT 会连接到您的 MCP 服务器
3. 如果成功，您会看到 **7 个工具**的列表

---

## 🧪 测试对话

### 测试 1: 查询同工服侍

在 ChatGPT 中输入：

```
请查询 2025 年 10 月 12 日的同工服侍安排
```

**预期结果**:
- 显示"正在查询同工服侍安排..."
- 返回敬拜主领、司琴、技术同工等信息

### 测试 2: 查询证道

```
2025 年 10 月 12 日的证道是什么内容？
```

**预期结果**:
- 调用 `query_sermon_by_date`
- 返回讲员、题目、经文信息

### 测试 3: 分析统计

```
请分析 2025 年 10 月的同工服侍情况
```

**预期结果**:
- 调用 `query_date_range`
- 返回整月的服侍记录和统计

---

## ✅ 验证成功标志

当连接成功时，您应该看到：

1. **工具调用显示**
   - ✅ 工具名称显示
   - ✅ 状态提示（"正在查询..." → "查询完成"）
   - ✅ 结果以自然语言呈现

2. **数据准确性**
   - ✅ 返回的日期、人名正确
   - ✅ 数据结构完整
   - ✅ 中文显示正常

---

## 🔄 刷新元数据

如果您修改了工具或添加了新功能：

1. 重启 MCP 服务器
2. 在 ChatGPT **Settings → Connectors** 中
3. 点击您的连接器
4. 选择 **Refresh**
5. 验证工具列表更新

---

## ⚠️ 重要提示

### ngrok 限制

免费版 ngrok 的限制：
- 🔄 **URL 会变化**：每次重启 ngrok 会生成新 URL
- ⏱️ **会话超时**：长时间不活动可能断开
- 📊 **请求限制**：有流量限制

**解决方案**：
- 短期测试：可以接受
- 生产使用：部署到 Cloud Run（固定 URL）

### 获取新的 ngrok URL

如果 ngrok 重启了，获取新 URL：

```bash
curl -s http://localhost:4040/api/tunnels | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```

然后在 ChatGPT 中更新连接器 URL 并刷新。

---

## 🚀 生产部署

### 推荐: Cloud Run

一键部署到 Google Cloud Run（获得稳定的 HTTPS URL）：

```bash
./deploy-mcp-cloud-run.sh
```

**优势**:
- ✅ 固定的 HTTPS URL（不会变化）
- ✅ 自动扩展
- ✅ 免费额度充足
- ✅ 无需 ngrok

**部署后**:
- URL 格式: `https://YOUR_SERVICE-wu7uk5rgdq-uc.a.run.app/mcp`
- 在 ChatGPT 中更新连接器 URL
- 建议启用认证（设置 `MCP_BEARER_TOKEN`）

---

## 📊 监控

### 查看请求

ngrok Web 界面: http://localhost:4040

### 查看日志

```bash
# MCP 服务器日志
tail -f /tmp/mcp_8090.log

# ngrok 日志
tail -f /tmp/ngrok_8090.log
```

### 健康检查

```bash
# 本地
curl http://localhost:8090/health

# 公网
curl https://2e3dfdd56609.ngrok-free.app/health
```

---

## 🎯 快速参考

### 当前 ngrok URL

```
https://2e3dfdd56609.ngrok-free.app/mcp
```

### 停止所有服务

```bash
pkill -f mcp_http_server.py
pkill ngrok
```

### 重启所有服务

```bash
cd /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean
MCP_REQUIRE_AUTH=false PORT=8090 python3 mcp_http_server.py > /tmp/mcp_8090.log 2>&1 &
ngrok http 8090 > /tmp/ngrok_8090.log 2>&1 &
sleep 5
curl -s http://localhost:4040/api/tunnels | python3 -c "import json, sys; print('MCP URL:', json.load(sys.stdin)['tunnels'][0]['public_url'] + '/mcp')"
```

---

## 📚 更多资源

- [完整连接指南](CHATGPT_CONNECTION_GUIDE.md)
- [OpenAI 对齐报告](docs/OPENAI_ALIGNMENT.md)
- [故障排除](docs/TROUBLESHOOTING.md)

---

**最后更新**: 2025-10-10  
**有效期**: 直到 ngrok 重启


