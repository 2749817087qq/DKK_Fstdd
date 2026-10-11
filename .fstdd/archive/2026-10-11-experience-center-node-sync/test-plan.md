# 2026-10-11 测试方案与详细案例

> 版本：2026-10-11-v1
> 创建日期：2026-10-11
> 对应 Phase 2 Spec：canonical/specs/code/2026-10-11-experience-center-node-sync.yaml + canonical/specs/agent/2026-10-11-experience-center-node-sync.yaml
> 锚定等级：L3（proposal.risk_assessment.safety_critical=true ⇒ ≥L3；cross_system=true ⇒ ≥L2，取严）

## 一、测试策略

### 1.1 测试金字塔

- **单元（≈55%）**：抽取解析器（_cmd_extract 扩展）、`_exp_crypto` 混合加密 round-trip、冲突合并函数（updated_at LWW）、第三方外发字面量审计（静态）。底座为纯函数，可离线夹具驱动。
- **集成（≈35%）**：auto-deposit 接 DELIVER 非交互接线 + FSTDD_NO_SHARE 开关、kg_sync 式 pull 增量合并、hub push/pull 端到端（依赖 fstdd-hub SSH 可达；CI 中可 mock ssh/scp）。
- **E2E（≈10%）**：两节点经第一方 hub 收敛（A push → B pull == A）、安全档端到端加密/解密、幂等重跑。依赖真实 hub，放 BUILD 末期手动+沙箱实测。

### 1.2 测试原则

- **幂等优先**：所有 sync 路径必须 `--dry-run` 绝对安全 + 重跑无副作用（沿用 kg_sync 契约）。
- **不静默**：冲突/覆盖一律显式冲突日志；回归 consolidation 静默丢字段教训。
- **出站不变量**：任何同步出站前先脱敏；安全档密文对自检不透明。
- **零密钥可用**：默认开放档不依赖任何密钥即可同步（能用就好）。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| upstream/tests/commands/test_experience_parser.py | 5 | 单元 | 双块 frontmatter 解析（consolidation 已建，REQ-001 复用） |
| E:/FSTDD/.workbuddy-ai/tmp/credtest/selftest.sh | 5(T1–T5) | 契约 | RSA-OAEP 参数敏感性 + 318B 上限（REQ-004 仿制；密钥对在 E:/FSTDD/.secrets/cred-relay/） |
| upstream/fstdd/kg_sync.py（自带逻辑） | — | 单元 | ADD/UPDATE/DEPRECATE 幂等合并（REQ-003 复用范式） |

## 二、详细测试案例

### 功能 1：experience extract 扩源（C1 / REQ-001）

| 字段 | 内容 |
|------|------|
| **ID** | TC-EEXT-001 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 含 draft 条目的 test-report.md（GIVEN/WHEN/THEN + SHALL） |
| **输入** | `fstdd experience extract`（默认 test-report 源） |
| **预期结果** | SHALL 产出 discovered 草稿条数 > 0；既有路径不退化 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EEXT-002 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 含偏差记录的 design-adjustments.md |
| **输入** | `fstdd experience extract --source design-adjustments` |
| **预期结果** | SHALL 从设计偏离产出 discovered 草稿条数 > 0 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EEXT-003 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 含同 eid 多版本裁决的 adjudication-log.tsv |
| **输入** | `fstdd experience extract --source adjudication` |
| **预期结果** | SHALL 从裁定日志产出 discovered 草稿条数 > 0 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EEXT-004 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-004 |
| **优先级** | P1 |
| **预置条件** | 同一 change 同时含三类源 |
| **输入** | `fstdd experience extract --all` |
| **预期结果** | SHALL 三类源均纳入并按 experience_id 去重合并 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EEXT-005 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-005 |
| **优先级** | P1 |
| **预置条件** | 扩展前可正常抽取的 test-report 夹具 |
| **输入** | 扩展后再次 extract（仅 test-report） |
| **预期结果** | SHALL 结果与扩展前逐条一致（无回归） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 2：非交互自动沉淀（C2 / REQ-002）

