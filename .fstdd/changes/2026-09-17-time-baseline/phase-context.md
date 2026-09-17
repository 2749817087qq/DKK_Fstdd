# Phase Context — 2026-09-17-time-baseline

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  每章节末尾附"完整上下文文件清单"，需要更多细节时回溯原文。

  ⚠️ 此文件由 AI 自动维护，人类不应手动编辑。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-09-17T23:07:38+08:00)

### 关键决策
- **需求边界确定**：本 change 只做**时间基线的记录与校验**（记录 / 统一 / 标注 / 检测 / 报告），
  不做自动校时、不做时间戳签名、不回溯历史归档、不规定统一时区
  （详见 proposal.yaml `non_goals` 6 条）。
- **优先级判断**：P0 —— 时间基线是**横切契约**，越晚补越贵。且 D哥 指出这是
  "使用 agent 时普遍缺失"的系统性问题，而非本项目个案。
- **模式判定**：复杂度评分 **13 分**（文件 2 + 行数 3 + capability 2 + 风险 4 + 数据/API 2 + 安全 0）
  → **thorough**（≥8）。

### 用户关注点
- D哥 在 Gate 1 明确要求：「我使用 agent 的时候，很多都不建立时间基线，这个需要进入到 FSTDD 中去。」
- 补充范围：「**3 台机器及 FSTDD 自身的时钟对齐**」—— 即不只是本机，而是整个协作面。
- 明确要求把**自身**也纳入治理范围（不是只给别的项目立规矩）。

### 被否决的方向
- 自动校时 / 部署 NTP：本变更只做**检测与报告**，不做自动修正（non_goal）。
- 时间戳密码学签名：属审计链议题，另立。
- 历史归档回填：只处理活跃 change 与模板（避免改动历史产物、避免巨大 diff）。
- 规定全组织统一时区：只要求**显式声明、可比较**（UTC 是落地选择，不是强制时区）。
- 修复 `extract-proposal` 的 capabilities 解析缺陷：同属工具链缺陷，但为独立议题。

### 产出物清单
- `proposal.md` — Gate 1 已确认，`confirmed_at: 2026-09-17T23:07:38+08:00`
- `canonical/proposals/2026-09-17-time-baseline.yaml` — 246 行，8 项变更 C1–C8、
  4 个新增 capability、7 个修改 capability、7 条 constraints、4 项 risk_areas、
  6 条 non_goals、8 条 success_criteria
- `.fstdd.yaml` — `mode: thorough` / `complexity_score: 13` / `score_confidence: preliminary`

### 完整上下文文件清单
- `proposal.md`：需求背景、能力列表、约束条件、成功标准
- `canonical/proposals/2026-09-17-time-baseline.yaml`：同上（AI 主读的结构化源）

---

## Phase 2: SPEC (completed 2026-09-17T23:22:20+08:00)

### 关键技术决策
1. **基线写进 `.fstdd.yaml` 顶层 `baseline:` 块** — 理由：该文件已是 change 权威状态文件、
   已含 Gate 审计四字段、已被多处工具读写，不新增文件类型。
   排除：独立 `baseline.yaml`（多一处同步点）／写进 canonical proposal（运行时状态混进文档，
   且会连带触发 Human View 重生成）／外部注册表（跨机不可读）。
2. **Gate 1 确认时由 CLI 自动写基线 + 提供幂等回填** — 理由：Gate 1 才是"决定要做"的时刻；
   凡依赖自觉的字段必然漏填（本 change 要治的就是这个病）。
   排除：`fstdd new` 时建立（那时还没有 proposal，`base_git_sha` 无意义）／纯人工填／每个 Gate 都刷新（基线漂移）。
   ⚠️ **回填必须取 Gate 1 的 `confirmed_at`**，不得取回填动作时刻 —— 否则基线记录本身就是假信息。
3. **时间戳统一 UTC（`+00:00`）** — 理由：控制面 `tools/fstdd_hub.py:99` 已是 UTC，
   统一到既有的那一种改动面最小；跨机比较/排序无需换算。
   排除：本地 `+08:00`（三机 offset 可能不同）／双写（必然不同步）／仅日期（粒度不足）／Unix 整数（与既有产物形态断裂）。
   显示层由 Human View 转本地，存储层不动。
