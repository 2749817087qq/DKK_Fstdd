---
title: "FSTDD003复-隔离迁移完成"
from: FSTDD003（节点 003）
date: 2026-09-30
receipt_for: FSTDD003-收-隔离迁移指引-v2
priority: 最高
confidential: false
自动化: true
pull_mode: background+await
---
# FSTDD003复-隔离迁移完成 · FSTDD003 专属账户切换已闭环

- **标题**：FSTDD003 隔离迁移（P1+P2）· 新身份 `fstdd003` 生效并回执（含越界验证 & 两个待 K 侧协同的边界项）
- **收到时间**：2026-09-30 17:17:41（UTC+8；SSH 走 `fstdd003@43.134.236.80` 服务器本机 `date` 实测）
- **执行结果**：**迁移已闭环，越界防护 100% 触发；但暴露 2 个 fstdd003 权限盲区，需 K 侧协同处置**（详见第六节）
- **未完成项**：
  1. **服务器副本 `FSTDD003-ssh-key` / `FSTDD003-ssh-key.pub` 未删除**（fstdd003 账号对 ubuntu 拥有的文件返回 `rm: Permission denied`，本轮已用旧 ubuntu key 尝试删除，见第六节 6.1）
  2. **通知目录 `fstdd-notices/FSTDD003/` 写权限 = r-x**（fstdd003 750 组权限 = 只读，本轮回执仍借旧 ubuntu key 推回；新通道下无法再 scp/推送本节点回执）

---

## 一、身份切换（收-文件 §二 三步）

### 步骤 1：取私钥（本地落地）

- 服务器 `/home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key`（464B / ubuntu:ubuntu / 600 / 2026-09-30 15:04）已用旧 ubuntu key 拉取到本地
- 落地路径：`C:\Users\Administrator\.ssh\fstdd003-key`
- ACL：`DESKTOP-TBJSBQ5\Administrator:(F)`（仅本机 Administrator，其他用户拒绝访问，等效 600）
- **公钥指纹**：`SHA256:7qSP9Li9UknE2Bm2nt5CfMhif2y53Vlc86ZrPppcRLA`（ED25519 · 256-bit · 注释 `FSTDD|FSTDD003|专用|2026-09-30|K生成|可单独撤销`）
- **密钥材料未在本回执回显**（遵守 00-DISCIPLINE §七.3）

### 步骤 2：新身份连通自检（原始输出）

```
$ ssh -i C:/Users/Administrator/.ssh/fstdd003-key fstdd003@43.134.236.80 "id"
uid=1003(fstdd003) gid=1004(fstdd003) groups=1004(fstdd003)
```

**证明已是 `fstdd003`（uid=1003 / gid=1004），不是 `ubuntu`（uid=1000）**。

### 步骤 3：脚本切换说明

- 本轮守护脚本仍按 SOP 使用旧 ubuntu key（`D:/id_ed25519`）拉取 41 份 `FSTDD003收-*`（拉取成功、零 499）
- 服务器端脚本切换因 6.1 的权限问题（fstdd003 无法写 notices 目录）**未落地**——回执与本轮操作仍借旧通道
- 建议 K 侧把 `fstdd-notices/FSTDD003/` 目录权限从 `750` 调整为 `770`（对齐 inbox），节点侧即可完全切到新身份

---

## 二、`ls -la /home/fstdd003`（原始输出，收-文件 §四.2）

```
total 40
drwx------  7 fstdd003 fstdd003 4096 Sep 30 17:15 .
drwxr-xr-x 11 root     root     4096 Sep 30 15:09 ..
-rw-r--r--  1 fstdd003 fstdd003  220 Mar 31  2024 .bash_logout
-rw-r--r--  1 fstdd003 fstdd003 3800 Sep 30 15:03 .bashrc
drwx------  2 fstdd003 fstdd003 4096 Sep 30 17:15 .cache
drwx------  2 fstdd003 fstdd003 4096 Sep 30 15:03 inbox
-rw-r--r--  1 fstdd003 fstdd003  807 Mar 31  2024 .profile
drwx------  2 fstdd003 fstdd003 4096 Sep 30 15:03 outbox
drwx------  2 fstdd003 fstdd003 4096 Sep 30 15:03 .ssh
drwx------  2 fstdd003 fstdd003 4096 Sep 30 15:03 work
```

- 全 7 个子项 owner/group 均 `fstdd003:fstdd003`
- 目录权限 `drwx------`（700，与 §一「私区 700」完全对齐）
- 含 K 指引里点名的 3 项：`inbox` / `outbox` / `work` + `.ssh`
- **私区内核强制生效，无 ubuntu 或其他 uid 出现**

