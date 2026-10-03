# 消除轮询守护 499 取消错误：scp/ssh 前台调用改为后台+await 模式

<!-- source_hash: 5e2a041025514409 -->
<!-- generated_at: 2026-10-03T14:55:50+00:00 -->
<!-- canonical: canonical/proposals/2026-09-23-poll-daemon-499-fix.yaml -->

## Why

FSTDD003 节点的每小时轮询守护（自动化 06ec2c4f）在第 0/1/4 步大量使用前台
`scp`/`ssh`：列服务器 `收-`、拉取 notices、回执 scp 回写。这些传输在弱网/大目录
时耗时 2–3 分钟，超过前台调用超时上限后被编排层自动转入后台，网关将"被放弃的
前台 HTTP 调用"记为 `499 canceled`（nginx: Client Closed Request）。

2026-09-17 轮次 scp 耗时 2m18s → 网关记录
`499 canceled (5410f1f68acf47c594f518be029c1fd4/07c1b217-0667-4acb-82fc-49a6c4302935)`；
两个十六进制串是网关 request-id / trace-id，不是服务端故障。scp 实际 exit=0、
文件已落地（已验证），但 499 噪声会掩盖真实失败、也违反"干净闭环"纪律。


## What Changes

- 修改守护自动化 prompt（06ec2c4f）：新增铁律"所有 scp/ssh 必须
run_in_background=true 启动并 TaskOutput 等待，禁止前台长阻塞"。
第 0/1/4 步的 scp/ssh 示例统一加注后台+await 约定。

- 第 5 步自查新增 `pull_mode` 记录行：每轮显式标注本次拉取/回写为
background+await，使"是否仍走前台"可审计、可回溯。

- 新增 `tools/fstdd003_daemon_499_sop.md`：后台+await 调用模式的可操作 SOP
（含 Git Bash 路径、超时上限、await 超时设置、失败判定以文件系统为准而非
网关状态码），供守护每轮参照。


### New Capabilities

- **daemon-scp-background-await**：守护内所有 scp/ssh 传输以后台任务启动并由 TaskOutput 等待完成，
前台 turn 不被长传输阻塞，从根上消除 499 canceled 噪声。


### Modified Capabilities

- **daemon-self-check**：第 5 步自查增加 pull_mode 审计字段，记录本轮传输是否走后台+await。


## Success Criteria

- [ ] GIVEN 守护执行拉取 WHEN scp 被调用 THEN 以 run_in_background=true 启动并由 TaskOutput 等待完成（前台 turn 不被长传输阻塞），本轮闭环无 499。
- [ ] 演示轮：本次 pull 实际以 background+await 执行，scp exit=0、文件落地、 前台 turn 完好（无自动后台化 499）。
- [ ] 负向对照：历史前台模式（2m18s）曾触发 499；新模式下同耗时传输不再产生 499。
- [ ] 收/复 对账与回执闭环功能零回归（缺口仍能自愈、最长延迟 ≤60min）。
- [ ] 第 5 步自查每轮记录 pull_mode: background+await，可审计。
- [ ] 新增 SOP `tools/fstdd003_daemon_499_sop.md` 存在且被 prompt 引用。
