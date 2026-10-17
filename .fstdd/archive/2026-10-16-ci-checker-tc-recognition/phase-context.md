# Phase Context — 2026-10-16-ci-checker-tc-recognition

## Phase 1 关键决策（UNDERSTAND）

- 两类缺陷：① 测试文件 glob 失明（ci.py:558 / diff.py:99 / trace.py:95 三处 `rglob("test_*.py")`，对连字符 `test-*.py` 结构性失明，EXP-2026-0001 类假红）；② TC-ID 查重口径分裂（ci.py:317 全文计数 vs validate.py:82-88 定义行计数，EXP-2026-0017）。
- Gate 1 范围裁定：C3（diff/trace 同根因点位）用户未异议，按建议纳入；mode=standard（覆盖敏感性）。
- 经验库命中：EXP-20260917-A1（本仓 2026-09-17 录入，severity=high）——早已确诊 (d) 粒度错误并给出同样修法，30 天未落地；本 change 正式落地并把「10 归档 change 0 误报」写成真实数据验收（SC-CTR-007）。

## Phase 2 关键决策（SPEC）

- 5 个技术决策：共享 helper（vs 三处内联）/ 命名收敛两种 / (d) 对齐 validate 定义行（正则逐字复制）/ TC-CI-008 换语义留痕 / 两层测试落点。
- 规格：3 REQ / 9 SC；测试方案：9 TC（P0×6 + P1×3），1:1 覆盖。
- Step 5.5 自审发现并修复 1 项：test-plan 正文嵌入字面 `| **ID** | TC-… |` 示例被定义行口径计为真实 ID 行（validate 报重复）→ 改写表述 + 把「定义行字面禁忌」写进测试原则。
- 已知局限（用户 Gate 2 确认接受）：本仓测试实际在 `upstream/tests/`，覆盖检查只看根 `tests/`——自身 planned TC 的覆盖检查不随 glob 修复转绿；真实数据验收放下游仓（其 tests/ 在根且全连字符命名）。

## Phase 3 切片记录（BUILD，full_auto 长程，授权 2026-10-16T23:17）

### Slice 1：helper + ci 覆盖检查 ✅ done @2026-10-16T23:32
- 实现：`utils.iter_test_files()`（`_TEST_FILE_PATTERNS = ("test_*.py", "test-*.py")`，seen 去重，Iterator[Path]）；ci.py:558 切换（函数内 import）。
- 测试：TC-CTR-001（test_ci.py 新增类 TestTcImplementationCoverageRecognition）、TC-CTR-002（同类）、TC-CTR-003（test_utils.py 新增）。
- RED：TC-CTR-001 行为性失败（检查器返回 FAIL 0/N）；TC-CTR-003 ImportError；TC-CTR-002 守卫用例修复前即过（防放宽）。
- GREEN：34/34（Slice 1 后 test_ci.py 25 + test_utils.py 9 = 34；后续 Slice 2 追加 5 个测试后 test_ci.py 达 30）。含 test_utils.py 的 ci+validate+utils 三文件合计 45 passed（9+28+8）。
- 质量：ruff 与 HEAD 逐项一致（8 项全预存在、零新增；**后修正为 9 项**——F541 跨 ci.py/validate.py 两文件共 3 项，见 Slice 2 / ADJ-004）；全量基线另见 Part C（HEAD worktree 比对）。
- tc_coverage 3/3，new_tests 3。
- 插曲：首轮全量回归（sY5LvN）因 pytest 运行中途编辑测试/源文件被污染（14 failed 不可信）→ 弃用，改在 HEAD worktree 跑干净基线（IYhaHC 后台）。

