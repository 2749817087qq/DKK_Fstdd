# Spec: skill-engineering-standards

> Change: 2026-09-15-skill-engineering-standards | Auto-generated Human View

## Requirements

### Requirement: 校验必须验证 CLI 真正可执行，而不只是文件存在

#### Scenario: SC-001

- **GIVEN** 已改造的 verify_workbuddy_skills.py 与可用的 STDD CLI
- **WHEN** 执行该校验脚本
- **THEN** 脚本 SHALL 在临时目录实际执行 stdd 的 init / new / status，并输出冒烟结果
- **AND** 脚本源码中 SHALL 存在 subprocess 调用（计数 > 0）
- **AND** 临时目录 SHALL 在使用后被清理，不得残留

#### Scenario: SC-002

- **GIVEN** CLI 路径被临时替换为不可用（模拟故障）
- **WHEN** 执行校验脚本
- **THEN** 脚本 SHALL 以非 0 退出码结束
- **AND** 输出 SHALL 明确指出是冒烟失败，而非静默通过

### Requirement: 元数据扫描必须如实反映现状，且默认不修改任何文件

#### Scenario: SC-003

- **GIVEN** 本机两个 skill 目录共 40 个 skill
- **WHEN** 执行 check_skill_metadata.py（不带 --fix）
- **THEN** 输出 SHALL 显示 license 缺 37、version 缺 23，与实测一致
- **AND** 全部 40 个 SKILL.md 的内容哈希 SHALL 在运行前后保持一致

#### Scenario: SC-004

- **GIVEN** 执行 check_skill_metadata.py --fix
- **WHEN** 检查备份目录与文件改动
- **THEN** 备份目录中文件数 SHALL 等于待修改文件数，且全部 40 个 skill 四项元数据齐全
- **AND** 每个 SKILL.md 的正文部分（frontmatter 之后）哈希 SHALL 与备份一致
- **AND** 缺失值 SHALL 写入 unknown，不得出现 MIT 等推测值

### Requirement: 安装器生成的 skill 天生满足元数据规范

#### Scenario: SC-005

- **GIVEN** 执行 install_workbuddy_skills.py
- **WHEN** 检查生成的 6 个 SKILL.md 的 frontmatter
- **THEN** 每个 SHALL 包含 name / description / version / license 四项
- **AND** license SHALL 反映该 skill 的真实来源（上游 STDD 为 MIT）

### Requirement: 发布前清单必须可执行、可判据，而非原则性描述

#### Scenario: SC-006

- **GIVEN** 仓库根目录
- **WHEN** 查看 docs/SKILL_RELEASE_CHECKLIST.md
- **THEN** 该文件 SHALL 存在，且含许可、凭证、路径、冒烟、元数据五项检查
- **AND** 每一项 SHALL 给出可执行命令与明确的通过判据（不得只写原则）

### Requirement: 强化校验不得引入假失败

#### Scenario: SC-007

- **GIVEN** 改造完成后的真实环境（CLI 可用、6 个 skill 已安装）
- **WHEN** 执行 verify_workbuddy_skills.py
- **THEN** 脚本 SHALL 输出 PASS 且退出码为 0
- **AND** 输出 SHALL 包含冒烟通过的结果，证明强化项已生效而非被跳过
