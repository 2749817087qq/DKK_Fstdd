# Spec: guard-path

> Change: 2026-08-17-v3.0.5-gate-hardening | Auto-generated Human View

## Requirements

### Requirement: guard 增加 --hook-stdin 开关，hook 模式读 stdin JSON 拿目标文件路径

#### Scenario: SC-GUARD-001

- **GIVEN** guard 以 --hook-stdin 模式运行，stdin 传入 JSON {tool_input: {file_path: app/foo.py}}
- **WHEN** 执行 stdd guard check --platform claude-code --hook-stdin
- **THEN** guard SHALL 成功解析目标路径并按其 phase 规则判定
- **AND** stdin 解析失败 SHALL fail-open 返回 0（不误伤编辑）

### Requirement: understand/spec 阶段放行 canonical/ 下的 YAML 流程产出物（修 YAML-first 冲突）

#### Scenario: SC-GUARD-002

- **GIVEN** 一个 active change 处于 understand 阶段（Gate 1 未确认）
- **WHEN** 尝试用 Edit/Write 工具写 changes/<c>/canonical/proposals/<c>.yaml
- **THEN** guard SHALL 返回 0 放行（YAML-first 流程产出物）
- **AND** 同样放行 change 内 design.md/test-plan.md/proposal.md/specs/ 下的流程产出物

#### Scenario: SC-GUARD-003

- **GIVEN** 一个 active change 处于 understand 阶段
- **WHEN** 尝试用 Edit/Write 工具写 app/foo.py（非流程产出物）
- **THEN** guard SHALL 返回 2 阻断（understand 非可编辑阶段）

### Requirement: guard 阻断 AI 直接写 GATE<N>_APPROVED token 文件与篡改 .fstdd.yaml 确认字段

#### Scenario: SC-GUARD-004

- **GIVEN** 任何 phase
- **WHEN** 尝试用 Edit/Write 工具写 changes/<c>/GATE3_APPROVED
- **THEN** guard SHALL 返回 2 阻断（token 必须由用户人工创建）
- **AND** 写 .fstdd.yaml 且内容含 confirmed_at/confirmed_by SHALL 返回 2 阻断

#### Scenario: SC-GUARD-005

- **GIVEN** active change 处于 build 阶段
- **WHEN** 尝试用 Edit/Write 工具写 app/foo.py
- **THEN** guard SHALL 返回 0 放行

### Requirement: guard 阻断范围不得超出项目边界，且 integrity 报错须自带定位信息

#### Scenario: SC-GUARD-006

- **GIVEN** 本项目存在一个 integrity 失败的 active change（如缺 `confirmed_at`）
- **WHEN** hook 模式的目标路径落在**本项目之外**（另一项目目录）
- **THEN** guard SHALL 返回 0 放行（本项目 change 状态对目标文件不适用）
- **AND** SHALL 输出说明该路径不在本项目内的提示
- **AND** GATE token 写入与 `.fstdd.yaml` 确认字段篡改仍 SHALL 返回 2

#### Scenario: SC-GUARD-007

- **GIVEN** 同一个 integrity 失败的 active change
- **WHEN** hook 模式的目标路径落在**本项目之内**（含项目根下的普通文件）
- **THEN** guard SHALL 仍返回 2 阻断（不因 SC-GUARD-006 降低安全强度）

#### Scenario: SC-GUARD-008

- **GIVEN** integrity 校验失败
- **WHEN** guard 输出阻断信息
- **THEN** 信息 SHALL 含 `change_id`，可定位是哪个 change 被卡

### Requirement: Gate 阶段遍历必须有序，报错不得随进程 hash 变化

#### Scenario: SC-GUARD-009

- **GIVEN** 多个 gate 阶段均未确认（如 understand 与 spec 都缺 `confirmed_at`）
- **WHEN** 执行完整性校验
- **THEN** guard SHALL 稳定报出**最靠前**的 gate（Gate 1）
- **AND** 跨进程不同 `PYTHONHASHSEED` 下，报错文本 SHALL 完全一致
- **AND** gate 阶段集合 SHALL 为有序序列，顺序与 `phase_constants.GATE_PHASE_ORDER` 一致

### Requirement: 非法 gate 字段不得冒充确认凭据，且须可诊断

#### Scenario: SC-GUARD-010

- **GIVEN** 某 phase 的 yaml 含手写字段 `gate: approved` 但无 `confirmed_at`
- **WHEN** 执行完整性校验
- **THEN** guard SHALL 判定该 phase **未确认**（`gate` 不是确认凭据）
- **AND** 报错 SHALL 列出该 phase 的实际字段名
- **AND** 报错 SHALL 给出可复制的 `gate approve` 修复命令
- **AND** 报错 SHALL 指出 `gate: approved` 为非法字段并提示删除

#### Scenario: SC-GUARD-011

- **GIVEN** 任何 phase
- **WHEN** 尝试用 Edit/Write 工具写 `.fstdd.yaml` 且内容含 `gate:` 字段（行首缩进后为 `gate:`）
- **THEN** guard SHALL 返回 2 阻断（与 `confirmed_at`/`confirmed_by` 同级）
- **AND** 形如 `gate_notes:` 的非确认字段 SHALL NOT 被误伤

### Requirement: 安装与卸载必须对称（disable 须真能关掉 guard）

#### Scenario: SC-GUARD-012

- **GIVEN** `guard init` 已在 `.claude/` 与 `.codebuddy/` 两处写入 PreToolUse hook
- **WHEN** 执行 `guard disable`
- **THEN** 两处的 guard hook SHALL 均被摘除（不得只处理 `.claude/`）
- **AND** 识别 hook SHALL 依据实际命令内容（`guard check` 等），不得依赖过期标记 `stdd guard`
- **AND** 旧写法（`bin/stdd guard check …`）SHALL 同样能被摘除（向后兼容）
- **AND** `guard enable` 后再 `guard disable` 的往返 SHALL 无残留

#### Scenario: SC-GUARD-013

- **GIVEN** PreToolUse 中除 guard hook 外还有其他 hook 或 `permissions` 配置
- **WHEN** 执行 `guard disable`
- **THEN** SHALL NOT 删除任何非 guard hook
- **AND** SHALL NOT 改动 `permissions` 等其他配置
- **AND** 摘除后若 `hooks` 为空，SHALL 清除空的 `hooks`/`PreToolUse` 骨架

#### Scenario: SC-GUARD-014

- **GIVEN** 已无可摘除的 guard hook，或项目内不存在任何 settings 文件
- **WHEN** 执行 `guard disable`
- **THEN** SHALL 幂等：明确报告「Already disabled」或「Nothing to disable」
- **AND** SHALL NOT 抛出异常

#### Scenario: SC-GUARD-015

- **GIVEN** 任意已安装 guard hook 的项目
- **WHEN** 执行 `guard disable --dry-run`
- **THEN** SHALL 报告将被摘除的位置
- **AND** SHALL NOT 修改任何文件（对齐「预览操作，不实际修改文件系统」）

