---
name: stdd-hardening
description: "STDD 本地加固：禁止 stdd-deliver 把项目经验自动发到外部站点。升级 STDD、重装技能、初始化新项目、或怀疑防线被覆盖时使用；含一键施加/检查/网络层兜底脚本。"
agent_created: true
version: 1.1.0
---

# STDD 数据外发加固

## 威胁：两条外发路径（已读源码确认）

`stdd-deliver` Step 2.8 → `stdd experience share` → `_cmd_share_single()`：

| 路径 | 触发条件 | 行为 | 泄露内容 |
|---|---|---|---|
| **A. gh CLI**（优先） | 本机装了 `gh` 且已登录 | `gh repo clone leonai42/stdd-experiences` → 写 `pending/<eid>.md` → `git add/commit` → **`git push`** | 经验正文 + **GitHub 账号身份**（commit author = 本机 git user.name/email）。比路径 B 更严重 |
| **B. server API**（fallback） | 无 `gh` 时 | `POST https://hzddyy.com/stdd/api/share-experience` | `content`（经验正文）+ `author`（`git config user.name`，本机为 `CCREITs`） |

本机当前：`gh` **未安装** → 走路径 B。一旦装了 gh 并登录，路径 A 会自动启用。

## 三层防线

| 层 | 防的是什么 | 命令 |
|---|---|---|
| 1. skill 层 | AI 自动执行 Step 2.8 | `apply.py`（默认） |
| 2. 网络层 | 人肉/脚本误调用 CLI 上传 | `apply.py block` |
| 3. 项目层 | 项目内 `.stdd/skills/deliver.md` **+ `.stdd/platforms/*/skills/stdd-deliver.md` 安装源模板** | `apply.py --project <path>` |

```bash
PY="C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe"
A="C:/Users/Administrator/.workbuddy-ai/stdd-hardening/apply.py"

"$PY" "$A" --check                 # 只检查（缺失 exit 1）
"$PY" "$A"                         # 施加 skill 层（幂等）
"$PY" "$A" block                   # 网络层兜底（三手段）
"$PY" "$A" unblock                 # 撤销网络层
"$PY" "$A" status                  # 三层状态总览
"$PY" "$A" --project <项目路径>     # 加固项目级副本（含 3 个平台安装源模板）
```

> **为什么项目层要管 `platforms/`**（v1.1.1 扩展）：`.stdd/platforms/{claude-code,trae,workbuddy}/skills/stdd-deliver.md`
> 是 `stdd init` 写入的 **v2.2 陈旧快照**（含已废弃的 slice/verify 阶段）。经读 CLI 源码核实：
> `stdd install` 读的是**源仓库** `stdd_source/.stdd/skills/`（`install.py:142/169`），
> **并不读项目内 `platforms/`** —— 所以这里加固**不是**因为 install 会写回，
> 而是**纵深防御**：该目录位于项目树内、文件名与真实技能同名，人或 AI 可能误当权威指引照它执行，
> 而其中的 Step 2.8 未加固。
> 实测：2026-09-15 在 `D:\项目\数据文件` 一次性补了 4 处缺失（1 处 skill 副本 + 3 处 platforms）。

## 网络层三个手段（block 会全部施加）

1. **防火墙出站规则**（主手段）：阻止到 `hzddyy.com` 解析 IP 的出站 TCP。
   → hosts 常被安全软件回滚，防火墙才是可靠的。
2. **hosts 屏蔽**：`127.0.0.1 hzddyy.com`（尽力而为，写入后脚本会回读校验）。
3. **git pushInsteadOf**：把 `leonai42/stdd-experiences` 的 push 重定向到 `127.0.0.1:1` → push 必失败，**堵死路径 A**。

## 何时必须重新施加

1. 跑过 `stdd-upgrade`（GitHub raw 覆盖技能文件）
2. 重新 `stdd install workbuddy`（读源仓库 `.stdd/skills/`，会覆盖平台技能目录里的副本）
3. `git pull` 更新了 `~/.workbuddy-ai/stdd/`
4. **新项目 `stdd init` 之后**（项目副本是上游原版）→ 立即跑 `apply.py --project <新项目路径>`
5. 装了 `gh` CLI 之后（路径 A 从不可用变可用）
6. 重装/升级安全软件之后（hosts、防火墙规则可能被清）
7. 拉取/覆盖了项目 `.stdd/` 快照（如从 git 恢复了旧版本、或 clone 到新机器）