### Slice 2：(d) 定义行口径 + TC-CI-008 换语义 + 真实数据验收 ✅ done @2026-10-16T23:5x
- 实现：`utils.py` 新增常量 `TC_ID_DEFINITION_ROW_PATTERN`（`\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})`）；ci.py `check_tcid_unique` 切换为该常量；validate.py 查重保留同表达式内联字面量（设计偏离：原计划同切常量，但源码级守卫测试 test_c3_validate_source_uses_scoped_regex 要求 validate.py 内含定义行正则 ⇒ 回退内联 + 双向同步注释，最终回归 design D3 原案，详见 design-adjustments）。
- **设计偏离（已记 design-adjustments）**：落地中途曾把 validate.py 也从内联正则切到共享常量（design D3「逐字复制」的增强），C2 全量比对时被源码守卫测试 test_c3_validate_source_uses_scoped_regex 捕获（该测试要求 validate.py 源码含定义行正则字面量）⇒ 回退 validate.py 为同表达式内联 + 双向同步注释；最终实现 = design D3 原案 + ci.py 侧常量引用。
- 测试：TC-CTR-005/006（test_ci.py 新类 `TestTcidUniqueDefinitionRow`）、TC-CTR-008（同类，TC-CI-008 迁移审计）；TC-CI-008 fixture 由「裸重复字面」迁移为「两 `| **ID** | TC-CASUAL-001 |` 定义行」+ 审计注释。
- RED：TC-CTR-005 `AssertionError: 多处引用被误判为重复: (d) 重复 TC-ID: ['TC-UNI-001']`（全文口径实锤）；生产代码切换后 TC-CI-008 旧 fixture 预期转红（C5 计划内更新，同 slice 修复）。
- GREEN：36 passed（test_ci.py 28 + test_validate.py 8）；含 test_utils.py 45 passed。
- **自指缺陷自查并修复**：TC-CTR-008 首版源码扫描断言被自身文本污染（docstring 内含目标字面使 count=3≠2；断言 3 的期望字面自我命中）→ 改为 `inspect.getsource` 限定 TC-CI-008 函数体 + 期望字面运行时拼接（自指免疫）。
- **变异验证（EXP-2026-0013 规程）**：ci.py 临时还原全文口径 → TC-CTR-005 转红（突变体被杀）、TC-CTR-006/008 保持绿（守卫与静态检查不受影响）；备份 sha256 `a07d9434…dab9` 逐字节还原复核通过，还原后 3/3 绿。
- **真实数据验收**：
  - SC-CTR-007：EXP-20260917-A1 表内 10 个归档 change 全量跑现行 CLI，`(d)` **10/10 PASS**（修复前 10/10 误报）；contract-auto-share 计数 24 vs EXP 记录 25 = 定义行口径与全文口径的预期差。
  - SC-CTR-009（下游 `多层次agent` 归档 change `2026-10-16-default-free-fixture`，HEAD CLI vs 修复 CLI 同 cwd 对比）：`(d)` ✓ 保持 PASS，计数 10→6（10=全文提及含散文引用 EPR/PSP/PMD，6=真实定义行 DFJ）；TC 实现覆盖 **0/10 (0%) → 9/10 (90%)**，缺失 TC-EPR-002（该 ID 仅在散文出现、从未建定义行、tests/ 无实现——真实缺口，非检查缺陷）；`tests/test-platform-model-discovery.py`（连字符命名，修复前结构性不可见，含 7 处 DFJ 引用）现已纳入扫描。
  - 规格 SC-CTR-009 原文「(d) FAIL→PASS」经实测修正为「(d) 保持 PASS 且计数回归真实定义行」——该 change 全文无重复字面故修复前即 PASS； FAIL→PASS 发生在覆盖检查（0/10→9/10）。
- 质量：ruff 与 HEAD worktree **逐项一致**（ utils/ci/validate/test_ci/test_utils 五文件 9 项全预存在、零新增——此前"8 项"为误计，本次以 HEAD worktree 精确比对为准）；干净 HEAD 全量基线已出：**14 failed / 859 passed / 8 skipped**（15m52s），失败均为环境性预存在，C2 比对以此为准。
- tc_coverage 3/3（TC-CTR-005/006/008），new_tests 3（+1 既有测试换语义迁移）。
- 新发现 followup（不属本 change 范围）：覆盖检查的 planned-TC 提取仍是全文口径（planned=10 vs 定义行 6）；(g) AND 计数粒度（EXP-20260917-A1 同记）。

### Slice 3：diff/trace 同根因点位 ✅ done @2026-10-17T00:3x
- 实现：`diff.py` `cmd_diff`、`trace.py` `cmd_trace` 切换至 `iter_test_files`（函数内 import + REQ-CTR-001 注释）；全仓 `rglob("test_*.py")` 直扫点清零（仅剩注释引用）。
- 测试：新增 `tests/commands/test_diff_trace_hyphen.py`（TC-CTR-004a trace / 004b diff，subprocess 级 CLI）。
- RED：2/2 失败且特征精确——trace 无「测试: tests/test-hyphen.py」行（test-plan 能定位、tests/ 无产出）；diff 源码列有 tests\test-hyphen.py（引用搜索走 *.py）但「测试函数」列空。
- GREEN：2/2；回归 tests/commands/ 全量 + test_utils.py = **453 passed**。
- 真实数据确认（下游 多层次agent，HEAD CLI vs 修复 CLI）：`fstdd trace TC-DFJ-001` 修复前无任何「测试:」输出，修复后 `测试: tests\test-platform-model-discovery.py`。
- 质量：diff.py/trace.py ruff 与 HEAD worktree 逐项一致（8 项同规则同位置，零新增）。
- tc_coverage 2/2（TC-CTR-004a/004b），new_tests 2。
- 该切片完成后本 change 三处 glob 失明点位（ci/diff/trace）全部切换单一事实源 `iter_test_files`。

