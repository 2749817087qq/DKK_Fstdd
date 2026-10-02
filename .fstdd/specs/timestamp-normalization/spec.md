# Spec: timestamp-normalization

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: CLI 写入持久化产物的时间戳必须带时区，且与控制面可直接比较

#### Scenario: SC-010

- **GIVEN** 改造后的 CLI 生成一个含时间字段的产物
- **WHEN** 检查该时间字段的值
- **THEN** 该值 SHALL 匹配带时区的 ISO 8601（`([+-]\d{2}:\d{2}|Z)$`）
- **AND** 该值 SHALL NOT 为 naive 形态（无 offset 后缀）
- **AND** 该值 SHALL 由单一来源函数产生，而非各调用点自行拼装

#### Scenario: SC-011

- **GIVEN** CLI 产物中的时间字段与控制面返回的时间字段
- **WHEN** 对两者做字符串比较或排序
- **THEN** 比较与排序 SHALL 得到正确的时间先后关系
- **AND** 无需解析或换算时区即可比较
- **AND** 两者的时区表示 SHALL 一致（同为 UTC offset 形式）

#### Scenario: SC-012

- **GIVEN** 某字段是纯日期语义（无时刻）
- **WHEN** 检查该字段的值
- **THEN** 该字段 SHALL 为 `YYYY-MM-DD`，SHALL NOT 含时刻部分
- **AND** 含时刻却无时区的形态 SHALL 被判定为违规
- **AND** 用作标识符或目录名的日期片段 SHALL NOT 被判定为时间戳字段

### Requirement: naive 时间戳必须可被检测，且检测器不得产生大量误报

#### Scenario: SC-013

- **GIVEN** 产物文件中存在一个 naive 时间戳字段值
- **WHEN** 运行时间戳规范检测
- **THEN** 检测器 SHALL 报出该字段及其位置
- **AND** 判定 SHALL 基于字段的**值**，而非源码中是否出现某个调用
- **AND** 检测器 SHALL 输出被检查的字段总数，使「0 个违规」可被信任

#### Scenario: SC-014

- **GIVEN** 源码中存在上述 4 类非时间戳用途的 `datetime.now()` / `time.time()` 调用
- **WHEN** 运行时间戳规范检测
- **THEN** 检测器 SHALL NOT 将其报为违规
- **AND** 豁免类别 SHALL 以**配置数据**形式维护，而非散落在代码注释中
- **AND** 每条豁免 SHALL 附理由

#### Scenario: SC-015

- **GIVEN** 豁免清单中登记了若干条目
- **WHEN** 运行豁免清单自检
- **THEN** 每条豁免 SHALL 仍能在源码中定位到对应位置
- **AND** 无法定位的豁免 SHALL 被报出
- **AND** 该自检 SHALL 有对应测试覆盖

### Requirement: 时间戳规范必须有可执行的验收口径

#### Scenario: SC-016

- **GIVEN** 全仓扫描已执行
- **WHEN** 统计活跃 change 与模板中的 naive 时间戳数量
- **THEN** 结果 SHALL 为 0
- **AND** 扫描范围 SHALL 明确列出（活跃 change 的 `.fstdd.yaml` / canonical YAML / Human View 头部 + 两处 templates）
- **AND** 扫描 SHALL 可在任意节点重复执行且结果一致
- **AND** 扫描 SHALL 只读，SHALL NOT 修改任何被扫描文件
