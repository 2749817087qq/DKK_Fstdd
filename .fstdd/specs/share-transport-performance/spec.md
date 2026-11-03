# Spec: share-transport-performance

> Change: 2026-10-31-share-scp-tar-packing | Auto-generated Human View

## Requirements

### Requirement: scp 通道须先把 out_dir 的全部文件打成**单个** tar.gz 再传输，
而非把每个文件路径逐个塞进 scp 命令行。打包须扁平化（成员名不含目录成分）。


#### Scenario: SC-SCP-001

- **GIVEN** out_dir 含 5 个 .md 文件（含子目录下的文件）
- **WHEN** 调用 _pack_tar(out_dir)
- **THEN** 返回单个 .tar.gz 路径，SHALL NOT 返回 None
- **AND** 解包后文件数 SHALL 等于 5
- **AND** 解包后每个成员的 name SHALL 不含 '/'（已扁平化）

#### Scenario: SC-SCP-002

- **GIVEN** out_dir 下有子目录 a/b/EXP-001.md
- **WHEN** 调用 _pack_tar(out_dir)
- **THEN** 该成员在 tar 内的 name SHALL 为 'EXP-001.md'
- **AND** SHALL NOT 为 'a/b/EXP-001.md'

### Requirement: 走 tar 路径时，scp 命令行的源文件列表须**恰好 1 个**（tar 包本身）。


#### Scenario: SC-SCP-003

- **GIVEN** out_dir 含 112 个文件，远端 tar 可用
- **WHEN** 调用 _scp_dir(out_dir, ...)
- **THEN** 捕获到的 scp argv 中，源文件参数 SHALL 恰好 1 个
- **AND** 该参数 SHALL 以 .tar.gz 结尾

### Requirement: 远端解包后须校验文件数与本地一致，不一致则返回失败（防解包不完整被当成功）。


#### Scenario: SC-SCP-004

- **GIVEN** 本地打包 112 个文件，但远端解包后只有 100 个 .md
- **WHEN** 执行数量校验
- **THEN** _scp_dir SHALL 返回 (False, reason)
- **AND** reason SHALL 含本地数与远端数两个数字
- **AND** 批次目录 SHALL 被清理（不留半成品）

#### Scenario: SC-SCP-005

- **GIVEN** 本地 112 个，远端解包后也是 112 个
- **WHEN** 执行数量校验
- **THEN** _scp_dir SHALL 返回 (True, '')

### Requirement: tar 打包失败时须自动回退到逐文件传输，且 reason 里标注已回退。


#### Scenario: SC-SCP-006

- **GIVEN** _pack_tar 因文件被占用抛异常（monkeypatch 模拟）
- **WHEN** 调用 _scp_dir(out_dir, ...)
- **THEN** SHALL 走逐文件路径完成传输，返回 (True, reason)
- **AND** reason SHALL 含「回退」字样
- **AND** SHALL NOT 直接返回失败

#### Scenario: SC-SCP-007

- **GIVEN** 远端 command -v tar 返回非 0（无 tar）
- **WHEN** 调用 _scp_dir(out_dir, ...)
- **THEN** SHALL 回退逐文件，SHALL NOT 尝试 tar 解包
- **AND** reason SHALL 说明远端无 tar

### Requirement: 既有安全校验在 tar 路径上须继续生效：`..` 路径、`-` 开头文件名、`--` 终止选项。


#### Scenario: SC-SCP-008

- **GIVEN** out_dir 里有文件名以 '-' 开头（如 '-oProxyCommand=x'）
- **WHEN** 调用 _scp_dir(out_dir, ...)
- **THEN** SHALL 返回 (False, reason) 且 reason 含「以 `-` 开头」
- **AND** SHALL NOT 执行任何 scp / ssh 子进程

#### Scenario: SC-SCP-009

- **GIVEN** remote_dir 为 '../etc'（含上跳）
- **WHEN** 调用 _scp_dir(out_dir, '../etc')
- **THEN** SHALL 返回 (False, reason) 且 reason 含拒绝原因
- **AND** SHALL NOT 执行任何子进程

### Requirement: 批次目录命名与远端布局须保持不变（消费方依赖）。


#### Scenario: SC-SCP-010

- **GIVEN** FSTDD_NODE_ID=local
- **WHEN** 走 tar 路径完成一次传输
- **THEN** 远端批次目录名 SHALL 匹配 `local-experiences-\d{8}-\d{6}`
- **AND** 解包后 SHALL 只留 .md 文件，tar.gz 已被删除

### Requirement: tar 路径的端到端耗时须显著低于逐文件路径（性能目标）。


#### Scenario: SC-SCP-011

- **GIVEN** 112 个 1-5KB 的文件
- **WHEN** 只跑 _pack_tar 的打包阶段（不含网络）
- **THEN** 打包耗时 SHALL < 2 秒
- **AND** （端到端 <30s 由真实链路验证，不进单测 —— 单测不依赖网络）
