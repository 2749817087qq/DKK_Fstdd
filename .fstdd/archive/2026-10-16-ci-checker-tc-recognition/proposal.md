# 修复 CI 检查器两类识别缺陷：测试文件 glob 失明 + TC-ID 查重口径分裂

<!-- source_hash: 6585d544f4e9f447 -->
<!-- generated_at: 2026-10-16T14:42:25+00:00 -->
<!-- canonical: canonical/proposals/2026-10-16-ci-checker-tc-recognition.yaml -->

## Why

2026-10-16-default-free-fixture 交付期间实测暴露 FSTDD 检查器两类识别缺陷： ① `check_tc_implementation_coverage`（ci.py:558）以 `rglob("test_*.py")` 扫描测试文件， 对连字符命名 `test-*.py`（本仓族既定约定，经 run-all.py 聚合，EXP-2026-0001）结构性失明—— 对该 change 报「TC 实现覆盖 0/10」假 FAIL，修正 glob 后实测 9/10； 狼来了效应会训练用户忽略红，从而掩盖真实覆盖缺口。同一根因还见于 diff.py:99 与 trace.py:95 （fstdd diff 对连字符测试文件显示「未覆盖」、fstdd trace 找不到测试引用）。 ② `check_tcid_unique`（ci.py:317）对 test-plan.md **全文** findall TC-ID， 任一 ID 出现两次即 FAIL；而 validate.py:82-88 的查重只数 `| **ID** | TC-... |` **定义行** （注释明示意图「两个案例不得共用同一 ID」，并说明测试执行矩阵/建议补充顺序中引用 TC-ID 是模板正常写法）。两检查器口径分裂（EXP-2026-0017）迫使作者把每个 TC-ID 字面压到 全文恰一次，否则满足 validate 的 test-plan 仍被 ci (d) 拒——文档扭曲适配工具。

## What Changes

- fstdd/cli/utils.py 新增共享 helper `iter_test_files(tests_dir)`：同时产出 `test_*.py` 与 `test-*.py` 两种命名（两模式第 5 字符互斥，天然不会重复； 仍以 seen 集合防御未来模式扩张）。单一事实源，杜绝第 4 处同根因点位。
- ci.py `check_tc_implementation_coverage` 切换至 iter_test_files——修复项① （连字符命名的测试文件不再漏扫）。判据不变：planned TC-ID 在全部测试文件中 均不存在仍按原阈值 FAIL/WARN。
- diff.py:99 与 trace.py:95 两个同根因点位一并切换至 iter_test_files （同一 glob 失明：fstdd diff 显示「未覆盖」假阴性、fstdd trace 找不到测试引用）。 此项为范围扩张（超出用户点名的 2 条），Gate 1 请用户明示裁定；建议采纳—— 同根因留半根比全修更危险（下一份假报告还会再来）。
- ci.py `check_tcid_unique` 查重正则由全文 `(TC-[A-Z]+-\d{3})` 改为定义行 `\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})`，与 validate.py:82-88 逐字一致——修复项② （EXP-2026-0017）。语义收敛为 validate 注释声明的意图：两个案例定义行不得共用 同一 TC-ID；矩阵/补充顺序/正文中引用 TC-ID 属正常写法，不再误判。 代码注释引用 EXP-2026-0017 与 validate.py 对齐事实，防回归性再分裂。
- tests/commands/test_ci.py：更新 TC-CI-008 fixture 至新语义（两条 `| **ID** | TC-X-001 |` 定义行 → FAIL），并在测试内注释说明「旧 fixture 编码旧全文语义，随 C4 同批更新」， 保留审计痕迹。
- 新增回归测试（RED→GREEN 固定）： (a) 连字符 `test-hyphen.py` 承载 planned TC-ID → check_tc_implementation_coverage PASS （修复前 FAIL，EXP-2026-0001 类假红）； (b) planned TC-ID 在两种命名测试文件中均不存在 → 仍 FAIL（真实缺口不放松）； (c) test-plan 中同一 TC-ID 在正文/矩阵多处引用但定义行恰一条 → (d) PASS（EXP-2026-0017 固化）； (d) iter_test_files 单测（tests/test_utils.py）：混合目录同时含两种命名 → 全部产出且无重复。

### New Capabilities

- **ci-checker-tc-recognition**：CI 检查器对「测试文件」与「TC-ID」的识别口径：测试文件扫描覆盖 test_*.py 与 test-*.py 两种命名（单一事实源 iter_test_files）；TC-ID 查重以定义行 （`| **ID** | TC-... |`）为口径，与 validate 对齐。真实缺口检测判据不变。

## Success Criteria

- [ ] RED→GREEN：新测试 (a)(c) 在修复前必败（连字符文件漏扫致覆盖不足；全文查重误判），修复后必过。
- [ ] 真实判据不回退：新测试 (b)（planned TC 无实现）修复后仍 FAIL；更新后的 TC-CI-008（两定义行共用 ID）FAIL。
- [ ] 既有套件：pytest tests/commands/test_ci.py tests/commands/test_validate.py 全绿（含更新后的 TC-CI-008）。
- [ ] 真实数据复跑取证：对归档 change 2026-10-16-default-free-fixture 跑 ci check-failures——(d) 由 FAIL（重复 TC-ID）转 PASS，TC 实现覆盖由 0/10 转 9/10（唯一缺失为模板引用 TC-EPR-002，成因不变）。
- [ ] 全仓 pytest 无新增失败（相对基线 c99ef7d）；iter_test_files 单测覆盖两种命名混合目录无重复。
