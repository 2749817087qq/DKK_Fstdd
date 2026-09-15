# Spec: guard-path

> Change: 2026-08-17-v3.0.5-gate-hardening | Auto-generated Human View

## Requirements

### Requirement: guard 增加 --hook-stdin 开关，hook 模式读 stdin JSON 拿目标文件路径

#### Scenario: SC-GUARD-001

- **GIVEN** guard 以 --hook-stdin 模式运行，stdin 传入 JSON {tool_input: {file_path: app/foo.py}}
- **WHEN** 执行 stdd guard check --platform claude-code --hook-stdin
- **THEN** guard SHALL 成功解析目标路径并按其 phase 规则判定
- **AND** stdin 解析失败 SHALL fail-open 返回 0（不误伤编辑）

### Requirement: understand/spec 阶段放行 canonical/ 下的 YAML 流程产出物（修 YAML-first 冲突）

#### Scenario: SC-GUARD-002

- **GIVEN** 一个 active change 处于 understand 阶段（Gate 1 未确认）
- **WHEN** 尝试用 Edit/Write 工具写 changes/<c>/canonical/proposals/<c>.yaml
- **THEN** guard SHALL 返回 0 放行（YAML-first 流程产出物）
- **AND** 同样放行 change 内 design.md/test-plan.md/proposal.md/specs/ 下的流程产出物

#### Scenario: SC-GUARD-003

- **GIVEN** 一个 active change 处于 understand 阶段
- **WHEN** 尝试用 Edit/Write 工具写 app/foo.py（非流程产出物）
- **THEN** guard SHALL 返回 2 阻断（understand 非可编辑阶段）

### Requirement: guard 阻断 AI 直接写 GATE<N>_APPROVED token 文件与篡改 .fstdd.yaml 确认字段

#### Scenario: SC-GUARD-004

- **GIVEN** 任何 phase
- **WHEN** 尝试用 Edit/Write 工具写 changes/<c>/GATE3_APPROVED
- **THEN** guard SHALL 返回 2 阻断（token 必须由用户人工创建）
- **AND** 写 .fstdd.yaml 且内容含 confirmed_at/confirmed_by SHALL 返回 2 阻断

#### Scenario: SC-GUARD-005

- **GIVEN** active change 处于 build 阶段
- **WHEN** 尝试用 Edit/Write 工具写 app/foo.py
- **THEN** guard SHALL 返回 0 放行
