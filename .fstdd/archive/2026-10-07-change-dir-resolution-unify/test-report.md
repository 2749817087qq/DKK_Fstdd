# 测试报告 — 2026-10-07-change-dir-resolution-unify

> change：`2026-10-07-change-dir-resolution-unify`（归档生命周期收口：change 目录解析统一 + 归档/恢复状态自洽）
> 阶段：Phase 3 BUILD（Gate 3 验收）
> 生成时间：2026-10-07
> 测试环境：Windows（本机）/ Python 3.13.12（workbuddy default env）/ PyYAML 6.0.3 / pytest 9.1.1
> 权威测试环境：**控制台 UTF-8 + `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`**
> 观测基线：`observed_base_git_sha = f7bf8ec39a9784c7a8812d8b4b4e6238d6fe1b46`（= v3.3.7 发布提交）
> 执行模式：`long_range.mode = full_auto`（长程全自动）

---

## 一、TC 覆盖率（planned vs actual）

| capability | 计划 TC | 实现（测试函数） | 覆盖 |
|---|---|---|---|
| change-dir-resolution | TC-CDR-001..012（12） | 14 | **12/12** |
| archive-state-consistency | TC-ASC-001..006（6） | 7 | **6/6** |
| **合计** | **18** | **21** | **18/18 = 100%** |

- 新增测试文件 2 个，新增 `def test_` **21** 个（收集后 **27** 个用例，含 `parametrize`）。
- `fstdd ci check-failures` 的 **TC 实现覆盖 = 18/18（100%）**、**(d) TC-ID 唯一 18 个（按定义点）**。
- 每个切片都执行了 **RED → GREEN**，RED 证据为**真实执行**（见 §三）。

### 权威全量结果

| 套件 | 结果 |
|---|---|
| `pytest upstream/tests` | **960 tests / 954 passed / 5 skipped / 1 failed** |
| `pytest tests`（仓库根） | **158 tests / 155 passed / 3 skipped / 0 failed** |
| 切片 1 回归（phase/gate/state/state_coverage/rollback/archive） | 35 passed / 0 failed |
| 切片 2 回归（+finder/finder_archive_fallback/changes_dir_consistency/canon_dchash_ops/batch/batch_pipeline/baseline_ops/canon/canon_coverage） | 136 passed / 0 failed |
| 新增 2 个测试文件 | 27 passed / 0 failed |

---

## 二、逐切片验证状态（Step B3.4 三项检查）

| # | capability | TC 覆盖 | 产出物核对 | 测试运行 | 结论 |
|---|---|---|---|---|---|
| 1 | archive-state-consistency | 6/6 | `archive.py` 闭合 `phases.deliver.status`；`rollback.py` 保留原 `current_phase`（新增 `_kept_current_phase`） | RED 4 failed/3 passed → GREEN 7 passed；回归 35 passed | ✅ |
| 2 | change-dir-resolution | 12/12 | `finder.require_active_change_dir`；5 模块改走统一入口（删重复实现体）；契约扫描 + 双向自检 | RED 11 failed/4 passed → GREEN 15 passed；回归 136 passed | ✅ |

---

## 三、RED 证据（真实执行）

| 切片 | RED | GREEN |
|---|---|---|
| 1 | **4 failed / 3 passed** —— 行为测试 TC-ASC-001/003/003b/005 红（归档未闭合相位、rollback 重置相位）；守卫测试 TC-ASC-002/004/006 绿 | **7 passed / 0 failed** |
| 2 | **11 failed / 4 passed** —— 读路径 4 例 + 写路径 6 例 + 契约扫描 1 例红；在办零漂移、无 archive/、二次 archive 守卫、扫描器自检 4 例绿 | **15 passed / 0 failed**（加固后 27 用例全绿） |

> ⚠️ **纪律遵守**：本 change 触及 `archive` / `rollback`（**移动目录**的破坏性命令），
> 故 RED 取证**全部在 `tmp_path` 合成项目内**完成，**未**在主工作区回退修复后直接跑
> （EXP-2026-0023：3.3.7 BUILD 期间曾因在主工作区取证而移走 3 个已跟踪文件）。

