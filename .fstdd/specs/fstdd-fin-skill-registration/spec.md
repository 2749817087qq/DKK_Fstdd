# Spec: fstdd-fin-skill-registration

> Change: 2026-10-03-finance-integration | Auto-generated Human View

## Requirements

### Requirement: fstdd-fin SKILL.md 从 _scratch 游离位置回归主 skills/ 目录

#### Scenario: SC-001

- **GIVEN** _scratch/stdd-dev/stdd-repo/skills/fstdd-fin/SKILL.md 存在且 sha256=已知
- **WHEN** 执行资产回归：复制到 skills/fstdd-fin/SKILL.md
- **THEN** skills/fstdd-fin/SKILL.md SHALL 存在且与源文件 sha256 完全匹配
- **AND** 源文件在 _scratch/ 保留（作为备份）

### Requirement: install_workbuddy_skills.py 注册 fstdd-fin 的 source 路径和 install 输出

#### Scenario: SC-002

- **GIVEN** install_workbuddy_skills.py 含 source_paths 列表和 install 输出循环
- **WHEN** 在 source_paths 列表追加 fstdd-fin 条目
- **THEN** install_workbuddy_skills.py SHALL 包含 fstdd-fin 的 source 路径声明
- **AND** fstdd-fin 与 fstdd/understand/spec/build/deliver/upgrade 并列，同级安装

### Requirement: platforms.yaml 注册 fstdd-fin 为第 7 个 skill

#### Scenario: SC-003

- **GIVEN** platforms.yaml 当前注册 6 个 skill
- **WHEN** 追加 fstdd-fin skill 条目
- **THEN** platforms.yaml SHALL 包含 fstdd-fin 条目，name=skills/fstdd-fin, path=skills/fstdd-fin
