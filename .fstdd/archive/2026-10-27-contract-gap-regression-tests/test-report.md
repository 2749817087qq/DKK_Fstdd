# Phase 3 BUILD 测试报告 — contract_gap 回归测试加固

> Change: 2026-10-27-contract-gap-regression-tests
> 版本: v3.4.0 增量
> 观测基线: git 5c5c40dc6ab506c494714d2f8815ba10e151b854
> 观测时刻: 2026-10-27T10:50:00+08:00

## 一、变更范围

### 已完成修复（0 项 —— 本 change 只加测试）

本 change **不修改生产代码**。3 条经验（EXP-2026-0027/0031/0032）描述的
contract_gap 攻击向量在代码里**已经修复**，本 change 的工作是加回归测试锁定。

### 3 类攻击向量的现有修复位置

| EXP-ID | 修复位置 | 修复形态 |
|--------|---------|---------|
| EXP-2026-0027 | `upstream/fstdd/cli/finder.py:104` | `hit.resolve().relative_to(archive_root.resolve())` 归一化判定 |
| EXP-2026-0031 | 全仓 0 残留（`grep -rn '(?i)' upstream/fstdd/ --include=*.py` → 0） | 使用 `re.compile(pat, re.IGNORECASE)` 参数 |
| EXP-2026-0032 | `upstream/fstdd/cli/finder.py:_resolve_in` | `Path(name).parts` 段级判据 + 拒绝含分隔符的 name |

### 新增测试资产

| 文件 | 用例数 | 类型 | 覆盖 |
|-----|-------|------|------|
| `tests/test_contract_gap_regression.py` | 9 | 单元 | 3 类攻击向量的输入拒绝 + 归一化判定 + 扫描 |

### 生命周期推进

| EXP-ID | 前状态 | 后状态 |
|--------|-------|-------|
| EXP-2026-0027 | discovered | verified |
| EXP-2026-0031 | discovered | verified |
| EXP-2026-0032 | discovered | verified |

## 二、测试结果

### 2.1 单元测试（pytest）

| 指标 | 数值 |
|------|------|
| 测试文件 | `tests/test_contract_gap_regression.py` |
| 用例总数 | 9 |
| 通过 | 9 (100%) |
| 失败 | 0 |
| 执行时间 | 7.29s |
| Python | 3.13.12 |
| pytest | 9.1.1 |

### 2.2 TDD 用例与 TC-ID 对应表

| TC-ID | 用例 | 类型 | 状态 |
|-------|------|------|------|
| TC-CGR-001 | `test_reject_path_separators` | 正常路径（`/` 与 `\\` 分隔符） | ✅ |
| TC-CGR-002 | `test_reject_dotdot_variants` | 正常路径（`..` 逃逸形态 6 种） | ✅ |
| TC-CGR-003 | `test_reject_empty_and_dot` | 边界（空串 / `.`） | ✅ |
| TC-CGR-004 | `test_accepts_valid_change_name` | 回归（正例必须放行） | ✅ |
| TC-CGR-005 | `test_archive_path_is_under_archive` | 正常路径（真归档态） | ✅ |
| TC-CGR-006 | `test_changes_path_is_not_under_archive` | 正常路径（在办态） | ✅ |
| TC-CGR-007 | `test_lexical_dotdot_cannot_escape_guard` | 边界（词法 `..` 陷阱） | ✅ |
| TC-CGR-008 | `test_scan_no_inline_dot_dot_i` | 正常路径（全仓扫描 0 残留） | ✅ |
| TC-CGR-009 | `test_inline_dot_dot_i_in_concatenation_crashes` | 回归（攻击向量真实存在） | ✅ |

## 三、门禁检查（`ci check-failures`）

| 检查项 | 结果 |
|--------|------|
| (a) 必需文件存在 + Spec 存在 | ✅ PASS |
| (b) proposal capability 列表 | ⏭ SKIP（未声明 capability 列表） |
| (d) TC-ID 唯一（按定义点） | ✅ PASS（9 个） |
| (f) THEN 含 SHALL | ✅ PASS |
| (g) AND 数量 | ✅ PASS |
| (j) coverage 覆盖 | ⏭ SKIP（无 coverage.json） |
| (k) capability 契约 | ⏭ SKIP（少于 2 个 capability） |
| (l) canonical proposal 锚定 | ⏭ SKIP |
| TC 实现覆盖 | ✅ PASS（9/9 = 100%） |
| 切片完成记录 | ⏭ SKIP |

**总计**：5 PASS / 0 WARN / 5 SKIP / **0 FAIL**

## 四、已知限制与风险

1. **本 change 未新增 ci check-failures 检查项**：out_of_scope 明确排除。若未来要主动防御 EXP-2026-0031 类回退，需另开 change 加一条 grep 门禁。
2. **`_resolve_in` 的 `Path(name).parts` 判据边界**：`Path("foo\\bar").parts` 在 Windows 上是 `("foo", "bar")`（会识别为含分隔符），在 Unix 上是 `("foo\\bar",)`（不会识别）——测试仅在当前环境验证。
3. **测试 C.1 扫描 `upstream/fstdd/**/*.py` 剔除 `__pycache__`**：若未来 `__pycache__` 被重命名（例如 `.pyc_cache`），扫描会漏扫。当前无风险。

## 五、结论

- **Phase 3 BUILD 完成**：9 TDD 用例全部通过，0 FAIL
- **门禁通过**：5 PASS / 0 WARN / 5 SKIP / 0 FAIL
- **生命周期推进**：3 条经验从 discovered 推进到 verified
- **可进入 Phase 4 DELIVER**
