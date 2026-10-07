# 测试报告 — 2026-10-07-tool-defect-fixes

> change：`2026-10-07-tool-defect-fixes`（工具链契约保真：6 个既有缺陷修复）
> 阶段：Phase 3 BUILD（Gate 3 验收）
> 生成时间：2026-10-07
> 测试环境：Windows（本机）/ Python 3.13.12（workbuddy default env）/ PyYAML 6.0.3 / pytest 9.1.1
> 权威测试环境：**控制台 UTF-8 + `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`**
> 观测基线：`observed_base_git_sha = 0710d5462f973164f83f5096cdf739380e579fb8`
> 执行模式：`long_range.mode = full_auto`（长程全自动）

---

## 一、TC 覆盖率（planned vs actual）

| capability | 计划 TC | 实现（测试函数） | 覆盖 |
|---|---|---|---|
| dry-run-fidelity | TC-DRY-001..004（4） | 6 | **4/4** |
| experience-io-contract | TC-EIO-001..005（5） | 7 | **5/5** |
| proposal-extraction-fidelity | TC-PXF-001..003（3） | 7 | **3/3** |
| ci-check-accuracy | TC-CCA-001..002（2） | 7 | **2/2** |
| quarantine-opt-in-safety | TC-QIS-001..003（3） | 6 | **3/3** |
| **合计** | **17** | **33** | **17/17 = 100%** |

- 新增测试文件 5 个，新增测试函数 **33** 个（`.fstdd.yaml` → `traceability.test_functions: 33`）。
- `fstdd ci check-failures` 的 **TC 实现覆盖 = 18/18（100%）**（其口径为「TC-ID 在 `tests/` 中出现」，
  18 = 17 个 TC-ID + 1 个脚本内锚定的附加 ID）。
- 每个切片都执行了 **RED → GREEN**，RED 证据为**真实回退对照**（见 §三）。

### 权威全量结果

**第一次全量回归**（暴露 4 处失败 → 逐条处置，见 §九-1..4）：

| 套件 | 结果 |
|---|---|
| `pytest upstream/tests` | **951 passed / 5 skipped / 4 failed**（899s） |
| `pytest tests`（仓库根） | **127 passed / 3 skipped / 1 failed** |

4 处失败处置后**逐条隔离复跑**：

| 失败用例 | 处置 | 复跑 |
|---|---|---|
| `upstream/tests/test_except_audit.py::test_aud_002_table_matches_live_scan` | 生成本 change 审计活表（行号位移刷新） | ✅ |
| `upstream/tests/test_guard_silent_except.py::test_grd_001_check_passes_on_current_repo` | 同上 | ✅ 两文件合跑 **11 passed** |
| `upstream/tests/test_evidence_ops.py::test_epr_004_005_freshness_three_states` | `baseline.py` 新增相对导入 ⇒ 测试改**包导入** | ✅ |
| `tests/test_upstream_baseline.py::test_ubl_003_leading_gap_list_consistent_with_machine_sources` | `docs/UPSTREAM_BASELINE.md` R 轴 `3.3.5`→`3.3.6`（上一版遗留失真） | ✅ 两文件合跑 **11 passed** |
| `upstream/tests/test_repo_home.py::test_a6_no_stray_untracked_files` | **不修** —— 在办 change 期结构性必红（新文件未跟踪）；DELIVER 提交后转绿 | ⏳ 预期 |

**最终全量结果**（处置后复跑，权威，2026-10-07）：

| 套件 | 结果 |
|---|---|
| `pytest upstream/tests` | **954 passed / 5 skipped / 1 failed**（836s）—— 唯一失败为 `test_a6_no_stray_untracked_files`（**结构性**，见下） |
| `pytest tests`（仓库根） | **128 passed / 3 skipped / 0 failed**（122s） ✅ |

> `test_a6_no_stray_untracked_files` 的判据是「除 `.fstdd/changes/` 外无未跟踪项」，
> 而在办 change 的新文件（5 个测试 + 2 个新模块 + 3 条经验）**在提交前必然未跟踪**
> ⇒ **在办 change 期结构性必红**，DELIVER 提交后自动转绿（上一版 v3.3.6 同此流程）。
> 已独立核验：`git status --short` 的 `??` 项 = 1 个 change 目录 + 10 个本 change 新增文件，**无遗留垃圾**。

