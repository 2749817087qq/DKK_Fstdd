# v1.0 测试报告 — ci-checker-tc-recognition

> change：`2026-10-16-ci-checker-tc-recognition`
> 基线：`c99ef7d`（worktree `D:/tools/FSTDD/FSTDD005-wt-311`，detached HEAD）
> 阶段：FSTDD Phase 3 BUILD — Part C 质量验证（C7 产出）
> 日期：2026-10-17
> 范围：REQ-CTR-001/002/003，SC-CTR-001~009，TC-CTR-001~009

---

## 一、结论摘要

| 项 | 结果 |
|---|---|
| SC 覆盖 | **9/9**（8 项自动化 + SC-CTR-009 跨仓执行取证） |
| 新增用例 | **+15**（test_ci 23→30、test_utils 8→14、test_diff_trace_hyphen 0→2） |
| 受影响套件 | **54 passed**（4 文件：test_utils 14 + test_ci 30 + test_diff_trace_hyphen 2 + test_validate 8）；含 diff/trace 的 **6 文件 63 passed** |
| 全量回归 | 相对基线 `c99ef7d`（14 failed / 859 passed / 8 skipped）**无新增失败**（真实新增 0；1 项瞬态已于交付后转绿，见 §3.2） |
| 静态检查 | ruff 本 change **零新增**（cli/ 128=128；5 改动文件 16=16 行号归一后逐条一致）；mypy **零新增**（80=80） |
| C1 三路评审 | code **PASS**（0🔴/0🟠）；test **CONDITIONAL**（2🟠→已由 ADJ-006/008 处置）；docs **CONDITIONAL**（3🟠→已由 ADJ-002/007 + 文档修正处置） |
| C3 diff 审查 | **PASS**（0🔴/0🟠）；两份独立报告并列（team-lead 复核 + code-reviewer 独立审查）；独立报告另记 2🟡：**D-01 已由 ADJ-009 修复**（Gate 3 用户裁定纳入）、D-02 交付清单登记已采纳 — 见 §八 |
| C4 失败模式 | 14 类 **13 ✅ + 1 SKIPPED + 0 ❌**；8 类金融 **全 SKIPPED**（FINANCIAL_PROJECT=NO） |
| C6 设计偏离 | **9 条**（ADJ-001~009），全部留痕 |
| **总判定** | **通过**（无阻断项；1 项瞬态已于交付后复证转绿） |

---

## 二、变更概述

修复 FSTDD CLI 两个检查器缺陷：

| # | 缺陷 | 症状 | 根因 | 修复 |
|---|---|---|---|---|
| ① | **测试文件识别失明** | `ci check-failures` 的「TC 实现覆盖」恒定假 FAIL `0/N`；`diff` 显示「未覆盖」；`trace` 找不到测试引用 | `ci.py:558` / `diff.py:99` / `trace.py:95` 三处各自 `tests_dir.rglob("test_*.py")`，对仓库惯例的连字符命名 `test-*.py` **结构性失明** | 新增单一事实源 `utils.iter_test_files(tests_dir)`（产出 `test_*.py` + `test-*.py`，`seen` 去重、`is_file()` 过滤目录条目）；三处调用点一律经此 helper |
| ② | **TC-ID 口径分裂** | 归档 change 被误报「重复 TC-ID」（同集合 10/10 假红）；下游被迫把每个 TC-ID 字面压到全文恰一次 | `ci.py check_tcid_unique` 对 **test-plan 全文** 计数（任意重复即 FAIL），而 `validate.py:82-88` 只数 `\| **ID** \| TC-… \|` **定义行** | `check_tcid_unique` 改定义行口径（`utils.TC_ID_DEFINITION_ROW_PATTERN`）；`validate.py` 保留同表达式内联字面量（源码守卫测试约束，见 ADJ-001） |

**真实判据不放宽**（proposal constraint #1）：planned TC 双命名均无实现仍 FAIL；两案例定义行共用 ID 仍 FAIL。

**改动面**：9 个已跟踪文件 `+370 / -14`，另 1 个新测试文件（94 行）。

```
 .fstdd/experiences/.experience-index.yaml |  14 +-
 .fstdd/experiences/EXP-20260917-A1.md     |  16 +-
 upstream/fstdd/cli/commands/ci.py         |  14 +-
 upstream/fstdd/cli/commands/diff.py       |   9 +-
 upstream/fstdd/cli/commands/trace.py      |   7 +-
 upstream/fstdd/cli/commands/validate.py   |   4 +
 upstream/fstdd/cli/utils.py               |  42 +++++-
 upstream/tests/commands/test_ci.py        | 204 +++++++++++++++++++++++++++++-
 upstream/tests/test_utils.py              |  74 +++++++++++
 9 files changed, 370 insertions(+), 14 deletions(-)
```

