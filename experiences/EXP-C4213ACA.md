---
experience_id: EXP-C4213ACA
category: process_deviation
severity: medium
occurrences: 1
source_change: 2026-09-15-skill-engineering-standards
title: 6.1 统计口径争议（数据修正）
exported_at: 2026-09-15
sanitized: true
---
### 6.1 统计口径争议（数据修正）

**现象**：首次统计 version 为「17/40 有，缺 23」，check 脚本给出「9/40，缺 31」。

**根因**：首次统计用正则 `^(version|stdd_version):`，把 STDD 系列的
`stdd_version: "3.0.5"` 也算作版本。但那是**上游 STDD 的版本号**，
不是 skill 自身版本，混算会得出偏乐观的数字。

**处理**：统一采用严格口径——只认 `version` 字段。修正提案、测试与报告中的
全部相关数字（23 → 31，四项齐全 3 → 1）。

**性质**：实测修正了提案数据。这正是 STDD「证据优先」的体现——
提案里的数字被后续实测推翻时，以实测为准并同步更正。
