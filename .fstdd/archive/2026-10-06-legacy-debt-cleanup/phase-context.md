# Phase Context — 2026-10-06-legacy-debt-cleanup

<!--
  阶段交接摘要 — 每个 phase 结束时由 AI 撰写对应章节。
  新 session Agent 优先读取此文件以快速恢复上下文。
  每章节末尾附「完整上下文文件清单」，需要更多细节时回溯原文。

  ⚠️ 此文件由 AI 自动维护，人类不应手动编辑。
  冲突时以各 phase 的正式产出物为准。
-->

---

## Phase 1: UNDERSTAND (completed 2026-10-06T13:31:54+00:00)

### 关键决策
- **需求边界确定**：四项遗留债务合并为一个 change 处理（测试套件编码敏感 / 发布清单失真 + 根 tests 预存失败 / canon 哈希欠账 / `_scratch/` 20MB 误入库）。理由是四者同属「门禁可信度」一条主线，单项体量都小（详见 proposal.md Constraints / NonGoals）。
- **优先级判断**：C1（编码敏感）为 P0 —— 它使门禁结果**双向**依赖环境，是「绿灯不可信」的直接来源；C4（`_scratch`）为 P0 —— 含破坏性操作风险（误删备份源）。
- **模式判定**：complexity_score = 6 → `standard`（文件数 20+ → 3｜行数 50-200 → 1｜Capability 4 → 2｜风险 低 → 0｜数据/API 无 → 0｜安全 无 → 0）。

### 用户关注点
- D哥 明确要求把四项**合并**处理（原话「新开change」），未要求拆分。
- 对「测试套件对环境编码敏感」的根因已自行定位到 `subprocess(text=True)` 不指定 `encoding=`，并要求据此修复。

### 被否决的方向
- 方向 A：拆成两个 change（test-suite-env-robustness + legacy-hygiene-cleanup）— 原因：D哥 选择合并，且四者同主线、单项小。
- 方向 B：复杂度上调为 `thorough` — 原因：纯测试/工具/文档面，无生产代码、无数据、可经 git 完全回退。

### 产出物清单
- proposal.md — Gate 1 已确认，confirmed_at: 2026-10-06T13:31:54+00:00，evidence: 「确认」
- canonical/proposals/2026-10-06-legacy-debt-cleanup.yaml — source_hash: f4c5b29793c2d38f

### 完整上下文文件清单
- proposal.md：需求背景、5 条 what_changes、4 个 modified capability、约束条件、6 条成功标准

---

## Phase 2: SPEC (completed 2026-10-06T14:00:27+00:00)

### 关键技术决策
- **决策 1（编码修复）**：逐点补 `encoding="utf-8", errors="replace"`（16 文件 36 处）— 理由：问题有**两个方向**（子进程输出 UTF-8 被 GBK 解 / 子进程输出 GBK 被 UTF-8 解），全局 `PYTHONUTF8=1` 只能压一个方向且恰恰制造第二个方向；排除：conftest 设全局环境变量（压不住 GBK 方向）、`errors="ignore"`（静默丢弃）、改 `text=False` + 手工 decode（改动面大无收益）。
- **决策 2（版本断言）**：`test_L1_11` 改为动态读 `.fstdd/version.yaml` 并与 `project.yaml` 的 `stdd_version` 比对 — 理由：硬编码把「版本一致性」降级为「人记得改」，自 3.3.1 起已过期 5 个版本；排除：每升版改字面量（注定再犯）、删除用例（丢失字段保护）。
- **决策 3（canon 哈希）**：只同步归档 `proposal.md` 的 `source_hash` → `29c0012fe4d0b612`，**不改归档正文** — 理由：V2.9.2 Canonical-First 下 YAML 是唯一源头，MD 的 `source_hash` 是「渲染自哪个 YAML 版本」的指纹；归档属历史证据，重渲染会改写其时间戳注释；排除：反向改 YAML（内容回退）、不处理（门禁永久噪声）。
- **决策 4（仓库卫生）**：`git rm -r --cached _scratch/` + `.gitignore` 加 `_scratch/` — 理由：`_scratch/` 是历史 change 明文保留的 `fstdd-fin/SKILL.md` 备份源，绝不能删磁盘；gitignore 是**必要第二步**（否则 27 文件变 untracked，撞 `test_a6_no_stray_untracked_files`）；排除：`git rm`（毁备份）、只 gitignore（对已跟踪文件无效）、`.git/info/exclude`（不随仓库传播）。

### 经验触发记录
- EXP-2026-0013（(k) 契约断层：声明形态 ≠ regex 实际可匹配形态）— 在「版本断言硬编码」场景触发，已纳入 SC-002 / SC-003 的测试覆盖。
- EXP-2026-0014（(f) 运行时行为偏差：`except Exception: pass` 静默降级）— 在「编码修复可能吞错」场景触发，已纳入 SC-004（强制 `errors="replace"`，禁止 `ignore`）。
- EXP-2026-0015（(e) 工具误用：破坏性副作用，隔离 = 移动）— 在「`_scratch/` 取消跟踪」场景触发，已纳入 SC-002（磁盘实体零损失断言）。
- EXP-2026-0016（(e) 工具误用：纯文本扫描假阳性）— 在「定向文本扫描断言」场景触发，已纳入 test-plan 回归风险矩阵。