---

## 三、测试执行结果

### 3.1 受影响套件（终态）

```
C:/Python311/python.exe -m pytest \
  upstream/tests/test_utils.py \
  upstream/tests/commands/test_ci.py \
  upstream/tests/commands/test_diff_trace_hyphen.py \
  upstream/tests/commands/test_validate.py -q
→ 54 passed
```

| 测试文件 | 基线 | 终态 | 增量 |
|---|---|---|---|
| tests/commands/test_ci.py | 23 | **30** | +7（TC-CTR-001/002/005/006/008 + 3 项 Part C 补强） |
| tests/test_utils.py | 8 | **14** | +6（TC-CTR-003 + 4 项边界/契约补强 + 1 项全仓副本收敛守卫[ADJ-009]） |
| tests/commands/test_diff_trace_hyphen.py | 0 | **2** | +2（TC-CTR-004a/004b，新文件） |
| tests/commands/test_validate.py | 8 | 8 | 0（回归保护） |
| **合计** | 39 | **54** | **+15** |

### 3.2 全量回归（相对基线）

| 运行 | 结果 | 说明 |
|---|---|---|
| 基线 `c99ef7d`（干净 worktree `D:/tools/_stdd_head_baseline`） | 14 failed / 859 passed / 8 skipped | 环境性预存在失败 |
| 修复前（仅 glob 修复，未含 C2 补丁） | 12 failed / 870 passed / 7 skipped | — |
| 修复后（含 ADJ-009 终态，串行重跑 882.80s） | **11 failed / 878 passed / 7 skipped** | 提交前终态，见下方归因 |
| **交付后（commit `d20994b`，串行 652.83s）** | **10 failed / 879 passed / 7 skipped** | `test_a6` 如预期**转绿**（ADJ-005 闭环）；10 项均为基线同名预存在 ⇒ **真实新增失败 0**。采集总数仍 896（提交未增删用例） |

**增量算术自洽校验**（证明新增用例全部计入且无额外夹带）：

```
基线合计 14+859+8 = 881        终态合计 11+878+7 = 896
采集增量 896-881 = +15  ← 恰等于本 change 新增 15 个测试
通过数   859 + 15(新增) + 3(基线失败转通过) + 1(基线 skip 转通过) = 878 ✓
失败数   14 - 3 = 11 ✓          跳过数 8 - 1 = 7 ✓
```

**11 项失败归因**：

- **10 项** 与基线失败**逐一同名** ⇒ 预存在，非本 change 引入。
- **1 项** `test_a6_no_stray_untracked_files` ⇒ **瞬态**（ADJ-005）：该测试仅豁免 `.fstdd/changes/` 下的未跟踪项，而本 change 新增的 `upstream/tests/commands/test_diff_trace_hyphen.py` 尚未提交，故判红。**已于交付后（commit `d20994b`）复证转绿**（见 §十一）。
- **真实新增失败：0**。

> 说明：此前记录的「11 failed / 871 passed」为 C1 补强前的中间态；ADJ-006/007/008/009 陆续补入 7 个用例后终态为 **878 passed**，失败集合与归因不变。

> **C2 捕获的真实回归 1 项（已修复）**：`test_cross_cutting_verification.py::TestCValidateTcIds::test_c3_validate_source_uses_scoped_regex` 曾在「validate.py 切换共享常量」时转红（基线 PASS）——该源码守卫测试要求 validate.py 内含定义行正则**字面量**，与「共享常量」互斥。已回退 validate.py 为内联字面量（同表达式）+ 双向同步注释，回归 design D3 原案。详见 **ADJ-001**；复跑后 69 passed。

### 3.3 静态检查

| 工具 | 范围 | 基线 | 终态 | 结论 |
|---|---|---|---|---|
| ruff | `upstream/fstdd/cli/` 全目录 | 128 | 128 | **零新增**（规则码分布逐项一致） |
| ruff | 本 change 5 个生产文件 | 16 | 16 | **零新增**（行号归一后错误集合逐条一致） |
| ruff | 本 change 7 个有 HEAD 对照的文件（5 生产 + test_ci + test_utils） | 17 | 17 | **零新增**（行号归一后逐条一致） |
| ruff | 新增 `tests/commands/test_diff_trace_hyphen.py` | — | 0 | `All checks passed!` |
| mypy | 全包 | 80 | 80 | **零新增** |

