<!-- fstdd-inbox
experience_id: EXP-42D8F11A
author: anonymous
received_at: 2026-10-04T10:15:04.511498+00:00
remote_addr: 172.18.0.8
node_id: FSTDD006
-->

---
exported_at: 2026-10-04
sanitized: true
---
<!-- fstdd-inbox
experience_id: EXP-42D8F11A
author: anonymous
received_at: 2026-09-26T08:30:09.628589+00:00
remote_addr: <IP>
node_id: FSTDD001
-->

---
exported_at: 2026-09-26
sanitized: true
---
<!-- fstdd-inbox
experience_id: EXP-42D8F11A
author: (anonymous)
received_at: 2026-09-18T16:33:39.468961+00:00
remote_addr: <IP>
-->

---
experience_id: EXP-42D8F11A
category: process_deviation
severity: medium
occurrences: 2
source_change: 2026-09-15-skill-engineering-standards
title: 6.3 两个用例的断言依赖一次性状态（已修正）
exported_at: 2026-09-19
sanitized: true
lifecycle_state: deposited
---
### 6.3 两个用例的断言依赖一次性状态（已修正）

- **TC-SES-003**：原断言依赖「修复前」的 37/31 状态，`--fix` 后不再可复现。
  改为构造样本验证统计逻辑，保证随时可重复。初始实测数据已在 4.1 记录。
- **TC-SES-004**：原断言假设总有文件待修复，已合规时会误报 FAIL。
  改为「合规状态 + 备份完整 + 正文一致 + 幂等」四项复合断言。

两者都属于**测试设计缺陷**，非实现缺陷，均由红灯暴露。

## 第二次命中（2026-09-30，change `2026-09-29-clean-rename-residue` 切片 S5 / ADJ-012）

同一形态出现在**新写的护栏**上，而不是旧用例：`tests/integration/test_diff_no_upstream.py`
的「工作区噪声例外表」原先断言 `present == table`（例外表内容与实际噪声**逐字相等**）。
该判据依赖的是**本机工作区的外部状态**：换一个节点、网盘客户端多留一个 `.downloading` 残留、
或本 change 归档后噪声自然消失，断言就会无原因地红/白。改为按**性质分类判定**后仍保留拦截力：
mtime 晚于 Gate 1 基线 ⇒ FAIL（撞进例外表也不豁免）；早于基线且未登记 ⇒ warning；
登记项在工作区已不存在 ⇒ warning（与 `stale_layout_entries()` 同形）。

同一切片里另一处同族修正：`change_window_open()` —— 该护栏只对本 change 窗口内的动作有意义，
归档后窗口必然不存在，若不断言「窗口关了就 skip」，它会在归档之后变成一条**永远红**的护栏。
⇒ 一般化：**护栏必须声明自己的适用窗口**；对窗口外的运行 SHALL `skip` 而非 `fail`，
否则「迟早恒红的护栏」会训练读者忽略它，与 EXP-20260917-A1 的「误报比漏报更危险」同一结论。
