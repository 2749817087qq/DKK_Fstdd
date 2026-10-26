---
adoption_count: 0
category: coverage_vacuum
community_votes_unuseful: 0
community_votes_useful: 0
confidence: 0.5
detection_trigger: ci check-failures 报 TC 实现覆盖 0/N，但 impl 测试文件确实含 TC-ID 字样；或 change
  的测试全在 upstream/tests/ 而非根 tests/。
experience_id: STDD-EFC09CF4-EXP-2026-0041
first_seen: '2026-10-26'
fix_template: 沿用既定先例：在根 tests/ 放一份 *traceability.py，真正双树（tests/ + upstream/tests/）扫描验证实现存在，同时让
  ci 命中 TC-ID 字符串过门；不要为了过 ci 而把单测搬出 upstream/tests/。
language: python
last_seen: '2026-10-26'
lifecycle_state: discovered
occurrences: 1
pattern: fstdd ci check-failures 的「TC 实现覆盖率」检查硬编码只扫 project_root/"tests"，不扫 upstream/tests/（框架
  vendored 内核的单测目录），导致测试落在 upstream/tests/ 的 change 必然报 TC 覆盖 0/9 假红，错误阻断 Gate 3。
project_type: python
provenance: ai-inferred
provenance_weight: 0.6
root_cause: ci.py:605 写死 tests_dir = project_root / "tests"，未把 vendored 内核的 upstream/tests/
  纳入扫描根；框架自研的双根结构（根 tests/ 放集成测试 + upstream/tests/ 放单测）与 ci 的单根假设冲突。
severity: high
source_change: 2026-10-22-installation-id-backfill
source_file: ''
tags:
- ci
- coverage-blindspot
- tc-coverage
- false-red
- test-discovery
---

实测（2026-10-22-installation-id-backfill）：本 change 测试落在 upstream/tests/commands/test_installation_id_backfill.py，ci check-failures 报 TC 实现覆盖 0/9 假红（错误 1）。照搬上一 change（2026-10-21-installation-id-prefix）先例，在根 tests/ 新增 test_installation_id_backfill_traceability.py 做双树扫描，ci 转 9/9 PASS，错误归零。该盲区是框架结构性限制，不是本 change 的 bug；根因证据见 ci.py:605。同族参考：任何框架自研仓若把单测放在非根 tests/ 目录，都会踩同样的 ci 假红。