| 字段 | 内容 |
|------|------|
| **ID** | TC-EAUT-001 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | DELIVER 激活，当前 change 含三类源 |
| **输入** | `fstdd experience auto-deposit`（非交互） |
| **预期结果** | SHALL 自动抽取并入库 discovered 草稿，不调用交互式 input() |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EAUT-002 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-007 |
| **优先级** | P0 |
| **预置条件** | FSTDD_NO_SHARE=1 |
| **输入** | 触发 auto-deposit |
| **预期结果** | SHALL 跳过抽取与入库（本地 0 新增，且无任意出站） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EAUT-003 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-008 |
| **优先级** | P0 |
| **预置条件** | auto-deposit 已产出若干草稿 |
| **输入** | 检查入库条目 frontmatter |
| **预期结果** | SHALL 每条 lifecycle=discovered，STATUS 不为 shared |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-EAUT-004 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-009 |
| **优先级** | P1 |
| **预置条件** | 非 TTY / 管道运行 |
| **输入** | 执行 auto-deposit |
| **预期结果** | SHALL 不阻塞于标准输入，退出码受控（FSTDD_NO_SHARE 时静默跳过） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 3：中心节点同步（C3 / REQ-003）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECNS-001 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 节点 A 本地经验非空且 FSTDD_NO_SHARE 未置位 |
| **输入** | `fstdd experience sync --push` |
| **预期结果** | SHALL 经 share_experience 第一方传输推到 fstdd-hub（不新建 git 仓） |
| **当前状态** | ❌ 测试缺（BUILD 补，依赖 hub SSH） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECNS-002 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-011 |
| **优先级** | P0 |
| **预置条件** | hub 已聚合 A 的经验 |
| **输入** | 节点 B `fstdd experience sync --pull` |
| **预期结果** | SHALL 增量合并进 B 本地库（复用 _index_lock/_rebuild_index） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECNS-003 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-012 |
| **优先级** | P0 |
| **预置条件** | A 已 push 全部；B 初始为空或子集 |
| **输入** | B 执行 --pull |
| **预期结果** | SHALL 使 B 的 eid 集合与内容逐条等于 A（收敛），不丢条目 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECNS-004 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-013 |
| **优先级** | P1 |
| **预置条件** | B 已与 A 收敛（无新变更） |
| **输入** | B 再次 --pull |
| **预期结果** | SHALL 幂等：无新增、无错误、索引不变 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECNS-005 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-014 |
| **优先级** | P1 |
| **预置条件** | 任意本地库状态 |
| **输入** | `fstdd experience sync --pull --dry-run` |
| **预期结果** | SHALL 仅打印计划，不写本地库、不推/拉 hub |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 4：opt-in 安全档加密（C4 / REQ-004）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESEC-001 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-015 |
| **优先级** | P0 |
| **预置条件** | 安全档启用 + cred-relay 密钥对存在 |
| **输入** | `fstdd experience sync --push --secure` |
| **预期结果** | SHALL 先脱敏再混合加密（RSA-OAEP 包裹 AES-256 密钥 + AES-GCM 正文）后出站 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESEC-002 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-016 |
| **优先级** | P0 |
| **预置条件** | 已脱敏明文载荷 |
| **输入** | cred-relay 混合加密后解密 |
| **预期结果** | SHALL 解密内容与原明文逐字节一致 |
| **当前状态** | ❌ 测试缺（BUILD 补，仿 selftest T1） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESEC-003 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-017 |
| **优先级** | P0 |
| **预置条件** | 加密 rsa_oaep_md=sha256 且 rsa_mgf1_md=sha256 |
| **输入** | 同私钥解密 |
| **预期结果** | SHALL 解密成功（对照 MGF1 sha1 失败，契约锁定） |
| **当前状态** | ❌ 测试缺（BUILD 补，仿 selftest T3b） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESEC-004 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-018 |
| **优先级** | P1 |
| **预置条件** | 一条经验正文 > 318 字节 |
| **输入** | 安全档加密该载荷 |
| **预期结果** | SHALL 走混合加密（RSA 仅包裹 AES 密钥，AES-GCM 加密超长正文） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESEC-005 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-019 |
| **优先级** | P0 |
| **预置条件** | 未启用 --secure 且本地无密钥 |
| **输入** | `fstdd experience sync --push` / `--pull` |
| **预期结果** | SHALL 成功完成明文（已脱敏）同步，无需任何密钥 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 5：冲突策略（C5 / REQ-005）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECON-001 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-020 |
| **优先级** | P0 |
| **预置条件** | 同 eid A/B 内容不同，B 的 updated_at 较新 |
| **输入** | B 执行合并 |
| **预期结果** | SHALL 以 B（updated_at 较新）为胜出版本 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECON-002 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-021 |
| **优先级** | P0 |
| **预置条件** | 同 eid 内容冲突（A 旧 / B 新） |
| **输入** | 合并完成 |
| **预期结果** | SHALL 旧版本写入冲突日志（含 eid/双方 updated_at/落点），不静默丢弃 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ECON-003 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-022 |
| **优先级** | P1 |
| **预置条件** | 多节点并发 sync |
| **输入** | 并发合并 |
| **预期结果** | SHALL 经索引锁保证无半写/竞争损坏 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 6：不引入第三方外发（SC6 / REQ-006）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESAF-001 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-023 |
| **优先级** | P0 |
| **预置条件** | upstream/fstdd/cli/commands/experience.py 的 _cmd_share_single |
| **输入** | 本变更落地后检查该段 |
| **预期结果** | SHALL 仍含 leonai42 + hzddyy 禁用分支，注释与禁用逻辑未被改动 |
| **当前状态** | ❌ 测试缺（BUILD 补，静态 grep） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ESAF-002 |
| **对应 Spec** | experience-center-node-sync/spec.md → Scenario: SC-024 |
| **优先级** | P0 |
| **预置条件** | 本变更新增/修改全部源码 |
| **输入** | 第三方外发字面量审计（grep 已知第三方域名/仓库名） |
| **预期结果** | SHALL 不出现任何指向 leonai42/hzddyy 之外的第三方外发目标（仅第一方 fstdd-hub 出现在 share_experience 既有路径） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| experience extract 扩源 | TC-EEXT-001..005 | — | — | 🔴 全缺 |
| 非交互自动沉淀 | TC-EAUT-001,003 | TC-EAUT-002,004 | — | 🔴 全缺 |
| 中心节点同步 | TC-ECNS-005 | TC-ECNS-001,002,004 | TC-ECNS-003 | 🔴 全缺（依赖 hub） |
| 安全档加密 | TC-ESEC-001..004 | TC-ESEC-005 | — | 🔴 全缺 |
| 冲突策略 | TC-ECON-001..003 | — | — | 🔴 全缺 |
| 不引入第三方外发 | TC-ESAF-001,002（静态） | — | — | 🔴 全缺 |

