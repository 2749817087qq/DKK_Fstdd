# v1.0 任务清单 — 2026-10-16-ci-checker-tc-recognition

## 1. ci-checker-tc-recognition — 测试文件识别（helper + ci 覆盖检查）（P0）

- [x] 1.1 `upstream/fstdd/cli/utils.py` 新增 `iter_test_files(tests_dir)`：同时产出 `test_*.py` 与 `test-*.py`（seen 去重 + docstring 声明唯一修改点），公共函数带完整类型注解（依赖无）——Slice 1
- [x] 1.2 `ci.py:558` `check_tc_implementation_coverage` 切换至 `iter_test_files`，判据/阈值不变（依赖 #1.1）——Slice 1
- [x] 1.3 新增 `tests/commands/test_ci.py`：TC-CTR-001（连字符文件承载 planned TC → PASS）、TC-CTR-002（双命名均无 → 仍 FAIL）（依赖 #1.1）——Slice 1
- [x] 1.4 新增 `tests/test_utils.py`：TC-CTR-003（混合命名目录全产出无重复）（依赖 #1.1）——Slice 1

## 2. ci-checker-tc-recognition — TC-ID 查重定义行口径（P0）

- [x] 2.1 `ci.py:317` `check_tcid_unique` 正则改定义行 `\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})`，与 validate.py:82-88 逐字一致 + 注释引用 EXP-20260917-A1/EXP-2026-0017（依赖无）——Slice 2
  > 落地偏离：ci.py 正则改取 utils.TC_ID_DEFINITION_ROW_PATTERN 常量；validate.py 原计划同切常量，但源码级守卫测试 test_c3_validate_source_uses_scoped_regex 要求 validate.py 内含定义行正则字面量 ⇒ 回退为内联字面量（同表达式）+ 双向同步注释，最终回归 design D3 原案。详见 design-adjustments。
- [x] 2.2 更新既有 `tests/commands/test_ci.py::test_check_failures_detects_duplicate_tc_ids`（TC-CI-008）：fixture 换新语义（两定义行共用 ID → FAIL）+ 审计注释（依赖 #2.1）——Slice 2
- [x] 2.3 新增 TC-CTR-005（多处引用定义一次 → PASS）、TC-CTR-006（两定义行共用 → FAIL）、TC-CTR-008（TC-CI-008 审计注释在位）（依赖 #2.1）——Slice 2
  > TC-CTR-008 首版源码扫描断言自指污染 → 改 inspect.getsource 限定 TC-CI-008 函数体 + 期望字面运行时拼接。

## 3. ci-checker-tc-recognition — diff/trace 同根因点位（P1）

- [x] 3.1 `diff.py:99` / `trace.py:95` 切换至 `iter_test_files`（依赖 #1.1）——Slice 3
- [x] 3.2 新增 `tests/commands/test_diff_trace_hyphen.py`（或并入既有 test 文件）：TC-CTR-004 subprocess 跑 `fstdd diff` / `fstdd trace`，连字符测试文件被识别（依赖 #3.1）——Slice 3

## 4. 测试与验证

- [x] 4.1 每切片 RED→GREEN 留证（Slice 1/2/3 各自先红后绿）—— 证据见 phase-context 三切片记录（RED 失败形态 + GREEN 计数 + 变异验证）
- [x] 4.2 真实数据验收：SC-CTR-007（10 归档 change (d) 0 误报，EXP-20260917-A1 取证复跑）+ SC-CTR-009（下游归档 change 修复前后对比：(d) FAIL→PASS、覆盖 0/10→9/10）
  > 修正记录：SC-CTR-009 实测 (d) 修复前即 PASS（全文无重复字面），FAIL→PASS 实际发生在覆盖检查 0/10→9/10；(d) 的改善是计数 10→6 回归真实定义行。证据见 phase-context Slice 2。SC-CTR-007 已由手工取证升级为自动化测试（见 4.6）。
- [x] 4.3 临时回退式变异验证：修复后短暂还原 ci.py 新正则为全文口径 → 新测试必红 → sha256 校验还原（EXP-2026-0013 纪律）
  > TC-CTR-005 被杀（转红），TC-CTR-006/008 守卫保持绿；sha256 `a07d9434…dab9` 还原复核通过。注：变异只覆盖 (d) 口径；helper（glob）变异由 test-reviewer 独立执行（`_TEST_FILE_PATTERNS` 回退 → TC-CTR-001/003/004a/004b 被杀，sha256 `a903c971…` 还原复核）。
- [ ] 4.4 全量回归：`pytest upstream/tests/` 相对基线 c99ef7d（14 failed / 859 passed / 8 skipped，环境性预存在）**无新增失败**
  > 实测（Okypgp，validate.py 修复后）：11 failed / 871 passed / 7 skipped；11 项失败中 10 项与基线逐一同名，余 1 项为 ADJ-005 瞬态（test_a6，DELIVER 提交后复证）。C2 比对曾捕获 1 项真实回归（test_c3，已修复，见 ADJ-001）。
- [x] 4.5 Part C 质量验证（C1 三路评审 / C2 质量检查 / C3 diff / C4 失败模式全量 / C5 经验 / C6 design-adjustments / C7 test-report）
- [x] 4.6 C1 评审驱动补强（ADJ-006/007/008）：SC-CTR-007 自动化测试、subprocess 编码对齐、常量↔字面量等价守卫、helper 目录条目过滤、断言补强、非模板 WARN 语义钉死

<!--
优先级说明：P0 = 阻塞性任务；P1 = 当前阶段应完成。
依赖标注：(依赖 #N.M) 见各任务尾注。
串行说明：Slice 1/2 均改 ci.py 与 test_ci.py，Slice 3 改 diff/trace——同文件写冲突，三切片串行执行。
-->
