# Phase Context — 2026-09-17-mirror-failure-alert

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  每章节末尾附"完整上下文文件清单"，需要更多细节时回溯原文。

  ⚠️ 此文件由 AI 自动维护，人类不应手动编辑。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-09-17T15:21:49)

### 关键决策

- **需求边界确定**：只做镜像失败的**告知**，不做**自愈**（重试 / 补偿另立）；只复用控制面既有
  `POST /messages`，**不新增端点、不改控制面代码**（详见 proposal.md 的 out_of_scope）。
- **优先级判断**：P0 —— 上一轮 change 的 design 已把它列为后续项；且实测 `mirror.log`
  WARN 次数为 **0**，说明这条告警路径**从未被真实触发过**，其有效性是未经检验的假设。

### 用户关注点

- **时间基线（D哥 在 Gate 1 确认时明确提出）**：
  > 「我使用 agent 的时候，很多都不建立时间基线，这个需要进入到 FSTDD 中去。」
  并补充范围：「还有 3 台机器及 FSTDD 自己的时钟对齐。」
  - 处理方式已与 D哥 确认：**本 change 推完 spec 后再另开 change**，不在本 change 夹带。
  - 现状证据（本阶段已实测）：宪法搜「时间/时效/基线/新鲜」零命中；`base_git_sha` 只存在于
    hub 的 tasks 表（即**只有被分派的任务**有基线，本地发起的 change 完全没有）。

### 被否决的方向

- 服务器定时巡检（systemd timer）—— 引入最长一个巡检周期的滞后窗口，且需额外状态去重；
  实测服务器**无任何 fstdd timer**，为这件事新增常驻服务不划算
- 失败时让钩子返回非零退出码 —— 与「真值源已更新即 push 成功」语义冲突，
  会制造「报失败但其实成功」，并诱导使用者 `--force` 重推
- 新增 `POST /alerts` 端点 —— 需改控制面并重新部署；而 `notice` 已在 `MESSAGE_KINDS` 中
- 把故障态写进控制面 SQLite 或裸库 ref —— 前者引入控制面依赖，后者把运维状态混进代码内容

### 产出物清单

- proposal.md — Gate 1 已确认，confirmed_at: `2026-09-17T15:21:49`（confirmed_by: `dialog`）
- canonical/proposals/2026-09-17-mirror-failure-alert.yaml — 6 项 what_changes /
  3 新 + 2 修改能力 / 10 条 success_criteria / 6 条 out_of_scope

### 完整上下文文件清单

- `proposal.md`：需求背景、能力列表、成功标准
- `canonical/proposals/2026-09-17-mirror-failure-alert.yaml`：含 `why.evidence`
  （服务器只读实测数据）与 `out_of_scope` —— **注意这两项不会出现在渲染出的 proposal.md 中**

---

## Phase 2: SPEC (completed 2026-09-17T16:06:38)

### 关键技术决策

| # | 决策 | 理由 | 排除的备选 |
|---|------|------|-----------|
| 1 | **四层告警通道**：tee 回显 / mirror.log / mirror-failed.flag / 控制面 notice | 四种接收方需求互不替代（当次推送的人 / 事后追溯 / 自动化程序 / 协作层其他节点） | 只做回显、只做控制面消息、只做定时巡检、走退出码 |
| 2 | **故障标记用独立文件** | 最小依赖（纯文件）、语义简单（存在即故障）、任何工具可读 | 写进 SQLite / 写进日志字段 / 用退出码 / 写进裸库 ref |
| 3 | **复用 `/messages` + 注册基础设施节点身份** | `notice` 已在契约中，**控制面零代码改动**；且解决了 `from_node_id` 必须已注册的硬约束 | 新增 `/alerts` 端点、冒充某个 agent 节点、不接控制面 |
| 4 | **上报尽力而为，不制造新单点** | 控制面是单机服务，强依赖它等于用一个单点解决另一个单点；钩子在推送关键路径上 | 失败重试直到成功、本地排队下次补发 |
| 5 | **告警不走退出码，钩子恒 `exit 0`** | 真值源已更新，push 语义上是成功的；否则诱导 `--force` 重推 | 失败 `exit 1`、阻塞等待人工确认 |
| 6 | **文档与能力同批交付** | 现有文档主动教人「人工 tail 日志」，能力升级而文档不动会**教人做已被取代的事** | 文档另开 change、只加一句「已支持告警」 |

### 经验触发记录

- **`EXP-20260915-B4`**（自研产物没纳入分发入口 —— 本地能跑，别人装不到 / 装了跑不起来；
  high，×2）→ 触发于「`tools/check_mirror.sh` 的使用者是分布在 **3 台机器上的 6 个 agent**，
  而非作者本人」。已纳入 **REQ-009 / SC-018** 与 **TC-MFA-024 / 025**（可执行位 + 最小依赖 +
  干净克隆可用 + 前置条件缺失时明确提示）。
- **`EXP-20260915-A5`**（验证脚本内部执行了会修改仓库状态的命令，造成副作用并污染自身后续判断）
  → 触发于「巡检命令经 ssh 执行，而本环境经 ssh 的命令会**执行两次**」。
  已纳入 **TC-MFA-014**（巡检命令只读且幂等，断言执行前后端状态不变）。

### 已知坑点 / 注意事项

- **⚠️ `DC-HASH` 与 EOL 归一相互矛盾（本阶段实测发现，重要）**
  - `canon verify` 的 `DC-HASH` 对 YAML **原始字节**做 `sha256(...)[:16]`
    （`upstream/fstdd/cli/commands/canon.py:299`）
  - 而 `.gitattributes` 规定 `* text=auto eol=lf` → **git 中存的是 LF**
  - CLI 以 **CRLF** 写文件 → 归一为 LF 后 `DC-HASH` 必然失配；
    反过来在 CRLF 工作区生成，则记录的哈希与 git 中的 LF blob 不一致
  - **后果：干净克隆必然校验失败。** 已归档 change 实测受影响：
    `2026-09-17-server-bare-repo-mirror` 的 `proposal.md` 记录 `87af3c0361efbf5d`（CRLF 工作区），
    而其 LF blob 实际为 `c041bff129ef7268`
  - **本 change 的处理**：先把 YAML 归一为 LF，**再** `canon generate --type proposal`
    重新渲染 `proposal.md` → 记录哈希 `a0f8101377c55cd6` = LF blob 哈希，干净克隆可校验
  - **建议**：另立 change，把 `DC-HASH` 改为「先做 EOL 归一再哈希」（内容哈希而非字节哈希），
    并补一条「干净克隆可校验」的测试（当前 `extract_proposal` / `canon` 的往返**零测试覆盖**）
