---
title: "00-COLLAB 协作开发 SOP"
---
# 00-COLLAB 协作开发 SOP（K 发布，2026-09-18）

FSTDD 进入多节点协作开发：K 按 Slice 拆分任务下发，节点在统一基线上
开发自测，交付 patch + 测试证据，K 终审、合并、推送。

## 角色

| 角色 | 职责 |
|---|---|
| K（归口） | 拆任务、定基线、终审、全量回归、合并推送、汇总 test-report |
| 开发节点 | 在自己文件域内 TDD 实现，交付 patch + 测试输出 + 回执 |
| 评审节点 | 交叉评审他人 patch（只读），产出评审回执 |

## 工作流

1. K 下发 `FSTDD00X收-协作开发-*`（含基线地址、文件域白名单、验收标准）。
2. 节点 scp 拉基线包 → 解压 → 在独立 scratch 目录工作（不动自己的正式安装）。
3. **TDD**：先写失败测试（RED）→ 实现（GREEN）→ 自测通过。
4. 交付到**自己文件夹**三件套：
   - `<编号>-slice<N>.patch`（基线之上的 git diff，含测试文件）
   - `<编号>-slice<N>-tests.txt`（相关 pytest 完整输出）
   - `<编号>复-<主题>.md`（回执：改动清单/设计取舍/自测结果/已知风险）
5. K：`git apply --check` → 应用到自己分支 → 全量回归 → 合并推送
   → K-reply 通知结果；不合并也会在回执里说明原因。
6. 评审节点按 checklist 评审交付物，评审回执同样放自己文件夹。

## 硬规矩

- **文件域白名单外一律不许改**；文件域冲突的任务 K 会串行排期，不并行。
- 不跑 `gate` / `canon` 等会改 `.fstdd` 状态的命令；不改版本号；
  不向任何 remote push；不碰他人文件夹（00-DISCIPLINE 全文适用）。
- patch 必须基于指定基线 commit；含测试文件；测试文件名
  `test_<域>_voice.py` 之类，放 upstream/tests/。
- 开发中发现的**本任务外问题**只写进回执「观察项」，不顺手修
  （防越权，D哥 2026-09-18 规矩）。

## 本轮分工（detection-silence-fixes 收尾）

| 节点 | 角色 | Slice |
|---|---|---|
| FSTDD003 | 开发 | S2+S3（status.py：DFX-005/006 + COV-001..003） |
| FSTDD002 | 开发 | S4a（validate/baseline/batch：DFX-007/008/009） |
| FSTDD004 | 开发 | S4b（fix/gate：DFX-010/011） |
| FSTDD001 | 评审 | 003 交付物 |
| FSTDD006 | 评审 | 002/004 交付物 |
| FSTDD005 | 暂不派 | 与 K 同机写域冲突 + 自有 active change 收尾中 |

后续轮换，人人有份；005 的写任务等其 change 归档后补。
