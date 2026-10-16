# Spec: canon-merge-automation

> Change: 2026-10-12-canon-merge-command | Auto-generated Human View

## Requirements

### Requirement: `fstdd canon merge <change>` 子命令必须存在；传入 `--dry-run` 时只打印将发生的写操作，不修改文件系统。

#### Scenario: SC-001

- **GIVEN** 一个含 canonical/ 三类文件的 change（在办或已归档）
- **WHEN** 以 `--dry-run` 执行 `fstdd canon merge <change>`
- **THEN** 命令 SHALL 以退出码 0 结束并打印「将写入哪些目标文件、索引如何变化」的决策清单，且 SHALL NOT 创建或修改任何文件（执行前后 `git status --porcelain` 逐字一致）

### Requirement: 「merge 写目标的根 canonical」与「项目级 canonical（canon init/generate 依赖）」是两个不同用途的目录，各自有显式定义点，不互相混用。

#### Scenario: SC-002

- **GIVEN** 项目根目录下存在仓库根 `canonical/`（含 proposals/ 与 specs/）与项目级 `.fstdd/canonical/`
- **WHEN** 分别查询 `_root_canonical_dir(root)`（merge 写目标）与 `_get_canon_dir(root)`（无 change_name，项目级）
- **THEN** `_root_canonical_dir(root)` SHALL 返回 `<project_root>/canonical`（仓库根）；`_get_canon_dir(root)` 无 change_name 时 SHALL 返回 `<project_root>/.fstdd/canonical`（项目级），SHALL NOT 返回仓库根

### Requirement: 连续执行两次不得产生差异；目标已存在且内容不同时必须报错而非静默覆盖。

#### Scenario: SC-003

- **GIVEN** 已成功执行过一次 `canon merge <change>`（目标文件与源逐字节相同、索引条目已登记）
- **WHEN** 再次执行 `fstdd canon merge <change>`（不带 --dry-run）
- **THEN** 第二次 SHALL 以退出码 0 结束，且 `git diff` SHALL 为空（无任何新变更），已存在的目标文件 SHALL NOT 被重写

#### Scenario: SC-003b

- **GIVEN** 根 canonical 中某目标文件已存在，且内容与源**不同**（如根侧有过人工修订）
- **WHEN** 执行 `fstdd canon merge <change>`
- **THEN** 命令 SHALL 以**非 0** 退出码结束，SHALL NOT 覆盖该目标文件，并 SHALL 在输出中说明冲突文件路径与「已写 / 未写哪些」

### Requirement: 目标文件名只能由源文件内的 meta.change_id / meta.capability 决定；缺字段时告警并跳过，不得静默改名或启发式推断。

#### Scenario: SC-005

- **GIVEN** 源 proposals/<change>.yaml 与 specs/agent/<change>.yaml 只有 meta.change_id；specs/code/<cap>.yaml 有 meta.capability
- **WHEN** 执行 `fstdd canon merge <change>`
- **THEN** proposal 与 agent spec SHALL 以 meta.change_id 为目标文件名，code spec SHALL 以 meta.capability 为目标文件名，且 SHALL NOT 由人工或命令行参数决定

#### Scenario: SC-005b

- **GIVEN** 某个源文件**缺少**其对应的元数据字段（如 code spec 无 meta.capability）
- **WHEN** 执行 `fstdd canon merge <change>`
- **THEN** 命令 SHALL 为该文件输出含文件路径的**告警**并将其**跳过**，SHALL NOT 静默改名、SHALL NOT 据内容推断名字；退出码 SHALL 为非 0（因为有未合并项）

### Requirement: DELIVER 的时序是先归档再合并，故 merge 必须能解析已归档 change 的 canonical。

#### Scenario: SC-006

- **GIVEN** 目标 change 已通过 `fstdd archive` 归档到 `.fstdd/archive/<change>/`
- **WHEN** 执行 `fstdd canon merge <change>`
- **THEN** 命令 SHALL 正确定位到 archive/<change>/canonical/ 并完成合并，SHALL NOT 以「已归档」为由拒绝

### Requirement: 本 change 修改 vendored 内核，动手前必须在 docs/UPSTREAM_PATCHES.md 表体正式登记。

#### Scenario: SC-007

- **GIVEN** `docs/UPSTREAM_PATCHES.md` 表体在改动前为空（仅「待登记」区 2 条）
- **WHEN** 本 change 的 upstream 改动落地时
- **THEN** 表体 SHALL 含本 change 的登记行，且 8 列（文件 / 行号 / 修改原因 / 关联上游 issue-PR / 登记日期 / 登记人 / 预期回退版本）SHALL 全部非空；「待登记」区既有两条 SHALL 原样保留

### Requirement: canon init / generate / verify 的行为与既有测试不得被破坏；CLI 解析面不得回归。

#### Scenario: SC-008

- **GIVEN** 本 change 的全部改动已落地
- **WHEN** 跑既有 canon 相关测试 + 全量根级与框架侧测试 + CLI 冒烟（--help / init / new / status）
- **THEN** 上述测试 SHALL 0 failed（既有失败须逐条归因）；除 --dry-run 外不得有行为变化

### Requirement: change 名来自用户输入，必须经统一解析入口且内置穿越防护；不得自建解析器。

#### Scenario: SC-009

- **GIVEN** 用户传入含路径分隔符或 `..` 的 change 名（如 ../../x、a/b）
- **WHEN** 执行 `fstdd canon merge <that name>`
- **THEN** 命令 SHALL 以非 0 退出码结束并报「找不到 change」，SHALL NOT 解析到 changes/ 或 archive/ 之外的任何路径，SHALL NOT 写入任何文件

#### Scenario: SC-009b

- **GIVEN** 用户传入**合法**的 change 名（含连字符、点、数字，如 2026-10-12-test-teardown-resilience）
- **WHEN** 执行 `fstdd canon merge <that name>`
- **THEN** 命令 SHALL 正常解析并合并，不得因输入校验过紧而误拒

### Requirement: 测试必须断言 merge 路径**调用**了统一解析入口，而非仅在模块顶部 import。

#### Scenario: SC-010

- **GIVEN** `canon.py` 的源码
- **WHEN** 检查 merge 相关函数体内是否出现对 find_change_dir / _resolve_change_dir 的**调用**
- **THEN** SHALL 存在该调用；且 SHALL NOT 存在第二套自行拼接 `.fstdd/changes/<name>` 的解析逻辑
