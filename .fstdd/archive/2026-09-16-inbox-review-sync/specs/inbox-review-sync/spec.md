# Spec: inbox-review-sync

> Change: 2026-09-16-inbox-review-sync | Auto-generated Human View

## Requirements

### Requirement: 待审核池的内容必须能一条命令取回本地，不再依赖人工 ssh 搬运

#### Scenario: SC-001

- **GIVEN** 自建接收端点可达，池中有已落盘的待审核经验
- **WHEN** 执行拉取命令
- **THEN** 经验 SHALL 被取回并落到本地暂存目录
- **AND** SHALL NOT 要求使用者手工 ssh 或手工复制文件
- **AND** 拉取结果 SHALL 可复现（同一池内容重复拉取得到相同结果）

#### Scenario: SC-002

- **GIVEN** 池中文件名为 `<experience_id>-<UTC时间戳>.md`
- **WHEN** 拉取落盘
- **THEN** 本地文件名 SHALL 归一为 `<experience_id>.md`（丢弃时间戳后缀）
- **AND** 归一后同一 id 只会有一个文件，重复投稿不会堆积

#### Scenario: SC-003

- **GIVEN** 端点不可达（网络不通 / 服务未运行）
- **WHEN** 执行拉取命令
- **THEN** SHALL 以明确的失败原因退出（非零退出码）
- **AND** SHALL NOT 在未取到任何内容时报告成功

### Requirement: 发布物必须剥离服务端元数据头 —— 其中含投稿者 IP，公开即泄露第三方个人信息

#### Scenario: SC-004

- **GIVEN** 池中文件的头部形如 `<!-- fstdd-inbox ... remote_addr: <ip> -->`
- **WHEN** 解析该文件
- **THEN** SHALL 能提取 experience_id / author / received_at / remote_addr
- **AND** 这些字段 SHALL 仅用于本地审核展示
- **AND** 解析 SHALL 容忍头部缺失（缺头不报错，按无元数据处理）

#### Scenario: SC-005

- **GIVEN** 一个含 `remote_addr: 203.0.113.7` 的待审核文件
- **WHEN** 构造发布物
- **THEN** 发布物 SHALL NOT 包含该 IP，也 SHALL NOT 包含 `fstdd-inbox` 头
- **AND** 反向验证：断言该 IP 字符串在发布物中出现次数为 0
- **AND** 剥离 SHALL NOT 误删正文（正文内容 SHALL 逐字保留，除脱敏替换外）

### Requirement: 必须两级去重，避免经验库堆积重复条目

#### Scenario: SC-006

- **GIVEN** 同一 experience_id 有 2 份，received_at 不同
- **WHEN** 归一落盘
- **THEN** SHALL 只保留 received_at 最新的一份
- **AND** 丢弃的那份 SHALL 在审核表中标注为「重复（同 id）」

#### Scenario: SC-007

- **GIVEN** 两个不同 experience_id 的文件，正文完全相同
- **WHEN** 归一落盘
- **THEN** SHALL 只保留一份
- **AND** 去重 SHALL 基于内容哈希，不依赖文件名

#### Scenario: SC-008

- **GIVEN** 已拉取并归一过的暂存目录
- **WHEN** 再次执行同一拉取
- **THEN** 结果 SHALL 与首次一致（幂等），不产生新增文件

### Requirement: 必须复用既有能力，不得出现第二套脱敏或推送实现

#### Scenario: SC-009

- **GIVEN** `tools/inbox_pull.py`
- **WHEN** 检查其脱敏逻辑
- **THEN** SHALL 调用 `share_experience.sanitize()`
- **AND** SHALL NOT 内联复制一份脱敏规则表

#### Scenario: SC-010

- **GIVEN** `tools/inbox_pull.py`
- **WHEN** 检查其推送逻辑
- **THEN** SHALL 调用 `share_experience.publish()`
- **AND** SHALL NOT 出现第二套 git clone / commit / push 实现
- **AND** 仓库内 `publish()` 的定义处数 SHALL 为 1

### Requirement: 维护者必须能在入库前完成审核，并能拒绝个别条目

#### Scenario: SC-011

- **GIVEN** 暂存目录中有若干待审核经验
- **WHEN** 执行审核命令
- **THEN** 审核表 SHALL 含 id / 作者 / 接收时间 / 字节数 / 脱敏命中 / 重复情况
- **AND** 审核表 SHALL 让人能据以判断「哪些可以入库」

#### Scenario: SC-012

- **GIVEN** 暂存目录中的某条经验
- **WHEN** 执行拒绝命令
- **THEN** 该条 SHALL 被移出待发布集合
- **AND** SHALL 留痕（移入单独的 rejected 位置），SHALL NOT 直接删除
- **AND** 被拒条目 SHALL NOT 出现在后续发布物中

### Requirement: 发布目标与内容边界必须正确

#### Scenario: SC-013

- **GIVEN** 暂存目录中的待发布经验
- **WHEN** 执行发布
- **THEN** 目标仓库 SHALL 为 `2749817087qq/Fstdd-experiences`（我方位置）
- **AND** SHALL NOT 指向任何第三方仓库

#### Scenario: SC-014

- **GIVEN** 暂存目录中同时存在经验文件与索引/说明文件（README.md / SUBMIT.md）
- **WHEN** 构造发布物
- **THEN** 发布物 SHALL 只含经验文件
- **AND** 索引与说明文件 SHALL 被排除（复用既有 export_files 的排除规则）
