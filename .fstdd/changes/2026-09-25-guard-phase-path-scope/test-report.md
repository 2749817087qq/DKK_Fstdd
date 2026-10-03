# 2026-09-25-guard-phase-path-scope 测试报告

> 测试日期：2026-10-04（收口实跑）｜实现落地：2026-09-25（提交 `4eec636`）
> 测试环境：Windows / Python 3.13.14（workbuddy default env）/ PyYAML 6.0.3 / pytest / git 2.x
> 基线：`df3b27cace3b28c6762932ef03638217024c2dae`（Gate 1 建基线时）
> **追溯补记声明**：本 change 的代码与测试于 2026-09-25 落地，但记录长期停留 `build/in_progress`
> （无 tasks.md / test-report.md、traceability 恒 0、无 Gate 3），被 `fstdd status` 判为僵尸 change。
> 本报告为 2026-10-04 收口时**按实况重建**，数据取自仓库既有测试与本次实跑，非虚构。

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 本变更 TC 数 | 14（TC-SCOPE-001..014，其中 013/014 为收口补全） |
| 覆盖 SC | SC-001..SC-010（全覆盖） |
| 新增测试类 | 1（`upstream/tests/commands/test_guard.py::TestGuardChangeScope`，14 用例） |
| 收口补测试 | 2（SC-005 变体、SC-010 变体，P0） |
| 全量回归（`upstream/tests`） | **887 passed, 54 skipped, 0 failed** |
| guard 单文件 | 51 → **53 passed**（含 `TestGuardChangeScope` 14/14） |
| 四自检脚本 | verify_rename / verify_eol / verify_skill_standards / verify_workbuddy_skills |

## 二、按模块统计

| 测试模块 | 关键用例 | 结果 | 说明 |
|----------|----------|------|------|
| `test_guard.py::TestGuardChangeScope` | `test_tc_scope_001_loads_declared_paths` | ✅ | TC-SCOPE-001：声明 scope 时返回路径列表（SC-001 前置） |
| 同上 | `test_tc_scope_002_returns_none_when_not_declared` | ✅ | TC-SCOPE-002：无 scope / 空列表 / 无 proposal ⇒ None（SC-003） |
| 同上 | `test_tc_scope_003_exact_file_in_scope` | ✅ | TC-SCOPE-003：精确文件命中（SC-001） |
| 同上 | `test_tc_scope_004_directory_pattern_matches_descendants` | ✅ | TC-SCOPE-005：目录模式匹配子文件（SC-007） |
| 同上 | `test_tc_scope_005_out_of_scope_is_false` | ✅ | TC-SCOPE-004：范围外判 False（SC-002） |
| 同上 | `test_tc_scope_010_dotdot_normalized_before_matching` | ✅ | TC-SCOPE-006：`..` 先归一化再判定（SC-006） |
| 同上 | `test_tc_scope_006_in_scope_blocks_in_readonly` | ✅ | TC-SCOPE-003：只读相位范围内 ⇒ exit 2 + 提示扩展 scope（SC-001） |
| 同上 | `test_tc_scope_007_out_of_scope_warns_and_allows` | ✅ | TC-SCOPE-004：范围外 ⇒ exit 0 + `out of scope`（SC-002） |
| 同上 | `test_tc_scope_008_no_scope_declared_keeps_global_block` | ✅ | TC-SCOPE-002：未声明 ⇒ 全局拦截零漂移（SC-003） |
| 同上 | `test_tc_scope_009_gate_token_still_blocked` | ✅ | TC-SCOPE-007：GATE token 硬阻断优先（SC-004） |
| 同上 | `test_tc_scope_011_yaml_first_artifact_still_allowed` | ✅ | TC-SCOPE-010：YAML-first 产物放行不变（SC-008） |
| 同上 | `test_tc_scope_012_editable_phase_ignores_scope` | ✅ | TC-SCOPE-009：可编辑相位不受 scope 影响（SC-009） |
| 同上 | `test_tc_scope_013_state_confirmation_still_blocked` | ✅ | TC-SCOPE-008：已声明 scope 时 `.fstdd.yaml` 确认字段仍硬阻断（SC-005，**本次补**） |
| 同上 | `test_tc_scope_014_agent_runtime_exempt_ignores_scope` | ✅ | TC-SCOPE-011：已声明 scope 时 agent runtime 豁免不被覆盖（SC-010，**本次补**） |