## ⚠️ `stdd-upgrade` Step 7 的已知覆盖缺口

`stdd-upgrade` Step 7 只跑**全局** `apply.py --check`（不带 `--project`），
而它的 **Step 4 会从 GitHub raw 覆盖项目 `.stdd/skills/deliver.md`**
→ **项目级加固会被抹掉且无人察觉**。

**跑完 `stdd-upgrade` 后必须补跑**（对每个受影响的项目）：

```bash
PY="C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe"
"$PY" C:/Users/Administrator/.workbuddy-ai/stdd-hardening/apply.py \
      --check --project "D:/项目/数据文件"
# 报 MISS → 去掉 --check 施加
```

**完整的三处检查清单**（升级后逐项过）：

| # | 路径 | 谁覆盖它 |
|---|---|---|
| 1 | `~/.workbuddy-ai/skills/stdd-deliver/SKILL.md` | 技能层升级 |
| 2 | `~/.workbuddy-ai/stdd/.stdd/skills/deliver.md` | `git pull` 仓库副本 |
| 3 | `<项目>/.stdd/skills/deliver.md` | `stdd-upgrade` Step 4 |
| 4 | `<项目>/.stdd/platforms/*/skills/stdd-deliver.md`（3 处） | `stdd install <platform>` |

## 已知坑

- **hosts 会被安全软件回滚**：脚本报 FIXED 后文件里可能已无内容。因此 `status` 用 **DNS 实测**（`hzddyy.com` 是否解析到 127.*）而非只看文件；防火墙规则是主手段。
- **脚本曾谎报成功**：早期版本写入 hosts 后不回读，报 FIXED 但实际没生效。现版本写入后强制回读校验。
- **防火墙按 IP 拦**：`hzddyy.com` 换 IP 后需重跑 `block`（脚本每次会重新解析并带上已知 IP `124.222.113.129`）。

## 已核实安全（不要误伤）

| 项 | 判定 |
|---|---|
| `stdd knowledge merge` | 只读 GET GitHub raw，**入站**，照常执行 |
| `stdd-upgrade` 下载 | 入站，安全（但会覆盖本加固） |
| 配置层 `auto_share` 开关 | **不存在**。`.stdd/config.d/experience.yaml` 无此开关 → 只能在 skill / 网络层拦 |

## 现状核查（2026-09-14）

**从未发生外发**：全盘无本地 `EXP-*.md`；唯一项目级 `.stdd/` 仅含 `projects.yaml`，无 `experiences/`；`share` 从未被调用。存在的是风险，不是泄露。

---

## ⚠️ 2026-09-16 状态变更：旧 STDD 已卸载，本技能转为「备用」

旧 STDD 已备份到 `~/.workbuddy-ai/stdd-hardening/_backup_stdd_20260916/`，
现役为 **FSTDD**（`~/.workbuddy-ai/FSTDD/`，装在 `~/.workbuddy-ai/skills/fstdd-*`）。

- **外发防护已由 FSTDD 自带**：哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 打在 `fstdd-deliver` 里，
  升级后有其自带校验脚本复查。本技能不再需要主动执行。
- **网络层兜底仍然有效且建议保留**：防火墙 `STDD-Block-Experience-Upload`
  拦的是上游外发端点 `hzddyy.com`，对 FSTDD 的**自建回传**（目标 `2749817087qq/Fstdd-experiences`，
  走 github.com）**不适用**——那是你们自己的仓库，且需显式 `--export` + 强制脱敏。
- **本技能保留用途**：万一回到上游 STDD、或需要复现当时的加固方式。
- FSTDD 仓库 `.fstdd/experiences/` 下有 15 个 `EXP-20260915-*.md`，是潜在外发数据源，留意。

**关键认知纠正**：skills 目录有两个，`~/.workbuddy-ai/skills` 和 `~/.workbuddy/skills`
（内核 `codebuddy.js` 里 `.workbuddy-ai` 出现 0 次）。本文件里旧的路径假设已过时。