4. **时钟巡检三态判定（可接受 / 超限 / 无法测量），退出码 0/1/2** — 核心决策。
   采用**最小 RTT 样本**（非平均），并把**误差上界与容差比较**（不只比偏移）。
   理由：实测 RTT 抖动 5.1–6.2s，取平均会把网络抖动混进偏移估计；
   若 `err > TOLERANCE` 则测出的偏移完全落在噪声里，此时报"可接受"是伪结论。
   排除：`ping`（100% 丢包）／不算误差直接比 `date`／部署 NTP（non_goal）／
   用控制面 `/health` 的 `time`（单采样、无误差估计、与控制面可用性耦合）／只报偏移不报三态。
   **本 change 的预期实测结论就是「无法测量」**（err ≈ 2.7s > 2.0s）—— 这是诚实的结果，不是失败。
5. **新增 CLI 子命令 `fstdd baseline`**（`establish` / `show` / `check`）— 理由：分发
   （CLI 已随仓提交、已在 3 台机器上）、结构化输出、参数与帮助自动获得。
   ⚠️ **注册需五处同时到位**（动态导入字符串，EXP-20260915-B1）：`COMMAND_GROUPS` /
   `_CMD_HELP` / `add_parser` / 命令分发表 / 命令模块文件。少一处不报错，只表现为"命令不存在"。
   因此验收**必须真实执行命令**，禁止只 grep 字符串（EXP-20260917-A2）。
6. **naive 时间戳检测器按「值」判，不按「调用」判** — L1 值层（产物字段值）为权威，
   L2 源层（AST + 数据化豁免清单）仅辅助。
   理由：实测 `datetime.now()` 相关命中 ~48 处 / 19 文件，其中真正的持久化时间戳字段约 25 处 / 15 文件；
   直接 grep 会把 4 类豁免（单调钟 / 标识符 / 纯时间差 / 渲染参数）全报成违规 → 20+ 条误报
   → 检测器立刻失去可信度（EXP-20260917-A1）。
7. **DC-HASH 改为归一后内容哈希** — `sha256(normalize_eol(bytes))[:16]`，与 `tools/verify_eol.py`
   的 `normalize()` 同口径。一次性迁移只覆盖活跃 change 与项目级 canonical，**归档不回溯**。
   排除：双哈希字段（必然不同步）／verify 时两种算法都试（等于不解决，校验退化为恒真）／
   放弃哈希（失去"是否同步"的检测能力）／强制归一工作区（治不了根因，仍依赖自觉）。
8. **模板必须同时改两处**：`upstream/.fstdd/templates/**`（`fstdd init` 安装源）
   与 `.fstdd/templates/**`（本仓自身）。理由：EXP-20260915-B2（只改引用文本、漏掉被引用实体）。
9. **宪法条款 + 机器检查双落地** — 宪法新增 `### 7. 时间基线`（**两份副本必须同步**：
   仓根与 `.fstdd/memory/`），同时 `fstdd validate` 加基线完整性检查（**warning 级，不阻断**）
   与 skill 的 Gate 前自检清单。理由：纯文档条款无法被机器验证；
   而 Gate approve 硬阻断会让本 change 自身（存量无基线）立即自锁。

### 经验触发记录
- `EXP-20260917-A1`（high，误报驱动修复）→ 触发于 Decision 6，已纳入 SC-013/SC-014/SC-015 的测试覆盖
- `EXP-20260915-B1`（high，动态导入字符串）→ 触发于 Decision 5，已纳入 SC-038/SC-039
- `EXP-20260915-B2`（medium，漏掉被引用实体）→ 触发于 Decision 8/9，已纳入 SC-036/SC-033
- `EXP-20260917-A3`（high，恢复现场写在正常路径）→ 触发于测试原则 3
- `EXP-20260917-A4`（high，环境注入看起来生效其实没生效）→ 触发于 Decision 5 的验收口径
- `EXP-20260915-B4`（high ×2，自研产物没纳入分发入口）→ 触发于 Decision 5（用 CLI 而非独立脚本）
- `EXP-20260915-A6`（high，照单执行去修不存在的问题）→ 触发于 Step 5.5 审查（首轮 13 项中 7 项是判据误报）
- 知识图谱风险预测：**数据不足（0 节点 < 3）→ 按 Step 2.5 跳过**

