# 更新日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [3.4.0] - 2025-10-10

### 🔄 主要更新：MCP服务器统一实现

**从两个文件合并为单一文件**

#### 1. 统一服务器实现 ✅

##### `mcp_local/mcp_server.py` - 单一文件实现
- **功能**：stdio 和 HTTP/SSE 两种模式统一在一个文件中
- **特性**：
  - 自动模式检测（基于 PORT 环境变量）
  - 同时支持 Claude Desktop（stdio）和 ChatGPT/OpenAI（HTTP/SSE）
  - 单一代码库，避免重复维护
  - 生产就绪，完全兼容

#### 2. 移除冗余文件 ✅

- **删除** `mcp_local/mcp_http_server.py`（功能已合并）
- 所有 HTTP/SSE 功能现在在 `mcp_server.py` 中

#### 3. 更新部署配置 ✅

- **Dockerfile更新**：使用统一的 `mcp_server.py`
- **deploy-mcp.sh更新**：单一镜像构建流程
- **环境变量**：PORT 自动触发 HTTP 模式

#### 4. 文档整理 ✅

- **更新** `mcp_local/README.md` - 完整的统一实现说明
- **更新** `README.md` - 精简并聚焦核心功能
- **删除** 23+ 个重复和过时文档：
  - ChatGPT 连接相关（6个）
  - 实施状态文档（3个）
  - 临时修复文档（4个）
  - MCP 优化和总结（4个）
  - 重复的 README（3个）
  - 其他过时文档（3个）

#### 5. 技术实现细节

- **模式检测**：
  ```python
  if PORT in env or "--http" in args:
      run_http_mode()
  else:
      run_stdio_mode()
  ```
- **代码重用**：100% 工具、资源、提示词实现共享
- **向后兼容**：所有现有配置继续工作

#### 6. 部署和使用 ✅

**本地 stdio 模式（Claude Desktop）**：
```bash
python mcp_local/mcp_server.py
```

**本地 HTTP 模式（ChatGPT）**：
```bash
PORT=8080 python mcp_local/mcp_server.py
```

**Cloud Run 部署**：
```bash
./deploy/deploy-mcp.sh  # PORT 自动设置
```

#### 7. 实际应用价值

- ✅ **简化维护**：一个文件，一次更新
- ✅ **降低复杂度**：不再需要同步两个文件
- ✅ **统一测试**：单一测试套件
- ✅ **自动适配**：根据环境自动选择模式
- ✅ **生产就绪**：经过完整测试验证

---

## [3.3.0] - 2025-10-10

### 🚀 主要更新：6个新规划工具

**从"查询历史"升级到"规划未来"**

#### 1. 新增6个MCP工具 ✅

##### `check_upcoming_completeness` - 未来排班完整性检查
- **功能**：检查未来N周的排班完整性，识别空缺岗位
- **特性**：
  - 检查volunteer和sermon域的空缺
  - 按紧急度排序（日期越近越紧急）
  - 基于历史数据建议可填补的人员
  - 生成待办清单

##### `generate_weekly_preview` - 周报预览生成
- **功能**：生成指定日期的主日预览报告
- **特性**：
  - 整合证道信息（讲员、题目、经文、系列）
  - 整合同工安排（敬拜、技术、现场服侍）
  - 支持多种输出格式（text/markdown/html）
  - 适合直接发送（微信、邮件）

##### `analyze_role_coverage` - 岗位覆盖率分析
- **功能**：分析岗位健康度，识别单点故障岗位
- **特性**：
  - 计算岗位健康度指数（0-100分）
  - 统计备份人员数量
  - 识别"单点故障"岗位
  - 生成培训建议

##### `analyze_preacher_rotation` - 讲员轮换分析
- **功能**：分析讲员轮换模式，建议未来安排
- **特性**：
  - 计算每位讲员的平均间隔周期
  - 评估轮换质量（healthy/unbalanced）
  - 建议未来讲员安排
  - 识别需要培养的新讲员

