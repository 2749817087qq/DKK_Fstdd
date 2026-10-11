# Phase Context — 2026-10-11-experience-center-node-sync

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-10-10T21:55:33+00:00)

### 关键决策
- **需求边界确定**：经验库走 hub-and-spoke 中心节点汇聚，而非各平台/各机孤岛；本 change 只做「自动沉淀 + 中心节点同步 + 双模安全」三件（详见 proposal.md）。
- **优先级判断**：P0 —— 4 副本 / 23 漂移的根因（多平台各存一份）未改，残留会持续复发。

### 用户关注点
- 根因校正：漂移的真正乘数是「一台机用 3 个 agent 平台，各存一份经验库」，不是 per-project。
- 务实双模安全：默认开放同步（能用就好），安全敏感者 opt-in 私有/加密通道；不给所有人上 GPG/审批闸门。
- 安全档加密拍板（2026-10-11 05:46）：**复用现成 `.secrets/cred-relay/` 的 RSA 密钥对**，不另起加密方案。

### 被否决的方向
- 新建 hub 上独立 git 仓同步经验 — 原因：与既有 `tools/share_experience.py` 第一方 scp/inbox 链路冗余。
- per-node 密钥 + hub 重加密 — 原因：需 hub 维护密钥目录与重加密逻辑，超出本变更范围。
- git hook 触发自动沉淀 — 原因：项目规则明确「不改 hook」，且 hook 在多平台行为不一致。

### 产出物清单
- proposal.md — Gate 1 已确认，confirmed_at: 2026-10-10T21:55:33+00:00（C1–C5 / SC1–SC6）

### 完整上下文文件清单
- proposal.md：需求背景、能力列表（2 new + 1 modified）、约束条件、成功标准、风险

---

## Phase 2: SPEC (completed 2026-10-11T03:39:04+00:00)

### 关键技术决策
- 决策 1（push 腿）：复用 `tools/share_experience.py` 的 scp(fstdd-hub)/inbox 第一方传输 — 理由：已带强制脱敏 + 出站自检 + 审计 + `share_disabled` 开关；排除：新建 hub git 仓（冗余）。⚠️ 此决策偏离 proposal 原文的「基于 git」表述，已在 Gate 2 向用户披露。
- 决策 2（pull 腿）：新增 `experience sync --pull`，inbox GET 端点优先、scp 兜底，kg_sync 式增量合并 — 排除：git clone hub 经验仓。
- 决策 3（自动沉淀）：新增非交互 `experience auto-deposit` 接进 DELIVER，honor `FSTDD_NO_SHARE`，产物一律 `lifecycle=discovered` — 排除：git hook 触发。
- 决策 4（安全档）：新增 `_exp_crypto`，复用 cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256 混合加密（RSA 包裹随机 AES-256 密钥 + AES-GCM 正文，因 318B 载荷上限），出站前先脱敏 — 排除：per-node 密钥 + hub 重加密。
- 决策 5（冲突）：`updated_at` 末写胜 + 显式冲突日志，绝不静默覆盖（重演 `_load_experience` 静默丢字段教训）。

### 经验触发记录
- EXP-2026-0013（contract_gap：声明形态与解析器实际不覆盖）— 在 extract 扩源场景触发，已纳入 SC-001..005 的 parametrized 覆盖。
- consolidation 变更的「双块 frontmatter 静默丢字段」教训 — 已纳入 REQ-005 / SC-021（冲突必留日志）。

### 已知坑点 / 注意事项
- **OAEP 参数**：必须显式 `rsa_oaep_md:sha256` **且** `rsa_mgf1_md:sha256`，否则 MGF1 默认 sha1 导致解密失败（cred-relay selftest T3b 已验证）→ TC-ESEC-003 契约锁定。
- **318B 上限**：RSA-3072 OAEP-SHA256 明文载荷上限 318 字节 → 超限必须走混合加密（SC-018 / TC-ESEC-004）。
- **索引写脏**：`experience list` 会重写被跟踪的 `.experience-index.yaml`；sync 合并须经 `_save_index(newline="")` 且落盘后 `git status` 校验（CP-12）。

### 未解决问题（待 Phase 3 验证）
- **hub inbox GET 端点形态未确认**：当前假设 = 与 push 的 POST 端点对称；验证方式 = BUILD 期实测对齐，必要时降级为 scp 拉取。

### 产出物清单
- design.md — Gate 2 已确认
- specs/experience-center-node-sync/spec.md — 24 个 Scenario，confirmed
- canonical/specs/code + agent YAML — 6 REQ / 24 SC / CP-1..CP-12
- test-plan.md — 24 个 TC-ID，confirmed（P0 17 / P1 7）

