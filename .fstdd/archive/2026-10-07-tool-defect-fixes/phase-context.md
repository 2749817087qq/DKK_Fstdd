# Phase Context — 2026-10-07-tool-defect-fixes

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  每章节末尾附「完整上下文文件清单」，需要更多细节时回溯原文。

  ⚠️ 此文件由 AI 自动维护，人类不应手动编辑。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-10-06T17:47:57+00:00)

### 关键决策
- **需求边界**：D哥 指定把上一版（v3.3.6）test-report §九 遗留 11 条中的 **6 条既有工具缺陷**合并为一个 change。共同主线 = **契约断层**（工具的声明 / 参数名 / 参数语义 / 检查判据与实际可执行形态不一致），与 EXP-2026-0013 同族。
- **模式判定**：complexity_score = **8** → `thorough`（文件数 ~11 → 2｜行数 300-600 → 2｜Capability 5 → 2｜风险 中 → 2｜数据/API 无 → 0｜安全 无 → 0）。
- **D哥 未调整模式建议**，按 `thorough` 执行。

### 用户关注点
- D哥 明确要求**合并处理**（"合并成下一个 change 处理"），未要求拆分。
- C6（`verify_notices` 默认行为变更）在 Gate 1 展示后**未被否决** ⇒ 按「默认只报告 + `--quarantine` 显式移动」执行。

### 被否决的方向
- 方向 A：把 6 条拆成多个 change — 原因：D哥 指定合并，且六者同主线、单项都小。
- 方向 B：只修 `phase` 的 dry-run 而不加防复发契约测试 — 原因：EXP-2026-0013 / KG-093 的形态会重现。

### 产出物清单
- proposal.md — Gate 1 已确认，confirmed_at: 2026-10-06T17:47:57+00:00，evidence:「确认」
- canonical/proposals/2026-10-07-tool-defect-fixes.yaml — source_hash: `8be04ae641046ce6`
- 6 what_changes / 5 capabilities（全 modified）/ impact（code+config+infra）/ 9 success_criteria
- 复杂度评分 8 → mode `thorough`

### 完整上下文文件清单
- proposal.md：需求背景、6 条 what_changes、5 个 modified capability、约束、9 条成功标准

---

## Phase 2: SPEC (completed 2026-10-06T18:13:48+00:00)

### 关键技术决策（design.md 的 7 条）
- **D1 `--dry-run` 契约同源**：`phase.py` 按既有范式（`getattr(args, "dry_run", False)` + 早返回）补实现；**并新增契约扫描测试**（凡有写操作的命令模块必须处理 `dry_run`），使「新命令忘记实现」不复发。`--dry-run` 是全局注册选项（`cli/__init__.py:13`），既有 8 个命令已实现，唯独 `phase.py` 漏网。
- **D2 索引写盘 LF**：`_save_index()` 补 `newline=""` + 显式换行符。
- **D3 JSON 统一归一**：引入 `_json_default()` 并覆盖该模块**全部 5 个** `json.dumps` 调用点（468/539/638/1186/1253），不逐处补。
- **D4 渲染器/解析器锚点同源（双向修）**：渲染器补出 `## Capabilities` 与 `## Impact`（实测 `canon.py` 中 `Impact` **0 命中**），解析器兼容 h2 与 h3；两者共用锚点常量。`what_changes` 解析在首个 capability 锚点处截断（消泄漏）。
- **D5 `ci` (d) 判据改结构化「定义点」**：不再用全文 `count>1`；引用不计，两个定义点才 FAIL。
- **D6 隔离改 opt-in**：`verify_notices` 默认只报告（新增 `would_quarantine` + 非零退出码），`--quarantine` 才移动。
- **D7 新增断言自带自检 + 覆盖全量**：扫描/审计类测试须含正反双向样本；枚举类断言用**集合相等**而非抽检。

