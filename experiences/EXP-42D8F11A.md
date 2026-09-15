---
experience_id: EXP-42D8F11A
category: process_deviation
severity: medium
occurrences: 1
source_change: 2026-09-15-skill-engineering-standards
title: 6.3 两个用例的断言依赖一次性状态（已修正）
exported_at: 2026-09-15
sanitized: true
---
### 6.3 两个用例的断言依赖一次性状态（已修正）

- **TC-SES-003**：原断言依赖「修复前」的 37/31 状态，`--fix` 后不再可复现。
  改为构造样本验证统计逻辑，保证随时可重复。初始实测数据已在 4.1 记录。
- **TC-SES-004**：原断言假设总有文件待修复，已合规时会误报 FAIL。
  改为「合规状态 + 备份完整 + 正文一致 + 幂等」四项复合断言。

两者都属于**测试设计缺陷**，非实现缺陷，均由红灯暴露。
