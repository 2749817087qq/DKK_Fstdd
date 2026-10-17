# Spec: ci-checker-tc-recognition

> Change: 2026-10-16-ci-checker-tc-recognition | Auto-generated Human View

## Requirements

### Requirement: 测试文件识别由单一事实源 iter_test_files(tests_dir) 承担：同时产出 test_*.py 与 test-*.py 两种命名，去重无重复；ci.py check_tc_implementation_coverage / diff.py / trace.py 三处调用点一律经此 helper 扫描。

#### Scenario: SC-CTR-001

- **GIVEN** tests/ 目录下存在连字符命名 test-hyphen.py，其内容承载 test-plan 中的 planned TC-ID
- **WHEN** 调用 check_tc_implementation_coverage
- **THEN** 该 TC-ID SHALL 被识别为实现，覆盖检查 SHALL PASS（不再因命名漏扫报 0/N 假 FAIL）

#### Scenario: SC-CTR-002

- **GIVEN** planned TC-ID 在 tests/ 下两种命名的全部测试文件中均不存在
- **WHEN** 调用 check_tc_implementation_coverage
- **THEN** 检查 SHALL 仍按原阈值判定 FAIL/WARN（glob 补全只扩大识别面，不放宽缺口检测）

#### Scenario: SC-CTR-003

- **GIVEN** tests/ 目录同时含 test_*.py 与 test-*.py 混合命名文件
- **WHEN** 调用 iter_test_files
- **THEN** 两种命名文件 SHALL 全部产出且无重复条目；docstring SHALL 声明「新增命名模式唯一修改点」

#### Scenario: SC-CTR-004

- **GIVEN** tests/ 下仅有连字符命名测试文件承载某 TC-ID
- **WHEN** 执行 fstdd diff 与 fstdd trace（subprocess CLI）
- **THEN** diff SHALL 识别到该测试文件（不再显示「未覆盖」假阴性）；trace SHALL 定位到该测试文件与函数（不再空手）

### Requirement: TC-ID 查重以定义行为口径：check_tcid_unique 与 validate.py:82-88 逐字一致地统计 `| **ID** | TC-… |` 定义行——两个案例定义行不得共用同一 TC-ID；矩阵/正文中引用 TC-ID 属正常写法，不判重复。

#### Scenario: SC-CTR-005

- **GIVEN** test-plan.md 中同一 TC-ID 在正文/矩阵多处被引用，但 `| **ID** | TC-… |` 定义行恰有一条
- **WHEN** 调用 check_tcid_unique
- **THEN** 检查 SHALL PASS（多处引用属模板正常写法，EXP-2026-0017 固化）

#### Scenario: SC-CTR-006

- **GIVEN** test-plan.md 中两条案例定义行共用同一 TC-ID
- **WHEN** 调用 check_tcid_unique
- **THEN** 检查 SHALL FAIL 并列出该重复 ID（真实判据不放松）

#### Scenario: SC-CTR-007

- **GIVEN** EXP-20260917-A1 证据表中的 10 个历史归档 change（2026-09-15 ~ 2026-09-17，全部已通过 Gate 3 验收）
- **WHEN** 对每个归档 change 执行 ci check-failures 的 (d) 项
- **THEN** (d) SHALL 全部 PASS（0 误报；修复前该集合 10/10 FAIL）

### Requirement: 修复落地方式须可审计：既有测试 TC-CI-008 随语义同批更新并留痕；新增回归测试固定 RED→GREEN；修复前后对同一 change 复跑对比留证。

#### Scenario: SC-CTR-008

- **GIVEN** 本 change 修改 ci.py 的 check_tcid_unique 统计口径
- **WHEN** 运行更新后的既有测试 test_check_failures_detects_duplicate_tc_ids（TC-CI-008）
- **THEN** 该测试 SHALL 以新语义 fixture（两定义行共用 ID）通过，且测试内 SHALL 含「旧 fixture 语义随 C4 同批更新」的审计注释

#### Scenario: SC-CTR-009

- **GIVEN** 下游归档 change 2026-10-16-default-free-fixture（修复前实测 (d) FAIL、覆盖 0/10）
- **WHEN** 修复后对其复跑 ci check-failures
- **THEN** (d) SHALL 由 FAIL 转 PASS，TC 实现覆盖 SHALL 由 0/10 转 9/10（唯一缺失 TC-EPR-002 为模板引用，成因不变）