## Part C 质量验证记录（BUILD 末段，full_auto）

### C1 三路评审（子代理并行，2026-10-17）
- 模型分配（分散 key 池）：code=hy4-preview（平台）、test=custom-local:deepseek-v4-flash、doc=custom-local:glm-5.2；报告落 `reviews/c1-{code,test,docs}-2026-10-17.md`。
- 结论：code **PASS**（0 🔴/0 🟠，4 🟡 全非阻塞）；test **CONDITIONAL**（0 🔴，2 🟠：SC-CTR-007 无自动化而数据可自动化、subprocess 编码未对齐既有模式）；docs **CONDITIONAL**（0 🔴，3 🟠：design_adjustments.count 与产物矛盾、design-adjustments schema 偏离模板、tasks 4.4 基线表述与实测矛盾）。
- test-reviewer 独立变异验证：`_TEST_FILE_PATTERNS` 回退 → TC-CTR-001/003/004a/004b 被杀（TC-CTR-002 守卫存活），sha256 `a903c971…` 还原复核一致（无带病离场）。
- code-reviewer 复核：正则两处 `ast.literal_eval` 逐字节相等；全仓生产代码 `rglob("test_*.py")` 0 残留；ruff 0 新增。

### C2 质量检查（全量回归，三次运行）
- 干净 HEAD 基线（detached worktree `D:/tools/_stdd_head_baseline`）：**14 failed / 859 passed / 8 skipped**（两次复跑一致；其中 test_repo_home 的 a2/a3/b4/d1 四项为「worktree 路径敏感」，在基线 worktree 失败、主 worktree 通过）。
- 修复前全量（b2Ne34）：12 failed / 870 passed / 7 skipped → 对 12 项逐一在 HEAD worktree 复跑：**10 项预存在；1 项真实回归（test_c3，validate.py 常量切换破坏源码守卫测试，已修复 ADJ-001）；1 项瞬态（test_a6，未跟踪新测试文件，ADJ-005）**。
- 修复后全量（Okypgp，C1 补强前中间态）：11 failed / 871 passed / 7 skipped。
- **终态全量（含 ADJ-006/007/008/009 补入的 7 个用例，串行重跑 882.80s）：11 failed / 878 passed / 7 skipped**——失败集合与归因不变（10 项与基线同名预存在 + 1 项瞬态 test_a6）。增量算术自洽：采集 +15 恰等于新增 15 个测试；859+15+3+1=878；14-3=11；8-1=7。
- 静态检查（权威口径 = 与 HEAD worktree 逐条比对）：ruff `upstream/fstdd/cli/` 全目录 128=128、本 change 7 个有 HEAD 对照的文件 17=17、新增 test_diff_trace_hyphen.py 0 项，**全部零新增**；mypy 全包 80=80（零新增）。注：Slice 1 记「8 项」/ Slice 2 记「9 项」/ 本节初记「19 项」均为不同选取范围下的计数（「9」为 `[*] N fixable` 子集，非总数），以本节逐条比对为准（ADJ-004；2026-10-17 两 worktree 复测确认 7 文件 17=17、5 生产文件 16=16）。
- 本 change 测试规模：test_ci 23→30（+7）、test_utils 8→14（+6）、test_diff_trace_hyphen 0→2（+2）= **新增 15 个测试**（含 D-01 修复新增的全仓副本集合守卫）。

### C1→C2 驱动补强（ADJ-006/007/008）
- SC-CTR-007 由手工取证升级为自动化（10 归档 change 语料逐个断言 (d) PASS）→ 自动化覆盖 7/9 → **9/9 SC**（SC-CTR-009 跨仓依赖保留取证并显式标注）。
- helper 增加 is_file() 过滤（目录条目不再产出，消 ci/trace 裸 read_text 崩溃面）；diff.py 日志变量泄漏修正。
- 新增常量↔validate 内联字面量等价守卫（钉死 ADJ-001 回退后的 2 副本同步通道）。
- subprocess 测试对齐既有 run_cli 编码模式；TC-CTR-003/006 断言补强；非模板写法 → WARN 语义钉死。

