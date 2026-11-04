---
adoption_count: 0
category: pipeline_break
community_votes_unuseful: 0
community_votes_useful: 0
confidence: 0.5
detection_trigger: 任何「据审计/日志/报告判断成败」的结论，在采取行动前必须先直接核验目标系统上的实际状态（文件在不在、进程活没活、tag 在不在）
experience_id: STDD-EFC09CF4-EXP-2026-0044
first_seen: '2026-11-04'
fix_template: 核验动作清单化：1 目标系统直接查（ls/ssh/API 查询）；2 与记录交叉比对；3 不一致时以一手事实为准并给记录系统提缺陷
language: null
last_seen: '2026-11-04'
lifecycle_state: discovered
occurrences: 1
pattern: 审计/日志是二手证据，落盘文件/服务器状态才是第一手事实 —— 二手证据与一手事实冲突时，先核实一手事实再下结论
project_type: config
provenance: ai-inferred
provenance_weight: 0.6
root_cause: 管道化系统（回传、CI、镜像）的成败记录由中间环节写入，中间环节自身的故障（timeout 杀进程、shim 吞输出、helper 静默跳过）会让记录与事实脱节；只看记录会得出与现场相反的结论
severity: high
source_change: 2026-10-31-share-scp-tar-packing
source_file: ''
tags:
- process
- audit
- evidence
- gate-approval
---

实例：v3.6.0 DELIVER 收尾时仅凭 share-audit.yaml 的 failure 记录误报「回传失败、112 条待传」，实际 scp 批次每次都落盘（三次 timeout 留下 13/25/37 个文件的半成品批次）。讽刺的是该误判发生在反漂移机制（形态 A：无证据断言）发布后的第一次收尾。延伸：git checkout -- 对 stat 缓存未变的损坏文件静默跳过，同属「工具说没问题、现场已损坏」一族。
