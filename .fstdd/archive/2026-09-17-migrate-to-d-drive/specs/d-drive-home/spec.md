# Spec: d-drive-home

> Change: 2026-09-17-migrate-to-d-drive | Auto-generated Human View

## Requirements

### Requirement: 全部 FSTDD 资产必须完整迁移到 D 盘，不随 C 盘系统重装丢失

#### Scenario: SC-001

- **GIVEN** C 盘工作区（stdd-repo + backups + .workbuddy-ai + 根文件）
- **WHEN** 整体复制到 `D:/tools/FSTDD/`
- **THEN** D 盘副本的文件数 SHALL 与 C 盘一致
- **AND** 逐文件哈希 SHALL 一致
- **AND** 目录结构 SHALL 一致（镜像而非只搬仓库）

#### Scenario: SC-002

- **GIVEN** `D:/tools/FSTDD/stdd-repo`
- **WHEN** 检查其 git 状态
- **THEN** HEAD / 分支 / tag `fstdd-v1.0.0` / remote SHALL 与 C 盘一致
- **AND** 工作区 SHALL 干净（无未提交改动）

#### Scenario: SC-003

- **GIVEN** 迁移完成后
- **WHEN** 检查 C 盘工作区
- **THEN** SHALL 仍完整存在，文件数不变
- **AND** SHALL NOT 被删除或清空

### Requirement: D 盘必须成为新的法定源，环境自洽

#### Scenario: SC-004

- **GIVEN** `D:/tools/FSTDD/stdd-repo`
- **WHEN** 从该位置运行三项校验
- **THEN** `verify_eol` SHALL 7/7、`verify_skill_standards` SHALL 7/7、`verify_rename` SHALL 8/8
- **AND** 校验脚本的路径解析 SHALL 自适配到 D 盘（基于 `__file__`，不硬编码 C 盘）

#### Scenario: SC-005

- **GIVEN** `D:/tools/FSTDD/stdd-repo`
- **WHEN** 从该位置运行全量测试
- **THEN** SHALL 543 passed，无回归
- **AND** SHALL NOT 因路径变化而出现新增失败

#### Scenario: SC-006

- **GIVEN** `D:/tools/FSTDD/stdd-repo/tools/install_workbuddy_skills.py`
- **WHEN** 从该位置执行安装（不设 `FSTDD_SRC`）
- **THEN** SRC SHALL 解析为 `D:/tools/FSTDD/stdd-repo/upstream`
- **AND** SHALL NOT 解析到 C 盘路径

### Requirement: 已安装 skill 的固化路径必须指向 D 盘

#### Scenario: SC-007

- **GIVEN** 从 D 盘重装后的 `~/.workbuddy/skills/fstdd*/SKILL.md`
- **WHEN** 检查其中的绝对路径
- **THEN** SHALL 指向 `D:/tools/FSTDD/stdd-repo`
- **AND** SHALL NOT 含 C 盘工作区路径（`WorkBuddy AI/2026-…`）
- **AND** `verify_workbuddy_skills.py` SHALL 全绿

### Requirement: 文档与记忆必须反映新位置

#### Scenario: SC-008

- **GIVEN** `docs/WORKBUDDY_INSTALL_NOTES.md`
- **WHEN** 阅读第 0 节
- **THEN** 法定源 SHALL 写为 `D:/tools/FSTDD/stdd-repo`
- **AND** SHALL 说明 C 盘工作区保留作历史归档
- **AND** SHALL 保留「GitHub 是上传目标」与「`D:/Programs/DKK_Fstdd` 不要动」

#### Scenario: SC-009

- **GIVEN** 项目 `MEMORY.md`
- **WHEN** 读取法定源条目
- **THEN** SHALL 反映 D 盘为新家
- **AND** SHALL 保留 `D:/Programs/DKK_Fstdd` 的告警

### Requirement: 迁移不得影响其它位置的既有资产

#### Scenario: SC-010

- **GIVEN** `D:/Programs/DKK_Fstdd` 与 `~/.workbuddy-ai/Fstdd`
- **WHEN** 迁移前后比对
- **THEN** 二者 SHALL 未被本变更修改
- **AND** `D:/Programs/DKK_Fstdd` 是另一程序的调试副本，全程只读