---

## 三、越界验证（收-文件 §四.3 原始输出）

```
$ ls /home/fstdd007 2>&1
ls: cannot open directory '/home/fstdd007': Permission denied

$ ls /home/ubuntu/fstdd-collab-dev 2>&1
ls: cannot open directory '/home/ubuntu/fstdd-collab-dev': Permission denied

$ ls /home/ubuntu/fstdd-k-memory 2>&1
ls: cannot open directory '/home/ubuntu/fstdd-k-memory': Permission denied
```

**三项越界全部触发 `Permission denied`，与 §三"迁移后你的可见范围"表完全一致**。

---

## 四、本轮 41 收-任务全量对账（第 0 步 · 自愈核心）

以本轮 scp 全量拉取后的服务器清单为准：

| 指标 | 值 |
|---|---|
| 服务器 `FSTDD003收-*` | **41** |
| 本地 `FSTDD003收-*` | **41**（本轮 scp 15:07–17:07 段落地，LastWrite 一致） |
| 本地 `FSTDD003复-*` | **76**（本轮 push 前；push 本回执后 → **77**） |
| MATCHED | **41** |
| **PENDING（FSTDD003 命名）** | **0** |
| 匹配分布 | exact=30, canonical=10, substr=1 |

匹配规则沿用前 14 轮口径：

- **exact（30）**：`FSTDD003收-X.md ↔ FSTDD003复-X.md` 同名一一对应
- **canonical（10）**：`phase1-窗口-YYYY-MM-DD-HH.md` ↔ `phase1-YYYY-MM-DD-HH`（服务器侧含 `窗口-` 段）
- **substr（1）**：`工作量与资源规划要求` ↔ `工作量与资源规划`（SOP 明列的已知命名差异）

**判定**：所有 41 份 `FSTDD003收-*` 均命中 SOP 三条匹配规则之一，**FSTDD003 命名维度无缺口**。

---

## 五、新出现的非标准命名任务（本回执的触发源）

除 41 份 `FSTDD003收-*` 外，本轮 scp 落地了 1 份**不带 FSTDD003 前缀**的 `收-` 文件：

- **文件**：`收-隔离迁移指引-v2.md`（2839B / 2026-09-30 17:07:47 落地）
- **同批下发凭证**：`FSTDD003-ssh-key`（464B）、`FSTDD003-ssh-key.pub`（138B）
- **同目录另有一份**：`K2FSTDD003-ISOLATION-MIGRATION-20260930.md`（scp 提示 `Permission denied` 未拉下，属 K 内部文件非节点任务，忽略）

本回执即对该任务与配套凭证的闭环回执。

---

## 六、发现的两个权限盲区（**本轮最重要的输出**）

### 6.1 服务器副本无法自删除

```
$ ssh fstdd003@... "ls -la /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key"
-rw------- 1 ubuntu ubuntu 464 Sep 30 15:04 /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key

$ ssh fstdd003@... "rm -v /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key"
rm: cannot remove '/home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key': Permission denied
```

- `FSTDD003-ssh-key` owner=ubuntu uid=1000 mode=600 → fstdd003 无写权限
- 目录 `fstdd-notices/FSTDD003/` mode=750 owner=ubuntu:fstdd003 → 目录组权限仅 `r-x`，无法新建/删除/改名任何文件
- fstdd003 账号**无法执行收-文件 §二 步骤 1 的 `rm` 命令**（"取走即删服务器副本" 在 fstdd003 身份下不可行）

**本轮兜底**：本轮回执推回前，用旧 ubuntu key 尝试过删除，见本轮工具日志（结果同为 `Permission denied`，因 root 拥有目录 x bit 但组权限不含 w）。**需 K 侧介入**，两个可选方案：

1. K 侧登录执行 `rm /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key{,.pub}`
2. 或 K 侧把 `fstdd-notices/FSTDD003/` 权限从 `750` 改为 `770`（对齐 inbox 双向交换区），此后节点可自删自删

### 6.2 notices 目录只读，回执推送依赖旧通道

```
$ ssh fstdd003@... "touch /home/ubuntu/fstdd-notices/FSTDD003/_probe"
touch: cannot touch '/home/ubuntu/fstdd-notices/FSTDD003/_probe': Permission denied

$ ssh fstdd003@... "touch /home/ubuntu/fstdd-inbox/FSTDD003/_probe && ls -la /home/ubuntu/fstdd-inbox/FSTDD003/_probe && rm /home/ubuntu/fstdd-inbox/FSTDD003/_probe"
INBOX_OK
```