ruff 17 项明细均为预存在历史问题（`F401`/`F541`×/`F841`×/`E741`×/`E701`×），**无一项落在本 change 新增行**；行号位移（如 `ci.py:474→480`、`validate.py:126→130`）由新增代码行导致，非新错误。

> 记录校正：`phase-context.md` 中 Slice 1 曾记 ruff「8 项」、Slice 2 记「9 项」，本报告初版曾记「19 项」，均为不同选取范围下的计数；**权威口径为「与 HEAD 逐条比对、零新增」**，本报告 §3.3 以此为准（见 ADJ-004）。2026-10-17 于两 worktree 复测：7 文件 **17 = 17**、5 生产文件 **16 = 16**、新文件 0，三口径全部零新增（此前的「19」为误计；注意 `[*] N fixable` 是 ruff 的可自动修复子集，非错误总数，`--fix` 前不可据此判读数）。

---

## 四、SC ↔ TC ↔ 测试函数 覆盖矩阵（9/9）

| SC | 规格 THEN 要点 | TC | 测试函数 | 判定 |
|---|---|---|---|---|
| SC-CTR-001 | 连字符文件承载 planned TC → 覆盖 PASS | TC-CTR-001 | `test_ci.py::TestTcImplementationCoverageRecognition::test_tc_coverage_hyphen_named_file_recognized` | ✅ |
| SC-CTR-002 | 双命名均无实现 → 仍 FAIL（不放宽判据） | TC-CTR-002 | 同 :: `test_tc_coverage_real_gap_still_fails` | ✅ |
| SC-CTR-003 | 两命名全产出无重复 + docstring 声明唯一修改点 | TC-CTR-003 | `test_utils.py::test_iter_test_files_recognizes_both_naming_patterns` + `::test_iter_test_files_docstring_declares_single_source` | ✅ |
| SC-CTR-004 | diff 不显示「未覆盖」；trace 定位文件与函数 | TC-CTR-004a/b | `test_diff_trace_hyphen.py::TestDiffTraceHyphenRecognition::test_trace_finds_hyphen_named_test_file` / `::test_diff_fills_test_function_for_hyphen_named_file` | ✅ |
| SC-CTR-005 | 多处引用 + 定义行恰一条 → PASS | TC-CTR-005 | `test_ci.py::TestTcidUniqueDefinitionRow::test_tcid_unique_allows_cross_references`（+ `::test_non_template_plan_warns_not_fails` 语义钉死） | ✅ |
| SC-CTR-006 | 两定义行共用 ID → FAIL 并列出该 ID | TC-CTR-006 | 同 :: `test_tcid_unique_two_definition_rows_fail`（断言 msg 含 `TC-UNI-002`） | ✅ |
| SC-CTR-007 | 10 归档 change (d) 0 误报 | TC-CTR-007 | `test_ci.py::TestTcidUniqueArchivedCorpus::test_archived_changes_no_duplicate_tc_ids` | ✅ 已自动化（ADJ-008） |
| SC-CTR-008 | TC-CI-008 新语义通过 + 审计注释在位 | TC-CTR-008 | `test_ci.py::TestTcidUniqueArchivedCorpus::test_tc_ci_008_fixture_migrated_with_audit_trace`（+ `TestCiCheckFailures::test_check_failures_detects_duplicate_tc_ids` 本体） | ✅ |
| SC-CTR-009 | 下游归档 change 修复前后对比 | TC-CTR-009 | 无自动化（跨仓依赖）⇒ 执行取证，见 §5.2 | ✅ 已取证 |

**自动化覆盖 8/9**；SC-CTR-009 为跨仓依赖（依赖下游 `D:/tools/多层次agent` 的归档 change），以执行取证替代，证据固化于 §5.2。

---

## 五、真实数据验收

### 5.1 SC-CTR-007 — 10 个历史归档 change（本仓 `EXP-20260917-A1` 证据表）

**独立复现**（对同一 10 个 change 分别用 HEAD 代码与修复后代码直调 `check_tcid_unique`）：

```
--- HEAD c99ef7d: (d) PASS 0/10 ---
    crlf-eol-governance FAIL / rename-to-fstdd FAIL / skill-engineering-standards FAIL
    contract-auto-share FAIL / inbox-review-sync FAIL / install-source-repo FAIL
    canonical-in-workspace FAIL / distributed-task-coordination FAIL
    migrate-to-d-drive FAIL / server-bare-repo-mirror FAIL
--- 修复后: (d) PASS 10/10 ---
```

