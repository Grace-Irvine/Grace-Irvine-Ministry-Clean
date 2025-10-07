# MCP (Model Context Protocol) 架构设计方案

## 📋 目录

- [设计理念](#设计理念)
- [MCP Tools（工具）](#mcp-tools工具)
- [MCP Resources（资源）](#mcp-resources资源)
- [MCP Prompts（提示词）](#mcp-prompts提示词)
- [实现方案](#实现方案)
- [使用场景](#使用场景)
- [架构图](#架构图)

---

## 🎯 设计理念

### MCP 三大组件的设计原则

| 组件 | 用途 | 特点 | 本项目应用 |
|------|------|------|-----------|
| **Tools** | 执行动作/操作 | 改变状态、触发任务 | 数据清洗、生成服务层 |
| **Resources** | 提供数据资源 | 只读访问、结构化数据 | 证道数据、同工数据 |
| **Prompts** | 预定义对话模板 | 引导用户提问 | 数据分析、排班助手 |

### 本项目的 MCP 定位

```
原始层 (Google Sheets)
    ↓
清洗层 (Cleaning Pipeline)
    ↓
服务层 (Domain Models)
    ↓
MCP 服务器 ← AI 助手通过 MCP 协议访问
```

---

## 🛠️ MCP Tools（工具）

**定义**：需要执行操作、改变状态或触发任务的功能

### 1. 数据清洗工具

#### `clean_ministry_data`
```typescript
{
  name: "clean_ministry_data",
  description: "触发数据清洗管线，从原始层读取数据并清洗标准化",
  inputSchema: {
    type: "object",
    properties: {
      dry_run: {
        type: "boolean",
        description: "是否为测试模式（不写入Google Sheets）",
        default: false
      },
      force: {
        type: "boolean", 
        description: "是否强制执行（跳过变化检测）",
        default: false
      }
    }
  }
}
```

**映射到**: `POST /api/v1/clean`

**用途**: 
- ✅ 执行清洗操作（状态变化）
- ✅ 更新Google Sheets（写操作）
- ✅ 生成清洗报告

---

#### `validate_raw_data`
```typescript
{
  name: "validate_raw_data",
  description: "校验原始数据质量，检查必填字段、格式错误等（不执行清洗）",
  inputSchema: {
    type: "object",
    properties: {
      check_duplicates: {
        type: "boolean",
        description: "是否检查重复记录",
        default: true
      },
      generate_report: {
        type: "boolean",
        description: "是否生成详细报告",
        default: true
      }
    }
  }
}
```

**新增功能** - 需要实现

**用途**:
- ✅ 数据质量检查（只读操作，但生成报告）
- ✅ 早期发现数据问题

---

### 2. 服务层生成工具

#### `generate_service_layer`
```typescript
{
  name: "generate_service_layer",
  description: "生成或更新服务层领域数据（sermon 和 volunteer 域）",
  inputSchema: {
    type: "object",
    properties: {
      domains: {
        type: "array",
        items: { type: "string", enum: ["sermon", "volunteer"] },
        description: "要生成的领域列表",
        default: ["sermon", "volunteer"]
      },
      generate_all_years: {
        type: "boolean",
        description: "是否生成所有年份的数据",
        default: true
      },
      upload_to_bucket: {
        type: "boolean",
        description: "是否上传到 Cloud Storage",
        default: false
      }
    }
  }
}
```

**映射到**: `POST /api/v1/service-layer/generate`

**用途**:
- ✅ 生成领域模型数据（状态变化）
- ✅ 可选上传到Cloud Storage（写操作）

---

### 3. 别名管理工具

#### `add_person_alias`
```typescript
{
  name: "add_person_alias",
  description: "添加人员别名映射（例如：将'张牧师'和'Pastor Zhang'映射到同一person_id）",
  inputSchema: {
    type: "object",
    properties: {
      alias: {
        type: "string",
        description: "别名（如'张牧师'）",
        required: true
      },
      person_id: {
        type: "string",
        description: "人员ID（如'person_6511_王通'）",
        required: true
      },
      display_name: {
        type: "string",
        description: "显示名称",
        required: true
      }
    },
    required: ["alias", "person_id", "display_name"]
  }
}
```

**新增功能** - 需要实现

**用途**:
- ✅ 添加别名映射（写操作）
- ✅ 更新Google Sheets别名表

---

#### `merge_person_aliases`
```typescript
{
  name: "merge_person_aliases",
  description: "合并两个人员ID的所有别名（当发现重复人员时使用）",
  inputSchema: {
    type: "object",
    properties: {
      source_person_id: {
        type: "string",
        description: "源人员ID（将被合并）",
        required: true
      },
      target_person_id: {
        type: "string", 
        description: "目标人员ID（保留）",
        required: true
      },
      keep_display_name: {
        type: "string",
        enum: ["source", "target"],
        description: "保留哪个显示名称",
        default: "target"
      }
    },
    required: ["source_person_id", "target_person_id"]
  }
}
```

**新增功能** - 需要实现

**用途**:
- ✅ 批量更新别名（写操作）
- ✅ 数据去重

---

### 4. 调度和监控工具

#### `trigger_scheduled_update`
```typescript
{
  name: "trigger_scheduled_update",
  description: "手动触发定时更新任务（通常由Cloud Scheduler自动执行）",
  inputSchema: {
    type: "object",
    properties: {
      force: {
        type: "boolean",
        description: "是否强制执行（跳过变化检测）",
        default: false
      }
    }
  }
}
```

**映射到**: `POST /trigger-cleaning`（需要认证）

**用途**:
- ✅ 手动触发定时任务
- ⚠️ 需要Bearer Token认证

---

#### `get_pipeline_status`
```typescript
{
  name: "get_pipeline_status",
  description: "获取数据清洗管线的运行状态和历史记录",
  inputSchema: {
    type: "object",
    properties: {
      last_n_runs: {
        type: "integer",
        description: "返回最近N次运行记录",
        default: 10
      }
    }
  }
}
```

**新增功能** - 需要实现

**用途**:
- ✅ 查看清洗历史
- ✅ 监控数据质量趋势

---

## 📦 MCP Resources（资源）

**定义**：提供只读访问的结构化数据资源

### 资源 URI 设计规范

```
ministry://domain/resource/identifier?params
```

**示例**:
```
ministry://sermon/records/2024
ministry://volunteer/assignments/2024-10-07
ministry://stats/summary
```

---

### 1. 证道域资源（Sermon Domain）

#### Resource: `sermon-records`
```typescript
{
  uri: "ministry://sermon/records/{year?}",
  name: "sermon-records",
  description: "证道域记录（包含讲道标题、讲员、经文、诗歌等）",
  mimeType: "application/json",
  parameters: {
    year: {
      type: "string",
      description: "按年份筛选（2024, 2025, 2026）",
      required: false
    }
  }
}
```

**映射到**: `GET /api/v1/sermon?year={year}`

**返回结构**:
```json
{
  "metadata": {
    "domain": "sermon",
    "version": "1.0",
    "total_count": 52,
    "date_range": {
      "start": "2024-01-07",
      "end": "2024-12-29"
    }
  },
  "sermons": [
    {
      "service_date": "2024-01-07",
      "sermon": {
        "title": "第一个福音",
        "series": "遇见耶稣",
        "scripture": "创世纪 3"
      },
      "preacher": {
        "id": "person_6511_王通",
        "name": "王通"
      },
      "songs": ["奇异恩典", "有福的确据"]
    }
  ]
}
```

---

#### Resource: `sermon-by-preacher`
```typescript
{
  uri: "ministry://sermon/by-preacher/{preacher_name}",
  name: "sermon-by-preacher",
  description: "按讲员查询证道记录",
  mimeType: "application/json",
  parameters: {
    preacher_name: {
      type: "string",
      description: "讲员名称",
      required: true
    },
    year: {
      type: "string",
      description: "年份筛选",
      required: false
    }
  }
}
```

**新增功能** - 需要实现

---

#### Resource: `sermon-series`
```typescript
{
  uri: "ministry://sermon/series/{series_name?}",
  name: "sermon-series",
  description: "讲道系列信息和进度",
  mimeType: "application/json"
}
```

**新增功能** - 需要实现

**用途**: 
- 追踪系列讲道进度
- 查看某个系列的所有讲道

---

### 2. 同工域资源（Volunteer Domain）

#### Resource: `volunteer-assignments`
```typescript
{
  uri: "ministry://volunteer/assignments/{date?}",
  name: "volunteer-assignments",
  description: "同工服侍安排（敬拜同工、技术同工等）",
  mimeType: "application/json",
  parameters: {
    date: {
      type: "string",
      description: "日期（YYYY-MM-DD）或年份（YYYY）",
      required: false
    }
  }
}
```

**映射到**: 
- `GET /api/v1/volunteer?year={year}`
- `GET /api/v1/volunteer?service_date={date}`

**返回结构**:
```json
{
  "metadata": {
    "domain": "volunteer",
    "version": "1.0",
    "total_count": 52
  },
  "volunteers": [
    {
      "service_date": "2024-01-07",
      "worship": {
        "lead": { "id": "person_8101_谢苗", "name": "谢苗" },
        "team": [
          { "id": "person_9017_屈小煊", "name": "屈小煊" }
        ],
        "pianist": { "id": "person_shawn", "name": "Shawn" }
      },
      "technical": {
        "audio": { "id": "person_3850_靖铮", "name": "靖铮" },
        "video": { "id": "person_2012_俊鑫", "name": "俊鑫" }
      }
    }
  ]
}
```

---

#### Resource: `volunteer-by-person`
```typescript
{
  uri: "ministry://volunteer/by-person/{person_id}",
  name: "volunteer-by-person",
  description: "查询某人的所有服侍记录",
  mimeType: "application/json",
  parameters: {
    person_id: {
      type: "string",
      description: "人员ID或名称",
      required: true
    },
    year: {
      type: "string",
      description: "年份筛选",
      required: false
    }
  }
}
```

**新增功能** - 需要实现

**用途**:
- 查看个人服侍历史
- 统计服侍频率

---

#### Resource: `volunteer-availability`
```typescript
{
  uri: "ministry://volunteer/availability/{date_range}",
  name: "volunteer-availability",
  description: "查询某时间范围内的空缺岗位",
  mimeType: "application/json",
  parameters: {
    date_range: {
      type: "string",
      description: "日期范围（YYYY-MM）",
      required: true
    }
  }
}
```

**新增功能** - 需要实现

**用途**:
- 发现排班空缺
- 辅助排班

---

### 3. 统计和分析资源

#### Resource: `ministry-stats`
```typescript
{
  uri: "ministry://stats/summary",
  name: "ministry-stats",
  description: "教会主日事工数据的综合统计信息",
  mimeType: "application/json"
}
```

**映射到**: `GET /api/v1/stats`

**返回结构**:
```json
{
  "stats": {
    "total_records": 131,
    "date_range": {
      "earliest": "2024-01-07",
      "latest": "2026-07-05"
    },
    "sermon_domain": {
      "unique_preachers": 12,
      "unique_series": 15
    },
    "volunteer_domain": {
      "unique_worship_leaders": 15,
      "unique_audio_technicians": 8
    }
  }
}
```

---

#### Resource: `preacher-stats`
```typescript
{
  uri: "ministry://stats/preachers/{year?}",
  name: "preacher-stats",
  description: "讲员统计（讲道次数、涉及经文等）",
  mimeType: "application/json"
}
```

**新增功能** - 需要实现

---

#### Resource: `volunteer-stats`
```typescript
{
  uri: "ministry://stats/volunteers/{year?}",
  name: "volunteer-stats",
  description: "同工统计（服侍次数、岗位分布等）",
  mimeType: "application/json"
}
```

**新增功能** - 需要实现

---

### 4. 配置和元数据资源

#### Resource: `alias-mappings`
```typescript
{
  uri: "ministry://config/aliases",
  name: "alias-mappings",
  description: "人员别名映射表",
  mimeType: "application/json"
}
```

**新增功能** - 需要实现

**返回结构**:
```json
{
  "aliases": [
    {
      "alias": "张牧师",
      "person_id": "preacher_zhang",
      "display_name": "张牧师"
    },
    {
      "alias": "Pastor Zhang",
      "person_id": "preacher_zhang",
      "display_name": "张牧师"
    }
  ]
}
```

---

#### Resource: `data-schema`
```typescript
{
  uri: "ministry://config/schema",
  name: "data-schema",
  description: "数据模型和字段说明",
  mimeType: "application/json"
}
```

**新增功能** - 需要实现

**用途**:
- AI助手了解数据结构
- 自动生成查询

---

## 💬 MCP Prompts（提示词）

**定义**：预定义的对话模板，引导用户提问和分析

### 1. 数据分析提示

#### `analyze_preaching_schedule`
```typescript
{
  name: "analyze_preaching_schedule",
  description: "分析讲道安排和系列进度",
  arguments: [
    {
      name: "year",
      description: "要分析的年份",
      required: false
    },
    {
      name: "focus",
      description: "分析重点（series/preachers/scripture）",
      required: false
    }
  ],
  prompt: `请分析 {{year}} 年的讲道安排：

1. 列出所有讲道系列及其进度
2. 统计每位讲员的讲道次数
3. 分析涉及的圣经书卷分布
4. 识别可能的排班问题（如空缺、过于集中等）

使用 ministry://sermon/records/{{year}} 获取数据`
}
```

---

#### `analyze_volunteer_balance`
```typescript
{
  name: "analyze_volunteer_balance",
  description: "分析同工服侍负担均衡性",
  arguments: [
    {
      name: "year",
      description: "要分析的年份",
      required: false
    },
    {
      name: "role",
      description: "关注的岗位（worship_lead/audio/video等）",
      required: false
    }
  ],
  prompt: `请分析 {{year}} 年 {{role}} 岗位的同工服侍情况：

1. 统计每位同工的服侍次数
2. 计算服侍频率（平均多久服侍一次）
3. 识别服侍过多或过少的同工
4. 建议如何更均衡地分配服侍

使用 ministry://volunteer/assignments/{{year}} 获取数据`
}
```

---

### 2. 排班助手提示

#### `find_scheduling_gaps`
```typescript
{
  name: "find_scheduling_gaps",
  description: "查找排班空缺",
  arguments: [
    {
      name: "month",
      description: "查找的月份（YYYY-MM）",
      required: true
    }
  ],
  prompt: `请查找 {{month}} 月的排班空缺：

1. 列出所有主日日期
2. 识别哪些岗位尚未安排（讲员、敬拜、技术等）
3. 按紧急程度排序（日期越近越紧急）
4. 建议可以填补空缺的人员（基于历史数据）

使用 ministry://volunteer/availability/{{month}} 获取数据`
}
```

---

#### `suggest_preacher_rotation`
```typescript
{
  name: "suggest_preacher_rotation",
  description: "建议讲员轮换安排",
  arguments: [
    {
      name: "start_date",
      description: "开始日期",
      required: true
    },
    {
      name: "weeks",
      description: "计划周数",
      required: true
    }
  ],
  prompt: `请为从 {{start_date}} 开始的 {{weeks}} 周建议讲员轮换安排：

1. 获取所有讲员及其近期讲道频率
2. 考虑公平性和多样性
3. 避免同一讲员连续多周
4. 生成具体的日期和讲员配对建议

使用 ministry://stats/preachers 和 ministry://sermon/records 获取数据`
}
```

---

### 3. 数据质量提示

#### `check_data_quality`
```typescript
{
  name: "check_data_quality",
  description: "检查数据质量和完整性",
  prompt: `请全面检查数据质量：

1. 必填字段完整性（讲员、日期等）
2. 重复记录检测
3. 日期逻辑性（是否为主日、是否有时间跳跃）
4. 人名拼写一致性（可能的别名问题）
5. 生成详细的问题报告和修复建议

使用 validate_raw_data 工具执行检查`
}
```

---

#### `suggest_alias_merges`
```typescript
{
  name: "suggest_alias_merges",
  description: "建议可能需要合并的人员别名",
  prompt: `请分析并建议可能需要合并的人员别名：

1. 查找相似的人名（如'张牧师'和'张'）
2. 查找中英文名称对应（如'王丽'和'Wang Li'）
3. 识别拼写变体
4. 生成合并建议清单

使用 ministry://config/aliases 获取当前别名映射`
}
```

---

## 🔧 实现方案

### 阶段 1：扩展现有 API（已完成 90%）

#### 已实现的功能 ✅
- `POST /api/v1/clean` → `clean_ministry_data`
- `POST /api/v1/service-layer/generate` → `generate_service_layer`
- `GET /api/v1/sermon` → `sermon-records`
- `GET /api/v1/volunteer` → `volunteer-assignments`
- `GET /api/v1/stats` → `ministry-stats`

#### 需要补充的 API 端点 🔨

```python
# app.py 新增端点

@app.get("/api/v1/sermon/by-preacher/{preacher_name}")
async def get_sermons_by_preacher(preacher_name: str, year: Optional[int] = None):
    """Resource: sermon-by-preacher"""
    # 实现代码
    pass

@app.get("/api/v1/sermon/series")
async def get_sermon_series():
    """Resource: sermon-series"""
    # 实现代码
    pass

@app.get("/api/v1/volunteer/by-person/{person_id}")
async def get_volunteer_by_person(person_id: str, year: Optional[int] = None):
    """Resource: volunteer-by-person"""
    # 实现代码
    pass

@app.get("/api/v1/volunteer/availability/{year_month}")
async def get_volunteer_availability(year_month: str):
    """Resource: volunteer-availability"""
    # 实现代码
    pass

@app.get("/api/v1/stats/preachers")
async def get_preacher_stats(year: Optional[int] = None):
    """Resource: preacher-stats"""
    # 实现代码
    pass

@app.get("/api/v1/stats/volunteers")
async def get_volunteer_stats(year: Optional[int] = None):
    """Resource: volunteer-stats"""
    # 实现代码
    pass

@app.get("/api/v1/config/aliases")
async def get_alias_mappings():
    """Resource: alias-mappings"""
    # 实现代码
    pass

@app.post("/api/v1/config/aliases")
async def add_alias(request: AliasAddRequest):
    """Tool: add_person_alias"""
    # 实现代码
    pass

@app.post("/api/v1/config/aliases/merge")
async def merge_aliases(request: AliasMergeRequest):
    """Tool: merge_person_aliases"""
    # 实现代码
    pass

@app.post("/api/v1/validate")
async def validate_data(request: ValidationRequest):
    """Tool: validate_raw_data"""
    # 实现代码
    pass

@app.get("/api/v1/pipeline/status")
async def get_pipeline_status(last_n_runs: int = 10):
    """Tool: get_pipeline_status"""
    # 实现代码
    pass
```

---

### 阶段 2：实现 MCP 服务器

#### 选项 A：基于 FastAPI 的 MCP 服务器（推荐）

使用 FastAPI + MCP SDK 实现标准 MCP 服务器：

```python
# mcp_server.py

from mcp import Server
from mcp.server import NotificationOptions, ServerCapabilities
from mcp.server.models import InitializationOptions
import mcp.types as types

# 创建 MCP 服务器
server = Server("ministry-data-mcp")

# 注册 Tools
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="clean_ministry_data",
            description="触发数据清洗管线",
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {"type": "boolean", "default": False},
                    "force": {"type": "boolean", "default": False}
                }
            }
        ),
        # ... 其他工具
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "clean_ministry_data":
        # 调用 FastAPI 端点
        result = await call_api("POST", "/api/v1/clean", arguments)
        return [types.TextContent(type="text", text=json.dumps(result))]
    # ... 其他工具

# 注册 Resources
@server.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="ministry://sermon/records/{year}",
            name="sermon-records",
            description="证道域记录",
            mimeType="application/json"
        ),
        # ... 其他资源
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    # 解析 URI 并调用对应的 API
    if uri.startswith("ministry://sermon/records/"):
        year = extract_year_from_uri(uri)
        result = await call_api("GET", f"/api/v1/sermon?year={year}")
        return json.dumps(result)
    # ... 其他资源

# 注册 Prompts
@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="analyze_preaching_schedule",
            description="分析讲道安排和系列进度",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份",
                    required=False
                )
            ]
        ),
        # ... 其他提示
    ]

