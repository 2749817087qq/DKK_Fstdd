# canonical 合并自动化 —— 新增 fstdd canon merge，消除 DELIVER 的手工拷贝

<!-- source_hash: fd2916ad4e5f37d6 -->
<!-- generated_at: 2026-10-16T17:00:10+00:00 -->
<!-- canonical: canonical/proposals/2026-10-12-canon-merge-command.yaml -->

## Why

DELIVER 的「canonical 合并」**没有 CLI 命令，全靠人工拷贝**：
  · `fstdd canon` 只有 `init` / `generate` / `verify`（注册点 `upstream/fstdd/cli/__init__.py:301-310`），
    `canon.py` 532 行内**无 merge**；
  · 而 DELIVER skill（`.workbuddy-ai/skills/fstdd-deliver/SKILL.md` L52-53）要求
    「① proposal → `canonical/proposals/`；② 各 capability 的 agent_spec → `canonical/specs/agent/`」；
  · `archive` 命令**只合并 Human View**（`.fstdd/specs/`），**不碰**根 `canonical/`。

由此产生三类实际损耗（均在本仓已发生）：
  ① **每次 DELIVER 固定手工动作**：根 canonical 已积 **71 个 YAML**、`.canon-index.yaml` 22 条；
     累计 **207 个归档 canonical 文件**，每次都要人工判断该拷哪些、拷到哪、索引怎么改。
  ② **命名口径不一致且无人裁决**：归档 change 内 3 个文件**全用 change 名**
     （如 `specs/code/2026-10-11-share-hardening-audit-fixes.yaml`）；而根 canonical 的
     `specs/code/` 用 **capability 名**（`repo-hygiene.yaml` / `yagni-ladder-gate.yaml` …），
     `specs/agent/` **两种混存**（既有 `inbox-deploy.yaml` 又有 change 名）。
     ⇒ 手工合并时「该叫什么名」没有单一事实源。
  ③ **易漏**：DELIVER skill 只提 proposal + agent_spec，**未提 code spec** ——
     实测 2026-10-10 那次由主理人手工补了 code spec（capability 名），
     而 2026-10-11 的 3 个 change 用了 change 名 ⇒ **同类文件两套命名并存**。


## What Changes

- 新增子命令 `fstdd canon merge <change>`（注册点 `upstream/fstdd/cli/__init__.py`，
实现在 `upstream/fstdd/cli/commands/canon.py`）：把 `changes/<change>/canonical/` 下的
`proposals/` + `specs/agent/` + `specs/code/` 合并进仓库根 `canonical/`。

- **命名口径单一事实源（含实测修正）**：目标文件名取源文件内的元数据 ——
  · proposal → `meta.change_id`；
  · code spec → `meta.capability`（实测**均含**该字段）；
  · agent spec → **回退 `meta.change_id`**（⚠️ 实测 `specs/agent/*.yaml` **不含** `meta.capability`）。
缺字段时按既有约定回退并在输出中告警，**不得静默改名**。
⇒ 结论：命名口径**无法**统一为「全部 capability 名」；上述三分法是当前数据模型下的唯一自洽解，
若要真正统一须改 agent spec 的 schema（列入 non_goals）。

- 自动维护根 `canonical/.canon-index.yaml`：登记/更新条目，**幂等**（重复执行不产生差异）。

- 支持 `--dry-run`（只预览将写哪些文件、索引如何变化）与归档 change（走 `finder` 的归档回退），
并在合并后自动跑一次 `canon verify` 自证。

- 在 `docs/UPSTREAM_PATCHES.md` **正式登记**本 change 对 `upstream/fstdd/cli/` 的修改
（本仓首个正式登记项，同时验证登记契约可用）。


## Capabilities

### New Capabilities

- **canon-merge-automation**：canonical 合并的确定性自动化：`fstdd canon merge` 按源文件元数据决定目标命名与索引登记，
幂等、可预览、可自证，消除 DELIVER 的手工拷贝与命名漂移。


### Modified Capabilities


## Impact

**代码层面**：
- upstream/fstdd/cli/commands/canon.py：新增 `cmd_canon_merge` 与根 canonical 解析/索引维护辅助函数（改动集中在新增函数，不改 `init`/`generate`/`verify` 既有逻辑）
- upstream/fstdd/cli/__init__.py：在既有 `canon` 子解析器下注册 `merge` 子命令（注册点见该文件 301-307 的 canon_subs）
- 新增测试：upstream/tests/ 下覆盖 merge 的幂等 / dry-run / 归档回退 / 命名三分法 / 索引登记 / changen-name 输入校验（正向 + 反向），以及既有 canon 测试不回绿验证

**配置层面**：
- docs/UPSTREAM_PATCHES.md：本 change 对 upstream/fstdd/cli/ 的修改**首个正式登记项**（表体 8 列齐全，含「预期回退版本」）

**基础设施**：
- 无：不动服务器、不推远端、不改 CI / hook

## Success Criteria

- [ ] SC1 `fstdd canon merge <change>` 子命令存在，且 `--dry-run` 不写盘（执行前后 `git status` 一致）
- [ ] SC2 合并后根 `canonical/` 出现该 change 的 proposal + agent/code spec，且 `.canon-index.yaml` 已登记对应条目
- [ ] SC3 **幂等**：连续执行两次，第二次 `git diff` 为空
- [ ] SC4 合并后 `fstdd canon verify <change>` **2/2 通过**
- [ ] SC5 目标命名取自源文件元数据：proposal 与 agent spec 用 `meta.change_id`、code spec 用 `meta.capability`（三分法，见 C2）；缺字段时输出告警且不静默改名
- [ ] SC6 对**已归档** change 同样可用（走 `finder` 归档回退）
- [ ] SC7 `docs/UPSTREAM_PATCHES.md` 表体已含本 change 的 upstream 修改登记行（8 列齐全）
- [ ] SC8 既有 `canon init` / `generate` / `verify` 测试全绿；全量根级与框架侧测试 0 failed
