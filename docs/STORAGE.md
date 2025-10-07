# Cloud Storage 和数据管理

## 📋 目录

- [概述](#概述)
- [文件组织结构](#文件组织结构)
- [快速开始](#快速开始)
- [数据统计](#数据统计)
- [访问方式](#访问方式)
- [定时更新](#定时更新)
- [成本估算](#成本估算)
- [故障排除](#故障排除)

---

## 概述

项目使用 Google Cloud Storage (GCS) 存储服务层数据，支持：

- ✅ **自动上传**：清洗管线自动生成并上传
- ✅ **多年份管理**：按年份组织数据（2024-2026）
- ✅ **版本控制**：支持历史版本管理
- ✅ **API 访问**：通过 API 查询各年份数据
- ✅ **成本低廉**：< $0.01/月

### Bucket 信息

```
名称: grace-irvine-ministry-data
项目: ai-for-god
位置: us-central1
状态: ✅ 正常运行
```

---

## 文件组织结构

### Cloud Storage 结构

```
gs://grace-irvine-ministry-data/
└── domains/
    ├── sermon/                        【证道域】
    │   ├── latest.json               70.1 KB ✅
    │   ├── 2024/
    │   │   └── sermon_2024.json      70.1 KB ✅
    │   ├── 2025/
    │   │   └── sermon_2025.json      28.7 KB ✅
    │   └── 2026/
    │       └── sermon_2026.json      11.0 KB ✅
    └── volunteer/                     【同工域】
        ├── latest.json               120.4 KB ✅
        ├── 2024/
        │   └── volunteer_2024.json   120.4 KB ✅
        ├── 2025/
        │   └── volunteer_2025.json   50.6 KB ✅
        └── 2026/
            └── volunteer_2026.json   19.0 KB ✅
```

### 本地文件结构

```
logs/service_layer/
├── sermon.json                    # latest（所有数据）
├── volunteer.json                 # latest（所有数据）
├── 2024/
│   ├── sermon_2024.json          # 52 条记录
│   └── volunteer_2024.json       # 52 条记录
├── 2025/
│   ├── sermon_2025.json          # 52 条记录
│   └── volunteer_2025.json       # 52 条记录
└── 2026/
    ├── sermon_2026.json          # 27 条记录
    └── volunteer_2026.json       # 27 条记录
```

---

## 快速开始

### 1. 创建 Bucket（首次）

```bash
# 使用 gcloud 命令创建 bucket
gcloud storage buckets create gs://grace-irvine-ministry-data \
  --location=us-central1 \
  --project=ai-for-god

# 或使用 gsutil
gsutil mb -l us-central1 -p ai-for-god gs://grace-irvine-ministry-data
```

### 2. 生成并上传数据

#### 方法 1：通过清洗管线（推荐）

```bash
# 运行完整管线（自动生成并上传）
python3 scripts/clean_pipeline.py --config config/config.json
```

#### 方法 2：通过 API

```bash
# 生成并上传（Cloud Run 部署后）
curl -X POST https://your-service-url.run.app/api/v1/service-layer/generate \
  -H "Content-Type: application/json" \
  -d '{"upload_to_bucket": true, "generate_all_years": true}'
```

#### 方法 3：通过命令行工具

```bash
# 生成服务层数据
python3 scripts/service_layer.py \
  --input logs/clean_preview.json \
  --output-dir logs/service_layer

# 上传到 bucket
python3 scripts/cloud_storage_utils.py \
  --bucket grace-irvine-ministry-data \
  --service-account config/service-account.json \
  --upload logs/service_layer/sermon.json \
  --domain sermon
```

### 3. 验证上传

```bash
# 列出所有文件
gsutil ls -lh gs://grace-irvine-ministry-data/domains/**/*.json

# 查看文件内容（前50行）
gsutil cat gs://grace-irvine-ministry-data/domains/sermon/latest.json | python3 -m json.tool | head -50

# 使用 Python 验证
python3 -c "
from google.cloud import storage
from google.oauth2 import service_account
import json

credentials = service_account.Credentials.from_service_account_file('config/service-account.json')
client = storage.Client(credentials=credentials)
bucket = client.bucket('grace-irvine-ministry-data')

# 列出所有文件
blobs = client.list_blobs('grace-irvine-ministry-data', prefix='domains/')
for blob in blobs:
    print(f'{blob.name}: {blob.size / 1024:.1f} KB')
"
```

---

## 数据统计

### 总体统计
- **总记录数**: 131 条
- **覆盖年份**: 2024, 2025, 2026
- **生成文件**: 8 个（每年 2 个域 × 3 年 + 2 个 latest）
- **总数据量**: 490.3 KB

### 按年份统计

| 年份 | 记录数 | 日期范围 | Sermon 大小 | Volunteer 大小 |
|-----|--------|---------|-------------|----------------|
| **2024** | 52 条 | 2024-01-07 ~ 2024-12-29 | 70.1 KB | 120.4 KB |
| **2025** | 52 条 | 2025-01-05 ~ 2025-12-28 | 28.7 KB | 50.6 KB |
| **2026** | 27 条 | 2026-01-04 ~ 2026-07-05 | 11.0 KB | 19.0 KB |

---

## 访问方式

### 1. Google Cloud Console

浏览器访问：
```
https://console.cloud.google.com/storage/browser/grace-irvine-ministry-data
```

### 2. gsutil 命令行

```bash
# 列出所有文件
gsutil ls -r gs://grace-irvine-ministry-data/

# 下载特定文件
gsutil cp gs://grace-irvine-ministry-data/domains/sermon/2024/sermon_2024.json ./

# 查看文件内容
gsutil cat gs://grace-irvine-ministry-data/domains/sermon/latest.json | python3 -m json.tool | head -50

# 下载整个域
gsutil -m cp -r gs://grace-irvine-ministry-data/domains/sermon/ ./local_backup/
```

### 3. Python API

```python
from google.cloud import storage
from google.oauth2 import service_account
import json

# 初始化客户端
credentials = service_account.Credentials.from_service_account_file(
    'config/service-account.json'
)
client = storage.Client(credentials=credentials)

# 列出所有文件
bucket = client.bucket('grace-irvine-ministry-data')
blobs = client.list_blobs('grace-irvine-ministry-data', prefix='domains/')
for blob in blobs:
    print(f"{blob.name}: {blob.size / 1024:.1f} KB")

# 读取 2024 年证道数据
blob = bucket.blob('domains/sermon/2024/sermon_2024.json')
sermon_2024 = json.loads(blob.download_as_text())
print(f"2024 年证道记录数: {sermon_2024['metadata']['record_count']}")
```

### 4. 项目 API

```bash
# 获取证道域数据（API 部署后）
curl "https://your-service-url.run.app/api/v1/sermon?year=2024&limit=10"

# 获取同工域数据
curl "https://your-service-url.run.app/api/v1/volunteer?year=2024&limit=10"
```

---

## 定时更新

### Cloud Scheduler 配置（推荐）

```bash
# 创建定时任务（每周日晚上 23:00）
gcloud scheduler jobs create http ministry-data-update \
  --schedule="0 23 * * 0" \
  --uri="https://your-service-url.run.app/api/v1/service-layer/generate" \
  --http-method=POST \
  --message-body='{"generate_all_years":true,"upload_to_bucket":true}' \
  --headers="Content-Type=application/json" \
  --oidc-service-account-email=SERVICE_ACCOUNT_EMAIL \
  --location=us-central1 \
  --time-zone="America/Los_Angeles"
```

### 工作流程

```
每周日 23:00
    ↓
Cloud Scheduler 触发
    ↓
调用 API 生成服务层数据
    ↓
生成所有年份 (2024, 2025, 2026)
    ↓
上传到 Cloud Storage
    ↓
更新 latest 和年度文件
    ↓
记录日志
```

---

## 成本估算

### Google Cloud Storage 定价（美国中部）

- **标准存储**: $0.020 per GB/月
- **操作费用**: $0.004 per 1,000 读取
- **网络费用**: $0.12 per GB（出站到互联网）

### 当前使用

- **存储空间**: 490 KB ≈ 0.0005 GB
- **月成本**: < $0.01
- **年成本**: < $0.12

### 未来预估（按每年 52 条记录）

- **每年新增**: ~200 KB
- **5 年累计**: ~2.5 MB
- **5 年总成本**: < $0.60

### 总运营成本（含 Cloud Run + Scheduler）

| 服务 | 月成本 | 年成本 |
|-----|--------|--------|
| Cloud Storage | < $0.01 | < $0.12 |
| Cloud Run | ~$0.57 | ~$6.84 |
| Cloud Scheduler | $0.00 | $0.00 |
| **总计** | **~$0.57** | **~$7** |

---

## 数据管理

### 生成特定年份数据

```bash
# 通过 API 生成所有年份数据
curl -X POST https://your-service-url.run.app/api/v1/service-layer/generate \
  -H "Content-Type: application/json" \
  -d '{"upload_to_bucket": true, "generate_all_years": true}'

# 或本地运行清洗管线（自动生成所有年份）
python3 scripts/clean_pipeline.py --config config/config.json
```

### 手动生成特定年份

```python
# 使用 Python 脚本生成特定年份
from pathlib import Path
import pandas as pd
import json
from scripts.service_layer import ServiceLayerManager

# 读取清洗层数据
with open('logs/clean_preview.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
df = pd.DataFrame(data)

# 筛选特定年份
year = 2025
df_year = df[df['service_date'].str.startswith(str(year))]

# 生成服务层数据
manager = ServiceLayerManager()
domain_data = manager.generate_domain_data(df_year, ['sermon', 'volunteer'])

# 保存
output_dir = Path(f'logs/service_layer/{year}')
output_dir.mkdir(parents=True, exist_ok=True)
for domain, data in domain_data.items():
    with open(output_dir / f'{domain}_{year}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

### 备份数据

```bash
# 下载到本地
gsutil -m cp -r gs://grace-irvine-ministry-data/domains/ ./backup/

# 压缩备份
tar -czf domains_backup_$(date +%Y%m%d).tar.gz backup/domains/

# 上传到另一个 bucket（灾备）
gsutil -m cp -r gs://grace-irvine-ministry-data/domains/ \
  gs://grace-irvine-ministry-backup/$(date +%Y%m%d)/
```

### 清理旧数据

```bash
# 删除旧年份数据（谨慎操作！）
gsutil rm -r gs://grace-irvine-ministry-data/domains/sermon/2023/
gsutil rm -r gs://grace-irvine-ministry-data/domains/volunteer/2023/
```

---

## 使用场景

### 场景 1：年度报告生成

```python
# 生成 2024 年度证道统计报告
import json
from collections import Counter

# 从 Cloud Storage 读取
from google.cloud import storage
client = storage.Client(credentials=credentials)
bucket = client.bucket('grace-irvine-ministry-data')
blob = bucket.blob('domains/sermon/2024/sermon_2024.json')
data = json.loads(blob.download_as_text())

# 统计讲员次数
preachers = [s['preacher']['name'] for s in data['sermons']]
print("2024 年讲员统计:")
for preacher, count in Counter(preachers).most_common():
    print(f"  {preacher}: {count} 次")
```

### 场景 2：多年份对比

```python
# 对比不同年份的数据
years = [2024, 2025, 2026]

for year in years:
    blob = bucket.blob(f'domains/sermon/{year}/sermon_{year}.json')
    data = json.loads(blob.download_as_text())
    count = data['metadata']['record_count']
    date_range = data['metadata']['date_range']
    print(f"{year}: {count} 条记录 ({date_range['start']} ~ {date_range['end']})")
```

### 场景 3：数据导出

```python
# 导出为 CSV
import pandas as pd

blob = bucket.blob('domains/sermon/2024/sermon_2024.json')
data = json.loads(blob.download_as_text())

# 转换为 DataFrame
df = pd.DataFrame(data['sermons'])
df.to_csv('sermon_2024_export.csv', index=False)
```

---

## 故障排除

### 问题 1: 上传失败 - 权限错误

**错误**: `403 Forbidden`

**解决**: 确保服务账号有正确的权限

```bash
# 授予 Storage Object Creator 权限
gcloud projects add-iam-policy-binding ai-for-god \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectCreator"

# 或授予 Storage Admin（更高权限）
gcloud projects add-iam-policy-binding ai-for-god \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.admin"
```

### 问题 2: Bucket 名称已被占用

**错误**: `Bucket name already exists`

**解决**: 在 `config/config.json` 中更改 bucket 名称

```json
{
  "service_layer": {
    "storage": {
      "bucket": "your-unique-bucket-name"  // 改为唯一的名称
    }
  }
}
```

### 问题 3: 文件未上传

**检查步骤**:

1. 确认配置正确
```bash
cat config/config.json | grep -A 5 "service_layer"
```

2. 检查本地文件是否生成
```bash
ls -lh logs/service_layer/
ls -lh logs/service_layer/*/
```

3. 查看日志
```bash
# 查看清洗管线日志
tail -100 logs/*.log

# 查看 Cloud Run 日志（如果部署了）
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### 问题 4: 网络超时

**解决**: 

```bash
# 设置代理（如果需要）
export HTTPS_PROXY=http://proxy.example.com:8080

# 增加超时时间
gsutil -o "GSUtil:http_socket_timeout=300" cp ...
```

### 问题 5: 数据不完整

**验证数据完整性**:

```bash
# 检查记录数
gsutil cat gs://grace-irvine-ministry-data/domains/sermon/2024/sermon_2024.json | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"记录数: {data['metadata']['record_count']}\")"

# 验证所有文件
python3 -c "
from google.cloud import storage
from google.oauth2 import service_account
import json

credentials = service_account.Credentials.from_service_account_file('config/service-account.json')
client = storage.Client(credentials=credentials)
bucket = client.bucket('grace-irvine-ministry-data')

# 检查 sermon domain
for year in ['2024', '2025', '2026']:
    blob = bucket.blob(f'domains/sermon/{year}/sermon_{year}.json')
    if blob.exists():
        data = json.loads(blob.download_as_text())
        print(f\"✓ Sermon {year}: {data['metadata']['record_count']} 条记录\")
    else:
        print(f\"✗ Sermon {year}: 文件不存在\")

# 检查 volunteer domain
for year in ['2024', '2025', '2026']:
    blob = bucket.blob(f'domains/volunteer/{year}/volunteer_{year}.json')
    if blob.exists():
        data = json.loads(blob.download_as_text())
        print(f\"✓ Volunteer {year}: {data['metadata']['record_count']} 条记录\")
    else:
        print(f\"✗ Volunteer {year}: 文件不存在\")
"
```

---

## 监控和维护

### 设置监控告警

```bash
# 创建告警策略（存储使用超过 1GB）
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Storage Usage Alert" \
  --condition-display-name="Storage > 1GB" \
  --condition-threshold-value=1073741824 \
  --condition-threshold-duration=300s
```

### 查看使用情况

```bash
# 查看 bucket 大小
gsutil du -sh gs://grace-irvine-ministry-data/

# 查看各域的大小
gsutil du -h gs://grace-irvine-ministry-data/domains/sermon/
gsutil du -h gs://grace-irvine-ministry-data/domains/volunteer/

# 统计文件数量
gsutil ls -r gs://grace-irvine-ministry-data/ | wc -l
```

### 定期维护任务

```bash
# 每月备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d)
gsutil -m cp -r gs://grace-irvine-ministry-data/domains/ \
  gs://grace-irvine-ministry-backup/$DATE/

# 保留最近 3 个月的备份
# ...（添加清理逻辑）
```

---

## 相关文档

- [SERVICE_LAYER.md](SERVICE_LAYER.md) - 服务层详细文档
- [DEPLOYMENT.md](DEPLOYMENT.md) - 云部署指南
- [API 文档](https://your-service-url.run.app/docs) - 交互式 API 文档
- [Google Cloud Storage 文档](https://cloud.google.com/storage/docs)

---

## 快速命令参考

```bash
# 列出文件
gsutil ls -lh gs://grace-irvine-ministry-data/domains/**/*.json

# 下载文件
gsutil cp gs://grace-irvine-ministry-data/domains/sermon/latest.json ./

# 查看内容
gsutil cat gs://grace-irvine-ministry-data/domains/sermon/latest.json | python3 -m json.tool | head -50

# 上传文件
gsutil cp sermon.json gs://grace-irvine-ministry-data/domains/sermon/

# 删除文件
gsutil rm gs://grace-irvine-ministry-data/domains/sermon/old_file.json

# 同步目录
gsutil -m rsync -r local_dir/ gs://grace-irvine-ministry-data/domains/

# 设置权限
gsutil iam ch serviceAccount:SERVICE_EMAIL:objectCreator \
  gs://grace-irvine-ministry-data
```

---

**版本**: 2.0  
**创建时间**: 2024-10-07  
**状态**: ✅ 生产就绪