其余回归面：

| 套件 | 结果 |
|---|---|
| `tools/test_verify_notices.py` | 20 passed / 1 skipped |
| `upstream/tests/commands/test_ci.py` + `test_canon.py` + `test_canon_coverage.py` | 36 passed |
| `upstream/tests/commands/test_batch.py` + `test_batch_pipeline.py` | 21 passed |
| 新增 5 个测试文件 | 33 passed |

---

## 二、逐切片验证状态（Step B3.4 三项检查）

| # | capability | TC 覆盖 | 产出物核对 | 测试运行 | 结论 |
|---|---|---|---|---|---|
| 2 | experience-io-contract | 5/5 | `_save_index` 2 处 `newline=""`；`_json_default` 覆盖 5 个 `json.dumps` | RED 5 failed/2 passed → GREEN 7 passed | ✅ |
| 4 | ci-check-accuracy | 2/2 | `_tcid_definition_points`（形态 A 优先 / B 回退） | RED 2 failed/3 passed → GREEN 7 passed | ✅ |
| 1 | dry-run-fidelity | 4/4 | `_dryrun.py` + 15 模块接入 + `canon verify` 守卫 | RED 3 failed/2 passed → GREEN 6 passed | ✅ |
| 5 | quarantine-opt-in-safety | 3/3 | 默认只报告 + `--quarantine` + `would_quarantine` | RED 6 failed → GREEN 6 passed | ✅ |
| 3 | proposal-extraction-fidelity | 3/3 | `_proposal_anchors.py` + 渲染器两 h2 + 解析器同源 | RED 5 failed/1 passed → GREEN 7 passed | ✅ |

---

## 三、RED 证据（真实回退对照，非推测）

| 切片 | 取证方式 | RED | GREEN |
|---|---|---|---|
| 5 | 备份新文件 → `git checkout` 还原 `tools/verify_notices.py` → 跑新测试 → 还原 | 6 failed | 6 passed |
| 3 | 备份 → 还原 `canon.py` + `extract_proposal.py`（保留锚点模块）→ 跑新测试 → 还原 | 5 failed / 1 passed | 6 passed（后增至 7） |
| 1 | 前序会话已用真实 stash 对照取证 | 3 failed / 2 passed | 5 passed（后增至 6） |
| 2 | 前序会话 | 5 failed / 2 passed | 7 passed |
| 4 | 前序会话 | 2 failed / 3 passed | 5 passed（后增至 7） |

> 🔴 **RED 取证的副作用事故（已复原，留档）**：为切片 5 取 RED 证据时，回退后的
> `verify_notices.py` 在「对仓库根默认运行」用例中把 `README.md` / `CHANGELOG.md` /
> 一份 notices md **移入 `tools/_quarantine/`**（EXP-2026-0015 第三次命中）——
> 工作树出现 3 个 `D`，全量测试收集阶段即失败。
> 处置：3 个文件与 `HEAD` **逐字节比对一致**后 `git checkout` 复原，隔离区记录清除；
> 并在测试内固化为 `_restore_repo_root_from_quarantine()`（`finally` 自愈）。

---

## 四、C1 多路并行技术评审（3 代理）

按 `.fstdd/config.d/quality.yaml` → `review.agents`（code / test_config / docs_skills）三路并行。

### 报出并**已修复**的缺陷（3 条）

| # | 严重度 | 发现 | 修复 |
|---|---|---|---|
| 1 | 🔴 critical | `canon verify --dry-run` 仍经 `_generate_one` 写 `proposal.md` + `caveman_summary.txt` | `cmd_canon_verify` 的自动重生成分支加 `dry_run_requested` 守卫；新增行为断言 TC-DRY-003c |
| 2 | 🟡 high | `ci` (d) 的形态 B（ID 作首列）把「TC↔测试函数映射表」误计为定义点 ⇒ `2026-09-25-guard-phase-path-scope` 假红 | 形态 B **仅在形态 A 抽不到时**启用（不做并集）；新增回归自检 TC-CCA-002d2 |
| 3 | 🟡 medium | `batch child status`（纯读）被 dry-run 误伤屏蔽 | 读路径白名单补 `child` + 默认子动作 `status` |

### 报出并**已加固**的测试问题（6 条）

