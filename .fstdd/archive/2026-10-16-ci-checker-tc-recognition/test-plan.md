# v1.0 测试方案与详细案例 — ci-checker-tc-recognition

> 版本：v1.0
> 创建日期：2026-10-16
> 对应 Phase 2 Spec：canonical/specs/code/2026-10-16-ci-checker-tc-recognition.yaml（3 REQ / 9 SC）+ canonical/specs/agent/（CP-1~CP-6）

## 一、测试策略

### 1.1 测试金字塔

以**单元/行为测试为主**（checker 函数直调 + CLI subprocess 取证），无 E2E：
- 单元层（~70%）：`check_tcid_unique` / `check_tc_implementation_coverage` / `iter_test_files` 直调，临时目录 fixture
- CLI 层（~30%）：`fstdd ci check-failures` / `fstdd diff` / `fstdd trace` subprocess 端到端取证（真实归档 change 复跑）

### 1.2 测试原则

- **真实判据不回退**：缺口场景（planned TC 无实现）必须仍 FAIL；两案例共用 ID 必须仍 FAIL——修复只针对识别面与口径，不放宽判定
- **RED→GREEN 留证**：每个新用例先在不打补丁的代码上跑出预期失败形态，再实现到绿
- **真实数据验收**：以 EXP-20260917-A1 的 10 归档 change 取证表 + 下游归档 change 做修复前后对比，不自造理想数据
- **审计痕迹**：既有测试 TC-CI-008 的 fixture 更新必须带语义迁移注释，禁止静默改绿
- **定义行字面禁忌**：test-plan 正文中不得出现字面 `| **ID** | TC-… |` 示例行——定义行口径会把它计为真实 ID 行（本 test-plan 编写时实测触雷，已规避；该注意事项源自本 change 的语义设计）

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| tests/commands/test_ci.py | 23 | 单元（直调 cmd_ci / check_*） | ci init/generate/check-failures、check_scope_creep、check_coverage_vacuum 等 |
| tests/commands/test_validate.py | 8 | 单元（直调 cmd_validate） | validate 结构检查、TC-ID 重复、THEN/SHALL、GIVEN 充分性 |
| tests/test_utils.py | 8 | 单元 | utils 既有函数（iter_test_files 为新增） |

## 二、详细测试案例

### 功能 1：测试文件识别（iter_test_files + 三处调用点）

对应 REQ-CTR-001 / SC-CTR-001~004

#### 案例 1.1 — 连字符命名测试文件被覆盖检查识别

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-001 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-001 |
| **优先级** | P0 |
| **预置条件** | 临时项目：test-plan 含 planned TC-CTR-001；tests/ 下建 test-hyphen.py，内容含该 TC-ID |
| **输入** | 直调 check_tc_implementation_coverage(change_dir, project_root) |
| **预期结果** | 返回 PASS，「TC 实现覆盖 1/1 (100%)」（修复前：FAIL/WARN 0/1，连字符文件漏扫） |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

#### 案例 1.2 — planned TC 双命名均无实现仍判缺口

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-002 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-002 |
| **优先级** | P0 |
| **预置条件** | 临时项目：test-plan 含 planned TC-CTR-002；tests/ 下两种命名文件均不含该 ID |
| **输入** | 直调 check_tc_implementation_coverage |
| **预期结果** | 仍 FAIL（覆盖率 <50% 阈值不变）；证明 glob 补全未放宽真实判据 |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

#### 案例 1.3 — iter_test_files 混合命名全产出无重复

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-003 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-003 |
| **优先级** | P0 |
| **预置条件** | 临时 tests/ 目录：test_a.py、test-b.py、test_c.py、test-d.py 四个文件 |
| **输入** | 调用 iter_test_files(tests_dir) |
| **预期结果** | 恰产出 4 个文件、无重复；helper docstring 含唯一修改点声明 |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

#### 案例 1.4 — diff/trace 识别连字符测试文件

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-004 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-004 |
| **优先级** | P1 |
| **预置条件** | 临时项目：change 的 test-plan/spec 引用 TC-CTR-004；tests/ 下仅 test-hyphen2.py 承载该 ID |
| **输入** | subprocess 跑 `fstdd diff --name <change>` 与 `fstdd trace TC-CTR-004` |
| **预期结果** | diff 不显示该 TC「未覆盖」；trace 输出含 test-hyphen2.py 路径（修复前两者均失明） |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

### 功能 2：TC-ID 查重定义行口径（check_tcid_unique）