| 检查项 | HEAD `c99ef7d` | 修复后 |
|---|---|---|
| (d) `check_tcid_unique` | **0/10 PASS**（10/10 误报「重复 TC-ID」） | **10/10 PASS** ✅ |

> 该验收已由**手工取证升级为自动化回归测试** `TestTcidUniqueArchivedCorpus::test_archived_changes_no_duplicate_tc_ids`（ADJ-008，C1-test 🟠 F1 处置）。

### 5.2 SC-CTR-009 — 下游归档 change（跨仓，含**规格修正**）

对象：下游 `D:/tools/多层次agent/.fstdd/archive/2026-10-16-default-free-fixture`（tests/ 全为连字符命名）。

**独立复现**（对同一 change 分别用 HEAD 代码与修复后代码直调两个检查器）：

| 检查项 | HEAD `c99ef7d` | 修复后 |
|---|---|---|
| (d) `check_tcid_unique` | `('PASS', '(d) TC-ID 唯一 (10 个)')` | `('PASS', '(d) TC-ID 唯一 (6 个)')` |
| TC 实现覆盖 | `('FAIL', 'TC 实现覆盖严重不足: 0/10 (0%)。缺失: TC-DFJ-001, …')` | `('WARN', 'TC 实现覆盖: 9/10 (90%)。缺失: TC-EPR-002')` |

> **⚠️ 规格修正（放行必办项，C1-docs 🟡 #6）**
>
> SC-CTR-009 的 GIVEN「修复前实测 (d) FAIL」与 THEN「(d) SHALL 由 FAIL 转 PASS」**与实测不符**：
> - `(d)` 修复前**即为 PASS**（该 change 全文无重复 TC-ID 字面），修复后的改善是**计数 10 → 6**（回归真实定义行），**不是** FAIL→PASS；
> - 真正的 **FAIL → 非 FAIL 跃迁发生在「TC 实现覆盖」检查**：`0/10 (0%)` → `9/10 (90%)`。
>
> 该失实前提**不予改写** Gate 2 已确认的 canonical spec（遵循既有惯例，参见 `archive/2026-09-17-mirror-failure-alert` ADJ-007），改由 **本报告 + Gate 3 确认项显式承接**，并在 `test-plan.md` 案例 3.2 加交叉引用（「实测修正见 ADJ-003 / tasks 4.2」）。
> 修正留痕位置：`design-adjustments.yaml` ADJ-003、`tasks.md` 4.2、`phase-context.md` Slice 2、`test-plan.md` 案例 3.2。
>
> 唯一缺失 `TC-EPR-002` 为模板引用，**成因不变**（修复前后一致），非本 change 引入。

---

## 六、变异验证（EXP-2026-0013 纪律：备份 + sha256 校验 + 串行执行）

| 变异维度 | 变异体 | 被杀测试 | sha256 还原校验 |
|---|---|---|---|
| **(d) 口径**（BUILD 阶段，主代理） | `ci.py` 新正则还原为**全文口径** | TC-CTR-005（转红） | `a07d9434…dab9` ✅ |
| **glob 识别**（C1 阶段，test-reviewer 独立） | `utils._TEST_FILE_PATTERNS` 回退为 `("test_*.py",)` | TC-CTR-001 / TC-CTR-003 / TC-CTR-004a / TC-CTR-004b（4 killed） | `a903c971…` ✅ |
| **定义行常量漂移**（D-01 修复后，主代理） | `utils.TC_ID_DEFINITION_ROW_PATTERN` 的 `\d{3}` → `\d{3,4}` | 新增全仓副本守卫（ADJ-009）+ ADJ-007 等价守卫（**双双转红**并报「与常量漂移」） | `3c48a16f…` ✅ |

**存活项符合预期**：TC-CTR-002（缺口守卫，修复前后均预期 FAIL，不受 glob 变异影响）、TC-CTR-006/008（(d) 口径守卫，(d) 变异下保持绿）。
两轮变异的生产文件均**逐字节还原**，未带病离场。

---

## 七、C1 三路并行技术评审结论与处置

