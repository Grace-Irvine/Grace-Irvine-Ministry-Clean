# Google Sheets 设置指南

## 📋 Sheet: VolunteerMetadata

### 步骤 1: 创建新 Sheet

1. 打开 Google Sheets: https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit?gid=900093610#gid=900093610

2. 点击底部的 "+" 按钮创建新 Sheet

3. 重命名为：`VolunteerMetadata`

---

### 步骤 2: 添加表头

在第一行添加以下列名（A1-H1）：

```
person_id | person_name | family_group | unavailable_start | unavailable_end | unavailable_reason | notes | updated_at
```

**详细说明**：

| 列 | 列名 | 类型 | 说明 | 是否必填 |
|----|------|------|------|---------|
| A | person_id | string | 人员唯一ID（如 person_8101_谢苗） | ✅ 必填 |
| B | person_name | string | 显示名称（如 谢苗） | ✅ 必填 |
| C | family_group | string | 家庭组ID（如 family_xie_qu）<br>同组成员不能在同一周服侍 | ❌ 可选 |
| D | unavailable_start | date | 不可用开始日期（YYYY-MM-DD） | ❌ 可选 |
| E | unavailable_end | date | 不可用结束日期（YYYY-MM-DD） | ❌ 可选 |
| F | unavailable_reason | string | 不可用原因（如：旅行、回国探亲） | ❌ 可选 |
| G | notes | string | 其他备注（如：优先安排早场） | ❌ 可选 |
| H | updated_at | date | 更新时间（YYYY-MM-DD） | ❌ 可选 |

---

### 步骤 3: 添加示例数据

从第2行开始，添加以下示例数据：

#### 示例 1: 夫妻/家庭成员

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

#### 示例 2: 长期不可用

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

#### 示例 3: 多段不可用（需要多行）

```
A5: person_6878_杜德双
B5: 杜德双
C5: 
D5: 2024-10-15
E5: 2024-10-20
F5: 出差
G5: 优先技术岗
H5: 2024-10-07
```

```
A6: person_6878_杜德双
B6: 杜德双
C6: 
D6: 2024-11-10
E6: 2024-11-12
F6: 参加会议
G6: 优先技术岗
H6: 2024-10-07
```

---

### 步骤 4: 格式化建议

1. **第一行（表头）**：
   - 加粗
   - 背景色设为浅灰色
   - 冻结第一行（视图 > 冻结 > 1行）

2. **日期列（D、E、H）**：
   - 选中列 D、E、H
   - 格式 > 数字 > 自定义日期格式
   - 输入：`yyyy-mm-dd`

3. **条件格式（可选）**：
   - 选中 D2:E100
   - 格式 > 条件格式
   - 设置规则：如果日期 <= 今天，背景色设为浅红色（表示已过期）

---

### 步骤 5: 数据验证（可选但推荐）

#### A列（person_id）验证
- 选中 A2:A1000
- 数据 > 数据验证
- 条件：文本包含 "person_"
- 拒绝输入时：显示警告信息 "person_id 必须以 person_ 开头"

#### D、E列（日期）验证
- 选中 D2:E1000
- 数据 > 数据验证
- 条件：日期
- 允许：有效日期

---

## 📊 完整的数据示例表

| person_id | person_name | family_group | unavailable_start | unavailable_end | unavailable_reason | notes | updated_at |
|-----------|-------------|--------------|-------------------|-----------------|-------------------|--------|------------|
| person_8101_谢苗 | 谢苗 | family_xie_qu | 2024-11-01 | 2024-11-15 | 旅行 | 优先安排早场 | 2024-10-07 |
| person_9017_屈小煊 | 屈小煊 | family_xie_qu | | | | 与谢苗是夫妻 | 2024-10-07 |
| person_3850_靖铮 | 靖铮 | | 2024-12-20 | 2024-12-31 | 回国探亲 | 擅长音控 | 2024-10-07 |
| person_6878_杜德双 | 杜德双 | | 2024-10-15 | 2024-10-20 | 出差 | 优先技术岗 | 2024-10-07 |
| person_6878_杜德双 | 杜德双 | | 2024-11-10 | 2024-11-12 | 参加会议 | 优先技术岗 | 2024-10-07 |
| person_2012_俊鑫 | 俊鑫 | | | | | 擅长视频导播 | 2024-10-07 |
| person_huayaxi | 华亚西 | | | | | 优先敬拜 | 2024-10-07 |

---

## 🔐 步骤 6: 权限设置

1. **点击右上角 "共享" 按钮**

2. **添加服务账号邮箱**（与 alias 表相同的服务账号）
   - 格式：`your-service-account@your-project.iam.gserviceaccount.com`
   - 权限：**编辑者**

3. **保存**

---

## 🎯 family_group 命名规范

为了方便管理，建议使用统一的命名规范：

| 格式 | 示例 | 说明 |
|------|------|------|
| family_{姓氏}_{姓氏} | family_xie_qu | 夫妻：谢苗 & 屈小煊 |
| family_{姓氏} | family_du | 家庭：杜德双、杜XX |
| family_{自定义} | family_smith | 外国姓氏 |

**重要规则**：
- 同一 family_group 的成员不能在同一周服侍
- 一个人只能属于一个 family_group
- 如果有多段不可用时间，可以添加多行（person_id 和 family_group 保持一致）

---

## 📝 维护指南

### 添加新同工
1. 在新行填入 person_id（与系统中一致）
2. 填入 person_name
3. 如有家庭成员，填入相同的 family_group
4. 更新 updated_at

### 更新不可用时间
1. 找到对应的 person_id
2. 更新 unavailable_start、unavailable_end、unavailable_reason
3. 更新 updated_at

### 添加多段不可用时间
1. 添加新行，使用相同的 person_id 和 person_name
2. 填入新的时间段
3. 更新 updated_at

### 删除过期数据
- 定期清理已过期的不可用时间段
- 或保留用于历史记录分析

---

## ✅ 完成检查清单

- [ ] 创建了 VolunteerMetadata Sheet
- [ ] 添加了正确的表头（A1-H1）
- [ ] 添加了示例数据
- [ ] 设置了日期格式（yyyy-mm-dd）
- [ ] 冻结了第一行
- [ ] 添加了服务账号权限
- [ ] 测试了数据读取（运行 API 测试）

---

## 🔗 下一步

完成表格创建后：

1. **更新配置文件** (`config/config.json`)
2. **测试 API 端点**
3. **开始使用 MCP**

详见：`docs/VOLUNTEER_METADATA_ANALYSIS.md`

---

**Sheet URL**: https://docs.google.com/spreadsheets/d/1ypiXsdrfOrWxsAVJxQfZVwA0qtzRzb-siGiV2vixuoc/edit#gid=YOUR_SHEET_GID

