# 同工元数据需求分析

## 📋 需求描述

通过 MCP 实现以下功能：
1. **分析下周同工安排**：查看下周有哪些人服侍
2. **同工关系管理**：记录谁和谁是一家，避免同一周服侍
3. **可用性管理**：记录同工在什么时间段不在
4. **冲突检测**：自动检测排班冲突

---

## 🔍 当前 API 能力分析

### ✅ 已支持的功能

| 功能 | API 端点 | 说明 |
|------|----------|------|
| 查询特定日期同工 | `GET /api/v1/volunteer?service_date=2024-10-14` | 可以查询任意日期 |
| 查询某人服侍记录 | `GET /api/v1/volunteer/by-person/{id}` | 查看个人历史 |
| 查询月度空缺 | `GET /api/v1/volunteer/availability/{month}` | 查看哪些岗位空缺 |
| 同工服侍统计 | `GET /api/v1/stats/volunteers` | 服侍频率统计 |

### ❌ 缺失的功能

| 功能 | 当前状态 | 需要实现 |
|------|---------|---------|
| 同工元数据存储 | ❌ 不存在 | ✅ 需要新增 |
| 家庭关系管理 | ❌ 不存在 | ✅ 需要新增 |
| 不可用时间段 | ❌ 不存在 | ✅ 需要新增 |
| 冲突检测 | ❌ 不存在 | ✅ 需要新增 |
| "下周"智能查询 | ❌ 需要计算 | ✅ 需要新增 |

---

## 💡 解决方案设计

### 方案 1：Google Sheets 存储（推荐）✨

**优势**：
- ✅ 与 alias 表结构一致
- ✅ 便于非技术人员维护
- ✅ 版本历史和协作编辑
- ✅ 无需额外数据库

**数据表设计**：

#### Sheet: `VolunteerMetadata`

| 列名 | 类型 | 示例 | 说明 |
|------|------|------|------|
| person_id | string | person_8101_谢苗 | 人员唯一标识 |
| person_name | string | 谢苗 | 显示名称 |
| family_group | string | family_xie_qu | 家庭组ID（同组不能同周服侍）|
| unavailable_start | date | 2024-11-01 | 不可用开始日期 |
| unavailable_end | date | 2024-11-15 | 不可用结束日期 |
| unavailable_reason | string | 旅行 | 不可用原因 |
| notes | string | 优先安排早场 | 其他备注 |
| updated_at | datetime | 2024-10-07 | 更新时间 |

**示例数据**：

```csv
person_id,person_name,family_group,unavailable_start,unavailable_end,unavailable_reason,notes,updated_at
person_8101_谢苗,谢苗,family_xie_qu,2024-11-01,2024-11-15,旅行,优先安排早场,2024-10-07
person_9017_屈小煊,屈小煊,family_xie_qu,,,夫妻关系,晚场优先,2024-10-07
person_3850_靖铮,靖铮,,,2024-12-20,2024-12-31,回国探亲,,2024-10-07
person_6878_杜德双,杜德双,family_du,,,,优先技术岗,2024-10-07
```

**配置文件**（`config/config.json`）：

```json
{
  "volunteer_metadata_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
    "range": "VolunteerMetadata!A1:H"
  }
}
```

---

### 方案 2：JSON 文件存储

**适用场景**：不想使用 Google Sheets

**文件位置**：`config/volunteer_metadata.json`

```json
{
  "metadata_version": "1.0",
  "last_updated": "2024-10-07T12:00:00Z",
  "volunteers": [
    {
      "person_id": "person_8101_谢苗",
      "person_name": "谢苗",
      "family_group": "family_xie_qu",
      "family_members": ["person_9017_屈小煊"],
      "unavailable_periods": [
        {
          "start": "2024-11-01",
          "end": "2024-11-15",
          "reason": "旅行"
        }
      ],
      "notes": "优先安排早场"
    }
  ],
  "family_groups": [
    {
      "group_id": "family_xie_qu",
      "group_name": "谢苗-屈小煊家庭",
      "members": ["person_8101_谢苗", "person_9017_屈小煊"],
      "constraint": "不能在同一周服侍"
    }
  ]
}
```

---

## 🛠️ 需要新增的 API 端点

### 1. 同工元数据管理

#### 获取同工元数据
```
GET /api/v1/volunteer/metadata
GET /api/v1/volunteer/metadata/{person_id}
```

