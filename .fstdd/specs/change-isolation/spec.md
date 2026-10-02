# Spec: change-isolation

> Change: 2026-09-25-new-isolate-flag | Auto-generated Human View

## Requirements

### Requirement: `stdd new` SHALL 提供显式隔离形态选择，默认 none 保持零行为漂移

#### Scenario: SC-001

- **GIVEN** 当前目录位于 git 工作树内
- **WHEN** 执行 `stdd new x --isolate worktree`
- **THEN** SHALL 建出独立 worktree 与显式命名分支，且 change 骨架（.fstdd/changes/<dir>/）落在 worktree 内而非主工作区

#### Scenario: SC-002

- **GIVEN** project.yaml 无 isolation 块
- **WHEN** 执行 `stdd new x`（不带 --isolate）
- **THEN** SHALL 在主工作区建骨架，且不创建任何 worktree 或分支（与改动前行为逐字一致）

#### Scenario: SC-003

- **GIVEN** 任意目录
- **WHEN** 执行 `stdd new --help`
- **THEN** SHALL 列出 --isolate 及取值 none/worktree/branch

### Requirement: 隔离所用的分支 SHALL 显式命名，不得产生隐式同名分支

#### Scenario: SC-004

- **GIVEN** 位于 git 工作树内且分支 fstdd/<dir> 不存在
- **WHEN** 执行 `stdd new x --isolate worktree`
- **THEN** SHALL 以 `git worktree add -b <branch_prefix><change_dir_name>` 建分支，分支名不含路径后缀（非 -explore/-research 之类派生名）

#### Scenario: SC-005

- **GIVEN** 位于 git 工作树内且工作区干净
- **WHEN** 执行 `stdd new x --isolate branch`
- **THEN** SHALL 用 `git checkout -b <branch_prefix><change_dir_name>` 切到新分支，且不创建 worktree

### Requirement: 隔离形态选择 SHALL 不静默降级，失败时不留半成品

#### Scenario: SC-006

- **GIVEN** 当前目录不在 git 工作树内
- **WHEN** 执行 `stdd new x --isolate worktree`（或 branch）
- **THEN** SHALL 以非 0 退出并说明原因，且 SHALL NOT 创建 change 目录（不静默降级为 none）

#### Scenario: SC-007

- **GIVEN** 位于 git 工作树内但工作区存在未提交改动（含未跟踪文件）
- **WHEN** 执行 `stdd new x --isolate branch`
- **THEN** SHALL 以非 0 退出并提示改用 --isolate worktree，SHALL NOT 切换分支

#### Scenario: SC-008

- **GIVEN** 目标分支名已存在，或 worktree 目标路径已存在
- **WHEN** 执行 `stdd new x --isolate worktree`
- **THEN** SHALL 在创建前检出冲突并以非 0 退出，输出可直接执行的清理命令，SHALL NOT 自行删除已存在的路径

### Requirement: worktree 存放位置 SHALL 不污染被隔离的仓库

#### Scenario: SC-009

- **GIVEN** project.yaml 未配置 isolation.worktree_root
- **WHEN** 执行 `stdd new x --isolate worktree`
- **THEN** SHALL 把 worktree 建在项目根**之外**（`<project_parent>/<project_name>.worktrees/<change_dir_name>`），使主工作区 `git status` 不因该 worktree 变脏

#### Scenario: SC-010

- **GIVEN** project.yaml 配置了 isolation.worktree_root
- **WHEN** 执行 `stdd new x --isolate worktree`
- **THEN** SHALL 使用该配置值作为 worktree 父目录

### Requirement: 隔离状态 SHALL 可见，且提示不得阻塞

#### Scenario: SC-011

- **GIVEN** 任意隔离形态（含 none）
- **WHEN** `stdd new` 正常结束
- **THEN** SHALL 输出一行隔离提示（当前形态 + 如需隔离的完整命令）

#### Scenario: SC-012

- **GIVEN** 任意隔离形态
- **WHEN** `stdd new` 全程执行
- **THEN** SHALL NOT 调用 input() 等待输入（零交互）

### Requirement: `stdd init` SHALL 写入隔离策略配置，且对既有配置幂等无害

#### Scenario: SC-013

- **GIVEN** 项目尚无 isolation 配置
- **WHEN** 执行 `stdd init`
- **THEN** SHALL 在 .fstdd/config.d/project.yaml 写入 isolation 块（default/worktree_root/branch_prefix）

#### Scenario: SC-014

- **GIVEN** project.yaml 已含 isolation 块或用户自定义键
- **WHEN** 再次执行 `stdd init`
- **THEN** SHALL 保留既有取值不变（只补缺失键，幂等）

### Requirement: `new` SHALL 消费配置默认值，且任何读取失败都回退 none

#### Scenario: SC-015

- **GIVEN** project.yaml 配置 isolation.default: worktree
- **WHEN** 执行 `stdd new x`（不带 --isolate）
- **THEN** SHALL 按 worktree 形态创建

#### Scenario: SC-016

- **GIVEN** project.yaml 缺失、YAML 不可解析、或 isolation.default 取值非法
- **WHEN** 执行 `stdd new x`（不带 --isolate）
- **THEN** SHALL 回退为 none 并正常建骨架，SHALL NOT 报错退出

### Requirement: 不可达的 --parallel 死代码 SHALL 被移除并留痕

#### Scenario: SC-017

- **GIVEN** 改动后的代码库
- **WHEN** 检索 `parallel` 与 `_setup_parallel_worktrees`
- **THEN** SHALL 无任何命中（函数与调用点均已移除）

#### Scenario: SC-018

- **GIVEN** 改动后的仓库
- **WHEN** 查看 CHANGELOG
- **THEN** SHALL 记录 --parallel 死代码的移除说明

### Requirement: 隔离 SHALL NOT 使流程门禁静默失效

#### Scenario: SC-019

- **GIVEN** 主工作区存在 Guard hook 注册文件（.claude/settings.local.json 或 .codebuddy/settings.local.json）
- **WHEN** 以 --isolate worktree 建出 worktree
- **THEN** SHALL 把该 hook 注册一并复制进 worktree，使 worktree 内 guard check 可被触发

#### Scenario: SC-020

- **GIVEN** 主工作区不存在任何 Guard hook 注册文件
- **WHEN** 以 --isolate worktree 建出 worktree
- **THEN** SHALL 明确输出告警说明该 worktree 内门禁未激活，SHALL NOT 静默通过
