# FSTDD003 守护 SOP — scp/ssh 后台+await（消除 499 canceled）

> 配套变更：`2026-09-23-poll-daemon-499-fix`（FSTDD P1→P4）。
> 适用：每小时轮询守护自动化 `06ec2c4f` 的第 0/1/4 步所有 `scp`/`ssh` 调用。

## 1. 背景

`499 canceled`（nginx: Client Closed Request）不是服务端错误，而是**本守护前台
`scp`/`ssh` 在弱网时耗时 2–3 分钟，超过前台调用超时上限，被编排层自动转入后台，
网关把"被放弃的前台 HTTP 调用"记为 499**。两个十六进制串是网关 request-id / trace-id。

根因 = 前台长阻塞被自动后台化。修复 = 调用模式改为后台启动 + 显式 await。

## 2. 标准模式（每轮必做）

对**任何** `scp`/`ssh` 调用（列服务器 `收-`、拉取 notices、回执回写）：

1. **启动**：Bash 工具调用设 `run_in_background=true`。立即返回 `task_id`，
   前台 turn 不被传输阻塞。
2. **等待**：调用 `TaskOutput(task_id, block=true, timeout=600000)` 等待完成。
   10 分钟 await 上限 ≫ 历史最长 scp（~3min），不会误超时。
3. **判定**：**只以文件系统为准**——`scp` exit code（查后台任务输出）+ 目标目录
   `ls`/关键文件落地/md5。不以网关 499 状态码判成败。

## 3. Git Bash 路径约定（沿用前置修正）

- 密钥：`/d/id_ed25519`（Windows `D:/id_ed25519`）
- Host：`ubuntu@43.134.236.80`，加 `-o StrictHostKeyChecking=no`
- `fstdd` CLI：`$(cygpath -m ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd)` + venv python

## 4. 失败判定（防 499 噪声误判）

- 传输成功：`scp` exit=0 且目标文件存在/一致。
- 传输失败：`scp` exit≠0 或文件缺失 → 上报，按原对账/重试逻辑处理。
- **网关 499 噪声 ≠ 失败**：不触发重试风暴、不误判服务端故障；仅文件系统校验失败
  才升级为失败事件。

## 5. 反模式（禁止）

- ❌ 前台阻塞等待 scp/ssh（即 Bash 调用不设 `run_in_background=true` 且直接依赖其返回）。
- ❌ fire-and-forget：后台启动后不 `TaskOutput` 等待就继续（会丢失传输结果）。
- ❌ 以网关 499 状态码判定传输失败。

## 6. 审计

第 5 步自查每轮追加 `pull_mode: background+await`，使是否仍走前台可回溯。
