# 实现任务清单 — 2026-09-25-guard-phase-path-scope

> mode: standard | task_type: code
> 目标文件：`upstream/fstdd/cli/commands/guard.py`、`upstream/tests/commands/test_guard.py`
>
> **追溯补记声明**：本 change 的代码与测试于 2026-09-25 落地（提交 `4eec636`），其后
> change 记录长期停留 `build/in_progress`（缺 tasks.md / test-report.md、`traceability`
> 恒为 0、无 Gate 3），被 `fstdd status` 判为僵尸 change。2026-10-04 依 CHANGELOG
> §[3.3.1] 既定政策「待其 BUILD 完成后各自 DELIVER」补全记录并收口。
> **本文件为收口时追溯重建**，条目均以仓库既有证据（提交 / 测试类 / 实跑结果）为准，
> 未虚构任何未发生的步骤；新增的 2 处 P0 变体测试（S3）为本次补全，已实跑取证。

## 切片 S1：作用域声明读取与命中判定（P0 / REQ-001、REQ-004）

- [x] T1.1 `_load_change_scope(change_dir)`：读 `canonical/proposals/*.yaml` 的 `scope.paths`
- [x] T1.2 无 `scope` 块 / `paths` 为空 / 无 proposal / YAML 不可解析 ⇒ 一律 `None`（fail-closed）
- [x] T1.3 `_is_in_change_scope(project_root, file_path, patterns)`：先 `normpath` 归一化再 `fnmatch` 匹配
- [x] T1.4 目录模式（`/` 结尾）匹配其下全部文件；`..` 穿越越界 ⇒ 范围外

## 切片 S2：判定序接入 `cmd_guard_check`（P0 / REQ-002、REQ-003、REQ-005）

- [x] T2.1 两道硬阻断（GATE token / `.fstdd.yaml` 确认字段）与 agent runtime 豁免**保持在作用域判定之前**
- [x] T2.2 只读相位 + 已声明 scope：范围内 ⇒ `exit 2` 并提示扩展 `scope.paths`
- [x] T2.3 只读相位 + 已声明 scope：范围外 ⇒ warn-only（含目标路径与 `out of scope`）`exit 0`
- [x] T2.4 只读相位 + 未声明 scope ⇒ 维持既有全局拦截（行为零漂移）
- [x] T2.5 作用域变量在函数级预置默认值（消除无 active change 时 `UnboundLocalError` fail-open）

## 切片 S3：回归测试（P0 / SC-001..SC-010）

- [x] T3.1 `TestGuardChangeScope`：`_load_change_scope` 判定矩阵（TC-SCOPE-001/002）
- [x] T3.2 `TestGuardChangeScope`：`_is_in_change_scope` 命中矩阵（TC-SCOPE-003/004/005/010）
- [x] T3.3 `TestGuardChangeScope`：`cmd_guard_check` 判定序与退出码（TC-SCOPE-006..009/011/012）
- [x] T3.4 **补全（2026-10-04）** SC-005 变体：已声明 scope 时 `.fstdd.yaml` 确认字段仍硬阻断（TC-SCOPE-013）
- [x] T3.5 **补全（2026-10-04）** SC-010 变体：已声明 scope 时 `.workbuddy-ai/` 豁免不被覆盖（TC-SCOPE-014）

## 切片 S4：全量回归与收口（P0 / TC-SCOPE-015）

- [x] T4.1 `pytest upstream/tests/commands/test_guard.py -q` 全绿（14/14 scope 用例）
- [x] T4.2 全量 `pytest upstream/tests -q` 0 failed
- [x] T4.3 四自检脚本全绿
- [x] T4.4 回填 `.fstdd.yaml` 的 `traceability`（spec_scenarios / tc_cases / test_functions）