### 已知坑点 / 注意事项
- **CLI 五处注册**：新增命令必须五处同时到位，否则开发期不报错、运行时"命令不存在"。
- **模板双源**：改模板必须两处同步。
- **宪法双份**：改宪法必须两份同步（本项目历史上已因手工 cp 发生过两次漂移）。
- **`structure` 系列命令的 cwd 语义与其他命令相反**：`canon`/`gate`/`phase`/`archive` 要求项目根，
  而 `structure` 要求以 `.fstdd/` 为 cwd（`structure.py:30/63` 写 `project_root / "changes" / <name>`）。
- **归档后 `canon verify` 找不到 change 级 canonical**（`canon.py:12-14` 只解析 `.fstdd/changes/<change>/canonical`）
  → 需要在临时镜像中验证。
- **`canon` 渲染 Human View 会丢弃 `out_of_scope` / `why.evidence` / `constraints` / `risk_areas` / `non_goals`**
  → `extract-proposal` 因此恒返回空 `capabilities`（已实测复现），Phase 2 的结构化数据必须直接读 canonical YAML。
- **本机经 ssh 的命令会执行两次** → 巡检采样必须按"收到的有效读数条数"计数，不按"发起的调用次数"。
- **`core.autocrlf=true`** → CLI 写入的文件为 CRLF，提交前必须归一为 LF；且 `git status` 说 `M` ≠ 内容变了
  （可能是 index 的 stat 缓存过期）。

### 未解决问题（待 Phase 3 验证）
1. **本机↔服务器时钟偏差的真实判定** — 当前假设：RTT ~5.5s → `err ≈ 2.7s > 容差 2.0s`
   → 判定为「无法测量」。验证方式：实现后对服务器实际执行 `fstdd baseline check`。
2. **另 2 台机器是否可达** — 当前假设：不可达（`~/.ssh/config` 中只有 `fstdd-hub` 一个 Host）
   → 会被标记「无法测量」。验证方式：巡检时观察是否被正确标记且不导致命令挂起。
3. **一次性迁移 `source_hash` 的完整影响面** — 当前假设：只有活跃 change 与项目级 canonical
   需要重生成，归档不回溯。验证方式：迁移后对活跃 change 跑 `canon verify`，并确认归档 change 未被改动。
4. **`traceability` 计数器从零更新为真实值后是否有下游消费方** — 当前假设：无 CLI 命令读取它。
   验证方式：全仓 grep。

### ⚠️ Phase 2 期间发现的「陈旧状态」缺陷（按 D哥 既定原则：记录为后续 change，不在本 change 内修）
1. **`current_phase` 字段陈旧** —— Gate 2 确认后，`.fstdd.yaml` 同时存在
   `current_phase: understand`（陈旧）与 `phases.spec.status: completed`（已更新）。
   后果：`fstdd phase status` 会在 spec 已完成之后仍提示「Next: Phase 2: SPEC」。
   **本 change 的 proposal `why.evidence (8)` 正是用这个缺陷论证"状态本身没有基线"，
   而它在 Phase 2 结束时当场复现了一次**（已人工修正为 `spec`）。
   → 与 C1「基线契约」同族，但**不在本 change 范围**（C1 只覆盖 `baseline` 块）。
2. **`traceability` 计数器从不更新** —— `spec_scenarios` / `tc_cases` / `test_functions`
   仅在 `new.py:70` 与 `batch.py:584` 初始化为 0，**全仓无任何 CLI 命令写入**。
   后果：这些字段永久为 0，即"产物无法回答基于什么状态"的又一实例。
   → 已在本 change 内人工填入真实值（47 / 52），但**修复机制属后续 change**。