### C3 diff 审查（两份并列，2026-10-17）
- `reviews/c3-diff-2026-10-17.md`（team-lead 独立复核）+ `reviews/c3-diff-code-2026-10-17.md`（code-reviewer 独立审查）。**结论均为 PASS**（0🔴/0🟠）。
- 六项要点全部通过：调试残留 0（新增行命中 0，旧实现为删除而非注释）；三处调用点全切换、裸 `rglob("test_*.py")` 活调用归零（24 处 rglob 逐条分类，唯一测试扫描点为 `utils.py:78` 单一事实源本身）；`validate.py:83` ↔ `utils.py:63` 正则逐字节等价（`ast.literal_eval` 复核，repr 同、长 35/35）；新文件 subprocess 防护齐备（encoding/errors/PYTHONIOENCODING/timeout/cwd）；无夹带（16 项预存在删除已识别排除 + 证明零引用耦合）。
- ruff 新增行与 ruff 行号**求交 = 0**（所有命中落在未改动行）；独立报告实测 `pytest tests/commands/ tests/test_utils.py -q` = **459 passed**。
- **独立报告 2 项 🟡**：
  - **D-01** `commands/diff.py:45` 存在**第 3 份**定义行正则内联副本，等价守卫只覆盖 `utils↔validate` ⇒ 常量变更时 `diff` 口径静默漂移（EXP-20260917-A1 复发通道）。**已取证为预存在**（`git show HEAD:...diff.py:45` 已有；本 change 仅改 import 与 helper 切换）⇒ 不在 Gate 2 范围，记 follow-up 候选，交 Gate 3 裁定。
  - **D-02** DELIVER 清单须显式登记 4 项 `.fstdd/experiences/` 改动 + 1 个新增测试文件（与已排除的 16 项删除分开陈述）⇒ 采纳。
- 🟢 D-03（注释仍含 `rglob("test_*.py")` 字面量，字面 grep 判据不成立但调用语义归零）/ D-04（`seen`+`resolve()` 去重当前不可达，防御性代码）/ D-05（归档语料即测试数据集）——接受不改。
- **事故**：`reviews/c3-diff-2026-10-17.md` 于 08:25 被 code-reviewer 的 Write（**未先 Read 既有文件**）覆盖，team-lead 已据原内容重建；code-reviewer 独立报告改存 `c3-diff-code-2026-10-17.md` 避免同路径冲突。教训：**派发子代理写报告前必须指定唯一文件名，或要求先 Read 再 Write**。

### C4 失败模式全量（test-reviewer 独立，2026-10-17）
- 14 类通用：**13 ✅ + 1 SKIPPED（context-overflow，非 LLM 任务）+ 0 ❌**；8 类金融全 SKIPPED（FINANCIAL_PROJECT=NO，依据 `test-plan.md:189` + `.fstdd/config.d/project.yaml` 无 financial 标记）。
- 关键取证：`iter_test_files` 的 `is_file()` 过滤实测跳过名为 `test_dir.py` 的目录（防 `IsADirectoryError`）；不存在目录 → 空产出；子目录嵌套递归产出；依赖单向无循环导入。
- 报告：`reviews/c4-failure-modes-2026-10-17.md`。

### C7 测试报告（2026-10-17）
- `test-report.md`（12 节）产出。含：SC↔TC↔测试函数覆盖矩阵 9/9、受影响套件 53 passed、全量回归归因（11 项失败 = 10 项预存在同名 + 1 项瞬态）、真实数据验收（SC-CTR-007 10/10、SC-CTR-009 含**规格修正显式承接**）、变异验证、C1/C3/C4 结论、8 条设计偏离、8 项已知局限、Gate 3 四项确认事项。

## ⚠️ DELIVER 注意事项（预写，归档时必读）

- 本 change 修改的是 upstream/  vendored CLI 源码（utils.py / ci.py / diff.py / trace.py）与 upstream/tests/；归档后 canonical 合并按常规（capability: ci-checker-tc-recognition，本仓 .fstdd/canonical/ 当前为空索引，需新建 specs/code + specs/agent 条目与 .canon-index.yaml 登记）。
- 同步考虑：下游项目（多层次agent）长期受 (d) 假红与 glob 失明之苦，交付后可在其回归中复证 SC-CTR-009。
