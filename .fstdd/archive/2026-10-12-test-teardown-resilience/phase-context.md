# Phase Context — 2026-10-12-test-teardown-resilience

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-10-12T21:55+08:00)

### 关键决策
- **需求边界确定**：本 change 只解「**门禁数可判**」，不解「守卫本身」（守卫在仓外 shim，不可改）。
  范围锁死在 `tests/`，**不碰 `upstream/`**（详见 proposal.md NonGoals）。
- **优先级判断**：P0 —— 门禁不可判 ⇒ 后续任何 change 的「全量是否转绿」都无意义，属**前置阻塞**。

### 用户关注点
- D哥 在本 change 之前已多轮追问「同一 HEAD 同一命令为何失败数不同」，并要求**给实证**（≥2 次）。
- 强调**不得伪造 evidence**（Gate 1/2 均由 D哥 回「确认」原文，未由 AI 代跑）。

### 被否决的方向
- 「改 shim 把 SystemExit 降级」—— 仓外程序 + 削弱守卫语义 ⇒ 排除。
- 「改 `upstream/.../experience.py` 的 `except` 范围」—— 违反范围约束 ⇒ 登记为**独立欠账**。
- 「只把 `d.mkdir()` 改 `exist_ok=True` 了事」—— 只治症状末端 ⇒ 保留为 C2 但不作主方案。

### 产出物清单
- `proposal.md` — Gate 1 已确认，confirmed_at: 2026-10-12T21:55+08:00（`source_hash 0bb6c66a83534845`）

### 完整上下文文件清单
- `proposal.md`：需求背景、能力列表（C1–C4）、约束条件、成功标准（7 条 SC）

---

## Phase 2: SPEC (completed 2026-10-12T22:47+08:00)

### 关键技术决策
- **决策 1（双轨）**：规避（D1a 临时目录中立化）+ 兜底（D1b 包装删除原语）——
  理由：单靠规避不能 100% 不触发（守卫含并发状态锁仲裁）；单靠兜底则触发面不减。排除：只做其一。
- **决策 2（落点）**：包装**删除原语外层**，安装点 `pytest_configure` ——
  理由：与 fixture 生命周期解耦（hook 方案会被 fixture 自身 teardown 的 SystemExit 打断）。
- **决策 3（可见性）**：捕获即 `warnings.warn`（含目标路径）+ 计数 + 会话汇总；**严禁静默**。
- **决策 4（反向守卫）**：只放行 `SystemExit`，其余异常照抛。排除：`except BaseException`（语义过宽）。
- **决策 5（边界）**：② 的代码不修，登记欠账。**决策 6**：`mkdir(exist_ok=True)` 定位为症状末端加固。

### 经验触发记录
- **EXP-2026-0029**（沙箱 safe-delete 守卫拦截 `os.remove` ⇒ SystemExit 整片报红）——
  **已记录过本 change 的根因**；其 `fix_template` 的「TMP/TEMP 指向中立目录」被纳入 D1a。
- **EXP-2026-0030**（TMP 指向 agent runtime 目录会被 Guard 误判）—— 佐证中立目录须在仓库外。
- **EXP-2026-0014 / KG-092**（静默降级 / 失败静默腐烂）—— 支撑 D3「必须可见」。
- **EXP-2026-0021**（审计类断言必须自带自检测试）—— 支撑 TC-001/005 的**双向断言**。

### 已知坑点 / 注意事项
- 🔴 **根因有两个位置**，其中 ② 在 vendored 内核内（`experience.py:241` 的 `except OSError` 抓不到 SystemExit）。
- ⚠️ `gate approve --gate 1/2` 的产物（`proposal.md` / `spec.md` / `.fstdd.yaml`）**都是 CRLF** ⇒ 每次 gate 后必须归一。

### 未解决问题（待 Phase 3 验证）
- 「包装删除原语」能否真的拦到守卫的 SystemExit？——**假设**：能；**验证方式**：monkeypatch 让原实现抛 SystemExit。
  ⚠️ **Phase 3 实测结论：原假设不完整**（见 Phase 3「设计偏离汇总」ADJ-008）。
- `TMP/TEMP` 中立化会不会影响其它测试的路径假设？——**假设**：不会；**验证方式**：全量跑对比。

### 产出物清单
- `design.md` — Gate 2 已确认（6 条决策 D1–D6 + 映射表 + 调用链 + 6 条风险）
- `canonical/specs/code/test-teardown-resilience.yaml` — **5 REQ / 7 SC**，confirmed
- `canonical/specs/agent/2026-10-12-test-teardown-resilience.yaml` — **7 CP** + rollback
- `specs/test-teardown-resilience/spec.md` — Gate 2 自动生成的 Human View
- `test-plan.md` — **9 个 TC-ID**（TC-TTR-001..009），confirmed

### 完整上下文文件清单
- `design.md`：Decisions（D1–D6）、决策↔What Changes↔SC 映射、Architecture、Risks
- `specs/test-teardown-resilience/spec.md`：GIVEN/WHEN/THEN 行为规格（7 SC）
- `test-plan.md`：TC-ID 映射、测试策略、回归风险矩阵、证据记录

---

## Phase 3: BUILD (completed 2026-10-13T01:4x+08:00)

> V3.0.5：SLICE / BUILD / VERIFY 三阶段合一。以下为三小节内容。
> **执行模式**：全自动长程（D哥 2026-10-12 22:4x 一次性预授权，`long_range.mode = full_auto`）。