| 维度 | 报告 | 结论 | 发现 | 处置 |
|---|---|---|---|---|
| code | `reviews/c1-code-2026-10-17.md` | **PASS** | 0🔴 / 0🟠 | — |
| test | `reviews/c1-test-2026-10-17.md` | CONDITIONAL | 2🟠（SC-CTR-007 未自动化；subprocess 编码未对齐）+ 4🟡 + 4🟢 | **ADJ-008**（补 `TestTcidUniqueArchivedCorpus`）+ **ADJ-006**（`_run_cli` 加 `encoding="utf-8"` / `errors="replace"` / `PYTHONIOENCODING` / `timeout=120`）+ docstring 断言 + `TC-UNI-002` 断言补强 |
| docs | `reviews/c1-docs-2026-10-17.md` | CONDITIONAL | 3🟠（`.fstdd.yaml` count 矛盾；design-adjustments schema 偏离；tasks 4.4 基线表述）+ 5🟡 + 3🟢 | count→8；design-adjustments 重写为完整 schema（8 条，含 `original/actual/reason/impact/evidence`）；tasks 4.4 改为「相对基线无新增失败」；🟡 逐条修正 |

**C1 → C2 补强效果**：补强后受影响套件 69 → **77 passed**；ruff 与 mypy 仍零新增。
**六方编号一致性**（REQ↔SC↔TC↔CP↔canonical↔Human View）经 C1-docs 核对**通过**。

---

## 八、C3 diff 审查结论

> 报告（两份并列）：
> - `reviews/c3-diff-2026-10-17.md` — **team-lead 独立复核**（原派 code-reviewer 子代理 running 超时 ~10 分钟无产出，team-lead 先行收口；该文件曾于 08:25 被覆盖，已重建）
> - `reviews/c3-diff-code-2026-10-17.md` — **code-reviewer 独立审查**（同结论 PASS，另记 2🟡 / 3🟢）
>
> 独立性补充：**代码质量维度**另有 C1-code（`c1-code-2026-10-17.md`，PASS，0🔴/0🟠）；**diff 阅读**另有 C4（`c4-failure-modes-2026-10-17.md`）覆盖。

**结论：PASS**（0🔴 / 0🟠）

| 审查项 | 结果 | 证据（可复跑） |
|---|---|---|
| 调试残留（print / pdb / breakpoint / TODO / FIXME / XXX） | ✅ 无 | 新增行命中 `0`；旧实现为**删除**（`-` 行）而非注释保留 |
| 死代码 / 注释掉的旧逻辑 | ✅ 无 | 三处调用点为「注释说明旧行为 + 新调用」（`ci.py:560`、`diff.py:100`、`trace.py:96`） |
| 裸 `rglob("test_*.py")` 残留 | ✅ 活调用清零 | 全目录 24 处 `rglob` 逐条分类：唯一测试扫描点为 `utils.py:78`（单一事实源本身）；其余为注释/docstring（7 处）或无关 `*.md`/`*.py`/`*` 调用 |
| `validate.py:83` 内联正则 ↔ `utils.py:63` 常量 | ✅ 逐字节等价 | 解析后均为 `r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})"`；守卫测试 `test_tc_id_pattern_matches_validate_literal` 钉死 |
| 新文件 subprocess 防护 | ✅ 齐备 | `encoding="utf-8"` + `errors="replace"` + `env PYTHONIOENCODING=utf-8` + `timeout=120` + `cwd=tmp_path` + `sys.executable`（ADJ-006） |
| 范围夹带 | ✅ 无 | 见下 |

**范围声明（已识别并排除）**：工作树含 **16 个 `.fstdd/changes/2026-10-03-release-validation-framework/*` 的未暂存删除**（` D`）。取证：该 change 由 `d409196` 创建、`f1a2bf2`（`chore(archive): 归档 release-validation-framework change`）归档到 `.fstdd/archive/`，其 `.fstdd.yaml` 与 archive 副本 `diff` 一致；独立报告另证新测试与该 16 项**零引用耦合**（`grep 2026-10-03 upstream/tests/` 无命中）。⇒ **与本 change 无关**，**不计入本次审查**，且 **DELIVER 提交时必须用显式 pathspec** 排除（见 §十一）。

### 8.1 独立报告（code-reviewer）的 🟡 发现