##### `analyze_sermon_series_progress` - 证道系列进度追踪
- **功能**：追踪证道系列进度，识别中断
- **特性**：
  - 计算已讲次数和预计剩余次数
  - 识别系列中断或跳跃
  - 预测系列完成日期
  - 支持分析所有系列或特定系列

##### `analyze_volunteer_trends` - 同工趋势分析
- **功能**：分析同工趋势，识别新/活跃/休眠同工
- **特性**：
  - 识别同工状态（新/活跃/休眠/不活跃）
  - 计算留存率和流失率
  - 分析增长/流失趋势
  - 提供同工关怀建议

#### 2. 新增6个提示词模板 ✅

- `check_upcoming_schedule` - 检查未来排班完整性
- `generate_sunday_preview` - 生成主日预览报告
- `analyze_role_health` - 分析岗位健康度
- `analyze_preacher_schedule` - 分析讲员轮换
- `track_sermon_series` - 追踪证道系列进度
- `analyze_volunteer_growth` - 分析同工趋势

#### 3. 技术实现 ✅

- **辅助函数**：6个核心分析函数
- **数据集成**：复用现有`load_service_layer_data()`函数
- **错误处理**：统一的错误处理和输出格式
- **向后兼容**：不修改现有工具，只新增功能

---

## [3.2.0] - 2025-10-10

### 🎯 主要更新：同工服侍分析提示词

**新增三个智能分析提示词**

#### 1. 新增提示词 ✅

##### `analyze_next_sunday_volunteers`
- **功能**：自动分析下周日的同工服侍安排
- **特性**：
  - 自动计算下周日日期（无需手动输入）
  - 列出所有服侍岗位及对应同工
  - 统计服侍人数和岗位覆盖情况
  - 识别空缺岗位
- **使用场景**：周中准备、服侍提醒、空缺填补

##### `analyze_recent_volunteer_roles`
- **功能**：分析最近几周同工在不同岗位的服侍情况
- **特性**：
  - 识别"多面手"同工（在多个岗位服侍）
  - 分析岗位轮换模式
  - 发现岗位依赖性风险
  - 提供培训和优化建议
- **使用场景**：同工培训规划、岗位优化、风险管理

##### `analyze_volunteer_frequency`
- **功能**：分析同工服侍频率，优化排班均衡性
- **特性**：
  - 统计每位同工的服侍次数和频率
  - 识别服侍过多的同工（需要关怀）
  - 识别服侍较少的同工（可以增加）
  - 评估排班均衡性
  - 按岗位分析人手配置
- **使用场景**：同工关怀、排班优化、年度评估

#### 2. 文档更新 📄
- **新增** `VOLUNTEER_ANALYSIS_PROMPTS.md` - 完整使用指南
  - 详细功能说明
  - 参数说明
  - 使用场景
  - 预期输出示例
  - 最佳实践
- **新增** `examples/volunteer_analysis_examples.md` - 实际使用示例
  - 4个完整对话示例
  - 使用技巧
  - 常见问题解答
- **更新** `README.md` - v3.2 特性说明

#### 3. 测试验证 ✅
- 创建自动化测试脚本 `test_volunteer_analysis_prompts.py`
- 验证所有三个提示词功能正常
- 测试日期自动计算逻辑
- 测试参数灵活性

#### 4. 技术实现细节
- **日期计算**：自动计算下周日日期（考虑周日情况）
- **灵活参数**：所有参数都是可选的，使用智能默认值
- **中文支持**：完全支持中文提示和输出
- **数据来源**：基于现有的 MCP 工具和资源
  - `query_volunteers_by_date`
  - `query_date_range`
  - `ministry://volunteer/assignments`
  - `ministry://stats/volunteers`

#### 5. 实际应用价值
- 📅 **提前准备**：周中就能了解下周日安排
- 🤝 **同工关怀**：及时发现服侍过于频繁的同工
- 📊 **数据驱动**：基于数据优化排班决策
- 🎯 **精准培训**：识别培训需求和人才缺口
- ⚖️ **均衡服侍**：让每位同工都有合适的服侍机会

