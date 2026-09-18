# Spec: except-audit

> Change: 2026-09-18-silent-failure-audit | Auto-generated Human View

## Requirements

### Requirement: 29 处吞异常点位 100% 有审计结论，逐条记录理由

#### Scenario: SC-001

- **GIVEN** Gate 1 盘点清单（29 处）与豁免清单 audit-exceptions.yaml
- **WHEN** 逐点审计并写入结论
- **THEN** 每处条目含 file / line / anchor / category / reason / audited_at / audited_by 七字段
- **AND** category ∈ {intentional, bug-fixed, narrowed}，无空值
- **AND** reason 非空且非套话（少于 10 字视为无效）
- **AND** 29 处覆盖率 100%，审计清单本身有测试断言

### Requirement: 审计分类不得改变既有检测的判定语义

#### Scenario: SC-002

- **GIVEN** 审计完成后的代码
- **WHEN** 运行全量工程测试
- **THEN** 无回归（基线 692 passed / 694 collected；允许因修复 bug 类点位而新增通过）
- **AND** narrow 类点位的旧行为变化必须有对应测试用例说明新行为

### Requirement: bug 类点位修复遵循 TDD 且真跑代码路径

#### Scenario: SC-003

- **GIVEN** 审计判定为 bug 的点位
- **WHEN** 修复
- **THEN** 先有失败测试暴露该缺陷（RED），修复后 GREEN
- **AND** 测试真实执行该代码路径（非打桩绕过）
- **AND** 修复后的 except 块留 logger.debug 痕迹（留痕规范）
