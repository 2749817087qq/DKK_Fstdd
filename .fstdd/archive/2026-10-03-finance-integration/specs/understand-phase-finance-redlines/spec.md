# Spec: understand-phase-finance-redlines

> Change: 2026-10-03-finance-integration | Auto-generated Human View

## Requirements

### Requirement: understand.md 前置金融系统判定钩子（关键词白名单匹配）

#### Scenario: SC-010

- **GIVEN** understand.md 是四阶段 UNDERSTAND 入口 skill
- **WHEN** 在 Step 1 之前插入金融系统判定段落
- **THEN** understand.md SHALL 包含关键词白名单判定：支付/银行/交易/撮合/风控/KYC/AML/DeFi/结算/对账/资金/金额/Decimal/幂等/账户/余额/汇率/杠杆/保证金/清算/行情/托管/票据/债券/股票/期货/期权/私募/公募/资管/净值/回撤/夏普/贝塔/阿尔法/波动率/流动性风险/信用风险/市场风险
- **AND** 判定结果 SHALL 标记为 FINANCIAL_PROJECT=YES/NO

### Requirement: 金融项目必须过 7 红线强制检查

#### Scenario: SC-011

- **GIVEN** 判定结果 FINANCIAL_PROJECT=YES
- **WHEN** UNDERSTAND 阶段执行
- **THEN** Agent SHALL 逐项检查 7 红线，缺失任一则 Gate 1  SHALL NOT 通过
- **AND** 红线检查 SHALL 记录到 proposal.md 的 Critical/Security 章节

### Requirement: 非金融项目不触发金融钩子

#### Scenario: SC-012

- **GIVEN** 判定结果 FINANCIAL_PROJECT=NO（如普通 CRUD 工具）
- **WHEN** UNDERSTAND 阶段执行
- **THEN** understand.md 的金融条件段落 SHALL 不要求任何额外检查
