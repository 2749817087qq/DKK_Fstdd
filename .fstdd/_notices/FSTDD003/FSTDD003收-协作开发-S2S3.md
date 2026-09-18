---
title: "FSTDD003收-协作开发-S2S3"
---
# FSTDD003收-协作开发-S2S3：status 家族失败有声（S2）+ scan 覆盖（S3）

**发文**：K ｜ **限期**：2026-09-20 13:00 前交付并回执
**性质**：写任务（scratch 目录内）——正式动手前**先回本任务回执确认已读**，
回执即开工信号；遇基线/环境阻断也回执说明。

## 基线准备

```bash
scp ubuntu@43.134.236.80:/home/ubuntu/fstdd-k-baseline/stdd-baseline-5e3f9a3.tar.gz .
tar xzf stdd-baseline-5e3f9a3.tar.gz     # 解压出 stdd-repo/
cd stdd-repo && git log --oneline -1     # 必须显示 5e3f9a3
```

在 stdd-repo 目录内直接开发（它自带 .git，diff 基于此基线）。
规格来源：`.fstdd/changes/2026-09-18-detection-silence-fixes/` 下
canonical/specs/code/ 的 YAML 与 test-plan.md，动手前必读。

## 验收标准（对应需求 DV-005/006（S2）、COV-001..003（S3））

| TC | 层级 | 断言 |
|---|---|---|
| DFX-005 | CLI | `fstdd status`：唯一 change 活跃停滞 8 天 → 输出含僵尸清单 + change 名 +「当前活跃」标注 |
| DFX-006 | 单元 | `_show_zombie_changes` 遇不可解析 last_mod → stderr 警告；该 change 进「无法判定」提示 |
| COV-001 | 单元 | change YAML 含不可解析内容 → `scan_change_values` 返回含 `category=scan_error` 项 |
| COV-002 | 单元 | proposal.md 不可读 → `scan_human_view_headers` 返回 scan_error 项 |
| COV-003 | 单元 | `full_scan` 汇总 report 含 `scan_errors` 键；既有 naive_count 断言不回归 |

## 文件域白名单（只许改这些 + 新增测试文件）

- upstream/fstdd/cli/commands/status.py
- 新增 upstream/tests/test_status_voice.py（及必要的测试夹具文件）

## 要求

1. **TDD**：先写测试跑红，再实现跑绿；测试放 upstream/tests/。
2. 设计约束：scan_errors 单列、不污染 naive_count（设计决策 D5）；僵尸清单对「当前活跃」change 需保留豁免但加标注（F-1 修正）；统一失败形态=stderr 警告+安全默认值（D1）。
3. 自测：新测试 + 既有相关测试全绿（`python -m pytest tests -k <关键词> -q`）。
4. 交付三件套到**自己文件夹**：
   - `FSTDD003-sliceS2S3.patch`（基线之上的 git diff，勿 commit/push）
   - `FSTDD003-sliceS2S3-tests.txt`（pytest 完整输出）
   - `FSTDD003复-协作开发-S2S3.md`（改动清单/设计取舍/自测结果/已知风险）
5. patch 生成：`git add -A && git diff --cached > <patch名>` 后
   `git reset` 撤销暂存（保持工作区即可）。

## 纪律

文件域外不改；不跑 gate/canon；不碰他人文件夹；任务外问题写回执「观察项」。
