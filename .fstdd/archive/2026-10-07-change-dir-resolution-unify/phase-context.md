# Phase Context — 2026-10-07-change-dir-resolution-unify

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  每章节末尾附「完整上下文文件清单」，需要更多细节时回溯原文。

  ⚠️ 此文件由 AI 自动维护，人类不应手动编辑。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-10-07T14:19:00+00:00)

### 需求来源

v3.3.7 DELIVER 期间实测撞上 `fstdd phase advance <已归档 change>` 不可用（报 `.fstdd.yaml not found`），
导致归档态停在 `deliver: in_progress` 无法用 CLI 闭合。D哥 指示「另立 change 统一收口」。

### 侦察结论（实测 + 代码双证，@f7bf8ec）

- **缺陷面 = 5 个模块**保留自建 change 目录解析器，只扫 `.fstdd/changes/`，**无 `archive/` 回退**：
  `phase.py::_find_change`(20-31) / `gate.py::_find_change_dir`(23-30) / `state.py::_find_change_dir`(17-26) /
  `work.py::_find_change`(16-30) / `baseline.py::_resolve_change`(65-80)。
- **已走统一入口的 10 处**：`canon` / `ci`(×2) / `dependency_graph` / `diff` / `extract_proposal` /
  `status` / `structure` / `validate`（+ `archive`/`abort`/`rollback` 刻意用 `include_archive=False`）
  ⇒ 问题是**口径分裂**，不是「全都没做」。
- **实测失败**：`phase status` ❌ / `state` ❌ / `work list` ❌（均报 `.fstdd.yaml not found in <name>`，
  属**误导文案**）；`gate` / `baseline` 为代码确认。
- 🔴 **最刺眼**：`gate amend-audit` 的设计用途就是「给历史/归档 Gate 追加追认审计」，却因解析器不支持归档而用不了。
- 连带同族两处状态机不自洽：① `archive` 不闭合相位（实测 3 个历史 change 悬空）；
  ② `rollback` 无条件把 `current_phase` 重置为 `understand`（`--dry-run` 实测输出已证实）。

### 关键决策

- **需求边界**：只收口「归档生命周期」一条主线 —— 解析统一（C1/C2/C5）+ 归档/恢复状态自洽（C3/C4）。
- **模式判定**：complexity_score = **9** → `thorough`
  （文件 2 + 行数 2 + Capability 2→1 + 风险 4 + 数据 0 + 安全 0）。
  风险取 4 的理由：命中经验库 high（EXP-2026-0013 / EXP-2026-0024）+ 改的是**流程自身的状态机与闸门路径**，
  错的后果是状态/审计被写坏，而非显示不对。
- **YAGNI 删项**：初稿的 `--allow-archived` 逃生口已删（C3 已消除其唯一动机）。

### 用户关注点

- D哥 明确要求「另立 change 统一收口」（原话）；Gate 1 以「确认」通过，未调整模式建议。
- 三个待定点由 AI 给出建议并被采纳：① C3/C4 纳入 ② 模式 thorough ③ 写路径拒绝 + 指路 rollback。

### 被否决的方向

- 方向 A：只补 `phase` 一个模块 —— 缺陷面是 5 个模块，且「补一个漏一个」正是本次缺陷的成因。
- 方向 B：`find_change_dir` 默认改为 `include_archive=True` —— 会破坏 SC-001（默认语义零漂移）并让
  `archive`/`abort` 有「解析到归档区后把自己再移动一次」的风险（SC-011）。
- 方向 C：为归档 change 开放写操作 —— 削弱「归档即终态」；C3 已消除其唯一动机。

### 产出物清单

- `canonical/proposals/2026-10-07-change-dir-resolution-unify.yaml`（`source_hash: 658c04db4dcce882`）
  —— 5 what_changes / 1 new + 1 modified capability / 8 constraints / 2 risk_areas / 4 non_goals / 7 success_criteria
- `proposal.md`（Gate 1 自动生成）；`canon verify` **2/2**
- Gate 1 已确认（`--confirmed-by dialog --evidence "确认"`）；`phase advance` → `spec` / `in_progress`

### 完整上下文文件清单

- `proposal.md`：需求背景、5 条 what_changes、2 个 capability、约束、7 条成功标准

---

## Phase 2: SPEC (completed 2026-10-07T14:37:00+00:00)

### 关键技术决策（design.md 的 8 条）

- **D1 单一入口强制化**：5 个自建解析器全部换 `finder.find_change_dir(..., include_archive=True)`，删重复实现。
- **D2 读/写语义分层**：读放行、写拒绝并指路 `rollback`；**`gate amend-audit` 例外**（其设计用途即归档 Gate 追认）。
- **D3 ★ 把「读/写差异」也收口**：新增 `finder.require_active_change_dir()` —— 否则等于又造 5 份实现
  （正是本 change 要消灭的形态；EXP-2026-0020）。
