# Spec: experience-id-generation

> Change: 2026-10-21-installation-id-prefix | Human View

## Requirements

### Requirement: `_next_id()` SHALL 在 `installation_id` 可用时产出带前缀的 ID

#### Scenario: SC-EID-001

- **GIVEN** 项目 `.fstdd/version.yaml` 含 `installation_id: STDD-A1B2C3D4`
- **WHEN** 调用 `_next_id(index, project_root)`
- **THEN** 返回值 SHALL 为 `STDD-A1B2C3D4-EXP-{year}-{NNNN:04d}`
- **AND** NNNN SHALL 为 index.last_id + 1

#### Scenario: SC-EID-002

- **GIVEN** 项目 `.fstdd/version.yaml` 不存在、无 `installation_id` 字段、或字段值形状非法
- **WHEN** 调用 `_next_id(index, project_root)`
- **THEN** 返回值 SHALL 为 `EXP-{year}-{NNNN:04d}`（旧格式，无前缀）
- **AND** 不得抛异常
- **AND** 不得生成空前缀（如 `-EXP-2026-0001`）
- **AND** 字段值形状非法时（如 `[A, B]` / `../etc/passwd` / `WBCC`）SHALL 向 stderr 出声，
  SHALL NOT 静默回落 —— 否则「配了 ID 却一直产出旧格式」会被当成功能未生效
- **AND** 形状校验 SHALL 复用 `fstdd.cli.utils.INSTALLATION_ID_RE`（与生成端同一常量）

#### Scenario: SC-EID-003

- **GIVEN** `project_root` 参数为 None
- **WHEN** 调用 `_next_id(index, None)`
- **THEN** 返回值 SHALL 为 `EXP-{year}-{NNNN:04d}`（旧格式）

### Requirement: `experience add` 命令产出的经验文件 SHALL 使用带前缀的 ID

#### Scenario: SC-EID-004

- **GIVEN** 项目有 `installation_id: STDD-A1B2C3D4`，index last_id=5
- **WHEN** 执行 `fstdd experience add --pattern 'test' --root-cause 'bug' ...`
- **THEN** 产出文件名 SHALL 含 `STDD-A1B2C3D4-EXP-{year}-0006`
- **AND** frontmatter 的 `experience_id` SHALL 为完整带前缀 ID
- **AND** index 的 last_id SHALL 更新为 6

### Requirement: `_iter_experience_files` SHALL 能识别带前缀的经验文件

#### Scenario: SC-EID-005

- **GIVEN** 经验目录含文件 `STDD-A1B2C3D4-EXP-2026-0001.md`，frontmatter 含
  `experience_id: STDD-A1B2C3D4-EXP-2026-0001`
- **WHEN** 调用 `_iter_experience_files(exp_dir)` 与 `_rebuild_index(exp_dir)`
- **THEN** `_iter_experience_files` SHALL 返回该文件（`Path` 列表）；
  `_rebuild_index` 的 eid 集合 SHALL 含完整带前缀 ID
- **AND** 不得因前缀不符合 `EXP-*` glob 而遗漏
- **AND** `_iter_experience_files` 返回 `Path` 而非 `(eid, data)` 元组 ——
  eid 解析发生在 `_load_experience` / `_rebuild_index` 内
- **AND** 完全无 frontmatter 的 `.md` 会被 `_load_experience` 判为 None 而不进索引
  （2026-09 起既有语义，本 change 不改）

#### Scenario: SC-EID-006

- **GIVEN** 经验目录含文件 `random-name.md`，frontmatter `experience_id: STDD-X-EXP-2026-0001`
- **WHEN** 调用 `_rebuild_index(exp_dir)`
- **THEN** 索引中的 eid SHALL 为 `STDD-X-EXP-2026-0001`（从 frontmatter 取）
- **AND** frontmatter 优先于文件名 stem
- **AND** 索引中 SHALL NOT 出现 `random-name`

### Requirement: `_rebuild_index` SHALL 正确提取带前缀 ID 的数字部分用于 `last_id` 计算

#### Scenario: SC-EID-007

- **GIVEN** 经验目录含 `STDD-A1B2C3D4-EXP-2026-0005.md` 和 `EXP-2026-0003.md`（旧格式共存）
- **WHEN** 调用 `_rebuild_index(exp_dir)`
- **THEN** `last_id` SHALL 为 5（取两者数字部分的最大值）
- **AND** 不得因前缀部分无法解析为数字而报错或跳过
