# Spec: contract-auto-share

> Change: 2026-09-16-contract-auto-share | Auto-generated Human View

## Requirements

### Requirement: Phase 4 (Deliver) 必须静默回传本次沉淀的经验：自动、无交互、不要求使用者额外操作

#### Scenario: SC-001

- **GIVEN** 一个已完成 Phase 3、进入 DELIVER 阶段的 change
- **WHEN** 执行 Phase 4 (Deliver)
- **THEN** 系统 SHALL 回传本次 change 沉淀的经验
- **AND** 该过程 SHALL NOT 产生任何需要使用者回答的交互提示
- **AND** 该过程 SHALL NOT 要求使用者额外执行命令
- **AND** 回传动作 SHALL 记录在 DELIVER 的完成摘要中

#### Scenario: SC-002

- **GIVEN** 使用者环境中存在 GitHub 凭证（GITHUB_TOKEN / PUSH_TOKEN / GH_TOKEN / .gh_token 任一）
- **WHEN** Phase 4 执行静默回传
- **THEN** 回传目标 SHALL 为 Fstdd-experiences
- **AND** 无写权限时 SHALL 降级为 fork + Pull Request，而不是直接失败

#### Scenario: SC-003

- **GIVEN** 使用者环境中不存在任何 GitHub 凭证
- **WHEN** Phase 4 执行静默回传
- **THEN** 回传 SHALL 降级到自建接收端点（FSTDD_INBOX_URL，默认 http://43.134.236.80:8787）
- **AND** 该路径 SHALL NOT 要求使用者拥有 GitHub 账号
- **AND** 该路径 SHALL NOT 静默失败——降级必须真的发生，且结果进入审计记录

#### Scenario: SC-004

- **GIVEN** 已安装到使用者机器的 FSTDD skill（~/.workbuddy/skills 等）
- **WHEN** 检查 fstdd-deliver 的 Phase 4 步骤定义
- **THEN** 该步骤定义 SHALL 包含静默回传动作，且引用 tools/share_experience.py
- **AND** 对照：本变更前该文件对 share_experience / --publish 零引用（已实测）

### Requirement: 静默回传的目标必须锁死在我方位置，代码层面不可能指向第三方

#### Scenario: SC-005

- **GIVEN** 完整仓库（含 tools/、upstream/、skills/、契约文本）
- **WHEN** 静态扫描所有回传目标标识（leonai42/stdd-experiences、hzddyy.com、share-experience API）
- **THEN** 指向第三方的**可执行**路径数 SHALL 为 0
- **AND** 这些标识仅允许出现在「历史/已永久移除」说明语境中
- **AND** 扫描 SHALL 区分「可执行代码」与「注释/文档说明」，不得因说明文本而误判

#### Scenario: SC-006

- **GIVEN** 回传目标常量（DEFAULT_EXP_REPO / FSTDD_INBOX_URL）
- **WHEN** 读取其默认值
- **THEN** 默认值 SHALL 指向我方位置（2749817087qq/Fstdd-experiences、43.134.236.80:8787）
- **AND** 目标 SHALL 可通过环境变量覆盖（自建实例场景）
- **AND** 覆盖能力 SHALL NOT 被用于把默认值改成第三方

### Requirement: 静默回传必须零阻塞：回传失败或超时不得影响使用者的 DELIVER 流程

#### Scenario: SC-007

- **GIVEN** 回传端点不可达（网络不通 / 端口被封 / 服务未运行）
- **WHEN** Phase 4 执行静默回传
- **THEN** DELIVER 流程 SHALL 继续正常完成
- **AND** 退出码 SHALL 为成功（回传失败不改变 DELIVER 的成败）
- **AND** 失败原因 SHALL 写入审计记录与摘要提示，而不是抛出异常中断

#### Scenario: SC-008

- **GIVEN** 回传端点响应极慢（不返回）
- **WHEN** Phase 4 执行静默回传
- **THEN** 请求 SHALL 在有限超时内放弃
- **AND** 超时后 SHALL 按既有退避策略重试有限次，而非无限等待

### Requirement: 静默回传必须可审计、可关闭——使用者可查、可停

#### Scenario: SC-009

- **GIVEN** 一次成功与一次失败的静默回传
- **WHEN** 查看本地审计记录
- **THEN** 记录 SHALL 包含每条经验标识、回传目标、结果（成功/失败及原因）
- **AND** 记录位置 SHALL 在项目内可预期路径（不得散落系统临时目录）
- **AND** 审计记录 SHALL NOT 包含凭证明文

#### Scenario: SC-010

- **GIVEN** 使用者通过开关关闭静默回传
- **WHEN** 执行 Phase 4 (Deliver)
- **THEN** 系统 SHALL NOT 发起任何回传网络请求
- **AND** 关闭状态 SHALL 在 DELIVER 摘要中明示（让使用者知道回传被跳过）
- **AND** 关闭开关 SHALL 在文档中可查

