# Spec: multi-platform-adapters

> Change: 2026-09-30-multi-platform-adapters | Auto-generated Human View

## Requirements

### Requirement: 多平台适配必须由平台薄清单 platforms.yaml 作为唯一事实源，每平台一条清单描述其 skill 根目录解析规则与 front-matter 规则

#### Scenario: SC-001

- **GIVEN** 仓库需要把同一套 FSTDD 共享正文安装到多个目标平台
- **WHEN** 读取多平台适配的配置来源
- **THEN** 每平台的显示名、skill 根目录解析规则与 front-matter 规则 SHALL 集中在 platforms.yaml 单一声明
- **AND** 正文来源 SHALL 引用仓库共享 skill 正文，SHALL NOT 在清单内复制正文

#### Scenario: SC-002

- **GIVEN** 需要为仓库新增一个目标平台
- **WHEN** 开发者准备让安装层支持该平台
- **THEN** 新增平台 SHALL 只需在 platforms.yaml 增/改一条清单
- **AND** SHALL NOT 需要新增按平台编写的安装代码分支

### Requirement: 安装器 install_workbuddy_skills.py 必须接受 --platform 选择目标平台，并按 platforms.yaml 渲染 front-matter 与输出目录

#### Scenario: SC-003

- **GIVEN** target 平台为 claude-code 且 platforms.yaml 已声明其规则
- **WHEN** 执行安装器并指定 --platform claude-code
- **THEN** 产出 SHALL 落在 `<claude skills 根>/<name>/SKILL.md`
- **AND** 其 front-matter SHALL 符合 Claude Code 规则：不含 version 与 trigger_keywords
- **AND** description SHALL 采用 Claude Code 要求的引号形态

#### Scenario: SC-004

- **GIVEN** 传入的 --platform 值未在 platforms.yaml 中声明
- **WHEN** 执行安装器
- **THEN** 安装器 SHALL 以非零退出码报错并列出可用平台
- **AND** SHALL NOT 静默回退到 workbuddy 或其它平台继续安装

### Requirement: `--platform workbuddy`（含缺省）必须与本次变更前的产出逐字节一致，作为回归保护

#### Scenario: SC-005

- **GIVEN** 在变更前已保存 workbuddy 产出的基准快照
- **WHEN** 以 `--platform workbuddy` 重新安装
- **THEN** 每个 `<name>/SKILL.md` 的字节内容 SHALL 与变更前基准逐字节一致

#### Scenario: SC-006

- **GIVEN** 未显式传入 --platform
- **WHEN** 执行安装器
- **THEN** 行为 SHALL 等同显式 `--platform workbuddy`
- **AND** 默认值 SHALL 在 platforms.yaml 或安装器参数声明中集中定义，不得散落

### Requirement: 实现必须只保留一套共享正文，禁止产出按平台复制的手写正文分支

#### Scenario: SC-007

- **GIVEN** 仓库内存在任一平台的 skill 产出
- **WHEN** 比对任意平台 skill 的正文与仓库共享正文源
- **THEN** 该正文 SHALL 与共享正文源同源可验
- **AND** 仓库内 SHALL NOT 存在第二份按平台复制的手写正文副本

#### Scenario: SC-008

- **GIVEN** 安装层代码已实现多平台支持
- **WHEN** 审查安装层源码
- **THEN** SHALL NOT 存在按平台展开的 if/else 硬编码分支
- **AND** 平台差异 SHALL 全部由 platforms.yaml 数据驱动

### Requirement: 入口脚本 install.sh 与 install.ps1 必须把平台选择透传给安装器

#### Scenario: SC-009

- **GIVEN** 用户在 POSIX shell 环境下执行一键安装
- **WHEN** 执行 `./install.sh --platform <p>`
- **THEN** 脚本 SHALL 把 `<p>` 透传给安装器并据此完成安装与校验
- **AND** 未传 --platform 时 SHALL 保持原有默认行为不变

#### Scenario: SC-010

- **GIVEN** 用户在 Windows PowerShell 环境下执行一键安装
- **WHEN** 执行 `./install.ps1 -Platform <p>`
- **THEN** 脚本 SHALL 把 `<p>` 透传给安装器并据此完成安装与校验
- **AND** 未传 -Platform 时 SHALL 保持原有默认行为不变

### Requirement: 校验脚本必须平台感知，保证装哪平台就校验哪平台

#### Scenario: SC-011

- **GIVEN** 未显式指定平台
- **WHEN** 执行校验脚本
- **THEN** 校验 SHALL 针对 workbuddy 安装点进行
- **AND** 校验判据 SHALL 与安装器共用同一 platforms.yaml 事实源

#### Scenario: SC-012

- **GIVEN** 目标平台为 claude-code 或 trae 且已按该平台安装
- **WHEN** 执行校验脚本并指定该平台
- **THEN** 校验 SHALL 针对该平台的安装点与其 front-matter 规则进行
- **AND** 校验结果 SHALL 能区分『已装且合规』与『未装/不合规』