| ID | 位置 | 内容 | 处置 |
|---|---|---|---|
| **D-01** | `commands/diff.py:45` | **第 3 份定义行正则内联副本**（`re.search(r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})", line)`）；等价守卫只覆盖 `utils↔validate` ⇒ 常量变更时 `diff` 口径静默漂移（EXP-20260917-A1 复发通道） | **取证为预存在**（`git show HEAD:...diff.py` 第 45 行已有该正则）。**用户于 Gate 3 裁定「先修 D-01 再放行」⇒ 已由 ADJ-009 修复并验证**，见 §8.2 |
| **D-02** | 工作区 | DELIVER 清单须显式登记 4 项 `.fstdd/experiences/` 改动 + 1 个新增测试文件（与已排除的 16 项删除分开陈述） | **采纳**，见 §十一-7 |

🟢 D-03（注释仍含 `rglob("test_*.py")` 字面量）/ D-04（`seen`+`resolve()` 去重当前不可达，防御性代码）/ D-05（`TestTcidUniqueArchivedCorpus` 依赖仓库归档数据集）均**接受不改**，维护责任已记 §十一。

独立报告支持证据：当前修订 `pytest tests/commands/ tests/test_utils.py -q` = **459 passed**（较 C1 轮 453 增 6，全绿）；ruff 新增行命中 `0`；归档语料 10/10 可复现。

### 8.2 D-01 修复（ADJ-009，Gate 3 用户裁定纳入）

**改动**：
- `commands/diff.py:45` 由内联字面量改为引用 `utils.TC_ID_DEFINITION_ROW_PATTERN`（并在 `cmd_diff` 内补该常量的 import）。
- 新增 `tests/test_utils.py::test_tc_id_definition_row_copies_confined_to_constant_and_validate`：`ast` 扫描 `upstream/fstdd/` 全部 `.py` 的字符串字面量，筛出「定义行 TC-ID 正则」（判据：去转义后含 `**ID**` 且原值含 `TC-`），断言 ① 副本位置集合恰为 `{cli/utils.py, cli/commands/validate.py}`、② 每份与常量逐字节相等。

**验证（全部可复跑）**：

| 项 | 方法 | 结果 |
|---|---|---|
| RED | 修复前跑新守卫 | ❌ 失败，`locations` 含 `cli/commands/diff.py`（副本 3 处） |
| GREEN | 修复后跑新守卫 | ✅ 通过（副本收敛为 2 处） |
| **行为等价** | 4 个含 TC 定义行的归档 change，两 worktree 各跑 `fstdd diff` 并逐字节比对 | ✅ **完全一致**（28/20/18/11 行，均正常解析出 TC-ID 行） |
| 变异验证 | 常量 `\d{3}`→`\d{3,4}` | ✅ 新守卫 + ADJ-007 守卫**双双转红**并报漂移；sha256 `3c48a16f…` 逐字节还原 |
| 假阳排查 | 确认 `validate.py:96` 的锚点-only 正则 `\*\*ID\*\*\s*\|`（统计案例行数用，非提取 TC-ID）不被误纳入 | ✅ 判据含 `TC-` 要求，正确排除 |
| 静态检查 | ruff 7 文件 vs HEAD | ✅ `17 = 17` 零新增 |
| 受影响套件 | 6 文件（含 diff/trace） | ✅ **63 passed** |
| 独立复验 | 另派子代理独立验证（报告 `reviews/c3-d01-verify-2026-10-17.md`） | ✅ **PASS**（正确性/行为等价 4/4 逐字节一致/变异红-还原 sha256 复核/无假阳/无假阴/63 passed 全部复现；ruff 实测 17=17） |

> 影响：生产代码定义行正则副本 **3 → 2**；**行为零变化**（引用与字面量逐字节等价）。

---

## 九、C4 失败模式检查（全量）

> 报告：`reviews/c4-failure-modes-2026-10-17.md`

### 9.1 14 类通用失败模式

| # | 失败模式 | 结论 | 依据（摘要） |
|---|---|---|---|
| 1 | hallucination | ✅ | 所有导入符号实存（`utils.py:63,66`），调用点路径正确 |
| 2 | overtrust | ✅ | `iter_test_files` 对不存在目录产出空；三处调用点先 `tests_dir.exists()` |
| 3 | prompt-injection | ✅ | CLI 工具代码，无 LLM prompt 处理路径 |
| 4 | memory-pollution | ✅ | 函数局部 `seen` 集合；常量不可变；无模块级可变状态 |
| 5 | context-overflow | **SKIPPED** | 非 LLM 任务，无 context window 语义 |
| 6 | tool-drift | ✅ | 三处调用点统一经 helper；全仓裸 `rglob` 直扫点清零 |
| 7 | credential-leak | ✅ | 无凭据/密钥处理 |
| 8 | privilege-bypass | ✅ | 无权限/授权逻辑 |
| 9 | race-condition | ✅ | 无共享可变状态；测试隔离（tmp_path / monkeypatch.chdir / subprocess） |
| 10 | path-traversal | ✅ | `tests_dir = project_root / "tests"` 固定子目录，非用户输入 |
| 11 | cross-session-state | ✅ | 无持久化状态/跨 session 缓存 |
| 12 | output-truncation | ✅ | `capture_output=True` + 子串断言，无截断依赖 |
| 13 | malformed-output | ✅ | `is_file()` 过滤目录条目（实测 `test_dir.py` 目录被跳过），防 `IsADirectoryError`；不存在目录 → 空产出 |
| 14 | circular-dependency | ✅ | 依赖单向（`utils` 不 import `commands/*`），无循环导入 |