- **D4 拒绝文案契约**：三要素（「已归档」+ 归档路径 + `rollback`）+ 非 0 退出码（KG-092/KG-095）。
- **D5 `archive` 只写 `phases.deliver.status = completed`**，其余字段一个不碰。
- **D6 `rollback` 保留原 `current_phase`**（老数据兜底「首个未完成相位」→ `understand`）。
- **D7 防复发双层**：AST 契约扫描（自带双向自检）+ 真实归档 change 逐命令行为断言（EXP-2026-0024）。
- **D8 破坏性写操作白名单**：只允许 `phases.deliver.status` / `current_phase` / `status` 变，
  **闸门字段逐字段相等**（KG-094 / EXP-2026-0015）。

### 经验触发记录（Step 2 / 2.5）

- **EXP-2026-0013**（契约断层，high）→ D1/D3：声明与实现同源，扫描器用声明样例做参数化输入
- **EXP-2026-0015**（隔离=移动，high）→ D8：破坏性操作白名单 + 逐字段断言
- **EXP-2026-0016**（文本扫描假阳性，low）→ D7：判据改 AST 结构化
- **EXP-2026-0020**（按接收者语义收窄，high）→ D1/D3：`archive`/`abort`/`rollback` 三处必须保持 `include_archive=False`
- **EXP-2026-0021**（审计器假绿，high）→ D7：扫描器自带双向自检
- **EXP-2026-0023**（RED 取证即执行旧代码，high）→ Phase 3 纪律：破坏性命令的 RED 取证必须在隔离环境
- **EXP-2026-0024**（模块级判据漏判局部，high）→ **D7 双层**（本 change 的核心防线）
- **EXP-2026-0025**（放宽判据引入新误判，medium）→ D7：全量样本回归
- **KG-092**（失败静默腐烂）→ D4；**KG-093**（声明了约束但从未生效，= 本 change 根因）→ D1/D3；
  **KG-094**（断言不得抽检，critical）→ D8；**KG-095**（第二层防线不可观测）→ D4

### 已知坑点 / 注意事项

- 🔴 **`extract-proposal` 的 `constraints` / `stakeholders` / `risk_areas` / `non_goals` 仍恒返回空**
  （ADJ-005 未修）⇒ Phase 2/3 取数**以 canonical YAML 为准**（`capabilities` / `impact` / `success_criteria`
  已修好，可放心用）。
- 🔴 **`ci check-failures` 的 TC 覆盖检查会把 test-plan 里「引用他人 TC-ID」也算作计划 TC**
  ⇒ test-plan 里**不要写别处的 TC-ID 字面量**（改写为文件名/描述）。
- ⚠️ **`work` 命令此前无任何直接测试** ⇒ TC-CDR-003 将是它的首个覆盖。
- ⚠️ **`test_rollback.py` 只断言 `status == "active"`**，不断言 `current_phase` ⇒ C4 不破坏既有用例。
- ⚠️ **Gate 2 之前 `ci check-failures` 必然大面积 SKIP/FAIL**（`specs/` 为空、TC 覆盖 0/18）—— 非缺陷。
- ⚠️ **`canon verify` 的 DC-HASH 只比对 `source_hash`** ⇒ 改 canonical YAML 后必须重跑 `canon generate`。
- ⚠️ `fstdd new` + `gate approve` 会写 CRLF（`.fstdd.yaml` / canon-index / canonical YAML / spec.md /
  caveman_summary.txt / proposal.md）⇒ **每次都要归一**。

### 未解决问题（待 Phase 3 验证）

- **`_resolve_in` 与 `baseline._resolve_change` 的「多命中」语义差异**：前者取名字倒序首个、后者返回 None。
  当前假设：取首个不误伤既有用法（`baseline` 的调用点都是单命中场景）。验证方式：TC-CDR-006 覆盖。
- **`require_active_change_dir` 的双入口可能被误用**（写路径用了读入口）。当前假设：契约扫描可覆盖。
  验证方式：TC-CDR-009 要求写分支必须出现 `require_*`。
- **C4 对老数据（无 `current_phase`）的兜底取值**是否合理。当前假设：「首个未完成相位」→ `understand`。
  验证方式：TC-ASC-003/005。

### 产出物清单

