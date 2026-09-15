# Spec: bootcamp-scenarios (NEW)

## ADDED Requirements

### Req: 5关训练场景 SHALL 各自包含 scenario.yaml + answer/ 标准答案
#### Scenario: 关卡1 — lightweight
- GIVEN bootcamp start 加载第1关
- WHEN AI 执行训练
- THEN scenario.yaml SHALL 包含模拟需求（typo修复）
- AND answer/ SHALL 包含正确的 .stdd.yaml（含 phase推进和Gate确认）
- AND 考评 SHALL 检查 phase_cli/gate_cli/no_manual_yaml/archive_cli

#### Scenario: 关卡2 — standard
- GIVEN 加载第2关
- WHEN AI 执行训练
- THEN scenario SHALL 包含模拟需求（API限流功能）
- AND answer SHALL 包含 design.md+specs/+test-plan.md+proposal.yaml
- AND 考评 SHALL 检查 slice_analysis/mode_selection/canonical_yaml

#### Scenario: 关卡3 — thorough
- GIVEN 加载第3关
- WHEN AI 执行训练
- THEN 考评 SHALL 检查 long_range/anchoring/per_slice_evidence/failure_modes/gate3

#### Scenario: 关卡4 — agent
- GIVEN 加载第4关
- WHEN AI 执行训练
- THEN 考评 SHALL 检查 agent_spec/cp_checkpoints/cross_check/bash_in_change

#### Scenario: 关卡5 — 综合
- GIVEN 加载第5关
- WHEN AI 执行训练
- THEN 考评 SHALL 检查 multi_capability/experience/knowledge_graph/full_gate_chain

### Req: stdd bootcamp grade SHALL 对每关执行自动评分
#### Scenario: 文件存在+格式校验
- GIVEN work/ 目录存在训练产出
- WHEN 执行 bootcamp grade N
- THEN 系统 SHALL 逐文件对比 answer/ 检查存在性
- AND SHALL 检查 spec.md 含 SHALL 关键字
- AND SHALL 输出得分+通过/未通过
