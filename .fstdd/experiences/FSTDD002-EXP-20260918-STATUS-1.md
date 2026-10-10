---
title: FSTDD002 节点状态回传：CLI 版本与通道配置
experience_id: FSTDD002-EXP-20260918-STATUS-1
category: status
severity: info
occurrences: 1
exported_at: 2026-09-18
sanitized: true
source: FSTDD002 节点按 FSTDD005 通知要求汇报
---

## 现象

FSTDD005 通知要求各节点当日内完成首次最小回传，并汇报节点状态。

## 节点状态

- FSTDD CLI 版本：FSTDD V3.0.5（config.d/project.yaml stdd_version=3.0.5，适配层仓库 DKK_Fstdd）；项目根无 bin/stdd CLI，以 .fstdd/ skills+config 方式驱动。
- 最近 change：无进行中 change（.fstdd/changes/ 为空）；主规范 specs/spec.md 存在。
- 通道：GitHub（github.com:443）本环境实测不可达；有效通道为 POST http://43.134.236.80:8787/api/share-experience（无需凭证，批量上限 50）。
- 本机工具：无标准 tools/share_experience.py，等效工具为 submit_experiences.py（零依赖）。
- 历史：09-18 上午已以旧命名 EXP-20260918-01~05 回传 5 条（inbox received 68→73），按新命名规范无法归属本节点，故本次以新命名正式回传。

## 复现

N/A（状态汇报）

## 证据

inbox /health received=77（2026-09-18T02:35Z）。

## 处理

以 FSTDD002-EXP-* 新命名标准完成首次回传；后续经验一律新命名并保留本机原件。

## 性质

节点状态快照。
