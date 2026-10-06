# Phase Context — 2026-10-05-upstream-baseline-alignment

## Phase 2 (SPEC) 关键决策

- **版本三轴模型（E / K / R）**：把仓库内混为一谈的「版本」按**对象**拆轴 ——
  - **E（外部上游锚）** = 上游项目 `leonai42/stdd` 最新发布 `v3.0.5`（tag / HEAD sha / pushed_at，仅作对标锚）；
  - **K（vendored 内核）** = `upstream/` 内核版本 `3.1.0`（`.fstdd/version.yaml: upstream_version`）；
  - **R（本仓发行版）** = 本仓 FSTDD 发布号 `3.3.4`（`.fstdd/config.d/project.yaml: stdd_version`）。
  核心事实：**K ≠ E**，内核领先上游发布；任何把 K 写成 E 的声明都是错的。
- **单一事实源**：新增 `docs/UPSTREAM_BASELINE.md` 作为快照证据唯一出处（观测时点 + base sha + E 全套 + 通道排除 + 本仓领先量清单 + 经验库对标）；NOTICE/README 只**链接**不复制易变数字。
- **适配层去硬编码**：`tools/install_workbuddy_skills.py` 的 frontmatter `version` ← R（既有 `REPO_VERSION`）、`stdd_version` ← K（本文件内新增最小读取函数 `_vendored_kernel_version()`，读 `.fstdd/version.yaml: upstream_version`，读不到回落 `unknown`）；来源横幅与 docstring 去硬编码。刻意**不外提**到 `_skill_install_env.py`（YAGNI，proposal 限定唯一代码面改动）。
- **`stdd_version` 形态约束**：必须为纯 `[\d.]+` ⇒ K 取裸 `3.1.0`（不追 `-fin.N` 后缀），兼容既有测试与 `frontmatter_version()` 读取口径。
- **经验库对标 = 只读**：`leonai42/stdd-experiences` 非我方回传目标（我方目标 = `2749817087qq/Fstdd-experiences`）；只读核对「清单中我方 node 前缀条目数」，不修改 / 不外发 / 不接入回传链路。
- **改动边界**：只动 5 个活体声明面 + 新增 1 文档；`upstream/` 上游自有文档、`.fstdd/archive/**`、`skills-archive/**`、`_scratch/**`、`artifacts/**` 零改动（保 MIT 署名忠于事实 + 保 `verify_rename` 8/8）。
- **anchoring（Step 4.5）不触发**：proposal `is_critical=false` 且三项 risk 均 false ⇒ 维持 L1。

## 用户关注点（Gate 2 确认要点）

- 门禁项须**明确确认**后才 approve —— 本次以用户原文「确认无误，执行吧」为 evidence，非静默自跑。
- 16 个 Scenario 全部高置信度；术语演进 1 项（proposal「双轴」→ design/specs「三轴 E/K/R」）已由 design 决策 1 显式承接（proposal 为 Gate 1 锁定件，不擅改）。
- 既有门禁判定语义**零改动**：`verify_rename.ALLOWED_OLD_MENTIONS`（含 `"STDD V3.0.5"`）原样保留；`verify_skill_standards` 只认 `version` 字段，不受 `stdd_version` 改动影响。
- 已知非阻断项：`fstdd validate` 报 2 条 AND 警告 —— 系 validate.py **文件级**计数（`len(re.findall(r"\*\*AND\*\*", content))`，validate.py:68），非按 Scenario 计数；本 change 逐 Scenario AND 上限为 3（≤5，合规），exit code 0。

## 产出物清单

- `canonical/proposals/2026-10-05-upstream-baseline-alignment.yaml`
- `design.md`（Context 三轴表 + 10 行漂移点定位 + 5 决策 + Architecture 流向图 + 7 行风险表）
- `canonical/specs/code/version-nomenclature.yaml`（3 REQ / 10 SC）
- `canonical/specs/code/upstream-baseline-alignment.yaml`（3 REQ / 6 SC）
- `canonical/specs/agent/2026-10-05-upstream-baseline-alignment.yaml`（task_type=documentation）
- `specs/version-nomenclature/spec.md`、`specs/upstream-baseline-alignment/spec.md`（Gate 2 自动生成）
- `test-plan.md`（18 TC：TC-VNOM-001..010 / TC-UBL-001..006 / TC-REG-001..002；P0×14 / P1×4）
- `canonical/.canon-index.yaml`（specs.code 双 capability）

## Phase 3 预告（BUILD）