### 经验触发记录（Step 2 / 2.5）
- **EXP-2026-0013**（契约断层，high）→ D1 / D4：声明与实现同源 + 用声明样例做参数化测试。
- **EXP-2026-0016**（文本扫描假阳性，low）→ D5：改结构化映射。**该经验正是缺陷 4 的历史记录**，本次把它真正修掉（此前只是「记为已知假阳性」）。
- **EXP-2026-0015**（隔离=移动，high）→ D6：破坏性默认改 opt-in。
- **EXP-2026-0021**（审计工具假绿，high）→ D7：审计器必须自带自检。
- **KG-093**（high，跨项目 12 次）「声明了约束但从未生效」→ D1 / D4。
- **KG-092**（high）「失败静默腐烂」→ D1 / D6。
- **KG-094**（critical）「断言只覆盖少数几个字段」→ D7：集合相等，不抽检。
- **KG-095**（medium）「第二层防线不可观测」→ D6：保留 `would_quarantine`。

### 已知坑点 / 注意事项
- 🔴 **`extract-proposal` 本 change 期间不可用**（正是待修缺陷 3）⇒ Phase 2 全程改用 canonical YAML 取数。
- 🔴 **`experience list --format json` 无过滤时崩溃**（待修缺陷 5）⇒ 改用文本模式 / 脚本直读。
- 🔴 **`--dry-run` 在 `phase` 上会真实落盘**（待修缺陷 1）⇒ Phase 2 未使用 `--dry-run`。
- 🔴 **`experience` 命令会把索引写成 CRLF**（待修缺陷 2）⇒ Phase 2 期间实测复现（LF → CRLF=322），已 `git checkout` 还原。
- ⚠️ **`knowledge predict` 的参数是 `--change-name`**（不是位置参数）。
- ⚠️ **`canon` 渲染器不输出 `## Capabilities` / `## Impact`** ⇒ 任何依赖 `extract-proposal` 的自动化在修复前都拿不到这两块。
- ⚠️ **`ci check-failures` 的 (d) 判据**：38→41 份 test-plan 中 25 份（60%）被误判，属既有噪声。

### 未解决问题（待 Phase 3 验证）
- **渲染器新增两个 h2 后，历史归档 proposal.md 是否仍可解析？** 当前假设：可以（解析器双向兼容）。验证方式：对归档 change 抽样执行 `extract-proposal`（TC-PXF-003）。
- **`json.dumps(default=)` 是否改变既有输出？** 当前假设：不变（仅在无法原生序列化时生效）。验证方式：对 `--language python` 子集比对修复前后 JSON 文本（TC-EIO-005）。
- **放宽 (d) 判据是否会漏掉真冲突？** 当前假设：不会（定义点计数）。验证方式：构造「两个定义点」样本必须 FAIL（TC-CCA-002）。

### 产出物清单
- design.md — 7 决策 + 缺陷→修复点→Scenario 映射 + 调用链 + 8 条风险
- canonical/specs/code/{dry-run-fidelity, experience-io-contract, proposal-extraction-fidelity, ci-check-accuracy, quarantine-opt-in-safety}.yaml — **7 REQ / 15 Scenario**（置信度全 high）
- canonical/specs/agent/2026-10-07-tool-defect-fixes.yaml — 9 步验证 + 4 期望 + 3 步回滚
- specs/<capability>/spec.md — 5 个 Human View（Gate 2 自动生成）
- test-plan.md — **17 TC**（TC-DRY×4 / TC-EIO×5 / TC-PXF×3 / TC-CCA×2 / TC-QIS×3）；P0 14 / P1 3 / P2 0
- canonical verify: 2/2

### 完整上下文文件清单
- design.md：Decisions（D1–D7）、Architecture、Risks
- specs/<capability>/spec.md：GIVEN/WHEN/THEN 行为规格
- test-plan.md：TC-ID 映射、测试策略、执行矩阵、回归风险矩阵、证据表

---

## Phase 3: BUILD (completed 2026-10-07)

### 执行模式
- `long_range.mode = full_auto`（Gate 2 后选定；`pre_auth_completed: true`）。全程无交互，仅在 Gate 3 暂停。

### 切片方案与执行结果（5 切片，实际顺序 S2 → S4 → S1 → S5 → S3）

| # | capability | TC 覆盖 | 新增测试 | 状态 |
|---|-----------|---------|---------|------|
| 2 | experience-io-contract | 5/5 | 7 | ✅ done |
| 4 | ci-check-accuracy | 2/2 | 7 | ✅ done |
| 1 | dry-run-fidelity | 4/4 | 6 | ✅ done |
| 5 | quarantine-opt-in-safety | 3/3 | 6 | ✅ done |
| 3 | proposal-extraction-fidelity | 3/3 | 7 | ✅ done |