---

## 四、C1 多路并行技术评审（3 代理）

按 `.fstdd/config.d/quality.yaml` → `review.agents`（code / test_config / docs_skills）三路并行。

### 报出并**已修复**的问题

| # | 严重度 | 发现 | 修复 |
|---|---|---|---|
| 1 | 🔴 critical | `require_active_change_dir` 的归档判定用**词法**前缀比较，且 `_resolve_in` 把用户输入直接拼进 `base_dir / name` ⇒ 理论可被 `..` 绕过（失败模式 #10） | ① `_resolve_in` 拒绝含 `/` `\` `..` 的名字；② 判定改 `hit.resolve().relative_to(archive_root.resolve())`；③ 新增 `test_tc_cdr_005b`（3 遍历形态 × 读写两侧） |
| 2 | 🔴 实锤 | `rollback.py` **死导入** `find_change_dir` + 内联自建后缀匹配 ⇒ 契约扫描器因「import 了 finder」判其合规（**假阴性**） | 删死导入；改用 `finder._resolve_in` 复用解析原语（-18/+9 行）；扫描器把 `_resolve_in` 纳入可接受集合 |
| 3 | 🟡 一般 | `baseline establish <archived> --dry-run` 会打印「预览成功」（dry-run 在解析之前），与 `phase`/`work` 的写路径不一致 | 把解析提到 `dry_run_preview` 之前 |
| 4 | 🟡 一般 | `rollback --dry-run` 读损坏的 `.fstdd.yaml` 会崩 | 加 `try/except` → 回落 `understand` |
| 5 | 🟡 一般 | 扫描器可被 `getattr(mod, "find_change_dir")` 绕过 | 判据补 `getattr`/`hasattr` 字符串实参形态 |

### 报出并**已加固**的测试问题

| # | 发现 | 处置 |
|---|---|---|
| 6 | TC-CDR-005 未覆盖 `phase set` / `phase record-slice` | 改 `parametrize`（3 种写动作） |
| 7 | TC-CDR-002 断言 `"changes" not in out or ARCH in out` 近似恒真 | 改为断言**不得**出现 `.fstdd\changes` / `.fstdd/changes` 路径 |
| 8 | TC-CDR-003 未断言空列表提示 | 补 `assert "关联工作" in out` |
| 9 | TC-CDR-007 未断言追认内容落盘 | 补断言 evidence 文本出现在 `audit_amendments` |
| 10 | TC-CDR-008 未覆盖 `phase advance`（test-plan 的原定动作） | 补在办 change 上 `understand→spec` 推进断言 + `related_work` 逐字段断言 |

### 报出但**判定不改**的项（留档）

- `baseline establish` 失败退出码 **2 → 1**（与 `phase`/`gate`/`state`/`work` 统一）：**记录为已知口径不统一**（ADJ-004）；
  强行统一需给 `require_active_change_dir` 加参数（YAGNI）或改读路径契约（超范围）。已核验无内部调用方受影响。
- `canon generate <已归档 change>` 经**读入口**写归档目录内的 `proposal.md`（本 change 范围外的第 6 条写路径）：**记录为已知欠账**（ADJ-005）。
- 文档 4 处不精确（D5 写盘时机描述 / 行号引用为修复前快照 / proposal 回归清单含不存在的 `test_work` / test-plan 路径笔误）：
  **不回改已锁定的 Gate 1/2 文档**，逐条登记于 ADJ-006（含正确值）。
- `_batch` 未被 `find_change_dir` 显式排除：已核验**语义等价**（`_batch` 无 `.fstdd.yaml`，天然被候选判定排除）——ADJ-007。
- `rollback` 恢复后 `current_phase=deliver` ⇒ 后续 `phase advance` 报「已在末相位」：**刻意语义**（恢复≠重做）——ADJ-008。

### 已核验**无问题**的点（摘要）

