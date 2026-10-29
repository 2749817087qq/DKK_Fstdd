# Spec: anti-drift-gates

> Change: 2026-10-28-anti-drift-gates | Auto-generated Human View

## Requirements

### Requirement: 范围锁：`ci check-failures` 的 (b) 检查须基于 change 自己声明的
`scope.paths` 与实际 diff 逐文件比对，而非 capability 名与路径前缀的
模糊匹配。严格度按「是否声明 scope.paths」分界。


#### Scenario: SC-ADG-001

- **GIVEN** change 的 canonical/proposals/*.yaml 声明了 scope.paths: ['upstream/fstdd/cli/commands/ci.py']
- **WHEN** baseline..HEAD 的 diff 含 upstream/fstdd/cli/commands/guard.py（不在 scope 内）
- **THEN** (b) 检查 SHALL 返回 FAIL
- **AND** 结果文本 SHALL 列出越界文件名
- **AND** 结果文本 SHALL 提示「改这里不在本 change 声明范围内」

#### Scenario: SC-ADG-002

- **GIVEN** change 声明了 scope.paths: ['upstream/fstdd/cli/commands/ci.py']
- **WHEN** baseline..HEAD 的 diff 只含 upstream/fstdd/cli/commands/ci.py
- **THEN** (b) 检查 SHALL 返回 PASS
- **AND** 结果文本 SHALL 注明「在声明范围内」

#### Scenario: SC-ADG-003

- **GIVEN** change 的 proposal 未声明 scope.paths
- **WHEN** 执行 ci check-failures
- **THEN** (b) 检查 SHALL 返回 WARN（不是 FAIL，不是 SKIP）
- **AND** 结果文本 SHALL 含「范围锁未生效」与补声明指引

#### Scenario: SC-ADG-004

- **GIVEN** change 的 proposal 未声明 scope.paths
- **WHEN** 执行 ci check-drift --strict
- **THEN** 闸2 结论 SHALL 为 FAIL（WARN 升格）

#### Scenario: SC-ADG-005

- **GIVEN** change 声明 scope.paths: ['upstream/']（覆盖整个内核目录）
- **WHEN** 执行 ci check-failures
- **THEN** (b) 检查 SHALL 返回 WARN 并提示 scope 过宽
- **AND** 空串、'.'、'tests/' 同样触发过宽判定

#### Scenario: SC-ADG-006

- **GIVEN** change 声明 scope.paths 含 '../etc/passwd' 或 'upstream/../.git/'
- **WHEN** 读取 scope 并做范围判定
- **THEN** 含 '..' 的 pattern SHALL 被剔除
- **AND** 剔除动作 SHALL 产生 WARN，说明剔除了哪条

### Requirement: DELIVER 冻结：进入 deliver 相位且 build 已完成时，禁止新增源文件或测试文件。


#### Scenario: SC-ADG-007

- **GIVEN** change 的 current_phase == deliver 且 phases.build.status == completed
- **WHEN** baseline..HEAD 的 diff 含状态 A（新增）的 upstream/fstdd/cli/commands/foo.py
- **THEN** (n) 检查 SHALL 返回 FAIL
- **AND** 结果文本 SHALL 列出新增文件与「收尾阶段禁止新增」的说明
- **AND** 结果文本 SHALL 提示逃生阀 --allow-late-change

#### Scenario: SC-ADG-008

- **GIVEN** change 的 current_phase == deliver 且 build 完成
- **WHEN** baseline..HEAD 的 diff 只含状态 M（修改）的 upstream/fstdd/cli/commands/ci.py
- **THEN** (n) 检查 SHALL 返回 PASS
- **AND** 收尾修 typo / 补文档属正常收尾，不得拦

#### Scenario: SC-ADG-009

- **GIVEN** 同上 SC-ADG-007 的新增源文件情形
- **WHEN** 执行 ci check-failures --allow-late-change '评审要求补一个适配器'
- **THEN** (n) 检查 SHALL 返回 PASS（放行）
- **AND** 放行理由 SHALL 记录到 .fstdd.yaml 的 design_adjustments

#### Scenario: SC-ADG-010

- **GIVEN** change 的 current_phase == deliver 且 build 完成
- **WHEN** baseline..HEAD 的 diff 含状态 A 的 .fstdd/changes/<change>/test-report.md
- **THEN** (n) 检查 SHALL 返回 PASS
- **AND** .fstdd/ 下的归档产出物全豁免

### Requirement: 断言核实：commit message 里出现的版本号须与实际版本一致。


#### Scenario: SC-ADG-011

- **GIVEN** .fstdd/version.yaml 的 fstdd_version == '3.5.0'
- **WHEN** baseline..HEAD 的某条 commit message 含 'v3.4.0 增量'
- **THEN** (o) 检查 SHALL 返回 FAIL
- **AND** 结果文本 SHALL 列出矛盾的两处值（commit 里的 vs version.yaml 的）

#### Scenario: SC-ADG-012

- **GIVEN** .fstdd/version.yaml 的 fstdd_version == '3.5.0'
- **WHEN** 所有 commit message 里的版本号都是 v3.5.0，或不含版本号
- **THEN** (o) 检查 SHALL 返回 PASS

### Requirement: `ci check-drift` 提供三闸聚合报告，供 AI 在 BUILD 末与 DELIVER 前自查。


#### Scenario: SC-ADG-013

- **GIVEN** 存在活跃 change
- **WHEN** 执行 fstdd ci check-drift
- **THEN** stdout SHALL 含三节：闸1 断言证据 / 闸2 范围锁 / 闸3 收尾冻结
- **AND** 每节 SHALL 给出该闸的结论（PASS / WARN / FAIL / SKIP）
- **AND** 任一闸 FAIL 时退出码 SHALL 为 1

#### Scenario: SC-ADG-014

- **GIVEN** 闸2 结论为 WARN（未声明 scope）且其余闸 PASS
- **WHEN** 执行 fstdd ci check-drift --strict
- **THEN** 退出码 SHALL 为 1（WARN 升格为失败）
- **AND** 不加 --strict 时退出码 SHALL 为 0

### Requirement: Gate 确认的 evidence 须含事实标签 `[F]`，否则拒绝（默认强制）。


#### Scenario: SC-ADG-015

- **GIVEN** 执行 fstdd gate approve <change> --gate 2 --confirmed-by dialog --evidence '已完成'
- **WHEN** evidence 不含 [F] 或 [F:来源] 形态标签
- **THEN** 命令 SHALL 拒绝执行并以非 0 退出
- **AND** stdout/stderr SHALL 打印正确写法示例（含 [F] 与 [D] 的用法）
- **AND** Gate 状态 SHALL NOT 被写入（拒绝须是原子的）

#### Scenario: SC-ADG-016

- **GIVEN** evidence 为 '[F:pytest] 9/9 全绿；[D] 由测试结果推出实现正确'
- **WHEN** 执行 gate approve
- **THEN** 命令 SHALL 成功（退出码 0）
- **AND** Gate 状态 SHALL 正常写入

#### Scenario: SC-ADG-017

- **GIVEN** 执行 fstdd gate amend-audit <change> --gate 1 --evidence '补历史追认'（无 [F] 标签）
- **WHEN** evidence 不含事实标签
- **THEN** 命令 SHALL 正常执行（amend-audit 不受标签约束）

### Requirement: 全局候选池 `.fstdd/backlog.md` 作为范围外发现的唯一去处。


#### Scenario: SC-ADG-018

- **GIVEN** 仓库已安装模板
- **WHEN** 比对 .fstdd/templates/backlog.md 与 upstream/.fstdd/templates/backlog.md
- **THEN** 两文件 SHALL 逐字节一致
- **AND** 文件 SHALL 含「## 未处理」与「## 已处理」两节
- **AND** 文件 SHALL 说明条目格式 [<change-id>] 前缀

#### Scenario: SC-ADG-019

- **GIVEN** 执行 fstdd new some-new-change
- **WHEN** 检查新建的 change 目录
- **THEN** 目录 SHALL NOT 含 discoveries.md

#### Scenario: SC-ADG-020

- **GIVEN** phase == deliver，backlog.md 有 3 项未勾选（其中 1 项标 [<本 change>]）
- **WHEN** 执行 ci check-failures
- **THEN** (n) 检查 SHALL 返回 WARN
- **AND** 结果文本 SHALL 分别给出「本 change 引入 N 项」与「历史遗留 M 项」
- **AND** 该 WARN SHALL NOT 阻断（不改变退出码）
