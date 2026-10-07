# 3.3.6+ 任务清单 — 2026-10-07-tool-defect-fixes

> 执行顺序：**S2 → S4 → S1 → S5 → S3**（风险升序；S3 改共享渲染器，排最后）

## 2. experience-io-contract（P0，🟢 低 · 先做）✅ 完成 2026-10-06

- [x] 2.1 新增 `tests/test_experience_io_contract.py`：`--format json` 无过滤可解析（TC-EIO-003）→ 确认 RED
- [x] 2.2 `experience.py::_save_index()` 的 2 处 `open(...)` 补 `newline=""`（TC-EIO-001/002）
- [x] 2.3 `experience.py` 引入 `_json_default()`，覆盖全部 5 个 `json.dumps` 调用点（468/539/638/1186/1253）（TC-EIO-004）
- [x] 2.4 断言既有可序列化输出逐字节不变（TC-EIO-005）
- [x] 2.5 回归：`test_experience.py` / `test_experience_v29.py` / `test_experience_glob_consistency.py` / `test_experience_index_freshness.py`

## 4. ci-check-accuracy（P0，🟢 中）✅ 完成 2026-10-07

- [x] 4.1 新增 `tests/test_ci_tcid_definition.py`：41 份既有 test-plan 零误判（TC-CCA-001）→ 确认 RED
- [x] 4.2 构造「两个定义点」样本须 FAIL、「一个定义点 + 多处引用」须 PASS（TC-CCA-002）
- [x] 4.3 `ci.py::check_tcid_unique()` 改按定义点判定
      —— ⚠️ 评审后加固：形态 B（ID 作首列）**只在形态 A 抽不到时**才启用（否则会把
      「TC↔测试函数映射表」误计为定义点，实测 `2026-09-25-guard-phase-path-scope` 会假红）
- [x] 4.4 回归：`test_ci.py`（23 passed）

## 1. dry-run-fidelity（P0，🟢 中）✅ 完成 2026-10-07

- [x] 1.1 新增 `tests/test_dry_run_fidelity.py`：dry-run 后 `.fstdd.yaml` 字节与 mtime 不变（TC-DRY-001）→ 确认 RED
- [x] 1.2 契约扫描测试：凡有写操作的命令模块必须处理 `dry_run`（TC-DRY-003）
- [x] 1.3 扫描器自检：识别 `getattr(args,"dry_run",…)` 与 `args.dry_run` 两种写法（TC-DRY-004）
      —— ⚠️ 评审后改 **AST 口径**并补反向样本（注释/docstring/字符串字面量提及 ⇒ 判「未处理」）
- [x] 1.4 `phase.py::cmd_phase` 补 dry-run 分支（按既有范式 + 早返回 + 打印 from → to）
- [x] 1.5 断言非 dry-run 路径行为不变（TC-DRY-002）
- [x] 1.6 回归：`test_phase.py`（258 行）
- [x] 1.7 ⚠️ **评审追加**：`canon verify --dry-run` 仍会经 `_generate_one` 落盘 → 补守卫
      + 新增行为断言 `TC-DRY-003c`（静态扫描因 canon.py 已含 dry_run 而漏判）

## 5. quarantine-opt-in-safety（P0，🟢 中 · 行为语义变更）✅ 完成 2026-10-07

- [x] 5.1 新增 `tests/test_verify_notices_default_safe.py`：默认运行后目录零变化（TC-QIS-001）→ 确认 RED（6 failed）
- [x] 5.2 `tools/verify_notices.py::verify_notices()` 增 `quarantine: bool = False` 形参；为 `False` 时不移动
- [x] 5.3 CLI 增 `--quarantine`；`--json` 顶层增 `would_quarantine` 键（TC-QIS-003）
- [x] 5.4 docstring 与 `--help` 与行为对齐（模块头 + 退出码契约改写 + 人类可读输出提示）
- [x] 5.5 断言 `--quarantine` 时行为与修复前一致（TC-QIS-002）
- [x] 5.6 回归：`tools/test_verify_notices.py`（20 passed / 1 skipped）
      —— ⚠️ 修正 2 个断言旧默认行为的既有用例：`TC_NAV_009` 显式传 `quarantine=True`；
      `TC_NAV_015` 由「恰好 4 键」改为「既有 4 键须存在」子集断言（第 5 键由 TC-QIS-003 锚定）