**使用示例**:
```
# 在 Claude Desktop 或 ChatGPT 中
"下周日有哪些同工服侍？"
"分析最近2个月同工的服侍频率"
"哪些同工在多个岗位服侍？"
```

---

## [3.1.0] - 2025-10-10

### 🎯 主要更新：OpenAI Apps SDK 对齐

**完全兼容 ChatGPT Apps SDK**

#### 1. 工具元数据增强 ✅
- 为所有 7 个工具添加 `meta` 字段
- 支持状态字符串显示（`openai/toolInvocation/invoking` 和 `invoked`）

#### 2. 响应格式升级 ✅
- `text` 字段：人类可读的简短描述（非 JSON 字符串）
- `structuredContent` 字段：AI 可理解的结构化数据
- 移除冗余的 `timestamp` 字段

#### 3. 测试验证 ✅
- 创建自动化测试脚本 `test_openai_alignment.py`
- 100% 测试通过率
- 验证 HTTP 服务器序列化兼容性

#### 4. 文档更新 📄
- 新增 `docs/OPENAI_ALIGNMENT.md` - 完整对齐报告
- 更新 `README.md` - v3.1 特性说明

**参考**:
- [OpenAI Apps SDK 文档](https://developers.openai.com/apps-sdk/build/mcp-server)
- [Pizzaz 示例代码](https://github.com/openai/openai-apps-sdk-examples)

---

## [3.0.3] - 2025-10-07

### 修复 (Hotfix) 🔧
- 🐛 **修复 GCS 客户端初始化失败问题**
  - **问题**: `sync_from_gcs` 返回 "GCS client not initialized"
  - **原因**: MCP Server 使用相对路径，工作目录不同导致文件找不到
  - **修复**: 
    - 使用绝对路径加载配置文件和服务账号
    - `SCRIPT_DIR = Path(__file__).parent.absolute()`
    - 自动转换相对路径为绝对路径
  - **改进**: 
    - 增强错误日志，显示详细的初始化过程
    - `sync_from_gcs` 返回诊断信息（配置路径、文件存在性等）
    - 提供故障排查建议

### 重构 🔄
- 🎯 **MCP Tools 架构重构：从 GCS Bucket 直接读取数据**
  - **问题**: 每次查询都触发数据清洗管线，速度慢（30-60秒），频繁失败
  - **解决方案**: MCP Server 直接从 GCS bucket 读取已生成的服务层数据
  - **性能提升**: 响应时间从 30-60秒 降至 1-2秒
  - **架构**: 优先从 GCS 读取，失败时回退到本地文件
  
### 新增 ✨
- 📊 **新增 3 个查询工具**（AI 优先使用）
  - `query_volunteers_by_date` - 查询指定日期的同工服侍安排
  - `query_sermon_by_date` - 查询指定日期的证道信息
  - `query_date_range` - 查询时间范围内的所有安排
  
- 🔄 **新增 `sync_from_gcs` 工具**
  - 从 GCS bucket 同步最新数据到本地
  - 支持多版本同步（latest, 2025, 2024...）
  
- 🔧 **GCS 客户端自动初始化**
  - MCP Server 启动时自动连接 GCS
  - 从 `config/config.json` 读取配置
  - 支持服务账号认证

### 改进 🎨
- 📝 **工具分类标记**
  - 查询工具：无标记（AI 优先使用）
  - 管理工具：标记 `[管理员]`（AI 避免使用）
  
- 🏷️ **智能数据加载**
  - 优先从 GCS bucket 读取（生产数据）
  - 失败时自动回退到本地文件
  - 友好的错误提示

### 移除 ❌
- 🗑️ **移除 2 个非核心工具**
  - `get_pipeline_status` - 不再需要检查pipeline状态
  - `add_person_alias` - 非 MCP 职责，需手动编辑 Sheets

### 文档 📄
- 📖 **新增重构说明文档**
  - `MCP_TOOLS_REFACTOR_v3.0.3.md` - 完整重构说明
  - 包含设计理念、使用示例、性能对比
  - 迁移指南和测试验证步骤

## [3.0.2] - 2025-10-07

### 修复 🐛
- 🔧 **修复 MCP Tools 参数不匹配问题**
  - **问题 1**: `ServiceLayerManager.__init__() takes 1 positional argument but 2 were given`
    - 原因：`ServiceLayerManager()` 不接受参数，但传递了 `CONFIG_PATH`
    - 修复：移除 `CONFIG_PATH` 参数，使用无参初始化
    - 位置：`mcp_server.py` line 254
  
  - **问题 2**: `CleaningPipeline.run() got an unexpected keyword argument 'force_clean'`
    - 原因：`run()` 方法只接受 `dry_run` 参数，但传递了 `force_clean`
    - 修复：移除 `force_clean` 参数
    - 位置：`mcp_server.py` lines 235, 287
  
  - **问题 3**: `CleaningPipeline.run()` 返回值类型不匹配
    - 原因：`run()` 返回 `int` 退出码，而非字典
    - 修复：正确处理整数返回值，转换为适当的 JSON 响应
    - 影响：`clean_ministry_data` 和 `validate_raw_data` 工具
  
  - **问题 4**: `ServiceLayerManager` 方法调用错误
    - 原因：不存在 `generate_sermon_domain()` 和 `generate_volunteer_domain()` 方法
    - 修复：使用 `generate_all_years()` 和 `generate_and_save()` 方法
    - 加载清洗后的数据：从 `logs/clean_preview.json` 读取
  
  - 影响范围：所有 MCP Tools 调用
  - 测试状态：待 Claude Desktop 验证

### 改进 🎨
- 📊 **增强 `generate_service_layer` 工具**
  - 自动检查清洗数据是否存在，给出友好提示
  - 支持 `generate_all_years` 参数，可选择生成所有年份或仅最新数据
  - 返回生成的文件路径列表，便于后续操作
  
- 📈 **改进 `validate_raw_data` 工具**
  - 返回验证报告预览（前 1000 字符）
  - 指引用户查看完整验证报告文件

## [3.0.1] - 2025-10-07

### 修复 🐛
- 🔧 **修复 MCP 查询失败问题**
  - 问题：查询"下个主日都有谁事工"时出现 `'AnyUrl' object has no attribute 'startswith'` 错误
  - 原因：MCP SDK 传递的 URI 是 `AnyUrl` 对象而非字符串
  - 修复：在 `handle_read_resource` 函数中添加 `uri_str = str(uri)` 转换
  - 影响范围：所有 MCP 资源查询（sermon, volunteer, stats 等）
  - 测试：创建了完整的测试脚本 `test_next_sunday.sh`

### 新增 ✨
- 📄 **新增文档**
  - `MCP_QUERY_FIX.md` - 技术修复说明文档
  - `HOW_TO_QUERY_NEXT_SUNDAY.md` - 用户使用指南
  - `test_next_sunday.sh` - 快速测试脚本

## [3.0.0] - 2025-10-07

### 新增 ✨

#### MCP (Model Context Protocol) 集成
- 🤖 **完整 MCP 服务器实现**：支持 AI 助手无缝集成
  - 5 个 Tools（工具）：执行数据清洗、生成服务层、验证数据等
  - 10 个 Resources（资源）：提供证道数据、同工数据、统计信息的只读访问
  - 5 个 Prompts（提示词）：预定义分析模板，引导 AI 进行数据分析
- 🔌 **双传输模式**
  - stdio 模式：本地 Claude Desktop 集成
  - HTTP/SSE 模式：远程访问支持
- 🔒 **Bearer Token 鉴权**：保护远程 MCP 服务
- 📦 **MCPB 打包格式**：一键分发和部署

#### MCP Tools（工具）
- `clean_ministry_data` - 触发数据清洗管线
- `generate_service_layer` - 生成服务层数据
- `validate_raw_data` - 校验原始数据质量
- `add_person_alias` - 添加人员别名映射
- `get_pipeline_status` - 查询管线运行状态

#### MCP Resources（资源）
- `ministry://sermon/records` - 证道记录
- `ministry://sermon/by-preacher/{name}` - 按讲员查询
- `ministry://sermon/series` - 讲道系列
- `ministry://volunteer/assignments` - 同工安排
- `ministry://volunteer/by-person/{id}` - 个人服侍记录
- `ministry://volunteer/availability/{month}` - 排班空缺
- `ministry://stats/summary` - 综合统计
- `ministry://stats/preachers` - 讲员统计
- `ministry://stats/volunteers` - 同工统计
- `ministry://config/aliases` - 别名映射

#### MCP Prompts（提示词）
- `analyze_preaching_schedule` - 分析讲道安排
- `analyze_volunteer_balance` - 分析同工均衡
- `find_scheduling_gaps` - 查找排班空缺
- `check_data_quality` - 检查数据质量
- `suggest_alias_merges` - 建议合并别名

#### 新增 HTTP 端点
- `GET /mcp/capabilities` - MCP 能力查询
- `POST /mcp` - JSON-RPC 端点
- `POST /mcp/sse` - SSE 流式端点
- `GET /mcp/tools` - 列出所有工具
- `POST /mcp/tools/{name}` - 调用工具
- `GET /mcp/resources` - 列出所有资源
- `GET /mcp/resources/read` - 读取资源
- `GET /mcp/prompts` - 列出所有提示词
- `GET /mcp/prompts/{name}` - 获取提示词

#### 新增工具和脚本
- `mcp_server.py` - MCP Server 核心实现（stdio 模式）
- `mcp_http_server.py` - HTTP/SSE 传输层实现
- `deploy-mcp-cloud-run.sh` - MCP Cloud Run 一键部署
- `test_mcp_server.sh` - MCP 本地测试脚本
- `examples/mcp_client_example.py` - Python 客户端示例

#### MCPB Bundle
- 📦 **ministry-data.mcpb** - 独立可执行的 MCP 包
  - 包含所有依赖和配置
  - 支持一键安装到 Claude Desktop
  - 支持 Windows、macOS、Linux
- 🚀 **一键部署命令**
  ```bash
  npx -y @mcpbundle/cli install ministry-data.mcpb
  ```

#### 新增文档
- `docs/MCP_DESIGN.md` - MCP 架构设计方案（1300+ 行）
- `docs/MCP_DEPLOYMENT.md` - MCP 部署完整指南
- `docs/MCP_INTEGRATION.md` - MCP 集成指南
- `QUICKSTART_MCP.md` - MCP 5分钟快速开始
- `MCP_IMPLEMENTATION_SUMMARY.md` - MCP 实施总结
- `MCP_QUICK_REFERENCE.md` - MCP 快速参考
- `MCPB_BUNDLE_GUIDE.md` - MCPB 打包指南
- `config/claude_desktop_config.example.json` - Claude Desktop 配置示例

### 改进 🔧

#### AI 集成体验
- 🤖 **自然语言查询**：通过 Claude Desktop 自然对话查询数据
- 📊 **智能分析**：AI 自动调用合适的 Resources 进行分析
- 🎯 **预定义模板**：5 个 Prompts 引导常见分析任务
- 🔄 **自动化操作**：AI 可触发数据清洗和生成任务

#### 架构优化
- 🏗️ **模块化设计**：MCP Server 独立于 FastAPI 应用
- 🔌 **可插拔传输**：stdio 和 HTTP/SSE 可切换
- 📦 **容器化支持**：`MCP_MODE` 环境变量控制启动模式
- 🌐 **云原生**：支持部署到 Cloud Run

#### 安全增强
- 🔐 **Bearer Token 鉴权**：保护 MCP HTTP 端点
- 🔒 **Secret Manager 集成**：安全存储敏感配置
- 📝 **请求审计日志**：记录所有 MCP 操作
- 🛡️ **CORS 配置**：限制跨域访问

### 技术栈更新 🛠️

#### 新增依赖
- `mcp>=1.0.0` - MCP Python SDK
- `sse-starlette>=2.0.0` - SSE 流式传输
- `jsonschema>=4.0.0` - JSON Schema 验证

#### 部署工具
- mcpbundle CLI - MCPB 打包工具
- Cloud Run - MCP HTTP 服务部署

### 使用场景 🎬

#### 场景 1：AI 助手数据分析
```
用户: "请分析2024年的讲道安排"

Claude:
1. [调用 Resource] ministry://sermon/records?year=2024
2. [调用 Resource] ministry://stats/preachers?year=2024
3. [生成分析报告]

输出:
- 2024年共52次主日聚会
- 12位讲员参与，其中王通讲道15次
- 涉及15个讲道系列
- 建议：李牧师仅讲道2次，可考虑增加机会
```

#### 场景 2：AI 辅助排班
```
用户: "10月份还有哪些周日没安排敬拜带领？"

Claude:
1. [调用 Resource] ministry://volunteer/availability/2024-10
2. [分析空缺]
3. [建议候选人]

输出:
- 10月6日和10月20日尚未安排
- 建议候选人：谢苗（近期服侍2次）、华亚西（1次）
```

#### 场景 3：自动化数据清洗
```
用户: "帮我更新一下最新的数据"

Claude:
1. [调用 Tool] clean_ministry_data(dry_run=false)
2. [调用 Tool] generate_service_layer(generate_all_years=true)

输出:
✅ 数据清洗完成 - 新增3条记录
✅ 服务层生成完成 - 覆盖2024-2026年份
```

### MCP 架构 🏗️

```
┌─────────────────────────────────────────────────────┐
│                    AI 助手层                         │
│  (Claude Desktop / ChatGPT / Custom AI)             │
└────────────────┬────────────────────────────────────┘
                 │ MCP 协议 (stdio / HTTP/SSE)
┌────────────────▼────────────────────────────────────┐
│                   MCP 服务器                         │
│  ┌──────────┬──────────────┬──────────────────┐    │
│  │  Tools   │  Resources   │     Prompts      │    │
│  │ (执行操作)│  (数据访问)   │   (对话模板)      │    │
│  └──────────┴──────────────┴──────────────────┘    │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│                 FastAPI 应用层                       │
│  清洗管线 + 服务层 + Cloud Storage                   │
└─────────────────────────────────────────────────────┘
```

### 文档更新 📚
- 📖 更新 README.md 到 v3.0
- 📝 新增 MCP 相关文档（6个）
- 🔍 更新 CHANGELOG.md 到 v3.0
- 📋 新增配置示例文件

### 成本估算 💰

- **Cloud Run（MCP HTTP 模式）**：~$1.00/月（含 MCP 端点）
- **Cloud Scheduler**：$0.00/月（免费额度内）
- **Cloud Storage**：< $0.01/月
- **总计**：~$1.00/月（相比 v2.0 增加 $0.43/月）

### Breaking Changes ⚠️

- 🔄 **MCP 端点需要鉴权**：HTTP 模式下默认启用 Bearer Token
- 🔄 **Dockerfile 更新**：支持 `MCP_MODE` 环境变量
- 🔄 **新增环境变量**：`MCP_BEARER_TOKEN`, `MCP_REQUIRE_AUTH`, `MCP_MODE`

### 迁移指南

#### 从 v2.0 升级到 v3.0

1. **更新依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置 MCP（可选）**
   ```bash
   # 本地 stdio 模式
   cp config/claude_desktop_config.example.json ~/.config/Claude/claude_desktop_config.json
   # 编辑并设置正确路径
   
   # 远程 HTTP 模式
   export MCP_MODE=http
   export MCP_BEARER_TOKEN=$(openssl rand -hex 32)
   ./deploy-mcp-cloud-run.sh
   ```

3. **验证功能**
   ```bash
   # 测试本地 MCP Server
   ./test_mcp_server.sh
   
   # 运行客户端示例
   python examples/mcp_client_example.py
   ```

4. **继续使用原有功能**
   - ✅ 所有 v2.0 功能完全兼容
   - ✅ 原有 API 端点保持不变
   - ✅ 数据清洗和服务层功能无变化

---

## [2.0.0] - 2025-10-07

### 新增 ✨

#### 服务层（Service Layer）
- 📦 **服务层架构**：将清洗层数据转换为两个独立的领域模型
  - Sermon Domain（证道域）：证道相关的核心信息
  - Volunteer Domain（同工域）：主日服侍同工信息
- 🔄 **自动生成所有年份**：智能检测并生成所有历史年份的数据
- ☁️ **Cloud Storage 集成**：自动上传到 Google Cloud Storage
- 📊 **数据组织**：按领域和年份组织文件（latest + yearly）

#### 云部署（Cloud Deployment）
- ☁️ **Cloud Run 部署**：一键部署到 Google Cloud Run
- ⏰ **Cloud Scheduler**：定时任务自动更新数据（每30分钟）
- 🔍 **智能变化检测**：SHA-256哈希比对，仅在数据变化时执行清洗
- 🚀 **FastAPI 应用**：提供完整的 RESTful API
- 🔒 **Bearer Token 认证**：保护定时触发端点

#### API 端点
- `POST /api/v1/clean` - 手动触发数据清洗
- `POST /api/v1/query` - 查询数据（支持多种过滤条件）
- `GET /api/v1/stats` - 获取统计信息
- `GET /api/v1/preview` - 获取最新清洗预览
- `POST /api/v1/service-layer/generate` - 生成服务层数据
- `GET /api/v1/sermon` - 获取证道域数据
- `GET /api/v1/volunteer` - 获取同工域数据
- `POST /trigger-cleaning` - Cloud Scheduler 触发端点
- `GET /mcp/tools` - MCP 工具定义

#### 存储和数据管理
- 📦 **Google Cloud Storage Bucket**：grace-irvine-ministry-data
- 📁 **文件组织结构**：domains/sermon|volunteer/{latest, 2024, 2025, 2026}
- 🔄 **版本控制**：支持历史版本管理

#### 工具和脚本
- `scripts/service_layer.py` - 服务层转换器
- `scripts/cloud_storage_utils.py` - 云存储工具
- `scripts/change_detector.py` - 变化检测
- `app.py` - FastAPI 应用
- `Dockerfile` - 容器配置
- `deploy-cloud-run.sh` - 部署脚本
- `setup-cloud-scheduler.sh` - 定时任务设置

#### 测试脚本
- `test_deployed_api.sh` - API 端点测试
- `test_change_detection.sh` - 变化检测测试
- `test_service_layer.sh` - 服务层测试
- `test_all_years_api.sh` - 所有年份API测试

#### 文档
- `SERVICE_LAYER.md` - 服务层完整文档
- `DEPLOYMENT.md` - 云部署完整文档
- `STORAGE.md` - 存储和数据管理文档
- `MCP_INTEGRATION.md` - MCP 集成指南
- `TROUBLESHOOTING.md` - 故障排除指南
- `QUICK_COMMANDS.md` - 快速命令参考
- `ARCHITECTURE.md` - 项目架构文档

### 改进 🔧

#### 性能优化
- ⚡ **智能跳过**：无数据变化时< 1秒返回
- 🎯 **并行处理**：多年份并行生成
- 📊 **增量更新**：仅更新变化的部分

#### 用户体验
- 📝 **详细日志**：完整的操作记录和错误信息
- 🎨 **交互式 API 文档**：Swagger UI（/docs）
- 📊 **实时统计**：动态数据统计和分析

### 技术栈更新 🛠️

#### 新增依赖
- `fastapi>=0.109.0` - Web 框架
- `uvicorn[standard]>=0.27.0` - ASGI 服务器
- `pydantic>=2.5.0` - 数据验证
- `google-cloud-storage` - GCS 集成（可选）
- `python-multipart>=0.0.6` - 文件上传支持

#### 部署工具
- Docker - 容器化
- Google Cloud Build - 镜像构建
- Google Cloud Run - 无服务器部署
- Google Cloud Scheduler - 定时任务
- Google Cloud Storage - 对象存储

### 数据流 🔄

```
原始层 (Google Sheets)
    ↓
清洗层 (Google Sheets)
    ↓
服务层 (JSON)
    ├── Sermon Domain
    └── Volunteer Domain
    ↓
Cloud Storage (GCS)
    ├── latest.json
    └── yearly files (2024, 2025, 2026)
```

### 成本估算 💰

- **Cloud Run**：~$0.57/月（基本在免费额度内）
- **Cloud Scheduler**：$0.00/月（免费额度内）
- **Cloud Storage**：< $0.01/月（490 KB）
- **总计**：~$0.57/月

### 安全更新 🔒

- 🔐 Bearer Token 认证保护定时任务
- 🔒 Secret Manager 存储敏感凭证
- 🛡️ 最小权限原则（IAM）
- 🔍 详细的审计日志

---

## [1.0.0] - 2025-10-06

### 新增 ✨

#### 核心功能
- 完整的数据清洗管线，支持从原始 Google Sheet 到清洗层 Google Sheet 的自动化清洗
- 可配置的清洗规则（通过 `config/config.json` 管理）
- 人名别名映射功能，支持多对一映射（中文名/英文名/昵称 → 统一 ID）
- 数据校验功能，生成详细的错误和警告报告
- Dry-run 模式，支持先预览后写入

#### 清洗规则
- 日期标准化（支持多种格式输入，统一输出 YYYY-MM-DD）
- 文本清理（去除空格、全角空格、占位符处理）
- 经文引用标准化
- 歌曲拆分与去重（支持多种分隔符）
- 列合并功能（如合并多个敬拜同工列）
- 服务周数自动计算（ISO 周数）

#### 模块
- `gsheet_utils.py`: Google Sheets API 封装
- `cleaning_rules.py`: 清洗规则实现
- `alias_utils.py`: 别名映射工具
- `validators.py`: 数据校验器
- `clean_pipeline.py`: 主清洗管线

#### 工具和脚本
- `run_pipeline.sh`: 便捷执行脚本，支持参数解析和环境检查
- 完整的单元测试套件（`tests/test_cleaning.py`）
- 样例数据（`tests/sample_raw.csv`, `tests/sample_aliases.csv`）

#### 文档
- 完整的用户指南（`README.md`）
- 快速上手指南（`QUICKSTART.md`）
- 项目概览文档（`PROJECT_OVERVIEW.md`）
- 任务说明文档（`README_prompt.md`）
- 示例配置文件（`config/config.example.json`）

#### 输出
- CSV 预览文件
- JSON 预览文件
- 详细的校验报告（保存到 `logs/`）
- 控制台摘要输出

### 安全 🔒
- 最小权限原则（原始表只读、清洗表只写）
- 服务账号认证
- 敏感信息保护（`.gitignore` 配置）
- 日志不打印敏感令牌

### 测试 🧪
- 单元测试覆盖所有核心功能（17个测试，100%通过）
- 日期清洗测试
- 别名映射测试
- 歌曲拆分测试
- 列合并测试
- 数据校验测试
- 完整管线测试

---

## 版本说明

### 版本号格式：主版本号.次版本号.修订号

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向下兼容的功能新增
- **修订号（Patch）**：向下兼容的问题修复

### 变更类型

- **新增（Added）**：新功能
- **变更（Changed）**：现有功能的变更
- **废弃（Deprecated）**：即将移除的功能
- **移除（Removed）**：已移除的功能
- **修复（Fixed）**：问题修复
- **安全（Security）**：安全相关的变更