对应 REQ-CTR-002 / SC-CTR-005~007

#### 案例 2.1 — 多处引用定义一次判 PASS

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-005 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-005 |
| **优先级** | P0 |
| **预置条件** | 临时 change：test-plan 中 TC-CTR-005 在正文/矩阵多处出现，但案例定义行恰一条（该行 ID 列指向 TC-CTR-005） |
| **输入** | 直调 check_tcid_unique(change_dir, None) |
| **预期结果** | 返回 PASS（EXP-2026-0017 固化；修复前：FAIL「重复 TC-ID」） |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

#### 案例 2.2 — 两案例定义行共用同一 ID 判 FAIL

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-006 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-006 |
| **优先级** | P0 |
| **预置条件** | 临时 change：test-plan 含两条案例定义行，其 ID 列均指向 TC-CTR-006 |
| **输入** | 直调 check_tcid_unique |
| **预期结果** | 返回 FAIL 且列出 TC-CTR-006（真实判据不放松） |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

#### 案例 2.3 — 10 个历史归档 change 0 误报（EXP-20260917-A1 取证复跑）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-007 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-007 |
| **优先级** | P0 |
| **预置条件** | .fstdd/archive/ 下 EXP-20260917-A1 证据表的 10 个 change（crlf-eol-governance / rename-to-fstdd / skill-engineering-standards / contract-auto-share / inbox-review-sync / install-source-repo / canonical-in-workspace / distributed-task-coordination / migrate-to-d-drive / server-bare-repo-mirror） |
| **输入** | 自动化：`TestTcidUniqueArchivedCorpus::test_archived_changes_no_duplicate_tc_ids` 逐个直调 check_tcid_unique（Part C 补强前为手工 `fstdd ci check-failures <change>` 采集） |
| **预期结果** | (d) 全部 PASS、0 个「重复 TC-ID」（修复前同集合 10/10 FAIL，EXP-20260917-A1 已取证） |
| **当前状态** | ✅ 已自动化（ADJ-008） |

### 功能 3：修复落地可审计性

对应 REQ-CTR-003 / SC-CTR-008~009

#### 案例 3.1 — 既有 TC-CI-008 换语义更新并留痕

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-008 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-008 |
| **优先级** | P1 |
| **预置条件** | tests/commands/test_ci.py 的 test_check_failures_detects_duplicate_tc_ids 已按 design Decision 4 更新 |
| **输入** | 跑该测试（含 fixture 静态检查：注释含语义迁移说明） |
| **预期结果** | 测试通过（两定义行共用 ID → FAIL 路径仍被覆盖）；fixture 含「旧 fixture 编码旧全文语义，随 C4 同批更新」注释 |
| **当前状态** | ✅ 已实现（映射见 test-report 覆盖矩阵） |

#### 案例 3.2 — 下游归档 change 修复前后复跑对比

| 字段 | 内容 |
|------|------|
| **ID** | TC-CTR-009 |
| **对应 Spec** | ci-checker-tc-recognition → Scenario: SC-CTR-009 |
| **优先级** | P1 |
| **预置条件** | 下游项目归档 change 2026-10-16-default-free-fixture 的 test-plan 可读（本仓以同判据复跑其文本） |
| **输入** | 修复前后各跑一次 (d) 查重与 TC 实现覆盖 |
| **预期结果** | 覆盖 0/10→9/10（唯一缺失 TC-EPR-002 为模板引用，成因不变）；(d) 保持 PASS 且计数回归真实定义行（10→6） |
| **当前状态** | ✅ 已取证（手工对比，跨仓依赖；规格原文「(d) FAIL→PASS」失实，修正见 ADJ-003 / tasks 4.2） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| iter_test_files（helper） | TC-CTR-003 | — | — | ✅ 已实现（tests/test_utils.py，含 3 项 Part C 边界/契约补强） |
| ci 覆盖检查（glob 修复） | TC-CTR-001/002 | TC-CTR-009 | — | ✅ 已实现（tests/commands/test_ci.py::TestTcImplementationCoverageRecognition） |
| ci (d) 查重（口径对齐） | TC-CTR-005/006/008 | TC-CTR-007/009 | — | ✅ 已实现（TestTcidUniqueDefinitionRow + TestTcidUniqueArchivedCorpus） |
| diff/trace（同根因点位） | — | TC-CTR-004 | — | ✅ 已实现（tests/commands/test_diff_trace_hyphen.py，TC-CTR-004a/b） |

