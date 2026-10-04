# Spec: inbox-api-only-write

> Change: 2026-09-18-inbox-api-only-write | Auto-generated Human View

## Requirements

### Requirement: 收目录属主与权限：仅服务运行用户 fstdd-inbox 可写，ubuntu 只读

#### Scenario: SC-001

- **GIVEN** 服务 fstdd-inbox 以用户 fstdd-inbox 运行，收目录已 chown 至该用户
- **WHEN** 以 ubuntu 身份执行 touch /home/ubuntu/fstdd-inbox/.perm-probe
- **THEN** 操作 SHALL 失败，输出含 Permission denied 且退出码非 0
- **AND** 收目录下 SHALL 不存在 .perm-probe 文件
- **AND** namei -l /home/ubuntu/fstdd-inbox SHALL 显示属主 fstdd-inbox:fstdd-inbox
- **AND** 目录权限位 SHALL 为 0755（属主外无写位）

#### Scenario: SC-002

- **GIVEN** 服务运行中，客户端持有效 token
- **WHEN** POST /api/share-experience 提交 1 条经验（带 X-FSTDD-Token）
- **THEN** SHALL 返回 200 且 accepted=1
- **AND** 新落盘文件 SHALL 位于收目录且属主为 fstdd-inbox
- **AND** GET /health 的 received SHALL 相对提交前 +1

#### Scenario: SC-003

- **GIVEN** 收目录已收权
- **WHEN** 以 ubuntu 身份 tail /home/ubuntu/fstdd-inbox/server.log 并 curl /health
- **THEN** 两项 SHALL 均成功（权限收口不得破坏只读巡检链路）
- **AND** server.log 文件权限 SHALL 允许 other 读（0644 或更宽）

### Requirement: 非 API 写入通道（scp / 人工直写）被文件系统拒绝

#### Scenario: SC-004

- **GIVEN** 节点以 ubuntu 身份 scp 一个 .md 文件到收目录
- **WHEN** 执行 scp 传输
- **THEN** 传输 SHALL 失败（Permission denied，exit≠0）
- **AND** 收目录中 SHALL 不存在该文件
- **AND** server.log 中 SHALL 不出现该文件的 accepted 记录

#### Scenario: SC-005

- **GIVEN** 部署执行时收目录根下存在 EXP-20260915/16/17-* 试运行文件共 30 个
- **WHEN** 部署脚本执行 quarantine 步骤
- **THEN** 这 30 个文件 SHALL 全部移入收目录下 quarantine/ 子目录
- **AND** 收目录根下 SHALL 不再存在匹配 EXP-2026091[567]-*.md 的文件
- **AND** quarantine/ 内文件 SHALL 数量守恒（30，只移不删）

### Requirement: 鉴权与限流语义不因本次变更回退，且鉴权版源码回灌仓库

#### Scenario: SC-006

- **GIVEN** 服务端已配置 FSTDD_INBOX_TOKEN
- **WHEN** 来自白名单外 IP 的无凭证 POST
- **THEN** SHALL 返回 401 且 body 含 unauthorized
- **AND** server.log SHALL 出现 '[inbox] 401 <- <ip>' 行

#### Scenario: SC-007

- **GIVEN** 服务端已配置 token 且请求源 IP 在 FSTDD_INBOX_ALLOW_IPS 内
- **WHEN** 无凭证 POST
- **THEN** SHALL 放行（200 accepted=1）
- **AND** server.log SHALL 出现 legacy-ip 放行行

#### Scenario: SC-008

- **GIVEN** 未配置 FSTDD_INBOX_TOKEN
- **WHEN** 任意来源 POST
- **THEN** SHALL 返回 200（保持开放兼容旧行为）
- **AND** 启动日志 SHALL 含 'auth: OFF' 警告

#### Scenario: SC-009

- **GIVEN** 任意鉴权配置
- **WHEN** GET /health
- **THEN** SHALL 返回 200 且 received 等于收目录 *.md 数量
- **AND** SHALL 不要求任何凭证