- **改动域**：
  - 文档：`NOTICE.md`、`README.md`、`docs/WORKBUDDY_INSTALL_NOTES.md`、`skills/fstdd-fin/SKILL.md`
  - 新增：`docs/UPSTREAM_BASELINE.md`
  - 代码（唯一）：`tools/install_workbuddy_skills.py`（去硬编码）
- **待回填证据（BUILD 期）**：
  - TC-UBL-005：上游经验库「我方 node 前缀条目数」实测值（经 `ssh fstdd-hub` 只读）
  - TC-VNOM-005 / TC-UBL-006：定向扫描命令原文与输出（记入 `test-report.md`）
- **需注意的回归面**：`test_fstdd_matrix` / `test_cross_cutting_verification` / `test_install_source` / `test_canonical_in_workspace` 直接加载/读取安装脚本，须确认不受去硬编码改动波及（风险🟡中）。
- **闸门**：四自检全绿（rename 8/8、eol 7/7、skill_standards 7/7、workbuddy_skills PASS）+ `pytest upstream/tests` 0 failed。
- **交接**：Gate 3 等待用户确认；B 层生产端 ssh 运维动作按既有分工移交。

## Phase 3 执行记录（BUILD）

> 模式：standard；Part A 切片规划 3 切片（并行组 1：Slice 1+2；组 2：Slice 3）。
> 依赖图：`zero_dependency=[version-nomenclature, upstream-baseline-alignment]`，无环。

- **Slice 1 — 活体声明面版本轴显式化**（组1，🟡M）：`NOTICE.md` / `README.md` / `skills/fstdd-fin/SKILL.md` / `docs/WORKBUDDY_INSTALL_NOTES.md`
  - 新增 `tests/test_version_nomenclature.py`（TC-VNOM-001..005，12 passed）。
  - RED 证据：改前 11 failed / 1 passed（预期 RED）；GREEN：12 passed。
  - 偏离：INSTALL_NOTES :225 历史叙述含 `3.0.5` → 改写为「看到旧版本号就以为装好了」以消除歧义版本词（SC-004）。
  - verified_at `2026-10-05T11:53:05+08:00`，tc_coverage 5/5，new_tests 12。
- **Slice 2 — 适配层版本字段派生去硬编码**（组1，🟡S）：`tools/install_workbuddy_skills.py`
  - 新增 `tests/test_install_version_derivation.py`（TC-VNOM-006/007/008，3 passed）。
  - 新增 `_vendored_kernel_version()`（读 `.fstdd/version.yaml: upstream_version`）；`version`←R、`stdd_version`←K（裸 `3.1.0`）。
  - verified_at `2026-10-05T11:57:00+08:00`，tc_coverage 3/3，new_tests 3。
- **Slice 3 — 上游基线快照单一事实源**（组2，🟢M）：新增 `docs/UPSTREAM_BASELINE.md` + `tests/test_upstream_baseline.py`
  - TC-UBL-001..006（6 passed）。RED 证据：产物缺位时 6 errors；GREEN：6 passed。
  - **TC-UBL-005 实测值 = 0**（口径：文件名前缀 `FSTDD003-`/`FSTDD-003-` 命中 0；`HEAD` 归档全文扫描命中 0），观测时点 `2026-10-05T12:02:00+08:00`，经 `ssh fstdd-hub` 只读。
  - verified_at `2026-10-05T12:10:00+08:00`，tc_coverage 6/6，new_tests 6。
- **设计偏离（小，已记 `pending-adjustments.yaml`）**：
  - ADJ-001：`tools/verify_eol.py: ALLOWED_DIFF_EXACT` 增补 `NOTICE.md`（门禁相容性，TC-EOL-005 否则假失败）。
  - ADJ-002：4 个新产物 `git add` 暂存（否则上游 `test_a6_no_stray_untracked_files` 判 untracked 而 FAIL）。
- **命中经验**：EXP-2026-0013（声明形态须被实现口径覆盖 → K 取裸 `3.1.0`）；EXP-2026-0016（TC-ID 显式注释于测试函数）。本次未新增经验条目（均为既有模式复用）。

## Phase 3 执行记录（Part C 质量验证 C1–C7）

