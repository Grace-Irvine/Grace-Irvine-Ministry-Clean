# 同工不可用时间标注指南

## 📋 概述

本指南说明如何在 `VolunteerMetadata` Google Sheet 中正确标注同工的不可用时间，以便系统能够在排班建议和冲突检测中做出正确的调整。

---

## 🎯 两种不可用情况

### 情况1：临时不可用（有明确结束日期）

**适用场景**：
- 短期旅行
- 参加培训
- 临时出差
- 短期生病
- 特定时间段的个人安排

**标注方法**：填写明确的开始和结束日期

**示例**：

```
person_id          | person_name | unavailable_start | unavailable_end | unavailable_reason        | notes
-------------------|-------------|-------------------|-----------------|---------------------------|------------------
person_8101_谢苗   | 谢苗        | 2025-11-01        | 2025-11-15      | 旅行                      | 
person_3850_靖铮   | 靖铮        | 2025-12-20        | 2025-12-31      | 回国探亲                  |
person_6745_明明   | 明明        | 2025-10-15        | 2025-10-22      | 出差                      |
person_noah        | Noah        | 2025-11-08        | 2025-11-10      | 参加婚礼                  |
```

**系统行为**：
- ✅ 在不可用期间，该同工不会出现在排班建议中
- ✅ 如果已排班，冲突检测会标记为 `error` 级别冲突
- ✅ 期限过后，自动恢复可用状态

---

### 情况2：长期/无限期不可用

**适用场景**：
- 长期生病休养
- 暂停服侍（恢复时间未定）
- 退出服侍团队
- 产假/陪产假
- 长期出国
- 工作/学业繁忙（暂停服侍）

**标注方法**：使用远期日期（推荐 `2099-12-31`）

**示例**：

```
person_id          | person_name | unavailable_start | unavailable_end | unavailable_reason        | notes
-------------------|-------------|-------------------|-----------------|---------------------------|------------------
person_6878_杜德双 | 杜德双      | 2025-10-01        | 2099-12-31      | 长期休息                  | 工作繁忙，暂停服侍
person_2165_吕晓燕 | 吕晓燕      | 2025-09-15        | 2099-12-31      | 产假                      | 预产期11月，具体恢复时间待定
person_7865_何凯   | 何凯        | 2025-08-01        | 2099-12-31      | 退出服侍                  | 已不在本教会
person_0464_蔡恩奇 | 蔡恩奇      | 2025-10-10        | 2099-12-31      | 身体原因                  | 长期休养
```

**系统行为**：
- ✅ 该同工不会出现在排班建议中
- ✅ 如果已排班，冲突检测会标记为 `error` 级别冲突
- ✅ 在 metadata API 中显示为 `is_available: false`
- ✅ 明确告知 LLM 该同工当前不可用

**恢复服侍时**：
只需更新 `unavailable_end` 为实际的恢复日期，或者清空该字段

---

## 📊 数据格式说明

### 字段定义

| 字段 | 类型 | 必填 | 格式 | 说明 |
|------|------|------|------|------|
| `person_id` | 字符串 | ✅ 是 | `person_xxxx_姓名` | 同工唯一标识 |
| `person_name` | 字符串 | ✅ 是 | 中文姓名 | 显示名称 |
| `unavailable_start` | 日期 | ❌ 否 | `YYYY-MM-DD` | 不可用开始日期 |
| `unavailable_end` | 日期 | ❌ 否 | `YYYY-MM-DD` | 不可用结束日期 |
| `unavailable_reason` | 字符串 | ❌ 否 | 简短说明 | 不可用原因 |
| `notes` | 字符串 | ❌ 否 | 详细说明 | 其他备注信息 |

### 日期格式要求

**正确格式**：
- ✅ `2025-11-01`
- ✅ `2025-12-25`
- ✅ `2099-12-31` （用于长期不可用）

**错误格式**：
- ❌ `11/01/2025`
- ❌ `2025/11/01`
- ❌ `永久` 或 `无限期`（不能用文字）

---

## 🔍 系统如何识别不可用状态

### API 响应示例

#### 1. 临时不可用的同工

