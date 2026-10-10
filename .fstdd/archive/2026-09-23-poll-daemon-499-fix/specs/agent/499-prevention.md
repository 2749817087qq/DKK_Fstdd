# Agent Behavior Spec — daemon-scp-background-await

<!-- behavior specs: GIVEN/WHEN/THEN, 机器与人工双读 -->

## Scenario S1 — 拉取 notices 走后台+await（TC-1）

- GIVEN 守护在第 1 步需要把服务器 notices 拉到本地
- WHEN 调用 `scp` 拉取
- THEN 必须以 `run_in_background=true` 启动该 scp，立即取得 `task_id`
- AND 随后必须以 `TaskOutput(task_id, block=true, timeout=600000)` 等待完成
- AND **不得**以前台方式阻塞等待 scp 返回

## Scenario S2 — 回执 scp 回写走后台+await（TC-1）

- GIVEN 守护在第 4 步需要把 `复-*.md` 推回服务器
- WHEN 调用 `scp` 回写
- THEN 同样以 `run_in_background=true` 启动并 `TaskOutput` 等待
- AND 回写完成后以文件系统校验服务器侧文件存在（如需）

## Scenario S3 — 列服务器 `收-` 也走后台+await（TC-1）

- GIVEN 守护在第 0 步需要列服务器侧 `收-` 清单
- WHEN 调用 `ssh ... "ls ... | grep '^FSTDD003收-'"`
- THEN 以 `run_in_background=true` 启动并 `TaskOutput` 等待取回 stdout

## Scenario S4 — 成功后以文件系统判定（TC-2）

- GIVEN scp 后台任务已完成
- WHEN 判定传输是否成功
- THEN 只看 `scp` exit code 与目标目录文件落地，**不**以网关 499 状态码判成败

## Scenario S5 — 历史负向对照（TC-3）

- GIVEN 历史前台模式 scp 耗时 2m18s 曾触发网关 499
- WHEN 同耗时传输改为后台+await
- THEN 前台 turn 不被拖垮，网关不再记 499

## Scenario S6 — 每轮可审计（TC-5）

- GIVEN 第 5 步自查
- WHEN 记录本轮传输方式
- THEN 必须写出 `pull_mode: background+await`，使是否仍走前台可回溯