## 3. proposal-extraction-fidelity（P0，🟡 高 · 最后做）✅ 完成 2026-10-07

- [x] 3.1 新增 `tests/test_proposal_extraction_fidelity.py`：渲染结果含 `## Capabilities` / `## Impact`（TC-PXF-001）→ 确认 RED（5 failed）
- [x] 3.2 抽 h2/h3 锚点常量到共享位置（**新增** `upstream/fstdd/cli/commands/_proposal_anchors.py`）；
      `canon.py` 渲染器补出两个 h2；`## What Changes` 段不再含 capability
- [x] 3.3 `extract_proposal.py::_parse_capabilities()` 兼容 h2/h3；`what_changes` 在首个 capability 锚点处截断
- [x] 3.4 断言 `extract-proposal` 返回非空且无泄漏（TC-PXF-002）
- [x] 3.5 断言历史 h3 形态仍可解析，且两形态结果一致（TC-PXF-003；含对 `.fstdd/archive/` 真实样本的只读验证）
- [x] 3.6 重渲染本 change 的 `proposal.md`；复核 `canon verify` 仍 **2/2**（source_hash `8be04ae641046ce6` 未变）
- [x] 3.7 回归：`test_canon.py` / `test_canon_coverage.py`（13 passed）

## 6. 测试与验证（全切片后）✅ 完成 2026-10-07

- [x] 6.1 全量 `pytest upstream/tests` 0 failed
      —— 首跑 **951 passed / 5 skipped / 4 failed**；逐条实证后 **3 修 1 结构性**
      （`test_a6` 在办 change 期必红，DELIVER 提交后转绿）；最终复跑结果见 test-report §一
- [x] 6.2 根 `tests/` 全量 0 failed
      —— 首跑 127 passed / 3 skipped / **1 failed**（`test_ubl_003`，上一版遗留的
      `docs/UPSTREAM_BASELINE.md` R 轴失真）⇒ 已纠正 → 复跑通过
- [x] 6.3 四自检脚本（rename 7/8 · eol 6/7 · skill_standards 7/7 · workbuddy_skills PASS+WARN）
      —— 两处红均为**结构性**（TC-EOL-005 / TC-RENAME-006 判据为「索引 vs HEAD」，须 DELIVER 提交后复跑）
- [x] 6.4 多路并行技术评审（C1，3 代理）—— 报 9 条 + 4 条「不改」；3 处生产缺陷已修、6 条测试问题已加固
- [x] 6.5 `fstdd ci check-failures`（C2）—— 6 通过 / 1 警告 / 3 跳过 / 0 错误
- [x] 6.6 Diff 审查（C3）—— `git diff --check` 干净；0 调试残留；0 注释掉的旧逻辑
- [x] 6.7 失败模式检查 23 项（C4）—— 14 ✅ / 9 SKIPPED（金融红线 8 项 + 覆盖率）；逐项动作与证据见 test-report §八
- [x] 6.8 经验库记录/更新（C5）—— 新增 **EXP-2026-0023 / 0024 / 0025**
- [x] 6.9 design-adjustments（C6）—— `design-adjustments.yaml`（8 条：3 闭合 / 4 欠账 / 1 记录）
- [x] 6.10 test-report.md（C7）—— 已生成

## ⚠️ 本 change 自设纪律（因待修缺陷会干扰自身验证）

- [x] 全程**不使用** `phase advance --dry-run`（缺陷 1 未修前会真实落盘）
- [x] 每次跑过 `experience` 命令后，检查 `.fstdd/experiences/.experience-index.yaml` 是否被写成 CRLF，
      提交前归一或 `git checkout` 还原（缺陷 2 已活体复现过一次）
      —— 本轮（Slice 3/5）未执行任何 `experience` 命令；实测索引仍为 `CRLF=0 / bare_LF=322`，与 HEAD 逐字节一致
- [x] ⚠️ **追加纪律（Slice 3 发现）**：`canon generate` 会把 `proposal.md` / `caveman_summary.txt`
      写成 CRLF（`canon.py` 的 `write_text` 未传 `newline=`，属 ADJ-002 同族）⇒ 重渲染后**必须归一为 LF**（本轮已归一）

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->