- **C1 多路并行评审**：3 代理（code / test_config / docs_skills）均返回；提出的 2 处疑点（`test_version_nomenclature` 段解析脆弱性、`test_install_version_derivation` 隔离性）经自核为假阳性（段解析用固定 `---` 边界、fixture 用 `tmp_path_factory` + `FSTDD_OUT` 隔离）。
- **C2 全量质量检查**：
  - 四自检全绿：rename **8/8**、eol **7/7**、skill_standards **7/7**、workbuddy_skills **PASS**（1 项影子副本 WARN，非阻断）。
  - 定向：3 个新测试文件 **21 passed**；全量 `pytest upstream/tests` = **906 passed / 54 skipped / 0 failed**（与基线逐字一致）。
  - coverage/lint/type：`pytest-cov`/`ruff`/`mypy` 本机 env **未安装** → 三项记 **SKIPPED**（未执行，非通过）。`quality.yaml` 的 `lint: ruff check app/ tests/` 中 `app/` 不存在 → 适配说明。
  - `tests/` 目录 **2 项预存失败**（`test_finance_content` 期望 3.3.0、`test_install_smoke` 期望 tag fstdd-v3.1.1），经 `git diff HEAD --name-only` 证明两文件及其输入均未被本 change 触碰 → **判为预存、非本变更引入，超范围不修**。
- **C3 Diff 审查**：逐文件核 6 改 / 4 新，无调试残留、无死代码、无注释旧逻辑；与 spec 一致（去硬编码 + 三轴显式化 + 快照单一事实源）。修正 1 处：`docs/UPSTREAM_BASELINE.md:37` 独立 `stdd` 标识（PyPI 行）→ 改写为路径式 `pypi.org/pypi/stdd`，使 `verify_rename` 回 **8/8**。
- **C4 失败模式检查**：23 类逐项，见 `test-report.md` §六。其中 #15–22（金融红线 8 类）**SKIPPED**（`FINANCIAL_PROJECT=NO`）；#7 附「`verify_notices.py` 破坏性隔离副作用」发现。
- **C5 经验库自动记录/更新**：**未新增条目**；两处**既有条目复现**并回填本节点证据——
  - `EXP-2026-0016`（TC-ID 纯文本扫描假阳性）：occurrences 1→2、last_seen→2026-10-05、附 grep 反证；
  - `EXP-2026-0015`（`verify_notices.py` 隔离=移动的破坏性副作用）：occurrences 1→2、last_seen→2026-10-05、detection_trigger 泛化到「任意无清单目录」、附本节点证据（对仓库根运行移走 3 个含未提交改动的跟踪文件，已还原）。
- **C6 设计调整汇总**：`design-adjustments.md` 已生成（ADJ-001 / ADJ-002 / ADJ-003，count = 3，均门禁相容性小偏离）。
- **C7 测试报告**：`test-report.md` 已生成（含 TC 覆盖对账 vs 实况、切片状态、23 类失败模式、6 项已知问题与补完计划）。
- **两处 CI 告警判为假阳性/假阴性**（均附源码根因 + grep 反证，未回避、未伪造）：
  - `(d) 重复 TC-ID`：`ci.py:311-324` 仅扫 `test-plan.md` 单文件字面计数；定义行每 ID 恰 1 次（18 行），其余为矩阵/优先级/证据表引用。
  - `TC 实现覆盖 14/21 (67%)`：`ci.py:536-573` 仅扫 `tests/*.py`；缺失 7 个 ID 实现于 `tools/verify_*.py` / CLI 闸门 / `upstream/tests` 或属 spec 级引用，真实新增 TC 覆盖 **14/14**。
- **收尾复跑核验**：全量 `pytest upstream/tests` 复跑 = **906 passed / 54 skipped / 0 failed**（451s）。期间一次复跑出现 `test_a6_no_stray_untracked_files` FAIL（`?? .tmp_norm_eol.py`），经核验为**外部并发进程瞬时产物**（全仓 grep `norm_eol` 零命中、文件运行前后均不存在），非本变更引入；单文件复跑 `16 passed / 3 skipped`，详见 `test-report.md` §5.2。
- **发布门禁 EOL 归一**：收尾时 `git ls-files --eol` 发现 4 个 FSTDD CLI 生成的 change 产物（`caveman_summary.txt`、`proposal.md`、`specs/upstream-baseline-alignment/spec.md`、`specs/version-nomenclature/spec.md`）呈**索引 LF + 工作区 CRLF** 混合态（CLI 生成为 CRLF，`git add` 后索引归一为 LF）→ 执行 `verify_eol.py --fix` 归一 4 个 → `verify_eol` **7/7**，`verify_rename` 复合项 TC-RENAME-006 随之回 **8/8**。属工具既有归一能力，**非设计偏离**（`design_adjustments.count` 维持 3）。
- **闸门状态**：**停在 Gate 3**，等待用户明确确认（不自动 approve、不静默自跑、不伪造 evidence）。