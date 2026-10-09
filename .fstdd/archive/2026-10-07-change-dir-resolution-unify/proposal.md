# 归档生命周期收口：change 目录解析统一 + 归档/恢复状态自洽

<!-- source_hash: 658c04db4dcce882 -->
<!-- generated_at: 2026-10-07T14:19:04+00:00 -->
<!-- canonical: canonical/proposals/2026-10-07-change-dir-resolution-unify.yaml -->

## Why

2026-09-26 的 change（`2026-09-26-finder-archive-fallback`）建立了 change 目录的
**统一解析入口** `finder.find_change_dir(name, root, *, include_archive=...)`，并让 4 条命令
在归档 change 上可用（validate / status / canon verify / structure merge）—— 但**只覆盖了一部分**。
实测（@f7bf8ec，对已归档的 `2026-10-07-tool-defect-fixes`）：

1) 仍有 **5 个模块**各留一套自建解析器，只扫 `.fstdd/changes/`，**无 `archive/` 回退**：
   `phase.py::_find_change`(20-31) / `gate.py::_find_change_dir`(23-30) /
   `state.py::_find_change_dir`(17-26) / `work.py::_find_change`(16-30) /
   `baseline.py::_resolve_change`(65-80)。而 `canon` / `ci` / `diff` / `dependency_graph` /
   `extract_proposal` / `status` / `structure` / `validate` 已走统一入口 ⇒ **口径分裂**。

2) 实测失败：`fstdd phase status <archived>` / `fstdd state <archived>` /
   `fstdd work list <archived>` 均以非 0 退出（`gate` / `baseline` 为代码确认）。

3) **错误信息误导**：报 `.fstdd.yaml not found in <name>`（`state` 甚至把
   `.fstdd\changes\<name>` 这个**它去错地方找**的路径打印出来）—— 读起来像「这个 change 不存在」，
   而实际是「本命令不支持归档区」。使用者会去翻找一个并不缺失的 change。

4) 最刺眼的一条：**`gate amend-audit` 的设计用途就是给历史/归档 Gate 追加追认审计**
   （`--gate` + `--confirmed-by` + `--evidence` 三参必填），却因解析器不支持归档而用不了。

连带发现同一族（归档生命周期）的两处状态机不自洽：

5) `archive` **不闭合相位** ⇒ 归档态悬空。实测 3 个历史 change 的归档态：
   `2026-10-04-baseline-failures-zero` → `deliver: in_progress`；
   `2026-10-06-legacy-debt-cleanup` → `current_phase: build` + `deliver: pending`；
   `2026-10-05-upstream-baseline-alignment` → 唯一正确闭合者（`deliver: completed`）。

6) `rollback` **无条件**把 `current_phase` 重置为 `understand`（`--dry-run` 实测输出
   `更新状态: status=active, current_phase=understand`），而 `phases.*.status` 全部保留 ⇒
   恢复后 `current_phase=understand` 与 `phases.understand.status=completed` 自相矛盾，
   继续推进会回到 `spec` 而非原相位（`rollback` 的语义是「恢复」，不是「重做」）。

共同主线：**同一件事（解析 change 目录 / 迁移归档状态）存在多份实现或多处写入，彼此口径不一致**
—— 与 EXP-2026-0013「契约断层」、EXP-2026-0024「判据粒度错配」同族。


## What Changes