- **`extract-proposal` 对 canon 渲染的 proposal.md 解析不出 capabilities**（同类契约断层）：
  渲染器把 `### New Capabilities` 直接挂在 `## What Changes` 之下
  （`canon.py:334-349`），而解析器要求先有 `## Capabilities`
  （`extract_proposal.py:40`）→ 恒返回空 `capabilities`，**任何 change 都拿不到能力清单**。
  且 `extract_proposal` / `canon` 往返**无任何测试引用**（592 passed 掩盖了它）
- 远端经 ssh 的命令**执行两次** → 巡检命令必须只读幂等、部署动作必须幂等
- 模拟镜像失败后**必须恢复现场**（已写进 agent spec 的 preconditions）

### 未解决问题（待 Phase 3 验证）

- **控制面 `POST /messages` 是否支持 `idempotency_key` 去重**：design 的风险表假设可用。
  Phase 3 需实测；若契约不支持，退化为「同一故障窗口只投递一次」的本地节流
- **`mirror.log` 因回显而增行**是否需要日志轮转：本变更不处理，记录为后续项
- **`.fstdd/archive/` 下 18 个既存混合态文件**（`git ls-files --eol` 口径 `i/lf w/crlf`）：
  已提交且工作区干净，**非本 change 引入**，待 D哥决定是否另立 change
- **上一轮 change 的 `proposal.md` 哈希失配**：同属 `DC-HASH` 缺陷，需与上一条一并决策

### 产出物清单

- `design.md` — 6 个 Decision（含备选方案与排除原因）+ Context + Architecture + 8 行风险表
- `canonical/specs/code/2026-09-17-mirror-failure-alert.yaml` — **9 REQ / 18 SC**
  （每条 SC 含 `confidence` / `evidence` / `given` / `when` / `then` / `and`）
- `canonical/specs/agent/2026-09-17-mirror-failure-alert.yaml` — **13 CP** + 4 条 `expected_outcomes`
- `test-plan.md` — **25 个 TC-ID**（`TC-MFA-001` … `TC-MFA-025`）+ 覆盖矩阵 + 回归风险矩阵
- `canonical/proposals/2026-09-17-mirror-failure-alert.yaml` + `proposal.md`（Gate 1 已确认）
- `specs/mirror-failure-alert/spec.md` — **Gate 2 自动生成**的 Human View（9 Requirement / 18 Scenario）

### 完整上下文文件清单

- `design.md`：技术决策与排除理由（Decisions）、架构与故障域（Architecture）、风险（Risks）
- `canonical/specs/**`：GIVEN/WHEN/THEN 行为规格与 agent 验证检查点（**权威源**）
- `test-plan.md`：TC-ID 映射、测试金字塔、执行矩阵、回归风险、补充顺序

---

## Phase 3: BUILD (in_progress, 自 2026-09-17T16:06)

### 执行模式

**全自动长程模式**（`long_range.mode: full_auto`，D哥 于 `2026-09-17T16:06` 选择）。
长程模式跳过的是**授权交互，不是流程步骤** —— 每个 Step、每个切片的 B3.4 验证、
失败模式检查均照常执行，仅在 Gate 3 或触发降级条件时暂停。

### 切片计划

`slices.md` —— 8 个切片 A–H（依赖图 + 执行计划表 + 逐切片 Rationale）：

| 切片 | 内容 | 优先级 | 风险 | 并行组 | 依赖 |
|---|---|---|---|---|---|
| A | 钩子核心：回显 + 结构化告警块 | P0 | 🟡 Med | 1 | 无 |
| B | 故障标记（写入 / 自动清除） | P0 | 🟢 Low | 2 | A |
| C | 既有语义守护（`exit 0` / 非强制推送） | P0 | 🟢 Low | 2 | A |
| D | 巡检命令 `tools/check_mirror.sh` | P0 | 🟡 Med | 1 | 无 |
| E | 控制面接入（节点注册 + `notice` 上报） | P0 | 🟢 Low | 2 | A |
| F | 文档同步 `docs/DISTRIBUTED_ACCESS.md` | P1 | 🟢 Low | 3 | A, D |
| G | 不破坏既有约束（回归 + 凭证扫描） | P0 | 🟢 Low | 5 | 全部 |
| H | 端到端故障链路（服务器实测） | P0 | 🟡 Med | 4 | A, B, D, E |

> 注：`dependency-graph --format json` 返回空（只索引**项目级** `.fstdd/specs/`，
> 而 change 级 spec 要到 Phase 4 才合并），依赖关系由 spec 语义手工推导，无循环依赖。

### 切片执行记录

#### Slice A：钩子核心 —— 回显 + 结构化告警块 ✅ `2026-09-17T16:58:55`

- **TC 覆盖 7/7**：TC-MFA-001 … TC-MFA-007
- **新增测试 7 个**：`upstream/tests/test_mirror_alert_ops.py`
- **改动文件**：`tools/deploy_server_bare_repo.sh`（仅 HOOKBODY 段，733 → 2887 字符）
- **关键实现**：
  - `} >> "$LOG" 2>&1` → `} 2>&1 | tee -a "$LOG"`（回显 + 落盘双出口）
  - 标识改为 `[MIRROR-OK]` / `[MIRROR-FAILED]`，不共用语义
  - `record_failure()` 统一失败记录；分支与 tag 两项**独立判定**、失败不短路
  - 超时（`rc=124`）与普通失败分别给出原因
  - 结构化告警块明写「裸库已更新 / GitHub 未同步 / 对外通道滞后」
