# Phase Context — 2026-10-11-share-hardening-audit-fixes

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
-->

---

## Phase 1: UNDERSTAND (completed 2026-10-11T10:14:58+00:00)

### 关键决策
- **需求边界确定**：本 change 是「按外部交付件 `DKK_Fstdd_audited_fixed.tar.gz` 的**意图**在本仓 HEAD 上重做」，不是照搬其字节（详见 proposal.md Constraints）。
- **优先级判断**：P0 —— 外部交付件本身有 critical 缺陷（`share_experience.py` import 即崩）+ 打破 3 个上游测试 + 零新增测试；且该链路是经验回传（DELIVER 静默回传 / `--publish` / `inbox_pull`）的唯一通道。

### 用户关注点
- 用户在 Gate 3 后明确选择**选项 2「我们按意图重做」**（而非退回提供方或仅留档）。
- 用户要求：补测试 + 升版 + changelog，且**不与上一 change 混在同一次提交**（先收掉 experience-center-node-sync 再开本 change）。

### 被否决的方向
- 方向 A「原样采用 tarball」— 原因：其 `OUTBOUND_RESIDUAL_RE` 内联 `(?i)` 在 Python 3.11+ 抛 `re.PatternError`，模块 import 即崩。
- 方向 B「退回提供方等重发」— 原因：用户选 2。

### 产出物清单
- proposal.md — Gate 1 已确认，confirmed_at: 2026-10-11T10:14:58+00:00

### 完整上下文文件清单
- proposal.md：需求背景、12 项变更（C1–C12）、3 capability、SC1–SC10
- `_incoming/ANALYSIS-DKK_Fstdd_audited_fixed-2026-10-11.md`：外部交付件的实测比对分析（缺陷证据）

---

## Phase 2: SPEC (completed 2026-10-11T13:59:25+00:00)

### 关键技术决策
- 决策 1：**脱敏规则同源对齐** —— 扩 `SANITIZE_RULES` 表，`OUTBOUND_RESIDUAL_RE` 与之同源（用 `re.IGNORECASE`，不用内联 `(?i)`）— 理由：防止「声明形态与实现不覆盖」；排除：内联 flags。
- 决策 2：**scp 目标输入校验** —— 新增 `_validate_remote_path()` 防 shell 注入。
- 决策 3：**token 文件权限告警** —— 新增 `_check_token_file_permissions()`（权限过宽只告警不阻断）。
- 决策 4：**`publish(pre_staged=)`** —— 防二次脱敏，只在内部 staging 时清理；并同步修测试桩。
- 决策 5：`strip_frontmatter()` 改逐行扫描。
- 决策 6：安全策略文本**模板化**（外置 `tools/templates/*.md.j2`，保留 fallback）。
- 决策 7：CLI 冒烟加 30s 超时 + `install.sh` 参数校验。
- 决策 8：`utils.py` 源根查找加 `max_depth=50`（防符号链接循环）。
- 决策 9：纯内容/注释类补充（C11/C12）。

### 经验触发记录
- EXP FSTDD005-EXP-20260918-C4（第二层防线天然不可观测）— 触发 ⇒ SC-004 改为**直接断言 `OUTBOUND_RESIDUAL_RE` 常量本身**，而非只做端到端断言。
- EXP-2026-0013（契约断层：声明形态与实现不覆盖）— 触发 ⇒ 每条脱敏规则必须**同时**出现在 `SANITIZE_RULES` 与 `OUTBOUND_RESIDUAL_RE`，并用同一组形态参数化断言。

### 已知坑点 / 注意事项
- `share_experience.py` 走 `importlib` 绝对路径加载（`tests/test_share_publish_sanitize.py`），非包导入。
- 行尾：CLI 产物会写 CRLF，改文件后须 `verify_eol --fix` 归一。

### 未解决问题（待 Phase 3 验证）
- `pre_staged=` 参数加入后，既有测试桩 `def fake_publish(out_dir, repo, tok)` 需同步更新（否则 `test_silent_share.py` 3 红）。