合计：**17/17 TC**、**33 个新增测试函数**（5 个新测试文件）、RED→GREEN 逐切片留痕。

### 新增/修改的源码
- **新增** `upstream/fstdd/cli/commands/_dryrun.py` —— `--dry-run` 统一守卫（`dry_run_guard` 装饰器 / `dry_run_preview` 早返回 / `dry_run_requested` 判定）
- **新增** `upstream/fstdd/cli/commands/_proposal_anchors.py` —— 渲染器与解析器**共用的锚点常量**（单一事实源）
- **修改** 16 个命令模块（`phase` 等）接入 dry-run 守卫；`experience.py`（`newline=""` + `_json_default`）；`ci.py`（(d) 定义点判定）；`canon.py`（渲染器补 `## Capabilities`/`## Impact` + verify 的 dry-run 守卫）；`extract_proposal.py`（锚点同源 + what_changes 截断）；`tools/verify_notices.py`（默认只报告 + `--quarantine`）
- **新增测试** `tests/`：`test_dry_run_fidelity.py`、`test_experience_io_contract.py`、`test_ci_tcid_definition.py`、`test_verify_notices_default_safe.py`、`test_proposal_extraction_fidelity.py`

### 设计偏离（7 条 → `design-adjustments.yaml`）
- **就地闭合**：ADJ-006（渲染器两 h3 恒定输出）、ADJ-007（C1 评审报出的 3 处真实缺陷）
- **转为独立欠账**：ADJ-002（70 处 `write_text` 未传 `newline`）、ADJ-003（`experience list` 读命令有写副作用）、ADJ-005（渲染器仍缺 Constraints/Stakeholders/Risk Areas/NonGoals 等 7 段）、ADJ-001（范围扩大至 15 模块，已获 D哥 授权）
- **仅记录**：ADJ-004（扫描口径收紧 ⇒ 数字修正 15 模块/78 写点）

### 🔴 BUILD 期间新增的硬事实（长期有效）

- 🔴 **`canon verify` 有一处隐藏写路径**：`cmd_canon_verify` 在「Human View 缺 source_hash」时会调
  `_generate_one` **自动重生成** `proposal.md` + `caveman_summary.txt` ⇒ 修复前 `canon verify --dry-run`
  照样落盘。**且静态契约扫描器抓不到** —— 判据是「模块级是否出现 dry_run」，而 `canon.py` 因其它
  装饰器已含 dry_run ⇒ **模块级判据存在固有上限**，必须配行为断言（TC-DRY-003b/003c）。
- 🔴 **为取 RED 证据而回退修复，本身就是破坏性操作**：2026-10-07 回退 `verify_notices.py` 后跑
  「对仓库根默认运行」的用例，实测把 `README.md` / `CHANGELOG.md` / 一份 notices md **移入
  `tools/_quarantine/`**（EXP-2026-0015 第三次命中），工作树出现 3 个 `D`、全量测试收集失败。
  ⇒ **纪律**：RED 证据必须在隔离环境取；若无法隔离，测试本身须带「自愈式 finally 复原」。
  已按字节比对复原（3 个文件与 HEAD 逐字节一致），并在测试里固化为
  `_restore_repo_root_from_quarantine()`。
- 🔴 **「TC-ID 作首列」的表格有两种语义**：既可能是定义表，也可能是 **TC↔测试函数映射表**。
  实测 `2026-09-25-guard-phase-path-scope/test-plan.md` 两者都有 ⇒ 若把两种形态取**并集**，
  会把「1 个定义 + 1 行映射」误判为重复定义（修 A 缺陷时引入 B 缺陷）。
  **正解**：形态 A（`| **ID** | TC-… |`）优先，仅当 A 抽不到时才启用形态 B。
- ⚠️ **`getattr(args, "dry_run", False)` 里的 `dry_run` 是字符串常量** —— 纯 Name/Attribute 的 AST
  匹配会漏判（实测漏掉 `structure.py`，其第 59 行正是该范式）⇒ 扫描器必须单独认 `getattr` 的
  字符串实参位置。