- **测试策略（重要）**：不满足于文本匹配 —— 从部署脚本提取真实 HOOKBODY，
  用 stub `git` / `timeout` **真实执行钩子**，断言推送方视角的 stdout 与 `mirror.log`。
  纯文本匹配只能证明「源码里有 `tee` 这个词」，证明不了「推送方真的看得到」
- **REFACTOR**：去掉冗余状态变量 `failed`，改用 `FAILED_ITEMS` 非空判定
  （同一事实只存一处），测试保持 GREEN
- **设计偏离**：`ADJ-001`（钩子路径改为环境变量可覆盖，否则无法自动化验证）、
  `ADJ-002`（标识措辞调整）—— 均 minor，详见 `pending-adjustments.yaml`
- **既有回归保护**：`test_server_bare_repo_ops.py` 6 passed —— 钩子保留
  `push github --all` / `push github --tags` / `timeout 180` / `timeout 120` 字面量，
  既有断言**一字未改**
- **验证**：`bash -n` 通过（部署脚本与提取出的钩子各自校验）

#### Slice B：故障标记 ✅

- **TC 覆盖 3/3**：TC-MFA-008 / 009 / 010
- **新增测试 3 个**（同文件）
- **关键实现**：失败分支写 `mirror-failed.flag`（键值行：`failed_at` / `failed_items` /
  `failed_detail` / `bare_head`）；全部成功时 `rm -f` 自动清除
- **实现先行说明**：标记的写入/清除与 Slice A 的失败分支是**同一段代码**，
  故实现在 Slice A 一并落地。本切片的独立价值在于**断言其格式与自动清除语义**
  （尤其 SC-006：只在失败分支写、忘了成功分支清 → 故障态永久滞留）
- **变异验证**：M1（删清除）/ M2（删写入）/ M3（键值行退化）均被捕获

#### Slice C：既有语义守护 ✅

- **TC 覆盖 2/2**：TC-MFA-019 / 020
- **关键实现**：5 组失败组合下钩子退出码恒 0；推送命令**剔除注释后**审查无强制选项
- **变异验证**：M4（`exit 1`）/ M5（`--force`）均被捕获

#### Slice D：巡检命令 ✅

- **TC 覆盖 6/6**：TC-MFA-011 / 012 / 013 / 014 / 024 / 025
- **新增文件**：`tools/check_mirror.sh`（107 行，`git ls-files -s` = `100755`）
- **关键实现**：单次 ssh 往返采集三项事实；三态退出码 0 / 2 / 3；
  只读（远端脚本仅 `rev-parse` / `ls-remote` / `cat` / `sed` / `echo`）
- **变异验证**：M9 / M10 / M11 均被捕获

#### Slice E：控制面接入 ✅

- **TC 覆盖 4/4**：TC-MFA-015 / 016 / 017 / 018
- **关键实现**：部署脚本新增 `7/7` 步骤注册基础设施节点 `fstdd-hub-infra`（幂等）；
  HOOKBODY 失败分支 `POST /messages` 投递 `notice`（`--max-time 3` + `|| true` 降级）
- **测试方式**：起**真实控制面实例**（内存 SQLite + `ThreadingHTTPServer`），而非 mock ——
  要验证的正是「契约是否支持幂等去重」，mock 掉就验证不到
- **REFACTOR**：curl 缺失从「静默跳过」改为显式降级回显
  （`[MIRROR-ALERT] 控制面告警未上报：服务器缺少 curl`）
- **变异验证**：3 个变异（去掉 `idempotency_key` / 去掉 `|| true` / 改短超时）均被捕获

#### Slice F：文档同步 ✅

- **TC 覆盖 1/1**：TC-MFA-021
- **改动**：`docs/DISTRIBUTED_ACCESS.md` 三处 ——
  ① 日常操作表「查镜像日志（ssh + tail）」→「查镜像状态（`./tools/check_mirror.sh`，含三态退出码）」；
  ② 故障处置表 `[WARN]` → `[MIRROR-FAILED]` 完整处置路径（含「再次 push 自动重试并清除标记」）；
  ③ 节点标识表新增 `fstdd-hub-infra`
- **新增测试 4 个**：三处改写各一条 + 一条否定式（不得再出现「人工 tail 日志」表述）
- **变异验证**：4 个变异均被捕获
- **修正 MF4**：原断言 `assert "自动清除" in text or "自动重试" in text` 中 `or` 掩盖了前者，
  已拆为两条独立断言并加 `assert "人工清理" not in text`

#### Slice G：不破坏既有约束 ✅ `2026-09-17T19:22:08`

- **TC 覆盖 2/2**：TC-MFA-022（全量回归保持绿）/ TC-MFA-023（仓库无凭证）
- **新增测试 2 个**：凭证扫描 + 本 change 触碰文件的 EOL 约束
- **凭证扫描的判据设计**：私钥不能只用裸模式 `-----BEGIN ... PRIVATE KEY-----`，
  因为 `upstream/tests/test_inbox_endpoint.py` 有**既存夹具**用它作为被测输入
  （验证 8787 端点拒绝含私钥的内容）。改为「**BEGIN/END 成对 + 主体 ≥ 128 字符**」判据 ——
  **基于内容而非路径白名单**：白名单会同时放走「有人真把私钥粘进测试文件」这种情况
- **修正了自身缺陷**：原断言消息打印 `match.group(0)[:12]` = 把凭证前 12 位写进日志，
  已改为只报「文件:行号 + 模式名」
- **加了空过防护**：`assert len(files) > 500`，防止 `git ls-files` 异常返回空导致测试静默通过
- **变异验证**：4 个变异捕获，且 MG4（占位私钥）**正确保持 GREEN** ——
  证明判据是真正按内容区分，不是路径白名单的副作用
- **全量回归**：630 passed / 1 failed。唯一失败 `test_migrate_to_d_drive.py::test_a6_d_repo_worktree_clean`
  断言「除 `changes/` 外无未提交改动」，而 BUILD 期间工作区**必然**有未提交改动
  （失败列表恰为本 change 的 5 个文件）→ **结构性已知**，提交后自动恢复，非本 change 缺陷

