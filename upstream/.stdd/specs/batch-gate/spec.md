# Spec: batch-gate

> Change: 2026-08-17-v3.0.5-gate-hardening | Auto-generated Human View

## Requirements

### Requirement: 批级 Gate 确认强制 --confirmed-by 通道声明，不再静默自动确认

#### Scenario: SC-BATCH-001

- **GIVEN** 一个 open batch 处于 spec 阶段（Gate 2 待确认）
- **WHEN** 运行 stdd batch gate --gate 2 且省略 --confirmed-by
- **THEN** 命令 SHALL 拒绝并提示需要 --confirmed-by 通道声明
- **AND** .stdd.yaml 的批级 confirmed_at SHALL 保持为空

#### Scenario: SC-BATCH-002

- **GIVEN** 一个 open batch 处于 spec 阶段，用户已确认 Gate 2
- **WHEN** 运行 stdd batch gate --gate 2 --confirmed-by dialog
- **THEN** 命令 SHALL 成功确认，批级 confirmed_by SHALL 为 dialog
- **AND** 子 change 继承批级 confirmed_by/confirmed_actor

### Requirement: 批级 deliver 的 Gate 3 不得静默自动确认（batch.py:673-675 收口）

#### Scenario: SC-BATCH-003

- **GIVEN** 批级 deliver 被调用且无 --confirmed-by 通道声明
- **WHEN** 运行 stdd batch deliver
- **THEN** Gate 3 SHALL 不被自动确认
- **AND** 命令 SHALL 输出提示要求显式通道声明，或跳过 Gate 3 确认仅聚合证据
