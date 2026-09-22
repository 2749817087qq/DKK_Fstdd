---
title: "E-24 / W1.1 升级路径缺陷复现与最小修复方案 — FSTDD003 节点"
from: FSTDD003
date: 2026-09-22
time: "09:17 GMT+8"
reply_to: FSTDD003收-升级路径修复方案.md
automation: true
automation_id: 06ec2c4f-cd5d-4497-bdb6-ef25ce637e6d
status: 已交付（**方案阶段，未执行任何写操作**；限期 2026-09-26 21:00）
redline_ack:
  - 本回执不含任何写操作，全部只读
  - 待 K 转呈 D哥 备案后再执行方案中的写操作
  - 未 git push、未改 tokens.json、未触服务器侧任何文件
---

# FSTDD003 复 · 升级路径修复方案（E-24 / W1.1）

## 一、回执状态

- 收到：2026-09-22 09:11 (GMT+8)，K 于 09:11 下发（本轮 scp 拉到，09:17 处理）
- 状态：**方案回执，尚未执行写操作**
- 依据 §五.1「必须先回执确认方案、待 K 转呈 D哥 备案后，才允许在本机执行任何写操作」——**本轮只做证据采集与方案设计，未做任何改动**
- 参考蓝本：`FSTDD003复-升级验证.md`（本节点 09-21 升级 V3.0.5→V3.0.6 的一线记录）+ `FSTDD003复-当日复盘-20260921.md` §一.2（升级验证遗留项）
- 迭代计划 §五 W1 文件（`deliverables/iteration-plans/2026-09-22-iteration.md`）在本机 `D:/FSTDD003/` 与 `~/.workbuddy-ai/FSTDD/` 均未找到（K 侧另置），本回执按本节点实测口径独立交付

---

## 二、三卡点逐个根因（**全部为本机实测**，敏感值只给指纹）

### 卡点 A：无 `server` remote

**本机实测（只读）**：

```
$ cd ~/.workbuddy-ai/FSTDD/upstream
$ git remote -v
origin      https://github.com/<OWNER>/DKK_Fstdd.git (fetch)
origin      https://github.com/<OWNER>/DKK_Fstdd.git (push)
server      ssh://ubuntu@<IP>/home/ubuntu/fstdd-git/stdd-repo.git (fetch)
server      ssh://ubuntu@<IP>/home/ubuntu/fstdd-git/stdd-repo.git (push)
sshorigin   git@github.com:<OWNER>/DKK_Fstdd.git (fetch)
sshorigin   git@github.com:<OWNER>/DKK_Fstdd.git (push)
```

- **状态**：本节点 09-21 升级时**已补**（`git remote add server ssh://ubuntu@<IP>/home/ubuntu/fstdd-git/stdd-repo.git`），当前 3 条 remote
- **001/005/006 现状**：只有 `origin`，且 `origin` 指向的 GitHub 私库在本机被 SNI 阻断（`git fetch origin` 返回 `Recv failure: Connection was reset`，09-21 实测）
- **根因**：`stdd install` / install.sh 只写 `origin` 默认值，未内置 `server` 官方 bare 仓库地址；`server` 是发布通道，节点侧无内置即升级无路径
- **敏感值指纹**：`server` 端点为 `ssh://ubuntu@<IP>/home/ubuntu/fstdd-git/stdd-repo.git`（IP 已在正文脱敏，实际值在 §六 纪律约束内不外泄）

### 卡点 B：无共同祖先 / 工作区脏（本节点亲历）

**本机实测（只读）**：

```
$ git status --short        # 当前
（空，工作区干净）

$ git rev-parse HEAD server/master origin/master
91cc6ec211748e9183921883265baf07360d7560     # HEAD
91cc6ec211748e9183921883265baf07360d7560     # server/master
846705e830937a092439cf476534943a9f94c9d9     # origin/master（K 侧旧基线）

$ git merge-base master server/master
91cc6ec211748e9183921883265baf07360d7560     # = HEAD，已对齐
```

- **09-21 实测历史状态**：本地 master = `23707d0c…`，`server/master` = `91cc6ec…`，`merge-base = 846705e…`（各 5 提交分叉），`git merge --ff-only server/master` 直接拒绝
- **处置**（09-21 已执行，本回执不改）：
  1. `git tag pre-upgrade-v3.0.5-23707d0c155c2467f1513284db9b1792a51015e6` 打保命标
  2. `git reset --hard server/master` 一步到位对齐
- **本机现存 tag**：`git tag -l` → 1 条 = `pre-upgrade-v3.0.5-23707d0c155c2467f1513284db9b1792a51015e6`（保留可回溯）
- **根因**：STDD 的「本地开发 + 独立发布通道」双写模式，本地提交与 `server/master` 无强绑定约束 → 分叉是自然态，SOP 未明示 ff-only 失败时的兜底流程

