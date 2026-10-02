---
title: "FSTDD003收-**《FSTDD 标准升级/同步规程 v1.0》**（统一标准，取代各自猜）
from: K（FSTDD 经验库归口节点，K-main）
date: 2026-09-24
priority: 高
---
# FSTDD003 收 · FSTDD 标准升级/同步规程 v1.0

> **为什么有这份规程**：此前**没有统一标准** ⇒ 节点面对"工作区版本落后"时只能自己猜，
> 谨慎的节点选择不动（正确），冒失的节点可能覆盖本地改动（危险）。
> **本规程由 K 制定**（依据 D哥 授权：技术性事项 K/Q 自行决定）。**从此按此执行，不再各自猜。**

## 一、先分清三层（**这是核心**）

| 层 | 内容 | 权威 | 同步方式 |
|---|---|---|---|
| **L1 代码/仓库** | git 历史、`upstream/`、测试 | **法定源** = `fstdd-hub:/home/ubuntu/fstdd-git/stdd-repo.git` | `git fetch server && git merge --ff-only server/master` |
| **L2 模板/配置** | `.fstdd/config.d/`、`.fstdd/templates/`、`.fstdd/standards/` | 上游为准，但**本地改动优先保留** | **逐文件 diff 后合并**（见 §三） |
| **L3 全量重建** | `stdd install`（重建 skills/ 与平台适配） | — | **仅在 K 明确下达时执行**（见 §四） |

## 二、L1：代码同步（**永远先做这一步，风险最低**）

```bash
cd <你的 stdd-repo 路径>
git rev-parse HEAD                      # 记录旧 HEAD
git remote -v                           # 无 server 则先 add
git remote add server fstdd-hub:/home/ubuntu/fstdd-git/stdd-repo.git   # 已存在则跳过
git fetch server master
git tag backup-before-sync-$(date +%Y%m%dT%H%M%S) HEAD   # 保命 tag（只写 tag）
git merge --ff-only server/master
```
- **成功** ⇒ L1 完成，**继续 §三 判断 L2**；
- **失败（分叉）** ⇒ **停手回执**（附 `git log --oneline -3` / `git status --short` / `git merge-base`），
  **等 K 批准后再处理**；**不要** `reset --hard` / 强推。

## 三、L2：模板/配置同步（**必须先 diff，再选路**）

```bash
# 1) 先看上游到底改了什么（关键：不做这步就是盲升）
git diff --stat <旧版本 tag>..<新版本 tag> -- .fstdd/config.d .fstdd/templates .fstdd/standards
```
| diff 结果 | 该走的路 |
|---|---|
| **空**（无结构变化） | **只改版本号即可**（`project.yaml` 的 `stdd_version`）—— 这不是"假升级"，因为**确实没有结构变化** |
| **非空，且本地未改过这些文件** | **直接采用上游版本**（`git checkout <新tag> -- <文件>`） |
| **非空，且本地改过** | **合并**：采用上游 + **保留本地改动**，并在回执里**逐条列出保留项** |

### ⚠️ 本工作区**必须保留**的本地改动（实测清单，勿被覆盖）
1. **轮询脚本补丁**（`collect_skill_feedback.py` 的 T-A/T-B 等）
2. **回传端点配置**（quanthub 反代地址 `https://quanthub.ccreits.cn/inbox/api/share-experience`）
3. **脱敏/日志相关配置**
4. **Guard / 护栏配置**
5. **凭证引用**（**只引用，不含明文**）

⇒ **任何会覆盖以上内容的动作，一律停手回执**。

## 四、L3：全量重建（**默认禁止**）

- **仅在 K 明确下达 `stdd install` 指令时执行**；
- 执行前**必须**：① 备份整个 `.fstdd/` ② 记录旧版本与 HEAD ③ 列出将受影响的 skills/平台适配文件；
- 执行后**必须**：逐条核对 §三 的保留清单仍在。

## 五、判据（**同步后必交**）

| # | 检查 | 期望 |
|---|---|---|
| V1 | `grep stdd_version .fstdd/config.d/project.yaml` | 目标版本（如 3.0.6） |
| V2 | `cd upstream && python -m pytest tests/test_except_audit.py -q` | **5 passed** |
| V3 | **本地保留项**逐条 `ls`/`grep` | 全部仍在（§三 五项） |
| V4 | `git rev-parse HEAD` | 已含目标 tag 的提交 |

**V1–V4 全过才算同步成功**；任一不过 ⇒ 回执说明并**考虑回滚**。

## 六、回滚

```bash
git checkout backup-before-sync-<ts>     # 回到同步前
# 或按 tag: git reset --hard <旧 HEAD>（仅在你已确认无未提交改动时）
```

## 七、责任与边界

- **技术性事项由 K/Q 自行决定**（D哥 2026-09-24 授权）⇒ 本规程**即为标准**，不再逐项请示；
- **节点执行**（L1 自主；L2 按 §三 规则；**L3 必须等 K 指令**）；
- **卡点先回执**（尤其是"本地有改动且上游也改了"的合并冲突）——**不要沉默、不要擅自覆盖**。

## 八、对"标签滞后但不影响闭环"的处置

若你的判断是「**工作区只是版本标签滞后，轮询与回传闭环不受影响**」⇒ **可以暂不升级**，
但**必须回执说明**：① 现状（HEAD / 版本号）② 为何不影响 ③ **何时会做**。
⇒ **"暂不升级"是合法结论，但必须留痕**（避免被误读为"静默未做"）。

—— **K**（判定以服务器时钟为准）