```json
{
  "person_id": "person_8101_谢苗",
  "person_name": "谢苗",
  "unavailable_start": "2025-11-01",
  "unavailable_end": "2025-11-15",
  "unavailable_reason": "旅行",
  "is_available": false,  // ← 当前不可用
  "notes": ""
}
```

#### 2. 长期不可用的同工

```json
{
  "person_id": "person_6878_杜德双",
  "person_name": "杜德双",
  "unavailable_start": "2025-10-01",
  "unavailable_end": "2099-12-31",
  "unavailable_reason": "长期休息",
  "is_available": false,  // ← 长期不可用
  "notes": "工作繁忙，暂停服侍"
}
```

#### 3. 可用的同工

```json
{
  "person_id": "person_3850_靖铮",
  "person_name": "靖铮",
  "unavailable_start": "",
  "unavailable_end": "",
  "unavailable_reason": "",
  "is_available": true,   // ← 可用
  "notes": ""
}
```

---

## 🤖 排班建议算法的处理

### 评分系统

当 LLM 请求排班建议时，系统会自动：

1. **检查时间可用性**（`consider_availability: true`）
   ```python
   if is_date_in_range(service_date, unavailable_start, unavailable_end):
       score -= 100  # 不可用，直接排除
       concerns.append(f"时间不可用（{unavailable_reason}）")
   ```

2. **返回建议时排除不可用同工**
   - 分数 ≤ 0 的候选人不会出现在建议列表中
   - LLM 只会看到可用的同工

### 示例：排班建议请求

**请求**：
```json
{
  "service_date": "2025-11-10",
  "required_roles": ["音控", "司琴"],
  "consider_availability": true,
  "consider_family": true,
  "consider_balance": true
}
```

**响应**（已自动排除 11月旅行的谢苗）：
```json
{
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
            "服侍次数适中（6次）"
          ],
          "concerns": []
        }
      ]
    }
  ]
}
```

---

## ⚠️ 冲突检测

### 不可用时间冲突

如果某个同工在不可用期间被安排服侍，系统会自动检测：

**冲突示例**：
```json
{
  "type": "unavailability_conflict",
  "severity": "error",
  "week": "2025-11-10",
  "description": "谢苗 在 2025-11-01 到 2025-11-15 期间不可用，但被安排服侍",
  "affected_persons": [
    {
      "person_id": "person_8101_谢苗",
      "person_name": "谢苗",
      "role": "音控",
      "service_date": "2025-11-10"
    }
  ],
  "unavailable_reason": "旅行",
  "suggestion": "需要重新安排其他人"
}
```

---

## 📝 实际操作步骤

### 步骤1：打开 Google Sheets

```
https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit
```

找到 `VolunteerMetadata` sheet

### 步骤2：找到对应的同工行

使用 `Ctrl+F`（Windows）或 `Cmd+F`（Mac）搜索同工姓名

### 步骤3：填写不可用信息

#### 临时不可用示例：
| unavailable_start | unavailable_end | unavailable_reason | notes |
|-------------------|-----------------|---------------------|-------|
| 2025-11-01 | 2025-11-15 | 旅行 | |

#### 长期不可用示例：
| unavailable_start | unavailable_end | unavailable_reason | notes |
|-------------------|-----------------|---------------------|-------|
| 2025-10-01 | 2099-12-31 | 长期休息 | 工作繁忙，暂停服侍 |

### 步骤4：验证数据

使用 API 验证：
```bash
curl "http://localhost:8080/api/v1/volunteer/metadata?person_id=person_8101_谢苗" | jq '.volunteers[0].is_available'
```

应该返回 `false`

---

## 🔄 常见场景处理

### 场景1：同工提前通知下月不能服侍

**处理**：
1. 在 Google Sheets 中找到该同工
2. 填写 `unavailable_start` 和 `unavailable_end`
3. 填写 `unavailable_reason`（如"旅行"）
4. 运行冲突检测，检查是否已安排
   ```bash
   curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
     -H "Content-Type: application/json" \
     -d '{"year_month": "2025-11", "check_availability": true}'
   ```

### 场景2：同工突然生病，需要长期休息

