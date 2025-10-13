# MCP Inspector 完整使用指南

## 📋 目录

- [快速开始](#快速开始)
- [使用方法](#使用方法)
- [UI界面说明](#ui界面说明)
- [故障排除](#故障排除)
- [最佳实践](#最佳实践)

---

## 快速开始

### 🚀 一键启动（最简单）

```bash
bash inspect_cloud_mcp.sh
```

这个脚本会：
- ✅ 自动检查服务器健康状态
- ✅ 创建配置文件
- ✅ 启动 MCP Inspector
- ✅ 在浏览器中打开交互界面（http://localhost:6274）

### ✅ 成功标志

当一切正常时，你会在左侧看到：

```
📋 Servers
  └─ 🔌 ministry-data-cloud [Connected] ✅
      ├─ 🔧 Tools (9)
      ├─ 📚 Resources (27+)
      └─ 💬 Prompts (2)
```

### 🎯 使用步骤

1. ✅ 点击左侧的 "ministry-data-cloud"
2. ✅ 选择 Tools / Resources / Prompts
3. ✅ 直接使用！

**关键点**：你的连接**已经配置好了**，不需要在 UI 中做任何额外设置！

---

## 使用方法

### 方法 1: 图形界面（推荐）

```bash
# 启动 Inspector
bash inspect_cloud_mcp.sh

# 停止所有进程
bash stop_mcp_inspector.sh

# 检查状态
bash verify_inspector.sh
```

### 方法 2: 快速测试

```bash
# 运行自动化测试
bash test_mcp_quick.sh
```

测试内容：
- 健康检查
- 工具列表
- 资源列表
- 工具调用
- 资源读取

### 方法 3: 手动使用 curl

```bash
# 设置变量
MCP_URL="https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app"
TOKEN="Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30"

# 健康检查
curl -H "Authorization: $TOKEN" "$MCP_URL/health"

# 列出工具
curl -X POST "$MCP_URL/mcp" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | jq .

# 调用工具（查询下周主日）
curl -X POST "$MCP_URL/mcp" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "generate_weekly_preview",
      "arguments": {}
    }
  }' | jq .
```

---

## UI界面说明

### 左侧边栏（Servers）

```
┌─────────────────────────────────────┐
│ 📋 Servers                          │
│                                     │
│ 🔌 ministry-data-cloud              │
│    Status: [Connected] ✅           │
│    Transport: stdio                 │
│                                     │
│    ├─ 🔧 Tools (9)                  │
│    │   ├─ clean_data                │
│    │   ├─ preview_changes           │
│    │   ├─ generate_weekly_preview   │
│    │   └─ ...                       │
│    │                                 │
│    ├─ 📚 Resources (27+)            │
│    │   ├─ ministry://stats/summary  │
│    │   ├─ ministry://sermons/2024   │
│    │   └─ ...                       │
│    │                                 │
│    └─ 💬 Prompts (2)                │
│        ├─ analyze_volunteer_data    │
│        └─ generate_report           │
└─────────────────────────────────────┘
```

### 使用工具

#### 步骤 1：选择工具
1. 展开左侧 "**Tools**"
2. 点击你想使用的工具，例如 `generate_weekly_preview`

#### 步骤 2：填写参数
在右侧参数编辑器中输入：

```json
{
  "format": "text",
  "date": "2024-10-13"
}
```

**参数格式说明**：
- 使用标准 JSON 格式
- 字符串用双引号
- 布尔值用 `true`/`false`（小写，无引号）
- 数字不加引号

#### 步骤 3：调用工具
点击 "**Call Tool**" 或 "**Execute**" 按钮

#### 步骤 4：查看结果
结果会显示在下方，包括：
- ✅ 成功状态
- 📊 返回数据
- ⏱️ 执行时间
- 📜 日志信息（如果有）

### 查看资源

#### 浏览资源列表
1. 展开左侧 "**Resources**"
2. 资源按照 URI 组织：
   ```
   ministry://stats/summary
   ministry://sermons/2024
   ministry://volunteers/all
   ```

#### 读取资源
1. 点击任一资源
2. 内容会自动加载并显示在右侧
3. 可以看到：
   - 📋 资源元数据
   - 📄 资源内容（JSON/文本）
   - 🔗 相关资源链接

### 资源类型

| URI 前缀 | 说明 | 示例 |
|----------|------|------|
| `ministry://stats/*` | 统计数据 | `ministry://stats/summary` |
| `ministry://sermons/*` | 讲道安排 | `ministry://sermons/2024` |
| `ministry://volunteers/*` | 志愿者信息 | `ministry://volunteers/all` |
| `ministry://unavailability/*` | 不可用记录 | `ministry://unavailability/2024` |

---

## 故障排除

### 问题 1: 端口被占用

**错误信息**:
```
❌ MCP Inspector PORT IS IN USE at http://localhost:6274 ❌
❌ Proxy Server PORT IS IN USE at port 6277 ❌
```

**解决方案**:

方法 1（推荐）:
```bash
# 使用清理脚本
bash stop_mcp_inspector.sh
```

方法 2:
```bash
# 手动清理端口
kill -9 $(lsof -ti:6274,6277)
```

方法 3:
```bash
# 脚本会自动清理，直接重新运行
bash inspect_cloud_mcp.sh
```

### 问题 2: 左侧没有显示服务器

**症状**：左侧边栏是空的，看不到 "ministry-data-cloud"

**解决**：
```bash
# 1. 停止 Inspector
bash stop_mcp_inspector.sh

# 2. 重新启动
bash inspect_cloud_mcp.sh

# 3. 等待浏览器自动打开
```

### 问题 3: 显示 "Connection Error"

**症状**：服务器显示为 [Disconnected] 或连接错误

**可能原因**：
1. 手动在 UI 中添加了 SSE 连接
2. 代理进程意外停止

**解决步骤**：

**步骤 1**：删除手动添加的连接
- 在 UI 中找到显示错误的连接
- 点击删除按钮（❌ 图标）

**步骤 2**：验证状态
```bash
bash verify_inspector.sh
```

**步骤 3**：如果还有问题，重启
```bash
bash stop_mcp_inspector.sh
bash inspect_cloud_mcp.sh
```

### 问题 4: 工具调用失败

**症状**：点击 "Call Tool" 后返回错误

**检查事项**：
1. ✅ 参数格式是否正确（有效的 JSON）
2. ✅ 必需参数是否都提供了
3. ✅ 参数值的类型是否正确

**示例 - 错误的参数**：
```json
{
  format: text,          ❌ 缺少引号
  date: 2024-10-13       ❌ 日期应该是字符串
}
```

**示例 - 正确的参数**：
```json
{
  "format": "text",      ✅ 字符串有引号
  "date": "2024-10-13"   ✅ 日期是字符串
}
```

### 问题 5: Python 依赖缺失

**错误信息**:
```
ModuleNotFoundError: No module named 'requests'
```

**解决方案**:
```bash
# 安装依赖
pip3 install -r requirements.txt

# 或者只安装 requests
pip3 install requests
```

### 问题 6: MCP Inspector 安装失败

**解决方案**:
```bash
# 清除 npm 缓存并重新安装
npm cache clean --force
npx -y @modelcontextprotocol/inspector --version

# 或者全局安装
npm install -g @modelcontextprotocol/inspector
```

---

## 常用命令参考

| 任务 | 命令 |
|------|------|
| 启动 Inspector | `bash inspect_cloud_mcp.sh` |
| 停止所有进程 | `bash stop_mcp_inspector.sh` |
| 快速测试 | `bash test_mcp_quick.sh` |
| 检查端口 | `lsof -ti:6274,6277` |
| 清理端口 | `kill -9 $(lsof -ti:6274,6277)` |
| 测试服务器 | `curl -H "Authorization: Bearer TOKEN" URL/health` |
| 查看日志 | `tail -f /tmp/mcp_cloud_proxy.log` |

---

## 重要提示

### ✅ 应该做的事情

- [ ] 运行 `bash inspect_cloud_mcp.sh` 启动
- [ ] 等待浏览器自动打开 http://localhost:6274
- [ ] 在左侧看到 "ministry-data-cloud" [Connected]
- [ ] 直接使用已连接的服务器
- [ ] 选择 Tools / Resources 并使用

### ❌ 不应该做的事情

- [ ] ~~在 UI 中点击 "Add Server"~~
- [ ] ~~尝试手动添加 SSE 连接~~
- [ ] ~~输入服务器 URL~~
- [ ] ~~配置 Bearer Token~~
- [ ] ~~尝试修改已连接的服务器~~

**记住**：连接已经自动配置好了！

---

## 为什么这样设计？

### 问题：为什么不直接支持 SSE？

1. **SSE 传输已弃用**
   - MCP Inspector 提示："SSE transport is deprecated"
   - 推荐使用 StreamableHttp

2. **服务器架构**
   - 云端服务器实现了 JSON-RPC HTTP 端点
   - 没有实现实时 SSE 流
   - 设计用于 API 调用而不是持久连接

3. **代理解决方案**
   - `mcp_cloud_proxy.py` 桥接两种传输方式
   - Inspector 使用 stdio（本地通信）
   - 代理使用 HTTP（云端通信）
   - 两全其美！

### 优势

✅ **稳定性**：stdio 比 SSE 更可靠  
✅ **兼容性**：支持所有 MCP 客户端  
✅ **灵活性**：可以轻松切换后端  
✅ **调试友好**：可以查看代理日志

---

## 测试场景示例

### 场景 1: 查询下周主日安排

```
1. Tools → generate_weekly_preview
2. 参数：{"format": "text"}
3. Call Tool
4. 查看本周安排
5. 复制结果用于分享
```

### 场景 2: 查看统计

```
1. Resources → ministry://stats/summary
2. 自动加载统计数据
3. 查看：
   - 总讲道数
   - 志愿者数量
   - 月度趋势
```

### 场景 3: 查询志愿者

```
1. Tools → query_volunteer_metadata
2. 参数：{"volunteer_name": "张三"}
3. Call Tool
4. 查看该志愿者的：
   - 服事频率
   - 首选角色
   - 历史记录
```

---

## 工作原理

### ❌ 错误方式（SSE 直连 - 不工作）

```
Inspector UI
    ↓ (尝试 SSE 直连)
    ↓
https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app
    ↓
404 Not Found (没有 SSE 端点)
```

### ✅ 正确方式（stdio + 代理 - 成功）

```
Inspector UI
    ↓ (stdio)
    ↓
mcp_cloud_proxy.py (本地代理)
    ↓ (HTTP JSON-RPC)
    ↓
https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp
    ↓
200 OK ✅
```

**关键区别**：
1. ✅ 使用 stdio 而不是 SSE
2. ✅ 通过本地代理转发
3. ✅ 代理处理认证和协议转换
4. ✅ 服务器支持 HTTP JSON-RPC 端点

---

## 诊断命令

### 全面诊断

```bash
#!/bin/bash
echo "=== MCP Inspector 诊断 ==="
echo ""

# 1. 检查 Python
echo "1. Python 版本:"
python3 --version

# 2. 检查依赖
echo ""
echo "2. Python 依赖:"
python3 -c "import requests; print('✓ requests OK')" 2>&1

# 3. 检查端口
echo ""
echo "3. 端口占用:"
lsof -ti:6274 && echo "⚠️ 端口 6274 被占用" || echo "✓ 端口 6274 空闲"
lsof -ti:6277 && echo "⚠️ 端口 6277 被占用" || echo "✓ 端口 6277 空闲"

# 4. 检查服务器
echo ""
echo "4. 服务器健康:"
curl -s -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
  https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/health | jq -r '.status'

# 5. 检查文件
echo ""
echo "5. 必要文件:"
[ -f "mcp_cloud_proxy.py" ] && echo "✓ mcp_cloud_proxy.py" || echo "✗ mcp_cloud_proxy.py"
[ -f "inspect_cloud_mcp.sh" ] && echo "✓ inspect_cloud_mcp.sh" || echo "✗ inspect_cloud_mcp.sh"
[ -f "stop_mcp_inspector.sh" ] && echo "✓ stop_mcp_inspector.sh" || echo "✗ stop_mcp_inspector.sh"

echo ""
echo "=== 诊断完成 ==="
```

---

## 相关文档

- 📖 [MCP 设计文档](MCP_DESIGN.md)
- 📖 [MCP 部署指南](MCP_CLOUD_RUN_DEPLOYMENT.md)
- 📖 [API 端点文档](API_ENDPOINTS.md)
- 📖 [故障排除](TROUBLESHOOTING.md)

---

## 获取帮助

### 验证工具
```bash
# 检查 Inspector 状态
bash verify_inspector.sh

# 测试服务器功能
bash test_mcp_quick.sh

# 停止所有进程
bash stop_mcp_inspector.sh
```

### 社区资源

- [MCP 官方文档](https://modelcontextprotocol.io)
- [MCP Inspector GitHub](https://github.com/modelcontextprotocol/inspector)
- [Google Cloud Run 文档](https://cloud.google.com/run/docs)

---

**版本**: 1.0  
**最后更新**: 2025-10-13  
**状态**: ✅ 已完成并测试

🎉 **祝您使用愉快！**

