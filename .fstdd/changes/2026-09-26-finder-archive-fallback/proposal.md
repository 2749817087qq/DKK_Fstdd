# change 目录解析增归档回退 —— 让 validate / status / canon verify / structure merge 归档后仍可用

<!-- source_hash: f0b91027f03c9ea1 -->
<!-- generated_at: 2026-09-26T04:04:19+00:00 -->
<!-- canonical: canonical/proposals/2026-09-26-finder-archive-fallback.yaml -->

## Why

一个 change 被 `stdd archive` 归档后，一组 CLI 命令**必然**失败（exit 1），
因为它们解析 change 目录时只查 `.fstdd/changes/`，**没有 `.fstdd/archive/` 回退**。
而 DELIVER 流程把「归档」排在这些步骤之前 ⇒ **DELIVER 自身不可用**：
走完 Step 1（归档）之后，Step 2 起的 canon / structure / validate 全部报
「找不到 change」，只能靠「还原 → 执行 → 再归档」的人工往返绕开。

更关键的是：**解析器不止一处**。实测存在四个各自独立、都硬编码 `changes/` 的实现：

  - upstream/fstdd/cli/finder.py:5            find_change_dir   （有校验、有后缀匹配）
  - upstream/fstdd/cli/commands/canon.py:12   _get_canon_dir    （纯路径拼接）
  - upstream/fstdd/cli/commands/gate.py:22    _find_change_dir  （纯路径拼接）
  - upstream/fstdd/cli/commands/state.py:16   _find_change_dir  （纯路径拼接）

另有 canon.py:20 `_find_current_change` 与 structure.py 内的直接拼接。
⇒ 只修 finder.py 一处**不足以**修好 `canon verify`（它根本不走 finder）。


## What Changes

- finder.find_change_dir 新增**关键字参数** include_archive（bool，默认 False）；
为 True 时先在 .fstdd/changes/ 解析，未命中再回退 .fstdd/archive/。
默认 False ⇒ 所有未显式传参的既有调用点行为**零漂移**。

- canon._get_canon_dir 不再纯拼接 changes/<name>/canonical，改走统一解析（含归档回退）
—— 这是让 canon verify / canon generate 归档后可用的必要修复。

- structure.cmd_structure_merge 的 delta 路径改走统一解析（含归档回退）。

- validate / status / ci / diff / dependency_graph / extract_proposal 六处调用点
显式传 include_archive=True（语义都是「查询某个 change」，归档后查询合法）。

- archive / abort **保持** include_archive=False —— archive 必须只解析 changes/，
否则会把自己从 archive/ 再移动一次。

- 新增测试：归档后四命令可用（正例）+ archive 不解析 archive/（零漂移反例）。


### New Capabilities

- **change-dir-resolution**：统一的 change 目录解析能力：可选归档回退、changes/ 优先、支持精确名与后缀匹配，
并区分「只查在办」与「含归档」两种语义。


### Modified Capabilities

- **validate**：支持校验已归档的 change（原先归档后 rc=1 找不到 change）
- **status**：支持查询已归档的 change 状态
- **canon verify**：支持对已归档 change 做 canonical 校验（原先必然报 canonical/proposals 不存在）
- **structure merge**：支持读取已归档 change 的 code-structure-delta

## Success Criteria

- [ ] find_change_dir 默认行为逐字不变：不传 include_archive 时，只存在于 archive/ 的 change 仍返回 None
- [ ] 传 include_archive=True 时，只存在于 archive/ 的 change 可被解析到；changes/ 与 archive/ 同名时取 changes/
- [ ] 归档后 validate / status / canon verify / structure merge 四条命令不再因「找不到 change」失败
- [ ] archive 命令行为零漂移：不得解析到 archive/（否则自我移动）
- [ ] rollback 既有的 archive 搜索逻辑不被破坏
- [ ] 全量测试 0 failed；新增用例覆盖上述正例与零漂移反例
