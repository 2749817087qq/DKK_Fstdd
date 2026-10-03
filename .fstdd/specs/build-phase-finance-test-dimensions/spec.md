# Spec: build-phase-finance-test-dimensions

> Change: 2026-10-03-finance-integration | Auto-generated Human View

## Requirements

### Requirement: build.md 注入 10 维金融特有测试维度

#### Scenario: SC-020

- **GIVEN** UNDERSTAND 阶段判定 FINANCIAL_PROJECT=YES
- **WHEN** 进入 BUILD 阶段
- **THEN** build.md SHALL 提示 Agent 覆盖 10 维金融测试
- **AND** 10 维 SHALL 逐项对应具体测试思路（如精度=Decimal 测试、幂等=重复请求无副作用）

### Requirement: 非金融项目 BUILD 阶段不触发金融测试

#### Scenario: SC-021

- **GIVEN** FINANCIAL_PROJECT=NO
- **WHEN** 进入 BUILD 阶段
- **THEN** build.md 的金融条件段落 SHALL 不要求 10 维金融测试