> 终态用例数（本 change 落地后）：tests/commands/test_ci.py 23→30、tests/test_utils.py 8→13、tests/commands/test_diff_trace_hyphen.py 0→2，合计 **+14 用例**；自动化覆盖 **9/9 SC**（SC-CTR-009 为跨仓依赖，保留执行取证）。

## 四、回归风险矩阵

| 风险区域 | 本 change 改动 | 已有回归保护 | 风险等级 |
|----------|---------------|-------------|---------|
| ci.py check-failures 全链路 | 改 2 个检查函数 | test_ci.py 23 例 + test_validate.py 8 例（基线 31/31） | 🟡 |
| diff.py / trace.py | 切换 helper 调用 | tests/commands/test_diff.py、test_trace.py 既有套件 | 🟡 |
| utils.py | 新增 1 函数（不动既有） | test_utils.py 8 例 | 🟢 |
| 存量归档 change 的 (d) 判定 | 口径收窄 | TC-CTR-007 真实数据验收 | 🟢 |

## 五、建议补充顺序

1. **第一优先（P0，修复前必须 RED 确认）**：TC-CTR-001、TC-CTR-002、TC-CTR-003、TC-CTR-005、TC-CTR-006、TC-CTR-007
2. **第二优先（P1）**：TC-CTR-004、TC-CTR-008、TC-CTR-009
3. **第三优先（P2）**：无（本 change 范围收敛，不设 P2）

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 连字符失明假 FAIL：下游归档 change 覆盖 0/10；修正 glob 复测 9/10 | 2026-10-16T22:30:00+08:00 | c99ef7d（下游侧对等观测） | 下游交付 test-report.md §8 |
| (d) 全文口径误报：10 归档 change 10/10 被判重复 | 2026-09-17（本仓经验录入） | — | EXP-20260917-A1（.fstdd/experiences/） |
| 基线 31/31：test_ci.py + test_validate.py 全绿 | 2026-10-16T22:36:00+08:00 | c99ef7d | `pytest tests/commands/test_ci.py tests/commands/test_validate.py -q` |
| 同根因三处点位：grep rglob("test_*.py") → ci.py:558 / diff.py:99 / trace.py:95 | 2026-10-16T22:30:00+08:00 | c99ef7d | 只读 grep |
| 下游 (d) FAIL 记录：TC-ID 全文重复被迫手工去重 | 2026-10-16T20:xx（下游 Phase 3） | 0015039 | EXP-2026-0017 / 下游 test-report.md §8 |

> 非金融项目（FINANCIAL_PROJECT=NO），第七节 10 维测试不适用，按模板规定跳过。

## 七、补充测试登记（Part C 补强，Gate 2 后追加）

> 以下用例为 Part C（C1 三路评审驱动）补强，**不改变** Gate 2 锁定的 9 个 TC 的判据；
> 用于覆盖边界与一致性守卫，登记见 design-adjustments ADJ-006/007/008。

| 用例（测试函数） | 类型 | 关联 SC | 断言要点 |
|---|---|---|---|
| `test_utils.py::test_iter_test_files_skips_directory_entries` | 边界 | SC-CTR-003 | 名为 `test_dir.py` 的**目录**不产出（防 read_text 抛 IsADirectoryError） |
| `test_utils.py::test_iter_test_files_recurses_nested_subdirs` | 边界 | SC-CTR-003 | 嵌套子目录两种命名递归产出且无重复 |
| `test_utils.py::test_iter_test_files_docstring_declares_single_source` | 契约 | SC-CTR-003 | docstring 含「唯一修改点」「新增命名模式」声明 |
| `test_utils.py::test_tc_id_pattern_matches_validate_literal` | 一致性守卫 | SC-CTR-005/006 | 常量与 validate.py 内联字面量逐字节相等（钉死 ADJ-001 的 2 副本同步通道） |
| `test_ci.py::TestTcidUniqueDefinitionRow::test_non_template_plan_warns_not_fails` | 语义钉死 | SC-CTR-005 | 非模板写法 → WARN（固定已接受取舍，防误判为回归） |
| `test_ci.py::TestTcidUniqueArchivedCorpus::test_archived_changes_no_duplicate_tc_ids` | 回归 | SC-CTR-007 | 10 个归档 change (d) 全部 PASS（TC-CTR-007 由手工取证升级为自动化） |

> 自动化覆盖：**9/9 SC**（SC-CTR-009 为跨仓依赖，保留执行取证，见上表）。