**小结：13 ✅ + 1 SKIPPED + 0 ❌**

### 9.2 8 类金融特有失败模式

**全部 SKIPPED** — 依据：`test-plan.md:189`「非金融项目（FINANCIAL_PROJECT=NO）」；`.fstdd/config.d/project.yaml` 无 `financial` 标记；本 change 修改对象为 FSTDD CLI 通用工具，不承载金额/币种/账务/时区结算/权限矩阵/审计留痕/PII/幂等语义。

---

## 十、C6 设计偏离汇总（`design-adjustments.yaml`，8 条）

| ID | 偏离 | 处置状态 |
|---|---|---|
| ADJ-001 | `validate.py` 由「切换共享常量」回退为「内联同表达式字面量」——源码守卫测试 `test_c3` 要求字面量存在，二者互斥 | 已回退 + 双向同步注释；新增一致性守卫测试 |
| ADJ-002 | TC-CTR-008 首版源码扫描断言**自指污染**（docstring/断言串自匹配） | 改 `inspect.getsource` 限定函数体 + 运行时字符串拼接 |
| ADJ-003 | SC-CTR-009 规格 THEN「(d) FAIL→PASS」**失实** | 留痕 ADJ-003 + tasks 4.2 + test-plan 3.2 + 本报告 §5.2；不改写 Gate 2 canonical |
| ADJ-004 | Slice 1 记录的 ruff「8 项」为**误计** | 修正为与 HEAD 逐条比对（16 项全预存在，零新增） |
| ADJ-005 | `test_a6_no_stray_untracked_files` 因新增未跟踪测试文件转红 | 判定为 BUILD 期**瞬态**，DELIVER 提交后复证 |
| ADJ-006 | `iter_test_files` 需过滤目录条目 + `diff.py` 日志变量泄漏（`py_file` → `test_file`） | 加 `is_file()` 防御；修正日志变量 |
| ADJ-007 | 常量 ↔ validate.py 内联字面量缺一致性守卫 | 新增 `test_tc_id_pattern_matches_validate_literal` |
| ADJ-008 | SC-CTR-007 未自动化（数据可自动化）；subprocess 编码未对齐；断言不完整 | 补 `TestTcidUniqueArchivedCorpus`；`_run_cli` 对齐既有 `run_cli` 模式；补 docstring / `TC-UNI-002` 断言 |

**C5 经验库**：新增 `EXP-2026-0014`（cross_system_mismatch：行为等价重构仍可能让源码文本断言的守卫测试转红）、`EXP-2026-0015`（tool_misuse：`experience add --dry-run` 实际写盘）；`EXP-20260917-A1` 记 `occurrences: 1→2` 并追加「采纳记录」（30 天前经验本 change 落地）。索引 `.experience-index.yaml` total 65。

---

## 十一、已知局限与后续