- 把 5 个模块（`phase` / `gate` / `state` / `work` / `baseline`）的自建 change 目录解析器全部替换为统一入口 `finder.find_change_dir(..., include_archive=True)`，删除重复实现 —— **读路径**（`phase status` / `state` 查看 / `work list` / `gate` 查询 / `baseline` 读）统一支持归档 change
- **写路径**在归档 change 上默认拒绝，并给出准确、可操作的提示（`已归档：<name>（.fstdd/archive/…）；如需修改请先 fstdd rollback <name>`），彻底消除「.fstdd.yaml not found」这类误导文案；**`gate amend-audit` 例外** —— 按设计用途允许对归档 change 追加追认审计
- `archive` 归档时闭合相位：写 `phases.deliver.status = completed`，消除「已归档但 deliver 仍 in_progress / pending」的悬空态
- `rollback` 恢复时保留原 `current_phase`（仅把 `status` 置回 `active`），不再无条件重置为 `understand` —— 使「恢复后可继续原相位」成立
- 防复发契约测试：凡「接受 change 名」的命令模块必须走统一入口（AST 扫描 + 双向自检）；并对归档 change 做逐命令行为断言（读必成功 / 写必给准确拒绝 / `amend-audit` 必放行）

## Capabilities

### New Capabilities

- **archive-state-consistency**：归档与恢复两端的相位状态自洽：归档即闭合相位；恢复保留原相位，不产生 current_phase 与 phases.*.status 互相矛盾的中间态

### Modified Capabilities

- **change-dir-resolution**：change 目录解析的唯一入口覆盖全部命令：读路径统一支持归档 change，写路径在归档 change 上有明确且准确的出口，不再出现口径分裂或误导性报错

## Impact

**代码层面**：
- upstream/fstdd/cli/commands/phase.py：删除 `_find_change`(20-31)，改走统一入口；写路径加归档拒绝
- upstream/fstdd/cli/commands/gate.py：删除 `_find_change_dir`(23-30)，改走统一入口；`amend-audit` 放行归档
- upstream/fstdd/cli/commands/state.py：删除 `_find_change_dir`(17-26)，改走统一入口；`--set` 在归档 change 上拒绝
- upstream/fstdd/cli/commands/work.py：删除 `_find_change`(16-30)，改走统一入口；`add` 在归档 change 上拒绝
- upstream/fstdd/cli/commands/baseline.py：`_resolve_change`(65-80) 改走统一入口；`establish` 在归档 change 上拒绝
- upstream/fstdd/cli/commands/archive.py：归档时闭合 `phases.deliver.status = completed`
- upstream/fstdd/cli/commands/rollback.py：恢复时保留原 `current_phase`（不再重置为 understand）
- 新增测试：契约扫描（接受 change 名的模块必须走统一入口）+ 归档 change 逐命令行为断言（读 / 写 / amend-audit 三侧）

**配置层面**：
- 无：不改 .fstdd/config.d/**、不改 .gitattributes、不改 .gitignore

**基础设施**：
- 无：不动服务器、不推远端、不改 CI / hook

## Success Criteria

- [ ] 对已归档 change：`phase status` / `state` / `work list` 均 rc=0 且输出该 change 的真实信息（修复前 rc≠0 且报「.fstdd.yaml not found」）
- [ ] 对已归档 change：`phase advance` / `phase set` / `phase record-slice` / `state --set` / `work add` / `baseline establish` 均**拒绝执行**，且输出同时含「已归档」与「rollback」字样
- [ ] 对已归档 change：`gate amend-audit` 可正常执行（rc=0），且行为与在办 change 上一致
- [ ] `archive` 完成后，归档 change 的 `phases.deliver.status == completed`；且 `phases.*` 的 `confirmed_at` / `confirmed_by` / `confirmed_evidence` 与归档前逐字节一致
- [ ] `rollback` 完成后，`current_phase` 与归档前一致、`status == active`，且 `phases.*` 状态与闸门字段零改动
- [ ] 契约扫描：全仓「接受 change 名」的命令模块 100% 走 `finder.find_change_dir`（违规数 = 0），且扫描器自带「能抓到违例」的反向自检
- [ ] 在办 change 上的既有行为零回归：`test_phase` / `test_gate` / `test_state` / `test_work` / `test_baseline*` / `test_finder` / `test_changes_dir_consistency` 全绿；全量 `pytest upstream/tests` 与仓库根 `tests/` 零新增失败；四自检全绿