#### Slice H：端到端故障链路 ✅ `2026-09-17T19:37:35`

- **TC 覆盖 13/13**（切片计划列 9 个，实际链路自然覆盖 13 个）：
  TC-MFA-001 / 002 / 004 / 008 / 009 / 011 / 012 / 013 / 015 / 016 / 017 / 019 / 020 的**真实执行**
- **新增产出**：`tools/e2e_mirror_alert.sh`（344 行，`100755`）+ 5 个守护测试
- **实测结果**：**PASS=38 / FAIL=0**；连续两次运行结果一致，证明脚本幂等
- **关键设计（零污染）**：
  - 日志与故障标记经 `FSTDD_MIRROR_LOG` / `FSTDD_MIRROR_FLAG` 指向 `/tmp/fstdd-e2e/`，
    **不碰生产的 `mirror.log` 与 `mirror-failed.flag`**（实测验证：生产日志无 E2E 痕迹）
  - remote URL 经 `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_0` / `GIT_CONFIG_VALUE_0` 环境变量注入，
    **不改裸库配置**
  - 故障态指向 `http://127.0.0.1:9/`（端口 9 = discard，连接必拒、快速失败），
    恢复态指向服务器上的临时裸库 —— **不依赖 GitHub 联网**。
    若依赖真断网，恢复阶段一旦 GitHub 恰好 502，服务器就会**留在故障态**，反而违反纪律
  - 唯一真实改动 remote URL 的是巡检三态（它读真实配置），由 `trap ... EXIT INT TERM` 兜底还原
- **现场恢复**：脚本收尾**验证**还原结果（不只是发命令），实测输出 `[OK] 现场已还原`
- **发现并修正**：`GET /messages` 是**收件箱**语义
  （`WHERE acked_at IS NULL AND (to_node_id=? OR to_node_id IS NULL)`），
  必须带 `node_id` 参数；不带会返回 `{"error": "node_id query parameter is required"}` 而非空列表。
  首次运行因此 SKIP，修正后 4 项断言全 PASS
- **修正自匹配缺陷**：守护测试原断言 `"--force" not in code` 命中了 E2E 脚本里
  **检测强制推送的 grep 模式**自身，已改为只检查真正的 `git ... push` 命令行

### 变异测试（断言有效性验证）

「测试绿了 ≠ 断言有效」—— 11 个变异注入被测代码，**9 个被捕获**。
其中 1 个（M7 超时判定）**暴露了真实缺陷**：

> `test_hook_timeout_counts_as_failure` 原断言 `"timeout" in r.stdout.lower()` 会被
> **pytest tmp_path 的目录名**意外命中（`test_hook_timeout_counts_as_failure0`），
> 而钩子会打印故障标记文件路径 —— 断言形同虚设。
> 已改为锚定钩子自身措辞（正则 `\[MIRROR-FAILED\] branches push timed out \(>180s\)`
> ＋ 标记字段 `branches=timeout(>180s)`）。

（M4 的"未捕获"是**变异脚本自身**的匹配 bug —— 参数化测试 ID 带 `[1-0]` 后缀；
修正后 11/11 捕获。）

### 控制面契约实测（解答 Phase 2 遗留问题）

- **`POST /messages` 支持 `idempotency_key` 去重** ✓（`fstdd_hub.py:495-499` 走 `_idempotent`）
  —— Phase 2 记录的"未解决问题"由此**关闭**，无需退化为本地节流
- `POST /nodes/register` 用 `INSERT ... ON CONFLICT(node_id) DO UPDATE` → **天然幂等** ✓
- `MESSAGE_KINDS` 已含 `notice` ✓；`from_node_id` 必须已注册（`_message` 第 504 行）

### 未解决问题（承接 Phase 2）

- **控制面 `POST /messages` 是否支持 `idempotency_key` 去重**：design 的风险表假设可用。
  Phase 3 需实测；若契约不支持，退化为「同一故障窗口只投递一次」的本地节流
- **`mirror.log` 因回显而增行**是否需要日志轮转：本变更不处理，记录为后续项
- **`.fstdd/archive/` 下 18 个既存混合态文件**（`git ls-files --eol` 口径 `i/lf w/crlf`）：
  已提交且工作区干净，**非本 change 引入**，待 D哥决定是否另立 change
- **上一轮 change 的 `proposal.md` 哈希失配**：同属 `DC-HASH` 缺陷，需与上一条一并决策

### Gate 记录

| Gate | 确认时刻 | confirmed_by | 证据 |
|---|---|---|---|
| Gate 1 | `2026-09-17T15:21:49` | `dialog` | D哥：确认 Gate 1（并指出『使用 agent 时很多都不建立时间基线，这个需要进入到 FSTDD 中去』） |
| Gate 2 | `2026-09-17T16:06:38` | `dialog` | D哥：Gate 2：2026-09-17-mirror-failure-alert（spec 阶段 9 REQ / 18 SC / 25 TC 已就绪） |


---

## Part C：质量验证（C1–C7）

### C1 多路并行技术评审 —— 3 路只读评审，20 条发现

| 评审路 | 范围 | 发现 |
|---|---|---|
| 代码质量 | `tools/deploy_server_bare_repo.sh`（钩子）、`tools/check_mirror.sh` | 8 |
| 测试质量 | `upstream/tests/test_mirror_alert_ops.py` | 7 |
| 文档一致性 | `docs/DISTRIBUTED_ACCESS.md`、脚本头部注释 | 5 |

**严重度分布**：3 high / 6 medium / 11 low。

**归因（回答「是不是别人的 skill 错得多」）**：

| 归属 | 条数 | 说明 |
|---|---|---|
| 本 change 新写的代码 | **16 / 20** | 约 1500 行（钩子告警逻辑、巡检命令、E2E 脚本、测试） |
| 上游 STDD 工具 | 4 / 20 | `ci.py` 统计粒度 ×2、`diff.py` 目录硬编码、`DC-HASH` 与 EOL 归一冲突 |