| # | 发现 | 处置 |
|---|---|---|
| 4 | `_handles_dry_run` 用子串匹配 ⇒ 「仅注释提及」会假绿 | 改 **AST 口径** + 4 个反向样本（注释 / docstring / 字符串字面量 / 无提及） |
| 5 | AST 口径漏认 `getattr(args, "dry_run", False)`（字符串常量）⇒ 假红 `structure.py` | 单独认 `getattr/hasattr/setattr` 的字符串实参位置 |
| 6 | `test_ci_tcid_definition.py` 自检**另抄**一份正则 | 自检改用生产实现 `ci._tcid_definition_points` |
| 7 | `test_experience_io_contract.py` 004b 同样另抄扫描逻辑 | `_json_dumps_calls_without_default(src=...)` 参数化，自检复用生产实现 |
| 8 | `_restore_repo_root_from_quarantine()` 会无差别搬回运行前既有的隔离证据 | 加 `only_names` 约束，只复原「本次运行期间新增」的条目 |
| 9 | `test_tc_qis_001b` 依赖 `git status`（受无关改动干扰） | 改为断言「仓库根顶层 `*.md` 的 {名称: md5} 不变」（精确、与 git 状态解耦） |

### 报出但**判定不改**的项（留档）

`TC-…-\d{3}` 硬编码 3 位（项目约定即 3 位）；`_proposal_anchors` 的 4 个常量（解析器已使用）；
`_h3_body` 不把 `####` 当边界（模板最深 h3）；`dry_run_guard` 返回 `None`（既有范式）；
测试向真实 `tools/_quarantine/` 写入（与既有 `tools/test_verify_notices.py` 同范式，目录已 gitignore）。

### 已核验**无问题**的点（摘要）

- 15 个模块的 dry-run 早返回**均位于所有写操作之前**；`phase` 的 `return` 与 `_dryrun` 的 `None` 均安全。
- `_proposal_anchors` 的常量与 `.fstdd/templates/proposal.md` **逐字一致**；渲染器/解析器**已无硬编码锚点残留**。
- `_parse_section` 重写与旧实现语义等价（含「目标标题不存在」「末节无后续标题」边界）。
- `_json_default` 覆盖 `experience.py` 全部 5 个 `json.dumps` 调用点；原生可序列化值输出不变。
- 版本三轴一致（`fstdd_version` = `stdd_version` = 3.3.6）；本 change 不升版。

---

## 五、C2 全量质量检查

