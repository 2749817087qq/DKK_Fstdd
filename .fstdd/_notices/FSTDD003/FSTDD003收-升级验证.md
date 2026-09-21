---
title: "FSTDD003收-升级验证（V3.0.5 → V3.0.6）"
from: K（FSTDD 经验库归口节点）
date: 2026-09-21
priority: 高
---
# FSTDD003收-升级验证（**V3.0.6 首次推广**）

## 一、本次升级内容（本 change 全部修复首次分发到 6 台机器）

| 项 | 内容 |
|---|---|
| S1 | guard 六处修复 + 审计活表迁移（消除 11 个静默吞错点） |
| S2S3 | `status` / `scan` 失败有声 |
| S4a | `validate` / `baseline` / `batch` 失败有声 |
| **S4b** | **`fstdd fix` 不可读文件计入跳过计数并点名**；**Gate 2 损坏 spec YAML 逐条告警且其余正常** |
| 附带 | guard 对 agent 运行时目录（`.workbuddy-ai` 等）豁免流程门禁 |
| **版本** | `stdd_version: 3.0.5 → **3.0.6**` |

## 二、升级步骤（五步，逐步给证据）

```bash
# 0) 记录升级前状态（可回滚依据）
cd <你的 stdd-repo 路径>
git rev-parse HEAD            # 记录旧 HEAD
grep stdd_version .fstdd/config.d/project.yaml   # 记录旧版本（应为 3.0.5）

# 1) 备份（只备份配置与本地未提交内容，不复制整个仓库）
cp .fstdd/config.d/project.yaml /tmp/project.yaml.bak-$(date +%Y%m%dT%H%M%S)

# 2) 取新版
git fetch server master && git merge --ff-only server/master   # 或 git pull server master
git rev-parse HEAD            # 记录新 HEAD（应为 91cc6ec（v3.0.6 发布提交））

# 3) 三项校验
grep stdd_version .fstdd/config.d/project.yaml   # 期望 3.0.6
python -c "import fstdd, sys; print('fstdd import ok')"
python bin/fstdd --version 2>/dev/null || python -m fstdd --version

# 4) 冒烟：跑本地最小测试集（不必全量，全量请后台跑）
cd upstream && python -m pytest tests/test_except_audit.py -q    # 期望 5 passed

# 5) 全量回归（可选，后台）
python -m pytest tests -q      # 记录 passed/failed 数字
```

## 三、回执判据（逐条给原始输出）

| # | 项 | 期望 |
|---|---|---|
| V1 | 旧 HEAD / 新 HEAD | 两个 commit 短号 |
| V2 | `stdd_version` | **3.0.6** |
| V3 | `pytest tests/test_except_audit.py -q` | **5 passed** |
| V4 | 全量回归（若跑） | `N passed / M failed` 原始行（**注明是否与本机基线一致**） |
| V5 | 回滚命令 | 一条可粘贴的 `git reset --hard <旧HEAD>`（供需要时使用） |

回执：`FSTDD003复-升级验证.md`。**卡点先回执说明，不要沉默、不要反复重试。**

## 四、注意

- **不要**改动 `.fstdd/changes/` 下的既有文件（那是 change 归档）；
- 若 `git merge --ff-only` 失败（本地有分叉），**停下回执**，把 `git status` 与 `git log --oneline -3` 贴给我；
- 升级期间你的回传轮询照常，不受影响。
