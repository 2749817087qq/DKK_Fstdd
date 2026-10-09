# Spec: archive-state-consistency

> Change: 2026-10-07-change-dir-resolution-unify | Auto-generated Human View

## Requirements

### Requirement: **归档即闭合**：`archive` 命令在成功移动 change 到 `.fstdd/archive/<name>/` 后 SHALL 把
`phases.deliver.status` 置为 `completed`，使归档态不再悬空（`status: archived` 却
`deliver: in_progress|pending`）。该写操作 SHALL 只触及这一个字段 ——
所有闸门审计字段（`phases.*.confirmed_at` / `confirmed_by` / `confirmed_evidence`）
SHALL 逐字段保持不变。


#### Scenario: SC-201

- **GIVEN** 一个处于 `deliver` 相位且 Gate 3 已确认的在办 change（`phases.deliver.status == in_progress`）
- **WHEN** 执行 `fstdd archive <name>` 并成功完成
- **THEN** 归档目录内 `.fstdd.yaml` 的 `phases.deliver.status` SHALL 等于 `completed`
- **AND** `status` SHALL 等于 `archived`
- **AND** 归档目录 SHALL 位于 `.fstdd/archive/<name>/`

#### Scenario: SC-202

- **GIVEN** 一个 Gate 1/2/3 均已确认的在办 change（`phases.*.confirmed_at/by/evidence` 全部有值）
- **WHEN** 执行 `fstdd archive <name>`，并在归档前后读取 `.fstdd.yaml`
- **THEN** 归档后 SHALL 仅 `phases.deliver.status` 与 `status` 两个字段发生变化
- **AND** `phases.understand|spec|build|deliver` 的 `confirmed_at` / `confirmed_by` / `confirmed_evidence` SHALL 与归档前逐字段相等
- **AND** 其余字段（`change_id` / `mode` / `complexity_score` / `traceability` 等）SHALL 逐字段相等

### Requirement: **恢复保留原相位**：`rollback` 把 change 从归档区恢复到 `.fstdd/changes/<name>/` 时，
SHALL 保留其原有 `current_phase`（只把 `status` 置回 `active`），SHALL NOT 无条件重置为
`understand`。由此保证「归档 → 恢复 → 继续推进」的相位接续正确，且不产生
`current_phase` 与 `phases.*.status` 互相矛盾的中间态。`phases.*` 的状态与闸门字段
SHALL 零改动。老数据（无 `current_phase`）SHALL 有确定的兜底取值。


#### Scenario: SC-203

- **GIVEN** 一个归档时 `current_phase` 为 `deliver` 的已归档 change，且 `changes/<name>/` 不存在
- **WHEN** 执行 `fstdd rollback <name>`
- **THEN** 恢复后 `.fstdd.yaml` 的 `current_phase` SHALL 仍为 `deliver`（= 归档前的值）
- **AND** `status` SHALL 等于 `active`
- **AND** 恢复后的目录 SHALL 位于 `.fstdd/changes/<name>/`
- **AND** 输出 SHALL NOT 宣称「current_phase=understand」（除非原值本就是 understand）

#### Scenario: SC-204

- **GIVEN** 一个 Gate 已确认的已归档 change
- **WHEN** 执行 `fstdd rollback <name>`，并在恢复前后读取 `.fstdd.yaml`
- **THEN** 恢复后 `phases.*` 的 `status` 与全部闸门字段 SHALL 与恢复前逐字段相等
- **AND** 仅 `status` 与（必要时）`current_phase` 允许变化

#### Scenario: SC-205

- **GIVEN** 一个在办 change，其 `current_phase` 为 `deliver`
- **WHEN** 依次执行 `archive <name>` → `rollback <name>` → 再次 `archive <name>`
- **THEN** 第二次归档后 SHALL 与第一次归档后状态一致（`deliver: completed`、`current_phase` 不变）
- **AND** 往返过程中 SHALL NOT 出现「changes/ 与 archive/ 同名并存」的中间态残留
- **AND** 第二次 rollback 后 `current_phase` SHALL 仍为 `deliver`