结论：**不是「改造别人的成品所以错多」**。本 change 的产物（镜像告警钩子 / 巡检命令 /
E2E 脚本）上游 STDD **根本没有** —— 是在别人的流程框架上从零新增能力。
上游那 4 条一直存在，只是**从未被真跑过**（10 个 change 全带着它们通过 Gate 3），
印证「通过了 ≠ 验证过」。

### C1 三条 high 及其修复

| # | 缺陷 | 性质 | 修法 |
|---|---|---|---|
| 1 | 混合态下同时出现 `[MIRROR-OK] tags mirrored` 与 `[MIRROR-FAILED]` | **契约缺陷** —— `grep MIRROR-OK` 把整体失败误读为成功 | 标识拆为 `[MIRROR-STEP]` / `[MIRROR-OK]` / `[MIRROR-FAILED]` / `[MIRROR-ALERT]`，`MIRROR-OK` 仅在整体成功时出现（ADJ-007） |
| 2 | `test_hook_echoes_mirror_result_to_pusher` 的断言被 **stub git 自己打印的** `pushing branches/tags` 满足 | **断言空过** —— 看着绿，实际没验证钩子 | stub 措辞去掉业务词（改 `push --all exit=N`），断言锚定钩子措辞 `[MIRROR-STEP] branches mirrored` |
| 3 | `test_hook_timeout_counts_as_failure` 匹配的是 `record_failure` 的**字面实参 180** | **断言空过** —— 把 `timeout 180` 改成 `timeout 5` 照样通过 | `_STUB_TIMEOUT` 记录实际收到的时长，断言 `timeout_secs == ["180", "120"]` |

3 条 high 里有 2 条是**测试断言空过** —— 这类缺陷自测发现不了，只有独立评审能发现。

### C1 修复清单（按文件）

**`tools/deploy_server_bare_repo.sh`**

- 标识语义拆分；EXIT trap 兜底「恒以 0 退出」（原写法下死于 `set -u` 即非零退出）
- 故障标记改为**临时文件 + mv 原子写入**（原写法下并发巡检可能读到半成品）
- 头部注释补 `FSTDD_SSH_ALIAS` / `FSTDD_HUB_URL` / `FSTDD_HUB_NODE_ID` /
  `FSTDD_MIRROR_LOG` / `FSTDD_MIRROR_FLAG`；删除与脚本无关的 pkill 注意事项
- **转义缺陷（本次实测踩到）**：钩子注释里写了未转义的 `` `> "$FLAG"` ``，
  而外层 heredoc `<<REMOTE` **未加引号** → 部署时被本机 shell 展开，报
  `line 213: FLAG: unbound variable`。注释里的展开无害，**同一写法落到代码行上就是真故障**。
  已修 + 新增守护测试 `test_hook_body_escapes_all_shell_variables`（静态扫描全部 `$`）

**`tools/check_mirror.sh`**

- 判定顺序反转为**先判故障标记、再判可测性**（ADJ-008）——
  原顺序会把「GitHub 不可达 + 已有标记」降级成 3（无法测量），丢掉已知的失败项与时间
- 新增 `FSTDD_MIRROR_URL`（经远端 `GIT_CONFIG_*` 注入），使验证**不必改动真实配置**
- 头部补「覆盖范围诚实声明」（只比对 master，不比对 tags/其他分支）；依赖清单按实际改写

**`tools/e2e_mirror_alert.sh`**

- 巡检段改用 `FSTDD_MIRROR_URL` 注入 → **全程不改裸库真实配置**；收尾由「发还原命令」
  改为「读回真实配置做比对」，成为**零污染的证据**（ADJ-009）
- 临时库从生产目录 `/home/ubuntu/fstdd-git/` 移到 `/tmp/fstdd-e2e/`
- 恢复态先**显式种下**故障标记并断言前置条件 —— 原断言可能恒真
- 新增「branches 失败 / tags 成功」**混合态实测**（用带 `pre-receive` 的专用假库）
- 新增两条巡检判定分支：**标记优先**（有标记 + 不可达 → 2）与 **sha 不一致**（无标记 + 落后 → 2）
- 静态审查正则补 `--force-with-lease` / `-f` 变体 / `+refspec`

**`upstream/tests/test_mirror_alert_ops.py`**

- 新增 `_STUB_CURL`：**curl 也做成测试替身**（见下）
- 退出码断言由 `rc != 0` 收紧为 `rc == 2`（`!= 0` 无法区分「滞后」与「无法测量」）
- 新增 4 个巡检用例：远端不可达 / GitHub sha 为空 / bare=unknown / **标记优先于可测性**
- 新增文档标识区分测试；E2E 守护断言补续行合并、`+refspec`、`rm -fr`、临时库不得落生产目录

### 关键发现：环回网络抖动导致断言随机失败

C1 修复后首次全量运行时，两个控制面测试失败：

```
test_failed_mirror_posts_notice_to_hub   → 钩子 60s 超时
test_hub_unreachable_degrades_gracefully → elapsed 57.9s（断言 < 20）
```

**根因不是本次改动**。对照实验（同一份代码，仅去掉不同改动）：

| 变体 | 耗时 |
|---|---|
| 当前钩子 | 29.9s / 12.5s / **121.0s** / 16.5s |
| 去掉 EXIT trap | 7.7s / 10.8s |
| 去掉原子写入 | 5.6s / 6.9s |
| 单独 `curl --max-time 3` 到 127.0.0.1:1 | 2.4s / 2.3s / 2.0s |

**方差远大于任何改动的影响** —— 本机环回连接耗时在 2s–121s 之间波动。

两个后果都很坏：断言随机失败（而随机失败的断言最终会被忽略，比没有断言更糟）；
测试文件从 74s 涨到 **287s**（每次钩子调用都真的去连网络）。

**修法**：与 `git` / `timeout` 一致，把 `curl` 也做成测试替身（不触碰网络）。

