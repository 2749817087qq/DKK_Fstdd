# 设计调整记录 — ci-checker-tc-recognition

**change**：2026-10-16-ci-checker-tc-recognition
**Gate**：3（build → deliver）
**日期**：2026-10-17
**基线**：`c99ef7d`（worktree `D:/tools/FSTDD/FSTDD005-wt-311`）
**Canonical 对照**：`design-adjustments.yaml`（AI 主读，逐条含 `original/actual/reason/impact/evidence`）

> 本文件记录 **BUILD 阶段相对原设计的偏离与调整**，供 Gate 3 确认（Human View）。
> 原则：**只记录「与 design.md 不一致」或「设计未覆盖但必须做」的项**，逐条给出依据与影响。
> 共 **9 项**：3 项原设计缺口（ADJ-001/002/003）、1 项记录更正（ADJ-004）、1 项瞬态状态（ADJ-005）、3 项 C1 评审驱动补强（ADJ-006/007/008）、1 项 C3 评审发现并经 **Gate 3 用户裁定纳入**的范围扩围（ADJ-009）。
> **无需回到 Phase 2 重做规格**（`requires_re_spec: false`），**无需重做 Phase 3 实现**（`requires_re_build: false`）。

---

## 调整汇总

| # | 调整类型 | 涉及文档 | 严重程度 | 阶段 | 影响 TC | 状态 |
|---|---|---|---|---|---|---|
| ADJ-001 | 技术方案变更（回退） | design.md D3 / validate.py | Medium | Phase 3 | TC-CTR-005/006 | fixed |
| ADJ-002 | 测试方案变更 | test_ci.py | Minor | Phase 3 | TC-CTR-008 | fixed |
| ADJ-003 | spec 期望修正 | SC-CTR-009 | Minor | Phase 3 | TC-CTR-009 | fixed（不改 canonical，由 test-report 承接） |
| ADJ-004 | 记录更正 | phase-context / test-report | Trivial | Phase 3 | — | fixed |
| ADJ-005 | 瞬态状态 | 验收判据 | Minor | Phase 3→4 | — | accepted（DELIVER 后复证） |
| ADJ-006 | 健壮性加固（原设计未覆盖） | utils.py / diff.py | Minor | Phase 3 | TC-CTR-003/004 | fixed |
| ADJ-007 | 测试方案变更（守卫） | test_utils.py | Minor | Phase 3 | TC-CTR-005/006 | fixed |
| ADJ-008 | 测试方案变更（补强） | test-plan / test_ci / test_utils / hyphen | Medium | Phase 3 | TC-CTR-003/006/007 | fixed |
| ADJ-009 | 范围扩围（Gate 3 用户裁定） | diff.py / test_utils.py | Minor | Phase 3 | TC-CTR-004 | fixed |

---

## A-01 · `validate.py` 由「共享常量」回退为「内联同表达式字面量」（ADJ-001）

| 项 | 原设计 | 调整后 |
|---|---|---|
| 方案 | design.md **D3**：`ci.py` 与 `validate.py` 的 TC-ID 定义行正则「**逐字复制**」；落地中途曾升级为 `utils.TC_ID_DEFINITION_ROW_PATTERN` **共享常量**（validate.py 亦切常量引用） | `validate.py` **回退**为同表达式**内联字面量**；`ci.py` 保留常量引用；`utils.py`/`ci.py`/`validate.py` 三处注释互相引用「须同步修改」 |
| 依据 | **C2 全量回归比对**（`b2Ne34` vs HEAD 基线）发现 validate.py 的常量切换**破坏仓库源码级守卫测试** `tests/test_cross_cutting_verification.py::TestCValidateTcIds::test_c3_validate_source_uses_scoped_regex`（该测试断言 validate.py **源码含定义行正则字面量**，防其回退到全文口径）。守卫测试属仓库既有不变量，**不得为迁就实现而放宽**。 | — |
| 影响 | 最终实现**回归 design D3 原案**（validate 内联 + ci 常量，值逐字节相等，行为零变化）；代价是正则存在 2 份副本 ⇒ 由 ADJ-007 等价守卫钉死同步 | — |

**证据**：复跑 `pytest tests/test_cross_cutting_verification.py` + ci/validate/utils = **69 passed**；code-reviewer 以 `ast.literal_eval` 实测两处**逐字节相等**（`c1-code-2026-10-17.md` §1）。

---

## A-02 · TC-CTR-008 断言范围收敛（自指免疫）（ADJ-002）