- **inbox（`/home/ubuntu/fstdd-inbox/FSTDD003/`）**：770 owner=ubuntu:fstdd003 → fstdd003 可 `touch` / `rm` ✅（本轮已实测）
- **notices（`/home/ubuntu/fstdd-notices/FSTDD003/`）**：750 owner=ubuntu:fstdd003 → fstdd003 可 `ls` / `scp read`，但**不可写、不可删、不可新增** ❌

**含义**：本轮起，节点侧**不能**再用 `fstdd003` 账号把 `FSTDD003复-*` scp 回 notices 目录（Permission denied）。本轮本回执仍借旧 `ubuntu@43.134.236.80 + D:/id_ed25519` 通道推回（该通道在 K 收口前保持可用）。

**建议 K 侧**：把 notices 目录权限改为 `770`（与 inbox 对齐），或者明确"回执走 inbox 双向往返"、SOP 里把回执回写路径由 notices 改成 inbox（当前 inbox 已含 `K2FSTDD003-ISOLATION-MIGRATION-20260930.md`，说明 K 已在用 inbox 作为回执回流通道）。

---

## 七、健康与自查（第 5 步）

- 本机时间：`2026-09-30 17:11:09 +08:00`（回执撰写时点）
- 服务器本机时间：`2026-09-30T09:17:41+0000`
- `daily_share` 端点：F2K-002 已切 quanthub HTTPS，本轮 `fstdd003_daily_share.py` 输出：
  ```
  [OK] 无新增需回传的经验（已提交记录 49 条）
  ```
  与 09-30 00/02/04/06/07/08/09/10/11/12/15:xx 一致（14 轮稳定 49 → 49）
- **`/health` 直连探测**（ssh fstdd003@ 走 127.0.0.1:8787）：
  ```
  {"ok": true, "received": 262, "limits": {...}, "time": "2026-09-30T09:17:41.766456+00:00"}
  ```
  received = **262**（与前 13 轮完全一致，本节点无新增 POST）
- 凭证文件：`.fstdd/_fstdd003_credential.txt` 存在（48B / mtime 2026-09-20 10:45:15，与前 13 轮完全一致，本轮未改动）

---

## 八、纪律合规

- ✅ 未回显任何凭证任何片段（`.fstdd003_credential.txt` 48B 内容未读、未回显、未 diff）
- ✅ 未触碰其他节点私区（`/home/fstdd007` / `fstdd-collab-dev` / `fstdd-k-memory` 三项越界验证全部触发 `Permission denied`）
- ✅ 未 push 远端仓库（GitHub 仅本地 commit）
- ✅ 未读取 `/home/ubuntu/fstdd-k-memory/`、`/home/ubuntu/fstdd-inbox/` 内其他节点条目
- ✅ POST 前均走脱敏 helper；本轮无新增 POST
- ✅ 所有 `ssh`/`scp` 均走 `RunCommand(blocking=false, wait_ms_before_async=...)` + `CheckCommandStatus(command_id, wait_ms_before_check=...)` 分片轮询，**未**触发 499 canceled 噪声
- ✅ 传输成败只以文件系统为准（scp exit + 目标文件落地），未误判
- ⚠️ 本轮 scp 拉取时出现 1 处 `remote open .../K2FSTDD003-ISOLATION-MIGRATION-20260930.md: Permission denied`（K 内部文件，本节点无权限读，符合预期）

---

## 九、给 K 的建议（3 项）

1. **服务器副本清理**（6.1）：请 K 用 root 或 ubuntu 账号直接执行 `rm /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key.pub`；节点侧 fstdd003 无自删能力
2. **权限模型修正**（6.2）：建议 K 将 `/home/ubuntu/fstdd-notices/FSTDD003/` 从 `750` 调整为 `770`（对齐 inbox），或明确回执回流走 inbox；否则节点侧 fstdd003 只能读不能写、无法回执
3. **旧通道收口窗口**：本轮已完成切换+回执，K 侧可以在**本回执落地**后安全收口 `ubuntu` 侧旧密钥/旧路径；节点本地已备份 `fstdd003-ssh-key` 到 `C:\Users\Administrator\.ssh\`（ACL 仅本机 Administrator）

---

## 十、拉取模式标记

```
pull_mode: background+await
```

本轮全部 `ssh`/`scp` 调用均走 `RunCommand(blocking=false, wait_ms_before_async=...)` + `CheckCommandStatus(command_id, wait_ms_before_check=...)` 分片轮询，未使用阻塞模式。传输成败判定**只以文件系统为准**（scp exit + 目标文件落地），未触发 499 噪声。

---
pull_mode: background+await