- ⚠️ **`batch child status` 是纯读路径**（`action=child` + 默认子动作 `status`），
  dry-run 白名单只放行 `list`/`status` 会把它误伤。
- ⚠️ **`canon generate` 每次都会把 `proposal.md` / `caveman_summary.txt` 写成 CRLF**
  （ADJ-002 同族）⇒ 重渲染后必须手工归一为 LF。
- ⚠️ **`ci check-failures` 的 (b) 范围蔓延检查对 canon 渲染的 proposal.md 恒被 SKIP** ——
  它靠 proposal.md 里的 `- capability: <name>` 行取数据，而该行只出现在**未被渲染**的
  Risk Areas 段（ADJ-005）⇒ **该检查实际长期失效**（属 ADJ-005 的连带后果）。
- ⚠️ **`ci check-failures` 的 (l) 锚定检查只认仓库根 `canonical/proposals/`**，
  开发期 canonical 在 `.fstdd/changes/<name>/canonical/` ⇒ BUILD 阶段恒 SKIP（DELIVER 合并后才可查）。
- 🔴 **改命令模块的行数会打破「裸 except 审计表」**：`test_except_audit.py::test_aud_002` 与
  `test_guard_silent_except.py::test_grd_001` 校验 `.fstdd/{changes,archive}/<change>/audit/except-points.yaml`
  （取**最新**一份）与实况扫描零漂移（指纹 `(file, stmt, handler)` + ±5 行容差）。
  本 change 造成 **7 处行号位移** ⇒ 必须生成本 change 的**活表**（25 点 / 0 新增 / 0 消失）。
  ⚠️ **未刷新时两条测试都会红**（`test_grd_001` 会把位移点报成「白名单外新增」+「失效条目」）。
- 🔴 **给命令模块加相对导入会破坏「孤立加载」型测试**：`test_evidence_ops.py` 用
  `spec_from_file_location` 单独加载 `baseline.py`，模块一旦含 `from ._dryrun import ...` 就
  `ImportError: attempted relative import with no known parent package`。⇒ 该测试已改为**包导入**
  （断言逻辑一字未改）。后续再加相对导入时须 grep `spec_from_file_location` 排查。
- ⚠️ **`experience add` 写出的条目文件是 CRLF**（实测 3 个新条目均 CRLF=30）—— ADJ-002 同族，
  须手工归一。
- ⚠️ **`experience` 的 `VALID_CATEGORIES` 与既有条目的 `category` 不一致**：合法列表 15 项不含
  `tooling` / `quality`，而既有 `EXP-2026-0020`（`tooling`）、`EXP-2026-0021`（`quality`）正是这两个值
  ⇒ 新条目被迫改用 `coverage_vacuum` / `contract_gap`。已登记为已知问题。
- ⚠️ **升版必须同步 `docs/UPSTREAM_BASELINE.md` 的 R 轴**，否则 `tests/test_upstream_baseline.py::test_ubl_003` 必红
  （上一版 v3.3.6 即遗留此失真，本 change 顺手纠正 3.3.5→3.3.6）。

### 完整上下文文件清单
- `slices.md` / `tasks.md`：切片计划与逐项完成状态
- `pending-adjustments.yaml`（7 条）/ `design-adjustments.yaml`（汇总）
- `test-report.md`：TC 覆盖率、逐切片验证、23 类失败模式检查、已知问题

---

## Phase 4: DELIVER (pending)

- 待 Phase 3 Gate 3 确认后进入

---

## Current: Phase 3 BUILD (completed) → 等待 Gate 3 确认

### 当前状态
- 5 个切片全部完成（`phases.build.slices_completed` 五项均 `status: done` 且带 tc_coverage / new_tests / verified_at）。
- `current_phase` = `build`；`mode` = `thorough`；`long_range.mode` = `full_auto`。
- 全量测试、四自检、`ci check-failures`、C1 三路评审、C3 Diff 审查、C4 失败模式检查均已完成（结论见 `test-report.md`）。

### 下一步
- **Step（强制）**：Gate 3 用户确认（长程模式**不跳过** Gate 3）。
  确认后执行 `fstdd gate approve --gate 3 --confirmed-by dialog --evidence "<用户确认原文>"`，
  再进入 Phase 4 DELIVER。
