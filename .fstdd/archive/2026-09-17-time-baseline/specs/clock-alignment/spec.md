# Spec: clock-alignment

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: 一条命令报告各节点与本机的时钟偏差，并给出误差上界

#### Scenario: SC-022

- **GIVEN** 节点清单已配置
- **WHEN** 执行时钟巡检命令
- **THEN** 输出 SHALL 含每个节点的 `offset`（偏移估计）、`rtt` 与 `err`（误差上界）
- **AND** SHALL 含实际采样次数与有效样本数
- **AND** SHALL 含 `jitter`（RTT 抖动）
- **AND** `--format json` SHALL 输出可被程序解析的结构

#### Scenario: SC-023

- **GIVEN** 同一节点存在多次采样
- **WHEN** 计算最终偏移估计
- **THEN** 系统 SHALL 采用最小 RTT 的那次样本
- **AND** SHALL NOT 采用全部样本的算术平均作为偏移估计
- **AND** 所选样本的 RTT SHALL 出现在输出中，使估计可被复核

### Requirement: 巡检必须给出三态判定，且三态可区分、不互相冒充

#### Scenario: SC-024

- **GIVEN** 节点可达、抖动在阈值内、且 `abs(offset) <= TOLERANCE` 且 `err <= TOLERANCE`
- **WHEN** 执行时钟巡检
- **THEN** 该节点 SHALL 被判定为「可接受」
- **AND** 命令 SHALL 以退出码 0 结束

#### Scenario: SC-025

- **GIVEN** 节点可达、抖动在阈值内、`err <= TOLERANCE`，但 `abs(offset) > TOLERANCE`
- **WHEN** 执行时钟巡检
- **THEN** 该节点 SHALL 被判定为「超限」
- **AND** 命令 SHALL 以退出码 1 结束
- **AND** 退出码 SHALL 与「无法测量」不同

#### Scenario: SC-026

- **GIVEN** 节点不可达，或有效样本数不足，或 `jitter > JITTER_MAX`，或 `err > TOLERANCE`
- **WHEN** 执行时钟巡检
- **THEN** 该节点 SHALL 被判定为「无法测量」
- **AND** 命令 SHALL 以退出码 2 结束
- **AND** SHALL NOT 报告为「可接受」
- **AND** SHALL NOT 报告为「超限」

#### Scenario: SC-027

- **GIVEN** 测量结果落在噪声中（`err > TOLERANCE`）
- **WHEN** 生成判定
- **THEN** 判定 SHALL NOT 为「可接受」
- **AND** 即使 `abs(offset)` 恰好小于容差，SHALL 仍判为「无法测量」
- **AND** 输出 SHALL 说明判为「无法测量」的具体原因（不可达 / 样本不足 / 抖动 / 误差上界）

### Requirement: 巡检必须只读、幂等，且对不可达节点稳健

#### Scenario: SC-028

- **GIVEN** 执行一次时钟巡检
- **WHEN** 对比执行前后各节点的状态
- **THEN** 各节点状态 SHALL 保持不变
- **AND** SHALL NOT 在远端写入任何文件
- **AND** SHALL NOT 修改本机任何被观测状态
- **AND** 重复执行 SHALL 得到结构相同的结果

#### Scenario: SC-029

- **GIVEN** 节点清单中存在一个不可达节点
- **WHEN** 执行时钟巡检
- **THEN** 系统 SHALL 完成对其余节点的巡检，SHALL NOT 因单点不可达而中止或崩溃
- **AND** 不可达节点 SHALL 被标记为「无法测量」
- **AND** 命令 SHALL NOT 无限挂起（每个节点 SHALL 有超时）
- **AND** 汇总 SHALL 明确列出哪些节点未能测量

#### Scenario: SC-030

- **GIVEN** 单次采样调用产生了多于一条远端读数
- **WHEN** 统计有效样本数
- **THEN** 计数 SHALL 基于实际收到的有效读数条数
- **AND** SHALL NOT 基于发起的调用次数
- **AND** 重复读数 SHALL NOT 使偏移估计产生系统性偏差
