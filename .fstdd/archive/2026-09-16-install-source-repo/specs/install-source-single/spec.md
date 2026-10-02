# Spec: install-source-single

> Change: 2026-09-16-install-source-repo | Auto-generated Human View

## Requirements

### Requirement: 必须存在唯一「法定源」且它是 git 仓库；工作区与 GitHub 均不是权威

#### Scenario: SC-001

- **GIVEN** 本机环境
- **WHEN** 检查 `~/.workbuddy-ai/Fstdd` 的 git 状态并与工作区比对
- **THEN** 该目录 SHALL 是 git 仓库，且其 HEAD SHALL 等于工作区 HEAD
- **AND** 其 tag `fstdd-v1.0.0` SHALL 存在且指向与工作区相同的提交
- **AND** 其 `origin` SHALL 指向 GitHub `2749817087qq/DKK_Fstdd`（上传目标）

#### Scenario: SC-002

- **GIVEN** 法定源已设 `receive.denyCurrentBranch=updateInstead`；工作区已设 `canonical` remote
- **WHEN** 工作区执行 `git push canonical master`
- **THEN** 法定源的**工作区文件** SHALL 被同步更新（而不只是 ref 更新）
- **AND** 反向 SHALL 可用：`git fetch canonical && git merge --ff-only FETCH_HEAD`
- **AND** 同步 SHALL NOT 依赖手工 cp

#### Scenario: SC-003

- **GIVEN** 契约文档（`docs/WORKBUDDY_INSTALL_NOTES.md`）
- **WHEN** 阅读其中关于位置与权威的说明
- **THEN** SHALL 写明「法定源唯一、GitHub 是上传目标、工作区是开发副本」三者关系
- **AND** SHALL NOT 把 GitHub 或工作区表述为权威来源

### Requirement: 校验脚本的「安装位置」解析必须自定位，不得硬编码某一副本路径

#### Scenario: SC-004

- **GIVEN** `tools/verify_skill_standards.py`
- **WHEN** 读取其安装位置解析逻辑
- **THEN** 解析顺序 SHALL 为：`FSTDD_INST_DIR`（显式覆盖）→ 脚本自身所在仓库的 `tools/` → 法定源 → 历史位置兜底
- **AND** SHALL NOT 把 `D:/Programs/DKK_Fstdd` 置于首位

#### Scenario: SC-005

- **GIVEN** `tools/verify_rename.py`
- **WHEN** 读取其安装位置解析逻辑
- **THEN** SHALL 与 SC-004 采用同一自定位策略

#### Scenario: SC-006

- **GIVEN** 本机（存在 D 盘调试副本、法定源、工作区）
- **WHEN** 从工作区运行 `verify_skill_standards.py` 与 `verify_rename.py`
- **THEN** 二者 SHALL 全绿（当前 5/7、7/8）
- **AND** 校验结果 SHALL NOT 受 `D:/Programs/DKK_Fstdd` 是否存在影响

### Requirement: 「备份完整性」检查必须容忍「无备份」这一合法状态

#### Scenario: SC-007

- **GIVEN** 一棵已符合行尾规则的树（`verify_eol --fix` 不需要做任何改动）
- **WHEN** 执行 `verify_skill_standards.py` 的备份完整性检查
- **THEN** 该检查 SHALL 通过
- **AND** 对照：修正前该场景恒定 FAIL
- **AND** 存在备份时，备份正文与当前文件一致性 SHALL 仍被校验

### Requirement: 经验与知识的流通必须完全收敛到自有仓库，不留上游第三方来源

#### Scenario: SC-008

- **GIVEN** `upstream/fstdd/cli/commands/knowledge.py`
- **WHEN** 读取其社区图谱拉取逻辑
- **THEN** SHALL NOT 存在硬编码的 `leonai42/stdd-experiences` 默认值
- **AND** 当配置中 `repo` 为空/未设时，函数 SHALL 提前返回 None（不落到 `gh clone`）

#### Scenario: SC-009

- **GIVEN** `upstream/.fstdd/config.d/knowledge.yaml` 与 `experience.yaml`
- **WHEN** 读取其社区来源配置
- **THEN** `knowledge.community.repo` SHALL 为空；`experience.community.registries` SHALL 为空列表
- **AND** 两份配置中指向第三方仓库的默认值 SHALL 已移除

#### Scenario: SC-010

- **GIVEN** `.fstdd/archive/2026-09-16-contract-auto-share/` 归档的测试与白名单
- **WHEN** 检查 `test_cross_cutting_verification.py` 的 `ALLOWED_REFS`
- **THEN** SHALL NOT 再包含以「拉取（只进）源」为由的条目
- **AND** 其 `test_a1_no_executable_third_party_path` 与 `test_a6_allowlist_is_not_rotten` SHALL 仍通过

### Requirement: 安装说明文档必须与实际事实一致

#### Scenario: SC-011

- **GIVEN** `docs/WORKBUDDY_INSTALL_NOTES.md`
- **WHEN** 读取其安装位置、skill 数量与安全策略三节
- **THEN** 全局 skill 目录 SHALL 写为 `~/.workbuddy/skills`（内核实际加载处）
- **AND** skill 数量 SHALL 与实测一致（7 个）
- **AND** 经验策略 SHALL 写为「静默回传到我方指定位置」，而非「默认禁用」

#### Scenario: SC-012

- **GIVEN** 同一文档
- **WHEN** 查找位置与权威的说明
- **THEN** SHALL 含法定源／开发副本／上传目标三者关系（同 SC-003）

### Requirement: 归并调试副本的独有工作，且不得修改该副本

#### Scenario: SC-013

- **GIVEN** `D:/Programs/DKK_Fstdd` 的独有文件
- **WHEN** 归并完成后检查工作区
- **THEN** 3 份实质工作（knowledge.py、两份 config）与 2 份 verify 修复 SHALL 已进入工作区
- **AND** 归并后 `knowledge.py` 的第三方默认值 SHALL 已移除

#### Scenario: SC-014

- **GIVEN** `D:/Programs/DKK_Fstdd`
- **WHEN** 归并完成前后比对
- **THEN** 该目录的文件内容 SHALL 未被本变更修改
- **AND** 不得对其执行任何写操作

### Requirement: 重装后 skill 内固化的路径必须指向法定源

#### Scenario: SC-015

- **GIVEN** 从法定源执行安装脚本后的 `~/.workbuddy/skills/fstdd*/SKILL.md`
- **WHEN** 检查其中的绝对路径
- **THEN** SHALL 指向 `~/.workbuddy-ai/Fstdd`
- **AND** SHALL NOT 出现会话工作区路径（`WorkBuddy AI/2026-…`）
- **AND** `verify_workbuddy_skills.py` SHALL 全绿
