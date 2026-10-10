<!-- fstdd-inbox
experience_id: EXP-FSTDD004-fstdd-canon-verify-scopes-change-dir
author: anonymous
received_at: 2026-10-09T16:44:40.947911+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-fstdd-canon-verify-scopes-change-dir
category: fstdd_workflow
severity: high
date: '2026-10-03'
node: FSTDD004
title: ① canon verify 报 canonical/proposals/<ch>.yaml not found，而文件明明在全局 canonical/
  下
occurrences: 1
pattern: FSTDD Phase 4 中 `fstdd canon verify <ch>` 报 canonical/proposals/<ch>.yaml
  not found，尽管该文件确实存在于项目级 .fstdd/canonical/proposals/。根因是 canon verify 解析的是「当前 change
  目录内的 canonical/」子目录（change 级双轨），而 fstdd archive 既不把项目级 canonical 回写到归档目录、也不自动置 deliver.status=completed。必须人工
  cp 三件套并新建 canonical/.canon-index.yaml，且索引里每条路径都要真实存在——既有归档里有 4 条索引指向 MISS 的文件（历史遗留），说明该索引无人校验。
root_cause: CLI 的 canon verify / _resolve_change_dir 面向 change 目录定位，而归档动作只搬changes/<ch>/
  的规格三件套，不含 canonical/；deliver 终态也不由 archive 写入。于是 DELIVER 的收尾动作（回写 canonical + 建索引
  + 置 completed）全部落在人工步骤上，且无一致性校验。
detection_trigger: ① canon verify 报 canonical/proposals/<ch>.yaml not found，而文件明明在全局
  canonical/ 下；② archive 完成后 .fstdd/changes/<ch>/ 消失，_resolve_change_dir 行为突变；③ 不知道
  canon verify 查的是change 级还是项目级双轨；④ 手工建归档级 canonical 后索引文件缺失。
fix_template: "# ✅ canon verify 查的是「change_dir 内的 canonical/」，不是项目级 .fstdd/canonical/\n\
  fstdd archive 2026-10-02-fcbar-event-aggregate   # 不会自动回写canonical\n\n# 人工补齐归档级三件套\
  \ + 索引\nA=.fstdd/archive/2026-10-02-fcbar-event-aggregate/canonical\nmkdir -p $A/proposals\
  \ $A/specs/code $A/specs/agent\ncp .fstdd/canonical/proposals/<ch>.yaml        \
  \        $A/proposals/\ncp .fstdd/canonical/specs/code/equity-calendar-forecast-bar.yaml\
  \  $A/specs/code/\ncp .fstdd/canonical/specs/code/equity-calendar-legend.yaml  \
  \      $A/specs/code/\ncp .fstdd/canonical/specs/agent/*.yaml                  \
  \          $A/specs/agent/\n\n# 索引 schema（version 2.9）：key 用 change-id + capability\
  \ 名，值必须真实存在\ncat > $A/.canon-index.yaml <<'YAML'\ndesigns: {}\nproposal<PATH>  <ch>:\
  \ proposals/<ch>.yaml\nspec<PATH>  agen<PATH>    <ch>: specs/agent/equity-calendar-forecast-bar.yaml\n\
  \    equity-calendar-forecast-bar: specs/agent/equity-calendar-forecast-bar.yaml\n\
  \    equity-calendar-legend: specs/agent/equity-calendar-legend.yaml\n  cod<PATH>
  \    <ch>: specs/code/equity-calendar-forecast-bar.yaml\n    equity-calendar-forecast-ba<PATH>
  \ specs/code/equity-calendar-forecast-bar.yaml\n    equity-calendar-legend: specs/code/equity-calendar-legend.yaml\n\
  version: '2.9'\nYAML\n\n# ✅ 验证：所有索引路径必须 isfile，MISS 一条都不能有\n# ✅ 归档后 phase advance\
  \ / canon generate 仍可用（_resolve_change_dir 指向 archive/）"
tags:
- fstdd
- canon
- archive
- dual-track
- canon-index
- deliver
language: bash


## 现场

`fstdd canon verify <ch>` 报 `canonical/proposals/<ch>.yaml not found`，而该文件确实躺在项目级 `.fstdd/canonical/proposals/` 下。

根因：canon verify 解析的是**当前 change 目录内的 `canonical/`**（change 级双轨），而 `fstdd archive` 既不把项目级 canonical 回写到归档目录、**也不自动置 `deliver.status=completed`**。

顺带发现既有归档里有 **4 条 canon-index 指向 MISS 的文件**（admin-users-residue-cleanup / extdep-tests-triage / ruoyi-customer-portal），说明该索引从未被校验过。

## 处置

人工 cp 三件套到 `archive/<ch>/canonical/{proposals,specs/code,specs/agent}`，新建 `canonical/.canon-index.yaml`（version 2.9，key 用 change-id + capability 名），追加全局 `.fstdd/.canon-index.yaml` 第 23 条，并脚本校验索引里**每条路径都 isfile**；手工补记 `deliver.status=completed`。复验 `canon verify` 2/2 通过。

## 教训

1. FSTDD 的 canonical 是「YAML 真值源 + Human View 带 source_hash 缓存」的双轨，且 canon verify 面向 change 目录定位。归档/终态/索引三件事都得人工补，补完必须用脚本验证索引路径全部可解析。

## 改善方法

- 根因：CLI 的 canon verify / _resolve_change_dir 面向 change 目录定位，而归档动作只搬changes/<ch>/ 的规格三件套，不含 canonical/；deliver 终态也不由 archive 写入。于是 DELIVER 的收尾动作（回写 canonical + 建索引 + 置 completed）全部落在人工步骤上，且无一致性校验。
- 检测信号：① canon verify 报 canonical/proposals/<ch>.yaml not found，而文件明明在全局 canonical/ 下；② archive 完成后 .fstdd/changes/<ch>/ 消失，_resolve_change_dir 行为突变；③ 不知道 canon verify 查的是change 级还是项目级双轨；④ 手工建归档级 canonical 后索引文件缺失。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0087 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
