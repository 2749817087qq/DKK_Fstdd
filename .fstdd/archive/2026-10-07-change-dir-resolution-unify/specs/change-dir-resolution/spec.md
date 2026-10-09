# Spec: change-dir-resolution

> Change: 2026-10-07-change-dir-resolution-unify | Auto-generated Human View

## Requirements

### Requirement: **读路径**：接受 change 名的命令 SHALL 统一经 `finder.find_change_dir(name, root, include_archive=True)`
解析，因此对**已归档** change 的只读操作 SHALL 正常完成（rc=0）并输出该 change 的真实信息，
SHALL NOT 报 `.fstdd.yaml not found`。
覆盖范围（本 change 新纳入的 5 个模块的读分支）：`phase status` / `state`（查看与 `--resume`）/
`work list` / `baseline` 读路径 / `gate` 查询。


#### Scenario: SC-101

- **GIVEN** change 已归档至 `.fstdd/archive/<name>/`，`.fstdd/changes/<name>/` 不存在
- **WHEN** 执行 `fstdd phase status <name>`
- **THEN** SHALL 以 rc=0 输出该 change 的当前相位与各相位状态
- **AND** 输出 SHALL NOT 含 `.fstdd.yaml not found`
- **AND** 输出 SHALL 含该 change 的真实目录名

#### Scenario: SC-102

- **GIVEN** change 已归档至 `.fstdd/archive/<name>/`
- **WHEN** 执行 `fstdd state <name>`（只读查看）与 `fstdd state <name> --resume`
- **THEN** SHALL 以 rc=0 输出该 change 的状态摘要
- **AND** 输出 SHALL NOT 含 `.fstdd.yaml not found`

#### Scenario: SC-103

- **GIVEN** change 已归档至 `.fstdd/archive/<name>/`
- **WHEN** 执行 `fstdd work list <name>`
- **THEN** SHALL 以 rc=0 输出该 change 的关联工作记录（无记录时输出空列表提示）
- **AND** 输出 SHALL NOT 含 `.fstdd.yaml not found`

#### Scenario: SC-104

- **GIVEN** change 以 `YYYY-MM-DD-<短名>` 形式归档，用户只记得短名
- **WHEN** 执行 `fstdd phase status <短名>`（或 `state` / `work list` 同形调用）
- **THEN** SHALL 经后缀匹配命中 `archive/YYYY-MM-DD-<短名>` 并正常输出
- **AND** 命中过程 SHALL NOT 因「changes/ 下无同名」而提前失败

### Requirement: **写路径**：对**已归档** change 的写操作 SHALL 被拒绝（非 0 退出码），并输出**准确可操作**的
文案（含「已归档」状态词 + 归档实际路径 + `rollback` 出口指引），SHALL NOT 复用
「未找到」类误导文案。**例外**：`gate amend-audit` 的设计用途即「事后追认归档 Gate」，
SHALL 对归档 change 放行。
在办（active）change 上的读写行为 SHALL 零漂移。


#### Scenario: SC-105

- **GIVEN** change 已归档，且其 `phases.deliver.status` 未闭合
- **WHEN** 执行 `fstdd phase advance <name>`（或 `phase set` / `phase record-slice`）
- **THEN** SHALL 以非 0 退出码拒绝执行，且**不得**改写 `.fstdd/archive/<name>/.fstdd.yaml`
- **AND** 输出 SHALL 含「已归档」字样
- **AND** 输出 SHALL 含 `rollback` 字样
- **AND** 输出 SHALL 含该 change 在 `.fstdd/archive/` 下的实际路径

#### Scenario: SC-106

- **GIVEN** change 已归档
- **WHEN** 分别执行 `fstdd state <name> --set current_phase=spec`、`fstdd work add <name> --type doc "x"`、`fstdd baseline establish <name>`
- **THEN** 三者 SHALL 均以非 0 退出码拒绝，且各自输出含「已归档」与 `rollback` 字样
- **AND** 拒绝时 SHALL NOT 在 `archive/<name>/` 内产生任何文件写入

#### Scenario: SC-107

- **GIVEN** change 已归档
- **WHEN** 执行 `fstdd gate amend-audit <name> --gate <N> --confirmed-by cli --evidence <文本>`
- **THEN** SHALL 正常执行（rc=0），并按既有逻辑追加追认审计记录
- **AND** 其行为 SHALL 与在办 change 上一致（同一命令、同一参数形态）

#### Scenario: SC-108

- **GIVEN** change 位于 `.fstdd/changes/<name>/`（在办）
- **WHEN** 执行读路径（`phase status` / `state` / `work list`）与写路径（`phase advance` / `state --set` / `work add`）各一次
- **THEN** SHALL 与修复前行为逐字一致（读 rc=0；写正常落盘）
- **AND** SHALL NOT 出现「已归档」字样

### Requirement: **单一入口**：全仓「接受 change 名」的命令模块 SHALL 一律经 `finder` 的统一入口
（`find_change_dir` 或 `require_active_change_dir`）解析，SHALL NOT 保留自建解析实现。
该约束 SHALL 由**静态契约扫描**锚定，且扫描器 SHALL 自带双向自检。
**且**静态判据为模块级、存在固有上限（EXP-2026-0024），故 SHALL 同时以**逐命令行为断言**作第二层防线。


#### Scenario: SC-109

- **GIVEN** 全仓 `upstream/fstdd/cli/commands/*.py` 与 `upstream/fstdd/cli/finder.py`
- **WHEN** 执行契约扫描：凡「接受 change 名」的模块必须出现统一入口调用
- **THEN** SHALL 报出违规模块数 = 0
- **AND** 扫描判据 SHALL 基于 AST（结构化），SHALL NOT 用字符串子串匹配
- **AND** 扫描 SHALL 覆盖 `phase` / `gate` / `state` / `work` / `baseline` 五个本 change 修复的模块

#### Scenario: SC-110

- **GIVEN** 扫描器实现
- **WHEN** 分别对「自建解析器」违例样本与「走统一入口」合法样本执行扫描
- **THEN** 违例样本 SHALL 被判违规；合法样本 SHALL NOT 被判违规
- **AND** 另需覆盖「注释里提到 find_change_dir 但代码未调用」的反例（SHALL 判违规）
