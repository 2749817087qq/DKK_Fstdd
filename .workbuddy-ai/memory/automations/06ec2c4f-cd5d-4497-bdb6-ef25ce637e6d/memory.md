# FSTDD003 每小时轮询守护 · 自动化记忆

> automation_id: 06ec2c4f-cd5d-4497-bdb6-ef25ce637e6d
> 目的：每小时闭环一次「收/复对账」，确保 K 下发的每个 `FSTDD003收-*.md` 都有 `FSTDD003复-*.md` 回执。

## 执行历史（最新在前）

### 2026-09-25 23:54 (cron)
- 第 0 步（初对账）：服务器 32 份 `收-`、本地 51 份 `复-`；逐一匹配 → **32/32 全部已回执，0 缺口**。
  - 精确同名匹配：28 条。
  - 命名差异/前后缀匹配：4 条（与前四轮一致）— `工作量与资源规划要求↔工作量与资源规划`、`助001接入与SOP收尾↔SOP收尾`、`FSTDD标准升级同步规程v1-回执催办↔FSTDD标准升级同步规程v1`、`phase1-窗口-2026-09-24-14↔phase1-2026-09-24-14`。
- 第 1 步（拉取）：`ssh` 列目录后台+await（10s），`scp` 后台+await 完成（5m04s），`pull_mode: background+await`；本地时间戳刷新至 23:50–23:53，服务器无新增 `收-` 文件（32 与拉取后本地完全一致）。
- 第 0 步（二次对账）：拉取后 32/51 计数不变，仍 32/32 全回执。
- 第 2 步（紧急快通道）：扫描到 25 份带 `priority` 的 `收-`（其中 4 份 `最高`：`inbox地址变更`、`phase1-更正8080不可用`、`Phase1执行方式增补-任务卡驱动`、`凭证安装硬时限`），全部已有对应 `复-` → 0 待办触发项。
- 第 3 步（执行）：0 新任务 → 0 执行动作（share 脚本、凭证安装、状态盘点均未触发）。
- 第 4 步（回写）：0 新回执 → 无 scp 回写。
- 第 5 步（自查）：`https://quanthub.ccreits.cn/inbox/health` → HTTP 200 `{"ok":true,"received":234,...}`（与 22:23 轮持平，本守护零 POST，符合预期）。
- 其他非收/复件：`K-reply-*.md`、`00-COLLAB.md` / `00-DISCIPLINE.md` 无新指令。
- 结果：**本轮零缺口，零回写，零 POST**。

### 2026-09-25 22:23 (cron)
- 第 0 步（初对账）：服务器 32 份 `收-`、本地 51 份 `复-`；逐一匹配 → **32/32 全部已回执，0 缺口**。
  - 精确同名匹配：28 条。
  - 命名差异/前后缀匹配：4 条（与前两轮一致）— `工作量与资源规划要求↔工作量与资源规划`、`助001接入与SOP收尾↔SOP收尾`、`FSTDD标准升级同步规程v1-回执催办↔FSTDD标准升级同步规程v1`、`phase1-窗口-2026-09-24-14↔phase1-2026-09-24-14`。
- 第 1 步（拉取）：`ssh` 列目录后台+await（6s），`scp` 后台+await 完成（4m12s），`pull_mode: background+await`；本地时间戳刷新至 22:25–22:28，服务器无新增 `收-` 文件（32 与拉取后本地完全一致）。
- 第 0 步（二次对账）：拉取后 32/51 计数不变，仍 32/32 全回执。
- 第 2 步（紧急快通道）：0 待办 → 无 `priority: 最高` / `confidential: true` 触发项。
- 第 3 步（执行）：0 新任务 → 0 执行动作（share 脚本、凭证安装、状态盘点均未触发）。
- 第 4 步（回写）：0 新回执 → 无 scp 回写。
- 第 5 步（自查）：`https://quanthub.ccreits.cn/inbox/health` → HTTP 200 `{"ok":true,"received":234,...}`（与 21:17 轮持平，本守护零 POST，符合预期）。
- 其他非收/复件：`K-reply-003c/d/e.md` + `K-reply-FSTDD003-催办-2026-09-24.md` 仍为 K 对历史回执的信息性回复，按纪律「只读不执行」忽略；`00-COLLAB.md` / `00-DISCIPLINE.md` 无新指令。
- 结果：**本轮零缺口，零回写，零 POST**。

### 2026-09-25 21:17 (cron)
- 第 0 步（初对账）：本地已有 51 份 `复-`、服务器上 32 份 `收-`；逐一匹配 → **32/32 全部已回执，0 缺口**。
  - 精确同名匹配：28 条。
  - 命名差异/前后缀匹配：4 条（同 20:08 轮）— `工作量与资源规划要求↔工作量与资源规划`、`助001接入与SOP收尾↔SOP收尾`、`FSTDD标准升级同步规程v1-回执催办↔FSTDD标准升级同步规程v1`、`phase1-窗口-2026-09-24-14↔phase1-2026-09-24-14`。
- 第 1 步（拉取）：`scp` 后台+await 完成，耗时 4m13s，`pull_mode: background+await`；本地时间戳统一刷新至 21:21，服务器无新增 `收-` 文件。
- 第 0 步（二次对账）：拉取后 32/51 计数不变，仍 32/32 全回执。
- 第 2 步（紧急快通道）：无 `priority: 最高` / `confidential: true` 的新任务。
- 第 3 步（执行）：本轮 0 个新任务 → 0 执行动作（share 脚本、凭证安装、状态盘点均未触发）。
- 第 4 步（回写）：本轮无新回执产生 → 无 scp 回写。
- 第 5 步（自查）：`https://quanthub.ccreits.cn/inbox/health` → `{"ok":true,"received":234,...}`（较上轮 233 增加 1，为本节点外的其他节点回传所致；本守护本轮未回传经验，符合预期）。
- 结果：**本轮零缺口，零回写，零 POST**。