### 切片方案（Slice）
- Slice 1（P0 · 独立）：韧性层 —— 包装 6 个删除入口 + 可见性 + 反向守卫 —— 5 个 TC
- Slice 2（P0 · 依赖 Slice 1）：规避层（临时目录中立化）+ 症状末端加固 —— 2 个 TC
- parallel_group: **无**（S1 与 S2 **同文件** `tests/conftest.py` ⇒ 串行）

### 风险提示
- Slice 1 涉及 `tests/conftest.py`（面状影响全部根级测试），风险评分 **🟡 中**；
- Slice 2 风险 **🟢 低**（环境变量 + 零风险 `mkdir` 加固）。

### 实现决策（非设计偏离）
- 用**手工逐属性复制**（`__name__`/`__qualname__`/`__doc__`）而非 `functools.wraps` ——
  因为后者会 `update` 原实现的 `__dict__`，而**内建函数没有 `__dict__`**。
- 包装体**调用时查表**取原实现（非闭包捕获）—— 使端到端判据可被 monkeypatch 驱动。

### 设计偏离汇总
<!-- 详见 design-adjustments.yaml（11 条：2 Major + 9 Minor；1 条结转欠账） -->
- **ADJ-008（Major · blocker）**：删除入口由 3 个**扩为 6 个**（+ `os.rmdir` / `Path.unlink` / `Path.rmdir`）——
  shim 直接替换 `pathlib.Path.unlink` 且非 bypass 分支不经 `os.unlink` ⇒ 原包装面**漏掉根因①**。
- **ADJ-001（Major）**：D1a 因果方向**被实证推翻**（「不落在被放行的目录里」→ 实为「必须留在系统临时根之下」）。
- ADJ-002..007、ADJ-009、ADJ-011（Minor）：查表取原实现 / notices 用例 6→7 / 源码级结构断言 /
  TC-006 空转弱点 / ADJ-006 更正取样偏差 / 汇总逐条列目标 / 文档一致性 / 自测隔离。
- ADJ-010：**结转欠账**（3 条框架缺陷，`upstream/`，须先 `UPSTREAM_PATCHES` 登记）。

### 经验触发记录
- **EXP-2026-0029 / 0030 / 0014 / 0021** 在 Phase 2 触发（见上）。
- **新增 4 条**：**EXP-2026-0034**（shim 替换 `Path.unlink`）· **EXP-2026-0035**（bypass 判据与 `_os_tmp_dirs` 固化）·
  **EXP-2026-0036**（取样偏差：无 shim 环境的结论不可外推）· **EXP-2026-0037**（`ci check-failures` 的 AND 假警告）。

### 切片完成状态
| Slice | TC覆盖 | 新增测试 | 状态 |
|-------|--------|---------|:---:|
| 1 | TC-TTR-001..005（20 个用例） | 20 | ✅ |
| 2 | TC-TTR-006/007（6 个用例） | 6 | ✅ |
| — | TC-TTR-008/009（会话级/边界级，不落代码） | 0 | ✅ 已执行 |

### 测试结果摘要（Verify）
- 全量：**230 passed / 6 skipped**（基线 204 / 6；本 change 新增 26 个测试函数），**0 failed / 0 errors**
- `tests/conftest.py` 覆盖率诊断 **76%**（未覆盖项均为幂等/防御分支或基线既有 helper）
- 失败模式检查：`ci check-failures` **3 通过 / 2 警告 / 0 错误 / 5 跳过**
  （2 条警告均已解释：AND 假警告 + TC 覆盖只统计代码内 TC-ID）
- `canon verify` **2/2**；`validate` 仅 1 条同类假警告

### 设计偏离确认
- 所有偏离已在 `design-adjustments.yaml` 中记录（11 条；2 Major + 9 Minor；1 条结转欠账）
- ⚠️ **C1 评审 1 项 major 明确不采纳**：「捕获即置 `exitstatus=1`」会重新引入非确定性（见 `test-report.md` §六）

### 产出物清单
- `slices.md` — 2 个切片，依赖关系已标注
- `tasks.md` — 3 组任务（S1 / S2 / Part C）
- 源文件：`tests/conftest.py`（+213/−4）· `tests/test_verify_notices_default_safe.py`（+18/−3）
- 测试文件：`tests/test_teardown_resilience_{capture,visibility,real_exception,tmp_neutral}.py`（4 个新增）
- `test-report.md` · `design-adjustments.yaml`（最终版）· `pending-adjustments.yaml`
- `code-structure-delta.md`（人工补全）

### 完整上下文文件清单
- `slices.md`：切片计划与完成状态
- `design-adjustments.yaml`：设计偏离详细说明（含 C1 评审处置表）
- `test-report.md`：测试结果、失败模式检查、确定性证据
- 关键源文件：`tests/conftest.py`（韧性层 + 规避层 + 自测隔离）、4 个新测试文件

---

## Phase 4: DELIVER (pending)

### 归档
- 待 Gate 3 确认后执行

### 版本
- 待定

---

## Current: Phase 3 BUILD — 待 Gate 3 确认

### 当前状态
- 全部切片完成，全量 **226 passed / 6 skipped**；偏离已记录；`test-report.md` 已生成
- ⏳ **等待 D哥 在 Gate 3 确认**（Gate 3 **不自动跳过**）

### 下一步
1. D哥 回「确认」⇒ 执行 `gate approve --gate 3 --confirmed-by dialog --evidence "<原文>"`
2. `phase advance` → Phase 4 DELIVER（归档 change / 合并 specs / 版本收口）
3. 另有两件挂起：③ `2026-10-12-canon-merge-command`（Gate 1 已过，待启动 Phase 2）；
   token / hosts / 3.3.9 Release（卡在「缺 GitHub 写凭证」）