| 项 | 原设计 | 调整后 |
|---|---|---|
| 断言 | 读**整个** `test_ci.py` 源码，断言「定义行恰 2 条 + 审计注释在位 + 旧字面零残留」 | 改为 `inspect.getsource` **限定 TC-CI-008 单函数体**；期望字面在**运行时拼接** |
| 依据 | 首版断言被**自身文本污染**：docstring 内含目标字面使 `count=3≠2`；断言 3 的期望字面出现在断言自身源码中导致**自我命中**（RED 实测 `AssertionError`） | — |
| 影响 | 断言范围收敛到被测函数体，**检测力不变**（fixture 回退旧语义 → 计数 ≠2 转红） | — |

**证据**：首版 RED 实测（`tests/commands/test_ci.py:639 AssertionError`）；修复后 GREEN；test-reviewer 运行时复核「定义行计数 2、不含自身标识」，确认自指免疫可靠（`c1-test-2026-10-17.md` §三.3）。

---

## A-03 · SC-CTR-009 期望表述失实（ADJ-003）

| 项 | 原设计（Gate 2 锁定） | 实测修正 |
|---|---|---|
| 期望 | 下游归档 change 复现「**(d) FAIL→PASS**、覆盖 0/10→9/10」 | `(d)` **修复前即 PASS**（该 change 全文无重复字面），修复后为**计数 10→6**（回归真实定义行）；**FAIL→PASS 实际发生在 TC 实现覆盖** `0/10→9/10` |
| 依据 | 规格起草时把两处改善**混记为同一句**；执行期 HEAD CLI vs 修复 CLI **同 cwd 对比**实测澄清 | — |
| 影响 | 验收结论**不变**（覆盖检查修复效果实证），但「(d) FAIL→PASS」表述失实；按 `archive/2026-09-17-mirror-failure-alert` ADJ-007 惯例**不擅改 Gate 2 已确认 canonical**，由 **test-report §5.2 与 Gate 3 确认项显式承接** | — |

**证据**：`phase-context.md` Slice 2 实测记录（HEAD CLI `✓ (d) TC-ID 唯一 (10 个)` / 修复 CLI `✓ (6 个)`；覆盖 `✗ 0/10` → `⚠ 9/10`）；`tasks.md` 4.2 修正记录；`test-plan.md` 案例 3.2 交叉引用。

---

## A-04 · ruff 计数口径统一（ADJ-004）

| 项 | 值 |
|---|---|
| 原记录 | Slice 1「**8 项**全预存在」→ Slice 2「**9 项**」→ Part C 初稿「**17 项**」 |
| 权威口径 | **与 HEAD worktree 逐条比对**：5 个生产文件 **16 项**、7 个有 HEAD 对照的文件 **17 项**、新增 `test_diff_trace_hyphen.py` **0 项**；行号归一后错误集合与 HEAD **逐条一致** ⇒ **零新增** |
| 原因 | 三次记录分别取自不同文件范围与不同 ruff 输出行，未统一口径；且把 `[*] 9 fixable` **误当作错误总数** |
| 影响 | 结论（**零新增**）不变，仅计数口径统一；`phase-context.md` 与 `test-report.md` §3.3 已同步 |

**证据**：HEAD worktree 同命令比对 — `cli/` 全目录 `128=128`（规则码分布一致）、5 生产文件 `16=16`、7 文件 `17=17`、新文件 0 项；行号归一后集合 `diff` 为空。（2026-10-17 于两 worktree 复测确认 7 文件 `17=17`、5 生产文件 `16=16`；此前本表曾记「19」，为误计。）

---

## A-05 · `test_a6` 瞬态失败（ADJ-005）

| 项 | 说明 |
|---|---|
| 现象 | `tests/test_repo_home.py::TestAWorkspaceIntegrity::test_a6_no_stray_untracked_files` 失败 |
| 根因 | 该仓库卫生测试的判据是「**未跟踪垃圾**」（`??` 且路径不含 `.fstdd/changes/`）；本 change 新增的 `upstream/tests/commands/test_diff_trace_hyphen.py` 在 BUILD 期**尚为未跟踪**（另有 2 个新增经验文件同理） |
| 性质 | **BUILD 期瞬态，非行为回归**（HEAD 干净检出下该用例 PASS） |
| 处置 | DELIVER 提交纳管后应转绿 ⇒ **已列入 Gate 3 后复证项**（`git add` 后即消失） |

**证据**：HEAD worktree 该用例 PASS；两次全量（`b2Ne34`/`Okypgp`）中 FAIL，且失败清单仅此一项不在基线 14 项内（除已修复的 `test_c3`）。

