# v3.4.0 增量 — contract_gap 回归测试方案

> 版本: v3.4.0 增量（EXP-0027/0031/0032 回归测试加固）
> 创建日期: 2026-10-27
> 对应 Phase 2 Spec: `specs/contract-gap-regression-tests/spec.md`
> Change: 2026-10-27-contract-gap-regression-tests

## 一、测试策略

### 1.1 测试金字塔

| 层级 | 用例数 | 比例 | 侧重点 |
|------|-------|------|--------|
| 单元 | 9 | 100% | `_resolve_in` 输入拒绝 + archive 守卫归一化 + (?i) 扫描 |

### 1.2 测试原则

- **攻击向量成对断言**：每个反例（逃逸形态）配一个正例（合法形态必须放行），避免收紧后误拒。
- **不修改生产代码**：本 change 只加测试，不改 `finder.py` / `ci.py`。若测试暴露回归，说明代码修复本身有问题，另行处理。
- **参数化覆盖边界**：`..`、绝对路径、跨盘符、Unicode 分隔符、空字符串、`.` 全部参数化。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---------|-------|------|---------|
| `tests/test_contract_gap_regression.py` | 9 | 单元 | EXP-0027/0031/0032 攻击向量 |

## 二、详细测试案例

### 功能 A：`_resolve_in` 输入层拒绝逃逸（EXP-2026-0032）

对应 spec Requirement: `_resolve_in` 输入层拒绝逃逸

#### 案例 A.1 — 拒绝含路径分隔符的 name

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-001 |
| **对应 Spec** | spec.md → Scenario: 拒绝包含路径分隔符的 name |
| **优先级** | P0 |
| **预置条件** | GIVEN base_dir = tmp_path 且含合法 change 子目录 `foo-bar/.fstdd.yaml` |
| **输入** | WHEN 调用 `_resolve_in(base_dir, "foo/bar")` 与 `_resolve_in(base_dir, "foo\\bar")` |
| **预期结果** | THEN SHALL 返回 None AND SHALL NOT 抛出异常 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 A.2 — 拒绝 `..` 与 `.` 逃逸

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-002 |
| **对应 Spec** | spec.md → Scenario: 拒绝包含 `..` 的 name |
| **优先级** | P0 |
| **预置条件** | GIVEN base_dir = tmp_path |
| **输入** | WHEN 分别调用 `_resolve_in(base_dir, "..")`、`"../bar"`、`"foo/.."`、`"foo/../bar"` |
| **预期结果** | THEN SHALL 全部返回 None AND 无一逃逸出 base_dir |
| **当前状态** | ✅ 已覆盖 |

#### 案例 A.3 — 拒绝空 name

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-003 |
| **对应 Spec** | spec.md → Scenario: 拒绝空 name 与 `.` |
| **优先级** | P1 |
| **预置条件** | GIVEN base_dir = tmp_path |
| **输入** | WHEN 分别调用 `_resolve_in(base_dir, "")`、`"."` |
| **预期结果** | THEN SHALL 全部返回 None |
| **当前状态** | ✅ 已覆盖 |

#### 案例 A.4 — 正例：合法 change 名必须放行

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-004 |
| **对应 Spec** | spec.md → Scenario: 允许合法 change 名 |
| **优先级** | P0 |
| **预置条件** | GIVEN base_dir 下有 `foo-bar-2026-10-27/.fstdd.yaml` |
| **输入** | WHEN 调用 `_resolve_in(base_dir, "foo-bar-2026-10-27")` |
| **预期结果** | THEN SHALL 返回该目录 Path 对象 AND NOT 返回 None |
| **当前状态** | ✅ 已覆盖 |

### 功能 B：archive 守卫使用 `resolve()` 归一化判定（EXP-2026-0027）

对应 spec Requirement: archive 守卫使用 `resolve()` 归一化判定

