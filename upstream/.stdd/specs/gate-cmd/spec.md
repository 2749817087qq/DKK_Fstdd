# Spec: gate-cmd

> Change: 2026-08-17-v3.0.5-gate-hardening | Auto-generated Human View

## Requirements

### Requirement: cmd_gate 必须强制要求显式 --confirmed-by 通道声明（dialog|file_token|cli），无默认值

#### Scenario: SC-GATE-001

- **GIVEN** 一个 active change 处于 understand 阶段（Gate 1 待确认）
- **WHEN** 运行 stdd gate approve --gate 1 且省略 --confirmed-by
- **THEN** 命令 SHALL 以 exit 2 拒绝，且不写入 confirmed_at
- **AND** stderr SHALL 提示合法的 --confirmed-by 通道值 (dialog|file_token|cli)
- **AND** .stdd.yaml 的 phases.understand.confirmed_at SHALL 保持为空

#### Scenario: SC-GATE-002

- **GIVEN** 用户已口头确认 Gate 1
- **WHEN** 运行 stdd gate approve --gate 1 --confirmed-by dialog --evidence "用户：确认"
- **THEN** 命令 SHALL 成功确认，.stdd.yaml 写入 phases.understand.confirmed_at
- **AND** phases.understand.confirmed_by SHALL 为 dialog
- **AND** phases.understand.confirmed_evidence SHALL 为传入的 evidence 原文

### Requirement: file_token 通道仅在 GATE<N>_APPROVED 文件存在时生效

#### Scenario: SC-GATE-003

- **GIVEN** change 目录下无 GATE2_APPROVED 文件
- **WHEN** 运行 stdd gate approve --gate 2 --confirmed-by file_token
- **THEN** 命令 SHALL 以 exit 2 拒绝，不写入 confirmed_at

#### Scenario: SC-GATE-004

- **GIVEN** change 目录下存在 GATE2_APPROVED 文件
- **WHEN** 运行 stdd gate approve --gate 2 --confirmed-by file_token
- **THEN** 命令 SHALL 成功确认，confirmed_by SHALL 为 file_token

### Requirement: _check_gate_order 顺序检查对所有通道生效（含 file_token 路径）

#### Scenario: SC-GATE-005

- **GIVEN** Gate 1 未确认、Gate 2 的 GATE2_APPROVED 已存在
- **WHEN** 运行 stdd gate approve --gate 2 --confirmed-by file_token
- **THEN** 命令 SHALL 拒绝并提示 Gate 1 尚未确认（exit 1）
