# Spec: time-baseline

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: 每个 change 必须携带显式时间基线，且四项非空

#### Scenario: SC-001

- **GIVEN** 一个 change 已经过 Gate 1 确认
- **WHEN** 读取其 `.fstdd.yaml`
- **THEN** 文件 SHALL 含 `baseline` 块，且包含 `at` / `base_git_sha` / `node_id` / `clock_source` 四项
- **AND** 四项 SHALL 均非空（不得为 null / 空字符串）
- **AND** `at` SHALL 是带时区的 ISO 8601（匹配 `([+-]\d{2}:\d{2}|Z)$`）
- **AND** `node_id` SHALL 为建立基线的节点标识

#### Scenario: SC-002

- **GIVEN** 某 change 的 `baseline` 块已存在且四项非空
- **WHEN** 再次执行基线建立（不带 `--force`）
- **THEN** 系统 SHALL 保持既有四项取值不变
- **AND** 命令 SHALL NOT 报错
- **AND** 命令 SHALL 以退出码 0 结束
- **AND** 输出 SHALL 报告「已存在，未改写」

#### Scenario: SC-003

- **GIVEN** 某 change 的基线已建立
- **WHEN** 执行 `fstdd baseline show <change>`
- **THEN** 系统 SHALL 输出该 change 的基线四项
- **AND** `--format json` SHALL 输出可被程序解析的结构
- **AND** 输出 SHALL 包含 `base_git_sha`，使「基于哪个状态」可被读取

### Requirement: 基线必须锚定代码状态，且锚点可被 git 定位

#### Scenario: SC-004

- **GIVEN** 在 HEAD 为 `<sha>` 的工作区建立基线
- **WHEN** 读取 `baseline.base_git_sha`
- **THEN** 该值 SHALL 与建立时刻的 `git rev-parse HEAD` 一致
- **AND** 短 sha 与完整 sha SHALL 可互相校验（短 sha 是完整 sha 的前缀）

#### Scenario: SC-005

- **GIVEN** `baseline.base_git_sha` 已记录
- **WHEN** 以该值在仓库中执行 `git log` 查询
- **THEN** 系统 SHALL 能定位到对应的提交
- **AND** 该提交 SHALL 是建立基线时 HEAD 的祖先或自身

### Requirement: 回填基线时不得伪造时刻

#### Scenario: SC-006

- **GIVEN** 某 change 的 Gate 1 已确认但缺 `baseline` 块
- **WHEN** 执行回填
- **THEN** `baseline.at` SHALL 等于该 change 的 `phases.understand.confirmed_at`
- **AND** `baseline.at` SHALL NOT 取回填动作发生的时刻
- **AND** 回填 SHALL 幂等

#### Scenario: SC-007

- **GIVEN** 基线由不同途径建立
- **WHEN** 读取 `baseline.established_by`
- **THEN** 该字段 SHALL 标明建立途径（`gate1` / `cli` / `backfill`）
- **AND** 三种取值 SHALL 可区分
- **AND** `clock_source` SHALL 标明时间来源（`system` / `hub` / `manual`）

### Requirement: 基线完整性必须可被机器检查，且检查不阻断既有 change

#### Scenario: SC-008

- **GIVEN** 一个 change 缺 `baseline` 块或其四项有空值
- **WHEN** 执行 `fstdd validate <change>`
- **THEN** 系统 SHALL 报告基线缺失或不完整
- **AND** 该报告 SHALL 为 warning 级，SHALL NOT 使校验失败
- **AND** 退出码 SHALL 保持校验通过时的取值

#### Scenario: SC-009

- **GIVEN** 以 `--check` 模式执行基线查询
- **WHEN** 基线完整
- **THEN** 系统 SHALL 以退出码 0 结束
- **AND** 基线缺失或不完整时 SHALL 以非 0 退出码结束
- **AND** 输出 SHALL 可被脚本直接判定，无需人工解读