- `design.md` — 8 决策（D1–D8）+ 决策→WhatChanges→Capability 映射 + 调用链 + 状态迁移图 + 7 条风险 + 命中映射表
- `canonical/specs/code/change-dir-resolution.yaml` — 3 REQ / 10 SC（SC-101..110，置信度全 high）
- `canonical/specs/code/archive-state-consistency.yaml` — 2 REQ / 5 SC（SC-201..205；SC-205 为 medium）
- `canonical/specs/agent/2026-10-07-change-dir-resolution-unify.yaml` — 8 CP / 7 期望 / 3 步回滚
- `specs/<capability>/spec.md` × 2（Gate 2 自动生成）
- `test-plan.md` — **18 TC**（TC-CDR-001..012 / TC-ASC-001..006）；P0 14 / P1 4 / P2 0
- `canon verify` 2/2；`ci check-failures` 的 (d) TC-ID 唯一 18 个（按定义点）

### 完整上下文文件清单

- `design.md`：Decisions（D1–D8）、Architecture、Risks、映射表
- `specs/<capability>/spec.md`：GIVEN/WHEN/THEN 行为规格
- `test-plan.md`：TC-ID 映射、测试策略、执行矩阵、回归风险矩阵、证据表

---

## Phase 3: BUILD (completed 2026-10-09T09:20:00+00:00)

### 切片方案（Slice）

| # | capability | TC | 执行序 | 结论 |
|---|---|---|---|---|
| 1 | `archive-state-consistency` | TC-ASC-001..006 | S1 | ✅ RED 4 failed/3 passed → GREEN 7 passed；回归 35 passed |
| 2 | `change-dir-resolution` | TC-CDR-001..012 | S2 | ✅ RED 11 failed/4 passed → GREEN 15 passed；回归 136 passed |

（执行序为 S1 → S2；S2 依赖 S1 的 `archive` 闭合语义，故先行。）

### 风险提示（实际处置）

- Slice `change-dir-resolution` 改 **5 个模块的解析入口 + `finder.py`**（🔴）⇒ 已对 15 个相关测试文件跑回归（136 passed），批级管线（`test_batch` / `test_batch_pipeline`）逐项确认未受影响。
- Slice `archive-state-consistency` 写 change 状态文件（🔴）⇒ 闸门字段由 TC-ASC-002/004 **逐字段相等**锚定。
- **RED 取证在隔离环境**（EXP-2026-0023）✅ 全部在 `tmp_path` 合成项目内，未在主工作区回退修复。
- **C1 三路评审**报出 1 处 critical（路径遍历，ADJ-001）+ 1 处实锤假阴性（`rollback.py` 死导入 + 内联自建匹配，ADJ-002），均已修。

### 产出物清单

- 源码：`upstream/fstdd/cli/finder.py`（+56）、`commands/{archive,baseline,gate,phase,rollback,state,work}.py` —— 共 **8 文件 / +261 −129**
- 测试：`tests/test_change_dir_resolution_unify.py`、`tests/test_archive_state_consistency.py`（21 个 `def test_` / 27 用例）
- 审计活表：`.fstdd/changes/2026-10-07-change-dir-resolution-unify/audit/except-points.yaml`（25 点 / 3 处行号刷新 / 0 新增 / 0 消失）
- 文档：`slices.md` / `tasks.md` / `pending-adjustments.yaml`（8 条 ADJ）/ `design-adjustments.yaml`（8 条）/ `test-report.md`
- 经验：`EXP-2026-0026`（coverage_vacuum）/ `EXP-2026-0027`（contract_gap）

### 权威验证（2026-10-09）

- `pytest upstream/tests` = **960 tests / 954 passed / 5 skipped / 1 failed**（唯一失败 `test_a6` 为结构性）
- `pytest tests` = **158 tests / 155 passed / 3 skipped / 0 failed**
- 四自检：`verify_eol` 6/7（结构性）· `verify_rename` 7/8（连带）· `verify_skill_standards` **环境阻塞**（沙箱 safe-delete 守卫 `state lock timeout`）· `verify_workbuddy_skills` PASS

---

## Phase 4: DELIVER (pending)

- 待 Gate 3 确认后执行。

---

## Current: Phase 3 BUILD (completed) → 等待 Gate 3 确认

### 当前状态

- Phase 1 / Phase 2 / Phase 3 均已确认锁定（Gate 1 / Gate 2 由 D哥 以「确认」确认；Gate 3 待确认）。
- `current_phase` = `build`；`build.status` = `completed`；2 个切片全部 done；`mode` = `thorough`。
- 工作树：8 个源码文件已修改 + 本 change 目录 + 2 条新经验 + 2 个新测试文件（均未跟踪）。
- 行尾已全量归一（`git ls-files --eol` 的 `w/crlf` = 0）。

### 下一步

- **Gate 3**：等 D哥 确认（`fstdd gate approve <change> --gate 3 --confirmed-by dialog --evidence "确认"`）。
- 确认后进入 Phase 4 DELIVER（归档 → canonical 合并 → 升版 → 三远端推送 → GitHub Release）。

