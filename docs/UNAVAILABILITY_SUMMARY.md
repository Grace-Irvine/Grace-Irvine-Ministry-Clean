# 同工不可用时间标注 - 功能说明

## ✅ 已验证功能

系统已完全支持两种不可用情况的标注和自动处理。

---

## 📋 两种情况的标注方法

### 情况1：临时不可用（有明确结束日期）

**适用**：短期旅行、出差、培训等有明确恢复日期的情况

**标注示例**：
```
person_id:          person_8101_谢苗
person_name:        谢苗
unavailable_start:  2025-11-01
unavailable_end:    2025-11-15
unavailable_reason: 旅行
notes:              (可选)
```

**系统行为**：
- ✅ 在 2025-11-01 至 2025-11-15 期间，排班建议会自动排除该同工
- ✅ 11月16日后自动恢复可用状态
- ✅ `is_available` 字段根据当前日期自动计算

---

### 情况2：长期/无限期不可用

**适用**：长期生病、工作繁忙、暂停服侍、退出团队等无明确恢复日期的情况

**标注示例**：
```
person_id:          person_6878_杜德双
person_name:        杜德双
unavailable_start:  2025-10-01
unavailable_end:    2099-12-31        ← 使用远期日期
unavailable_reason: 长期休息
notes:              工作繁忙，暂停服侍，恢复时间未定
```

**系统行为**：
- ✅ 在所有排班建议中永久排除该同工（直到手动更新）
- ✅ `is_available` 显示为 `false`
- ✅ LLM 能够清楚识别该同工长期不可用

---

## 🧪 验证测试

### 测试1：临时不可用
```bash
# 谢苗在 11月1-15日 旅行
# 查询 11月10日 的排班建议
curl -X POST http://localhost:8080/api/v1/volunteer/suggestions \
  -d '{"service_date": "2025-11-10", "required_roles": ["音控"], "consider_availability": true}'

# 结果：✓ 谢苗已被排除
```

### 测试2：长期不可用
```bash
# 杜德双长期休息（2099-12-31）
# 查询任意日期的排班建议
curl -X POST http://localhost:8080/api/v1/volunteer/suggestions \
  -d '{"service_date": "2025-12-25", "required_roles": ["司琴"], "consider_availability": true}'

# 结果：✓ 杜德双已被排除
```

### 测试3：元数据查询
```bash
# 查看所有不可用的同工
curl http://localhost:8080/api/v1/volunteer/metadata | \
  jq '.volunteers[] | select(.is_available == false)'

# 结果：显示所有长期不可用的同工
```

---

## 🤖 LLM 使用说明

### 如何让 LLM 识别不可用状态

**1. 在请求排班建议时，务必设置：**
```json
{
  "service_date": "2025-11-10",
  "required_roles": ["音控", "司琴"],
  "consider_availability": true  // ← 必须为 true
}
```

**2. 系统会自动：**
- 检查每个同工在指定日期是否可用
- 不可用的同工评分直接 -100（排除）
- 在 `concerns` 中说明不可用原因

**3. LLM 响应示例：**
```json
{
  "person_id": "person_8101_谢苗",
  "person_name": "谢苗",
  "score": -50,  // ← 分数为负，不会出现在建议中
  "concerns": [
    "时间不可用（旅行）"  // ← 明确告知原因
  ]
}
```

**4. 向用户解释时：**
```
"谢苗在 11月1日至15日期间旅行，因此无法参与本次服侍。
系统已自动排除他，并推荐明明作为替代人选。"
```

---

## 📝 Google Sheets 填写说明

### 在哪里填写

1. 打开 Google Sheets：
   ```
   https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit
   ```

2. 找到 `VolunteerMetadata` sheet

3. 找到对应同工的行（按 `Ctrl+F` 搜索姓名）

4. 填写以下列：

| 列名 | 临时不可用 | 长期不可用 |
|------|-----------|-----------|
| `unavailable_start` | 实际开始日期 | 当前日期 |
| `unavailable_end` | 实际结束日期 | `2099-12-31` |
| `unavailable_reason` | 简短原因（旅行） | 简短原因（长期休息） |
| `notes` | (可选) | 详细说明和恢复计划 |

### 日期格式

**✅ 正确格式**：
- `2025-11-01`
- `2025-12-25`
- `2099-12-31`

**❌ 错误格式**：
- `11/01/2025`（不支持）
- `2025/11/01`（不支持）
- `永久`（不能用文字）

---

## 🔄 恢复服侍

当同工恢复服侍时：

### 方法1：更新结束日期（推荐）
```
unavailable_end: 2099-12-31  →  2025-12-15
```

### 方法2：清空字段
```
unavailable_start: (清空)
unavailable_end:   (清空)
unavailable_reason: (清空)
notes: 已于2025-12-15恢复服侍
```

---

## 💡 最佳实践

### ✅ 推荐做法

1. **及时更新**：同工通知不可用后立即更新
2. **明确原因**：填写清晰的 `unavailable_reason`
3. **详细备注**：长期不可用在 `notes` 中说明详情
4. **定期检查**：每月检查长期不可用的同工
5. **运行验证**：更新后运行冲突检测

### ❌ 避免做法

1. ❌ 使用文字日期（"下周"、"永久"）
2. ❌ 留空 `unavailable_reason`
3. ❌ 忘记更新恢复后的状态
4. ❌ 直接删除同工记录

---

## 🎯 常见场景

### 场景1：同工提前1个月通知旅行
```
unavailable_start: 2025-11-01
unavailable_end:   2025-11-15
reason:           旅行
```

### 场景2：同工突然生病，恢复时间未定
```
unavailable_start: 2025-10-07
unavailable_end:   2099-12-31
reason:           身体原因
notes:            长期休养，恢复时间待定
```

### 场景3：同工工作繁忙，暂停服侍
```
unavailable_start: 2025-10-01
unavailable_end:   2099-12-31
reason:           工作原因
notes:            工作繁忙，暂停服侍，明年再评估
```

### 场景4：同工产假
```
unavailable_start: 2025-11-01
unavailable_end:   2099-12-31
reason:           产假
notes:            预产期11月，产后3-6个月恢复
```

### 场景5：同工离开教会
```
unavailable_start: 2025-08-01
unavailable_end:   2099-12-31
reason:           退出服侍
notes:            已不在本教会
```

---

## 📚 相关文档

- **完整指南**：`docs/UNAVAILABILITY_GUIDE.md`（包含详细的 API 说明、测试方法等）
- **快速参考**：`UNAVAILABILITY_QUICK_REF.md`（速查表）
- **API 文档**：`docs/API_ENDPOINTS.md`
- **设置指南**：`VOLUNTEER_METADATA_SETUP_GUIDE.md`

---

## 🚀 快速开始

```bash
# 1. 在 Google Sheets 中填写不可用信息
# 2. 验证数据
curl "http://localhost:8080/api/v1/volunteer/metadata?person_id=person_8101_谢苗" | jq

# 3. 测试排班建议
curl -X POST http://localhost:8080/api/v1/volunteer/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "service_date": "2025-11-10",
    "required_roles": ["音控"],
    "consider_availability": true
  }' | jq

# 4. 运行冲突检测
curl -X POST http://localhost:8080/api/v1/volunteer/conflicts \
  -H "Content-Type: application/json" \
  -d '{"year_month": "2025-11", "check_availability": true}' | jq
```

---

**文档版本**: v1.0  
**功能状态**: ✅ 已测试并验证  
**最后更新**: 2025-10-07