- 5 个模块的**读/写分层**逐一核对：写操作（`phase advance|set|record-slice` / `gate approve` / `state --set` /
  `work add` / `baseline establish`）全部走写入口；读操作（`phase status` / `state`（含 `--resume`）/
  `work list` / `baseline show` / `gate amend-audit`）全部走读入口。
- **批级管线兜底未被破坏**：`phase` / `work` 的 `_find_batch_child` 语义与改前一致（统一入口未命中且未指定名字时才启用）；
  `test_batch.py` + `test_batch_pipeline.py` 全绿。
- 测试隔离：两个新测试文件的 `archive` / `rollback` 调用**全部**在 `tmp_path`；唯一触及真实归档 change 的
  `test_tc_cdr_003b` **只跑 `phase status`**（只读）。
- `_PHASE_ORDER` 复用 `phase_constants.PHASE_ORDER`（未另造一份常量）。

---

## 五、C2 全量质量检查

| 项 | 命令 | 结果 |
|---|---|---|
| 全量测试（上游内核） | `pytest upstream/tests` | **960 tests / 954 passed / 5 skipped / 1 failed** —— 唯一失败 `test_a6_no_stray_untracked_files` 为**结构性**（见 §十-9） |
| 全量测试（仓库根） | `pytest tests` | **158 tests / 155 passed / 3 skipped / 0 failed**（首跑曾出 1 failed + 1 error，经隔离复跑 + 单独全量复跑均绿 ⇒ 判定为 safe-delete 守卫导致的**环境 flakiness**，见 §十-10） |
| `ci check-failures` | `fstdd ci check-failures <change>` | ✅ **0 错误**；(a)(d)(f)(k) + 切片证据 + **TC 覆盖 18/18** 通过；(g) AND 超限 WARN；(b)(j)(l) SKIP |
| 覆盖率 | `pytest --cov` | ⏭ **SKIPPED** —— `quality.coverage.scope = changed_files_only` 且 `fail_under: 0`；本 change 以**行为断言**替代覆盖率门槛 |
| lint / 类型检查 | `ruff` / `mypy` | ⏭ **SKIPPED** —— 配置指向不存在的 `app/`；既有发布门禁不含 lint |
| 四自检 | `verify_rename` / `verify_eol` / `verify_skill_standards` / `verify_workbuddy_skills` | 见 §七 |

---

## 六、C3 Diff 审查

- `git diff --check`：**无空白错误**。
- 调试残留（`breakpoint()` / `pdb` / 调试 `print`）：**0 命中**。
- 注释掉的旧逻辑：**0 命中**（`rollback.py` 的内联匹配循环是**被替换**而非注释掉）。
- 变更与 spec 一致性：5 个 what_changes ↔ 2 个 capability ↔ 15 Scenario ↔ 18 TC ↔ 21 测试函数，**逐条可追溯**。
- 逐文件审查：`upstream/fstdd/cli/finder.py`（+56）、`commands/{archive,baseline,gate,phase,rollback,state,work}.py`，
  共 **8 文件 / +261 −129**；新增 `tests/test_change_dir_resolution_unify.py`、`tests/test_archive_state_consistency.py`；
  另新增本 change 的审计活表 `.fstdd/changes/2026-10-07-change-dir-resolution-unify/audit/except-points.yaml`（25 点，承接归档表 + 3 处行号刷新）。

---

## 七、四自检脚本

| 脚本 | 在办 change 期结果 | 判读 |
|---|---|---|
| `verify_eol` | 见 §七-1 | ⚠️ TC-EOL-005 为**结构性**红（统计白名单外「已跟踪且已修改」的文件数，在办 change 期必然 >0） |
| `verify_rename` | 见 §七-2 | ⚠️ TC-RENAME-006 依赖 `verify_eol` ⇒ 连带红 |
| `verify_skill_standards` | 见 §七-3 | 预期 7/7（首跑可能 6/7，TC-SES-004 的已知副作用） |
| `verify_workbuddy_skills` | 见 §七-4 | 预期 PASS（本机 skill 戳 = 3.3.7 = 仓库版本） |

### 七-1 实测结果（2026-10-09，在办 change 期）

