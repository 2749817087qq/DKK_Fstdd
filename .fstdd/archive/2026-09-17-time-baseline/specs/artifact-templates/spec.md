# Spec: artifact-templates

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: 模板必须同时更新两处来源，使新 change 默认即符合规范

#### Scenario: SC-036

- **GIVEN** 模板字段已更新
- **WHEN** 比较两处同名模板
- **THEN** 两处内容 SHALL 一致
- **AND** 一致性 SHALL 有测试断言覆盖
- **AND** SHALL NOT 只更新其中一处

#### Scenario: SC-037

- **GIVEN** 以更新后的模板创建一个新 change
- **WHEN** 检查该 change 的模板产物
- **THEN** 产物 SHALL 含基线字段与观测时刻字段的占位
- **AND** SHALL 含填写示例或注释，而非仅字段名
- **AND** SHALL NOT 因模板新增字段而使既有解析失败

### Requirement: 新增 CLI 命令必须五处注册齐全并可实际执行

#### Scenario: SC-038

- **GIVEN** 新增了 `baseline` 命令
- **WHEN** 检查 `upstream/fstdd/cli/__init__.py`
- **THEN** 五处 SHALL 同时到位：`COMMAND_GROUPS` / `_CMD_HELP` / `subparsers.add_parser` / 命令分发表 / 命令模块文件
- **AND** 命令分发表中的路径 SHALL 为可导入的 dotted string
- **AND** 命令模块文件 SHALL 存在于对应路径

#### Scenario: SC-039

- **GIVEN** 命令已注册
- **WHEN** 执行 `fstdd baseline --help`
- **THEN** 命令 SHALL 被 CLI 识别并输出帮助
- **AND** 三个动作（`establish` / `show` / `check`）SHALL 各被真实调用一次并返回预期结果
- **AND** 验收 SHALL NOT 以「源码中出现某字符串」作为判据

#### Scenario: SC-040

- **GIVEN** 另一节点 `git pull` 后
- **WHEN** 直接执行新增命令
- **THEN** 命令 SHALL 在无额外安装步骤的情况下可执行
- **AND** 依赖 SHALL 限于 Python 标准库与既有依赖（PyYAML）
- **AND** 缺失配置（如节点清单不存在）时 SHALL 给出明确提示，而非静默失败

### Requirement: 基线配置必须可被外部调整而不改代码

#### Scenario: SC-041

- **GIVEN** 节点清单与巡检参数以配置形式存在
- **WHEN** 修改配置中的节点或阈值
- **THEN** 命令行为 SHALL 随之改变，SHALL NOT 需要改代码
- **AND** 节点清单 SHALL 位于 `.fstdd/config.d/` 下
- **AND** 巡检参数（采样数 / 容差 / 抖动阈值 / 超时）SHALL 位于 `.fstdd/config.d/` 下
- **AND** 配置缺失时 SHALL 使用有文档说明的默认值，或给出明确提示
