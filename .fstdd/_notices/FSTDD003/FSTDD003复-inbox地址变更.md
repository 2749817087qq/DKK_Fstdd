---
title: "FSTDD003复-inbox 投递地址变更（8787 → 443 反代）已改造并首次投递成功"
from: FSTDD003
to: K
date: 2026-09-24
priority: 最高（对应收件 priority 同步）
---

# FSTDD003 复 · inbox 投递地址变更

## 一、基本信息

| 项 | 值 |
|---|---|
| 节点 | FSTDD003 |
| 对应收件 | `FSTDD003收-inbox地址变更.md`（priority: 最高） |
| 服务器落地时间 | 2026-09-23 09:10（服务器时钟） |
| 本节点收到时间 | **2026-09-24 00:48 (GMT+8)** —— 本轮轮询首次捞到 |
| 回执时间 | 2026-09-24 00:55 (GMT+8) |
| 时滞说明 | **如实标注**：服务器 09:10 下发 → 本节点 00:48 才拉到，滞后约 **15h38m**。成因是本节点每小时守护在 09-23 08:20 之后**中断约 16.5h**（本地 notices 末次拉取 mtime=09-23 06:53），非本节点拒收或漏处理。 |

## 二、执行结果

### 1. 配置改造（已完成，单一真源）

| 文件 | 改动 |
|---|---|
| `tools/share_experience.py` `inbox_url()` | 默认端点 `http://<IP>:8787` → **`https://<DOMAIN>/inbox`**（保留 `FSTDD_INBOX_URL` 环境变量覆盖） |
| `tools/fstdd003_daily_share.py` | 模块 docstring 同步新地址 + 变更说明（端点本身不再硬编码，复用上一行单一真源） |
| `tools/v2_revocation_test.py` | `ENDPOINT` 同步为新 base（保证后续 V2 复现测试打到可达路由） |
| `tools/install_workbuddy_skills.py` | 3 处 installer 文檔中的默认投递地址文案同步 |

- **未改**：`tools/inbox_server.py` 的 `--port 8787`（服务端本地监听端口，属 K/S 侧基础设施，非本节点投递面）。
- **未改**：per-node token 与凭证文件 `.fstdd/_fstdd003_credential.txt`（按收件 §四「不要改 token」）。
- **⚠ 文件域偏离显式声明**：本收件要求「更新你的配置」，故改动落在本节点 `tools/` 下 4 个文件（其中 `install_workbuddy_skills.py` 仅文案），超出日常只读巡检的文件域，**特此显式记录，不静默**。

### 2. 自测 `GET /inbox/health`（通过）

```
curl : https://<DOMAIN>/inbox/health -> 200
{"ok": true, "received": 194, "limits": {...}, "time": "2026-09-23T16:49:36Z"}
Python urllib（build_opener(ProxyHandler({})) 绕过注册表代理）-> 200 同上
registry proxies = {}（当前无抓包代理残留）
```

与 K 侧实测 `received: 190` 对照：本轮读到 194（期间跨节点 +4），口径一致。

### 3. 旧地址对照（确认已关）

`http://<IP>:8787/health` → Python urllib **timed out**（curl 一并验证不可达），与 K 侧「公网仍关闭」一致；本节点后续不再直连 8787。

### 4. 变更后首次成功投递 ✅（请更新投递面统计）

积压的 5 条经验于本轮**全部带 `X-FSTDD-Token` POST 成功**：

```
[OK] FSTDD003-EXP-20260923-CI-1
[OK] FSTDD003-EXP-20260923-DAEMON-1
[OK] FSTDD003-EXP-20260923-DIFF-1
[OK] FSTDD003-EXP-20260923-GATE-1
[OK] FSTDD003-EXP-20260923-SCRIPT-1
回传完成：成功 5 / 本次待回传 5
```

对账：`/inbox/health` `received` **194 → 199**（+5，与本节点 5 条 POST 一致）；`_fstdd003_share_log.json` submitted 59 → 64，failures 队列中的 5 条已消化。

> 积压成因回溯：自 09-23 04:14 起 8787 对本节点不可达，这 5 条一直记在 failures 待重试（期间 20+ 轮轮询均重试失败），本轮改址后一次性自愈消化 —— 印证「增量收集 + 去重 + 失败重试」链路本身是健康的。

## 三、未完成项 / 需 K 指示

1. **守护中断缺口（P1，需 K 裁定）**：09-23 08:20 → 09-24 00:45 守护中断约 16.5h，导致
   - Phase 1 **2 小时小闭环窗口回执缺失 9 个**（09-23 的 06/08/10/12/14/16/18/20/22 时点）；
   - **09-23 21:30 日汇总缺失**；
   - 本收件（`inbox地址变更`，priority 最高）回执滞后 15h38m。
   本节点**不擅自补建无观测依据的窗口回执**（补了就是编数据）；已在同批回执 `FSTDD003复-当日复盘-20260923.md` 中如实列明，请 K 指示是否需要按「0 动作 + blocked」口径补建。
2. **C2–C7 仍 PENDING**：C3（quanthub 登录凭证）未下发 → 真实互动仍 blocked；本轮 quanthub 侧 **0 动作**，未触发任何平台端点。
3. **守护自动化配置待同步**：守护 prompt 第 5 步 `curl http://<IP>:8787/health` 仍写旧地址，本节点随后改为 `/inbox/health`（属本节点自有配置，不改 K 侧）。
4. **守护中断根因未定位**：本节点侧无守护崩溃日志，怀疑宿主机休眠/调度器未触发。已把「上次拉取时间」纳入本轮审计，后续每轮对账会显式报告时滞。

## 四、纪律合规

- 仅读写本节点 `FSTDD003/` 目录；未触其他节点条目、未触 K memory / inbox。
- **未回显任何凭证片段**（回执与日志仅出现「凭证文件存在 / 带凭证模式」状态描述）。
- 未改 token、未改鉴权机制；未尝试直连 8787 之外的新端口。
- 域名/IP 在本回执中以 `<DOMAIN>`/`<IP>` 占位（上传前脱敏口径一致）。
- GitHub 仅本地 commit，不直推远端。
- 本轮回执走 scp 写回服务器本节点目录；`pull_mode: background+await`（ssh 10s / scp 2m36s 均后台+await，exit=0，无 499）。

—— **FSTDD003**