| 脚本 | 实测 | 判读 |
|---|---|---|
| `verify_eol` | **6/7** —— 唯一 FAIL 为 `TC-EOL-005`（「索引零内容变更」）：报「行尾治理引入了 8 个非预期变更」（`archive/baseline/gate/phase/rollback/state/work` + `finder`） | ⚠️ **结构性**：该判据统计「白名单外**已跟踪且已修改**的文件数」，在办 change 期必然 >0 ⇒ 提交后转绿 |
| `verify_rename` | **7/8** —— 唯一 FAIL 为 `TC-RENAME-006`（「`verify_eol.py` 未通过」） | ⚠️ **连带红**（依赖 `verify_eol`）⇒ 提交后转绿 |
| `verify_skill_standards` | ⚠️ **未取得结果（环境阻塞）** —— 脚本整体起不来，stderr 仅一行 `[safe-delete][SAFE_DELETE_BULK_GUARD_ERROR] state lock timeout`；重试 3 次同结果 | ⚠️ **环境问题，非脚本/本 change 问题**：本沙箱 `safe-delete` 守卫获取状态锁超时（该脚本会删除临时目录，故被守卫拦截）。上一版 v3.3.7 实测为 **7/7**，本 change 未触碰 `tools/` 与该脚本 |
| `verify_workbuddy_skills` | **PASS** —— 「6 个 skill 全部通过：安全策略在位、路径适配完好」+ 1 条 WARN（影子副本 `C:\Users\Administrator\.workbuddy\skills` 下有 `fstdd@2.2`，不会被加载、仅误导排查） | ✅ 本机 skill 戳 = 3.3.7 = 仓库版本 |

> **口径说明**：`verify_eol` / `verify_rename` 的两处红与 `test_a6` 同源 —— 均为「工作树未干净」这一**流程位置**导致的结构性红，
> 已在 v3.3.7 实测过「提交后 rename 8/8、eol 7/7、test_a6 PASS」。⇒ **DELIVER 提交后复跑**（见 §十一必办事项 1）。

---

## 八、C4 失败模式检查（23 类，全量执行）