3. **`fstdd validate` 的 AND 判据口径错误，产生必然误报** ——
   `upstream/fstdd/cli/commands/validate.py:62`：
   ```python
   and_count = len(re.findall(r"\*\*AND\*\*", content))   # content = 整个 spec.md
   if and_count > 5:
       warnings.append(f"{spec_file.name}: AND 数量 ({and_count}) 超过上限 (5)")
   ```
   用**整个文件**的 AND 总数与**每 Scenario** 的上限 5 比较 → **任何含 ≥6 个 Scenario
   且每个 Scenario 都有 AND 的规范文件都必然告警**。本 change 的 7 份 spec.md 全部命中：
   | spec.md | 全文 AND 总数 | Scenario 数 | **每 SC 最大值** | 是否真超限 |
   |---|---|---|---|---|
   | artifact-templates | 13 | 6 | **3** | 否 |
   | canon-dual-track | 13 | 6 | **3** | 否 |
   | clock-alignment | 21 | 9 | **3** | 否 |
   | constitution | 10 | 5 | **3** | 否 |
   | evidence-provenance | 10 | 5 | **2** | 否 |
   | time-baseline | 18 | 9 | **3** | 否 |
   | timestamp-normalization | 15 | 7 | **3** | 否 |
   `validate` 退出码仍为 0（warning 不失败），但会输出 7 条**纯误报**。

   ⚠️ 讽刺之处：**同一文件的 `:69-72` 已经为 TC-ID 修过完全同类的问题**，注释写着
   「只统计「案例定义行」的 ID，而不是全文出现次数……按全文计数会把这种引用误判为
   「重复的 TC-ID」，使模板规定的格式反而无法通过校验」—— 判据口径错误的教训当时已总结，
   却没有应用到隔壁的 AND 检查。

   → 这正是 `EXP-20260917-A1`（high，「误报累积后使用者会养成忽略红叉的习惯，
   真正的失败反而被漏掉」）的又一实例，也正是本 change 的 SC-014 所要防的那类失效。
   **按 D哥 既定原则记录为后续 change，不在本 change 内修**（本 change 范围是时间基线，
   不含 validate 的判据修正）。修复方向：按 Scenario 分块计数，与 `:69-72` 的做法一致。

### 产出物清单
- `design.md` — 35.3 KB，9 项技术决策（含备选与排除理由）+ 3 张架构图 + 10 项风险 + 证据基础表
- `canonical/specs/code/*.yaml` — **7 份**（按 capability 分文件）：21 REQ / 47 Scenario
- `canonical/specs/agent/2026-09-17-time-baseline.yaml` — 20 个 CP 检查点 + 6 条 expected_outcomes
- `specs/<capability>/spec.md` — **7 份** Human View（Gate 2 自动生成）
- `test-plan.md` — 36.9 KB，**52 TC**（47 个 1:1 映射 SC + 5 个跨切面），P0 43 / P1 9 / P2 0
- `.fstdd.yaml` — Gate 2 审计四字段 + `current_phase: spec` + traceability 真实值

### 规模指标（Gate 2 展示用）
| 指标 | 值 |
|---|---|
| Spec Requirements | 21 |
| Spec Scenarios | 47 |
| 置信度分布 | 高 43 / 中 4 / 低 0 |
| TC Cases | 52 |
| 优先级 | P0 43 / P1 9 / P2 0 |
| 锚定评估 | 需求 L2（`cross_system: true`），提案 L2 → **通过** |
| Step 5.5 审查 | 4 维；首轮 13 项 → 分类处置后 **0 项** |

### 完整上下文文件清单
- `design.md`：架构决策（Decisions 9 项）、capability↔slug 映射表、风险与缓解（R1–R10）、证据基础表
- `canonical/specs/code/*.yaml`：21 REQ / 47 Scenario 的 GIVEN/WHEN/THEN 规格（AI 主读）
- `specs/<capability>/spec.md`：同上（人类阅读视图，Gate 2 生成）
- `canonical/specs/agent/*.yaml`：20 个 CP 验证检查点
- `test-plan.md`：TC-ID 映射、测试策略、测试执行矩阵、回归风险矩阵、补充顺序

---

## Current: Phase 2 SPEC ✅ → Phase 3 BUILD 待启动

### 当前状态
- Phase 1 UNDERSTAND ✅（Gate 1 `2026-09-17T23:07:38+08:00`，confirmed_by: dialog）
- Phase 2 SPEC ✅（Gate 2 `2026-09-17T23:22:20+08:00`，confirmed_by: dialog）
- 校验：`fstdd validate` 通过；`fstdd canon verify` **2/2 通过**；change 目录全部 `i/lf w/lf`
- 执行模式：`mode: thorough`（阶段缩放）+ **全自动长程模式**（交互模式，D哥 已选）

### 下一步
1. **Step 8a**：生成长程模式一次性预授权清单并取得 D哥 确认
2. 更新 `.fstdd.yaml` 的 `long_range` 块（`enabled: true` / `mode: full_auto` / `pre_auth_*`）
3. 提交并推送 Phase 2 产物
4. 进入 **Phase 3 BUILD**：切片规划 → TDD 实现（52 TC）→ 质量验证
   - thorough 缩放：`pass_k=3` / `review_agents=3` / `subagent_security+perf` /
     `plankton=proactive` / `test_scope=full_multi_version` / `archive=full`
5. **Gate 3 仍为强制确认门，不自动跳过**
