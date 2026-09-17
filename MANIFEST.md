# FSTDD003 迁移清单

> 迁移时间：2026-09-17 09:2x
> 来源：本次会话（2026-09-12 ~ 2026-09-17）在 WorkBuddy AI 实例与工作区产生的全部文件
> 目标：`D:\FSTDD003`（分布式任务根，task_id = FSTDD003）
> 方式：**复制**（源全部保留，见文末「未删除说明」）

## 1. 目录结构

```
D:\FSTDD003\
├─ TASK.md                    分布式任务卡（task_id=FSTDD003，含分布式执行约定）
├─ MANIFEST.md                本文件
├─ AGENTS.md                  FSTDD init 生成
├─ FSTDD_CONSTITUTION.md      FSTDD init 生成（强制流程契约）
├─ .fstdd\                    FSTDD 项目骨架（init 生成，54 个文件）
├─ .claude\                   Guard hook 配置（init 生成）
├─ docs\                      本会话问题报告（2）
├─ experiences\               导出/回传产物（29）
├─ tools\                     回传与校验工具（4，可独立运行）
└─ artifacts\
   ├─ skills\                 本会话新增/修改的 skill（10 个目录 / 12 文件）
   ├─ identity\               USER / IDENTITY / SOUL / MEMORY
   ├─ memory\                 工作区记忆日志（4）
   ├─ hardening-src\          外发防护全套 + 旧 STDD 备份
   ├─ install.sh.fixed        修复后的安装脚本
   └─ install.sh.patch        相对上游原版的完整补丁（71 行，含 4 项修复）
```

## 2. 文件映射

### docs/ — 问题报告

| 目标 | 来源 |
|---|---|
| `docs/INSTALL_RUN_ISSUES_2026-09-16.md` | `~/.workbuddy-ai/FSTDD/docs/`（首轮：4 项已修 + 5 项待修） |
| `docs/INSTALL_RUN_ISSUES_2026-09-17.md` | 同上（第二轮复测 + 第三轮 P10/P11 补充） |

### experiences/ — 经验条目（29 个文件）

| 目标 | 来源 | 说明 |
|---|---|---|
| `EXP-20260917-DOCS-1.md` | `~/.workbuddy-ai/FSTDD/experiences/` | 09-16 报告全文转写的经验条目 |
| `EXP-20260917-DOCS-2.md` | 同上 | 09-17 报告全文转写 |
| `EXP-20260917-INSTALL-4.md` | 同上 | 注释与实现矛盾 + 未 export + 实例 home 隔离 |
| `EXP-20260917-INSTALL-5.md` | 同上 | 4 项未合入 + `for`/`shift` 根因 |
| 其余 23 个 `EXP-*.md` | 同上 | 历史经验（09-15 A1–A6/B1–B4、09-16 INSTALL-1~3/RUN-1~2、哈希 ID） |
| `README.md` / `SUBMIT.md` / `回传指引-如何贡献经验.md` | 同上 | 导出索引与回传指引 |

### tools/ — 可独立运行的工具

| 目标 | 来源 | 用途 |
|---|---|---|
| `share_experience.py` | `~/.workbuddy-ai/FSTDD/tools/` | 脱敏导出 + 回传（无凭证降级到自建端点） |
| `inbox_server.py` | 同上 | 自建接收端点（服务端，本机不运行） |
| `install_workbuddy_skills.py` | 同上 | 升级后重新生成本机适配 skill |
| `verify_workbuddy_skills.py` | 同上 | 校验哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` |

### artifacts/

| 目标 | 来源 | 说明 |
|---|---|---|
| `skills/fstdd*` (7) | `~/.workbuddy-ai/skills/` | 本会话安装的 FSTDD skill 全套 |
| `skills/install-github-skill` | 同上 | 本会话创建（GitHub 手动安装 skill 流程） |
| `skills/stdd-hardening` | 同上 | 本会话创建（独立持久化加固规程，不被升级覆盖） |
| `skills/stdd-file-convention` | 同上 | 旧 STDD 文件约定（现转备用） |
| `identity/*` | `~/.workbuddy-ai/` | USER / IDENTITY / SOUL / MEMORY |
| `memory/2026-09-{12,14,16,17}.md` | 工作区 `.workbuddy-ai/memory/` | 会话记忆日志 |
| `hardening-src/` | `~/.workbuddy-ai/stdd-hardening/` | `apply.py`、`guard-block.md`、`push_issues.sh`、`pending-push/`、3 个旧 STDD 备份 |
| `install.sh.fixed` | `~/.workbuddy-ai/FSTDD/install.sh` | 含 4 项修复的安装脚本 |
| `install.sh.patch` | `git diff 846705e HEAD -- install.sh` | 上游原版 → 修复版完整补丁 |

## 3. install.sh 四项修复（见 `install.sh.patch`）

| # | 问题 | 修法 |
|---|---|---|
| P1 | `--py <path>` 解析失效，`line 57: --py: command not found` | `for arg in "$@"` + `shift` → 下标遍历 `_args=("$@")` |
| P2 | 未 `export FSTDD_OUT`，Python 退回自己默认值，装到错误目录 | 加 `export` |
| P3 | `/c/Users/...` 被 Windows Python 解析成 `\c\Users\...` | 调 `_winpath()`（`cygpath -m`） |
| P4 | echo 的目录与实际写入目录不一致 | echo 真实变量 `$FSTDD_OUT` |

## 4. 未删除说明

源位置**全部保留**，原因：

- `~/.workbuddy-ai/FSTDD` 是本机 FSTDD 安装源，`~/.workbuddy-ai/skills/*` 正在被本实例加载；删除会直接导致技能失效。
- `~/.workbuddy-ai/stdd-hardening/apply.py` 是网络层防护（`unblock` / `status`）的执行体；删除后无法恢复拦截状态。
- `~/.workbuddy-ai/{USER,IDENTITY,SOUL,MEMORY}.md` 是实例级档案，删除会丢失身份与偏好。

确认无碍后需要清理，逐个执行（勿用 `rm -rf` 通配）：

```
~/.workbuddy-ai/FSTDD/experiences/          # 导出产物，可清
~/.workbuddy-ai/stdd-hardening/_backup_*/   # 旧 STDD 备份，可清（约 9 MB）
```

## 5. 校验

```
# 在 D:\FSTDD003 下可独立回传（无凭证自动降级到自建端点）
python tools/share_experience.py --export --publish

# 校验外发哨兵是否仍在位
python tools/verify_workbuddy_skills.py
```