**返回示例**：
```json
{
  "success": true,
  "metadata": [
    {
      "person_id": "person_8101_谢苗",
      "person_name": "谢苗",
      "family_group": "family_xie_qu",
      "family_members": ["person_9017_屈小煊"],
      "unavailable_periods": [
        {
          "start": "2024-11-01",
          "end": "2024-11-15",
          "reason": "旅行"
        }
      ],
      "notes": "优先安排早场",
      "is_available": true
    }
  ]
}
```

#### 添加/更新元数据
```
POST /api/v1/volunteer/metadata
PUT /api/v1/volunteer/metadata/{person_id}
```

**请求体**：
```json
{
  "person_id": "person_8101_谢苗",
  "family_group": "family_xie_qu",
  "unavailable_start": "2024-11-01",
  "unavailable_end": "2024-11-15",
  "unavailable_reason": "旅行",
  "notes": "优先安排早场"
}
```

---

### 2. 下周同工分析

#### 获取下周同工安排
```
GET /api/v1/volunteer/next-week
GET /api/v1/volunteer/week/{date}
```

**参数**：
- `date` (可选): 指定周日日期，默认为下个周日

**返回示例**：
```json
{
  "success": true,
  "week_info": {
    "week_start": "2024-10-13",
    "week_end": "2024-10-19",
    "sunday_date": "2024-10-13",
    "is_next_week": true
  },
  "services": [
    {
      "service_date": "2024-10-13",
      "service_slot": "morning",
      "volunteers": [
        {
          "person_id": "person_8101_谢苗",
          "person_name": "谢苗",
          "role": "敬拜主领",
          "is_available": true,
          "metadata": {
            "family_group": "family_xie_qu",
            "notes": "优先安排早场"
          }
        }
      ]
    }
  ],
  "summary": {
    "total_volunteers": 15,
    "unique_volunteers": 12,
    "unavailable_count": 2,
    "family_conflicts": 0
  }
}
```

---

### 3. 冲突检测

#### 检测排班冲突
```
POST /api/v1/volunteer/conflicts
GET /api/v1/volunteer/conflicts/{year_month}
```

**功能**：
- 检测家庭成员在同一周服侍
- 检测不可用时间段冲突
- 检测过度服侍

**返回示例**：
```json
{
  "success": true,
  "conflicts": [
    {
      "type": "family_conflict",
      "severity": "warning",
      "week": "2024-10-13",
      "description": "谢苗 和 屈小煊 是家庭成员，在同一周服侍",
      "affected_persons": [
        {
          "person_id": "person_8101_谢苗",
          "person_name": "谢苗",
          "service_date": "2024-10-13",
          "role": "敬拜主领"
        },
        {
          "person_id": "person_9017_屈小煊",
          "person_name": "屈小煊",
          "service_date": "2024-10-13",
          "role": "敬拜同工"
        }
      ],
      "family_group": "family_xie_qu",
      "suggestion": "建议将其中一人调整到其他周"
    },
    {
      "type": "unavailability_conflict",
      "severity": "error",
      "week": "2024-11-03",
      "description": "谢苗 在 2024-11-01 到 2024-11-15 期间不可用，但被安排服侍",
      "affected_persons": [
        {
          "person_id": "person_8101_谢苗",
          "person_name": "谢苗",
          "service_date": "2024-11-03",
          "role": "敬拜主领",
          "unavailable_reason": "旅行"
        }
      ],
      "suggestion": "需要重新安排其他人"
    }
  ],
  "summary": {
    "total_conflicts": 2,
    "by_severity": {
      "error": 1,
      "warning": 1
    },
    "by_type": {
      "family_conflict": 1,
      "unavailability_conflict": 1
    }
  }
}
```

---

### 4. 智能排班建议

#### 获取排班建议
```
POST /api/v1/volunteer/suggestions
```

**请求体**：
```json
{
  "service_date": "2024-10-20",
  "required_roles": ["敬拜主领", "音控", "视频"],
  "consider_availability": true,
  "consider_family": true,
  "consider_balance": true
}
```

