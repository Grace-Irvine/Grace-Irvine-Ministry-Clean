# 服务层 (Service Layer) 完整指南

## 📋 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [数据格式](#数据格式)
- [配置](#配置)
- [API 端点](#api-端点)
- [使用场景](#使用场景)
- [故障排除](#故障排除)

---

## 概述

服务层将清洗层的扁平化数据转换为两个独立的领域模型：

1. **Sermon Domain（证道域）** - 包含证道相关的核心信息
2. **Volunteer Domain（同工域）** - 包含主日服侍同工信息

### 核心特性

- ✅ **自动生成所有年份**：智能检测并生成所有历史年份的数据（2024-2026）
- ✅ **Cloud Storage 集成**：自动上传到 Google Cloud Storage
- ✅ **文件组织**：按领域和年份组织（latest + yearly）
- ✅ **API 支持**：RESTful API 查询各年份数据
- ✅ **自动化**：集成到清洗管线，无需手动干预

---

## 架构设计

```
┌─────────────────┐
│  清洗层 (Clean) │
│  扁平化数据      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│    服务层转换器 (Service Layer)  │
│    - 领域分离                    │
│    - 数据建模                    │
│    - 按年份组织                  │
└──────┬──────────────────┬───────┘
       │                  │
       ▼                  ▼
┌──────────────┐    ┌──────────────┐
│ Sermon Domain│    │Volunteer     │
│ 证道域        │    │Domain        │
│ (sermon.json)│    │同工域        │
└──────┬───────┘    │(volunteer.   │
       │            │json)         │
       │            └──────┬───────┘
       │                   │
       ▼                   ▼
┌───────────────────────────────┐
│  Cloud Storage Bucket         │
│  gs://[bucket]/domains/       │
│  ├── sermon/                  │
│  │   ├── latest.json         │
│  │   ├── 2024/              │
│  │   │   └── sermon_2024.json│
│  │   ├── 2025/              │
│  │   │   └── sermon_2025.json│
│  │   └── 2026/              │
│  │       └── sermon_2026.json│
│  └── volunteer/              │
│      ├── latest.json         │
│      ├── 2024/              │
│      │   └── volunteer_2024. │
│      │       json            │
│      ├── 2025/              │
│      │   └── volunteer_2025. │
│      │       json            │
│      └── 2026/              │
│          └── volunteer_2026. │
│              json            │
└───────────────────────────────┘
```

---

## 快速开始

### 方法 1：通过清洗管线自动生成（推荐）

```bash
# 运行完整管线（自动生成所有年份并上传）
python3 scripts/clean_pipeline.py --config config/config.json
```

### 方法 2：通过命令行手动生成

```bash
# 生成服务层数据（所有年份）
python3 scripts/service_layer.py \
  --input logs/clean_preview.json \
  --output-dir logs/service_layer

# 只生成特定域
python3 scripts/service_layer.py \
  --input logs/clean_preview.json \
  --output-dir logs/service_layer \
  --domains sermon
```

### 方法 3：通过 API

```bash
# 生成所有年份并上传到 Cloud Storage
curl -X POST http://localhost:8080/api/v1/service-layer/generate \
  -H "Content-Type: application/json" \
  -d '{
    "generate_all_years": true,
    "upload_to_bucket": true
  }'

# 查询证道域数据
curl "http://localhost:8080/api/v1/sermon?year=2024&limit=10"

# 查询同工域数据
curl "http://localhost:8080/api/v1/volunteer?year=2024&limit=10"
```

---

## 数据格式

### Sermon Domain（证道域）

```json
{
  "metadata": {
    "domain": "sermon",
    "version": "1.0",
    "generated_at": "2024-10-07T10:30:00Z",
    "record_count": 52,
    "date_range": {
      "start": "2024-01-07",
      "end": "2024-12-29"
    }
  },
  "sermons": [
    {
      "service_date": "2024-01-07",
      "service_week": 1,
      "service_slot": "morning",
      "sermon": {
        "title": "第一个福音",
        "series": "遇见耶稣",
        "scripture": "创世纪 3",
        "catechism": "",
        "reading": ""
      },
      "preacher": {
        "id": "person_6511_王通",
        "name": "王通"
      },
      "songs": [
        "奇异恩典",
        "有福的确据",
        "宝贵十架"
      ],
      "source_row": 2,
      "updated_at": "2024-10-06T23:29:41.892121Z"
    }
  ]
}
```

### Volunteer Domain（同工域）

```json
{
  "metadata": {
    "domain": "volunteer",
    "version": "1.0",
    "generated_at": "2024-10-07T10:30:00Z",
    "record_count": 52,
    "date_range": {
      "start": "2024-01-07",
      "end": "2024-12-29"
    }
  },
  "volunteers": [
    {
      "service_date": "2024-01-07",
      "service_week": 1,
      "service_slot": "morning",
      "worship": {
        "lead": {
          "id": "person_8101_谢苗",
          "name": "谢苗"
        },
        "team": [
          {
            "id": "person_9017_屈小煊",
            "name": "屈小煊"
          },
          {
            "id": "person_6878_杜德双",
            "name": "杜德双"
          }
        ],
        "pianist": {
          "id": "person_shawn,yaxi,peter",
          "name": "Shawn, Yaxi, Peter"
        }
      },
      "technical": {
        "audio": {
          "id": "person_3850_靖铮",
          "name": "靖铮"
        },
        "video": {
          "id": "person_2012_俊鑫",
          "name": "俊鑫"
        },
        "propresenter_play": {
          "id": "person_3483_康康",
          "name": "康康"
        },
        "propresenter_update": {
          "id": "",
          "name": ""
        }
      },
      "source_row": 2,
      "updated_at": "2024-10-06T23:29:41.892121Z"
    }
  ]
}
```

---

## 配置

在 `config/config.json` 中配置服务层：

```json
{
  "service_layer": {
    "enabled": true,
    "domains": ["sermon", "volunteer"],
    "local_output_dir": "logs/service_layer",
    "storage": {
      "provider": "gcs",
      "bucket": "grace-irvine-ministry-data",
      "base_path": "domains/",
      "service_account_file": "config/service-account.json",
      "enable_versioning": true
    },
    "output_options": {
      "latest_file": true,
      "yearly_files": true,
      "quarterly_files": false,
      "monthly_files": false
    }
  }
}
```

### 配置说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `enabled` | Boolean | 是否启用服务层 |
| `domains` | Array | 要生成的领域列表 |
| `local_output_dir` | String | 本地输出目录 |
| `storage.provider` | String | 存储提供商（`gcs` 或留空） |
| `storage.bucket` | String | GCS Bucket 名称 |
| `storage.base_path` | String | Bucket 内的基础路径 |
| `storage.service_account_file` | String | 服务账号 JSON 文件路径 |

---

## API 端点

### 1. 生成服务层数据

**端点**: `POST /api/v1/service-layer/generate`

**请求体**:
```json
{
  "domains": ["sermon", "volunteer"],
  "generate_all_years": true,
  "force": false,
  "upload_to_bucket": false
}
```

**响应**:
```json
{
  "success": true,
  "message": "成功生成 2 个领域 × 4 个年份的数据",
  "domains_generated": ["sermon", "volunteer"],
  "years_generated": ["2024", "2025", "2026", "latest"],
  "files_saved": {
    "2024": {
      "sermon": "logs/service_layer/2024/sermon_2024.json",
      "volunteer": "logs/service_layer/2024/volunteer_2024.json"
    },
    "2025": { ... },
    "2026": { ... },
    "latest": { ... }
  },
  "record_counts": {
    "2024": {"sermon": 52, "volunteer": 52},
    "2025": {"sermon": 52, "volunteer": 52},
    "2026": {"sermon": 27, "volunteer": 27},
    "latest": {"sermon": 131, "volunteer": 131}
  },
  "uploaded_to_bucket": false,
  "timestamp": "2024-10-07T10:30:00Z"
}
```

### 2. 获取证道域数据

**端点**: `GET /api/v1/sermon`

**查询参数**:
- `year` (可选): 按年份筛选
- `limit` (默认 100): 返回数量限制
- `offset` (默认 0): 偏移量

**响应**:
```json
{
  "metadata": {
    "domain": "sermon",
    "version": "1.0",
    "total_count": 150,
    "returned_count": 10,
    "offset": 0,
    "limit": 10
  },
  "sermons": [...]
}
```

### 3. 获取同工域数据

**端点**: `GET /api/v1/volunteer`

**查询参数**:
- `year` (可选): 按年份筛选
- `service_date` (可选): 按日期筛选（YYYY-MM-DD）
- `limit` (默认 100): 返回数量限制
- `offset` (默认 0): 偏移量

**响应**:
```json
{
  "metadata": {
    "domain": "volunteer",
    "version": "1.0",
    "total_count": 150,
    "returned_count": 10,
    "offset": 0,
    "limit": 10
  },
  "volunteers": [...]
}
```

---

## 使用场景

### 场景 1：证道归档网站
- 按系列浏览证道
- 按讲员筛选
- 按经文搜索
- 查询某一年的所有证道

### 场景 2：同工排班管理
- 查看每周同工安排
- 统计同工服侍频率
- 检测排班冲突
- 分析同工参与度

### 场景 3：年度报告生成

```python
# 生成 2024 年度证道统计报告
import json
from collections import Counter

with open('logs/service_layer/2024/sermon_2024.json', 'r') as f:
    data = json.load(f)

# 统计讲员次数
preachers = [s['preacher']['name'] for s in data['sermons']]
print("2024 年讲员统计:")
for preacher, count in Counter(preachers).most_common():
    print(f"  {preacher}: {count} 次")

# 统计系列
series = [s['sermon']['series'] for s in data['sermons']]
print("\n2024 年讲道系列:")
for s in set(series):
    print(f"  - {s}")
```

### 场景 4：多年份对比

```python
# 对比不同年份的数据
years = [2024, 2025, 2026]

for year in years:
    with open(f'logs/service_layer/{year}/sermon_{year}.json', 'r') as f:
        data = json.load(f)
        count = data['metadata']['record_count']
        date_range = data['metadata']['date_range']
        print(f"{year}: {count} 条记录 ({date_range['start']} ~ {date_range['end']})")
```

---

## 故障排除

### 问题 1: 清洗层数据不存在

**错误**: `清洗层数据不存在，请先运行清洗任务`

**解决**: 先运行清洗管线生成清洗层数据

```bash
python3 scripts/clean_pipeline.py --config config/config.json
```

### 问题 2: Cloud Storage 上传失败

**错误**: `google-cloud-storage 未安装`

**解决**: 安装依赖

```bash
pip install google-cloud-storage
```

### 问题 3: 权限错误

**错误**: `403 Forbidden`

**解决**: 确保服务账号有正确的权限

```bash
# 授予 Storage Object Creator 权限
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectCreator"
```

### 问题 4: 文件未生成

**检查步骤**:
1. 确认配置文件中 `service_layer.enabled` 为 `true`
2. 检查 `local_output_dir` 路径是否正确
3. 查看清洗管线日志输出
4. 验证清洗层数据是否存在

---

## 核心代码

### ServiceLayerManager

```python
from scripts.service_layer import ServiceLayerManager
import pandas as pd
import json

# 读取清洗层数据
with open('logs/clean_preview.json') as f:
    clean_df = pd.DataFrame(json.load(f))

# 创建管理器
manager = ServiceLayerManager()

# 生成所有年份的服务层数据
all_files = manager.generate_all_years(
    clean_df, 
    output_dir='logs/service_layer', 
    domains=['sermon', 'volunteer']
)

# 返回格式:
# {
#   '2024': {'sermon': Path(...), 'volunteer': Path(...)},
#   '2025': {'sermon': Path(...), 'volunteer': Path(...)},
#   '2026': {'sermon': Path(...), 'volunteer': Path(...)},
#   'latest': {'sermon': Path(...), 'volunteer': Path(...)}
# }

print(f"生成的年份: {list(all_files.keys())}")
```

### 上传到 Cloud Storage

```python
from scripts.cloud_storage_utils import DomainStorageManager

# 创建存储管理器
storage_manager = DomainStorageManager(
    bucket_name='grace-irvine-ministry-data',
    service_account_file='config/service-account.json'
)

# 上传证道域数据
sermon_files = storage_manager.upload_domain_data(
    domain='sermon',
    data=sermon_data,
    year=2024
)

print(f"上传的文件: {sermon_files}")
```

---

## 性能指标

| 操作 | 耗时 | 数据量 |
|-----|------|--------|
| 生成所有年份（3年） | ~2秒 | 131 条记录 |
| 上传到 Bucket | ~3秒 | 8 个文件（490 KB） |
| **总计** | **~5秒** | **完整更新** |

---

## 存储成本

### 当前使用
- **总大小**: 490 KB ≈ 0.0005 GB
- **月成本**: < $0.01
- **年成本**: < $0.12

### 未来预估（按每年 52 条记录）
- **每年新增**: ~200 KB
- **5 年累计**: ~2.5 MB
- **5 年总成本**: < $0.60

*基于 Google Cloud Storage 标准存储定价（$0.020/GB/月）*

---

## 相关文档

- [STORAGE.md](STORAGE.md) - Cloud Storage 详细文档
- [DEPLOYMENT.md](DEPLOYMENT.md) - 云部署指南
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - MCP 集成指南
- [README.md](README.md) - 项目主文档

---

**版本**: 2.0  
**创建时间**: 2024-10-07  
**状态**: ✅ 生产就绪

