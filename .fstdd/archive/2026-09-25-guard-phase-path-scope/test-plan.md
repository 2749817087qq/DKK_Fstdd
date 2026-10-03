# Guard 相位门路径作用域 测试方案与详细案例

> 版本：v3.0.7（候选）｜创建日期：2026-09-25
> 对应 Phase 2 Spec：`specs/code/spec.md`（REQ-001..REQ-005，SC-001..SC-010）
>
> **收口追溯对账（2026-10-04）**：本文件 §二 的「当前状态」曾在 2026-09-25 SPEC 阶段
> 全部标记为「❌ 测试缺」，而代码与测试随后已落地（提交 `4eec636`）却**未回写本文件**，
> 导致 CHANGELOG §[3.3.1] 据陈旧标记误记「BUILD 未完成」。本次收口已按实况逐条回填
> 状态与**实际测试函数名**，并补 2 处 P0 变体（案例 3.2 / 3.5）。对账明细见 §八。

## 一、测试策略

### 1.1 测试金字塔

- **单元（主体）**：`_load_change_scope` / `_is_in_change_scope` 为纯函数，
  直接单测判定矩阵，覆盖全部 10 个场景；
- **集成（锁定判定序）**：以 `io.StringIO` 构造 stdin，调用 `cmd_guard_check`
  验退出码与 stdout 形态，锁定「新增分支位于硬阻断与豁免之后」的顺序不变；
- **手工端到端（验证 hook 生效）**：在临时工程装 hook，从**非项目 cwd** 模拟
  PreToolUse，确认放行/拦截两类各 1 例。

### 1.2 测试原则

- **断言退出码为下限，行为形态为上界**：warn-only 用例除 `exit 0` 外，
  还须断言 stdout 含目标路径与「out of scope」字样（防静默退化）；
- **顺序锁**：硬阻断与豁免用例在新增分支引入后必须**逐字不变**（防被新分支短路）；
- **字节固化**：构造含非 ASCII / 反斜杠路径的载荷一律用 Python
  `json.dumps(..., ensure_ascii=False).encode()` + `assert any(b >= 0x80)`，
  禁止经 shell `printf` 构造（skill 坑 5/6）；
