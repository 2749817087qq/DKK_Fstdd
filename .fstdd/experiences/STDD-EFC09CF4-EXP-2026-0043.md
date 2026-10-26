---
adoption_count: 0
category: tool_misuse
community_votes_unuseful: 0
community_votes_useful: 0
confidence: 0.5
detection_trigger: '任何「读 YAML -> 改某字段 -> yaml.dump 整体写回」的代码路径；尤其文件含 # 注释行或 `key: |`
  块标量标记时。'
experience_id: STDD-EFC09CF4-EXP-2026-0043
first_seen: '2026-10-26'
fix_template: '改用 bytes 级定向插入（如 utils.set_top_level_scalar）：按主导行尾（CRLF/LF）保持、剥 UTF-8
  BOM、在首个顶层键前插入 / 原位替换目标键；写入前做 4 条自检（safe_load 可解析、去掉目标键后深比较键值不变、原 # 注释行逐行仍在、块标量标记
  `^[A-Za-z_][A-Za-z0-9_]*:\s*\|` 仍在），任一失败不落盘。Windows 须用 write_bytes 保行尾，勿用 write_text（会把
  \n 翻成 \r\n）。'
language: python
last_seen: '2026-10-26'
lifecycle_state: discovered
occurrences: 1
pattern: '用 yaml.dump 整体回写带注释头 / 块标量（key: |）的手写 YAML（如 .fstdd/version.yaml），会丢掉全部
  # 注释、把 block scalar 退化成转义单行串、并重新排序键——一次写入把 336 行文件缩成 235 行、注释头全丢。'
project_type: python
provenance: ai-inferred
provenance_weight: 0.6
root_cause: yaml.dump 只序列化数据模型，不保留源文本形态；当 YAML 除数据外还承载人类维护的注释 / 块标量 / 键顺序时，整体重写即破坏这些信息。
severity: high
source_change: 2026-10-22-installation-id-backfill
source_file: ''
tags:
- yaml
- serialization
- text-preservation
- block-scalar
- comment-loss
- version-yaml
---

实测（2026-10-22-installation-id-backfill）：init._ensure_installation_id 与 upgrade._write_version_yaml 原先用 yaml.dump 整体回写 version.yaml，已造成注释头丢失、changelog 块标量退化为转义串。本 change 改用 utils.set_top_level_scalar（bytes 级定向插入），保留注释头 / 块标量 / 行尾，并加 4 条写入前自检防止静默破坏。判别力关键：验收测试必须用文本级断言（注释行 / 块标量标记仍在），不能只用 yaml.safe_load 语义相等——否则 baseline(yaml.dump) 也能语义通过，变成假绿。