**处理**：
1. 设置 `unavailable_start` 为当前日期
2. 设置 `unavailable_end` 为 `2099-12-31`
3. 填写 `unavailable_reason`（如"身体原因"）
4. 在 `notes` 中添加详细说明
5. 检测冲突并重新安排

### 场景3：同工休息后恢复服侍

**处理方法1**（推荐）：
- 更新 `unavailable_end` 为实际恢复日期
- 例如：从 `2099-12-31` 改为 `2025-12-15`

**处理方法2**：
- 清空 `unavailable_start` 和 `unavailable_end`
- 清空 `unavailable_reason`
- 在 `notes` 中记录恢复时间

### 场景4：同工多个时间段不可用

**方法1**（推荐）：只填写最近/最长的不可用期
```
unavailable_start: 2025-11-01
unavailable_end: 2025-11-15
unavailable_reason: 旅行
notes: 另外12月20-25日也不可用（圣诞节）
```

**方法2**：使用脚本添加多条记录（高级用法）
```bash
# 添加第一个不可用期
curl -X POST http://localhost:8080/api/v1/volunteer/metadata \
  -d '{"person_id": "person_8101_谢苗", ...}'

# 需要后续实现多时间段支持
```

---

## 💡 最佳实践

### ✅ 推荐做法

1. **及时更新**: 同工通知不可用时间后，立即更新 metadata
2. **明确原因**: 填写清晰的 `unavailable_reason`，便于后续查询
3. **使用备注**: 在 `notes` 中添加详细说明和恢复计划
4. **定期检查**: 每月检查长期不可用的同工，更新恢复日期
5. **运行冲突检测**: 更新后立即运行冲突检测

### ❌ 避免做法

1. ❌ 不要使用文字表示日期（如"下周"、"永久"）
2. ❌ 不要留空 `unavailable_reason`
3. ❌ 不要忘记更新恢复后的状态
4. ❌ 不要直接删除同工记录（应该标记为不可用）

---

## 🧪 测试验证

### 测试1：验证不可用状态

```bash
# 获取所有不可用的同工
curl "http://localhost:8080/api/v1/volunteer/metadata" | \
  jq '.volunteers[] | select(.is_available == false) | {person_name, unavailable_reason}'
```

### 测试2：验证排班建议已排除

```bash
# 请求排班建议
curl -X POST http://localhost:8080/api/v1/volunteer/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "service_date": "2025-11-10",
    "required_roles": ["音控"],
    "consider_availability": true
  }' | jq '.suggestions[0].candidates[] | .person_name'

# 不应该出现不可用的同工
```

### 测试3：验证冲突检测

```bash
# 检测冲突
curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
  -H "Content-Type: application/json" \
  -d '{"year_month": "2025-11", "check_availability": true}' | \
  jq '.conflicts[] | select(.type == "unavailability_conflict")'
```

---

## 🎓 LLM 使用指南

当您（LLM）需要为教会安排同工服侍时：

### 1. 查询当前可用的同工
```bash
GET /api/v1/volunteer/metadata
```
关注 `is_available` 字段

### 2. 获取排班建议时
```bash
POST /api/v1/volunteer/suggestions
```
**务必设置**：
```json
{
  "consider_availability": true  // ← 这会自动排除不可用同工
}
```

### 3. 解读响应
- `is_available: false` → 该同工当前不可用，不要推荐
- `concerns` 包含 "时间不可用" → 该同工在指定日期不可用
- `score <= 0` → 该候选人已被自动排除

### 4. 向用户解释
```
例如：
"谢苗在 11月1日至15日期间旅行，因此本次排班建议中没有包含他。
推荐使用明明（分数90）担任音控，因为他时间可用且服侍次数适中。"
```

---

## 📞 技术支持

如有问题，请参考：
- API 文档: `docs/API_ENDPOINTS.md`
- 设置指南: `VOLUNTEER_METADATA_SETUP_GUIDE.md`
- 完整报告: `VOLUNTEER_METADATA_FINAL_REPORT.md`

---

**文档版本**: v1.0  
**最后更新**: 2025-10-07