- **修订一致性**：测试报告记录 CLI 绝对路径 + `guard.py` 的 sha256。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/commands/test_guard.py` | 20（hook 相关）+ 14（`TestGuardChangeScope`） | 集成 | 钩子 stdin 解析、豁免、GATE token / `.fstdd.yaml` 硬阻断、相位门、**作用域判定**；全部喂合法 JSON |
| `upstream/tests/test_guard_silent_except.py` | 1（零漂移哨兵） | 静态 | 白名单外新增 `except Exception:` 判红；行号漂移 >±5 判红 |

## 二、详细测试案例

### 功能 1：作用域声明读取（REQ-001 / REQ-002）

#### 案例 1.1 — proposal 声明 scope 时返回路径列表

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-001 |
| **对应 Spec** | REQ-001 / SC-001 前置 |
| **优先级** | P0 |
| **预置条件** | 临时 change 目录，canonical/proposals/*.yaml 含 `scope.paths: [a.py, "d/"]` |
| **输入** | `_load_change_scope(change_dir)` |
| **预期结果** | 返回 `["a.py", "d/"]`（顺序保留） |
| **当前状态** | ✅ 已实现 → `test_tc_scope_001_loads_declared_paths` |

#### 案例 1.2 — 无 scope 块 / 空列表 ⇒ 返回 None（fail-closed）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-002 |
| **对应 Spec** | REQ-002 / SC-003 |
| **优先级** | P0 |
| **预置条件** | 三种：无 `scope` 键 / `paths: []` / 无 proposal 文件 |
| **输入** | `_load_change_scope(change_dir)` |
| **预期结果** | 均返回 `None`，不抛异常（含 proposal YAML 损坏时） |
| **当前状态** | ✅ 已实现 → `test_tc_scope_002_returns_none_when_not_declared`（3 情形参数化） |

### 功能 2：范围判定（REQ-001 / REQ-004）

#### 案例 2.1 — 范围内（精确文件）⇒ 拦截

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-003 |
| **对应 Spec** | REQ-001 / SC-001 |
| **优先级** | P0 |
| **预置条件** | 临时工程，只读相位（understand），scope 含 `src/app.py` |
| **输入** | hook stdin → `file_path = <root>/src/app.py` |
| **预期结果** | `exit 2`，stderr 含「不允许编辑」并提示扩展 `scope.paths` |
| **当前状态** | ✅ 已实现 → `test_tc_scope_003_exact_file_in_scope`（纯函数）+ `test_tc_scope_006_in_scope_blocks_in_readonly`（集成，断言提示 `scope.paths`） |

#### 案例 2.2 — 范围外 ⇒ warn-only 放行

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-004 |
| **对应 Spec** | REQ-001 / SC-002 |
| **优先级** | P0 |
| **预置条件** | 同上，scope 不含 `docs/x.md` |
| **输入** | hook stdin → `file_path = <root>/docs/x.md` |
| **预期结果** | `exit 0` 且 stdout 含「out of scope」与目标路径（防静默） |
| **当前状态** | ✅ 已实现 → `test_tc_scope_005_out_of_scope_is_false`（纯函数）+ `test_tc_scope_007_out_of_scope_warns_and_allows`（集成，断言 `out of scope`） |

#### 案例 2.3 — 目录模式（`/` 结尾）匹配子文件 ⇒ 范围内

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-005 |
| **对应 Spec** | REQ-004 / SC-007 |
| **优先级** | P1 |
| **预置条件** | scope 含 `"src/"` |
| **输入** | `file_path = <root>/src/deep/mod.py` |
| **预期结果** | `exit 2`（范围内） |
| **当前状态** | ✅ 已实现 → `test_tc_scope_004_directory_pattern_matches_descendants` |

#### 案例 2.4 — `..` 穿越出项目根 ⇒ 视为范围外

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-006 |
| **对应 Spec** | REQ-004 / SC-006 |
| **优先级** | P0 |
| **预置条件** | scope 含 `src/` |
| **输入** | `file_path = <root>/src/../tools/evil.py`（normpath 后出界或在界内均须明确） |
| **预期结果** | 越界 ⇒ `exit 0` warn-only；归一化后仍在界内则按模式判定，行为确定 |
| **当前状态** | ✅ 已实现 → `test_tc_scope_010_dotdot_normalized_before_matching` |

### 功能 3：硬阻断与既有通道回归（REQ-003 / REQ-005）

#### 案例 3.1 — GATE token 在任何相位/范围下硬阻断

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-007 |
| **对应 Spec** | REQ-003 / SC-004 |
| **优先级** | P0 |
| **预置条件** | change 已声明 scope，`<root>/.fstdd/GATE1_APPROVED` **不在** scope 内 |
| **输入** | hook stdin → 该 token 路径 |
| **预期结果** | `exit 2` + 「必须由用户人工创建」（**不得**被范围外放行短路） |
| **当前状态** | ✅ 已实现 → `test_tc_scope_009_gate_token_still_blocked`（已含「已声明 scope」变体，断言「人工创建」）|

#### 案例 3.2 — `.fstdd.yaml` 确认字段硬阻断

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-008 |
| **对应 Spec** | REQ-003 / SC-005 |
| **优先级** | P0 |
| **预置条件** | change 已声明 scope，`.fstdd.yaml` 含 `confirmed_at` 且不在 scope 内 |
| **输入** | hook stdin → `.fstdd.yaml` + content 含确认字段 |
| **预期结果** | `exit 2` + 「请走 stdd gate approve CLI 通道」 |
| **当前状态** | ✅ 已实现 → `test_tc_scope_013_state_confirmation_still_blocked`（2026-10-04 收口补全；原「已声明 scope」变体缺失，P0）|

#### 案例 3.3 — 可编辑相位不受 scope 影响

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-009 |
| **对应 Spec** | REQ-005 / SC-009 |
| **优先级** | P0 |
| **预置条件** | `current_phase: build` |
| **输入** | 编辑 scope 外任意文件 |
| **预期结果** | `exit 0` |
| **当前状态** | ✅ 已实现 → `test_tc_scope_012_editable_phase_ignores_scope` |

#### 案例 3.4 — YAML-first 流程产物放行不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-010 |
| **对应 Spec** | REQ-005 / SC-008 |
| **优先级** | P0 |
| **预置条件** | 只读相位 + 已声明 scope |
| **输入** | 编辑 change 内 `canonical/proposals/*.yaml` 与 `design.md` |
| **预期结果** | 均 `exit 0`（现状逐字一致） |
| **当前状态** | ✅ 已实现 → `test_tc_scope_011_yaml_first_artifact_still_allowed` |

#### 案例 3.5 — agent runtime 豁免不受 scope 影响

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCOPE-011 |
| **对应 Spec** | REQ-005 / SC-010 |
| **优先级** | P0 |
| **预置条件** | 只读相位 + 已声明 scope |
| **输入** | 编辑 `.workbuddy-ai/memory/2026-09-25.md`（项目级 + 用户级 `~/` 各一例） |
| **预期结果** | 均 `exit 0`，且输出仍为「agent runtime dir」而非 scope 相关文案 |
| **当前状态** | ✅ 已实现 → `test_tc_scope_014_agent_runtime_exempt_ignores_scope`（2026-10-04 收口补全；原「已声明 scope」变体缺失，P0）|

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| `_load_change_scope` | TC-SCOPE-001/002 | — | — | ✅ 已实现 |
| `_is_in_change_scope` | TC-SCOPE-003/004/005/010 | — | — | ✅ 已实现 |
| `cmd_guard_check` 判定序 | — | TC-SCOPE-006..009/011..014 | 2 例手工 | ✅ 已实现 |
| 既有硬阻断/豁免 | — | 回归（逐字不变） | — | 🟡 已有 |

## 四、回归风险矩阵

| 风险区域 | V3.0.7 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|----------|
| 两道硬阻断被新分支短路 | 新增分支插在相位门后 | TC-SCOPE-013/009 + 顺序锁 | 🟡 |
| 豁免面被 scope 逻辑覆盖 | 不改 `_is_exempt_path` | TC-SCOPE-014 + 既有豁免用例 | 🟢 |
| 未声明 scope 的 change 行为漂移 | `None` 分支保持旧路径 | TC-SCOPE-002/008 + 全量套件 | 🟡 |
| **吞异常白名单** | `_load_change_scope` 预计含 `try/except` | `test_guard_silent_except.py` 零漂移哨兵会判红 | 🔴 |
| YAML 解析引入依赖问题 | 复用既有 `yaml.safe_load` | 全量套件 | 🟢 |

## 五、建议补充顺序

1. **第一优先**（合并前必补）：TC-SCOPE-001..004、006..009、011、013、014（P0）— ✅ 全部完成
2. **第二优先**：TC-SCOPE-005（目录模式）— ✅ 完成
3. **第三优先**：手工 E2E（临时工程 + 非项目 cwd）— ✅ 完成

## 六、连带义务（**不做一定红**）

新增的 `try/except` 必须先更新活表
`audit/except-points.yaml`（新增 id、刷新因插入而漂移的行号、同步
`meta.total` 与 `by_classification`），否则
`tests/test_guard_silent_except.py` 判红。执行顺序：
改 `guard.py` → 跑 `python tools/audit_silent_except.py --json` 取实况行号 →
更新活表 → 跑 `pytest tests/commands/test_guard.py tests/test_guard_silent_except.py`。

> 收口核对（2026-10-04）：`_load_change_scope` 的 `except` 兜底已在活表入册
> （EA-004 家族，canon.py 侧）+ 哨兵 `--check` 通过；`test_guard_silent_except.py` 全绿。

## 七、证据记录

| 证据 | observed_at | observed_base_git_sha | 来源 |
|---|---|---|---|
| 相位门全项目粒度：`:735` 仅放行 YAML-first 产物、`:744–756` 可编辑相位放行、`:803–814` 无条件 `return 2`（不看路径） | 2026-09-25T04:20:00+00:00 | df3b27cace3b28c6762932ef03638217024c2dae | `guard.py` 源码直接阅读（本地法定源） |
| 两道硬阻断位于 `:700–706`、agent runtime 豁免位于 `:711`，均先于相位门 | 2026-09-25T04:20:00+00:00 | df3b27c | 同上 |
| D哥 实测：ACTIVE_CHANGE 停 understand ⇒ memory 日志追加被 Edit 拦截，仅 Bash 可写 | 2026-09-25T02:20:00+00:00 | df3b27c | 对话报告（csrc-filing change 会话） |
| SPEC 起草中写入 `design.md` / `specs/code/spec.md` 均被 Guard 放行（验证 SC-008 现状） | 2026-09-25T04:18:00+00:00 | df3b27c | 本会话 Edit/Write 工具调用结果 |
| 实现落地：作用域判定接入 `cmd_guard_check`（`4eec636`）+ 审计补记（`75a7b86`） | 2026-09-25 | df3b27c | `git log`（本地法定源） |
| 收口实跑：`TestGuardChangeScope` 14/14 通过；全量 `upstream/tests` 0 failed | 2026-10-04 | — | `pytest`（见 `test-report.md`） |

## 八、收口追溯对账（2026-10-04）

### 8.1 TC-ID 计划→实现映射

计划编号与实现时的测试函数编号存在漂移，逐条对账如下（**不回改计划编号**，以映射表收口）：

| 计划 TC | 计划语义 | 实现测试函数 | SC |
|---------|----------|--------------|-----|
| TC-SCOPE-001 | 读取声明路径 | `test_tc_scope_001_loads_declared_paths` | SC-001 前置 |
| TC-SCOPE-002 | 未声明 ⇒ None | `test_tc_scope_002_returns_none_when_not_declared` | SC-003 |
| TC-SCOPE-003 | 精确文件在范围内 | `test_tc_scope_003_exact_file_in_scope` / `test_tc_scope_006_in_scope_blocks_in_readonly` | SC-001 |
| TC-SCOPE-004 | 范围外 warn-only | `test_tc_scope_005_out_of_scope_is_false` / `test_tc_scope_007_out_of_scope_warns_and_allows` | SC-002 |
| TC-SCOPE-005 | 目录模式 | `test_tc_scope_004_directory_pattern_matches_descendants` | SC-007 |
| TC-SCOPE-006 | `..` 穿越归一化 | `test_tc_scope_010_dotdot_normalized_before_matching` | SC-006 |
| TC-SCOPE-007 | GATE token 硬阻断 | `test_tc_scope_009_gate_token_still_blocked` | SC-004 |
| TC-SCOPE-008 | `.fstdd.yaml` 确认字段硬阻断 | `test_tc_scope_013_state_confirmation_still_blocked`（本次补） | SC-005 |
| TC-SCOPE-009 | 可编辑相位不受 scope | `test_tc_scope_012_editable_phase_ignores_scope` | SC-009 |
| TC-SCOPE-010 | YAML-first 产物放行 | `test_tc_scope_011_yaml_first_artifact_still_allowed` | SC-008 |
| TC-SCOPE-011 | agent runtime 豁免 | `test_tc_scope_014_agent_runtime_exempt_ignores_scope`（本次补） | SC-010 |

### 8.2 缺口与处置

| 缺口 | 现象 | 处置 |
|------|------|------|
| SC-005「已声明 scope」变体缺失 | 原仅验证无 scope 时的 `.fstdd.yaml` 硬阻断 | 本次补 `test_tc_scope_013` |
| SC-010「已声明 scope」变体缺失 | 原仅验证无 scope 时的 agent runtime 豁免 | 本次补 `test_tc_scope_014` |
| `traceability` 恒为 0 | `phase advance` 未回写计数（已记 CLI 缺陷 #2，见 `audit/traceability-notes.md`） | 收口时按实况回填 `.fstdd.yaml` |
| 记录长期停留 `build` | 代码已随 V3.0.7 上线，change 记录未收口 ⇒ 被判僵尸 | 本次补 tasks.md/test-report.md + Gate 3 + DELIVER |
