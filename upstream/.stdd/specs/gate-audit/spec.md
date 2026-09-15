# Spec: gate-audit

> Change: 2026-08-17-v3.0.5-gate-hardening | Auto-generated Human View

## Requirements

### Requirement: _confirm_gate 必须写入完整审计链：confirmed_by + confirmed_actor + confirmed_evidence + confirmed_at

#### Scenario: SC-AUDIT-001

- **GIVEN** 用户确认 Gate 1 且 AI 带 --confirmed-by dialog --evidence "用户：确认" 运行 approve
- **WHEN** 检查 .stdd.yaml 的 phases.understand
- **THEN** 该 phase SHALL 包含 confirmed_at, confirmed_by=dialog, confirmed_evidence="用户：确认"
- **AND** confirmed_actor SHALL 存在（ai 或 user，由调用上下文推断）

#### Scenario: SC-AUDIT-002

- **GIVEN** Gate 1 已确认（confirmed_at 已存在）
- **WHEN** 再次运行 stdd gate approve --gate 1 --confirmed-by dialog
- **THEN** 命令 SHALL 输出"already confirmed"且不覆盖已存在的 confirmed_at/confirmed_by

### Requirement: 旧数据无 confirmed_by/actor/evidence 时 status 显示 (legacy) 容错

#### Scenario: SC-AUDIT-003

- **GIVEN** 一个已确认的 change 只有 confirmed_at 没有 confirmed_by
- **WHEN** 运行 stdd status
- **THEN** 该 change 的 Gate 行 SHALL 显示 (legacy) 标注
- **AND** 命令 SHALL 不抛异常