---

## A-06 · helper 目录条目过滤 + `diff.py` 日志变量泄漏（ADJ-006）

| 项 | 原设计 | 调整后 |
|---|---|---|
| 目录条目 | REQ-CTR-001 未涉及 | `iter_test_files` 增加 **`is_file()` 过滤**（只产出文件，跳过名为 `test_x.py` 的**目录**）+ docstring 声明 |
| 日志变量 | 未涉及 | `diff.py` 日志 `py_file.name` → **`test_file.name`**（原变量为上一循环泄漏，日志指向错误文件） |
| 依据 | C1 code 评审 **F-01/F-04**：`rglob` 会产出目录条目（实测 `is_dir()==True`），`ci.py` 与 `trace.py` 裸 `read_text` 会抛 `IsADirectoryError` **直接崩溃**；该缺陷虽为既有（原 `rglob` 同样如此），但 helper 现已是**唯一事实源**，一行即可根治 |
| 影响 | helper 语义收紧为「只产出文件」（与 docstring 一致）；三处调用点不再有目录条目崩溃面；对既有 `test_*.py` 产出**零变化** |

**证据**：新增 `tests/test_utils.py::test_iter_test_files_skips_directory_entries`；`c1-code-2026-10-17.md` F-01/F-04。

---

## A-07 · 常量 ↔ validate 字面量等价守卫（ADJ-007）

| 项 | 原设计 | 调整后 |
|---|---|---|
| 同步机制 | design.md D3 假设「正则两份副本**靠注释同步**」 | 新增 `tests/test_utils.py::test_tc_id_pattern_matches_validate_literal`：从 `validate.py` 源码提取内联字面量并与 `utils` 常量**逐字节比对** |
| 依据 | C1 code 评审 **F-03**：既有守卫 `test_c3` 只断言「validate.py 源码含定义行正则**子串**」，**无法检出**「常量改了、validate.py 字面量没改」的漂移（EXP-20260917-A1 复发通道）。ADJ-001 回退后该通道**确实存在** |
| 影响 | 两份副本的同步由**可执行断言**保障；未来任一处置换会立即转红 |

**证据**：新增测试 GREEN；`c1-code-2026-10-17.md` F-03。

> ✅ 原已知残留（`commands/diff.py:45` 第 3 份副本）已由 **A-09 / ADJ-009** 收口：该处改为引用同一常量，并新增「全仓副本集合」守卫。

---

## A-08 · C1 评审驱动的测试补强（ADJ-008）

| 项 | 原设计 | 调整后 |
|---|---|---|
| ① SC-CTR-007 | 以「执行取证」覆盖（TC-CTR-007 标注 P0 但**无自动化**） | 新增 `TestTcidUniqueArchivedCorpus::test_archived_changes_no_duplicate_tc_ids` — EXP-20260917-A1 取证表内 10 个归档 change 逐个直调 `check_tcid_unique` 断言 PASS（0 误报） |
| ② subprocess 编码 | `_run_cli` 仅设 `timeout` | 对齐仓库既有 `run_cli` 模式（`encoding="utf-8"` + `PYTHONIOENCODING=utf-8` + `errors="replace"`） |
| ③ TC-CTR-003 断言 | 仅断言「全产出无重复」 | 补 **docstring 唯一修改点**断言 + 边界用例（目录条目跳过、嵌套子目录递归） |
| ④ TC-CTR-006 断言 | 仅断言 `status == "FAIL"` | 补「FAIL 消息**列出重复 ID**」断言（`TC-UNI-002`） |
| ⑤ 非模板写法 | 未覆盖 | 新增**非模板写法 → WARN** 语义钉死用例（固定已接受的取舍，防未来误判为回归） |
| 依据 | C1 test 评审 **F1**（🟠：P0 场景无自动化而数据在库内可读、**完全可自动化**）/ **F2**（🟠：subprocess 未按既有模式指定编码，跨 locale/CI 有解码不稳定风险）/ F3/F4（🟡：THEN 断言不完整）+ C1 code 评审 F-02（🟡：建议把「非模板写法 → WARN」固化为测试） |
| 影响 | 自动化覆盖 **7/9 → 9/9 SC**（SC-CTR-009 为跨仓依赖，保留执行取证并显式标注）；新增 6 个测试（test_ci +2、test_utils +4） |

**证据**：`pytest tests/commands/test_ci.py tests/test_utils.py tests/commands/test_diff_trace_hyphen.py tests/commands/test_validate.py tests/test_cross_cutting_verification.py` = **77 passed**。

