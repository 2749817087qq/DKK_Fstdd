# 检测静默失效修复包（审计 15 处吞错 + F-1/F-2 + 审计勘误）

<!-- source_hash: b595d4a0d93aff91 -->
<!-- generated_at: 2026-09-18T02:28:03+00:00 -->
<!-- canonical: canonical/proposals/2026-09-18-detection-silence-fixes.yaml -->

## Why

silent-failure-audit 产出审计表：29 处裸 except 吞异常点中 15 处判
「意外吞错」（其中 7 处 P1 响应=升级 change），另有两个 BUILD 期发现
F-1（僵尸检测豁免活跃 change）与 F-2（滞后检测零接线）。这些检测路径
静默失效期间无人知晓（EXP-20260917-B3 同族教训）。本 change 按审计
分级一次性修复，并把其中一处审计误判（guard.py:315 实为 fail-closed）
以实证勘误。


## What Changes

- guard.py git 计数失败（EA-001/002）→ stderr 警告，不再静默返回 0
- guard.py 僵尸检测（EA-003）naive last_mod 按 UTC 归一，解析失败告警
- F-2：_check_phase_integrity_guard 接入 guard status 输出（滞后警告真正可见）
- F-2 同族：build/spec completed_at naive 归一（EA-005/006）
- F-1：status 僵尸扫描取消活跃豁免，活跃停滞 change 标注「当前活跃」
- status.py 僵尸 naive last_mod 归一 + 解析失败告警（EA-010）
- check_timestamps 三个扫描循环：文件级失败记 scan_errors，覆盖可观测（EA-011/012/013）
- validate 基线状态不可读 → 警告而非静默丢失（EA-014）
- baseline.py 基线文件损坏 → 警告而非视同未建立（EA-015）
- batch close Gate 3 确认失败 → 警告，证据链缺口可见（EA-017）
- fix.py 批量重写跳过计数并报告（EA-018）
- gate.py 单条 spec Human View 生成失败收集警告（EA-019）
- 审计勘误：guard.py:315（EA-004）改判合理容错——实证 except 路径 return False = 不放行 = fail-closed，最坏情况是合法产出物被拦（安全方向），原 P1 误判撤销， 勘误记录进 test-report

### Modified Capabilities

- **cli-guard**：检测路径失败全部有声（警告或 fail-closed），零静默跳过
- **cli-status**：僵尸检测覆盖活跃 change；naive 时间戳归一不再漏检
- **timestamp-guard-l2**：扫描错误计入报告，「零违规」不再掩盖覆盖缺口
- **experience-audit**：审计勘误机制落地（误判以实证纠正并留痕）

## Success Criteria

- [ ] 15 处意外吞错点全部修复或勘误，修复点有新测试锁定（每点 ≥1 断言其「有声」行为）
- [ ] F-1：单 change 项目活跃停滞 8 天，`fstdd status` 必报僵尸（端到端）
- [ ] F-2：`fstdd guard status` 输出包含滞后警告段（端到端）
- [ ] 修复后审计表刷新（tools/audit_silent_except.py --check 仍通过， 表条目与实际代码同步更新）
- [ ] 全量测试绿，新增测试函数 ≥12；verify_eol 7/7
- [ ] 无检测语义收紧：全部修复为「失败有声」，不改检测阈值