- 钩子侧：捕获它**实际发出的参数与载荷**，断言 `--max-time` 有界、载荷符合契约
- 服务端侧：把捕获到的**真实载荷**投给真实控制面实例，确认可被接受并按收件箱语义检索到
- 真实链路（钩子 → 服务器控制面）由 E2E 在服务器上验证（CP-008）

「不拖慢推送」的断言从**墙钟时间**改为**机制**：curl 必须带 ≤10s 的有界超时。
墙钟时间在本机不可复现；有界超时才是 SC-012 真正的保证。

**效果**：测试文件耗时回到 64s（另一次测量 225s，波动来自并发部署的负载）。

### 契约细节修正

`POST /messages` 返回 **201 Created**（不是 200）；`POST /nodes/register` 返回 200。
断言改为 `status in (200, 201)` —— 断言的是「载荷被接受」，不是某个特定成功码。

### C2–C7 摘要

| 步骤 | 结果 |
|---|---|
| C2 全量质量检查 | 覆盖率 65%（既存基线，本 change 未改 Python 生产代码）；ruff 本 change 文件全过；查明 2 项 CI 报错为**工具缺陷**（10/10 归档 change 对照验证） |
| C3 Diff 审查 | docs 与钩子 diff 逐行审查通过 |
| C4 失败模式检查 | 10 条经验逐项 + 6 项跨文件一致性；提取保护变异 ME1/ME2 均 RED |
| C5 经验库 | 新增 3 条：`EXP-20260917-A1`（检查工具统计粒度）、`A2`（断言自匹配）、`A3`（验证脚本改生产环境） |
| C6 设计调整 | `design-adjustments.yaml` 共 **9 项**（Part B 3 + Part C 质量验证 3 + C1 评审修复 3） |
| C7 测试报告 | `test-report.md` |

### C1 追加修复（Step 18–19）：镜像目标注入机制失效（ADJ-010，high）

**怎么发现的**：E2E 第三次运行 Step 7（CP-006 巡检判定）四条断言全红：

```
[FAIL] 巡检退出码（无标记 + 目标不可达 = 无法测量）：期望 3，实际 2
[FAIL] 前置条件不成立：故障标记未种下
[FAIL] 巡检退出码（有标记 + 目标不可达 = 滞后，标记优先于可测性）：期望 2，实际 0
[FAIL] 巡检退出码（无标记 + sha 不一致 = 滞后）：期望 2，实际 0
```

**排查过程（三次误判，值得记录）**：

| 阶段 | 判断 | 为什么错 |
|---|---|---|
| ① | `$WORK` 在远端未展开 → 路径不一致 | 最小复现证明 `rm -f '$WORK/mirror-failed.flag'` **生效**、路径一致 |
| ② | 故障标记残留（7a 的 rm 没生效） | 7c 用**完全相同**的语句却返回 0（要求标记已删），自相矛盾 |
| ③ | 环回抖动导致的偶发 | 单独复现 7b 的 printf，`read_flag` 返回 `flag=present` —— 写法没问题 |

**真根因**（一次远端探针定性）：

```
$ git -C <bare> remote -v
github  git@github.com:2749817087qq/DKK_Fstdd.git (fetch)
github  git@github.com:2749817087qq/DKK_Fstdd.git (push)
github  /nonexistent/repo.git                     (push)   <-- 注入值成了【额外 push URL】

$ GIT_CONFIG_KEY_0=remote.github.url GIT_CONFIG_VALUE_0=/nonexistent/repo.git     git -C <bare> config --get remote.github.url
/nonexistent/repo.git                                      <-- 看起来「生效了」

$ GIT_CONFIG_* … git -C <bare> ls-remote github refs/heads/master
c11789a8ea7da33bb7dbfc6761c114a439622a90                  <-- 但 ls-remote 仍连真实 GitHub
```

`remote.<name>.url` 是 git 的**多值**键：第一个值用于 fetch，**全部**值用于 push。
环境注入只往末尾**追加**一项 —— 于是 `config --get` 看得到注入值，
`ls-remote`（fetch）却永远用第一个 URL。

**两条后果**：

1. `FSTDD_MIRROR_URL` 形同虚设 → CP-006 的「无法测量 / 滞后」两条判定**永远测不出来**
2. 真实 GitHub 仍留在 push 目标里 → E2E 的 `run_hook` **真的会推线上**
   （所幸裸库与 GitHub 内容本就一致，推送为 no-op，**未造成数据污染**；
     但「零污染」的机制保证是假的）

**为什么单元测试没发现**：单测用 stub ssh 直接回放端状态，**绕过了注入路径**。
只有真在服务器上构造一次不可达场景才会露馅 —— 这正是「E2E 不可省略」的又一例证。

**修法**：把镜像目标**直接作为 git 参数**传递。

| 文件 | 改动 |
|---|---|
| `tools/check_mirror.sh` | 删 GIT_CONFIG_* 块；`TARGET="${MIRROR_URL:-github}"` + `ls-remote "$TARGET"` |
| `tools/deploy_server_bare_repo.sh` | 钩子加 `MIRROR_TARGET="${FSTDD_MIRROR_URL:-github}"`；两处 push 改直传 |
| `tools/e2e_mirror_alert.sh` | `run_hook` 改 `export FSTDD_MIRROR_URL='$1'` |
| `upstream/tests/…` | 新增 2 行为级 + 1 静态守护；同步修 `test_hook_never_uses_forced_push` 的筛选依据 |
| `docs/DISTRIBUTED_ACCESS.md` | 补「镜像目标」说明 + 「为什么不用 GIT_CONFIG_*」实测依据 |
| `.fstdd/experiences/EXP-20260917-A3.md` | **修正**其中推荐 GIT_CONFIG_* 的段落（它当时在教人做已被证伪的事）；并修正「trap 兜底」建议 |
| `.fstdd/experiences/EXP-20260917-A4.md` | **新增**：「看起来生效」类失效（GIT_CONFIG_* 注入） |

默认值仍是 remote 名 `github`，**生产行为完全不变**；
且此后**没有任何路径**会读或写裸库的真实 remote 配置。