## 四、回归风险矩阵

| 风险区域 | 本变更改动 | 已有回归保护 | 风险等级 |
|----------|-----------|-------------|---------|
| _load_experience 双块解析 | 复用 consolidation 修复，不改动 | test_experience_parser.py(46) | 🟢 |
| 索引写脏（P2 旧债） | sync 合并经 _save_index + git status 校验 | CP-12 / TC 工作树校验 | 🟡 |
| share_experience 出站脱敏 | 复用既有，新增调用点 | share_experience 自带 OUTBOUND_RESIDUAL_RE | 🟢 |
| 第三方外发误开 | 仅新增第一方 hub 调用 | TC-ESAF-001/002 静态审计 | 🟡 |
| RSA 参数错配 | 新增 _exp_crypto | TC-ESEC-003 仿 T3b 锁定 | 🟡 |
| hub GET 端点形态未确认 | pull 以 inbox GET 优先、scp 兜底 | BUILD 期实测对齐 | 🟡 |

## 五、建议补充顺序

1. **第一优先（部署前必补）**：TC-EEXT-001..003、TC-EAUT-001..003、TC-ECNS-001..003、TC-ESEC-001..003、TC-ECON-001..002、TC-ESAF-001..002（全部 P0）。
2. **第二优先（部署后尽快补）**：TC-EEXT-004..005、TC-EAUT-004、TC-ECNS-004..005、TC-ESEC-004..005、TC-ECON-003（P1）。
3. **第三优先（后续补）**：hub 端可见性监控、冲突日志人工复核流程文档。

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| consolidation 已落地 _cmd_extract 仅从 test-report 抽 draft | 2026-10-11T03:36:00+08:00 | d67c9b1 | upstream/fstdd/cli/commands/experience.py grep |
| K 侧中继自测 T1/T3b：OAEP-SHA256/MGF1-SHA256 round-trip + 318B 上限 | 2026-10-11T05:46:00+08:00 | — | E:/FSTDD/.workbuddy-ai/tmp/credtest/selftest.sh |
| share_experience.py 已具备 publish_via_scp(fstdd-hub) / publish_via_inbox + share_disabled | 2026-10-11T03:36:00+08:00 | d67c9b1 | tools/share_experience.py 只读实测 |
| kg_sync.py ADD/UPDATE/DEPRECATE 幂等合并范式 | 2026-10-11T03:36:00+08:00 | d67c9b1 | upstream/fstdd/kg_sync.py 只读实测 |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖（optional: FINANCIAL_PROJECT=YES 时填充）

> 本变更非金融项目（task_type=code，经验库基础设施），跳过此章节。BUILD Phase B2.5 不强制金融维度。

| 维度 | TC 编号 | 测试要点 | 状态 |
|------|--------|---------|------|
| 幂等 (Idempotency) | TC-ECNS-004 | 重跑 --pull 无副作用 | ☐ |
| 对账 (Reconciliation) | TC-ECNS-003 | B == A 收敛对账 | ☐ |
| 安全 (Security) | TC-ESEC-001..003 | 混合加密 round-trip + 参数锁定 | ☐ |
| 审计 (Audit) | TC-ESAF-001/002 | 第三方外发静态审计 | ☐ |
| 一致性 (Consistency) | TC-ECON-001..003 | updated_at LWW + 冲突日志 + 并发锁 | ☐ |
| 降级 (Degradation) | TC-ESEC-005 | 默认开放档无密钥可用降级路径 | ☐ |