### 产出物清单
- design.md — Gate 2 已确认
- specs/share-hardening-audit-fixes/spec.md — 22 个 Scenario，confirmed
- test-plan.md — 22 个 TC-ID（P0 14 / P1 7 / P2 1），confirmed
- canonical/specs/{code,agent}/*.yaml — YAML-first 源

### 完整上下文文件清单
- design.md：Decisions 1–9、Architecture、Risks/Trade-offs
- specs/share-hardening-audit-fixes/spec.md：GIVEN/WHEN/THEN 行为规格
- test-plan.md：TC-ID 映射、测试策略、回归风险矩阵

---

## Phase 3: BUILD (in_progress → 待 Gate 3)

> V3.0.5：SLICE / BUILD / VERIFY 三阶段合一。执行模式 = **full_auto（长程）**。

### 切片方案（Slice）
- Slice 1（P0）：脱敏补漏 + 第二层防线同源 — 5 TC
- Slice 2（P0）：scp 注入防护 + token 权限告警 — 3 TC（依赖 1）
- Slice 3（P0）：publish pre_staged + 重命名 + 测试桩同步 — 4 TC（依赖 1）
- Slice 4（P0）：strip_frontmatter + 安全策略模板化 — 4 TC
- Slice 5（P1）：CLI 冒烟超时 + install.sh 参数校验 + 源根深度上限 — 4 TC
- Slice 6（P1）：金融红线补充 + 不回归 — 2 TC
- parallel_group：全部零依赖；实际**串行**执行（沙箱并发重删除进程会触发 safe-delete 守卫状态锁竞争，EXP-2026-0029）

### 风险提示
- Slice 1–3 同改 `tools/share_experience.py`（脱敏是出站不变量，风险 🟡 高，风险分 5）
- Slice 4 改 `tools/install_workbuddy_skills.py` ⇒ 会影响全局 skill；**所有 install 测试一律用 `FSTDD_OUT` 隔离输出目录**
- Slice 5 改 `upstream/fstdd/cli/utils.py` ⇒ 会牵动裸 except 审计表行号（已一并刷新）

### 实现决策（非设计偏离）
- Jinja2 渲染用 `Environment(keep_trailing_newline=True)` ⇒ 模板渲染结果与内嵌常量**逐字节等价**（默认会吞尾换行）
- `OUTBOUND_RESIDUAL_RE` 新增形态一律带 `(?!<)` 负向前视 ⇒ 脱敏后的占位符（`?token=<REDACTED>`）不被误判为残余而整条剔除
- `_validate_remote_path` 用 `fullmatch`（非 `match`+`$`）⇒ 消除「尾随换行被 `$` 放行」的注入面

### 设计偏离汇总
<!-- 详见 design-adjustments.yaml / pending-adjustments.yaml -->
- ADJ-001（Minor）：`_validate_remote_path` 白名单放宽 `[\w.@:/-]` + 显式拒 `..` 段 + **拒前导 `-`**（C1 medium 修复）
- ADJ-002（Minor）：源根深度上限抽为 `_find_source_root(start, max_depth)`（可测性）
- ADJ-003（Minor）：冒烟超时可由 `FSTDD_SMOKE_TIMEOUT` 覆盖（默认 30s 不变；非法值回落 30）
- ADJ-004（Minor）：`silent_share()` 改传 `pre_staged=True`，测试桩 **3 处** 同步（设计预期 1 处）
- ADJ-005（Minor）：附带修复——刷新裸 except 审计活表 + 修上一 change 追溯测试的归档路径
- ADJ-006（Minor）：C12 的 `# noqa: E501` 不落地（实测会引入 RUF100 新违规；目的已由块注释达成）
- ADJ-007（Minor）：`code-structure-delta.md` 人工补全（CLI 自动段判据过窄，历史 change 同形）

### 经验触发记录
- `EXP-2026-0013`（声明与实现不覆盖）→ 3 条新规则**同时**落 `SANITIZE_RULES` 与 `OUTBOUND_RESIDUAL_RE`
- `FSTDD005-EXP-20260918-C4`（第二层防线不可观测）→ TC-SEG-004 直断言常量本身
- `EXP-2026-0017`（脱敏只做在导出、发送直读源目录）→ 保留 `publish_via_*` 出站收口；`pre_staged` 仅对「已自行脱敏」的调用方开放
- `EXP-2026-0024`（判据粒度错配）→ 安装测试一律 `FSTDD_OUT` 隔离 + 断言真实目录未被写
- 新增 `EXP-2026-0031`（模块级正则内联 `(?i)` ⇒ import 即崩）/ `EXP-2026-0032`（字符白名单拦不住 `..` 上跳；且漏 `@`/`:` 会误拒 `user@host`）/ `EXP-2026-0033`（第二层防线把脱敏后的占位符误判为残余 ⇒ 整条剔除）

### 切片完成状态
| Slice | TC覆盖 | 新增用例 | 状态 |
|-------|--------|---------|:---:|
| 1 | 5/5 | 8 | ✅ |
| 2 | 3/3 | 19 | ✅ |
| 3 | 4/4 | 4 | ✅ |
| 4 | 4/4 | 7 | ✅ |
| 5 | 4/4 | 6 | ✅ |
| 6 | 2/2 | 2 | ✅ |

### 测试结果摘要（Verify）
- 本 change 新测试：`tests/test_share_hardening.py`(15 函数/31 用例) + `tests/test_install_script_robustness.py`(15/15) + `tests/test_share_hardening_tc_traceability.py`(3/3) = **33 函数 / 49 用例**
- 全量回归：见 test-report.md §四（唯一允许失败 = `test_a6`，提交后转绿）
- `ci check-failures`：0 错误 / 0 警告，TC 实现覆盖 **24/24 (100%)**
- ruff：改动文件的规则画像与 HEAD 基线**逐条一致**（零新增问题类型）
- C1 三路评审：3 代理全部返回；**1 项 medium（前导 `-` ssh 选项注入）已修** + 5 项 low 已处置 + 3 项「高」文档问题已闭合（2 修 + 1 登记 ADJ-006）

### 设计偏离确认
- **7 条偏离（0 Major / 7 Minor）**全部登记于 `pending-adjustments.yaml`，汇总见 `design-adjustments.yaml`

### 产出物清单
- `slices.md` / `tasks.md`
- 源文件：`tools/share_experience.py`、`tools/install_workbuddy_skills.py`、`tools/verify_workbuddy_skills.py`、`upstream/fstdd/cli/utils.py`、`install.sh`、`skills/fstdd-fin/SKILL.md`
- 新增：`tools/templates/*.md.j2`（3）
- 测试：`tests/test_share_hardening.py`、`tests/test_install_script_robustness.py`、`tests/test_share_hardening_tc_traceability.py`；改 `upstream/tests/test_silent_share.py`、`tests/test_experience_sync_tc_traceability.py`
- 审计活表：`audit/except-points.yaml`
- `test-report.md` / `design-adjustments.yaml`

### 完整上下文文件清单
- `slices.md`、`tasks.md`、`pending-adjustments.yaml`、`design-adjustments.yaml`、`test-report.md`
- 关键源文件：`tools/share_experience.py`（`_validate_remote_path` / `_check_token_file_permissions` / `publish` / `silent_share`）、`tools/install_workbuddy_skills.py`（`strip_frontmatter` / `_render_template`）、`upstream/fstdd/cli/utils.py`（`_find_source_root`）

---

## Phase 4: DELIVER (pending)

### 归档
- 待填

### 版本
- 待填

---

## Current: Phase 3 BUILD（Gate 3 待确认）

### 当前状态
- 6 切片全部 RED→GREEN 并通过 per-slice 验证；C1–C7 质量验证执行中/已完成。

### 下一步
- 展示 Gate 3 验收框 → 用户确认 → Phase 4 DELIVER。

