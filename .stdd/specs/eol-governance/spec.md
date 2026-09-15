# Spec: eol-governance

> Change: 2026-09-15-crlf-eol-governance | Auto-generated Human View

## Requirements

### Requirement: 仓库必须在根目录声明明确的 EOL 规则，覆盖包括 upstream/ 在内的所有子目录

#### Scenario: SC-001

- **GIVEN** 一个已 clone 的 stdd-repo 仓库工作副本
- **WHEN** 读取仓库根目录的 .gitattributes 文件
- **THEN** 该文件 SHALL 存在，且内容 SHALL 为 `* text=auto eol=lf`
- **AND** 该规则 SHALL 对 upstream/ 子目录同样生效（Git 属性按路径递归匹配）
- **AND** 仓库的 .git/info/attributes SHALL 不存在（避免与入库规则冲突）

#### Scenario: SC-002

- **GIVEN** 一个干净的临时 Git 仓库，core.autocrlf=true，含 670 个 LF 行尾的文件
- **WHEN** 在该仓库执行 git add -A
- **THEN** stderr 中 'LF will be replaced by CRLF' 告警行数 SHALL 为 0
- **AND** 作为对照：相同文件集在无 .gitattributes 时实测告警为 640 行

### Requirement: 应用规则后，仓库的行尾状态必须在索引与工作区之间保持一致

#### Scenario: SC-003

- **GIVEN** 已应用 .gitattributes 规则并完成工作区重建的 stdd-repo
- **WHEN** 执行 git ls-files --eol 并统计 i/lf 与 w/crlf 同时出现的文件
- **THEN** 该类混合态文件数 SHALL 为 0
- **AND** 修复前实测值为 4（docs/WORKBUDDY_INSTALL_NOTES.md、skills/stdd-fin/SKILL.md、tools/verify_workbuddy_skills.py、upstream/.gitignore）

#### Scenario: SC-004

- **GIVEN** 已完成本变更的 stdd-repo
- **WHEN** 执行 git ls-files --eol 并统计 i/crlf 状态的索引项
- **THEN** 索引中 i/crlf 文件数 SHALL 为 0
- **AND** 此断言用于拦截 `* -text` 类规则误用导致的索引行尾翻转（实测该误用会产生 4 个 i/crlf）

#### Scenario: SC-005

- **GIVEN** 应用规则并执行 git add --renormalize . 之后
- **WHEN** 执行 git diff --cached --stat 查看索引相对 HEAD 的变更
- **THEN** 变更文件数 SHALL 为 0
- **AND** 此断言证明本变更仅归一工作区行尾，未改动任何文件的实质内容

### Requirement: EOL 治理不得破坏仓库内脚本的可执行性

#### Scenario: SC-006

- **GIVEN** 已完成本变更，且 upstream/bin/stdd 检出于工作区
- **WHEN** 检查该文件的行尾并执行 stdd init / new / status
- **THEN** 该文件行尾 SHALL 为 LF（不含 \r），且三个子命令 SHALL 均正常返回
- **AND** 文件首行 shebang SHALL 不以 \r 结尾

### Requirement: EOL 策略须在文档中可查，便于后续维护者理解与排障

#### Scenario: SC-007

- **GIVEN** 已完成本变更的 stdd-repo
- **WHEN** 查看 README 的「故障排除」章节
- **THEN** 该章节 SHALL 包含 .gitattributes 的作用说明
- **AND** 该章节 SHALL 包含批量 add 时的建议做法
