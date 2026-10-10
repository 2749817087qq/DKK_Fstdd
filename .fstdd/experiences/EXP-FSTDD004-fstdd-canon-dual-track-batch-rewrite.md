<!-- fstdd-inbox
experience_id: EXP-FSTDD004-fstdd-canon-dual-track-batch-rewrite
author: anonymous
received_at: 2026-10-09T16:44:40.947056+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-fstdd-canon-dual-track-batch-rewrite
category: fstdd_workflow
severity: high
date: '2026-10-03'
node: FSTDD004
title: ① 批量回改 canonical 数字后，fstdd canon verify 报 DC-HASH 不一致（YAML 哈希 ≠ MD source_hash）
occurrences: 1
pattern: Phase 4 DELIVER 中批量回改 canonical 产物时连环踩坑：① 改了 canonical/proposals/<ch>.yaml
  的数字后 proposal.md 里的 source_hash 变过期，canon verify 报 DC-HASH 不一致；② 修复脚本里 io.open(p,'w').write(s.encode('utf-8'))
  触发 TypeError（write 要str 不要 bytes），脚本在第一个文件后就崩，把 canonical/specs/code/<cap>.yaml
  截成了 0 字节；③ 从 change 级 spec.md 反解重建时用了 title 字段与缺失 evidence，与原版 schema 不一致，fstdd
  validate 直接失败。
root_cause: FSTDD 的 canonical 是「YAML 为真值源 + Human View（md）带 source_hash 缓存」的双轨结构，任何一侧单独改动都会让另一侧失效；批量改写脚本缺少「行尾探测
  + 原子写 + 逐文件断言」，一处失败即中断并留下半损坏产物；重建时未先读同族文件确认 schema。
detection_trigger: ① 批量回改 canonical 数字后，fstdd canon verify 报 DC-HASH 不一致（YAML 哈希 ≠
  MD source_hash）；② 归档后想重生成 Human View 但工具报 change not found；③ canonical/specs/code/<cap>.yaml
  变成 0 字节；④ 重建 spec 时 YAML 能 load 但 fstdd validate 报字段缺失。
fix_template: '# ✅ 1) 改过 canonical YAML 后，必须重生成 Human View 对齐 source_hash

  fstdd canon generate 2026-10-02-fcbar-event-aggregate

  #    归档后也能跑：_resolve_change_dir 会指向 archive/，工具直接写归档目录


  # ✅ 2) spec 被清空时从 change 级 Human View 反解重建（字段 schema 要对齐同族文件）

  import re, yaml, io

  md = io.open(r''changes/<ch>/specs/<cap>/spec.md'', encoding=''utf-8'').read()

  #    参照 code/<other-cap>.yaml 的真实 schema：requirements[].description（非 title）、

  #    scenarios[].confidence + evidence + given/when/then/and

  d = yaml.safe_load(io.open(r''canonical/specs/code/<other-cap>.yaml'', encoding=''utf-8'').read())

  print(list(d[''requirements''][0].keys()), list(d[''requirements''][0][''scenarios''][0].keys()))


  # ✅ 3) 批量回改前逐文件探测行尾（FSTDD 目录内 CRLF/LF 混杂）

  b = io.open(p, ''rb'').read(); nl = ''\r\n'' if b''\r\n'' in b else ''\n''

  old = nl.join([''  deliver:'', ''    status: in_progress'', ''''])

  assert s.count(old) == 1          # 断言拦住「行尾不符导致 0 命中」


  # ✅ 4) 写完立刻 safe_load 复验，别等下游报错

  yaml.safe_load(io.open(p, encoding=''utf-8'').read())'
tags:
- fstdd
- canon
- dual-track
- source-hash
- schema-mismatch
- crlf
- batch-rewrite
language: python


## 现场

DELIVER 批量回改 canonical 数字时连环踩坑：

① 改了 `canonical/proposals/<ch>.yaml` 后 `proposal.md` 的 `source_hash` 过期，`canon verify` 报 DC-HASH 不一致（`YAML: 38152dcdb32a2976, MD: 221335fb0136dd43`）；
② 修复脚本里 `io.open(p,"w").write(s.encode("utf-8"))` 触发 `TypeError: write() argument must be str, not bytes`，脚本在**第一个文件后就崩**，把 `canonical/specs/code/equity-calendar-forecast-bar.yaml` 截成 **0 字节**；
③ 从 change 级 `spec.md` 反解重建时用了 `title` 字段、缺 `evidence`，与原版 schema 不一致（首轮重建 8835 B 校验失败，按 `code/equity-calendar-legend.yaml` 的真实 schema 重建后才12140 B 通过）。

另外 FSTDD 目录内**行尾混杂**：`proposal.md` / `spec.md` 是 CRLF，`design.md` / `test-plan.md` 是 LF；`.fstdd.yaml` 也是 CRLF。统一按 LF 拼锚点会 `count==0`，靠 `assert s.count(old)==1` 拦下。

## 处置

① 重跑 `fstdd canon generate <ch>` 对齐 source_hash（归档后也能跑，`_resolve_change_dir` 指向 archive/）；② 从 change 级 spec.md 重建到 12140 B / 7 REQ / 18 SC；③ 批量改写前逐文件探测行尾，`compile`-free 纯字符串替换 + 逐文件 `assert count==1` + 写完 `safe_load`。

## 教训

1. 批量改写四件套：bytes 探测行尾 → 逐文件 `assert count==1` → 原子写 → 写完 `safe_load` 复验。任何一步都不能省，尤其是别让脚本「崩在半路」留下 0 字节产物。

## 改善方法

- 根因：FSTDD 的 canonical 是「YAML 为真值源 + Human View（md）带 source_hash 缓存」的双轨结构，任何一侧单独改动都会让另一侧失效；批量改写脚本缺少「行尾探测 + 原子写 + 逐文件断言」，一处失败即中断并留下半损坏产物；重建时未先读同族文件确认 schema。
- 检测信号：① 批量回改 canonical 数字后，fstdd canon verify 报 DC-HASH 不一致（YAML 哈希 ≠ MD source_hash）；② 归档后想重生成 Human View 但工具报 change not found；③ canonical/specs/code/<cap>.yaml 变成 0 字节；④ 重建 spec 时 YAML 能 load 但 fstdd validate 报字段缺失。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0086 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
