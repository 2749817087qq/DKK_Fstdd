# Spec: change-dir-resolution

> Change: 2026-09-26-finder-archive-fallback | Auto-generated Human View

## Requirements

### Requirement: change 目录统一解析：支持可选归档回退，且默认行为零漂移

#### Scenario: SC-001

- **GIVEN** change 只存在于 .fstdd/archive/ 下，changes/ 下没有
- **WHEN** 调用 find_change_dir(name, root) 且**不传** include_archive
- **THEN** SHALL 返回 None —— 默认语义仍是「只查在办」，既有调用点逐字零漂移

#### Scenario: SC-002

- **GIVEN** change 只存在于 .fstdd/archive/ 下
- **WHEN** 调用 find_change_dir(name, root, include_archive=True)
- **THEN** SHALL 返回 .fstdd/archive/<name> 且该目录含 .fstdd.yaml

#### Scenario: SC-003

- **GIVEN** 同名 change 同时存在于 changes/ 与 archive/（如 rollback 后残留）
- **WHEN** 调用 find_change_dir(name, root, include_archive=True)
- **THEN** SHALL 返回 changes/<name> —— 在办优先于归档

#### Scenario: SC-004

- **GIVEN** archive/ 下存在 2026-01-01-archived-feature
- **WHEN** 调用 find_change_dir('archived-feature', root, include_archive=True)（短名后缀匹配）
- **THEN** SHALL 命中 archive/2026-01-01-archived-feature —— 后缀匹配在归档区同样生效

#### Scenario: SC-005

- **GIVEN** changes/ 与 archive/ 下都有带 .fstdd.yaml 的 change
- **WHEN** 调用 find_change_dir(None, root, include_archive=True)（不指定名字）
- **THEN** SHALL 只返回 changes/ 下最近修改的那个 —— 「当前 change」语义上不可能位于归档区

#### Scenario: SC-006

- **GIVEN** 项目只有 changes/ 没有 archive/
- **WHEN** 调用 find_change_dir(name, root, include_archive=True)
- **THEN** SHALL 正常返回或返回 None，**不得抛异常**

### Requirement: 归档后四条命令不再因「找不到 change」失败

#### Scenario: SC-007

- **GIVEN** change 已归档至 .fstdd/archive/<name>/
- **WHEN** 执行 stdd validate <name>
- **THEN** SHALL 以 rc=0 完成校验（修复前 rc=1「找不到 change」）

#### Scenario: SC-008

- **GIVEN** change 已归档
- **WHEN** 执行 stdd status <name>
- **THEN** SHALL 以 rc=0 输出该 change 状态（修复前 rc=1「找不到 change」）

#### Scenario: SC-009

- **GIVEN** change 已归档，且其 canonical/proposals/<name>.yaml 完整
- **WHEN** 执行 stdd canon verify <name>
- **THEN** SHALL 以 rc=0 完成校验并输出通过项（修复前 rc=1「canonical/proposals/... not found」）

#### Scenario: SC-010

- **GIVEN** change 已归档，且其 code-structure-delta.md 存在
- **WHEN** 执行 stdd structure merge <name>
- **THEN** SHALL 读取到该 delta 而不再报「Delta not found」（修复前 rc=1）

### Requirement: 归档相关既有行为零漂移（反例守卫）

#### Scenario: SC-011

- **GIVEN** change 已归档至 archive/，changes/ 下已无该目录
- **WHEN** 再次执行 stdd archive <name>
- **THEN** SHALL 以非 0 退出并报找不到 change —— **不得**解析到 archive/ 后把自己再移动一次

#### Scenario: SC-012

- **GIVEN** change 已归档至 archive/
- **WHEN** 执行 stdd rollback <name>
- **THEN** SHALL 仍能把该 change 从 archive/ 恢复到 changes/（既有逻辑不回归）

#### Scenario: SC-013

- **GIVEN** 未归档的 change 位于 changes/
- **WHEN** 执行 stdd archive <name>
- **THEN** SHALL 正常归档（既有行为不回归）
