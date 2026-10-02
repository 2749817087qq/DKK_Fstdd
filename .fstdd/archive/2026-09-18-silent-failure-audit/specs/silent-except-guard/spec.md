# Spec: silent-except-guard

> Change: 2026-09-18-silent-failure-audit | Auto-generated Human View

## Requirements

### Requirement: audit_silent_except.py 枚举吞异常点位并报告清单外新增，只读、可入 CI

#### Scenario: SC-020

- **GIVEN** 仓库任意状态
- **WHEN** 运行 python tools/audit_silent_except.py
- **THEN** 输出全部吞异常点位及其豁免匹配结果
- **AND** 扫描口径与 Gate 1 盘点一致：upstream/fstdd + tools/ 的 .py；except [Exception] 块首语句为空操作
- **AND** 全程只读：不得修改被审计文件（有测试断言）
- **AND** 清单外点位存在时退出码非零

#### Scenario: SC-021

- **GIVEN** 豁免清单条目与当前代码
- **WHEN** 匹配点位与条目
- **THEN** 文件相同 + 行号 ±5 容差 + 锚点函数名一致 即视为同一处
- **AND** 清单条目七字段齐全（含 reason ≥10 字），字段缺失本身被报出

#### Scenario: SC-022

- **GIVEN** 审计工具自身异常（豁免清单 YAML 损坏等）
- **WHEN** 运行
- **THEN** 以明确错误退出（区别于「发现清单外点位」），不静默成功

### Requirement: 豁免清单入仓且自证：当前全部点位有合法条目（工具对己零误报）

#### Scenario: SC-023

- **GIVEN** 本 change 完成后的仓库状态
- **WHEN** 运行审计工具
- **THEN** 退出码 0，且无「字段缺失」「理由无效」类警告
- **AND** 此时若制造一个清单外的新增点位（临时文件），工具报出且非零退出（负向验证）

### Requirement: 检测语义文件中的新增裸 pass except 被单独标级

#### Scenario: SC-024

- **GIVEN** 检测语义文件（文件名含 check/verify/guard/validate/audit 等）中的裸 pass except
- **WHEN** 审计
- **THEN** 该点位在报告中带 intentional-no-trace 标记（区别于普通 intentional）
- **AND** 存量已判 intentional 的不强制返工，但报告列出供后续渐进留痕