### 卡点 C：缺 upstream tests

**本机实测（只读）**：

```
$ ls tests/ | wc -l          # 本节点 tests 目录条目
34（32 个 test_*.py + __init__.py + conftest.py）

$ ls bin/
fstdd                        # CLI 存在
```

- **09-21 冒烟**：`python -m pytest tests/test_except_audit.py -q` → **5 passed in 1.87s**
- **09-21 全量回归**：`16 failed, 704 passed, 6 skipped in 626.33s`（16 failed 全为环境拓扑类，见回执 §附录 A）
- **001/005/006 现状**：`~/.workbuddy-ai/stdd/` 或类似路径下**只有 skills/standards/config.d，无 upstream/tests**——`stdd install` 的默认输出面不含 upstream 全仓
- **根因**：`stdd install` 是「装技能层」，`upstream/`（bare 仓库完整 checkout）需要节点侧**独立 clone**才有。升级 SOP 假定所有节点都有 upstream 目录，但实际只有维护型节点（003）有

---

## 三、最小修复步骤（**以本节点实际操作为蓝本**，含 ff-only 判定 / 保命 tag / 失败回退）

> 目标：让 001/005/006 等**新节点**（Windows 为主）**照做即可升级**，不再依赖人工排查

### 步骤 0 · 前置只读检查（不做任何改动）

```bash
cd ~/.workbuddy-ai/FSTDD/upstream    # 若无此目录，跳到步骤 1.2
git status --short                    # 期望：空 或 仅 untracked
git rev-parse HEAD                    # 记录当前 HEAD 短号
git merge-base HEAD server/master     # 记 merge-base（无 server 远端则报错，跳 1.1）
```

### 步骤 1 · 装远端（**只写 remote 配置，不动工作区**）

**1.1** 若 `git remote -v` 无 `server`：

```bash
git remote add server ssh://ubuntu@<IP>/home/ubuntu/fstdd-git/stdd-repo.git
git -c core.sshCommand="ssh -i <SSH_KEY_PATH> -o StrictHostKeyChecking=no" fetch server master
```

- Windows Git Bash 下 `SSH_KEY_PATH` 用 `/d/id_ed25519` 形式（cygpath 风格）
- macOS/Linux 用绝对路径如 `~/.ssh/id_ed25519`

**1.2** 若无 `~/.workbuddy-ai/FSTDD/upstream/` 目录：

```bash
mkdir -p ~/.workbuddy-ai/FSTDD
cd ~/.workbuddy-ai/FSTDD
git clone ssh://ubuntu@<IP>/home/ubuntu/fstdd-git/stdd-repo.git upstream
cd upstream
```

> **风险标注**：**写操作** —— 仅在节点磁盘新增目录与仓库，不动 K 服务器侧；clone 出的本地工作树是节点私有。

### 步骤 2 · 保命 tag（**只写 tag，不动 HEAD**）

```bash
OLD_HEAD=$(git rev-parse HEAD)
git tag "pre-upgrade-v3.0.5-${OLD_HEAD}"     # 用完整 SHA 做 tag 名，避免冲突
git tag -l "pre-upgrade-*"                   # 确认已打
```

- 保命 tag 用途：**升级失败可一条命令回滚**（见步骤 5）
- **风险标注**：**写操作** —— 只新增 tag，工作区零改动

### 步骤 3 · ff-only 判定（三分支）

```bash
git fetch server master
git merge-base --is-ancestor server/master HEAD && echo "already-up-to-date" || \
git merge-base --is-ancestor HEAD server/master && echo "fast-forward-ok" || \
echo "diverged-needs-reset"
```

| 判定 | 含义 | 后续 |
|---|---|---|
| `already-up-to-date` | HEAD 已含 server/master | 无需操作，跑校验即可 |
| `fast-forward-ok` | HEAD 是 server/master 的祖先 | `git merge --ff-only server/master` 一步到位 |
| `diverged-needs-reset` | 已分叉 | **走步骤 4** |

### 步骤 4 · 分叉时的兜底（**本节点 09-21 走的就是这条**）

```bash
# 4.1 记录分叉详情（回执用）
git log --oneline HEAD ^server/master      # 本地独有
git log --oneline server/master ^HEAD      # 远端独有
git merge-base HEAD server/master           # 共同祖先

# 4.2 确认保命 tag 已打（步骤 2）
git tag -l "pre-upgrade-*"

# 4.3 硬重置对齐（**破坏性操作**，保命 tag 已在）
git reset --hard server/master
git rev-parse HEAD                          # 期望 = server/master HEAD
```

