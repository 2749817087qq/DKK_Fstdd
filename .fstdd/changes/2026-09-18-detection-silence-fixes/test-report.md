# test-report：detection-silence-fixes

**change**：`2026-09-18-detection-silence-fixes`
**日期**：2026-09-18
**结论**：🟢 通过（S1–S4a 已合并；S4b 由 FSTDD004 在途，限期 09-20）

---

## 一、TC 执行矩阵

| TC | 内容 | 状态 | 证据 |
|---|---|---|---|
| DFX-001 | `_count_changed_files` git 失败 → stderr 出声 | ✅ | test_detection_voice.py::test_dfx_001 |
| DFX-002 | `_check_file_type_mismatch` 统计失败 → 出声 | ✅ | ::test_dfx_002 |
| DFX-003 | `_is_zombie` naive last_modified → UTC 归一 | ✅ | ::test_dfx_003 |
| DFX-004 | `guard status` 输出 Phase Lag 段（F-2 接线） | ✅ | ::test_dfx_004（含阴性对照） |
| DFX-005 | `fstdd status` 活跃停滞 change 标注「当前活跃」 | ✅ | test_status_voice.py（FSTDD003 交付） |
| DFX-006 | `_show_zombie_changes` 不可解析 last_mod → 警告+无法判定 | ✅ | test_status_voice.py（FSTDD003） |
| DFX-007 | `fstdd validate` 基线损坏 → 「基线」警告 | ✅ | test_validate_voice.py（FSTDD002） |
| DFX-008 | `_load_yaml` 损坏基线 → {} + stderr 警告 | ✅ | test_validate_voice.py（FSTDD002） |
| DFX-009 | batch close `_confirm_gate` 抛错 → 警告且批次仍闭合 | ✅ | test_validate_voice.py（FSTDD002） |
| DFX-010 | `fstdd fix` 不可读文件 → 结束报告跳过计数 ≥1 | ⏳ | S4b（FSTDD004 在途） |
| DFX-011 | Gate 2 损坏 spec YAML → 逐条警告、其余正常 | ⏳ | S4b（FSTDD004 在途） |
| COV-001 | change YAML 不可解析 → scan_error 项 | ✅ | test_status_voice.py（FSTDD003） |
| COV-002 | proposal.md 不可读 → scan_error 项 | ✅ | test_status_voice.py（FSTDD003） |
| COV-003 | full_scan 含 scan_errors，naive_count 不回归 | ✅ | test_status_voice.py（FSTDD003） |
| ERR-001 | 315 勘误对照（本报告第二节） | ✅ | 见下 |
| ERR-002 | 审计表刷新后哨兵 `--check` 通过 | ✅ | 活表 18 点，哨兵 PASS |
| ERR-003 | 既有 test_mutation_alive.py 全量 | ✅ | 5 passed（阈值未收紧） |

## 二、ERR-001：EA-010（原 guard.py:315）勘误对照

| 项 | 内容 |
|---|---|
| **原判** | 意外吞错 / p1：「守卫路径判定 fail-open：异常时 return False = 未受保护文件被放行编辑。守卫必须 fail-closed」 |
| **实证** | ① 逐字核对审计时点源码：`git show 699c583:upstream/fstdd/cli/commands/guard.py` 第 315 行确为 `_is_workflow_artifact` 的 `except Exception: return False`；② 该函数语义为 **True = 放行白名单**（understand/spec 阶段允许编辑 canonical/、design.md、test-plan.md、proposal.md、spec.md），**False = 非白名单**；③ 调用点行为：未匹配白名单即由 Guard 拒绝编辑 |
| **新判** | **合理容错**（severity: null，response: 放行，detection_path: false）——异常 → 拒绝放行，属 **fail-closed**，方向安全 |
| **依据** | 函数 docstring（「understand/spec 阶段放行的 YAML-first 流程产出物」）+ 三处 `return True` 白名单分支 + 调用点拒绝语义 + 审计时点源码逐字核对 |
| **处置** | 不回改归档表（设计决策 D6）；新判落本 change 活表 `audit/except-points.yaml` 的 `meta.errata`，并留痕本报告 |

> 结论：原判把方向说反了（fail-open ↔ fail-closed）。该点无需修改代码，
> 也不该计入「待修复」清单——本 change 的改造清单因此不含它。

## 三、审计活表刷新记录（ERR-002）

| 项 | 值 |
|---|---|
| 表位置 | `.fstdd/changes/2026-09-18-detection-silence-fixes/audit/except-points.yaml`（活表，D8 决策） |
| 刷新前 | 24 点（含 S1 修复后的行号刷新） |
| 刷新后 | **18 点**（合理容错 13 / 意外吞错 5） |
| 哨兵 | `audit_silent_except.check()` → PASS（0 未覆盖） |
| 归档表 | **未改动**（D6 决策） |

**本轮消除的 11 个吞异常点**（从清单中消失 = 静默失败被真正消除）：

- S1（K）：guard.py 5 点（git diff 计数、类型占比、僵尸判定、build/spec 时效）
- S2+S3（FSTDD003）：status.py:135、check_timestamps.py:186、check_timestamps.py:209
- S4a（FSTDD002）：baseline.py:88、batch.py:709、validate.py:106

## 四、协作交付来源

| Slice | 节点 | 交付物 | 验收 |
|---|---|---|---|
| S2+S3 | FSTDD003 | `FSTDD003-sliceS2S3.patch`（14.9KB） | 基线 5e3f9a3 干净应用；5 用例绿 |
| S4a | FSTDD002 | `FSTDD002-sliceS4a.patch`（10.9KB） | 基线 5e3f9a3 干净应用；6 用例绿 |
| S4b | FSTDD004 | 在途（09-20 13:00 限期） | — |

合并提交：`635b3e9`（S2+S3+S4a）→ 推送 `5e3f9a3..29abbe5`。

**范围追认**：003 的 patch 含 `tools/check_timestamps.py`，属 K 的任务白名单
写漏（COV 目标函数在该文件），已追认合法并同步评审口径。

## 五、回归结果

| 范围 | 结果 |
|---|---|
| 节点补丁组合（patchtest 克隆） | 722 passed / 3 failed（2 项审计表漂移→已在合并态刷新修复；1 项区外副本测试为克隆环境性） |
| 合并态全量（stdd-repo） | **725 passed / 1 failed** |
| 相关子集复跑 | 26 passed（voice ×3 + 审计 ×2） |

**唯一失败**：`test_canonical_in_workspace.py::test_c2_archive_file_count_matches_source`
（归档 828 != 源 829）。根因已定位：源目录 `~/.workbuddy-ai/Fstdd/` 多出
`.git/config` 一个文件（归档快照之后产生，非本 change 引入）。
**不在本 change 范围内**，未修改；建议后续二选一：测试比较排除 `.git/`，
或重做归档快照（待 D哥 拍板）。

## 六、遗留项

1. **S4b**（DFX-010/011，FSTDD004）：到期 09-20 13:00，合并后本 change 收口。
2. **交叉评审**：FSTDD001（S2S3）、FSTDD006（S4a/S4b）改为事后审计，
   限期 09-20 21:00；有必须修复项则开 follow-up 补丁。
3. **区外副本测试**：见第五节，需 D哥 拍板修法。
4. Gate 3 待 S4b 合并后申请。