### 完整上下文文件清单
- design.md：架构决策（Decisions 1–5）、Architecture、风险与缓解（Risks/Trade-offs）
- specs/experience-center-node-sync/spec.md：GIVEN/WHEN/THEN/SHALL 行为规格
- test-plan.md：TC-ID 映射、测试策略、执行矩阵、回归风险矩阵

---

## Phase 3: BUILD (in_progress)

> V3.0.5：SLICE / BUILD / VERIFY 三阶段合一。以下为三小节内容。

### 切片方案（Slice）
- Slice 1（P0 · 组1）：extract 扩源 — 5 TC（TC-EEXT-001..005）
- Slice 2（P0 · 组2，依赖 1）：auto-deposit 非交互沉淀 — 4 TC（TC-EAUT-001..004）
- Slice 3（P0 · 组1）：_exp_crypto 混合加密 — 5 TC（TC-ESEC-001..005）
- Slice 4（P0 · 组2，依赖 3）：中心节点 sync push/pull/merge — 5 TC（TC-ECNS-001..005）
- Slice 5（P0 · 组3，依赖 4）：同步冲突策略 — 3 TC（TC-ECON-001..003）
- Slice 6（P0 · 组1）：第三方外发审计 — 2 TC（TC-ESAF-001..002）
- 并行组：组1 = {1,3,6}；组2 = {2,4}；组3 = {5}

### 风险提示
- Slice 4 涉及跨系统 hub 传输与合并语义，风险最高（🟡）。
- Slice 3 涉及加密参数，须锁定契约（🟡）。

### 实现决策（非设计偏离）
- 新增 `upstream/fstdd/cli/commands/_exp_sync.py`：**传输层与合并层解耦**。
  传输适配器两种实现同接口：`hub_dir=<path>` 本地目录适配器（离线/测试/手工中转）
  与第一方传输适配器（push = `tools/share_experience.py`；pull = scp hub `fstdd-inbox`）。
- 加密实现走 **openssl CLI 子进程**（环境无可用 `cryptography`），而非库调用。

### 设计偏离汇总
<!-- 详见 pending-adjustments.yaml / design-adjustments.yaml -->
- ADJ-001（Major）：正文层 AEAD 由 AES-256-GCM 改为 AES-256-CTR + HMAC-SHA256（encrypt-then-MAC）
- ADJ-002（Minor）：design.md 引用的「省略 rsa_mgf1_md 会失败」在 openssl 3.5.7 上不成立

### 经验触发记录
- EXP-2026-0013（契约断层）→ 抽取源扩至三类时以 parametrized 契约测试锁定
- consolidation 的「静默丢字段」教训 → REQ-005 冲突日志（TC-ECON-002）

### 切片完成状态
| Slice | TC覆盖 | 新增测试 | 状态 |
|-------|--------|---------|:---:|
| 1 extract 扩源 | 5/5 | 5 | ✅ |
| 2 auto-deposit | 4/4 | 4 | ✅ |
| 3 _exp_crypto | 5/5 | 5 | ✅ |
| 4 中心节点 sync | 5/5 | 5 | ✅ |
| 5 冲突策略 | 3/3 | 3 | ✅ |
| 6 外发审计 | 2/2 | 3 | ✅ |

### 测试结果摘要（Verify）
- 待 C2 全量质量检查回填

### 设计偏离确认
- 2 条偏离已在 pending-adjustments.yaml 记录，Gate 3 待披露

### 产出物清单
- slices.md — 6 个切片，依赖关系已标注
- tasks.md — 7 组任务
- 新增源码：`upstream/fstdd/cli/commands/_exp_crypto.py`、`_exp_sync.py`
- 修改源码：`upstream/fstdd/cli/commands/experience.py`、`upstream/fstdd/cli/__init__.py`
- 新增测试：6 个文件（extract_sources / auto_deposit / exp_crypto / experience_sync / sync_conflict / no_third_party_egress）

### 完整上下文文件清单
- slices.md：切片计划与完成状态
- pending-adjustments.yaml：设计偏离详细说明
- test-report.md：测试结果与失败模式检查
- 关键源文件：`upstream/fstdd/cli/commands/{experience,_exp_crypto,_exp_sync}.py`

---

## Phase 4: DELIVER (pending)

### 归档
- 待填

### 版本
- 待填

---

## Current: Phase 3 BUILD (in_progress)

### 当前状态
- Phase 1/2 均已 Gate 确认；`current_phase=build`，Guard 已放行 Edit/Write。等待用户选择 Phase 3 执行模式（长程/普通）。

### 下一步
- 用户选模式 → 切片规划 → 逐切片 TDD 实现 → 质量验证 → Gate 3。