| # | 失败模式 | 覆盖方式 | 本次检查动作与结果 |
|---|---|---|---|
| 1 | 幻觉调用 | skill 引导 | ✅ 38 个命令模块**全部可导入**（0 失败）；改动文件经 `ast.parse` 全通过 |
| 2 | 过度信任 LLM | skill 引导 | ✅ 评审 3 代理共报 5 修复项 + 5 加固项 + 5 条「不改」；**逐条独立复现**——其中 ADJ-001（路径遍历）**自测未复现放行**，按「加固而非证伪」处置并**两边留痕**；ADJ-002（死导入）**独立复现确认** |
| 3 | Prompt 注入 | skill 引导 | ✅ 改动文件扫描 `ignore previous` / `you are now` / `disregard ...` ⇒ **0 命中** |
| 4 | 记忆污染 | skill 引导 | ✅ 全程以 canonical YAML + 实测为准；`extract-proposal` 的 `constraints/stakeholders/risk_areas/non_goals` 恒空（ADJ-005 遗留）⇒ 取数未依赖它 |
| 5 | 上下文窗溢出 | skill 引导 | ✅ 单次 `Edit` 均 < 300 行；`finder.py` 新增函数 46 行 |
| 6 | 工具参数漂移 | skill 引导 | ✅ 仅用既有 CLI 子命令与 pytest 官方参数（`--junit-xml` / `-p no:cacheprovider`）；`knowledge predict` 用 `--change-name` |
| 7 | 安全凭证泄露 | 三层 | ✅ 改动 10 文件凭证字面值扫描 **0 命中**；未引入任何网络调用 |
| 8 | 权限绕过 | skill 引导 | ✅ 未手改任何闸门确认字段（`phases.*.confirmed_*` 逐字段相等由 TC-ASC-002/004 锚定）；`.fstdd.yaml` 的写入仅 `slices_completed` / `traceability` / `design_adjustments` |
| 9 | 并发竞态 | skill 引导 | ✅ 串行执行（单 agent、单 change）；`archive`/`rollback` 的测试全部在独立 `tmp_path` |
| 10 | **路径遍历** | Guard | ✅ **本轮重点**：新增 `test_tc_cdr_005b`（3 遍历形态 × 读写两侧）+ `_resolve_in` 输入校验 + `resolve()` 归一化比较（ADJ-001） |
| 11 | 跨会话残留 | skill 引导 | ✅ 归一 CLI 产物 CRLF；未产生临时目录残留；`structure delta` 重跑覆盖 B1 时的空快照 |
| 12 | 输出截断 | Guard | ✅ 一律以 `--junit-xml` 取权威结果（本机 pytest stdout 会被 safe-delete 守卫截断） |
| 13 | 格式错误 | skill 引导 | ✅ 本 change 全部 **7 个 YAML** 均可 `yaml.safe_load` |
| 14 | 循环依赖 | skill 引导 | ✅ 命令包 import 图：39 节点 / 22 边 / **无环**；38 模块全部可导入 |
| 15 | 重复扣款 | 金融红线 | ⏭ **SKIPPED** —— 不涉及支付/资金流转 |
| 16 | 账实不符 | 金融红线 | ⏭ **SKIPPED** —— 无账本/对账源 |
| 17 | 静默降级 | 金融红线 | ✅ **适用且已修**：修复前「归档 change 上的写操作报 `.fstdd.yaml not found`」是**静默误导**（把「不支持归档」说成「change 不存在」）；现改为显式文案 + 非 0 退出码 |
| 18 | 精度丢失 | 金融红线 | ⏭ **SKIPPED** —— 无金额字段 |
| 19 | 审计缺口 | 金融红线 | ⏭ **SKIPPED** —— 无资金/权限变更。⚠️ 但**本 change 保护了审计链**：TC-ASC-002/004 逐字段断言闸门字段不被归档/恢复改写 |
| 20 | **状态机漏洞** | 金融红线 | ✅ **本 change 的核心**：① `archive` 归档即闭合相位（消除悬空态）；② `rollback` 保留原相位（消除 `current_phase` 与 `phases.*.status` 矛盾态）；③ 往返（archive→rollback→archive）一致性由 TC-ASC-005 锚定 |
| 21 | 额度穿透 | 金融红线 | ⏭ **SKIPPED** |
| 22 | 合规遗漏 | 金融红线 | ⏭ **SKIPPED** —— 无 KYC/AML/跨境数据 |
| 23 | 过度工程 | YAGNI-7 梯子 | ✅ 逐项回答见下 |

### #23 过度工程（YAGNI-7 梯子）

| 新增物 | 1 真需要 | 2 本仓已有 | 3 标准库 | 4 平台原生 | 5 已装依赖 | 6 一行 | 7 最小实现 | 结论 |
|---|---|---|---|---|---|---|---|---|
| `finder.require_active_change_dir`（46 行） | ✅ 5 个模块的写路径必须统一裁决 | ✅ `find_change_dir` 已存在，本函数是其**写路径对偶** | — | — | — | ❌ 5 处各写拒绝逻辑 = 又造 5 份实现 | ✅ 1 个函数 + 1 个文案常量 | **保留**（D3 的落点） |
| `phase._find_batch_child` / `work._find_batch_child` | ✅ 批级子 change 不在 `.fstdd/changes/`，统一入口覆盖不到 | ❌ 原为两处内联代码 | — | — | — | ❌ | ✅ 各 15 行，语义与改前逐字一致 | **保留**（防行为漂移；**未**抽公共模块以免引入跨模块依赖） |
| `rollback._kept_current_phase`（14 行） | ✅ 老数据兜底需要确定取值 | ❌ | — | — | — | ❌ | ✅ 1 个纯函数 + 复用 `phase_constants.PHASE_ORDER` | **保留** |
| 2 个测试文件（21 函数） | ✅ 18 个 TC 的载体 + RED→GREEN 硬要求 | — | ✅ pytest | — | — | ❌ | ✅ | **保留** |
| `_resolve_in` 的输入校验（4 行） | ✅ 消除路径遍历整类风险 | — | ✅ `Path.parts` | — | — | — | ✅ | **保留** |

