# Schema 管理文档

## 概述

本系统支持灵活的 schema 管理，能够：

1. **自动检测两行表头**：第1行为部门信息，第2行为列名
2. **灵活列映射**：支持简单映射和高级映射（多列合并）
3. **部门信息管理**：在清洗层和服务层中添加部门元数据
4. **半自动检测新列**：检测未配置的列并生成配置建议

## 配置格式

### 1. 基本结构

```json
{
  "source_sheet": {
    "url": "...",
    "range": "总表!A1:Z",
    "header_rows": 2,
    "department_row": 1,
    "column_row": 2
  },
  "departments": { ... },
  "schema_validation": { ... },
  "columns": { ... }
}
```

### 2. 部门配置

定义组织结构和角色归属：

```json
{
  "departments": {
    "sermon": {
      "name": "讲道",
      "roles": ["preacher", "reading"]
    },
    "worship": {
      "name": "敬拜部",
      "roles": ["worship_lead", "worship_team", "pianist"]
    },
    "technical": {
      "name": "媒体部",
      "roles": ["audio", "video", "propresenter_play", "propresenter_update"]
    },
    "education": {
      "name": "儿童部",
      "roles": ["assistant"]
    }
  }
}
```

**说明**：
- `key`（如 `sermon`）: 部门标识符
- `name`: 部门显示名称（用于输出）
- `roles`: 该部门包含的角色字段列表

### 3. Schema 验证配置

控制 schema 变化检测行为：

```json
{
  "schema_validation": {
    "enabled": true,              // 启用 schema 验证
    "auto_detect_new_columns": true,  // 自动检测新列
    "strict_mode": false          // 严格模式（true 时发现新列会报错）
  }
}
```

### 4. 列映射配置

支持两种格式：

#### 简单映射（单列）

```json
{
  "columns": {
    "preacher": "讲员",
    "audio": "音控"
  }
}
```

#### 高级映射（多列合并）

```json
{
  "columns": {
    "worship_team": {
      "sources": ["敬拜同工1", "敬拜同工2", "敬拜同工3"],
      "merge": true,
      "department": "worship"
    },
    "assistant": {
      "sources": ["助教", "助教1", "助教2"],
      "merge": true,
      "department": "education"
    }
  }
}
```

**参数说明**：
- `sources`: 源列名数组（支持多个）
- `merge`: 是否合并为数组（true=合并，false=只取第一个）
- `department`: 所属部门（可选，优先级高于 departments 配置）

## 使用场景

### 场景 1: 新增列（如助教3）

当 source sheet 新增列时：

1. **运行检测工具**：
   ```bash
   python core/detect_schema_changes.py --config config/config.json
   ```

2. **查看报告**：
   ```bash
   cat logs/schema_detection_report.json
   ```

3. **更新配置**：根据建议更新 `config/config.json`：
   ```json
   {
     "assistant": {
       "sources": ["助教", "助教1", "助教2", "助教3"],
       "merge": true,
       "department": "education"
     }
   }
   ```

4. **运行清洗**：
   ```bash
   python core/clean_pipeline.py --config config/config.json
   ```

### 场景 2: 部门重组

当部门结构调整时：

1. **更新 departments 配置**：
   ```json
   {
     "departments": {
       "multimedia": {
         "name": "多媒体部",
         "roles": ["audio", "video", "propresenter_play", "propresenter_update", "photography"]
       }
     }
   }
   ```

2. **更新列映射**（如果需要）：
   ```json
   {
     "columns": {
       "photography": {
         "sources": ["摄影", "拍照"],
         "merge": true,
         "department": "multimedia"
       }
     }
   }
   ```

### 场景 3: 合并现有列

将现有的多个单列合并为一个字段：

**原配置**：
```json
{
  "assistant_1": "助教1",
  "assistant_2": "助教2"
}
```

**新配置**：
```json
{
  "assistant": {
    "sources": ["助教1", "助教2"],
    "merge": true,
    "department": "education"
  }
}
```

## 输出格式

### 清洗层输出

每个角色字段现在包含三个相关字段：

```csv
preacher_id,preacher_name,preacher_department
john_smith,John Smith,讲道
```

对于合并字段（如 worship_team, assistant）：

```csv
worship_team_ids,worship_team_names,worship_team_department
["alice","bob"],["Alice Wang","Bob Li"],敬拜部
```

### 服务层输出

#### Volunteer Domain

