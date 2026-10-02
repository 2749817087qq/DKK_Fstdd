# Spec: canonical-in-workspace

> Change: 2026-09-17-canonical-in-workspace | Auto-generated Human View

## Requirements

### Requirement: 法定源必须位于工作区内，全部 FSTDD 开发产物集中在工作区文件夹

#### Scenario: SC-001

- **GIVEN** 工作区 `C:\Users\Administrator\WorkBuddy AI\2026-09-14-18-36-54\`
- **WHEN** 检查法定源位置
- **THEN** 法定源 SHALL 为工作区内的 `stdd-repo`
- **AND** SHALL 持有完整 git 历史与 tag `fstdd-v1.0.0`
- **AND** SHALL NOT 存在任何**仅**位于区外副本中的内容

#### Scenario: SC-002

- **GIVEN** 区外副本 `~/.workbuddy-ai/Fstdd`
- **WHEN** 按 git blob 哈希逐个比对它与 `stdd-repo`
- **THEN** 每个文件的内容 SHALL 能在 `stdd-repo`（含其对象库）中找到
- **AND** 若发现仅存于区外的内容，SHALL 先归并再继续，SHALL NOT 直接归档

### Requirement: skill 内固化路径必须指向工作区内的法定源

#### Scenario: SC-003

- **GIVEN** 从 `stdd-repo` 重装后的 `~/.workbuddy/skills/fstdd*/SKILL.md`
- **WHEN** 检查其中的绝对路径
- **THEN** SHALL 指向工作区内的 `stdd-repo`
- **AND** SHALL NOT 含 `~/.workbuddy-ai/Fstdd`
- **AND** `verify_workbuddy_skills.py` SHALL 全绿

#### Scenario: SC-004

- **GIVEN** 安装脚本 `stdd-repo/tools/install_workbuddy_skills.py`
- **WHEN** 执行安装
- **THEN** SRC SHALL 解析为 `stdd-repo/upstream`
- **AND** SHALL NOT 需要额外设置 `FSTDD_SRC`

### Requirement: 校验脚本的安装位置解析必须与「安装源 = 工作区仓库」这一事实一致

#### Scenario: SC-005

- **GIVEN** `tools/verify_skill_standards.py`
- **WHEN** 读取 `_installed_tools()` 的候选顺序
- **THEN** 顺序 SHALL 为：`FSTDD_INST_DIR` → 脚本自身 `tools/` → 工作区仓库 → 历史兜底
- **AND** SHALL NOT 把区外副本 `~/.workbuddy-ai/Fstdd` 置于首位
- **AND** SHALL NOT 把 `D:/Programs/DKK_Fstdd` 置于首位

#### Scenario: SC-006

- **GIVEN** `tools/verify_rename.py`
- **WHEN** 读取其安装位置解析
- **THEN** SHALL 与 SC-005 采用同一顺序

#### Scenario: SC-007

- **GIVEN** 工作区（存在区外副本与 D 盘调试副本）
- **WHEN** 从工作区运行三项校验
- **THEN** `verify_eol` SHALL 7/7、`verify_skill_standards` SHALL 7/7、`verify_rename` SHALL 8/8
- **AND** 结果 SHALL NOT 受区外副本是否存在影响

### Requirement: 区外副本必须完整归档，不得丢失内容

#### Scenario: SC-008

- **GIVEN** `~/.workbuddy-ai/Fstdd`
- **WHEN** 归档到 `backups/`
- **THEN** 归档副本 SHALL 与原目录文件数一致
- **AND** 逐文件哈希 SHALL 一致
- **AND** 原目录 SHALL NOT 被删除

### Requirement: 文档与记忆必须反映新架构

#### Scenario: SC-009

- **GIVEN** `docs/WORKBUDDY_INSTALL_NOTES.md`
- **WHEN** 阅读第 0 节的位置与权威关系
- **THEN** 法定源 SHALL 写为工作区内的 `stdd-repo`
- **AND** SHALL 说明 `~/.workbuddy-ai/Fstdd` 已归档、不再是法定源
- **AND** SHALL 保留「GitHub 是上传目标」的表述

#### Scenario: SC-010

- **GIVEN** 项目 `MEMORY.md`
- **WHEN** 读取法定源条目
- **THEN** SHALL 反映新架构（法定源 = 工作区内 `stdd-repo`）
- **AND** SHALL 保留 `D:/Programs/DKK_Fstdd` 不要动 的告警