| 项 | 命令 | 结果 |
|---|---|---|
| 全量测试（上游内核） | `pytest upstream/tests` | 首跑 951/5/**4 failed** → 3 修 1 结构性 → **终跑 954 passed / 5 skipped / 1 failed**（仅 `test_a6`，结构性） |
| 全量测试（仓库根） | `pytest tests` | 首跑 127/3/**1 failed**（`test_ubl_003`，上一版遗留）→ 已修 → **终跑 128 passed / 3 skipped / 0 failed** ✅ |
| 覆盖率 | `pytest --cov` | ⏭ **SKIPPED** —— `.fstdd/config.d/quality.yaml` 的 `quality.coverage.scope = changed_files_only`，且 `ci check-failures` 报「无 `coverage.json`」；本 change 为工具契约修复，**以行为断言替代覆盖率门槛**（`fail_under: 0`） |
| lint | `ruff check app/ tests/` | ⏭ **SKIPPED** —— 该命令按配置指向不存在的 `app/`；本仓无 ruff 配置，且**既有发布门禁不含 lint**（见 `.fstdd/standards/release-and-docs.md`） |
| 类型检查 | `mypy app/` | ⏭ **SKIPPED** —— 同上（配置指向 `app/`，本仓未启用 mypy） |
| `ci check-failures` | `fstdd ci check-failures 2026-10-07-tool-defect-fixes` | ✅ **6 通过 / 1 警告 / 3 跳过 / 0 错误**（详见 §六） |
| 四自检脚本 | `verify_rename` / `verify_eol` / `verify_skill_standards` / `verify_workbuddy_skills` | 见 §七（含「在办 change 期必然红」的说明） |

---

## 六、C3 Diff 审查

- `git diff --check`：**无空白错误**。
- 调试残留扫描（`breakpoint()` / `pdb.set_trace` / 调试 `print`）：**0 命中**。
  （`canon.py` 里的 `TODO:` 命中均属 `CANONICAL_PROPOSAL_TEMPLATE` 的**脚手架占位文本**，非残留。）
- 注释掉的旧逻辑：**0 命中**。
- 删除行审查：全部为「被新行为取代的旧实现」（`verify_notices` 的默认隔离、`canon` 的 h3 直挂、
  `ci` 的全文计数、`experience` 的无 `default=` 调用、2 个断言旧契约的测试用例），**无功能误删**。
- 变更与 spec 一致性：6 个缺陷 ↔ 5 个 capability ↔ 17 个 TC ↔ 33 个测试函数，**逐条可追溯**。
- 逐文件审查清单（已跟踪 18 个 M + 7 个新增未跟踪）：`tools/verify_notices.py`、
  `tools/test_verify_notices.py`、`upstream/fstdd/cli/commands/{baseline,batch,bootcamp,canon,caveman,ci,curate,experience,extract_proposal,gate,hooks,index,knowledge,phase,skill,state,work}.py`、
  新增 `_dryrun.py`、`_proposal_anchors.py`、5 个测试文件。

### `ci check-failures` 明细

| 检查 | 结果 | 说明 |
|---|---|---|
| (a) 必需文件 + Spec 文件存在 | ✅ | — |
| (d) TC-ID 唯一 | ✅ | 17 个，按**定义点** |
| (f) THEN 含 SHALL | ✅ | — |
| (k) 契约一致 | ✅ | 5 capabilities |
| TC 实现覆盖 | ✅ | 18/18（100%） |
| 切片验证证据 | ✅ | 5 个切片均有 tc_coverage/new_tests/verified_at |
| (g) AND 超限 | ⚠ | `experience-io-contract/spec.md`=6、`quarantine-opt-in-safety/spec.md`=6。**口径说明**：该检查按**每文件**统计 `**AND**`，而本项目规格刻意用 AND 细化可验证条件（单 Scenario 最多 3 条）⇒ **接受**，不修改规格 |
| (b) 范围蔓延 | ⏭ SKIP | 「proposal 未声明 capability 列表」—— 该检查靠 proposal.md 的 `- capability: <name>` 行取数，而该行只在**未被渲染**的 Risk Areas 段 ⇒ **长期失效**（ADJ-005 连带） |
| (j) 覆盖率真空 | ⏭ SKIP | 无 `coverage.json` |
| (l) 锚定等级 | ⏭ SKIP | 只认仓库根 `canonical/proposals/`，开发期 canonical 在 change 内 ⇒ BUILD 阶段恒 SKIP（DELIVER 合并后可查） |

---

## 七、四自检脚本

| 脚本 | 在办 change 期结果 | 判读 |
|---|---|---|
| `verify_rename` | 7/8（TC-RENAME-006 FAIL：`verify_eol.py` 未通过） | ⚠️ **结构性**：TC-RENAME-006 依赖 `verify_eol`，而 `verify_eol` 的 **TC-EOL-005 判据是「索引 vs HEAD」**，在办 change 必然存在未提交改动 ⇒ **必然红**。须在 DELIVER 提交后复跑（上一版 v3.3.6 即为此流程，提交后 8/8） |
| `verify_eol` | 见 §七-1 | 同上 |
| `verify_skill_standards` | 见 §七-2 | ⚠️ 首跑 6/7、次跑 7/7 属**已知副作用**（TC-SES-004 会真的执行 `check_skill_metadata --fix` 改写 `~/.workbuddy/skills` 下第三方 skill） |
| `verify_workbuddy_skills` | 见 §七-3 | ⚠️ 会 WARN「生成戳版本与仓库不一致」（本机 skill 戳为 3.3.5、仓库 3.3.6）—— **属上一版遗留**（v3.3.6 DELIVER 时未重跑 `install_workbuddy_skills.py`），非本 change 引入 |

### 七-1 `verify_eol` 实测

```
[PASS] TC-EOL-001  .gitattributes 规则正确（* text=auto eol=lf）
[PASS] TC-EOL-002  批量 add 无 CRLF 告警（883 文件 / 0 行告警）
[PASS] TC-EOL-003  混合态文件清零（0 个）
[PASS] TC-EOL-004  索引无 CRLF 项（0 个）
[FAIL] TC-EOL-005  索引零内容变更 —— 「行尾治理引入了 17 个非预期变更」
[PASS] TC-EOL-006  CLI 脚本 LF 且可运行
[PASS] TC-EOL-007  README 含 EOL 说明
结果：6/7
```

**TC-EOL-005 的 FAIL 是结构性的**（已核验判据源码）：它统计 `git diff --cached --diff-filter=M`
中**不在白名单**的已跟踪文件数；白名单 = `tools/` `docs/` `skills/` `.fstdd/experiences/`
+ `README.md` `.gitignore` `NOTICE.md`。本 change 修改的 **17 个 `upstream/fstdd/cli/commands/*.py`**
恰好不在白名单 ⇒ 在办 change 期必然报 17 个。**提交后该数归 0**（上一版 v3.3.6 实测提交后 7/7）。
⇒ **判读：不是本 change 引入的缺陷，须在 DELIVER 提交后复跑确认。**

### 七-2 `verify_skill_standards` 实测

**7/7 通过**（TC-SES-001..007 全绿，含 TC-SES-004「真实目录 13 个 SKILL.md 零改动」的反副作用闸门）。

### 七-3 `verify_workbuddy_skills` 实测

`PASS`（6 个 skill 全部通过：安全策略在位、路径适配完好），附 7 条 WARN：

- 6 条「生成戳版本与仓库不一致（期望 3.3.6）」—— 本机 skill 戳为 **3.3.5**，
  **属上一版 v3.3.6 DELIVER 的遗留**（当时未重跑 `tools/install_workbuddy_skills.py`，已转 D哥）。
  本 change **不升版**，故不在本轮修复。
- 1 条「影子副本 `~/.workbuddy/skills` 下有 fstdd@2.2」—— 历史错装残留（不影响加载）。

### 七-4 `verify_rename` 实测

`7/8`，唯一 FAIL 为 **TC-RENAME-006「verify_eol.py 未通过」** —— 它是 `verify_eol` 的**上游依赖**
（见七-1），故与 TC-EOL-005 同因同果 ⇒ **DELIVER 提交后应同步转绿**。

---

## 八、C4 失败模式检查（23 类，全量执行）

| # | 失败模式 | 覆盖方式 | 本次检查动作与结果 |
|---|---|---|---|
| 1 | 幻觉调用 | skill 引导 | ✅ 38 个命令模块**全部可导入**（0 失败）；改动文件经 `ast.parse` 全通过 ⇒ 无未定义标识符 |
| 2 | 过度信任 LLM | skill 引导 | ✅ 评审 3 代理共报 9 条 + 4 条「不改」；**逐条实证**后修复 3 条生产缺陷、加固 6 条测试问题、驳回 0 条（另有 4 条经核验属可接受）—— 未凭报告直接采信 |
| 3 | Prompt 注入 | skill 引导 | ✅ 改动文件扫描 `ignore previous` / `you are now` / `disregard ...` ⇒ **0 命中** |
| 4 | 记忆污染 | skill 引导 | ✅ 本 change 全程以「Phase 1/2 产出物 + 实测」为准，未依赖上一 session 结论（其中 2 条上一版结论被实测**推翻**：`phase` 非唯一违规者、`_dryrun.py` docstring 数字失真） |
| 5 | 上下文窗溢出 | skill 引导 | ✅ 单次 `Edit` 均 < 300 行；新增模块 `_dryrun.py`(72) / `_proposal_anchors.py`(56) 均为小文件 |
| 6 | 工具参数漂移 | skill 引导 | ✅ 仅用既有 CLI 子命令（`canon`/`ci`/`extract-proposal`/`phase`）与 pytest 官方参数（`--junit-xml` / `-p no:cacheprovider`）；**未使用** `phase advance --dry-run`（本 change 自设纪律） |
| 7 | 安全凭证泄露 | 三层 | ✅ 改动文件凭证字面值扫描：**38 文件 / 0 命中**；`verify_notices` 实跑（临时目录 + 合成凭证形状）确认 `--json` **不回显**凭证且**默认不移动**文件；新增测试断言「隔离记录/记录 JSON 无凭证字面值」 |
| 8 | 权限绕过 | skill 引导 | ✅ 未手改任何闸门确认字段 —— 实测 `understand` / `spec` 的 `confirmed_by=dialog`、`confirmed_at`、`confirmed_evidence='确认'` **保持 Gate 1/2 原值**。本轮对 `.fstdd.yaml` 的写入仅为 `slices_completed` / `traceability` / `design_adjustments`（B3.4 明确要求写入的字段） |
| 9 | 并发竞态 | skill 引导 | ✅ 串行执行：单 agent、单 change、无并发推送。⚠️ 曾同时跑「全量 pytest」与「只读扫描脚本」，均为只读/独立进程，无共享写 |
| 10 | 路径遍历 | Guard | ✅ 新增代码不含用户可控的写路径拼接；`verify_notices` 的目录参数为**既有**接口（未改语义）；测试全部使用 `tmp_path` |
| 11 | 跨会话残留 | skill 引导 | ✅ 归一 `canon generate` 产出的 CRLF；清理事故产生的 `tools/_quarantine/` 条目（3 文件 + 3 记录）；`/tmp` 中间产物不落仓 |
| 12 | 输出截断 | Guard | ✅ 一律以 `--junit-xml` 取权威结果，**未据截断 stdout 下结论**（本机 pytest stdout 会被 safe-delete 守卫截断，截断时退出码非零） |
| 13 | 格式错误 | skill 引导 | ✅ 本 change 全部 11 个 YAML（含 `.fstdd.yaml` / 5 个 code spec / agent spec / proposal / canon-index / 两个 adjustments）**均可 `yaml.safe_load`**；`extract-proposal` 输出可 `json.loads` |
| 14 | 循环依赖 | skill 引导 | ✅ 命令包 import 图：39 节点 / 21 边 / **无环**；38 个模块全部可导入 |
| 15 | 重复扣款 | 金融红线 | ⏭ **SKIPPED** —— 本 change 不涉及支付/资金流转（`risk_assessment.financial = false`） |
| 16 | 账实不符 | 金融红线 | ⏭ **SKIPPED** —— 无账本/对账源 |
| 17 | 静默降级 | 金融红线 | ✅ **适用且已修**：本 change 修的正是「静默」类缺陷 —— `--dry-run` 被静默忽略（缺陷 1）、`verify_notices` 静默移走文件（缺陷 6）。修法均改为**显式出声**（预览行 / 告警 + 非零退出码 + `would_quarantine`） |
| 18 | 精度丢失 | 金融红线 | ⏭ **SKIPPED** —— 无金额字段 |
| 19 | 审计缺口 | 金融红线 | ⏭ **SKIPPED** —— 无资金/权限变更。⚠️ 但本 change 的**自我审计缺口**已闭环：`test-report.md`（本文件）+ `design-adjustments.yaml` + `.fstdd.yaml` 切片证据三方留痕 |
| 20 | 状态机漏洞 | 金融红线 | ⏭ **SKIPPED** —— 无交易状态机。⚠️ 但 FSTDD 自身的相位状态机已受 `test_phase.py` 回归保护（非 dry-run 路径行为不变，TC-DRY-002） |
| 21 | 额度穿透 | 金融红线 | ⏭ **SKIPPED** |
| 22 | 合规遗漏 | 金融红线 | ⏭ **SKIPPED** —— 无 KYC/AML/跨境数据 |
| 23 | 过度工程 | YAGNI-7 梯子 | ✅ 逐项回答见下 |

### #23 过度工程（YAGNI-7 梯子）

| 新增物 | 1 真需要 | 2 本仓已有 | 3 标准库 | 4 平台原生 | 5 已装依赖 | 6 一行 | 7 最小实现 | 结论 |
|---|---|---|---|---|---|---|---|---|
| `_dryrun.py`（72 行） | ✅ 15 个模块 / 78 个写点必须逐一守住 | ❌ 无 | ✅ `functools` | — | — | ❌ 15 模块 × 4 行 = 60 行散点、且必然再漏 | ✅ 1 装饰器 + 1 早返回助手 + 1 判定函数 | **保留**（消重 + 收口，符合 EXP-2026-0020） |
| `_proposal_anchors.py`（56 行） | ✅ D4 要求锚点同源，两侧硬编码正是缺陷 3 的成因 | ❌ 无 | — | — | — | ❌ 两侧各写一份 = 契约断层的复发口 | ✅ 纯常量 + 元组，零逻辑 | **保留** |
| 5 个测试文件（33 函数） | ✅ 17 个 TC 的载体，且 RED→GREEN 硬要求 | — | ✅ pytest | — | — | ❌ | ✅ | **保留** |

---

## 八-补、C5 经验库记录

新增 3 条经验（经 `fstdd experience add` 写入 `.fstdd/experiences/`，`lifecycle_state: discovered`）：

| ID | 分类 | 严重度 | 模式 |
|---|---|---|---|
| **EXP-2026-0023** | `runtime_deviation` | high | 「为取 RED 证据而临时回退修复，随后运行该修复对应的用例」—— 若被测行为本身是破坏性的，**取证过程就会造成真实事故**（本次实测移走 3 个已跟踪文件）。修法：RED 取证必须在隔离副本进行；无法隔离时测试须带 `finally` 自愈复原 |
| **EXP-2026-0024** | `coverage_vacuum` | high | 「契约扫描器按『模块里是否出现 X』判定合规」—— 模块内**局部**未守住 X 的路径被漏判（判据粒度 = 模块，缺陷粒度 = 写点/路径）。修法：静态判据之外必须配**行为断言** |
| **EXP-2026-0025** | `contract_gap` | medium | 「为消除误判而放宽判据时，新判据在**未见过的样本形态**上产生新的误判」—— 修 A 缺陷引入 B 缺陷。修法：变更判据后必须对**全量既有样本**回归并断言零误判 |

**顺带完成的活体验证（缺陷 2 / 5 的修复在生产路径上生效）**：

- `experience add` 三次 ⇒ `.fstdd/experiences/.experience-index.yaml` 全程 **CRLF=0**（修复前会变 CRLF=322）；
- `experience list --format json`（**无过滤**）⇒ **76 条全部输出、零崩溃**（修复前 `TypeError: date is not JSON serializable`，EXIT=1）；
- `experience add` 产出的 3 个条目文件本身是 CRLF（ADJ-002 同族，已手工归一并登记为已知问题 #9）。

---

## 九、已知问题与未完成项

| # | 名称 | 原因 | 影响 | 补完计划 |
|---|---|---|---|---|
| 1 | `upstream/fstdd/` 下 **70 处 `write_text` 未传 `newline=`** ⇒ Windows 写 CRLF | ADJ-002：D2 经 D哥 确认只覆盖经验库索引 | 每次 `canon generate` 产出 CRLF 的 `proposal.md`/`caveman_summary.txt`（BUILD 期间已复现并手工归一）；会撞 `verify_eol` TC-EOL-003 | 另立 change；复用 `tests/test_experience_io_contract.py` 的「写盘后断言无 CRLF」模式 |
| 2 | **`fstdd experience list`（读命令）会重写索引** | ADJ-003：与「dry-run 不被尊重」是两个缺陷 | 跑一次即把索引从 LF 改成 CRLF | 另立 change：`list` 走只读索引路径，或仅索引陈旧时重建 |
| 3 | **渲染器仍不输出 7 段**（Constraints / Stakeholders / Risk Areas / NonGoals / Critical / Risk Assessment / Anchoring） | ADJ-005：冻结的 SC-008/009/010 只要求 Capabilities + Impact | `extract-proposal` 的 `constraints/stakeholders/risk_areas/non_goals` 仍恒空；**连带** `ci` 的 (b) 范围蔓延检查**长期失效** | 另立 change；复用 `_proposal_anchors` 单一事实源模式 |
| 4 | **dry-run 契约扫描是模块级判据**，无法识别「同模块内某一处写路径未守住」 | 静态判据固有上限（正是 `canon verify` 漏判的成因） | 新命令若「部分守住」仍可能漏 | 已用行为断言（TC-DRY-003b/003c）作第二层防线；长期可考虑「写点级」扫描（需逐个定义写点的 dry-run 语义） |
| 5 | **`ci` 的 (b)/(l) 检查在 BUILD 阶段恒 SKIP** | (b) 依赖未渲染的 Risk Areas 段；(l) 只认仓库根 canonical | 门禁实际覆盖 7/10 | (b) 随 #3 一并解决；(l) 属流程设计（DELIVER 后可查），登记为口径说明 |
| 6 | **`TC-[A-Z]+-\d{3}` 硬编码 3 位** | 项目约定即 3 位（`quality.yaml` → `TC-{CAPABILITY}-{NNN}`） | 未来若出现 4 位 ID 会被截断 | 暂不改（放宽会改变既有解析语义）；出现 4 位 ID 时再改 |
| 7 | **四自检在办 change 期必然红**（TC-RENAME-006 / TC-EOL-005） | 判据是「索引 vs HEAD」/「无游离 untracked」，与「未提交」天然冲突 | 不能在 BUILD 阶段直接判门禁失败 | **DELIVER 两段式提交后复跑**（上一版 v3.3.6 实测：提交后 rename 8/8、eol 7/7、skill_standards 7/7） |
| 8 | **本机 skill 版本戳停在 3.3.5**（仓库 3.3.6） | 上一版 DELIVER 未重跑 `tools/install_workbuddy_skills.py` | `verify_workbuddy_skills` WARN | 属上一版遗留；随下一版 DELIVER 一并重跑（**本 change 不升版**） |
| 9 | **`experience add` 写出的条目文件是 CRLF**（实测 `EXP-2026-0023/0024/0025.md` 均 CRLF=30） | ADJ-002 同族（`_cmd_add` 的 `exp_file.write_text` 未传 `newline=`） | 每次 `experience add` 都在工作树引入 CRLF 条目，与已提交的 LF 条目不一致 ⇒ 反复触发 `add` 时的 CRLF 告警 | 已手工归一；根治随 ADJ-002 的独立 change |
| 10 | **全仓裸 except 审计表需随每次改动位移刷新**（机制性负担） | 审计表按 `(file, stmt, handler)` 指纹 + ±5 行容差校验；本 change 一次就造成 7 处位移 | 任何改动命令模块行数的 change 都必须顺手刷新活表，否则 `test_aud_002` / `test_grd_001` 红 | 机制设计如此（可接受）；建议在 BUILD 清单里显式列出「跑 `tools/audit_silent_except.py` 并刷新活表」 |
| 11 | **命令模块新增相对导入会破坏「孤立加载」型测试** | 本 change 为 15 个模块加了 `from ._dryrun import ...` | 实测仅 1 例（`test_evidence_ops.py` 加载 `baseline.py`）；已改为包导入 | 已修；后续给命令模块加相对导入时，须 grep `spec_from_file_location` 确认无孤立加载点 |
| 12 | **`VALID_CATEGORIES` 与既有条目的 category 不一致** | 合法值 15 项（`hallucination`/`contract_gap`/…）**不含** `tooling` / `quality`，而既有 `EXP-2026-0020`（`tooling`）、`EXP-2026-0021`（`quality`）正是这两个值 ⇒ CLI 无法再创建同类条目（本次被迫改用 `coverage_vacuum` / `contract_gap`） | 经验库分类口径分裂：老条目用旧分类、新条目用新分类 | 建议另立 change 统一分类口径（或把旧值加入合法列表） |

---

## 十、结论

- **TC 覆盖率 17/17（100%）**，33 个新增测试函数，5 个切片全部 RED→GREEN 通过。
- **全量回归首跑暴露 4 处失败，逐条实证后 3 处修复、1 处判定为结构性**（`test_a6`，DELIVER 提交后转绿）。
  另修复 1 处上一版遗留的文档失真（`test_ubl_003`）。**无「未知原因」失败，无 flaky 归因**。
- **C1/C2/C3/C4/C5/C6/C7 七步全部执行**，其中 C1 报出的 3 处生产缺陷已就地修复。
- 6 个目标缺陷全部修复，且**每个缺陷都有「违例能抓到 + 合法不误报」的双向断言**。
- 遗留 11 项已知问题**全部登记**（4 项属独立欠账，需另立 change）。
- **待 D哥 Gate 3 确认**后进入 Phase 4 DELIVER。

### ⚠️ 给 DELIVER 的必办事项（本 change 暴露的流程缺口）

1. **升版时必须同步 `docs/UPSTREAM_BASELINE.md` 的 R 轴** —— 否则 `test_ubl_003` 必红
   （上一版 v3.3.6 即栽在此处）。
2. **提交前归一 CLI 产物的行尾**（`canon generate` / `experience add` 都会写 CRLF，ADJ-002）。
3. **四自检须在提交后复跑**（TC-EOL-005 / TC-RENAME-006 / `test_a6` 只在干净树上为绿）。
4. `tools/install_workbuddy_skills.py` 需重跑以更新本机 skill 版本戳。
