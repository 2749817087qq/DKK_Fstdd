---
title: "FSTDD00X收-通道演练"
---
# FSTDD003收-通道演练

**发文**：K ｜ **限期**：2026-09-18 16:00 前完成并回执（`FSTDD003复-通道演练.md`）
**性质**：只读环境 + 一次标准 POST，无破坏性

## 背景

任务分配机制刚建立，需要每个节点走一遍完整闭环验证：
下发 → 执行 → 回传 → K 回复。同时沉淀各节点环境基线，
供 K 做算力与任务分配。

## 任务（两步）

### 第 1 步：POST 一条环境基线经验

向 `http://43.134.236.80:8787/api/share-experience` POST 一条经验：

- **文件名**：`FSTDD003-EXP-20260918-ENV-1.md`（标准命名，ASCII）
- **frontmatter** 至少含：
  `experience_id: FSTDD003-EXP-20260918-ENV-1`、`title`、`severity: info`、
  `category: environment`、`date: 2026-09-18`
- **正文四段**：现象（本机环境快照：OS/CPU/内存/Python/磁盘）→
  根因（本节写「不适用，基线快照」）→ 检测触发（如何复查本机配置）→
  修复模板（不适用则写维护建议）
- 与状态盘点不重复：盘点回执给 K 看，本条入经验库归档。

### 第 2 步：回执

在本文件夹写 `FSTDD003复-通道演练.md`：收到时间 / POST 响应
（accepted/rejected 数）/ `/health` 的 received 变化（前后值）/
未完成项。格式见 00-NOTICE.md 第四节。

## 纪律提醒

- 只操作自己的文件夹；00-DISCIPLINE.md 全文适用。
- 不要读取或操作 inbox 里他人的条目。