## 三、工具级验证（发布门禁证据）

| 命令 | 结果 |
|------|------|
| `python -m pytest upstream/tests -q` | `887 passed, 54 skipped, 0 failed`（退出码 0） |
| `python -m pytest upstream/tests/commands/test_guard.py -q` | `53 passed` |
| `python -m pytest upstream/tests/commands/test_guard.py::TestGuardChangeScope -q` | `14 passed` |
| `fstdd validate 2026-09-25-guard-phase-path-scope` | 0 error / 1 warning（`spec.md: 未找到 Scenario`，既有约定固定代价，见 `audit/traceability-notes.md`） |
| `python tools/verify_rename.py` | 通过 |
| `python tools/verify_eol.py --repo .` | 通过 |
| `python tools/verify_skill_standards.py` | 通过 |
| `python tools/verify_workbuddy_skills.py` | 通过 |

## 四、失败项详细分析

无。全量回归 0 failed；`TestGuardChangeScope` 14/14 通过。

## 五、功能/测试覆盖对照

| 功能模块 | 涉及文件 | 测试覆盖 | 缺失测试 |
|----------|----------|----------|----------|
| 作用域声明读取 | `guard.py::_load_change_scope` | TC-SCOPE-001/002 | 无 |
| 作用域命中判定 | `guard.py::_is_in_change_scope` | TC-SCOPE-003/004/005/006 | 无 |
| 判定序（硬阻断/豁免前置） | `guard.py::cmd_guard_check` | TC-SCOPE-007..014 | 无 |
| 回归（既有硬阻断/豁免） | `test_guard.py`（既有 20 用例） | 全绿 | 无 |

## 六、设计调整说明

**0 项大偏离 / 0 项小偏离**（见 `design-adjustments.md`）。收口补的 2 处测试属计划内既有 P0 要求，非偏离。

## 七、C4 失败模式检查（摘要）

| # | 失败模式 | 结果 | 证据 / 处置 |
|---|----------|------|-------------|
| 7 | 安全凭证泄露 | ✅ | 本变更为门禁逻辑，不涉凭证；全仓凭证形态门禁见 `2026-10-04-github-mirror-secret-remediation` |
| 8 | 权限绕过 | ✅ | 硬阻断/豁免判定序有 TC-SCOPE-009/013/014 锁定，未被 scope 收窄短路 |
| 11 | 跨会话残留 | ✅ | 收口补齐记录，无临时产物遗留 |
| 17 | 静默降级 | ✅ | 范围外为 **warn-only**（带目标路径与 `out of scope`），非静默放行 |
| 12 | 审计缺口 | ✅ | 审计活表（except-points）与哨兵一致，`test_guard_silent_except.py` 全绿 |
| 19 | 过度工程 | ✅ | 复用既有 `fnmatch`/`yaml`，未引入新依赖或抽象层 |
| — | 其余（资金/账本类） | n/a | 本变更无相关语义 |

## 八、已知问题与未完成项

| 项 | 名称 | 原因 | 影响 | 处置 |
|---|---|---|---|---|
| 1 | `traceability` 长期为 0 | `phase advance` 未回写计数（CLI 缺陷 #2，见 `audit/traceability-notes.md`） | 记录统计不准 | 收口时按实况回填 `.fstdd.yaml` |
| 2 | 旧修订 `guard.py` 副本 | 本机存在 40,082 B 无豁免逻辑副本（`patchtest` / `FSTDD004` 内嵌仓） | 豁免面不一致（排查任务 W5.3） | 独立立项，不混入本 change |

## 九、结论

**可进入 Gate 3。** `TestGuardChangeScope` 14/14 通过；全量 `upstream/tests` **887 passed / 54 skipped / 0 failed**；
四自检脚本全绿；SC-001..SC-010 全覆盖。风险等级：**低**。
本 change 代码已随 V3.0.7 上线，本次为**记录侧收口**（补 tasks/test-report/design-adjustments + Gate 3 + DELIVER）。
