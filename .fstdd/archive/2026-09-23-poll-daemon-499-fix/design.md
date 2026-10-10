# Design — 2026-09-23-poll-daemon-499-fix

## 根因（已验证）

`499 canceled` = nginx "Client Closed Request"。本守护的前台 `scp`/`ssh` 在弱网时
耗时 2–3 分钟，超过前台调用超时上限 → 编排层（网关）将其所在的前台 turn **自动转入
后台** → 网关把"已被放弃的前台 HTTP 调用"记为 499。两个十六进制串是
request-id / trace-id，与 K 侧服务无关。

证据：2026-09-17 轮次 scp 2m18s → 网关记 499；但 `scp` 实际 exit=0、文件落地，
属纯噪声。scp 本身没失败，失败的是"前台 turn 被长传输拖垮"。

## 修复策略

把"前台长阻塞"改成"后台启动 + 显式 await"：

1. 守护调用 `scp`/`ssh` 时，Bash 工具调用 **`run_in_background=true`**，立即拿到
   `task_id`（前台 turn 立刻返回，不再被传输阻塞）。
2. 随后调用 `TaskOutput(task_id, block=true, timeout=600000)` 等待传输完成。
   10 分钟 await 上限 >> 历史最长 scp（~3min），不会误超时。
3. 继续前以**文件系统**校验落地（目标目录 `ls` + 关键文件存在/md5），**不以网关
   状态码判定成败**——即便出现 499 噪声也不误判为服务端故障。

## 改动落点

- **C1**：守护自动化 prompt（06ec2c4f）新增铁律与第 0/1/4 步示例加注。
  patch 文本见 `specs/code/daemon-prompt-patch.md`。
- **C2**：第 5 步自查追加 `pull_mode: background+await` 一行。
- **C3**：新增 `tools/fstdd003_daemon_499_sop.md`（可操作 SOP）。

## 为什么不改其它

- 调度周期（HOURLY）、对账/自愈/紧急快通道逻辑均正常，不在本次范围。
- 共享池 :8787 可达性属 K 侧基础设施（本轮实测 :22 通 / :8787 不通），与 499 根因
  无关，单独记录、不混入此变更。
- 凭证落盘/回传链路正常，不改。

## 验收（RED→GREEN）

本变更为**调用模式 / 自动化配置变更**，无单元可测代码；GREEN 证明 = **本轮演示**：
以 background+await 执行拉取，scp exit=0、文件落地、前台 turn 完好（无 499），
且收/复 对账与回执闭环零回归。详见 `test-plan.md` TC-1~TC-6。

## 偏离记录

无。严格按提案实施（见 `design-adjustments.md`）。
