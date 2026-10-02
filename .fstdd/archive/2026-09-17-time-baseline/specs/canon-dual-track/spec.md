# Spec: canon-dual-track

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: DC-HASH 必须基于归一后的内容计算，解除与行尾治理的耦合

#### Scenario: SC-042

- **GIVEN** 同一份 canonical YAML 的两种行尾表示（CRLF 与 LF）
- **WHEN** 分别计算其 DC-HASH
- **THEN** 两个哈希 SHALL 相同
- **AND** 归一函数 SHALL 与 `tools/verify_eol.py` 的 `normalize()` 同口径
- **AND** 归一 SHALL NOT 改变 YAML 的语义内容

#### Scenario: SC-043

- **GIVEN** canonical YAML 在 CRLF 工作区中被写入并记录 DC-HASH
- **WHEN** 在 LF 工作区中执行 `canon verify`
- **THEN** 校验 SHALL 通过
- **AND** SHALL NOT 报告 DC-HASH 失配
- **AND** 校验 SHALL 不依赖工作区的行尾状态

### Requirement: 干净克隆必须能通过双轨校验

#### Scenario: SC-044

- **GIVEN** 一个干净克隆（全部文件为 LF）
- **WHEN** 在克隆中执行 `canon verify`
- **THEN** 结果 SHALL 为 2/2 通过（DC-HASH 源哈希一致 + DC-FIELD 字段引用完整）
- **AND** 该结论 SHALL 在非生成机器上同样成立
- **AND** SHALL NOT 需要先执行任何归一命令

#### Scenario: SC-045

- **GIVEN** 存量活跃 change 的 Human View 头部记录的是旧算法哈希
- **WHEN** 执行一次性重生成
- **THEN** 系统 SHALL 用新算法重写 Human View 头部的 `source_hash`
- **AND** 重生成 SHALL 只改动 `source_hash` 一行，SHALL NOT 改动正文
- **AND** 重生成后 `canon verify` SHALL 通过
- **AND** 归档 change SHALL NOT 被回溯修改

### Requirement: DC-HASH 的比对必须能真正发现不同步，不得退化为恒真

#### Scenario: SC-046

- **GIVEN** canonical YAML 被修改，但 Human View 未重新生成
- **WHEN** 执行 `canon verify`
- **THEN** 校验 SHALL 报告 DC-HASH 失配
- **AND** 校验 SHALL 以非 0 退出码结束
- **AND** 该行为 SHALL 有对应测试覆盖（含变异测试）

#### Scenario: SC-047

- **GIVEN** 在归一函数中注入一个已知缺陷（如只处理 `\r\n` 而忽略孤立 `\r`）
- **WHEN** 运行归一相关测试
- **THEN** 至少 1 个测试 SHALL 失败
- **AND** 变异 SHALL 以纯内存方式注入，SHALL NOT 留下文件残留
- **AND** 注入后 SHALL 恢复原状并复验