**返回示例**：
```json
{
  "success": true,
  "suggestions": [
    {
      "role": "敬拜主领",
      "candidates": [
        {
          "person_id": "person_8101_谢苗",
          "person_name": "谢苗",
          "score": 95,
          "reasons": [
            "近期服侍次数适中（2次/月）",
            "时间可用",
            "无家庭成员冲突",
            "优先安排早场（符合备注）"
          ],
          "concerns": []
        },
        {
          "person_id": "person_huayaxi",
          "person_name": "华亚西",
          "score": 85,
          "reasons": [
            "服侍次数较少（1次/月）",
            "时间可用"
          ],
          "concerns": [
            "近期刚服侍过（10-06）"
          ]
        }
      ]
    }
  ]
}
```

---

## 🔄 MCP Prompt 设计

### Prompt 1: `analyze_next_week_volunteers`

```typescript
{
  name: "analyze_next_week_volunteers",
  description: "分析下周同工安排，检测冲突并提供建议",
  arguments: [],
  prompt: `请分析下周（即将到来的周日）的同工安排：

步骤：
1. 使用 ministry://volunteer/next-week 获取下周安排
2. 使用 ministry://volunteer/conflicts 检测排班冲突
3. 使用 ministry://volunteer/metadata 获取同工备注信息

分析内容：
- 列出所有服侍的同工及其岗位
- 标记不可用的同工（如果有被安排）
- 识别家庭成员冲突（如果有）
- 统计服侍频率是否均衡
- 识别空缺岗位

输出格式：
1. 下周同工名单（按岗位分组）
2. 冲突警告（如有）
3. 备注信息（特殊要求）
4. 建议改进（如有）
`
}
```

### Prompt 2: `suggest_volunteer_schedule`

```typescript
{
  name: "suggest_volunteer_schedule",
  description: "为指定日期提供智能排班建议",
  arguments: [
    {
      name: "service_date",
      description: "主日日期 (YYYY-MM-DD)",
      required: true
    }
  ],
  prompt: `请为 {{service_date}} 提供智能排班建议：

步骤：
1. 使用 ministry://volunteer/suggestions 获取推荐候选人
2. 使用 ministry://volunteer/metadata 查看同工备注
3. 使用 ministry://stats/volunteers 查看服侍均衡度

考虑因素：
- ✅ 时间可用性（避开不可用时间段）
- ✅ 家庭关系（同一家庭不在同周）
- ✅ 服侍均衡（避免过度服侍）
- ✅ 特殊备注（优先安排、岗位偏好等）

输出格式：
为每个岗位推荐2-3位候选人，并说明推荐理由。
`
}
```

---

## 📝 实施步骤

### 第一步：创建 Google Sheets 数据表

1. **打开你的 Google Sheets**（与 alias 表在同一个 Spreadsheet）

2. **创建新 Sheet**：`VolunteerMetadata`

3. **添加表头**：
   ```
   person_id | person_name | family_group | unavailable_start | unavailable_end | unavailable_reason | notes | updated_at
   ```

4. **添加示例数据**：
   ```
   person_8101_谢苗 | 谢苗 | family_xie_qu | 2024-11-01 | 2024-11-15 | 旅行 | 优先安排早场 | 2024-10-07
   person_9017_屈小煊 | 屈小煊 | family_xie_qu | | | | 夫妻关系 | 2024-10-07
   ```

5. **共享给服务账号**：与 alias 表相同的服务账号

---

### 第二步：更新配置文件

**`config/config.json`**：

```json
{
  "alias_sources": {
    "people_alias_sheet": {
      "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
      "range": "PeopleAliases!A1:C"
    }
  },
  "volunteer_metadata_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
    "range": "VolunteerMetadata!A1:H"
  }
}
```

---

### 第三步：实现新 API 端点

需要在 `app.py` 中添加：

1. **Pydantic 模型**：
   - `VolunteerMetadataModel`
   - `ConflictCheckRequest`
   - `SuggestionRequest`

2. **API 端点**（5个新端点）：
   - `GET /api/v1/volunteer/metadata`
   - `POST /api/v1/volunteer/metadata`
   - `GET /api/v1/volunteer/next-week`
   - `POST /api/v1/volunteer/conflicts`
   - `POST /api/v1/volunteer/suggestions`

3. **工具函数**：
   - `get_next_sunday()` - 计算下个周日
   - `check_family_conflicts()` - 检测家庭冲突
   - `check_availability_conflicts()` - 检测可用性冲突
   - `calculate_volunteer_score()` - 计算推荐分数

---

### 第四步：测试

