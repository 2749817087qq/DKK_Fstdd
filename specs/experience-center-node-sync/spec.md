# Spec: experience-center-node-sync

> Change: 2026-10-11-experience-center-node-sync | Auto-generated Human View

## Requirements

### Requirement: 扩展 experience extract 抽取源：在 test-report.md 之外新增 design-adjustments.md 与 adjudication-log.tsv，保持现有 test-report 抽取路径不变

#### Scenario: SC-001

- **GIVEN** 存在一个含 draft 条目（GIVEN/WHEN/THEN + SHALL）的 test-report.md
- **WHEN** 调用 `fstdd experience extract`（默认 test-report 源）
- **THEN** SHALL 产出 discovered 草稿，条数大于 0（既有路径不退化）

#### Scenario: SC-002

- **GIVEN** 存在一个含偏差记录的 design-adjustments.md
- **WHEN** 调用 `fstdd experience extract --source design-adjustments`
- **THEN** SHALL 从设计偏离记录产出 discovered 草稿，条数大于 0

#### Scenario: SC-003

- **GIVEN** 存在一个含同 eid 多版本裁决的 adjudication-log.tsv
- **WHEN** 调用 `fstdd experience extract --source adjudication`
- **THEN** SHALL 从裁定日志产出 discovered 草稿，条数大于 0

#### Scenario: SC-004

- **GIVEN** 同一 change 同时含 test-report + design-adjustments + adjudication-log 三类源
- **WHEN** 调用 `fstdd experience extract --all`
- **THEN** SHALL 三类源均被纳入且按 experience_id 去重合并

#### Scenario: SC-005

- **GIVEN** 一个在扩展前可被正常抽取的 test-report 夹具
- **WHEN** 扩展后再次运行 extract（仅 test-report）
- **THEN** SHALL 抽取结果与扩展前逐条一致（无回归）

### Requirement: 新增非交互自动沉淀入口（auto-deposit），接进 DELIVER 阶段；尊重 FSTDD_NO_SHARE=1 总开关；产物一律 lifecycle=discovered

#### Scenario: SC-006

- **GIVEN** DELIVER 阶段激活，且当前 change 含 test-report + design-adjustments + adjudication-log 三类源
- **WHEN** fstdd-deliver 流程触发 `fstdd experience auto-deposit`（非交互）
- **THEN** SHALL 自动抽取三类源并将 discovered 草稿入库，不调用任何交互式 input()

#### Scenario: SC-007

- **GIVEN** 环境变量 FSTDD_NO_SHARE=1
- **WHEN** 触发 `fstdd experience auto-deposit`
- **THEN** SHALL 跳过抽取与入库（本地 0 新增，且无任意出站/外发）

#### Scenario: SC-008

- **GIVEN** auto-deposit 已产出若干草稿条目
- **WHEN** 检查入库条目的 frontmatter
- **THEN** SHALL 每条 lifecycle=discovered，且 STATUS 字段不为 shared

#### Scenario: SC-009

- **GIVEN** 以非 TTY / 管道方式运行 auto-deposit
- **WHEN** 流程执行
- **THEN** SHALL 不阻塞于任何标准输入读取，退出码 0 或受控非零（FSTDD_NO_SHARE 时静默跳过）

### Requirement: 新增中心节点同步能力：复用 tools/share_experience.py 的 scp(fstdd-hub)/inbox 第一方传输推到 hub；pull/merge 经 kg_sync 式增量合并回本地；幂等、可重入、honor share_disabled

#### Scenario: SC-010

- **GIVEN** 节点 A 本地 .fstdd/experiences 含若干条目且 FSTDD_NO_SHARE 未置位
- **WHEN** 执行 `fstdd experience sync --push`
- **THEN** SHALL 经第一方 share_experience 传输把本地经验推到 fstdd-hub（fstdd-inbox），不新建独立 git 仓

#### Scenario: SC-011

- **GIVEN** fstdd-hub 已聚合节点 A 的经验
- **WHEN** 节点 B 执行 `fstdd experience sync --pull`
- **THEN** SHALL 以增量合并方式把远端经验并入 B 的本地库（复用 _index_lock/_rebuild_index 并发安全）

#### Scenario: SC-012