### Requirement: 静默回传的载荷必须强制脱敏，且服务端二次校验保持生效——无人工把关时这是唯一防线

#### Scenario: SC-011

- **GIVEN** 经验正文中含凭证、绝对路径、IP、内网域名
- **WHEN** 静默回传构造载荷
- **THEN** 载荷 SHALL 经过强制脱敏后才发出
- **AND** 命中敏感规则的内容 SHALL 被替换，而不是原样发送
- **AND** 脱敏 SHALL NOT 可通过静默回传路径被绕过

#### Scenario: SC-012

- **GIVEN** 绕过客户端脱敏直接向端点提交含 ghp_ / 私钥 / 用户路径的内容
- **WHEN** 端点处理该请求
- **THEN** 端点 SHALL 拒绝该内容（422）且不落盘
- **AND** 本断言为「须保持」项：本变更 SHALL NOT 削弱该服务端校验

### Requirement: 契约面（AI 会当指令读的文本）必须与实际行为一致，且不再漂移

#### Scenario: SC-013

- **GIVEN** 一个空目录，执行 fstdd init
- **WHEN** 读取生成的 FSTDD_CONSTITUTION.md
- **THEN** 文本中 SHALL NOT 出现裸 STDD（仅允许出现在上游来源/历史语境）
- **AND** 文本 SHALL NOT 出现「显式执行」这一与既定语义相反的措辞
- **AND** 文本 SHALL 明确写出「静默回传到我方指定位置」
- **AND** 文本 SHALL 明确写出「不向第三方外发」
- **AND** 常用命令表中的命令名 SHALL 与真实 CLI 一致（fstdd ...）

#### Scenario: SC-014

- **GIVEN** 本仓库工作副本
- **WHEN** 用当前 init 模板在临时目录生成宪法，并与仓库根 FSTDD_CONSTITUTION.md 比对
- **THEN** 两者 SHALL 逐字节一致
- **AND** 本仓库副本由此成为生成产物，不再手工维护

#### Scenario: SC-015

- **GIVEN** 本仓库工作副本
- **WHEN** 检查 .fstdd/memory/FSTDD_CONSTITUTION.md
- **THEN** 该文件 SHALL 存在，且内容 SHALL 与仓库根副本一致

#### Scenario: SC-016

- **GIVEN** 本仓库工作副本
- **WHEN** 扫描 UPGRADE_NOTES 生成逻辑与 .fstdd/onboarding/AI_OPERATING_MANUAL.yaml
- **THEN** 其中 SHALL NOT 出现陈旧 rules（如「Phase 4 DELIVER 自动同步知识图谱」）
- **AND** 其中 SHALL NOT 出现裸 STDD 或 stdd <子命令> 形式的旧命令名
- **AND** 其中涉及回传的表述 SHALL 指向我方指定位置

### Requirement: 存量项目必须能升级到修正后的宪法，且不丢失用户自定义内容

#### Scenario: SC-017

- **GIVEN** 一个已存在陈旧 FSTDD_CONSTITUTION.md 的项目（含用户自定义条目）
- **WHEN** 执行升级（fstdd upgrade）
- **THEN** 升级 SHALL 先备份原文件
- **AND** 升级 SHALL 只迁移已知陈旧片段（自动上传到社区、旧命令名、漏改名）
- **AND** 用户自定义的条目 SHALL 被保留
- **AND** 升级结果 SHALL 报告实际改动了哪些片段

#### Scenario: SC-018

- **GIVEN** 一个已完成宪法升级的项目
- **WHEN** 再次执行升级
- **THEN** 第二次升级 SHALL NOT 产生任何文件变更（幂等）
- **AND** 重复执行 SHALL NOT 反复累积备份

### Requirement: validate 对 TC-ID 的判定必须与 test-plan 模板规定的写法相容（工具缺陷修复）

#### Scenario: SC-019

- **GIVEN** 一份按模板编写、含「测试执行矩阵」与「建议补充顺序」两节的 test-plan
- **WHEN** 执行 fstdd validate
- **THEN** SHALL 判定为通过
- **AND** 矩阵与优先级列表中对已有 TC-ID 的**引用** SHALL NOT 被判为「重复的 TC-ID」
- **AND** 对照：修正前实测报 16 个重复；归档样例 TC-EOL-001 出现 3 次同样会被误判

#### Scenario: SC-020

- **GIVEN** 在 test-plan 中追加一个与已有案例同 ID 的案例定义行
- **WHEN** 执行 fstdd validate
- **THEN** SHALL 判定为失败，并指出重复的 ID
- **AND** 该反向断言 SHALL 保持有效——修误报不得削弱检查本身
