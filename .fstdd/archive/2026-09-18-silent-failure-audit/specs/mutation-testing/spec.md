# Spec: mutation-testing

> Change: 2026-09-18-silent-failure-audit | Auto-generated Human View

## Requirements

### Requirement: 关键检测路径各有 ≥1 个变异测试，注入已知缺陷必红

#### Scenario: SC-010

- **GIVEN** 关键检测路径：guard 僵尸检测、guard 卡壳检测、check_timestamps L1 值层、check_timestamps L2 源层、validate 基线警告
- **WHEN** 向其依赖注入一个已知必触发该检测的缺陷
- **THEN** 检测报出（红）
- **AND** 每个路径的变异测试可独立运行（pytest -k 可选中）

#### Scenario: SC-011

- **GIVEN** 变异测试执行完毕（无论断言成败）
- **WHEN** 检查被测环境状态
- **THEN** 注入的缺陷已恢复（try/finally），后续测试不受污染
- **AND** 恢复后检测恢复绿（变异测试双自证的后半段）

#### Scenario: SC-012

- **GIVEN** 一个变异测试
- **WHEN** 审查其有效性
- **THEN** 含双自证：注入后必红 + 恢复后必绿
- **AND** 自证逻辑内联在同一条用例里（不接受「另一个测试验过它」）

### Requirement: 注入方式必须是真实代码路径上的真实缺陷，不得打桩绕过被检测逻辑

#### Scenario: SC-013

- **GIVEN** 变异测试设计
- **WHEN** 选择注入手段
- **THEN** 优先选择 monkeypatch 被测代码的内部依赖或临时写入缺陷数据
- **AND** 不得 mock 掉被检测的函数本身（否则检测永远没机会执行）
- **AND** 注入点即真实执行路径上的点
