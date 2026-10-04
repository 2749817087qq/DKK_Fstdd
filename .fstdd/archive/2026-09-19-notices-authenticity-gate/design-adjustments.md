# design-adjustments.md — 设计偏离记录

> change: `2026-09-19-notices-authenticity-gate`
> 约束依据：AGENTS.md 铁律 2 —— 绝不静默修改设计，偏离必须记录。
> 说明：以下偏离均发生于 Gate 1 之后、Gate 2 确认之前，属于 Phase 2 内的自我修正。
> Gate 2 尚未批准，本文件在 Gate 2 时会一并提交用户审阅。

## AD-1 ｜ 锚定等级 L1 → L3（Step 4.5 锚定评估）

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 2 Step 4.5 |
| 变更 | `canonical/proposals/*.yaml` 的 `anchoring.level` 由 `L1` 改为 `L3`，并补 3 条 `reference_changes` |
| 触发原因 | 提案 `critical.is_critical: true` 且 `risk_assessment` 无 true → 按 Step 4.5 规则「默认 critical → 至少 L3」。L1 低于最低需求，若不修则 **Gate 2 阻塞** |
| 补充的参考实现 | ① `FSTDD003-sliceS2S3`（本节点对 `tools/` 做 TDD 改动的既有做法）；② `EXP-20260918-CODE-1`（「宁可可见、不可沉默」原则来源）；③ `FSTDD003收-撤回令-伪造署名指令.md`（K 授权，处置边界权威依据） |
| 影响 | 无功能影响；仅提高规格锚定强度，Phase 3 实现自由度相应下降 |

## AD-2 ｜ 行为规格按 capability 拆分为 2 个文件

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 2 Step 5.5 设计审查（文档一致性检查） |
| 变更 | 删除 `canonical/specs/code/2026-09-19-notices-authenticity-gate.yaml`（单文件合并 2 个 capability），拆为 `notice-authenticity-verification.yaml`（REQ-001..005 / SC-001..015，15 个 Scenario）与 `notice-execution-pipeline.yaml`（REQ-006 / SC-016..018，3 个 Scenario） |
| 触发原因 | 模板 `.fstdd/templates/canonical/spec.yaml` 的 `meta.capability` 为**单数**字段，skill Step 4b / Step 7 明确要求「每个 capability 一个文件」；原文件的 `capability` 是逗号拼接的两个名字，违反约定 |
| 验证 | 拆分后用 `yaml.safe_load` 逐条比对：原 18 个 (REQ, SC) 组合**完全一致、无重复、无丢失**；15 + 3 = 18 |
| 影响 | 无内容影响；文件路径变化，`.canon-index.yaml` 与 `test-plan.md` 已同步更新 |

## AD-3 ｜ agent_spec 补模板字段 + 新增 rollback 段

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 2 Step 5.5 设计审查（文档一致性检查） |
| 变更 | ① `steps[]` 每项补 `id` 与 `description` 字段（原先把检查点编号写在 `action` 文本里）；② 新增模板定义的 `assertions[]` 类型化断言（`exit_code` / `stdout_contains` / `stderr_contains` / `diff_empty` / `file_exists`），原文本校验保留为 `verify` 与 `assertions_detail`；③ 新增模板定义的 `rollback.steps[]` 段 |
| 触发原因 | 模板 `.fstdd/templates/canonical/agent_spec.yaml` 明确要求 `steps[].id`、`steps[].description`、`steps[].assertions`（类型化）与顶层 `rollback:`，原文件三者皆缺 |
| 说明 | 保留 `verify` 自由文本字段（模板未定义但 Phase 3 需要 pytest 级校验描述），以及 `assertions_detail`（承载 Scenario 级别的断言明细） |
| 影响 | 无功能影响；Phase 3 消费 CP 检查点时可直接按 `id` 索引 |

## AD-4 ｜ design.md 架构图 stdout 键 3 → 4

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 2 Step 5.5 设计审查（术语一致性检查） |
| 变更 | `design.md` Architecture 段架构图的 `stdout:` 行由 3 键（`results` / `quarantined` / `warnings`）补为 4 键（新增 `exit_code`） |
| 触发原因 | `SC-015` 明确 `--json` 顶层键 **恰好** 为 `results`、`quarantined`、`warnings`、`exit_code` 四键。架构图漏写 `exit_code` 会让 Phase 3 实现者误以为 3 键即可，与测试断言冲突 |
| 影响 | 文档与规格对齐；`exit_code` 是轮询自动化判定「本次是否需要人工介入」的字段，不可省 |

## AD-5 ｜ SC-011 / SC-012 / SC-013 补 `and: []` 字段

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 2 Step 5.5 设计审查（Scenario 完备性检查） |
| 变更 | 三个 Scenario 显式补 `and: []` |
| 触发原因 | 模板中 `and: []` 是**必填字段**（"附加条件，最多 5 条"），允许为空数组但不允许缺字段。原文件这三个单断言 Scenario 直接省略了该键 |
| 影响 | 无语义影响；格式合规 |

## 汇总

| 编号 | 类型 | 位置 | 严重度 | 是否需用户裁定 |
|------|------|------|--------|---------------|
| AD-1 | 规格升级 | proposal.yaml | 低（规则强制） | 否 |
| AD-2 | 文件结构 | specs/code/ | 低 | 否 |
| AD-3 | 模板合规 | specs/agent/ | 低 | 否 |
| AD-4 | 文档一致性 | design.md | 低 | 否 |
| AD-5 | 格式合规 | specs/code/ | 低 | 否 |

**未发生功能层面的设计偏离**：5 项均为格式、结构与文档一致性问题，不改变 D1–D7 任何技术决策，
不改变 18 个 Scenario 的语义，不改变 21 个 TC 的断言。

## Gate 2 之后的追加记录位

Phase 3（BUILD）执行期间若出现偏离（技术阻塞、设计偏离、迭代超限），一律追加到本文件的
「Phase 3 记录」小节，不得静默修改设计。当前无 Phase 3 记录。