@server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
    if name == "analyze_preaching_schedule":
        year = arguments.get("year", "2024")
        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"请分析 {year} 年的讲道安排..."
                    )
                )
            ]
        )
    # ... 其他提示

# 启动服务器
if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ministry-data",
                    server_version="2.0.0",
                    capabilities=ServerCapabilities(
                        tools={"listChanged": True},
                        resources={"listChanged": True},
                        prompts={"listChanged": True}
                    )
                )
            )
    
    asyncio.run(main())
```

---

#### 选项 B：HTTP/SSE 传输层（用于远程访问）

如果需要远程访问MCP服务器（而不仅是本地stdio）：

```python
# mcp_http_server.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

mcp_http_app = FastAPI(title="Ministry Data MCP HTTP Server")

@mcp_http_app.post("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """SSE (Server-Sent Events) endpoint for MCP"""
    async def event_generator():
        # 处理 MCP 协议消息
        async for message in handle_mcp_messages(request):
            yield message
    
    return EventSourceResponse(event_generator())

@mcp_http_app.get("/mcp/capabilities")
async def get_mcp_capabilities():
    """返回 MCP 服务器能力"""
    return {
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True
        },
        "serverInfo": {
            "name": "ministry-data",
            "version": "2.0.0"
        }
    }
```

---

### 阶段 3：更新 Claude Desktop 配置

#### 本地 stdio 模式

```json
// ~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "ministry-data": {
      "command": "python",
      "args": [
        "/path/to/Grace-Irvine-Ministry-Clean/mcp_server.py"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",
        "CONFIG_PATH": "/path/to/config/config.json"
      }
    }
  }
}
```

#### 远程 HTTP 模式

```json
{
  "mcpServers": {
    "ministry-data-remote": {
      "url": "https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app/mcp/sse",
      "transport": "sse"
    }
  }
}
```

---

## 🎬 使用场景

### 场景 1：数据分析
```
用户: "请分析2024年的讲道安排"

Claude:
1. [调用 Resource] ministry://sermon/records/2024
2. [调用 Resource] ministry://stats/preachers/2024
3. [分析并生成报告]

输出:
- 2024年共52次主日聚会
- 12位讲员参与，其中王通讲道15次（最多）
- 涉及15个讲道系列，包括"遇见耶稣"、"以弗所书系列"等
- 建议：李牧师仅讲道2次，可以考虑增加机会
```

---

### 场景 2：排班助手
```
用户: "10月份还有哪些周日没安排敬拜带领？"

Claude:
1. [调用 Resource] ministry://volunteer/availability/2024-10
2. [分析空缺]
3. [调用 Resource] ministry://volunteer/by-person/{person_id} 查找候选人

输出:
- 10月6日（周日）尚未安排敬拜带领
- 10月20日（周日）尚未安排敬拜带领
- 建议候选人：
  - 谢苗（近3个月服侍2次，可用）
  - 华亚西（近3个月服侍1次，可用）
```

---

### 场景 3：数据清洗
```
用户: "帮我更新一下最新的数据"

Claude:
1. [调用 Tool] clean_ministry_data(dry_run=false, force=false)
2. [调用 Tool] generate_service_layer(generate_all_years=true)

输出:
✅ 数据清洗完成
- 检测到数据变化：新增3条记录
- 成功清洗131条记录
- 无错误
✅ 服务层生成完成
- 生成sermon和volunteer域
- 覆盖2024-2026年份
```

---

### 场景 4：质量检查
```
用户: "检查一下原始数据有没有问题"

Claude:
1. [调用 Tool] validate_raw_data(check_duplicates=true, generate_report=true)

输出:
⚠️ 发现3个问题：
1. 行15：日期格式错误（"2024/10/32"不是有效日期）
2. 行28：重复记录（2024-10-07 morning已存在）
3. 行42：讲员字段为空

建议：修复后重新运行清洗
```

---

### 场景 5：别名管理
```
用户: "发现'华亚西'和'亚西'是同一个人，帮我合并"

Claude:
1. [调用 Resource] ministry://config/aliases 查找现有映射
2. [调用 Tool] merge_person_aliases(
     source_person_id="person_yaxi",
     target_person_id="person_huayaxi",
     keep_display_name="target"
   )

输出:
✅ 别名合并完成
- 将"亚西"的所有别名合并到"person_huayaxi"
- 更新了13条历史记录
- 建议重新生成服务层数据
```

---

## 📐 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         AI 助手层                            │
│  (Claude Desktop / ChatGPT / Custom AI)                     │
└────────────────┬────────────────────────────────────────────┘
                 │ MCP 协议 (stdio / HTTP/SSE)
┌────────────────▼────────────────────────────────────────────┐
│                      MCP 服务器                              │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │   Tools      │  Resources   │      Prompts         │    │
│  │  (执行操作)   │  (数据访问)   │   (对话模板)          │    │
│  └──────┬───────┴──────┬───────┴───────┬──────────────┘    │
│         │              │               │                    │
│         │              │               │                    │
└─────────┼──────────────┼───────────────┼────────────────────┘
          │              │               │
┌─────────▼──────────────▼───────────────▼────────────────────┐
│                      FastAPI 应用层                          │
│  /api/v1/clean                                              │
│  /api/v1/sermon                                             │
│  /api/v1/volunteer                                          │
│  /api/v1/service-layer/generate                            │
│  /api/v1/stats                                             │
│  /api/v1/config/aliases                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                      服务层管理器                            │
│  ServiceLayerManager                                        │
│  ├── SermonDomainTransformer (证道域)                       │
│  └── VolunteerDomainTransformer (同工域)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                      清洗管线层                              │
│  CleaningPipeline                                           │
│  ├── CleaningRules (清洗规则)                               │
│  ├── Validators (数据校验)                                  │
│  ├── AliasUtils (别名映射)                                  │
│  └── ChangeDetector (变化检测)                              │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                      数据存储层                              │
│  ┌─────────────┬──────────────┬───────────────────────┐    │
│  │ Google      │  Cloud       │  Local Files          │    │
│  │ Sheets      │  Storage     │  (logs/, cache/)      │    │
│  │ (原始层)     │  (服务层)     │                        │    │
│  └─────────────┴──────────────┴───────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 对比表：Tools vs Resources

| 维度 | Tools（工具） | Resources（资源） |
|------|--------------|------------------|
| **目的** | 执行操作、改变状态 | 提供只读数据访问 |
| **HTTP方法** | 主要是 POST/PUT/DELETE | 主要是 GET |
| **幂等性** | 不一定（如清洗数据会改变状态） | 幂等（多次读取结果相同） |
| **缓存** | 不应缓存 | 可以缓存 |
| **用户意图** | "做某事" | "查某事" |
| **本项目示例** | clean_ministry_data, generate_service_layer | sermon-records, volunteer-assignments |

---

## ✅ 实施检查清单

### 阶段 1：基础设施（1-2天）
- [x] 补充缺失的 API 端点
- [x] 实现别名管理功能
- [x] 实现数据验证接口
- [x] 实现管线状态查询
- [ ] 编写单元测试

### 阶段 2：MCP 服务器（2-3天）
- [x] 安装 MCP SDK: `pip install mcp`
- [x] 创建 `mcp_server.py`
- [x] 实现 Tools 注册和调用
- [x] 实现 Resources 注册和读取
- [x] 实现 Prompts 定义和渲染
- [x] 测试 stdio 传输
- [x] 实现 HTTP/SSE 传输层
- [x] 实现 Bearer Token 鉴权

### 阶段 3：集成测试（1天）
- [x] 配置 Claude Desktop 示例
- [x] 创建测试脚本
- [ ] 测试所有 Tools
- [ ] 测试所有 Resources
- [ ] 测试所有 Prompts
- [ ] 性能和安全测试

### 阶段 4：文档和部署（1天）
- [x] 更新 Dockerfile
- [x] 编写 MCP 部署文档
- [x] 创建部署脚本
- [x] 创建快速开始指南
- [x] 创建客户端示例代码
- [ ] 部署到 Cloud Run 并验证
- [ ] 记录生产环境配置

## 📦 已交付文件清单

### 核心实现
- ✅ `mcp_server.py` - MCP Server 核心实现（stdio 模式）
- ✅ `mcp_http_server.py` - HTTP/SSE 传输层实现
- ✅ `requirements.txt` - 更新依赖（MCP SDK）
- ✅ `Dockerfile` - 支持 MCP 模式的容器配置

### 部署工具
- ✅ `deploy-mcp-cloud-run.sh` - Cloud Run 一键部署脚本
- ✅ `test_mcp_server.sh` - 本地测试脚本
- ✅ `.env.example` - 环境变量配置示例

### 配置文件
- ✅ `config/claude_desktop_config.example.json` - Claude Desktop 配置示例

### 文档
- ✅ `docs/MCP_DEPLOYMENT.md` - 完整部署指南
- ✅ `QUICKSTART_MCP.md` - 5分钟快速开始
- ✅ `docs/MCP_DESIGN.md` - 架构设计文档（本文件）

### 示例代码
- ✅ `examples/mcp_client_example.py` - Python 客户端示例

---

## 🎓 最佳实践

### 1. Tool 设计
- ✅ 命名使用动词（如 `clean_`, `generate_`, `validate_`）
- ✅ 提供 `dry_run` 选项用于预览
- ✅ 返回详细的执行报告
- ✅ 处理错误并返回友好信息

### 2. Resource 设计
- ✅ URI 使用名词（如 `/sermon/records`）
- ✅ 支持过滤和分页
- ✅ 返回结构化的 JSON
- ✅ 包含元数据（如 total_count）

### 3. Prompt 设计
- ✅ 明确分析目标
- ✅ 指定使用哪些 Resources
- ✅ 提供具体的输出格式要求
- ✅ 考虑多步骤的分析流程

### 4. 安全性
- ✅ 敏感 Tools 需要认证（如 `trigger_scheduled_update`）
- ✅ 限制 Resource 的访问频率
- ✅ 不在 Prompt 中暴露敏感信息
- ✅ 记录所有 Tool 调用日志

---

## 📚 参考资料

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP 集成](https://docs.anthropic.com/claude/docs/mcp)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

---

## 📞 支持

如有问题或建议，请联系项目维护者。


