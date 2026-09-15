---
experience_id: EXP-C6A698A8
category: process_deviation
severity: medium
occurrences: 1
source_change: 2026-09-15-crlf-eol-governance
title: 5.2 基准数值偏差（已记录）
exported_at: 2026-09-15
sanitized: true
---
### 5.2 基准数值偏差（已记录）

提案中记录的告警基准为 640 行 / 670 文件，RED 阶段实测为 **637 行 / 671 文件**。
差异来自仓库文件数随本变更（新增 `.gitattributes`、`tools/verify_eol.py`）而变动。
640 作为基准量级仍成立，脚本中已注明「随文件数浮动」，不做硬断言。
