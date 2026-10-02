# Spec: evidence-provenance

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: 证据条目必须携带观测时刻与观测时的代码版本

#### Scenario: SC-017

- **GIVEN** canonical proposal 的 `why.evidence` 已填写
- **WHEN** 检查该证据块
- **THEN** SHALL 含 `observed_at`（观测时刻，带时区）
- **AND** SHALL 含 `observed_base_git_sha`（观测时的代码版本）
- **AND** 两者 SHALL NOT 为空

#### Scenario: SC-018

- **GIVEN** canonical spec 的某个 scenario 已填写 `evidence`
- **WHEN** 检查该 evidence 字段
- **THEN** SHALL 能定位到其观测时刻
- **AND** 若 evidence 引用实测数据，SHALL 标注观测时刻
- **AND** test-report 的证据条目 SHALL 同样携带 `observed_at`

#### Scenario: SC-019

- **GIVEN** 读取两处模板中的 proposal 模板与 spec 模板
- **WHEN** 检查模板中的证据字段
- **THEN** 模板 SHALL 包含观测时刻与代码版本字段
- **AND** 两处模板（`upstream/.fstdd/templates/**` 与 `.fstdd/templates/**`）SHALL 一致
- **AND** 模板 SHALL 含填写示例，而非仅字段名

### Requirement: 证据是否过期必须成为可判定问题

#### Scenario: SC-020

- **GIVEN** 某条证据携带 `observed_at`，且所属 change 有 `baseline.at`
- **WHEN** 比较两者
- **THEN** 系统 SHALL 能判定证据是「在基线之后观测」还是「早于基线」
- **AND** 判定结果 SHALL 可被程序读取（非仅打印文本）
- **AND** 证据早于基线时 SHALL 被明确标识，而非静默通过

#### Scenario: SC-021

- **GIVEN** 证据缺少观测时刻
- **WHEN** 执行时效判定
- **THEN** 系统 SHALL 报告「无法判定时效」
- **AND** SHALL NOT 把「无法判定」当作「未过期」
- **AND** 该三态（未过期 / 早于基线 / 无法判定）SHALL 可区分