#### 案例 B.1 — archive 下的路径被识别为归档态

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-005 |
| **对应 Spec** | spec.md → Scenario: archive 目录下的路径被识别为归档态 |
| **优先级** | P0 |
| **预置条件** | GIVEN hit = tmp/archive/some-change（真归档路径） |
| **输入** | WHEN 执行 `hit.resolve().relative_to(archive_root.resolve())` |
| **预期结果** | THEN SHALL NOT 抛出 ValueError AND 判定为归档态 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 B.2 — changes 下的路径被识别为在办态

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-006 |
| **对应 Spec** | spec.md → Scenario: changes 目录下的路径被识别为在办 |
| **优先级** | P0 |
| **预置条件** | GIVEN hit = tmp/changes/some-change（在办路径） |
| **输入** | WHEN 执行 `hit.resolve().relative_to(archive_root.resolve())` |
| **预期结果** | THEN SHALL 抛出 ValueError AND 判定为在办态 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 B.3 — 词法陷阱：`..` 组合不能逃逸守卫

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-007 |
| **对应 Spec** | spec.md → Requirement 说明「必须归一化」 |
| **优先级** | P1 |
| **预置条件** | GIVEN hit 表面上路径含 `changes/../archive/some-change`（词法看起来在 archive 外） |
| **输入** | WHEN 执行 `hit.resolve().relative_to(archive_root.resolve())` |
| **预期结果** | THEN SHALL NOT 抛出 ValueError AND 判定为归档态（真实路径才是判定依据） |
| **当前状态** | ✅ 已覆盖 |

### 功能 C：全仓无内联 `(?i)` 拼接 regex（EXP-2026-0031）

对应 spec Requirement: 全仓无内联 `(?i)` 拼接 regex

#### 案例 C.1 — 扫描全仓 (?i) 残留为 0

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-008 |
| **对应 Spec** | spec.md → Scenario: 扫描全仓 (?i) 残留 |
| **优先级** | P0 |
| **预置条件** | GIVEN upstream/fstdd/**/*.py 剔除 __pycache__ |
| **输入** | WHEN 遍历每个 .py 文件，用 `re.search(r'\(\?i\)', source)` 扫描 |
| **预期结果** | THEN SHALL 匹配总数为 0 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 C.2 — 内联 (?i) 在拼接中会崩溃（回归证明）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CGR-009 |
| **对应 Spec** | spec.md → Scenario: 模块 import 不崩溃 |
| **优先级** | P1 |
| **预置条件** | GIVEN 一段拼接字符串 `"(?i)" + r"foo"` |
| **输入** | WHEN 尝试 `re.compile(pattern)` |
| **预期结果** | THEN SHALL 抛出 `re.PatternError` AND 异常消息含 "global flags not at the start" |
| **当前状态** | ✅ 已覆盖 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|---------|-----|------|
| `_resolve_in` 输入拒绝（EXP-0032） | 4 用例 | - | - | 🟢 |
| archive 守卫归一化（EXP-0027） | 3 用例 | - | - | 🟢 |
| (?i) 拼接扫描（EXP-0031） | 2 用例 | - | - | 🟢 |

## 四、回归风险矩阵

| 风险区域 | V3.4.0 改动 | 已有回归保护 | 风险等级 |
|---------|------------|-------------|---------|
| `_resolve_in` 输入拒绝 | 无代码改动 | TC-CGR-001/002/003/004 | 🟢 |
| archive 守卫归一化 | 无代码改动 | TC-CGR-005/006/007 | 🟢 |
| (?i) 内联拼接 | 无代码改动 | TC-CGR-008/009 | 🟢 |

## 五、建议补充顺序

1. **第一优先（部署前必补）**：全部 9 个用例（P0 + P1 混合）
2. **第二优先（部署后）**：为 `ci check-failures` 加一条 grep 门禁（本 change 明确 out_of_scope）
3. **第三优先（后续）**：把 EXP-0024/0026 描述的"审计器假阴性"纳入新 change

## 六、证据记录

| 证据 | observed_at | observed_base_git_sha | 来源 |
|------|-------------|----------------------|------|
| 全仓 `(?i)` 扫描 0 匹配 | 2026-10-27T10:45:00+08:00 | 5c5c40d | `grep -rn '(?i)' upstream/fstdd/ --include=*.py \| wc -l` → 0 |
| `relative_to` 未 `resolve()` 处 18 个均为显示用途 | 2026-10-27T10:45:00+08:00 | 5c5c40d | `grep -rn '\.relative_to(' upstream/fstdd/ ...` 剔除 `resolve().relative_to` |
| 9/9 TDD 用例全绿 | 2026-10-27T10:50:00+08:00 | 5c5c40d | `pytest tests/test_contract_gap_regression.py -v` |
| ci check-failures 门禁 0 FAIL | 2026-10-27T10:52:00+08:00 | 5c5c40d | `python -m fstdd ci check-failures ...` |

## 七、金融 10 维测试覆盖

> FINANCIAL_PROJECT=NO（本 change 不涉及金融业务逻辑）—— 章节跳过。
