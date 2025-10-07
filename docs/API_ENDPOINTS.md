# API 端点完整列表

## 📋 目录

- [概述](#概述)
- [已有端点](#已有端点)
- [新增端点（阶段1）](#新增端点阶段1)
  - [Sermon 高级查询](#-1-sermon-高级查询)
  - [Volunteer 高级查询](#-2-volunteer-高级查询)
  - [统计分析](#-3-统计分析)
  - [别名管理](#-4-别名管理)
  - [数据验证和管线状态](#-5-数据验证和管线状态)
  - [同工元数据和智能排班](#-6-同工元数据和智能排班)
- [快速测试](#快速测试)
- [MCP 端点映射](#mcp-端点映射)
- [总结](#总结)

---

## 概述

本文档列出所有可用的 API 端点，包括原有端点和新增的 MCP 相关端点。

**Base URL**: `https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app`  
（本地开发: `http://localhost:8080`）

---

## 已有端点

### 基础端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 根端点 - 健康检查 |
| `/health` | GET | 健康检查端点 |
| `/docs` | GET | Swagger API 文档 |
| `/redoc` | GET | ReDoc API 文档 |

### 数据清洗

| 端点 | 方法 | 描述 | MCP 类型 |
|------|------|------|----------|
| `/api/v1/clean` | POST | 手动触发数据清洗 | Tool |
| `/trigger-cleaning` | POST | 定时任务触发端点（需认证） | Tool |

**请求示例**:
```bash
curl -X POST http://localhost:8080/api/v1/clean \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "force": false}'
```

### 数据查询

| 端点 | 方法 | 描述 | MCP 类型 |
|------|------|------|----------|
| `/api/v1/preview` | GET | 获取清洗预览数据 | Resource |
| `/api/v1/query` | POST | 查询清洗后的数据 | Resource |
| `/api/v1/stats` | GET | 获取统计信息 | Resource |

**请求示例**:
```bash
# 查询数据
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"date_from":"2024-01-01","limit":10}'

# 获取统计
curl http://localhost:8080/api/v1/stats
```

### 服务层

| 端点 | 方法 | 描述 | MCP 类型 |
|------|------|------|----------|
| `/api/v1/service-layer/generate` | POST | 生成服务层数据 | Tool |
| `/api/v1/sermon` | GET | 获取证道域数据 | Resource |
| `/api/v1/volunteer` | GET | 获取同工域数据 | Resource |

**请求示例**:
```bash
# 生成服务层
curl -X POST http://localhost:8080/api/v1/service-layer/generate \
  -H "Content-Type: application/json" \
  -d '{"generate_all_years":true,"upload_to_bucket":false}'

# 获取证道数据
curl "http://localhost:8080/api/v1/sermon?year=2024&limit=10"

# 获取同工数据
curl "http://localhost:8080/api/v1/volunteer?year=2024&limit=10"
```

---

## 新增端点（阶段1）

### 🆕 1. Sermon 高级查询

#### 按讲员查询证道
```
GET /api/v1/sermon/by-preacher/{preacher_name}
```

**参数**:
- `preacher_name` (路径参数): 讲员名称（支持部分匹配）
- `year` (查询参数，可选): 年份筛选
- `limit` (查询参数，默认100): 返回记录数上限
- `offset` (查询参数，默认0): 偏移量

**示例**:
```bash
curl "http://localhost:8080/api/v1/sermon/by-preacher/王通?year=2024&limit=5"
```

**响应**:
```json
{
  "metadata": {
    "domain": "sermon",
    "version": "1.0",
    "preacher_name": "王通",
    "total_count": 15,
    "returned_count": 5
  },
  "sermons": [...]
}
```

---

#### 获取讲道系列
```
GET /api/v1/sermon/series
```

**参数**:
- `year` (查询参数，可选): 年份筛选

**示例**:
```bash
curl "http://localhost:8080/api/v1/sermon/series?year=2024"
```

**响应**:
```json
{
  "metadata": {
    "domain": "sermon",
    "total_series": 5,
    "year": 2024
  },
  "series": [
    {
      "series_name": "遇见耶稣",
      "sermon_count": 12,
      "date_range": {
        "start": "2024-01-07",
        "end": "2024-03-31"
      },
      "preachers": ["王通", "李牧师"],
      "sermons": [...]
    }
  ]
}
```

---

### 🆕 2. Volunteer 高级查询

#### 按人员查询服侍记录
```
GET /api/v1/volunteer/by-person/{person_identifier}
```

**参数**:
- `person_identifier` (路径参数): 人员ID或姓名
- `year` (查询参数，可选): 年份筛选
- `limit` (查询参数，默认100): 返回记录数上限
- `offset` (查询参数，默认0): 偏移量

**示例**:
```bash
curl "http://localhost:8080/api/v1/volunteer/by-person/谢苗?year=2024&limit=5"
```

**响应**:
```json
{
  "metadata": {
    "domain": "volunteer",
    "person_identifier": "谢苗",
    "total_count": 8,
    "role_statistics": {
      "敬拜主领": 5,
      "敬拜同工": 3
    }
  },
  "records": [
    {
      "service_date": "2024-01-07",
      "roles": ["敬拜主领"],
      "full_record": {...}
    }
  ]
}
```

---

#### 查询排班空缺
```
GET /api/v1/volunteer/availability/{year_month}
```

**参数**:
- `year_month` (路径参数): 年月，格式 YYYY-MM

**示例**:
```bash
curl "http://localhost:8080/api/v1/volunteer/availability/2024-10"
```

**响应**:
```json
{
  "metadata": {
    "year_month": "2024-10",
    "total_services": 5,
    "services_with_gaps": 2,
    "total_gaps": 4
  },
  "summary": {
    "gap_by_position": {
      "ProPresenter更新": 2,
      "司琴": 1,
      "音控": 1
    }
  },
  "availability": [
    {
      "service_date": "2024-10-06",
      "vacant_positions": ["ProPresenter更新", "司琴"],
      "urgency": "medium"
    }
  ]
}
```

---

### 🆕 3. 统计分析

#### 讲员统计
```
GET /api/v1/stats/preachers
```

**参数**:
- `year` (查询参数，可选): 年份筛选

**示例**:
```bash
curl "http://localhost:8080/api/v1/stats/preachers?year=2024"
```

**响应**:
```json
{
  "metadata": {
    "domain": "sermon",
    "year": 2024,
    "total_preachers": 12,
    "total_sermons": 52
  },
  "preachers": [
    {
      "preacher_id": "person_6511_王通",
      "preacher_name": "王通",
      "sermon_count": 15,
      "series": ["遇见耶稣", "以弗所书系列"],
      "scriptures": ["创世纪 3", "以弗所书 1:1-14", ...],
      "date_range": {
        "first": "2024-01-07",
        "last": "2024-12-29"
      }
    }
  ]
}
```

---

#### 同工统计
```
GET /api/v1/stats/volunteers
```

**参数**:
- `year` (查询参数，可选): 年份筛选

**示例**:
```bash
curl "http://localhost:8080/api/v1/stats/volunteers?year=2024"
```

**响应**:
```json
{
  "metadata": {
    "domain": "volunteer",
    "year": 2024,
    "total_volunteers": 45,
    "total_services": 52
  },
  "volunteers": [
    {
      "person_id": "person_8101_谢苗",
      "person_name": "谢苗",
      "total_services": 18,
      "unique_dates": 15,
      "roles": {
        "敬拜主领": 8,
        "敬拜同工": 10
      },
      "date_range": {
        "first": "2024-01-07",
        "last": "2024-12-29"
      }
    }
  ]
}
```

---

### 🆕 4. 别名管理

#### 获取别名映射
```
GET /api/v1/config/aliases
```

**示例**:
```bash
curl "http://localhost:8080/api/v1/config/aliases"
```

**响应**:
```json
{
  "success": true,
  "metadata": {
    "total_count": 150,
    "source": "Google Sheets"
  },
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

#### 添加别名
```
POST /api/v1/config/aliases
```

**请求体**:
```json
{
  "alias": "华亚西",
  "person_id": "person_huayaxi",
  "display_name": "华亚西"
}
```

**示例**:
```bash
curl -X POST http://localhost:8080/api/v1/config/aliases \
  -H "Content-Type: application/json" \
  -d '{"alias":"华亚西","person_id":"person_huayaxi","display_name":"华亚西"}'
```

**响应**:
```json
{
  "success": true,
  "message": "成功添加别名 '华亚西'",
  "alias": {
    "alias": "华亚西",
    "person_id": "person_huayaxi",
    "display_name": "华亚西"
  },
  "timestamp": "2025-10-07T12:00:00Z"
}
```

---

#### 合并别名
```
POST /api/v1/config/aliases/merge
```

**请求体**:
```json
{
  "source_person_id": "person_yaxi",
  "target_person_id": "person_huayaxi",
  "keep_display_name": "target"
}
```

**示例**:
```bash
curl -X POST http://localhost:8080/api/v1/config/aliases/merge \
  -H "Content-Type: application/json" \
  -d '{
    "source_person_id":"person_yaxi",
    "target_person_id":"person_huayaxi",
    "keep_display_name":"target"
  }'
```

**响应**:
```json
{
  "success": true,
  "message": "成功合并 3 个别名",
  "details": {
    "source_person_id": "person_yaxi",
    "target_person_id": "person_huayaxi",
    "merged_aliases": ["亚西", "Yaxi", "YaXi"],
    "display_name": "华亚西"
  },
  "timestamp": "2025-10-07T12:00:00Z"
}
```

---

### 🆕 5. 数据验证和管线状态

#### 数据验证
```
POST /api/v1/validate
```

**请求体**:
```json
{
  "check_duplicates": true,
  "generate_report": true
}
```

**示例**:
```bash
curl -X POST http://localhost:8080/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"check_duplicates":true,"generate_report":false}'
```

**响应**:
```json
{
  "success": true,
  "message": "数据验证完成",
  "summary": {
    "total_rows": 131,
    "success_rows": 131,
    "warning_rows": 0,
    "error_rows": 0,
    "duplicate_records": 0,
    "issues_by_severity": {
      "error": 0,
      "warning": 0
    }
  },
  "duplicates": [],
  "issues_by_field": {},
  "report_file": "logs/validation_report_20251007_120000.txt",
  "timestamp": "2025-10-07T12:00:00Z"
}
```

---

#### 管线状态
```
GET /api/v1/pipeline/status
```

**参数**:
- `last_n_runs` (查询参数，默认10): 返回最近N次运行记录

**示例**:
```bash
curl "http://localhost:8080/api/v1/pipeline/status?last_n_runs=5"
```

**响应**:
```json
{
  "success": true,
  "pipeline_status": {
    "last_run": "2025-10-07T05:23:51.813176Z",
    "last_row_count": 131,
    "last_hash": "a7f5d8c3e9b1f2d4...",
    "is_healthy": true
  },
  "service_layer": {
    "sermon": {
      "exists": true,
      "record_count": 131,
      "last_modified": "2025-10-07T05:23:51",
      "file_size": 234567
    },
    "volunteer": {
      "exists": true,
      "record_count": 131,
      "last_modified": "2025-10-07T05:23:51",
      "file_size": 345678
    }
  },
  "recent_runs": [
    {
      "timestamp": "20251007_052351",
      "file": "logs/validation_report_20251007_052351.txt",
      "stats": {
        "total_rows": 131,
        "success_rows": 131,
        "warning_rows": 0,
        "error_rows": 0
      },
      "preview": "..."
    }
  ],
  "timestamp": "2025-10-07T12:00:00Z"
}
```

---

### 🆕 6. 同工元数据和智能排班

#### 获取同工元数据
```
GET /api/v1/volunteer/metadata
```

**参数**:
- `person_id` (查询参数，可选): 人员ID，用于查询特定同工

**示例**:
```bash
# 获取所有同工元数据
curl "http://localhost:8080/api/v1/volunteer/metadata"

# 查询特定同工
curl --get --data-urlencode "person_id=person_8101_谢苗" \
  "http://localhost:8080/api/v1/volunteer/metadata"
```

**响应**:
```json
{
  "success": true,
  "metadata": {
    "total_count": 79,
    "available_count": 77,
    "unavailable_count": 2,
    "family_groups": {
      "family_bai_lv": ["person_2165_吕晓燕", "person_7613_白彧"],
      "family_jing_ming": ["person_3850_靖铮", "person_6745_明明"]
    },
    "source": "Google Sheets"
  },
  "volunteers": [
    {
      "person_id": "person_8101_谢苗",
      "person_name": "谢苗",
      "family_group": "family_xie_qu",
      "unavailable_start": "2025-11-01",
      "unavailable_end": "2025-11-15",
      "unavailable_reason": "旅行",
      "notes": "",
      "updated_at": "2025-10-07",
      "is_available": false
    }
  ]
}
```

---

#### 添加/更新同工元数据
```
POST /api/v1/volunteer/metadata
```

**请求体**:
```json
{
  "person_id": "person_8101_谢苗",
  "person_name": "谢苗",
  "family_group": "family_xie_qu",
  "unavailable_start": "2025-11-01",
  "unavailable_end": "2025-11-15",
  "unavailable_reason": "旅行",
  "notes": "提前通知"
}
```

**示例**:
```bash
curl -X POST http://localhost:8080/api/v1/volunteer/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "person_8101_谢苗",
    "person_name": "谢苗",
    "unavailable_start": "2025-11-01",
    "unavailable_end": "2025-11-15",
    "unavailable_reason": "旅行"
  }'
```

**响应**:
```json
{
  "success": true,
  "message": "成功更新同工元数据: 谢苗",
  "metadata": {
    "person_id": "person_8101_谢苗",
    "person_name": "谢苗",
    "unavailable_start": "2025-11-01",
    "unavailable_end": "2025-11-15",
    "unavailable_reason": "旅行"
  },
  "timestamp": "2025-10-07T12:00:00Z"
}
```

**不可用标注说明**:
- **临时不可用**: 填写实际的开始和结束日期
  - 示例：`unavailable_start: "2025-11-01"`, `unavailable_end: "2025-11-15"`
  - 适用：短期旅行、出差、培训等
- **长期不可用**: 使用 `2099-12-31` 作为结束日期，表示无限期不可用
  - 示例：`unavailable_start: "2025-10-01"`, `unavailable_end: "2099-12-31"`
  - 适用：长期生病、工作繁忙、暂停服侍、退出团队等
  - 建议在 `notes` 字段添加详细说明

**相关文档**: `docs/UNAVAILABILITY_GUIDE.md`

---

#### 获取下周服侍安排
```
GET /api/v1/volunteer/next-week
```

自动计算下一个周日，返回该周的所有服侍安排（包括元数据和可用性状态）。

**示例**:
```bash
curl "http://localhost:8080/api/v1/volunteer/next-week"
```

**响应**:
```json
{
  "success": true,
  "next_week": {
    "sunday_date": "2025-10-13",
    "week_range": "2025-10-07 到 2025-10-13",
    "assignments_count": 2
  },
  "assignments": [
    {
      "service_date": "2025-10-13",
      "worship": {
        "lead": {
          "id": "person_8101_谢苗",
          "name": "谢苗",
          "metadata": {
            "is_available": true,
            "family_group": "family_xie_qu"
          }
        }
      },
      "technical": {...}
    }
  ],
  "timestamp": "2025-10-07T12:00:00Z"
}
```

---

#### 检测排班冲突
```
POST /api/v1/volunteer/conflicts
```

检测家庭成员冲突、不可用时间冲突等排班问题。

**请求体**:
```json
{
  "year_month": "2025-11",
  "check_family": true,
  "check_availability": true,
  "check_overload": false
}
```

**示例**:
```bash
curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
  -H "Content-Type: application/json" \
  -d '{
    "year_month": "2025-11",
    "check_family": true,
    "check_availability": true
  }'
```

**响应**:
```json
{
  "success": true,
  "conflicts": [
    {
      "type": "family_conflict",
      "severity": "warning",
      "week": "2025-11-10",
      "week_range": "2025-11-04 到 2025-11-10",
      "description": "谢苗, 屈小煊 是家庭成员，在同一周服侍",
      "affected_persons": [
        {
          "person_id": "person_8101_谢苗",
          "person_name": "谢苗",
          "role": "敬拜主领",
          "service_date": "2025-11-10"
        }
      ],
      "family_group": "family_xie_qu",
      "suggestion": "建议将其中一人调整到其他周"
    },
    {
      "type": "unavailability_conflict",
      "severity": "error",
      "week": "2025-11-10",
      "description": "谢苗 在 2025-11-01 到 2025-11-15 期间不可用，但被安排服侍",
      "affected_persons": [...],
      "unavailable_reason": "旅行",
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
  },
  "timestamp": "2025-10-07T12:00:00Z"
}
```

---

#### 获取排班建议
```
POST /api/v1/volunteer/suggestions
```

基于可用性、家庭关系、服侍频率等因素，智能推荐合适的同工。

**请求体**:
```json
{
  "service_date": "2025-10-20",
  "required_roles": ["音控", "司琴", "敬拜主领"],
  "consider_availability": true,
  "consider_family": true,
  "consider_balance": true
}
```

**示例**:
```bash
curl -X POST http://localhost:8080/api/v1/volunteer/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "service_date": "2025-10-20",
    "required_roles": ["音控", "司琴"],
    "consider_availability": true,
    "consider_family": true,
    "consider_balance": true
  }'
```

**响应**:
```json
{
  "success": true,
  "service_date": "2025-10-20",
  "week_range": "2025-10-14 到 2025-10-20",
  "suggestions": [
    {
      "role": "音控",
      "candidates": [
        {
          "person_id": "person_6745_明明",
          "person_name": "明明",
          "score": 90,
          "reasons": [
            "时间可用",
            "无家庭成员冲突",
            "服侍次数适中（6次）",
            "距离上次服侍已有一段时间"
          ],
          "concerns": [],
          "statistics": {
            "total_services": 6,
            "unique_dates": 6,
            "roles": {
              "音控": 1,
              "敬拜同工": 4,
              "敬拜主领": 1
            }
          }
        }
      ]
    }
  ],
  "timestamp": "2025-10-07T12:00:00Z"
}
```

**评分系统**:
- 基础分: 50
- 时间可用: +10
- 无家庭冲突: +10
- 服侍较少: +20
- 距离上次服侍时间长: +10
- 岗位匹配: +15
- 时间不可用: -100 (排除)
- 家庭冲突: -30
- 近期服侍: -10 到 -20

---

## 快速测试

### 本地测试

```bash
# 给测试脚本执行权限
chmod +x test_new_api_endpoints.sh

# 运行测试（本地）
./test_new_api_endpoints.sh

# 或指定端口
./test_new_api_endpoints.sh http://localhost:8080
```

### 远程测试（Cloud Run）

```bash
./test_new_api_endpoints.sh https://ministry-data-cleaning-wu7uk5rgdq-uc.a.run.app
```

### 使用 curl 手动测试

```bash
# 健康检查
curl http://localhost:8080/health

# 获取讲道系列
curl "http://localhost:8080/api/v1/sermon/series?year=2024"

# 按讲员查询
curl "http://localhost:8080/api/v1/sermon/by-preacher/王通?limit=3"

# 查询排班空缺
curl "http://localhost:8080/api/v1/volunteer/availability/2024-10"

# 讲员统计
curl "http://localhost:8080/api/v1/stats/preachers?year=2024"

# 同工统计
curl "http://localhost:8080/api/v1/stats/volunteers?year=2024"

# 管线状态
curl "http://localhost:8080/api/v1/pipeline/status"

# 同工元数据
curl "http://localhost:8080/api/v1/volunteer/metadata"

# 下周服侍安排
curl "http://localhost:8080/api/v1/volunteer/next-week"

# 检测排班冲突
curl -X POST "http://localhost:8080/api/v1/volunteer/conflicts" \
  -H "Content-Type: application/json" \
  -d '{"year_month":"2025-11","check_family":true,"check_availability":true}'

# 获取排班建议
curl -X POST "http://localhost:8080/api/v1/volunteer/suggestions" \
  -H "Content-Type: application/json" \
  -d '{"service_date":"2025-10-20","required_roles":["音控"],"consider_availability":true}'
```

---

## MCP 端点映射

| MCP 类型 | MCP 名称 | API 端点 |
|----------|----------|----------|
| **Tools** | | |
| Tool | `clean_ministry_data` | `POST /api/v1/clean` |
| Tool | `generate_service_layer` | `POST /api/v1/service-layer/generate` |
| Tool | `add_person_alias` | `POST /api/v1/config/aliases` |
| Tool | `merge_person_aliases` | `POST /api/v1/config/aliases/merge` |
| Tool | `validate_raw_data` | `POST /api/v1/validate` |
| Tool | `get_pipeline_status` | `GET /api/v1/pipeline/status` |
| Tool | `trigger_scheduled_update` | `POST /trigger-cleaning` |
| Tool | `update_volunteer_metadata` | `POST /api/v1/volunteer/metadata` |
| Tool | `check_conflicts` | `POST /api/v1/volunteer/conflicts` |
| Tool | `get_suggestions` | `POST /api/v1/volunteer/suggestions` |
| **Resources** | | |
| Resource | `sermon-records` | `GET /api/v1/sermon` |
| Resource | `sermon-by-preacher` | `GET /api/v1/sermon/by-preacher/{name}` |
| Resource | `sermon-series` | `GET /api/v1/sermon/series` |
| Resource | `volunteer-assignments` | `GET /api/v1/volunteer` |
| Resource | `volunteer-by-person` | `GET /api/v1/volunteer/by-person/{id}` |
| Resource | `volunteer-availability` | `GET /api/v1/volunteer/availability/{month}` |
| Resource | `ministry-stats` | `GET /api/v1/stats` |
| Resource | `preacher-stats` | `GET /api/v1/stats/preachers` |
| Resource | `volunteer-stats` | `GET /api/v1/stats/volunteers` |
| Resource | `alias-mappings` | `GET /api/v1/config/aliases` |
| Resource | `volunteer-metadata` | `GET /api/v1/volunteer/metadata` |
| Resource | `next-week-schedule` | `GET /api/v1/volunteer/next-week` |

---

## 总结

### 新增端点统计

- ✅ **Sermon 高级查询**: 2个端点
- ✅ **Volunteer 高级查询**: 2个端点
- ✅ **统计分析**: 2个端点
- ✅ **别名管理**: 3个端点
- ✅ **验证和状态**: 2个端点
- ✅ **同工元数据和智能排班**: 5个端点

**总计**: 16个新端点

### 新增功能亮点

**智能排班系统**:
- 🎯 自动检测家庭成员冲突
- 📅 识别同工不可用时间（临时/长期）
- 🤖 基于多因素的智能排班建议
- ⚠️ 实时冲突检测和告警
- 📊 服侍频率均衡分析

### 下一步

1. 部署到 Cloud Run
2. 实现 MCP 服务器（阶段2）
3. 集成到 Claude Desktop

---

**相关文档**:
- [MCP 设计方案](MCP_DESIGN.md)
- [服务层架构](SERVICE_LAYER.md)
- [部署指南](DEPLOYMENT.md)