### 已知坑点 / 注意事项
- 🔴 **`--dry-run` 对本仓 `phase advance` 无效**：`phase.py::cmd_phase` 全文无 `dry_run` 判定，参数被静默忽略后**真实落盘**。凡涉及 `phase` 子命令，不要指望 `--dry-run` 保护。
- 🔴 **`extract-proposal` 解析不可靠**：读 `proposal.md`，`_parse_capabilities` 期望 `## Capabilities` h2，而渲染器把 `### Modified Capabilities` 挂在 `## What Changes` 下 ⇒ capabilities/impact/constraints 恒返回空。**改以 canonical YAML 为源**。
- ⚠️ **`experience list --format json` 崩溃**（`experience.py:468` 缺 `default=str`，`date` 不可序列化）；文本模式可用但大量行空白（双重 frontmatter 包裹坑）。
- ⚠️ **`canon generate <change>` 单 change 只渲染 proposal**；spec.md 由 `gate approve --gate 2` 自动生成（或直调 `_generate_spec`）。
- ⚠️ **capability spec 按 capability 命名**（非 change 名）；脚手架给的 change 名文件是占位，须删除并手工登记 `.canon-index.yaml`。

### 未解决问题（待 Phase 3 验证）
- **`errors="replace"` 是否会掩盖真实失败？** 当前假设：不会 —— 它只消除解码噪声，不改变子进程退出码与断言语义。验证方式：修复前后 `pytest --collect-only -q` 用例清单逐条比对（TC-TSP-005）。
- **权威环境全量基线 `906 passed` 是否含仓库根 `tests/`？** 当前假设：含。验证方式：Phase 3 全量跑后核对 passed/skipped 计数（TC-TSP-003）。
- **非 UTF-8 环境下是否还有其它用例受影响（超出 `test_multi_platform.py`）？** 当前假设：只有该文件 2 例。验证方式：非 UTF-8 环境跑根 `tests/` 全量（TC-RTA-004）。

### 产出物清单
- design.md — Gate 2 已确认（4 决策 + 架构闭环图 + 7 条风险表）
- canonical/specs/code/{test-suite-portability, release-tooling-accuracy, canonical-hash-integrity, repo-hygiene}.yaml — 7 REQ / **16 Scenario**，confirmed
- canonical/specs/agent/2026-10-06-legacy-debt-cleanup.yaml — 10 CP 检查点 + 回滚步骤
- specs/<capability>/spec.md — 4 个 Human View（Gate 2 自动生成）
- test-plan.md — **16 TC-ID**（TC-TSP-001..005 / TC-RTA-001..004 / TC-CHI-001..003 / TC-RH-001..004），confirmed
- canonical verify: 2/2

### 完整上下文文件清单
- design.md：架构决策（Decisions 章节）、风险与缓解（Risks/Trade-offs）
- specs/<capability>/spec.md：GIVEN/WHEN/THEN 行为规格
- test-plan.md：TC-ID 映射、测试策略、回归风险矩阵、证据表

---

## Phase 3: BUILD (in_progress — 4 切片完成，Part C 进行中)

### 切片方案（Slice）
- 依赖图实测**无环**（`cycles: []`）。并行组 1 = Slice 1/3/4（互不依赖）；并行组 2 = Slice 2（依赖 Slice 1）。
- **实际执行顺序**：Slice 3 → Slice 1 → Slice 2 → Slice 4（组内按「低风险先行」自裁；Slice 2 严守 Slice 1 之后）。

| # | capability | 状态 | 关键证据 |
|---|-----------|------|---------|
| 1 | test-suite-portability | ✅ | 双环境对照**逐字一致**；审计测试 5 passed |
| 2 | release-tooling-accuracy | ✅ | 根 `tests/` `83 passed / 4 skipped / 0 failed`；tag 字面量 5→0 |
| 3 | canonical-hash-integrity | ✅ | 归档 2/2；14 条 proposal 批量 2/2 |
| 4 | repo-hygiene | ✅ | 索引 27→0；顶层实体 12→12；实体缺失 0 |

### 关键技术决策（build 期新增）
- **决策 5（ADJ-004）**：`tests/test_install_smoke.py` 的硬编码发布 tag `fstdd-v3.1.1` 改为由 `.fstdd/version.yaml` 派生。该缺陷此前被 `git fetch` 失败 → `skip` 长期掩盖（仅在 fetch 可达时才走到断言）。补 2 个**宿主隔离**用例（monkeypatch `_run`）覆盖「一致/不一致」两分支。
- **决策 6（ADJ-006）**：SC-002 的事实假设被证伪 —— `_scratch/stdd-dev/stdd-repo/` 与 `_scratch/upstream-cli-sync/` **均为空目录**（gitlink 从未 init），故不存在「备份源 `…/fstdd-fin/SKILL.md`」。SC-002 改写为以**索引实体快照**为准。
- **决策 7（ADJ-007）**：`upstream/tests/test_install_scripts.py` 的 PowerShell 生产者编码缺陷。SC-001 的 AST 判据只查「是否声明 `encoding=`」，**抓不到「声明值与生产者不符」** —— 该文件声明了 `encoding="utf-8"`，但 PowerShell 5.1 重定向时按 `[Console]::OutputEncoding`（本机 CP936）输出 GBK。修法：`_force_utf8_output()` 强制子进程以 UTF-8 写出。