### 2026-09-25 20:08 (cron)
- 第 0 步（初对账）：本地已有 51 份 `复-`、服务器上 32 份 `收-`；逐一匹配 → **32/32 全部已回执，0 缺口**。
  - 精确同名匹配：28 条。
  - 命名差异/前后缀匹配：4 条 —
    - `收-工作量与资源规划要求` ↔ `复-工作量与资源规划`（已知差异，规则 2c）
    - `收-助001接入与SOP收尾` ↔ `复-SOP收尾`（`SOP收尾` 为 `助001接入与SOP收尾` 子串，规则 2b）
    - `收-FSTDD标准升级同步规程v1-回执催办` ↔ `复-FSTDD标准升级同步规程v1`（规则 2b：Y 是 X 前缀）
    - `收-phase1-窗口-2026-09-24-14` ↔ `复-phase1-2026-09-24-14`（`复-` 文件 `reply_to` frontmatter 明确回指本 `收-`，命名迭代后差异）
- 第 1 步（拉取）：`scp` 后台+await 完成，耗时 3m47s，`pull_mode: background+await`；本地时间戳更新至 20:14，服务器无新增文件。
- 第 0 步（二次对账）：拉取后无变化，仍 32/32 全回执。
- 第 2 步（紧急快通道）：无 `priority: 最高` / `confidential: true` 的新任务。
- 第 3 步（执行）：本轮 0 个新任务 → 0 执行动作（share 脚本、凭证安装、状态盘点均未触发）。
- 第 4 步（回写）：本轮无新回执产生 → 无 scp 回写。
- 第 5 步（自查）：`https://quanthub.ccreits.cn/inbox/health` → `{"ok":true,"received":233,...}`（本轮未回传经验，计数稳定，符合预期）。
- 备注：
  - 服务器 `K-reply-003c/d/e.md` + `K-reply-FSTDD003-催办-2026-09-24.md` 系 K 对我方历史回执的信息性回复，不属 `FSTDD003收-` 任务，按纪律「只读不执行」忽略。
  - 8787 端口已于 09-25 03:02 关闭，share 脚本已切到 `https://quanthub.ccreits.cn/inbox/*`；本守护健康检查也走新域名。
- 结果：**本轮零缺口，零回写，零 POST**。

### 历史轮次（早期摘要）
- 2026-09-24 至 2026-09-25 各轮：持续闭环 phase1 窗口卡回执（09-24-02/04/06/08/10/12/14）、交付物入仓、口径更正、账号规模扩展预告、协作 S2S3 验收、撤回令处置、凭证验证补充、澄清问询、状态盘点、经验回传要求、自动化率提升、通道演练、编写 per-node 接入 SOP、FSTDD 标准升级同步规程 v1（含催办）、SOP 收尾、seed 口径申报等；`复-` 覆盖全部历史 `收-`。
- 2026-09-23 起：Phase 1 转入「任务卡驱动 + 2 小时小闭环」，窗口卡要求每 15 分钟内回执，本守护在每轮对账时若发现窗口卡未回则自动补交。
- 2026-09-22 起：凭证下发类改为一次性下发 + 落地写入 `_fstdd003_credential.txt`（权限 600、gitignored）+ V1/V2 校验（带凭证 200、不带 401）+ 回执绝不回显凭证片段 + 完成后删除本地/服务端下发文件。

## 关键坑位与约定

- **499 SOP**：所有 `scp`/`ssh` 必须 `run_in_background=true` + `TaskOutput(block=true, timeout=600000)`；传输成败只以文件系统为准（`scp` exit=0 + 文件落地），不因网关 499 状态误判为服务端故障。SOP 全文：`tools/fstdd003_daemon_499_sop.md`。
- **fstdd CLI 前置**：裸 `python3` 缺 yaml，须用 venv python `C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`；Git Bash 下用 `$(cygpath -m ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd)` 转换路径，否则 `~` 展开成 `/c/Users` 会被 Windows Python 解析失败。
- **匹配规则**：`收-<X>` ↔ `复-<Y>` 匹配条件为 (a) 精确同名 / (b) 互为前后缀或子串 / (c) 去尾部修饰词（要求/要求说明/说明/补发/硬时限/通知/事宜/的）后核心相同。**只从 `收-` 找 `复-`，绝不反向**——`复-` 无对应 `收-` 是正常态。
- **纪律**：只读他人目录；POST 前脱敏（路径/IP/域名/凭证 → `<PATH>/<IP>/<DOMAIN>/<TOKEN>`）；文件名仅 ASCII；GitHub 仅本地 commit，不直推远端。
- **禁止发送**：`EXP-20260915/16/17-*` 等试运行数据（已 `_legacy_trial/` 归档）。

## 端点与地址

- Share：`https://quanthub.ccreits.cn/inbox/api/share-experience`（POST，带 `X-FSTDD-Token` 头）
- Health：`https://quanthub.ccreits.cn/inbox/health`（GET）
- 服务器：`ubuntu@43.134.236.80`，identity `/d/id_ed25519`，加 `-o StrictHostKeyChecking=no`
- 服务器 notices 目录：`/home/ubuntu/fstdd-notices/FSTDD003/`
- 本地 notices 目录：`D:/FSTDD003/.fstdd/_notices/FSTDD003/`
- 每日经验脚本：`D:/FSTDD003/tools/fstdd003_daily_share.py`