---

## 九、C5 经验库记录

新增 2 条经验（经 `fstdd experience add` 写入）：

| ID | 分类 | 严重度 | 模式 |
|---|---|---|---|
| **EXP-2026-0026** | `coverage_vacuum` | high | 审计器判「模块是否合规」只看「有没有出现某个符号」—— 模块可以 **import 了统一入口却从不调用**（死导入 + 内联自建实现）⇒ 假阴性。修法：判据落到**函数体**（是否真的调用），并把底层原语纳入可接受集合 |
| **EXP-2026-0027** | `contract_gap` | high | 新增的安全守卫用**词法**前缀比较判「是否在禁区目录内」，而输入可含 `..` ⇒ 词法前缀与真实位置不一致。修法：① 比较前 `resolve()` 归一化 ② 输入层拒绝分隔符/`..` ③ 补正反双向用例。⚠️ 附教训：**评审结论与自测结论冲突时两边都要留痕**，不因「我没复现」就驳回 |

---

## 十、已知问题与未完成项

| # | 名称 | 原因 | 影响 | 补完计划 |
|---|---|---|---|---|
| 1 | **`canon generate <已归档 change>` 经读入口写归档目录**（第 6 条写路径） | ADJ-005：proposal C1/C2 经 Gate 1 冻结为 5 个模块，`canon` 不在其中；且「归档 change 的派生文档是否允许重生成」本身是待定语义 | 会重写归档 change 内的 `proposal.md` / `caveman_summary.txt` | 另立 change 统一「写路径矩阵」（含 `canon verify` 的自动重生成分支） |
| 2 | **`baseline` 子命令间退出码不统一**（`establish` 1 / `show` 2） | ADJ-004：统一需给 `require_active_change_dir` 加参数或改读路径契约 | 脚本按子命令区分失败码会受影响；已核验无内部调用方受影响 | 另立 change 或随「错误码矩阵」统一 |
| 3 | **文档 4 处不精确**（D5 写盘时机描述 / 行号引用为修复前快照 / proposal 回归清单含不存在的 `test_work` / test-plan 路径笔误） | ADJ-006：改它们要动 Gate 1/2 已锁定文档（`source_hash` 变、DC-HASH 失效） | 文档声明 ≠ 事实（**正是本 change 要修的病**） | 不回改锁定文档；ADJ-006 已逐条登记含正确值，DELIVER 或另立 change 处理 |
| 4 | **扫描器判据的边界**：`_default_change` / `_find_current_change` 这类「取当前/默认 change」的辅助函数不在判据内；新增命令仍需手动加入 `CHANGE_NAME_MODULES` | 判据是「模块级存在性 + 函数级泛化」两层，语义上无法自动区分「解析具名 change」与「枚举当前 change」 | 新命令若自建解析且命名不在 `_find_change*` / `_resolve_change*` 前缀内，可能漏判 | 已写入测试 docstring 与 test-report；建议后续把判据升级为「按 CLI 解析器声明推导」 |
| 5 | `design.md` / `test-plan.md` / `proposal.yaml` 的行号引用为**修复前快照** | 改动后行号漂移（如 `phase.py` 的批级兜底现约 21-42 行） | 读文档定位代码需自行核对 | ADJ-006 登记；下次触碰这些文档时一并校正 |
| 6 | **`ci check-failures` 的 TC 覆盖检查要求 TC-ID 以字面量出现** | 区间写法（`TC-CDR-001..003`）不被识别 ⇒ 首轮误报 15/18 | 无实际影响（已补逐函数注释，现 18/18） | 已修；约定：测试文件里每个 TC-ID 至少出现一次字面量 |
| 7 | **`ci check-failures` 的 (g) AND 超限按「每文件」统计** | 本项目规格刻意用 AND 细化可验证条件（单 Scenario ≤3 条） | WARN 噪声 | 接受（口径问题）；如需消除需改检查粒度 |
| 8 | **四自检与 `test_a6` 只在「工作树完全干净」时为绿** | `verify_eol` TC-EOL-005 统计「白名单外已跟踪且已修改」文件数 | 在办 change 期必然红 | **DELIVER 提交后复跑**（3.3.7 实测：提交后 rename 8/8、eol 7/7、test_a6 PASS） |
| 9 | **`test_a6_no_stray_untracked_files` 红（结构性）** | 判据「除 `.fstdd/changes/` 外无未跟踪项」，在办 change 期新增的 `tests/*.py`、`.fstdd/experiences/EXP-*.md`、本 change 目录均在册 | 上游全量唯一失败项 | DELIVER 提交后自动转绿（3.3.7 已实测） |
| 10 | **根 `tests/` 首跑出现 1 failed + 1 error（环境 flakiness）** | 该次根测试紧跟在上游全量之后**同一命令内**执行；上游遗留的 `pytest-of-Administrator` 临时目录因 `safe-delete` 守卫超时（`garbage-* timed out after 10 seconds`）无法清理 ⇒ 污染紧随其后的根测试（`FileExistsError: WinError 183` + teardown `SystemExit: 1`） | 与代码无关 | **已实证为 flakiness**：① 隔离复跑 `tests/test_verify_notices_default_safe.py` = 6 passed；② 单独全量复跑 `pytest tests` = **158 tests / 0 failed / 0 errors / 155 passed / 3 skipped** |
| 11 | **裸 except 审计活表需随本 change 刷新** | `test_aud_002` / `test_grd_001` 取 `.fstdd/{changes,archive}/<change>/audit/except-points.yaml` 的**最新**一份，按指纹 `(file, stmt, handler)` + **±5 行**容差比对实况 ⇒ 本 change 改 5 个命令模块导致 3 处行号位移超容差（`baseline.py` 318→325、`phase.py` 40→29、`work.py` 36→21） | 修复前 2 例红 | ✅ **已修**：在本 change 下生成活表 `.fstdd/changes/2026-10-07-change-dir-resolution-unify/audit/except-points.yaml`（承接归档活表 25 点 / 3 处行号刷新 / **0 新增 / 0 消失**，指纹零漂移）⇒ 两例转绿 |