```bash
# 获取元数据
curl "http://localhost:8080/api/v1/volunteer/metadata"

# 查看下周安排
curl "http://localhost:8080/api/v1/volunteer/next-week"

# 检测冲突
curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
  -H "Content-Type: application/json" \
  -d '{"year_month":"2024-10"}'

# 获取排班建议
curl -X POST http://localhost:8080/api/v1/volunteer/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "service_date":"2024-10-20",
    "required_roles":["敬拜主领","音控"]
  }'
```

---

## 🎯 MCP 使用场景

### 场景 1：查看下周安排

**用户提问**：
> "下周都有谁服侍？"

**Claude 调用**：
```javascript
// 1. 获取下周安排
ministry://volunteer/next-week

// 2. 获取元数据
ministry://volunteer/metadata

// 3. 检测冲突
volunteer/conflicts
```

**Claude 回复**：
```
下周（2024-10-13）同工安排：

敬拜组：
- 主领：谢苗 ✅
- 同工：屈小煊 ✅
- 司琴：华亚西 ✅

技术组：
- 音控：靖铮 ⚠️ 
- 视频：俊鑫 ✅
- PPT播放：康康 ✅

⚠️ 发现 1 个冲突：
- 谢苗 和 屈小煊 是家庭成员，在同一周服侍

备注：
- 谢苗：优先安排早场 ✓
- 靖铮：即将在 11月 不可用（回国探亲）

建议：
- 考虑将屈小煊调整到下下周
- 提前安排 11月 音控人员
```

---

### 场景 2：排班前检查

**用户提问**：
> "10月20日想安排谢苗做主领，有没有问题？"

**Claude 调用**：
```javascript
// 1. 检查元数据
ministry://volunteer/metadata/person_8101_谢苗

// 2. 检查该周安排
ministry://volunteer/week/2024-10-20

// 3. 检查冲突
volunteer/conflicts
```

**Claude 回复**：
```
✅ 谢苗在 10月20日 可以服侍

检查结果：
- ✅ 时间可用（无不可用时间段）
- ✅ 无家庭成员冲突（屈小煊未在该周安排）
- ✅ 服侍频率合理（10月已服侍1次，本月第2次）
- ✅ 符合备注（早场服侍）

可以放心安排！
```

---

### 场景 3：智能排班

**用户提问**：
> "11月3日还需要安排音控和视频，帮我推荐几个人"

**Claude 调用**：
```javascript
// 1. 获取建议
volunteer/suggestions {
  service_date: "2024-11-03",
  required_roles: ["音控", "视频"]
}

// 2. 检查元数据
ministry://volunteer/metadata
```

**Claude 回复**：
```
11月3日 音控和视频推荐：

音控：
1. 🌟 张三（推荐度：95%）
   - ✅ 时间可用
   - ✅ 近期服侍次数适中（2次/月）
   - ✅ 无冲突
   
2. ⭐ 李四（推荐度：80%）
   - ✅ 时间可用
   - ⚠️ 上周刚服侍过
   
❌ 靖铮（不推荐）
   - ❌ 11月1-15日 不可用（回国探亲）

视频：
1. 🌟 俊鑫（推荐度：90%）
   - ✅ 时间可用
   - ✅ 服侍次数较少
   
2. ⭐ 周晨（推荐度：85%）
   - ✅ 时间可用
   - ⚠️ 本月已服侍2次

建议优先选择：张三（音控）+ 俊鑫（视频）
```

---

## ✅ 总结

### 当前 API 能满足的需求
- ✅ 查询特定日期的同工安排
- ✅ 查询个人服侍历史
- ✅ 统计服侍频率

### 需要补充的功能
- ❌ 同工元数据管理（家庭关系、可用性）
- ❌ 下周智能查询
- ❌ 冲突检测
- ❌ 排班建议

### 推荐方案
- ✅ **使用 Google Sheets 存储备注**（与 alias 表一致）
- ✅ **新增 5 个 API 端点**
- ✅ **新增 2 个 MCP Prompts**

### 预计工作量
- **数据表创建**：10分钟
- **API 实现**：4-6小时
- **测试验证**：1-2小时
- **总计**：约 1 天

---

## 📞 下一步

是否要我开始实施这些功能？我可以：

1. ✅ 更新 `config/config.json`
2. ✅ 实现 5 个新 API 端点
3. ✅ 创建测试脚本
4. ✅ 更新 MCP_DESIGN.md
5. ✅ 提供 Google Sheets 模板

请确认是否开始实施！