**验证**：变异测试 **5/5 捕获**（M1 钩子写死 github / M2 默认值写成 origin /
M3 巡检加回 GIT_CONFIG_* / M4 巡检写死 ls-remote github /
M5 E2E 退回 GIT_CONFIG_*）。

**变异测试自身的一次教训（v1 -> v2）**：

v1 直接改 `tools/*.sh` 原件、在 `finally` 里还原。结果后台任务被 kill 时
`finally` 不执行，**仓库里留下两处变异残留**：

```
tools/deploy_server_bare_repo.sh:270  MIRROR_TARGET="${FSTDD_MIRROR_URL:-origin}"   <- 应为 github
tools/check_mirror.sh:98              export GIT_CONFIG_COUNT=1                     <- 多余一行
```

靠人工 grep 比对才发现。而且 v1 用 8 次 pytest 子进程，单次调用 25.6s
（Python 启动开销占 23s），总计 >3 分钟且更容易被 kill。

v2 改为**纯内存变异**：静态变异在内存文本上做；行为变异把变异后的钩子源码
写入**临时目录**执行（复用测试模块的替身与断言口径）。零文件改动、
单进程秒级完成，并新增「零改动核验」断言三个文件内容与读入时逐字节一致。

**结论：改原件的变异测试本身就是缺陷源。** 已在 `EXP-20260917-A3` 中
修正「用 trap 兜底」的建议 —— trap 覆盖不了强杀。

### C1 追加修复（Step 23–24）：转义自检，与两处环境坑

#### ① 同一类缺陷第三次发作：未转义反引号

ADJ-010 修复时我在钩子体里加了两行注释，用反引号包裹 `github`：

```
# 调用时不设这些变量，一律走默认值（镜像目标 = remote 名 `github`），生产行为不变。
```

钩子体经**外层未加引号的 heredoc** 展开，反引号被**本机 shell 当作命令替换执行** ——
部署时真的去执行了一个叫 `github` 的"命令"：

```
tools/deploy_server_bare_repo.sh: line 214: github: command not found
```

（报的是 heredoc 起始行，症状离根因很远 —— 与第一次同类。）

**守护测试成功抓到**（`test_hook_body_escapes_all_shell_expansions` 报出 L240 / L269），
问题在于**我没跑它** —— 改完钩子只跑了 `-k "mirror_target or ..."`。

**修法（把纪律变成机制）**：部署脚本在安装钩子**之前**自检 HOOKBODY 区域，
发现未转义的 `$` / 反引号 / 行尾反斜杠就**拒绝部署并退出**（`_hookbody_scan`）。
不再依赖「记得跑测试」。守护测试仍是更全面的一道，两者互补。

#### ② 自检自身有 bug —— 被验证脚本抓到

自检的 awk 起始正则原为 `/<<.HOOKBODY./`，而**自检函数自己那一行**也含这个模式：

```
awk '/<<.HOOKBODY./{f=1;next} ...' "$0"
     ^^^^^^^^^^^^^^ 这一行本身就被匹配
```

于是它把**自己的函数体**（其中第二个 awk 块含大量 `$` 与反引号）当成 HOOKBODY 内容扫描
→ **干净内容也被拒绝**。改为 `/^cat .*<<.HOOKBODY.$/`（匹配真实的 heredoc 起始行）。

这个缺陷是**验证脚本抓到的** —— 又一次印证：**新写的检查工具必须自己先被验证**。

#### ③ Windows 环境坑：`subprocess.run(["bash", ...])` 命中 WSL 启动器

验证自检时 4 个用例全部 `rc=1`，其中 **3 个是假通过**（拒绝的原因是 WSL 失败，
不是自检拒绝）。dump 出的 stdout 是 **UTF-16LE**：

```
... L\x00i\x00n\x00u\x00x\x00 ... w\x00s\x00l\x00.\x00e\x00x\x00e\x00 ...
```

即 `C:\Windows\System32\bash.exe`（**WSL 启动器**）报「没有已安装的发行版」。
而 `shutil.which("bash")` 返回的是 PortableGit 的 bash：

```
C:\Users\Administrator\.workbuddy-ai\binaries\PortableGit\versions\1.2.0\usr\bin\bash.EXE
```

**规则**：Windows 上调用 bash 必须用 `shutil.which("bash")` 的**绝对路径**；
`CreateProcess` 的查找顺序把 `System32` 排在 PATH 之前，裸 `"bash"` 会命中 WSL。
（测试文件里的 `BASH = shutil.which("bash")` 一直是对的 —— 错的只是我新写的验证脚本。）

#### ④ 并发干扰导致的假失败

完整测试出现 `test_hook_clears_flag_automatically_on_success` 失败，而**单跑通过**。
原因：那次全跑期间我**同时在修改 `tools/deploy_server_bare_repo.sh` 并执行部署**，
而测试会读取该文件提取钩子源码（`hook_source` fixture）。

**纪律：跑测试期间不得改被测文件。** 已在断言消息中补入钩子 stdout，便于下次区分
「竞态」与「真实缺陷」（若含 `[MIRROR-ALERT]` 则是标记写入失败；若含 `[MIRROR-STEP]`
则是替身未按预期返回非零）。

### C1 追加修复（Step 25–29）：契约同步、E2E 复测与报告定稿

#### ① 契约变更必须同步所有依赖方（Step 26）

ADJ-010 把钩子的推送语句从 `push github` 改为 `push "$MIRROR_TARGET"`，
而**上一个 change** `server-bare-repo-mirror` 的测试 `test_server_bare_repo_ops.py:43-44`
硬编码了字面量：

```python
assert "push github --all" in text
assert "push github --tags" in text
```

这是**跨 change 的契约耦合**：钩子是本 change 的产物，但它的源码被另一个 change 的测试
断言着。若不修，全量回归必然出现**假红** —— 而假红会被误判为本 change 的缺陷。
修法：按 `MIRROR_TARGET` 断言（注意 `read()` 读的是**原始文件**，含 `\$`，
故断言串带反斜杠，且用 raw string 避免 `DeprecationWarning`）。

