---
title: STDD Guard 门禁真实判定逻辑与四条放行通道（源码实证）
experience_id: FSTDD002-EXP-20260918-GUARD-2
category: tooling
severity: high
occurrences: 1
exported_at: 2026-09-18
sanitized: true
source: FSTDD002 节点定位 Edit/Write 被 Guard 全量拦截的真实根因（勘误 GUARD-1）
---

## 现象

`enforce_stdd: true` 的仓库中，Edit / Write 工具被 PreToolUse hook 拦截，返回：

```
  [STDD Guard] ⛔ Blocked — 未进入可编辑流程
  [STDD Guard] 无 active change。微修复用 'stdd batch open "描述"'，新功能/重构用 '/fstdd-understand'。
```

与工作区有多少未提交改动**无关**——把工作区提交干净后依旧被拦。

## 根因

Guard 的门是「**是否处于可编辑流程**」，不是「改动量大不大」。

`guard.py` 的 `cmd_guard_check()` 判定顺序：

| 步骤 | 判据 | 本仓实况 |
|---|---|---|
| 1 | `project.yaml.enforce_stdd`（缺省 True） | 未写 → True（门生效） |
| 2 | active change：`.fstdd/changes/<name>/.fstdd.yaml` 且 status/phase 可编辑 | 无 |
| 3 | open batch：`.fstdd/changes/_batch/<id>/.fstdd.yaml` 且未 `closed_at` | 无 |
| 4 | `allow_bypass`（缺省 False） | 未写 → False |
| 5 | 以上皆否 → `return 2`（block） | **block** |

**两大常见误判**：

1. ❌「改了太多文件所以被拦」——`guard.yaml` 的 `thresholds` 与
   `_count_changed_files()` **只用于拼提示文案**；无 flow 时 `_assess_and_recommend()`
   的 `allow` 恒为 True，不参与返回码。
2. ❌「改 guard.yaml 阈值能解锁」——改阈值只改文案，不改判定。

## 检测触发

- 症状：Edit/Write 返回 `⛔ Blocked — 未进入可编辑流程`；
- 一步判定：`.fstdd/changes/` 是否为空且无 `_batch/` → 是则必为流程门，与基数无关；
- 交叉验证：把工作区提交干净重试，若文案从「检测到 N 个文件改动」变成「无 active change」
  但**仍 block** → 确认是流程门。

## 修复模板（四条通道，按侵入性升序）

| 通道 | 命令/操作 | 副作用 | 适用 |
|---|---|---|---|
| ① 开微修复批次（推荐） | `stdd batch open "<描述>"` | 在 `.fstdd/changes/_batch/` 建批次状态 | 小改动，符合 STDD 规约 |
| ② 放行开关 | `project.yaml` 加 `allow_bypass: true` | Guard 放行但仍打印提示；hook 带 `--strict` 时无效 | 运维期临时放行 |
| ③ 摘除 hook | `stdd guard disable`（`enable` 可逆） | 改写 `.claude/.codebuddy/settings.local.json` | 需长时间免打扰 |
| ④ 关强制门 | `project.yaml` 设 `enforce_stdd: false` | 违背项目强制门设计，**不推荐** | 不推荐 |

**兜底路径（不改任何配置）**：运维类落盘（记忆、日志、脚本）走 Bash / Python 通道完成，
并在回执与汇报中据实记录「Guard 拦截 + 采用路径 + 原因」，不静默绕过。

## 复现

在 `enforce_stdd` 生效且无 change/batch 的仓库中执行任意 Edit → 必 block；
`stdd batch open "x"` 后重试 → 放行。

## 证据

- 源码：`DKK_Fstdd/upstream/fstdd/cli/commands/guard.py:581-718`（判定链）、
  `:369-489`（`_assess_and_recommend`，无 flow 时 `allow` 恒 True）；
- 配置：`.fstdd/config.d/project.yaml` 无 `enforce_stdd`/`allow_bypass` 键；
  `.fstdd/config.d/guard.yaml:9-22` 阈值仅 small/medium/large 文案用；
- 实测：提交前 375 项改动 → block（文案含 files 计数）；提交后 0 项 → **仍 block**
  （文案变「无 active change」）。
