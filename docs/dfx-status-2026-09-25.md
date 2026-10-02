# DFX 现状表（检测静默家族）

**日期**：2026-09-25｜**盘点**：K-main（迭代 02 · W1.2）
**来源**：`change 2026-09-18-detection-silence-fixes`
**当前状态**：**11 / 11 全部已修复且有测试锚定；覆盖测试实测 `15 passed`**（2026-09-25）

## 一、逐条现状

| # | 缺陷 | 判据（修复后行为） | 状态 | 测试锚点 | 交付方 |
|---|---|---|---|---|---|
| DFX-001 | `_count_changed_files` 遇非 git 目录 | stderr 含「git」警告；返回 0 | ✅ 已修 | `test_detection_voice.py::test_dfx_001` | FSTDD001 |
| DFX-002 | `git diff` 失败时 `_check_file_type_mismatch` | stderr 警告；返回 (False, "") | ✅ 已修 | `::test_dfx_002` | FSTDD001 |
| DFX-003 | `_is_zombie` 遇 naive `last_mod`（8 天前） | 返回 True（UTC 归一后判定） | ✅ 已修 | `::test_dfx_003` | FSTDD001 |
| DFX-004 | `guard status`：Build 完成 25h 未 DELIVER | 输出含「Phase Lag」与「Build完成」 | ✅ 已修 | `::test_dfx_004`（**含阴性对照**） | FSTDD001 |
| DFX-005 | `fstdd status`：唯一 change 活跃停滞 8 天 | 输出含僵尸清单 + change 名 +「当前活跃」标注 | ✅ 已修 | `test_status_voice.py` | **FSTDD003** |
| DFX-006 | `_show_zombie_changes` 遇不可解析 `last_mod` | stderr 警告；该 change 进「无法判定」 | ✅ 已修 | `test_status_voice.py` | **FSTDD003** |
| DFX-007 | `fstdd validate`：基线状态文件损坏 | 输出含「基线」警告而非静默通过 | ✅ 已修 | `test_validate_voice.py` | **FSTDD002** |
| DFX-008 | `_load_yaml` 遇损坏基线文件 | 返回 {} 且 stderr 含「损坏」警告 | ✅ 已修 | `test_validate_voice.py` | **FSTDD002** |
| DFX-009 | batch close 时 `_confirm_gate` 抛错 | stderr 警告「Gate 3 确认失败」；批次仍闭合 | ✅ 已修 | `test_validate_voice.py` | **FSTDD002** |
| DFX-010 | `fstdd fix` 遇不可读 py 文件 | 结束报告含跳过计数 ≥1 | ✅ 已修 | S4b（commit `74ad408`） | **K**（004 澄清属主仓代码） |
| DFX-011 | Gate 2 含损坏 spec YAML | 输出含该 spec 警告；其余 spec 正常生成 | ✅ 已修 | S4b（commit `74ad408`） | **K** |

## 二、汇总

| 项 | 值 |
|---|---|
| 总数 | **11** |
| ✅ 已修 + 有测试 | **11（100%）** |
| ⬜ 仍开 | **0** |
| 🔄 转设计 | **0** |
| 覆盖测试实测 | **15 passed**（3 个 voice 测试文件，2026-09-25 复跑） |

**家族归属**（按原审计分类）：
- **S1 guard 家族**（DFX-001..004）：4 条 → FSTDD001 交付
- **S2 status 家族 F-1**（DFX-005/006）：2 条 → FSTDD003 交付
- **S4 流程家族**（DFX-007..011）：5 条 → FSTDD002 交付（007–009）+ K 实现（010/011）

## 三、结论

**DFX 家族已 100% 闭环**，无需再开 follow-up。
⇒ 迭代 02 的 **W1.2 判定：无遗留缺陷**，**不构成 v3.0.7 的内容来源**。

**唯一待补**：DFX-010/011 由 **K 实现**（原派 FSTDD004，其澄清「属主仓代码，不属节点自动化职责」）
⇒ 属**流程观察项**：**跨节点派单时需先判"是否属该节点职责域"**（已并入《发布与文档规程》的责任条款思路）。

—— **K-main**（2026-09-25）