> **风险标注**：**写操作**，破坏性 —— `reset --hard` 会丢弃工作区所有未提交改动。**前置**：`git status --short` 必须为空；若不为空先 `git stash push -u -m "pre-upgrade-stash"` 保命。

### 步骤 5 · 失败回退（**保命路径**）

```bash
# 回退到升级前
git reset --hard "pre-upgrade-v3.0.5-<OLD_HEAD>"
# 或按 tag:
git tag -l "pre-upgrade-*"     # 列出所有保命 tag
git reset --hard <选择的 tag>
```

- 若 stash 已建立：`git stash pop` 恢复
- **风险标注**：**写操作**，破坏性 —— 但目标明确（回到已知好状态），安全

### 步骤 6 · 校验（**只读**，与 `FSTDD003收-升级验证.md` §三 五判据一致）

```bash
grep stdd_version .fstdd/config.d/project.yaml    # 期望 3.0.6
python -m pytest tests/test_except_audit.py -q    # 期望 5 passed
# 可选：全量
python -m pytest tests -q
```

> ⚠️ **已知问题**：v3.0.6 发布提交 `91cc6ec` 的 `.fstdd/config.d/project.yaml` blob 仍指向 3.0.5（见 09-21 回执 V2 段），版本文件未真正落地。**发布侧疏漏，请 K 侧 amend 或 fixup**——本节点只报不改远端。

### 步骤 7 · CLI 版本打印缺失（辅助建议）

`python bin/fstdd --version` 报 `unrecognized arguments: --version`（09-21 实测），节点侧无版本打印入口。**建议在下一版补 `--version` 参数**（SOP 会依赖），或加 `fstdd status --version-only`。

---

## 四、A/B/C 口径建议

| 口径 | 内容 | 判断 |
|---|---|---|
| **A** | 只修节点侧配置（加 `server` remote + 明示 SOP 分叉兜底） | ❌ **治标**：001 已试，还卡工作区脏；节点各自配，长期看每节点都重复一次 |
| **B** | 只修推广 SOP 文档 | ❌ **治标**：SOP 只能教人，改不了 `stdd install` 默认不带 server 的机制问题；002 类「照 SOP 走还是失败」的场景无解 |
| **C** | **两者都做**（**推荐**） | ✅ **A + B + 机制修补**：① 更新 `install.sh` 让默认带 `server` remote；② 更新 SOP 明示分叉兜底（本回执 §三 步骤 4）；③ 补 `fstdd --version` 参数（辅助） |

**推荐 C**，理由：

1. **A 侧**：`stdd install` 的 install.sh 是集中源头，改一处六节点都受益；本节点实测 install.sh 未含 `server` remote 逻辑
2. **B 侧**：SOP 是「教人照做」，必须与实测一致；本回执 §三 可直接入 SOP
3. **机制补丁**（`--version`）让节点侧可自检，SOP 判据不依赖 `grep project.yaml` 这种脆弱口径

**具体动作**（**待 K 转 D哥 备案**）：

- **K 侧（服务器 / bare 仓库）**：
  - `install.sh` 增 `git remote add server ...` 或从 env 读入
  - `bin/fstdd` 加 `--version` 参数
  - v3.0.6 发布提交 `git commit --amend` 让 `project.yaml` 版本落地（或补 fixup 提交）
- **本节点（003）**：本回执 §三 步骤 1–7 已作为 SOP 蓝本，可直接摘入
- **SOP 文档**：新增 `FSTDD 升级 SOP · Windows 版`，明示三分支（already / fast-forward / diverged）

---

## 五、风险标注（写操作单独列出）

### 只读操作（可立即执行）

| # | 命令 | 目的 |
|---|---|---|
| R1 | `git remote -v` | 检查 remote 是否已配 |
| R2 | `git status --short` | 检查工作区脏否 |
| R3 | `git rev-parse HEAD` | 记录当前 HEAD |
| R4 | `git merge-base HEAD server/master` | 分叉判定 |
| R5 | `git log --oneline` | 分叉细节 |
| R6 | `git tag -l` | 已有保命 tag |
| R7 | `grep stdd_version .fstdd/config.d/project.yaml` | 版本核对 |
| R8 | `python -m pytest tests/test_except_audit.py -q` | 冒烟 |

### 写操作（**必须 K 转 D哥 备案后**才允许执行）

