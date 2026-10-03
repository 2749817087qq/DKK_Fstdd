# Test Plan — 2026-09-23-poll-daemon-499-fix

> 本变更为调用模式/自动化配置变更，无可编译单元代码；验收以"演示轮 + 配置审计"为
> GREEN 证据（RED = 历史前台模式曾触发 499）。TC-ID 与 `specs/agent/499-prevention.md`
> 场景一一对应。

| TC-ID | 场景 | 验收动作 | 期望结果 | 状态 |
|-------|------|----------|----------|------|
| TC-1 | 拉取走后台+await | 本轮 pull 用 `run_in_background=true` 启动 scp 并 `TaskOutput` 等待 | 前台 turn 不被长传输阻塞，本轮无 499 | GREEN（演示轮） |
| TC-2 | scp 实际成功 | 演示轮 scp 后查 `ls` 目标目录 + 关键文件落地 | `scp` exit=0，文件落地 | GREEN |
| TC-3 | 负向对照 | 对照历史前台模式（2m18s） | 历史曾触发 499；新模式同耗时不再产生 | 对照成立 |
| TC-4 | 对账/回执零回归 | 演示轮跑完第 0~4 步，比对收/复计数 | 缺口自愈、最长延迟 ≤60min，无重复/漏发 | GREEN |
| TC-5 | pull_mode 审计 | 第 5 步自查记录 `pull_mode: background+await` | 每轮可见、可回溯 | GREEN |
| TC-6 | SOP 存在且被引用 | 查 `tools/fstdd003_daemon_499_sop.md` 存在，且 prompt 引用之 | 文件存在、prompt 含后台+await 铁律 | GREEN |

## 失败判定约定（防 499 噪声误判）

- 传输成败**只以文件系统为准**：`scp` exit=0 + 目标文件存在/md5 一致。
- 网关若仍出现 499 噪声，**不代表服务端失败**，不触发重试/告警风暴；
  仅当文件系统校验失败（exit≠0 或文件缺失）才判失败并上报。