```json
{
  "volunteers": [
    {
      "service_date": "2024-10-20",
      "worship": {
        "department": "敬拜部",
        "lead": {
          "id": "alice",
          "name": "Alice Wang"
        },
        "team": [
          {"id": "bob", "name": "Bob Li"},
          {"id": "charlie", "name": "Charlie Chen"}
        ],
        "pianist": {
          "id": "david",
          "name": "David Lee"
        }
      },
      "technical": {
        "department": "媒体部",
        "audio": {"id": "evan", "name": "Evan Wu"},
        "video": {"id": "frank", "name": "Frank Zhang"}
      },
      "education": {
        "department": "儿童部",
        "assistants": [
          {"id": "grace", "name": "Grace Liu"},
          {"id": "henry", "name": "Henry Huang"}
        ]
      }
    }
  ]
}
```

## Schema 检测工具

### 基本用法

```bash
# 检测 schema 变化
python core/detect_schema_changes.py

# 指定配置文件
python core/detect_schema_changes.py --config config/config.json

# 自定义输出路径
python core/detect_schema_changes.py --output my_report.json

# 安静模式（不打印摘要）
python core/detect_schema_changes.py --quiet
```

### 输出示例

```json
{
  "timestamp": "2024-10-20T10:30:00",
  "total_columns": 25,
  "mapped_columns": 23,
  "unmapped_columns": 2,
  "new_columns_detected": 2,
  "columns": {
    "new": ["助教3", "新角色"]
  },
  "department_mapping": {
    "助教3": "儿童部",
    "新角色": "未知"
  },
  "suggestions": {
    "columns": {
      "助教3": {
        "source_column": "助教3",
        "suggested_field": "assistant",
        "department": "儿童部",
        "config_example_simple": "\"assistant_3\": \"助教3\"",
        "config_example_advanced": {
          "sources": ["助教3"],
          "merge": false,
          "department": "education"
        }
      }
    }
  }
}
```

## 最佳实践

### 1. 定期运行检测

在清洗前运行检测工具：

```bash
# 检测 -> 审核 -> 配置 -> 清洗
python core/detect_schema_changes.py && \
vi config/config.json && \
python core/clean_pipeline.py
```

### 2. 使用合并字段

对于可能扩展的角色，使用合并配置：

✅ **推荐**：
```json
{
  "assistant": {
    "sources": ["助教1", "助教2", "助教3"],
    "merge": true
  }
}
```

❌ **不推荐**：
```json
{
  "assistant_1": "助教1",
  "assistant_2": "助教2",
  "assistant_3": "助教3"
}
```

### 3. 明确部门归属

在列映射中明确指定部门（可选但推荐）：

```json
{
  "audio": {
    "sources": ["音控"],
    "merge": false,
    "department": "technical"
  }
}
```

### 4. 保持向后兼容

新增字段使用合并格式，现有字段保持简单格式（除非需要扩展）：

```json
{
  "preacher": "讲员",          // 简单格式（稳定）
  "assistant": {               // 高级格式（可扩展）
    "sources": ["助教1", "助教2"],
    "merge": true
  }
}
```

### 5. 部门信息的使用

- **清洗层**: 作为额外信息列，不影响核心数据
- **服务层**: 按部门组织数据，便于查询和统计
- **API 层**: 支持按部门筛选和聚合

## 常见问题

### Q1: 如何处理临时列？

临时列（如"备注"、"待定"）可以忽略：

```json
{
  "schema_validation": {
    "strict_mode": false  // 允许未配置的列存在
  }
}
```

### Q2: 列名变化了怎么办？

更新 sources 数组，保留旧列名一段时间以兼容：

```json
{
  "assistant": {
    "sources": ["助教", "助教1", "助教2", "教师助理"],  // 新旧名称都支持
    "merge": true
  }
}
```

### Q3: 部门信息不准确？

优先级顺序：
1. 列映射中的 `department` 字段
2. `departments` 配置中的 `roles` 映射
3. Source sheet 第1行的部门标注（如果有）

### Q4: 如何测试新配置？

使用 dry-run 模式：

```bash
python core/clean_pipeline.py --dry-run
# 检查 logs/clean_preview.json
```

### Q5: 能否自动合并所有带数字后缀的列？

目前需要手动配置。这是设计决策，确保数据处理的可预测性和可审计性。

## 迁移指南

### 从旧配置迁移

**步骤 1**: 添加新配置节

```json
{
  "departments": { ... },
  "schema_validation": { ... }
}
```

**步骤 2**: 转换需要合并的列

将：
```json
{
  "worship_team_1": "敬拜同工1",
  "worship_team_2": "敬拜同工2"
}
```

改为：
```json
{
  "worship_team": {
    "sources": ["敬拜同工1", "敬拜同工2"],
    "merge": true,
    "department": "worship"
  }
}
```

**步骤 3**: 测试

```bash
python core/detect_schema_changes.py
python core/clean_pipeline.py --dry-run
```

**步骤 4**: 部署

```bash
python core/clean_pipeline.py
```

## 参考

- [系统架构](ARCHITECTURE.md)
- [API 文档](API_ENDPOINTS.md)
- [服务层设计](SERVICE_LAYER.md)

