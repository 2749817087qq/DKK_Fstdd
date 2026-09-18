# detection-silence-fixes 测试方案与详细案例

> 版本：v1
> 创建日期：2026-09-18
> 对应 Phase 2 Spec：`specs/code/detection-voice`、`specs/code/scan-coverage`、`specs/code/audit-errata`

## 一、测试策略

- **先行类型**：每修复点先写「有声」断言（RED），再实现（GREEN）。
- **测试分层**：单元级（capfd 断言 stderr / 返回值）为主；F-1、F-2 必须 CLI 端到端。
- **不变量守卫**：修复不得改变检测阈值（7 天僵尸、24h 滞后、3 文件 50% 占比
  等），既有变异测试（test_mutation_alive.py）全量复跑作为回归锚。
- **哨兵门槛**：审计表刷新后 `tools/audit_silent_except.py --check` 必须通过。

## 二、测试案例

### detection-voice（guard / status / validate / baseline / batch / fix / gate）

| TC ID | 层级 | 场景 | 断言 |
|---|---|---|---|
| DFX-001 | 单元 | 非 git 目录调 `_count_changed_files` | stderr 含「git」警告；返回 0 |
| DFX-002 | 单元 | git diff 失败时 `_check_file_type_mismatch` | stderr 警告；返回 (False, "") |
| DFX-003 | 单元 | `_is_zombie` 遇 naive last_mod（8 天前） | 返回 True（归一后判定） |
| DFX-004 | CLI | `fstdd guard status`：Build 完成 25h 未 DELIVER | 输出含「Phase Lag」与「Build完成」 |
| DFX-005 | CLI | `fstdd status`：唯一 change 活跃停滞 8 天 | 输出含僵尸清单 + change 名 +「当前活跃」标注 |
| DFX-006 | 单元 | `_show_zombie_changes` 遇不可解析 last_mod | stderr 警告；该 change 进「无法判定」提示 |
| DFX-007 | CLI | `fstdd validate`：基线状态文件损坏 | 输出含「基线」警告而非静默通过 |
| DFX-008 | 单元 | `_load_yaml` 遇损坏基线文件 | 返回 {} 且 stderr 含「损坏」警告 |
| DFX-009 | CLI | batch close 时 _confirm_gate 抛错 | stderr 警告「Gate 3 确认失败」；批次仍闭合 |
| DFX-010 | CLI | `fstdd fix` 遇不可读 py 文件 | 结束报告含跳过计数 ≥1 |
| DFX-011 | CLI | Gate 2 含损坏 spec YAML | 输出含该 spec 警告；其余 spec 正常生成 |

### scan-coverage（check_timestamps）

| TC ID | 层级 | 场景 | 断言 |
|---|---|---|---|
| COV-001 | 单元 | change YAML 含不可解析内容 | scan_change_values 返回含 `category=scan_error` 项 |
| COV-002 | 单元 | proposal.md 不可读 | scan_human_view_headers 返回 scan_error 项 |
| COV-003 | 单元 | full_scan 汇总 | report 含 `scan_errors` 键；既有 naive_count 断言不回归 |

### audit-errata（勘误与哨兵）

| TC ID | 层级 | 场景 | 断言 |
|---|---|---|---|
| ERR-001 | 文档 | test-report 含 315 勘误对照（原判/实证/新判/依据） | 四要素齐备 |
| ERR-002 | 哨兵 | 审计表刷新（修复改变代码形态）后 `--check` | 通过（0 未覆盖） |
| ERR-003 | 回归 | 既有 test_mutation_alive.py 全量 | 5 passed（阈值未被收紧） |

## 三、执行矩阵（Slice 预分）

| Slice | 内容 | TC |
|---|---|---|
| S1 | guard 家族（DFX-001..004） | 4 |
| S2 | status 家族 F-1（DFX-005/006） | 2 |
| S3 | check_timestamps（COV-001..003） | 3 |
| S4 | 流程家族（DFX-007..011） | 5 |
| S5 | 勘误+哨兵+XCUT（ERR-001..003 + 全量） | 3+ |
