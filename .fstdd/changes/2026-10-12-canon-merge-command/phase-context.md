# Phase Context — 2026-10-12-canon-merge-command

## Phase 1: UNDERSTAND (completed 2026-10-12T13:45+08:00)

### 关键决策
- **需求边界确定**：只做「把已在跑的 DELIVER 手工步骤自动化」，**不**统一历史存量命名、不改 `archive` 行为。
- **优先级判断**：P0（ DELIVER 每次都要做，且已因手工产生口径分裂）。

### 用户关注点
- D哥 要求「命名不由人工决定」（Phase 1 反馈）⇒ 固化为 C2 的元数据单一事实源 + SC-005b 反向判据。

### 被否决的方向
- 「统一 `specs/agent/` 的 schema 使其含 `meta.capability`」—— 属数据模型变更，另立 change（已列 non_goal）。

### 产出物清单
- `proposal.md` — Gate 1 已确认（与 ① 同批，evidence 为 D哥 原文）
- Phase 2 补齐：`impact` 段（原模板缺该段）+ 观测 6 / 观测 7

### 完整上下文文件清单
- `proposal.md`：Why（7 条观测）、C1–C5、6 条约束、6 条 non_goals、8 条 SC

---

## Phase 2: SPEC (completed 2026-10-13T02:1x+08:00)

### 关键技术决策
- **D1 根 canonical 路径收口为单一事实源**：新增 `_root_canon_dir()`；`_get_canon_dir(None)` 委托它
  （原返回 `.fstdd/canonical` 空骨架 ⇒ `canon generate --all` 扫空目录的既有缺陷，顺带修好）
- **D2 命名三分法**：proposal/agent spec 用 `meta.change_id`；code spec 用 `meta.capability`；
  缺字段 ⇒ 告警 + 跳过（不静默改名、不启发式推断）
- **D3 幂等**：同值 SKIP-identical / **异值报错不覆盖**（覆盖会毁根侧人工修正）
- **D4 `--dry-run` 复用既有 `_dryrun` 守卫**（自造会被契约扫描判红）
- **D5 change 名走 `find_change_dir`**（`_resolve_in` 已内置 `..`/分隔符拒绝）
- **D6 归档 change 可用**，不用 `require_active_change_dir`（写路径专用，会拒自己的主场景）
- **D7 UPSTREAM_PATCHES 登记前置**（Phase 3 第一个动作）
- **D8 失败即响**：非 0 退出 + 说明已写/未写哪些

### 经验触发记录
- **EXP-2026-0027 / 0032**（路径穿越、白名单必配段级判据 + 合法正例）—— 直接塑造 D5 与 TC-CMA-006/006b 双向判据
- **EXP-2026-0026**（判据须落到函数体，不能只看 import）—— 直接塑造 D5 与 REQ-009 / TC-CMA-007
- **KG-092**（失败静默腐烂）—— 塑造 D8
- **EXP-2026-0034**（shim 替换 `Path.unlink`）—— 提醒 merge 只写不删，不加清理动作

### 已知坑点 / 注意事项
- 🔴 **两个根 canonical**：仓库根 `canonical/` 是真身（74 个被跟踪文件），`.fstdd/canonical/` 是空骨架（0 个）。
  `_get_canon_dir(None)` 原指空骨架 ⇒ D1 必修。
- ⚠️ 写 YAML 时**以反引号开头的标量值必须加双引号**，否则 `found character '`' that cannot start any token`。

### 未解决问题（待 Phase 3 验证）
- D1 改了 `_get_canon_dir(None)` ⇒ `canon init --project-level` 落点从 `.fstdd/canonical/` 变为仓库根 ⇒ 需靠既有 canon 测试兜底。
- SC-005b 的退出码取值（0 vs 非 0）—— 设计定「非 0」，Phase 3 与 D哥 确认后固化。

### 产出物清单
- `design.md` — 255 行，8 条决策 + 映射表 + 8 条风险
- `canonical/specs/code/canon-merge-automation.yaml` — **9 REQ / 12 SC**（capability 命名）
- `canonical/specs/agent/2026-10-12-canon-merge-command.yaml` — **12 CP** + rollback
- `test-plan.md` — **13 个 TC**（TC-CMA-001..010 + 003b/004b/006b）
- `canon verify` **2/2**

### 完整上下文文件清单
- `design.md`：Context（含两条 Phase 2 实拍发现）、Decisions D1–D8、Architecture、Risks
- `canonical/specs/code/canon-merge-automation.yaml`：GIVEN/WHEN/THEN 行为规格
- `canonical/specs/agent/…yaml`：12 个可执行检查点（含 fixture 隔离铁律）
- `test-plan.md`：TC-ID 映射、测试策略、回归风险矩阵、证据记录

---

## Current: Phase 2 SPEC — 等待 Gate 2 确认

### 当前状态
- 四个产出物齐备，自动审查 0 项问题，`canon verify` 2/2
- ⏳ **等待 D哥 在 Gate 2 确认**（Gate 2 不自动跳过）

### 下一步
1. D哥 回「确认」⇒ `gate approve --gate 2 --confirmed-by dialog --evidence "<原文>"`
2. 进入 Phase 3 BUILD：**第一动作 = 登记 `docs/UPSTREAM_PATCHES.md`**（D7），再动 `upstream/`