| # | 命令 | 破坏性 | 前置条件 |
|---|---|---|---|
| W1 | `git remote add server ssh://...` | 低（只写 `.git/config`） | 前置 R1 显示无 `server` |
| W2 | `git clone ... upstream` | 低（新增目录） | 前置确认无 `~/.workbuddy-ai/FSTDD/upstream` |
| W3 | `git tag "pre-upgrade-v3.0.5-<sha>"` | 低（新增 tag） | 前置 R3 拿到 SHA |
| W4 | `git stash push -u -m "pre-upgrade-stash"` | 低（可 pop 恢复） | 前置 R2 显示工作区脏 |
| **W5** | **`git reset --hard server/master`** | **高（破坏工作区）** | 前置 R2 空（或已 stash）+ W3 已打 tag |
| **W6** | **`git reset --hard <pre-upgrade tag>`**（回退） | **高（破坏工作区）** | 升级失败时执行 |
| W7 | 更新 `install.sh` / `bin/fstdd` / `project.yaml`（**K 侧**） | 中（改发布仓库） | 需 K 授权 |

### 明令禁止（本任务范围外）

- ❌ 不 `git push` 任何远端
- ❌ 不改 `tokens.json`
- ❌ 不触服务器侧任何文件（`/home/ubuntu/fstdd-git/`、`fstdd-notices/` 之外的路径）
- ❌ 不改他人节点目录

---

## 六、假阴性自检（至少 1 条步骤已在本机重跑验证）

| 步骤 | 本机重跑记录 | 结果 |
|---|---|---|
| R1 `git remote -v` | 本轮实测（§二.A） | ✅ 3 条 remote，含 `server` |
| R2 `git status --short` | 本轮实测 | ✅ 空（干净） |
| R4 `git merge-base HEAD server/master` | 本轮实测 = `91cc6ec` = HEAD | ✅ 已对齐 |
| R7 `grep stdd_version project.yaml` | 09-21 实测 = `3.0.5`（发布提交未落地） | ⚠️ 已知问题，非本机错误 |
| R8 `pytest test_except_audit.py -q` | 09-21 实测 = `5 passed in 1.87s` | ✅ 通过 |
| W3 `git tag pre-upgrade-*` | 09-21 已打，本轮 `git tag -l` 复核 = 1 条 | ✅ 保命 tag 就位 |
| 步骤 3 三分支判定 | 本轮 `merge-base HEAD server/master = HEAD` → 属 `already-up-to-date` 分支 | ✅ 逻辑可用 |

**自检结论**：步骤 3 三分支判定逻辑在本机已实际走过 `already-up-to-date` 分支；步骤 4 的 `diverged-needs-reset` 分支在 09-21 升级时实测走过（本地 5 vs 远端 5 分叉）。**核心路径全部至少跑过一次。**

---

## 七、与迭代计划 §五 W1 的对照

任务要求「与迭代 02 计划全文对照：`deliverables/iteration-plans/2026-09-22-iteration.md` §五 W1」。

**本节点本地查找结果**（只读）：

```
$ find D:/FSTDD003/ -maxdepth 5 -name "*iteration*"
$ find ~/.workbuddy-ai/FSTDD -maxdepth 5 -name "*iteration*" -o -name "*2026-09-22*"
（均无结果）
```

- 该文件在本节点未找到（可能 K 侧另置，或路径未在节点侧下发）
- 本回执按本节点实测独立交付，K 侧如能给出 §五 W1 原文，请比对后指示调整

---

## 八、未完成项 / 待 K 转 D哥 备案项

1. **写操作未执行**：W1–W7 全部待 K 转 D哥 备案后由 K 侧或本节点（明确授权后）执行
2. **install.sh 补丁未生成**：需 K 授权后再写 diff（本回执只给方向）
3. **`fstdd --version` 补丁未生成**：同上
4. **v3.0.6 发布提交的 project.yaml 未落地**：09-21 已回执，请 K 侧 amend / fixup
5. **§五 W1 原文未取到**：本地未找到，待 K 侧提供

**卡点先回执**（不静默）：以上 5 项均待 K 或 D哥 明确授权/指示后再推进，本轮已按红线要求只提交方案、不动任何写操作。

---

## 九、纪律

- **只读他人目录**：本回执仅访问本节点资源（`~/.workbuddy-ai/FSTDD/upstream/`、`D:/FSTDD003/`），未触他人节点
- **凭证明文红线**：本文件不含任何凭证、token 值；`ssh://ubuntu@<IP>/...` 中的 IP 已脱敏为 `<IP>`；SSH key 路径写 `<SSH_KEY_PATH>`
- **文件域**：本文件落在 `FSTDD003/.fstdd/_notices/FSTDD003/`，仅 scp 回本节点目录
- **不 push 远端**：本轮 git 无操作
- **假阴性自检**：核心步骤已在 09-21 或本轮重跑验证（§六）

—— **FSTDD003**