### 已知坑点 / 注意事项（build 期新增）
- 🔴 **参数名不可加引号**：PowerShell 里 `'-Yes'` 是**字符串字面量**，会把 `param()` 绑定降级为位置绑定（实测 `$Platform` 被赋成 `-Python`）。`_ps_arg()` 固化「参数名原样、值才引用」。
- ⚠️ **`env -u VAR` 在本沙箱是静默空操作**：构造「非 UTF-8 环境」须用显式 `PYTHONUTF8=0 PYTHONIOENCODING=gbk`，不能 `unset`。
- ⚠️ **`verify_eol` 的 TC-EOL-005 在 BUILD 期必然红**：判据是 `git add --renormalize .` 后「索引 vs HEAD」的已跟踪文件修改，减去白名单前缀（`tools/` `docs/` `skills/` `.fstdd/experiences/` + `README.md`/`.gitignore`/`NOTICE.md`）。在办 change 必然改 `tests/` 与 `upstream/` ⇒ 报 19 项「非预期变更」（实测 19 项**全部为本 change 的正当内容修改**，零纯行尾变更）。**仅提交后复跑为绿** —— 四自检脚本须在 DELIVER 提交后复验。
- ⚠️ **`test_a6_no_stray_untracked_files` 在 BUILD 期必然红**：判据是「无未跟踪文件（除 `.fstdd/changes/`）」，新建测试文件提交前必为 `??`。已用 `git ls-files --others --exclude-standard` 证明游离项**仅**为本 change 自身文件，`_scratch/` 已不在其中。
- ⚠️ 本机 pytest 输出偶被 safe-delete 守卫截断（`state lock timeout`）⇒ 取结果改用 `--junit-xml`。

### 产出物清单
- `tests/test_subprocess_encoding_policy.py`（5）／`tests/test_canon_hash_integrity.py`（3）／`tests/test_release_manifest_accuracy.py`（8）／`tests/test_repo_hygiene_scratch.py`（8）— 共 **24 个测试函数**
- 修改 24 个既有文件（16 编码 + 7 文本 I/O + 1 PowerShell 生产者编码；1 个重叠）
- `audit/scratch-inventory.txt` — 27 条 `_scratch/` 索引实体快照（含 25 个文件 md5）
- `pending-adjustments.yaml` — **7 条偏离**（ADJ-001/004/007 major；ADJ-002/003/005/006 minor）
- `slices.md` / `tasks.md` — 切片与任务收口
- canonical 规格：7 REQ / **18 Scenario**（新增 SC-005 挂 REQ-002、SC-006 挂 REQ-001）

### 完整上下文文件清单
- slices.md：依赖图、切片表、执行结果
- tasks.md：5 组任务与勾选状态
- pending-adjustments.yaml：7 条设计偏离（Part C 将汇总为 design-adjustments.yaml）
- audit/scratch-inventory.txt：`_scratch/` 实体快照

---

## Phase 4: DELIVER (pending)

- 待填

---

## Current: Phase 3 BUILD（Part C 完成，**等待 Gate 3 确认**）

### 当前状态
- Phase 1 / Phase 2 已确认锁定；长程模式（`full_auto`）已授权。
- **4 个切片全部完成**；**Part C 质量验证（C1–C7）全部执行完毕**。
- 最终验证数据：
  - 根 `tests/` 双环境 **94 passed / 0 failed / 4 skipped**，**逐字一致**；
  - `upstream/tests`（960）**953 passed / 5 skipped / 2 failed**（1 项提交前预期 + 1 项 flaky）；
  - **本变更引入的稳定失败 = 0**。
- 待 D哥 在 Gate 3 明确确认。

### 下一步
1. **Gate 3**：等 D哥 确认 → 带 `--confirmed-by dialog --evidence <原文>` 执行 `gate approve --gate 3`。
2. **Phase 4 DELIVER**：归档 change、合并 specs、提交、**提交后复跑四自检 + `test_a6`**、升版/tag（如需）。
3. 复跑后回填 §九 #11 的验收结果。

### ⚠️ 必须复验的提交后项（BUILD 期结构性为红）
- `upstream/tests/test_repo_home.py::TestAWorkspaceIntegrity::test_a6_no_stray_untracked_files`
  —— 提交前 4 个新测试文件必为 `??`。
- `tools/verify_eol.py::TC-EOL-005`（及连锁的 `verify_rename` TC-RENAME-006）
  —— 判据为「索引 vs HEAD」，在办 change 必然报非白名单文件修改。
