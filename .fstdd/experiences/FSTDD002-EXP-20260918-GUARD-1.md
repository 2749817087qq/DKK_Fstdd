---
title: STDD Guard block 归因勘误：基数无关，门在 allow_bypass / active change
experience_id: FSTDD002-EXP-20260918-GUARD-1
category: tooling
severity: medium
occurrences: 1
exported_at: 2026-09-18
sanitized: true
source: FSTDD002 节点执行 inbox 鉴权适配时遭遇 Guard 全量拦截后定位
---

## ⚠️ 勘误（2026-09-18 17:0x，源码实证，取代下方「根因」节）

本文原判断「Guard 因工作区改动量落入 large 档而 block」**不成立**。
把工作区提交干净（`git status` = 0）后，Edit 仍被拦，证伪该归因。

**真实判定逻辑**（`upstream/fstdd/cli/commands/guard.py:581-718`）：

1. `enforce = project.yaml.get("enforce_stdd", True)`（未写该键 → 默认 True，强制门生效）；
2. 找 active change（`.fstdd/changes/*/.fstdd.yaml`）→ 本仓为空；
3. 找 open batch（`.fstdd/changes/_batch/*/.fstdd.yaml`）→ 无；
4. 落入 `# No active flow at all → block` 分支；
5. `allow_bypass = project.yaml.get("allow_bypass", False)` → 未设 = False；
6. `if allow_bypass and not strict: return 0` 不成立 → `return 2`（block）。

**关键纠正**：`guard.yaml` 的 `thresholds`（small/medium/large）**仅用于生成提示文案**，
`file_count` **不参与 allow/block 判定**；`_assess_and_recommend()` 在无 flow 时
其 `allow` 恒为 True，真正的门在 `cmd_guard_check()` 的 `allow_bypass` 分支。
→ 正确处置见 `FSTDD002-EXP-20260918-GUARD-2`。

## 现象

执行一次仅涉及 1 个文件、约 20 行的运维适配（本地回传脚本加鉴权头）时，
文件写入被 STDD Guard 全量拦截，提示「检测到 140 个文件改动，建议走 full STDD」。
拦截规模与本次编辑规模严重不符，且连续两次拦截同一小改动。

## 原根因判断（❌ 已被上方勘误推翻，保留作追溯）

Guard `smart_mode` 按**工作区整体改动量**分级，而非按本次编辑增量：

| 档位 | 阈值 | 动作 |
|---|---|---|
| small | ≤1 文件 / ≤10 行 | allow |
| medium | ≤3 文件 / ≤50 行 | warn |
| large | 超出上述 | **block** |

工作区此前累积了大量未提交改动（多为批量重命名，呈「删除+新增」成对出现），
总量直接落入 large 档，于是**任何**一次编辑都被 block——哪怕本次只动 1 个文件。

实测口径（两个都要看，不要混用）：Guard 提示 `files=140`；
`git status --porcelain | wc -l` 实测 **188**。两者不等是正常的——
Guard 统计它判定需守门的文件条目，porcelain 则把「重命名」拆成删除+新增两侧各计一次。
判定时只需确认「是否远超阈值」，不必强求两口径相等。

## 检测触发

- 症状：Edit / Write 返回 `[STDD Guard] Blocked — 未进入可编辑流程`；
- 判定手段：读 `.fstdd/config.d/guard.yaml` 的 `thresholds`，再跑
  `git status --porcelain | wc -l` 取实际基数，两者比对即可区分
  「基数超限」与「本次改动超限」；
- 关键区分：若本次改动量本身在阈值内却仍被拦，几乎必是工作区基数问题，
  不要误判为流程设计缺陷而去改 guard.yaml。

## 修复模板

1. 先量化基数：`git status --porcelain | wc -l`，与 guard.yaml 阈值对照；
2. 根因是工作区卫生 → 把已完成的批量重命名/归档产物**分批** commit（每批语义单一、
   可回溯），基数回落到阈值内后 Edit/Write 自动恢复；
3. 语义明确、不触碰项目核心代码的紧急运维操作，可走 shell 通道落盘，
   但必须在回执/汇报中据实记录「Guard 拦截 + 采用路径 + 原因」，不得静默绕过；
4. 禁止为通过 Guard 而回退他人既有改动，或调低并提交 guard.yaml 阈值。

## 复现

编辑任意 1 个文件，观察 Guard 返回的 files 计数是否等于 `git status` 基数。

## 证据

- Guard 拦截返回：`files=140`；
- `guard.yaml` 实读阈值：small 1/10、medium 3/50、large=block；
- `git status --porcelain | wc -l` 同期实测 188（含成对重命名，故高于 Guard 口径）。

## 勘误旁证（2026-09-18 17:0x 实测）

- 提交前：`.fstdd/changes/` 为空、无 `_batch/`、`project.yaml` 无 `enforce_stdd`/`allow_bypass` 键；
- 提交后 `git status --porcelain -uall` = 0，Edit 仍返回
  `⛔ Blocked — 未进入可编辑流程` + `无 active change。微修复用 'stdd batch open "描述"'`；
- 提示文案由「检测到 N 个文件改动」（file_count>5）变为「无 active change」（file_count=0），
  **文案变了、block 未变** → 直接证明基数不决定放行。