---

## A-09 · `diff.py` 第 3 份正则副本收敛 + 全仓副本守卫（ADJ-009，**Gate 3 用户裁定纳入**）

| 项 | 原设计 | 调整后 |
|---|---|---|
| 范围 | REQ-CTR-002 只要求「`check_tcid_unique` 与 `validate.py:82-88` 两处口径统一」（design D3「逐字复制」）；ADJ-007 的等价守卫亦只覆盖这 2 处 | `commands/diff.py:45` 的第 3 份内联副本改为**引用** `utils.TC_ID_DEFINITION_ROW_PATTERN`（并补 import）；新增**全仓副本收敛守卫** `test_tc_id_definition_row_copies_confined_to_constant_and_validate` |
| 依据 | C3 独立评审 **D-01**：`diff.py:45` 的副本未被等价守卫覆盖 ⇒ 日后改常量时 `diff` 口径**静默漂移**（`diff` 与 `ci`/`validate` 口径再次分裂，即 EXP-20260917-A1 的**复发通道**）。该副本经取证为**预存在**（`git show HEAD:...diff.py:45` 已有），本 change 原未触碰 | 用户在 Gate 3 明确裁定「**先修 D-01 再放行**」⇒ 属**用户批准的范围扩围** |
| 守卫判据 | — | `ast` 扫描 `upstream/fstdd/` 全部 `.py` 的字符串字面量，筛出「定义行 TC-ID 正则」（去转义后含 `**ID**` 且原值含 `TC-`），断言：① 副本位置集合恰为 `{cli/utils.py, cli/commands/validate.py}`；② 每份与常量**逐字节相等**。新增第 3 份副本 ⇒ 立即转红 |
| 影响 | — | 生产代码定义行正则副本 **3 → 2**（常量 + validate 内联，后者为源码级守卫 `test_c3_validate_source_uses_scoped_regex` 所必需）；**行为零变化**（引用与字面量逐字节等价） |

**证据**：
- **RED**：新守卫在修复前失败，`locations = ['cli/commands/diff.py', 'cli/commands/validate.py', 'cli/utils.py']` → 修复后 GREEN。
- **行为等价**：4 个含 TC 定义行的归档 change（`contract-auto-share` / `inbox-review-sync` / `canonical-in-workspace` / `crlf-eol-governance`）的 `fstdd diff` 输出与 HEAD worktree **逐字节一致**（28/20/18/11 行，且均正常解析出 TC-ID 行）。
- **变异验证**（EXP-2026-0013 纪律）：常量 `\d{3}`→`\d{3,4}` ⇒ 本守卫与 ADJ-007 守卫**双双转红**并报「与常量漂移」；`utils.py` sha256 `3c48a16f…` **逐字节还原**。
- **静态检查**：ruff 7 文件 `17 = 17` 零新增；受影响 6 套件 **63 passed**。

---

## 未调整项（与原设计一致）

- **REQ-CTR-001**（三处调用点统一经 `iter_test_files`）：按原设计交付，无偏离。
- **REQ-CTR-002**（`check_tcid_unique` 定义行口径，与 `validate.py:82-88` 逐字一致）：按原设计交付；`validate.py` 侧回退见 A-01。
- **判据不放宽**：planned TC 双命名均无实现仍 FAIL（TC-CTR-002）；两案例定义行共用 ID 仍 FAIL（TC-CTR-006）。
- **本仓 tests 布局假设**（覆盖检查扫 `<root>/tests/`）：Gate 2 已确认的已知局限，未调整。

## 风险与回滚

| 项 | 说明 |
|---|---|
| 风险 | **低**。核心改动是**识别面扩大**（多扫一种文件名）+ **口径收窄**（全文→定义行），真实判据与阈值未动；ADJ-006 只收紧 helper 语义（跳过目录条目，原行为是崩溃）；ADJ-007/008 为**纯测试新增** |
| 回滚 | 改动集中在 5 个生产文件；`git revert` 本 change 提交即可。三处调用点切换是同一 helper 的三个调用，可整体回滚 |
| 回归 | 全量 `pytest upstream/tests/` 相对基线 `c99ef7d`（14F/859P/8S）**无新增失败**（详见 `test-report.md` §3.2） |
| 遗留 | ADJ-005 瞬态（提交后复证）。`diff.py:45` 第 3 份副本已由 ADJ-009 收口，不再是遗留项 |

---

*Human View 由 `design-adjustments.yaml`（Canonical）渲染 | 2026-10-17*
