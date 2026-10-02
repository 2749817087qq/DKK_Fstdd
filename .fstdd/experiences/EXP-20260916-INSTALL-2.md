<!-- fstdd-inbox
experience_id: EXP-20260916-INSTALL-2
author: anonymous
received_at: 2026-09-26T08:30:08.000115+00:00
remote_addr: 172.18.0.8
node_id: FSTDD001
-->

---
exported_at: 2026-09-26
sanitized: true
---
<!-- fstdd-inbox
experience_id: EXP-20260916-INSTALL-2
author: (anonymous)
received_at: 2026-09-18T02:08:00.740314+00:00
remote_addr: <IP>
-->

---
experience_id: EXP-20260916-INSTALL-2
category: tooling
severity: medium
occurrences: 1
exported_at: 2026-09-18
sanitized: true
lifecycle_state: deposited
---
## 现象

跑 `verify_workbuddy_skills.py` 之后，FSTDD 项目注册表 `~/.fstdd/projects.yaml` 里多出 6 条 `stdd_smoke_<随机串>` 条目，指向已删除的临时目录。

## 根因

verify 脚本的 CLI 端到端冒烟测试（`init / new / status`）在**真实 HOME 环境**的临时目录里执行，而 `fstdd init` 会把项目登记进 `~/.fstdd/projects.yaml`——冒烟跑一次就污染一次注册表，且临时目录随后被清理，留下悬空条目。

## 处理

- 手工清理：保留真实项目（数据文件、公众号历史文章），删除全部 `stdd_smoke_*` 与历史测试条目。
- 根治建议：冒烟测试应隔离 HOME（如临时 `HOME` 环境变量 + 临时注册表），或事后回滚注册表。

## 性质

测试隔离性缺陷：**凡是会写用户级状态的命令，跑冒烟/集成测试时必须隔离其状态写入面**，否则测试本身就会污染生产配置。
