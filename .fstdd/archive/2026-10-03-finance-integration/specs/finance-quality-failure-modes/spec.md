# Spec: finance-quality-failure-modes

> Change: 2026-10-03-finance-integration | Auto-generated Human View

## Requirements

### Requirement: quality.yaml 失败模式库追加 8 类金融特有模式

#### Scenario: SC-030

- **GIVEN** quality.yaml 已有 14 类通用失败模式
- **WHEN** 追加金融特有失败模式
- **THEN** quality.yaml SHALL 包含 8 类金融特有模式：重复扣款/账实不符/静默降级/精度丢失/审计缺口/状态机漏洞/额度穿透/合规遗漏
- **AND** 每类 SHALL 含 failure_pattern + detection_trigger + fix_template 三字段，与现有 14 类 schema 一致

### Requirement: 追加不破坏现有 14 类模式

#### Scenario: SC-031

- **GIVEN** quality.yaml 原有 14 类
- **WHEN** 追加 8 类
- **THEN** 原有 14 类条目 SHALL 一字不改