- **GIVEN** A 已 push 全部经验；B 初始为空或子集
- **WHEN** B 执行 --pull
- **THEN** SHALL 使 B 的 eid 集合与内容逐条等于 A（收敛），不丢条目

#### Scenario: SC-013

- **GIVEN** B 已与 A 收敛（无新变更）
- **WHEN** B 再次执行 `fstdd experience sync --pull`
- **THEN** SHALL 幂等：无新增条目、无错误、索引不变

#### Scenario: SC-014

- **GIVEN** 任意本地库状态
- **WHEN** 执行 `fstdd experience sync --pull --dry-run`
- **THEN** SHALL 仅打印将执行的合并计划，不写本地库、不推/拉 hub

### Requirement: 新增 opt-in 安全档：安全模式用 cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256 混合加密（RSA 包裹随机 AES-256 密钥，AES-GCM 加密正文，因 318B OAEP 载荷上限）后再 push；pull 时解密；默认开放档零密钥可用

#### Scenario: SC-015

- **GIVEN** 安全档启用且 cred-relay k_pub.pem/k_priv.pem 存在
- **WHEN** 执行 `fstdd experience sync --push --secure`
- **THEN** SHALL 先对载荷脱敏，再以混合加密（RSA-OAEP 包裹随机 AES-256 密钥 + AES-GCM 加密正文）后出站

#### Scenario: SC-016

- **GIVEN** 一段已脱敏明文经验载荷
- **WHEN** 用 cred-relay 混合加密后再用 cred-relay 私钥解密
- **THEN** SHALL 解密内容与原明文逐字节一致

#### Scenario: SC-017

- **GIVEN** 加密使用 rsa_oaep_md=sha256 且 rsa_mgf1_md=sha256
- **WHEN** 加密后用同一私钥解密
- **THEN** SHALL 解密成功（对照：若 MGF1 误用 sha1 则解密失败，契约测试须锁定）

#### Scenario: SC-018

- **GIVEN** 一条经验正文超过 318 字节
- **WHEN** 安全档加密该载荷
- **THEN** SHALL 走混合加密（RSA 仅包裹 AES 密钥，AES-GCM 加密超长正文），不尝试 RSA 直加密文

#### Scenario: SC-019

- **GIVEN** 未启用 --secure 且本地无密钥
- **WHEN** 执行 `fstdd experience sync --push` / `--pull`
- **THEN** SHALL 成功完成明文（已脱敏）同步，无需任何密钥

### Requirement: 新增同步冲突策略：同 eid 多节点编辑 → 以 updated_at 末写胜 + 显式冲突日志，绝不静默覆盖

#### Scenario: SC-020

- **GIVEN** 同一 experience_id 在 A、B 两节点有不同内容，且 B 的 updated_at 较新
- **WHEN** B 执行合并
- **THEN** SHALL 以 B（updated_at 较新）版本为胜出版本

#### Scenario: SC-021

- **GIVEN** 检测到同 eid 内容冲突（A 旧 / B 新）
- **WHEN** 合并完成
- **THEN** SHALL 把被覆盖的旧版本写入冲突日志（含 eid、双方 updated_at、落点），绝不静默丢弃

#### Scenario: SC-022

- **GIVEN** 多节点并发触发 sync
- **WHEN** 并发合并执行
- **THEN** SHALL 经索引锁保证不出现半写索引或竞争损坏

### Requirement: 保持框架「经验不外发第三方」硬规定：不 reintroduce 任何第三方外发；experience.py 中 _cmd_share_single 永久禁用 leonai42/hzddyy 的禁用状态与注释保持不变

#### Scenario: SC-023

- **GIVEN** upstream/fstdd/cli/commands/experience.py 的 _cmd_share_single
- **WHEN** 本变更落地后检查该段
- **THEN** SHALL 仍含 leonai42 与 hzddyy 的禁用分支且其注释与禁用逻辑未被改动

#### Scenario: SC-024

- **GIVEN** 本变更新增/修改的全部源码
- **WHEN** 对源码做第三方外发字面量审计（grep 已知第三方域名 / 仓库名）
- **THEN** SHALL 不出现任何指向 leonai42/hzddyy 之外的第三方外发目标（仅第一方 fstdd-hub 出现在 share_experience 既有路径）
