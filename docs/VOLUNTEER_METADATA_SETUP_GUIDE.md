# 同工元数据功能设置指南

## ✅ 已完成的实施

### 1. API 端点（4/5 完成）

| 端点 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/v1/volunteer/metadata` | GET | ✅ 完成 | 获取同工元数据 |
| `/api/v1/volunteer/metadata` | POST | ✅ 完成 | 添加/更新元数据 |
| `/api/v1/volunteer/next-week` | GET | ✅ 完成 | 查看下周安排 |
| `/api/v1/volunteer/conflicts` | POST | ✅ 完成 | 检测冲突 |
| `/api/v1/volunteer/suggestions` | POST | ⏳ 待实施 | 排班建议（代码已提供）|

### 2. 配置文件

✅ `config/config.json` 已更新，添加了 `volunteer_metadata_sheet` 配置

---

## 📝 现在需要你做的事（3步）

### 步骤 1: 在 Google Sheets 中创建表格

1. **打开你的 Google Sheets**  
   https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit

2. **创建新 Sheet**  
   - 点击底部的 "+" 按钮
   - 重命名为：`VolunteerMetadata`

3. **添加表头**（第一行 A1-H1）  
   ```
   person_id | person_name | family_group | unavailable_start | unavailable_end | unavailable_reason | notes | updated_at
   ```

4. **添加示例数据**（从第2行开始）  

   **示例1: 夫妻关系（谢苗和屈小煊）**
   ```
   A2: person_8101_谢苗
   B2: 谢苗
   C2: family_xie_qu
   D2: 2024-11-01
   E2: 2024-11-15
   F2: 旅行
   G2: 优先安排早场
   H2: 2024-10-07
   ```
   
   ```
   A3: person_9017_屈小煊
   B3: 屈小煊
   C3: family_xie_qu
   D3: 
   E3: 
   F3: 
   G3: 与谢苗是夫妻
   H3: 2024-10-07
   ```

   **示例2: 长期不可用（靖铮回国）**
   ```
   A4: person_3850_靖铮
   B4: 靖铮
   C4: 
   D4: 2024-12-20
   E4: 2024-12-31
   F4: 回国探亲
   G4: 擅长音控
   H4: 2024-10-07
   ```

5. **格式化**  
   - 第一行加粗，设置灰色背景
   - 冻结第一行（视图 > 冻结 > 1行）
   - 列 D、E、H 设置为日期格式（yyyy-mm-dd）

6. **添加服务账号权限**  
   - 点击右上角 "共享"
   - 添加你的服务账号邮箱
   - 权限设置为 "编辑者"

详细说明请查看：`docs/GOOGLE_SHEETS_SETUP.md`

---

### 步骤 2: 测试 API 端点

创建完表格后，测试 API：

```bash
# 1. 获取元数据
curl "http://localhost:8080/api/v1/volunteer/metadata" | jq

# 2. 查看下周安排
curl "http://localhost:8080/api/v1/volunteer/next-week" | jq

# 3. 检测冲突
curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
  -H "Content-Type: application/json" \
  -d '{"year_month":"2024-10"}' | jq

# 4. 添加元数据
curl -X POST http://localhost:8080/api/v1/volunteer/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "person_id":"person_test",
    "person_name":"测试人员",
    "family_group":"family_test",
    "unavailable_start":"2024-11-01",
    "unavailable_end":"2024-11-10",
    "unavailable_reason":"测试",
    "notes":"这是一个测试"
  }' | jq
```

---

### 步骤 3: （可选）实施排班建议功能

如果需要排班建议功能，请将 `volunteer_metadata_endpoints.py` 中的 `get_volunteer_suggestions` 函数复制到 `app.py` 的 `check_volunteer_conflicts` 函数之后。

或者让我知道，我可以帮你完成这最后一个端点。

---

## 🎯 使用场景演示

### 场景 1: 查看下周有谁服侍

**问题**: "下周都有谁服侍？"

**API调用**:
```bash
curl "http://localhost:8080/api/v1/volunteer/next-week"
```

**返回示例**:
```json
{
  "success": true,
  "week_info": {
    "week_start": "2024-10-07",
    "week_end": "2024-10-13",
    "sunday_date": "2024-10-13"
  },
  "volunteers": [
    {
      "person_name": "谢苗",
      "role": "敬拜主领",
      "is_available": true,
      "metadata": {
        "notes": "优先安排早场",
        "family_group": "family_xie_qu"
      }
    }
  ],
  "summary": {
    "total_volunteers": 12,
    "unique_volunteers": 10,
    "unavailable_count": 0
  }
}
```

---

### 场景 2: 检测排班冲突

**问题**: "10月有没有排班冲突？"

**API调用**:
```bash
curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
  -H "Content-Type: application/json" \
  -d '{"year_month":"2024-10"}'
