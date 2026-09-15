# Spec: bootcamp-system (NEW)

> V3.0.x | 训练营 CLI + 5 关训练矩阵 + 自动评分引擎

## ADDED Requirements

### Requirement: stdd bootcamp start 启动训练

系统 SHALL 支持 stdd bootcamp start 命令，从第 1 关开始或从上次中断处继续。

#### Scenario: 首次启动从第 1 关开始
- **GIVEN** 项目已安装 STDD V3.0.x
- **AND** .stdd/.bootcamp_certified 不存在
- **WHEN** 执行 stdd bootcamp start
- **THEN** 系统 SHALL 加载第 1 关训练场景
- **AND** SHALL 展示关卡说明和考评标准
- **AND** SHALL 引导 AI 完成训练任务

#### Scenario: 已通过部分关卡时继续
- **GIVEN** .stdd/.bootcamp_certified 标记为 basic（通过 1-2 关）
- **WHEN** 执行 stdd bootcamp start
- **THEN** 系统 SHALL 从第 3 关继续

#### Scenario: 全部通过时提示
- **GIVEN** .stdd/.bootcamp_certified 标记为 full
- **WHEN** 执行 stdd bootcamp start
- **THEN** 系统 SHALL 输出已毕业提示
- **AND** SHALL 退出码为 0

### Requirement: stdd bootcamp status 查看进度

系统 SHALL 支持 stdd bootcamp status 命令展示当前训练进度。

#### Scenario: 查看进度
- **GIVEN** 已通过第 1 关（6/10），第 2 关进行中
- **WHEN** 执行 stdd bootcamp status
- **THEN** SHALL 展示各关卡状态、得分、毕业等级

### Requirement: stdd bootcamp retry 重试

系统 SHALL 支持 stdd bootcamp retry N 重试指定关卡。

#### Scenario: 重试失败关卡
- **GIVEN** 第 2 关得分 4/10（不及格）
- **WHEN** 执行 stdd bootcamp retry 2
- **THEN** 系统 SHALL 重新加载第 2 关场景
- **AND** 重试次数 SHALL ≤ 3

### Requirement: 5 关训练矩阵

系统 SHALL 提供 5 个训练关卡，每关包含场景文件 + 标准答案 + 考评标准。

#### Scenario: 第 1 关 — lightweight code
- **GIVEN** 加载第 1 关
- **WHEN** AI 执行训练
- **THEN** 考评 SHALL 包含：phase advance CLI / gate approve CLI / 不手动改 yaml / archive CLI

#### Scenario: 第 2 关 — standard code
- **GIVEN** 加载第 2 关
- **WHEN** AI 执行训练
- **THEN** 考评 SHALL 包含：design.md / specs/ / test-plan.md / Canonical YAML / SLICE / 模式选择

#### Scenario: 第 3 关 — thorough code
- **GIVEN** 加载第 3 关
- **WHEN** AI 执行训练
- **THEN** 考评 SHALL 包含：长程模式 / 锚定 L2-L4 / per-slice 证据链 / 14 类失败检查 / Gate 3

#### Scenario: 第 4 关 — agent
- **GIVEN** 加载第 4 关
- **WHEN** AI 执行训练
- **THEN** 考评 SHALL 包含：agent_spec.yaml / CP / cross_check / Bash 在 Change 内

#### Scenario: 第 5 关 — 综合实战
- **GIVEN** 加载第 5 关
- **WHEN** AI 执行训练
- **THEN** 考评 SHALL 包含：多 capability + 经验记录 + 知识图谱 + Gate 1-3 全链路

### Requirement: 自动评分引擎

系统 SHALL 提供自动评分引擎，对比 AI 产出与标准答案。

#### Scenario: 文件存在性评分
- **GIVEN** 训练任务要求产出 proposal.md
- **WHEN** 评分
- **THEN** 文件存在得分 2 分，不存在 0 分

#### Scenario: 格式校验评分
- **GIVEN** spec.md 存在但缺少 SHALL 关键字
- **WHEN** 评分
- **THEN** 格式不符合得分 0 分，符合得分 3 分

### Requirement: 三级毕业标记

系统 SHALL 写入 .stdd/.bootcamp_certified 文件记录毕业等级。

#### Scenario: basic 毕业
- **GIVEN** 第 1-2 关全部通过（≥6/10）
- **WHEN** 完成训练
- **THEN** .stdd/.bootcamp_certified SHALL 标记 level: basic

#### Scenario: advanced 毕业
- **GIVEN** 第 1-4 关全部通过
- **WHEN** 完成训练
- **THEN** .stdd/.bootcamp_certified SHALL 标记 level: advanced

#### Scenario: full 毕业
- **GIVEN** 第 1-5 关全部通过
- **WHEN** 完成训练
- **THEN** .stdd/.bootcamp_certified SHALL 标记 level: full