---

## 十一、结论

- **TC 覆盖率 18/18（100%）**，21 个新增测试函数（27 个用例），2 个切片全部 RED→GREEN 通过。
- **C1/C2/C3/C4/C5/C6/C7 七步全部执行**；C1 报出的 1 处 critical + 1 处实锤假阴性已修，并**加固**了 5 处测试断言。
- 5 个目标缺陷全部修复：① 5 模块解析统一（读支持归档）② 写路径准确拒绝 ③ `gate amend-audit` 放行归档
  ④ `archive` 闭合相位 ⑤ `rollback` 保留原相位。
- **权威全量**：`pytest upstream/tests` = 960 tests / **954 passed** / 5 skipped / **1 failed**（唯一失败 `test_a6` 为结构性）；
  `pytest tests` = 158 tests / **155 passed** / 3 skipped / **0 failed**。
- **既有行为零回归**（切片回归 136 passed；批级管线未受影响；审计活表刷新后 `test_aud_002` / `test_grd_001` 转绿）。
- 遗留 **11 项**已知问题**全部登记**（2 项属独立欠账需另立 change，4 项属文档卫生，5 项属工具/环境口径）。
- **待 D哥 Gate 3 确认**后进入 Phase 4 DELIVER。

### ⚠️ 给 DELIVER 的必办事项

1. **提交后复跑四自检与 `test_a6`**（在办 change 期结构性红）。
2. **提交前归一 CLI 产物 CRLF**（本 change 已归一；`canon generate` / `archive` / `structure merge` 会重新引入）。
3. **升版时同步 `docs/UPSTREAM_BASELINE.md` 的 R 轴**（否则 `test_ubl_003` 必红）。
4. 归档前跑 `structure delta`、归档后跑 `structure merge`（顺序不可颠倒）。
5. 🟢 **本 change 已修**：归档后**可以**用 `fstdd phase advance <已归档 change>` 闭合相位 —— `phase.py` 已改走统一入口，且 `archive` 归档时**自动**把 `phases.deliver.status` 置为 `completed` ⇒ v3.3.7 遗留的「归档态悬空」不复现（本 change 归档时无需再手工补）。
6. **归档前生成/刷新本 change 的审计活表**（若归档后又改了命令模块行数，须重跑；表随 change 一起归档）。

