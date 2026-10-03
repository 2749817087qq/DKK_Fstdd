# Spec: phase-gate-path-scope

> Change: 2026-09-25-guard-phase-path-scope | Auto-generated Human View

## Requirements

### Requirement: 相位门 SHALL 按 change 声明的文件作用域判定拦截范围，而非全项目粒度

#### Scenario: SC-001

- **GIVEN** ACTIVE_CHANGE 处于只读相位（understand/spec）且其 proposal 声明了 scope.paths
- **WHEN** 编辑目标文件归一化后落在 scope.paths 内
- **THEN** SHALL 拦截并返回 exit 2，提示扩展 scope.paths

#### Scenario: SC-002

- **GIVEN** ACTIVE_CHANGE 处于只读相位且其 proposal 声明了 scope.paths
- **WHEN** 编辑目标文件归一化后不在 scope.paths 内
- **THEN** SHALL 打印 warn-only 提示并返回 exit 0 放行

### Requirement: 未声明作用域的 change SHALL 保持既有全局拦截行为（fail-closed）

#### Scenario: SC-003

- **GIVEN** ACTIVE_CHANGE 处于只读相位且 proposal 无 scope 块或 paths 为空
- **WHEN** 编辑任意项目内文件
- **THEN** SHALL 返回 exit 2（与现状行为逐字一致，无行为漂移）

### Requirement: 两道硬阻断 SHALL 不受作用域收窄影响，保持全局粒度

#### Scenario: SC-004

- **GIVEN** change 已声明 scope 且目标文件为 GATE<N>_APPROVED token
- **WHEN** 任何相位下尝试写入该 token
- **THEN** SHALL 返回 exit 2 硬阻断

#### Scenario: SC-005

- **GIVEN** change 已声明 scope 且目标文件为 .fstdd.yaml 含 confirmed_* 字段
- **WHEN** 尝试直接修改确认字段
- **THEN** SHALL 返回 exit 2 硬阻断

### Requirement: 路径判定 SHALL 先归一化再匹配，越界路径视为范围外

#### Scenario: SC-006

- **GIVEN** change 已声明 scope 且处于只读相位
- **WHEN** 目标路径经 normpath 后无法 relative_to(project_root)（如 .. 穿越出项目根）
- **THEN** SHALL 视为范围外，走 warn-only 放行

#### Scenario: SC-007

- **GIVEN** scope.paths 含目录模式（以 / 结尾）
- **WHEN** 编辑该目录下的任意文件
- **THEN** SHALL 判定为范围内（拦截）

### Requirement: 既有放行通道 SHALL 完全不变

#### Scenario: SC-008

- **GIVEN** 只读相位下编辑 change 内 YAML-first 流程产物（canonical/ 或 design.md 等）
- **WHEN** 触发 guard check
- **THEN** SHALL 返回 exit 0（行为与现状逐字一致）

#### Scenario: SC-009

- **GIVEN** ACTIVE_CHANGE 处于可编辑相位（build/deliver）
- **WHEN** 编辑任意项目文件
- **THEN** SHALL 返回 exit 0（不受 scope 影响）

#### Scenario: SC-010

- **GIVEN** 目标路径位于 .workbuddy-ai/ 下
- **WHEN** 任何相位下编辑
- **THEN** SHALL 返回 exit 0（agent runtime 豁免不受 scope 影响）