| # | 局限 | 影响 | 处置 |
|---|---|---|---|
| 1 | **本仓 tests 布局假设**：覆盖检查扫 `<root>/tests/`，而本仓测试在 `upstream/tests/` | 本 change 自身的 planned TC 覆盖检查**不随 glob 修复转绿**（仍 FAIL） | Gate 2 已确认的已知局限；真实数据验收放下游仓（§5.2） |
| 2 | ~~**`test_a6` 瞬态红**~~ **已闭环** | 全量回归中 1 项瞬态失败 | 交付后（`d20994b`）复跑 **1 passed**；全量 11F→**10F/879P/7S**（ADJ-005） |
| 3 | **(d) 计数粒度**：`AND` 语义按 per-SC 而非 per-file | 后续若同 SC 跨多文件，计数口径需再评估 | 记录为后续改进候选（非本 change 范围） |
| 4 | **`experience add --dry-run` 仍写盘**（CLI 缺陷，EXP-2026-0015） | 预览模式有副作用 | 记录为**新的候选 change** |
| 5 | SC-CTR-009 跨仓依赖 | 无法自动化 | 以执行取证替代（§5.2），test-plan 已显式标注 |
| 6 | ~~**定义行正则存在第 3 份副本**：`commands/diff.py:45`~~ **已收口**（独立报告 D-01） | 原风险：等价守卫只覆盖 `utils↔validate` ⇒ 日后改常量时 `diff` 口径会**静默漂移**（EXP-20260917-A1 类缺陷复发通道） | **用户 Gate 3 裁定「先修 D-01 再放行」⇒ 已由 ADJ-009 修复**：`diff.py:45` 改引用同一常量 + 新增「全仓副本集合」守卫（副本 3→2）。验证见 §8.2，**不再是遗留项** |
| 7 | **交付清单登记项**（独立报告 D-02） | 4 项 `.fstdd/experiences/` 改动 + 1 个新增测试文件不在「8 文件」清单内，易在 DELIVER 阶段被误判为夹带或漏登记 | **采纳**：DELIVER 清单显式登记这 5 项，与已排除的 16 项预存在删除**分开陈述** |
| 8 | `TestTcidUniqueArchivedCorpus` 以仓库 `.fstdd/archive/` 10 个 change 为数据集（D-05） | 归档迁移/清理会使其转红（失败信息已指向 EXP-20260917-A1 表，可诊断） | 接受；维护责任记于本表。已核实 10/10 存在且被 git 追踪 ⇒ CI 可复现 |
| 9 | **副本守卫可被字符串拼接绕过**：守卫只扫 `ast.Constant` 字面量，`r"\*\*ID\*\*\s*\|\s*(" + r"TC-[A-Z]+-\d{3})"` 这类拼接构造不在扫描内（独立验证者已给最小复现） | 属**刻意规避**才能触发；D-01 的真实形态（复制粘贴字面量）100% 被捕获 | 接受为 AST 字面量级守卫的固有边界（同类守卫 `test_tc_id_pattern_matches_validate_literal` 亦如此）；不阻塞放行，已记于验证报告 §4c |

---

## 十二、放行建议与 Gate 3 确认项

**建议：放行**（进入 Phase 4 DELIVER）。

**Gate 3 须确认的事项（3 项）**：

1. **SC-CTR-009 规格修正承接** — 认可「SC-CTR-009 THEN 中 `(d) FAIL→PASS` 失实；实际 FAIL→非 FAIL 跃迁在**覆盖检查** `0/10→9/10`，`(d)` 为计数 `10→6` 且修复前即 PASS」这一修正，并接受**不改写 Gate 2 canonical spec、由本报告承接**的处置方式。
2. **接受 1 项瞬态红（ADJ-005）** — `test_a6_no_stray_untracked_files` 在提交前为红，DELIVER 提交后复证转绿。
3. **接受 3 项已知局限** — 本仓 tests 布局假设（§11-1）；SC-CTR-009 以执行取证替代自动化（§11-5）；副本守卫拼接绕过边界（§11-9）。

> **D-01 已闭合**（原第 4 项）：用户 Gate 3 裁定「先修 D-01 再放行」⇒ 已由 **ADJ-009** 修复（`diff.py:45` 第 3 份副本收敛为常量引用 + 新增全仓副本集合守卫），并经**独立子代理复验 PASS**（`reviews/c3-d01-verify-2026-10-17.md`：正确性 / 4 个归档 change 行为逐字节一致 / 变异红-还原 sha256 复核 / 无假阳 / 无假阴 / 63 passed 全部复现）。**不再是待确认项。**

**DELIVER 阶段待办（承接项）**：

- `fstdd archive` 后**手工合并 canonical** 到 `.fstdd/canonical/{proposals,specs/{agent,code}}/` 并手编 `.canon-index.yaml`（该目录当前**为空**）。
- 提交须用**显式 pathspec**，排除 16 个 `2026-10-03-release-validation-framework/*` 预存在删除。
- 提交后回填 `traceability` / `complexity_score` / `design_adjustments.count`（`gate approve` 会重置，须最后手填）。
- 提交后复证 `test_a6` 转绿。

---

*报告生成：team-lead（FSTDD Phase 3 Part C C7）| 2026-10-17 | 证据来源：主代理独立复现 + C1/C3/C4 评审报告*