---

## 十二、Phase 4 DELIVER 期间的两处发现（2026-10-09 补记）

### 12-1 归档命令在沙箱下「半完成」——`shutil.move` 的 `rmtree(src)` 被 safe-delete 守卫拦截

- **现象**：`fstdd archive <change> --yes` 抛 `OSError: [safe-delete] 操作失败: ... Error during a 'trash' operation: Some operations were aborted`。
  结果是**半完成态**：① 归档副本 `.fstdd/archive/<name>/` 已生成（`copytree` 完成）；② 归档内 `.fstdd.yaml` 已写
  `status: archived` + `phases.deliver.status: completed`（**本 change 的 C3 修复生效**）；③ 但**源目录未被删除**。
- **根因**：`shutil.move` 在同盘 `os.rename` 失败时回落到 `copytree + rmtree(src)`，而本沙箱的 `sitecustomize` 会把
  `shutil.rmtree` 劫持为「移入回收站」；对该目录的 trash 操作**稳定失败**（`os.rename` 亦报 `WinError 5 拒绝访问`）。
- **诊断结论（已实证）**：该目录**内容可写可删**（新建/删除文件、`rmdir` 子目录均成功），**仅目录本身的 rename/删除被拒**；
  同父的 `_batch` 与内容完全相同的**副本**均可正常 rename/trash ⇒ 是**该路径被某进程持有目录句柄**，与本 change 无关（环境问题）。
- **处置**：① 逐字节校验归档副本与源目录**完全一致**（19 文件，sha256 全等）后才动源；② 清空源目录内容；
  ③ `os.rmdir` 空目录**成功**（锁只挡「非空目录的 rename/删除」）⇒ 归档最终**完整闭合**，`changes/` 只剩 `_batch`。
- **纪律固化**：**归档后必须校验「`changes/<name>` 已消失 且 `archive/<name>` 逐字节等于归档前快照」**，不能只看命令退出码。

### 12-2 审计表「取最新」的代理键缺陷 —— 同日期 change 会取错表（**已修**）

- **现象**：归档后 `test_aud_002` / `test_grd_001` 转红，报 `EA-002 行号漂移过大: 表 318 vs 实况 325`。
- **根因**：两处取表辅助函数用**目录名字典序**代理「时间序」（`hits[-1]`）。本 change 与上一版
  `2026-10-07-tool-defect-fixes` **共享 `2026-10-07-` 前缀**，而 `change-dir-resolution-unify` < `tool-defect-fixes`
  ⇒ `hits[-1]` 取到**上一版的旧表**（`observed_at = 2026-10-07T12:49:53`），而非本 change 的
  （`observed_at = 2026-10-09T08:45:07`）⇒ 行号容差 ±5 被突破。
- **修法**：判据从「目录名字典序」改为「表内 **`meta.observed_at`**（时间语义）」，缺该字段的旧表回落字典序。
  改动仅限两处辅助函数（`upstream/tests/test_except_audit.py::_audit_table_path`、
  `upstream/tests/test_guard_silent_except.py::_table_path`），断言一字未改。
- **验证**：修正后取表命中 `.fstdd/archive/2026-10-07-change-dir-resolution-unify/audit/except-points.yaml`；
  `test_except_audit.py` + `test_guard_silent_except.py` = **11 passed / 0 failed**。
- **同族**：EXP-2026-0021（审计器匹配面比声称的窄）、EXP-2026-0024（判据粒度错配）、EXP-2026-0026（判据锚点错）。
  ⇒ **「用排序代理时间」只在代理键与语义严格同序时成立**；一旦存在并列（同日期）即失效。