```

**返回示例**:
```json
{
  "success": true,
  "conflicts": [
    {
      "type": "family_conflict",
      "severity": "warning",
      "week": "2024-10-13",
      "description": "谢苗, 屈小煊 是家庭成员，在同一周服侍",
      "suggestion": "建议将其中一人调整到其他周"
    },
    {
      "type": "unavailability_conflict",
      "severity": "error",
      "week": "2024-10-27",
      "description": "张三 在 2024-10-20 到 2024-11-05 期间不可用，但被安排服侍",
      "suggestion": "需要重新安排其他人"
    }
  ],
  "summary": {
    "total_conflicts": 2,
    "by_severity": {
      "error": 1,
      "warning": 1
    }
  }
}
```

---

## 📊 数据结构说明

### family_group 字段

用于标识家庭成员关系，同一 `family_group` 的成员不能在同一周服侍。

**命名规范**:
- 夫妻: `family_{姓氏1}_{姓氏2}` (例如: `family_xie_qu`)
- 家庭: `family_{姓氏}` (例如: `family_du`)

### unavailable_start / unavailable_end

不可用时间段，支持多段：

**单段不可用**:
```csv
person_8101_谢苗,谢苗,,2024-11-01,2024-11-15,旅行,,2024-10-07
```

**多段不可用**（添加多行，person_id 相同）:
```csv
person_6878_杜德双,杜德双,,2024-10-15,2024-10-20,出差,,2024-10-07
person_6878_杜德双,杜德双,,2024-11-10,2024-11-12,参加会议,,2024-10-07
```

---

## 🔗 相关文档

| 文档 | 描述 |
|------|------|
| [GOOGLE_SHEETS_SETUP.md](docs/GOOGLE_SHEETS_SETUP.md) | 详细的 Google Sheets 设置指南 |
| [VOLUNTEER_METADATA_ANALYSIS.md](docs/VOLUNTEER_METADATA_ANALYSIS.md) | 完整的需求分析和设计方案 |
| [volunteer_metadata_endpoints.py](volunteer_metadata_endpoints.py) | 排班建议功能的完整代码 |

---

## ✅ 完成检查清单

- [ ] 在 Google Sheets 中创建 `VolunteerMetadata` 表
- [ ] 添加表头（A1-H1）
- [ ] 添加示例数据
- [ ] 格式化表格（日期格式、冻结行）
- [ ] 添加服务账号权限
- [ ] 测试 GET /api/v1/volunteer/metadata
- [ ] 测试 GET /api/v1/volunteer/next-week
- [ ] 测试 POST /api/v1/volunteer/conflicts
- [ ] （可选）实施 POST /api/v1/volunteer/suggestions

---

## 🚀 下一步

完成表格创建和测试后：

1. **集成到 MCP**：创建 MCP 服务器（阶段2）
2. **配置 Claude Desktop**：使其可以通过自然语言查询
3. **使用示例**：
   - "下周都有谁服侍？"
   - "10月有没有排班冲突？"
   - "谢苗11月3日可以服侍吗？"

---

**需要帮助吗？**
- 表格创建有问题？查看 `docs/GOOGLE_SHEETS_SETUP.md`
- API 测试有问题？检查服务账号权限
- 想要实施排班建议功能？让我知道，我可以帮你完成

**当前代码状态**:
- ✅ `app.py`: 2200+ 行，4个新端点已实现
- ✅ `config/config.json`: 已更新配置
- ✅ 文档齐全
- ⏳ Google Sheets 表格：需要你手动创建