> 一般化：**改一处「被别处断言着的字符串」时，要主动 grep 全仓找断言方** ——
> 依赖不会自己报错，它只会变红。

#### ② 沙箱批量删除守卫：从「伪装成断言失败」到「显式 skip」（Step 27）

`test_hook_clears_flag_automatically_on_success` 出现**全跑失败 / 单跑通过**，
且两次全跑的失败点不同（一次第一个断言「失败态未产生标记」、一次第二个断言「标记滞留」）。

独立复现脚本 `c1_diag_flag.py` **20/20 轮全部通过** —— 钩子逻辑正确，问题在环境。
决定性证据来自断言消息里的 stdout：

```
[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {"count":462,"threshold":180,
 "scope":"turn","targets":[".../test_hook_clears_flag_automati0/mirror-failed.flag"],"targetCount":1}
```

**沙箱按 turn 累计删除数（阈值实测 180）拦截 `rm` / `mv`** —— 拦截的是
**被测代码钩子自己的** `mv -f`（写标记）与 `rm -f`（清标记），不只是 pytest 的临时目录清理。
这解释了全部三个现象：单跑通过（新进程 turn 计数从 0）、全跑失败（累计超阈值）、
两次失败点不同（分别对应 mv 与 rm 被拦）。

**处置原则：skip，而不是放宽断言。**

| 方案 | 问题 |
|---|---|
| 放宽断言（失败即跳过） | 真实缺陷也会被吞掉 —— 断言从此不可信 |
| 无条件 skip | 该用例永远不跑，等于删除 |
| **`_skip_if_sandbox_blocked`（采用）** | **仅当该次运行的 stdout 确实出现守卫标记时**才跳过；其余情况照常失败 |

实现：`HookRun` 增 `sandbox_blocked` 字段（`"SAFE_DELETE_BULK_CONFIRM_REQUIRED" in combined`），
5 处断言前调用该辅助。

> 一般化：**「单跑绿、全跑红」不一定是顺序敏感**，也可能是**环境计数器跨用例累计**。
> 判定方法是看失败的 stdout 里有没有**环境自己的标记**，而不是去猜测试间的隐式依赖。

#### ③ E2E 复测：四条判定分支全部真正测到（Step 28）

ADJ-010 修复后重跑 `tools/e2e_mirror_alert.sh`：

```
=== 7/9 CP-006 巡检判定 ===
  [PASS] 巡检退出码（无标记 + 目标不可达 = 无法测量）（=3）
  [PASS] 输出明确标注「无法测量」
  [PASS] 前置条件：故障标记已种下
  [PASS] 巡检退出码（有标记 + 目标不可达 = 滞后，标记优先于可测性）（=2）
  [PASS] 输出点名故障标记
  [PASS] 巡检退出码（无标记 + sha 不一致 = 滞后）（=2）
  [PASS] 输出点明 sha 不一致
...
=== 汇总：PASS=48  FAIL=0 ===
```

**这是 ADJ-010 的决定性证据**：修复前这四条里有两条**永远返回错误值**
（`期望 3 实际 2`、`期望 2 实际 0`），因为「不可达」这个条件根本没被注入到 git 的
fetch 路径上。修复后四条全绿，断言数从 38 涨到 **48**。

同时印证了「零污染」现在是**证据**：收尾读回裸库真实 remote 未被改动
（`git@github.com:2749817087qq/DKK_Fstdd.git`）。

#### ④ 全量回归与报告定稿（Step 29）

```
cd D:/tools/FSTDD/stdd-repo/upstream
C:/Python311/python.exe -m pytest tests -q
→ 1 failed, 639 passed, 1 skipped in 418.98s
```

- **唯一失败** `test_migrate_to_d_drive.py::TestAMigrationIntegrity::test_a6_d_repo_worktree_clean`
  —— 断言「除 `.fstdd/changes/` 外无未提交改动」，正是 BUILD 期的结构性必然，**提交后自动恢复**。
  它失败的内容恰好**反证改动范围完全在预期内**。
- **1 skipped** 即 §② 的沙箱守卫用例（环境特性，非缺陷）。
- 单文件层面：`test_mirror_alert_ops.py` + `test_server_bare_repo_ops.py`
  → **`54 passed, 1 skipped in 65.57s`**。

**`test-report.md` 升级为 v2.0**（493 行），相对 v1.0 的实质变化：

| 项 | v1.0 | v2.0 |
|---|---|---|
| 版本定位 | 初版 | 纳入 C1 第二轮修复（ADJ-010 + 两个环境坑） |
| 新增测试 | 39 项 | **49 个收集用例**（45 个 `def test_`，含 4 处 `parametrize`） |
| E2E 断言 | PASS=38 / FAIL=0 | **PASS=48 / FAIL=0**，CP-006 从「三态」→ **四条判定分支** |
| 变异测试 | 24 个 | **29 个**（+ ADJ-010 的 5 个纯内存变异） |
| 设计调整 | 6 项 | **10 项** |
| C1 评审 | 无 | 新增 §五.4：3 路 20 条发现 + 第四条 high（ADJ-010）+ 转义缺陷 + 环回抖动 + 两个环境坑 |
| 规格缺口 | 无 | 新增 §7.3：SC-002 标识唯一性、SC-012 有界超时、**SC-002 目标可参数化** |
| 已知限制 | 3 条 | 7 条（+ 巡检只比 master、真实链路不在单测、`FSTDD_MIRROR_URL` 后门、沙箱 skip） |

`.fstdd.yaml` 同步：`traceability.test_functions` **44 → 45**。

**EOL 归一**：`.gitattributes` 要求 `text=auto eol=lf`，而 CLI / Write 以 CRLF 落盘。
`verify_eol.py --fix` **只处理已 tracked 的混合态文件**，本次产物是**未跟踪的新文件**
（`git ls-files` 看不到），故在 `git add` **之前**用脚本统一归一为 LF
（只去 `\r`，并断言「归一后字节 == 原文去掉 `\r` 的字节」以防内容被改）。
复核：21 个目标文件全部无 CR。
