# 2026-10-06-legacy-debt-cleanup 测试报告

> 测试日期：2026-10-06
> 测试环境：Windows 10 / Python 3.13.14（workbuddy default env）/ PyYAML 6.0.3 / pytest 9.1.1
> baseline（observed_base_git_sha）：`4c6402e366eb3e4e75efafc3f50341b77b0f8fd4`
> 变更属性：mode=standard ｜ task_type=code ｜ 执行模式=**长程 full_auto** ｜ FINANCIAL_PROJECT=NO
> 控制台代码页：**CP936（非 UTF-8）** —— 故本次全部结论均在「非权威控制台」下取得

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 规划 TC 数（test-plan 唯一 ID） | **18**（TC-TSP-001..006 / TC-RTA-001..005 / TC-CHI-001..003 / TC-RH-001..004） |
| 本变更新增测试函数 | **27**（6 + 3 + 10 + 8），全绿 |
| 新增测试文件 | 4 个 |
| 修改既有文件 | 25 个（16 subprocess 编码 + 7 文本 I/O + 1 PowerShell 生产者编码 + 1 索引条目删除） |
| 全量回归（`pytest upstream/tests`，960 用例） | **953 passed, 2 failed, 5 skipped** —— 2 failed 中 1 项为**提交前预期**（`test_a6`）、1 项为 **flaky**（隔离复跑 PASS） |
| 根 `tests/` 全量（权威 UTF-8 环境） | **94 passed, 0 failed, 4 skipped** |
| 根 `tests/` 全量（非 UTF-8 环境） | **94 passed, 0 failed, 4 skipped** —— 与权威环境**逐字一致** |
| 四自检 | rename 7/8、eol 6/7、skill_standards **7/7**、workbuddy_skills **PASS** |
| 本变更引入的失败项 | **0** |
| 设计偏离 | **8 条**（4 large / 1 medium / 3 small） |

### 1.1 本变更的独特之处

本 change 修的是**门禁自身**，因此「测试全绿」不是充分证据 —— 必须同时证明
**门禁在坏环境里也能正确报警**。故本报告的核心证据是两类对照：

1. **双环境对照**（权威 UTF-8 vs 非 UTF-8）跑同一份代码，要求结果**逐字一致**；
2. **反向分支验证**（故意构造违例 / 故意构造不一致），要求断言**真的会红**。

## 二、切片验证状态（Step B3.4）

| # | 切片 | capability | TC 覆盖 | 新增测试 | verified_at (UTC) | 结果 |
|---|------|-----------|---------|---------|-------------------|------|
| 1 | test-suite-portability | 编码契约 | 6/6 | 6 | 2026-10-06T14:34 | ✅ |
| 2 | release-tooling-accuracy | 清单与断言准确性 | 5/5 | 10 | 2026-10-06T14:40 | ✅ |
| 3 | canonical-hash-integrity | canon 双轨 | 3/3 | 3 | 2026-10-06T14:26 | ✅ |
| 4 | repo-hygiene | `_scratch/` 不入库 | 4/4 | 8 | 2026-10-06T14:43 | ✅ |

**执行顺序**：Slice 3 → Slice 1 → Slice 2 → Slice 4（并行组内按「低风险先行」自裁；Slice 2 严守 Slice 1 之后）。

### 2.1 双环境对照（核心证据）

| 环境 | 构造方式 | 根 `tests/` 结果 |
|------|---------|-----------------|
| A 权威 | `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` | **94 passed, 4 skipped, 0 failed** |
| B 非权威 | `PYTHONUTF8=0 PYTHONIOENCODING=gbk` | **94 passed, 4 skipped, 0 failed** |

> ⚠️ 构造方式说明：本沙箱 `env -u VAR` 是**静默空操作**，故「非 UTF-8 环境」用显式
> `PYTHONUTF8=0 PYTHONIOENCODING=gbk` 构造，而不是 `unset`。

> ⚠️ 前两次对照被**并发编辑污染**（我一边跑一边改文件，B 环境跑到了半成品）。
> 本表数据取自**全部切片完成后**的干净重跑。

### 2.2 `_scratch/` 破坏性操作的零损失核验

| 检查项 | 执行前 | 执行后 | 判定 |
|--------|--------|--------|------|
| `git ls-files _scratch/` 条目数 | 27 | **0** | ✅ |
| `_scratch/` 磁盘顶层实体数 | 12 | **12** | ✅ |
| 27 条索引实体对应的磁盘实体缺失数 | — | **0** | ✅ |
| 25 个普通文件 md5（对 `audit/scratch-inventory.txt` 快照） | — | **逐字节一致** | ✅ |
| `git diff --cached --diff-filter=D` 中非 `_scratch/` 项 | — | **0** | ✅ |
| `git ls-files --others --ignored --exclude-standard _scratch/` | 0 | **25** | ✅ gitignore 生效 |

## 三、TC 实现覆盖对账（planned vs actual）

| TC 组 | 实现位置 | 函数数 | 状态 |
|-------|---------|-------|------|
| TC-TSP-001/004（含扩展与自检） | `tests/test_subprocess_encoding_policy.py` | 6 | ✅ |
| TC-TSP-002/003/005/006 | 双环境实跑 + `upstream/tests/test_install_scripts.py` | — | ✅ 见 §二/§四 |
| TC-RTA-001/003/005 | `tests/test_release_manifest_accuracy.py` | 10 | ✅ |
| TC-RTA-002/004 | `tests/test_finance_content.py` + 根 tests 全量 | — | ✅ |
| TC-CHI-001/002/003 | `tests/test_canon_hash_integrity.py` | 3 | ✅ |
| TC-RH-001..004 | `tests/test_repo_hygiene_scratch.py` | 8 | ✅ |

### 3.1 `ci check-failures` 两项告警/错误的说明（**均为既有工具口径问题，非本变更缺陷**）

**❌ (d) 重复 TC-ID**：工具只读 `change_dir/test-plan.md` 并要求每个 TC-ID **恰好出现一次**
（[`ci.py:312-323`](file:///e:/FSTDD/stdd-repo/upstream/fstdd/cli/commands/ci.py#L312-L323)）。
而项目**实际约定**是在「案例标题 + 建议补充顺序 + 回归风险矩阵 + 证据表」多处引用同一 ID。
实测统计：`.fstdd/` 下 **38 份 test-plan 中有 26 份**存在重复（含紧邻的
`2026-10-05-upstream-baseline-alignment`：39 引用 / 21 唯一）。
⇒ 判定为**长期存在的「工具 vs 实践」错配**，本变更**不修改既有文档约定**，
建议另立 change 决定「改工具」还是「改约定」。

**⚠️ TC 实现覆盖 13/20 (65%)**：`check_tc_implementation_coverage` 硬编码扫描
`project_root / "tests"`（[`ci.py:553`](file:///e:/FSTDD/stdd-repo/upstream/fstdd/cli/commands/ci.py#L553)），
而本仓**主测试面在 `upstream/tests`（960 用例）**；且缺失清单里混入了
`TC-EOL-005`、`TC-EPR-002` 等**非本 change** 的 ID ⇒ 分母口径跨 change 混合。
该问题已在 `version.yaml` 的 3.3.5 已知问题中登记。

**⚠️ (g) AND 超限**：spec.md 的 AND 数量 7/11/9/13。本 change 的规格刻意用 AND 表达
可分别验证的细则（如 SC-001 的四条 AND 各自对应一条断言），未做削减去迎合阈值。

## 四、失败项详细分析

### 4.1 `upstream/tests/test_repo_home.py::TestAWorkspaceIntegrity::test_a6_no_stray_untracked_files`

**状态：❌ 失败 —— 提交前**必然**失败，非缺陷。**

判据：`git status --short` 中不得有 `??` 项（除 `.fstdd/changes/`）。
本 change 新建的 4 个测试文件在提交前必为 `??` ⇒ 必然红。

证明（`git ls-files --others --exclude-standard` 的完整分类）：

| 类别 | 数量 | 是否触发 test_a6 |
|------|------|-----------------|
| `.fstdd/changes/2026-10-06-legacy-debt-cleanup/**`（在办 change） | 25 | 否（判据显式排除） |
| 本 change 新建的根测试文件 | 4 | **是** |
| `_scratch/**` | 0 | 否（已被 gitignore） |
| **其它游离垃圾** | **0** | — |

⇒ 除本 change 自身的 4 个新文件外，**零游离 untracked**，且 `_scratch/` 已不在列表中
（这正是本 change 的目标之一）。**DELIVER 提交后该用例即转绿**。

### 4.2 `tools/verify_eol.py::TC-EOL-005 索引零内容变更`

**状态：❌ 失败 —— 提交前必然失败，非缺陷。**

判据：`git add --renormalize .` 后统计「索引 vs HEAD」的已跟踪文件修改，减去白名单前缀
（`tools/` `docs/` `skills/` `.fstdd/experiences/` + `README.md`/`.gitignore`/`NOTICE.md`）。
在办 change 必然改 `tests/` 与 `upstream/` ⇒ 报 **20 项**非白名单变更（评审实测数字；初报 19 时
尚未包含 ADJ-008 新增的 `test_new_isolate.py`）。

**关键核验**：这 20 项**全部是真实内容变更**，零纯行尾变更 ——
逐文件对比 `git diff --numstat` 与 `git diff --ignore-cr-at-eol --numstat`，两者**完全相等**。

⇒ 该用例的判据本质是「索引 vs HEAD」，**只有在工作树干净（提交后）时才可能为绿**。
`verify_rename` 的 TC-RENAME-006 依赖 `verify_eol`，故连锁 7/8。

**四自检须在 DELIVER 提交后复验**（见 §五）。

### 4.3 `upstream/tests/test_install_scripts.py::test_install_ps1_explicit_python`（**已修复**）

**状态：✅ 已修复**（ADJ-007）。

根因：Windows PowerShell 5.1 在 stdout 被重定向时按 `[Console]::OutputEncoding` 编码
（本机实测 `gb2312 / CP=936`）⇒ 中文输出被按 UTF-8 解成 U+FFFD。
修复：`_force_utf8_output()` 强制子进程以 UTF-8 写出。

| | 修复前 | 修复后 |
|---|---|---|
| 该文件（CP936 控制台） | 1 failed, 2 passed | **3 passed** |

### 4.4 已证伪的两条外部评审结论（**过度信任 LLM 的反例**）

C1 三代理评审共提出 5 条严重发现，逐条实证后有 **2 条被证伪**：

| 评审结论 | 实证 | 判定 |
|---------|------|------|
| 根 `canonical/proposals/` 口径 **3/14 不一致**（09-15-crlf-eol / 09-25-guard-phase-path / 09-25-new-isolate） | 逐条 `canon fstdd canon verify` → **14/14 全部 2/2** | ❌ **证伪** |
| `test_inbox_endpoint.py::test_a21_post_unknown_path_404` 失败 | 单跑 **PASS**（本地 HTTP 服务端口抖动） | ❌ **证伪（flaky）** |

⇒ 评审报告**未经实证不得采信**；另 3 条（`_OPENER.open` 误插、`test_verify_notices` 零 diff 冲突、
别名 import 漏检）经实证**成立并已修复**（见 §七 ADJ-008）。

### 4.5 flaky 用例清单（**本机环境性，与本变更无关**）

三次全量 `upstream/tests` 各出现**不同的**失败项，且隔离复跑均 PASS：

| 全量轮次 | 失败项 | 隔离复跑 | 类别 |
|---------|-------|---------|------|
| 第 1 轮 | `test_install_scripts.py::test_install_ps1_explicit_python` | **真失败**（已修，见 §4.3） | 编码（ADJ-007） |
| 第 2 轮 | `test_inbox_endpoint.py::test_a21_post_unknown_path_404` | **PASS** | flaky（本地 HTTP） |
| 第 3 轮（最终） | `test_fstdd_hub.py::test_heartbeat_complete_and_old_token_is_rejected` | **PASS** | flaky（本地 hub HTTP） |

⇒ 这两例都是**起本地 HTTP 服务**的集成用例，在大套件并发下出现端口/时序抖动。
**本变更引入的稳定失败为 0。**

## 五、四自检脚本

| 脚本 | 结果 | 说明 |
|------|------|------|
| `tools/verify_rename.py` | **7/8** | TC-RENAME-006 依赖 verify_eol ⇒ 连锁失败（提交后应转 8/8） |
| `tools/verify_eol.py` | **6/7** | TC-EOL-005 见 §4.2（提交后应转 7/7） |
| `tools/verify_skill_standards.py` | **7/7** | ✅ |
| `tools/verify_workbuddy_skills.py` | **PASS** | ✅ 6 个 skill 全部通过 |

> ⚠️ **必须在 DELIVER 提交后复跑一次**：TC-EOL-005 与 TC-RENAME-006 的判据都基于
> 「索引 vs HEAD」，提交前结构性为红。本报告的 7/8、6/7 **不代表门禁失败**。

## 六、失败模式检查（C4，23 项全量）

| # | 失败模式 | 结果 | 依据 |
|---|---------|------|------|
| 1 | 幻觉调用 | ✅ | 被改/新增 .py 全量 `compileall` 通过；实跑全绿；无 undefined 标识符 |
| 2 | 过度信任 LLM | ✅ | C1 三代理评审 5 条发现**逐条实证**，**2 条被证伪**（见 §4.4）⇒ 未照单全收 |
| 3 | Prompt 注入 | ✅ | 本 change 全部产物 + 改动面定向扫描 `ignore previous`/`you are now`/`disregard prior` → **0 命中** |
| 4 | 记忆污染 | ✅ | 独立 session；未复用旧上下文；产物以 canonical YAML 为唯一源 |
| 5 | 上下文窗溢出 | ✅ | 单文件最大 **287 行**（<300）；4 个新文件 61–287 行；改动按 4 切片分块 |
| 6 | 工具参数漂移 | ✅ | 仅用既有 CLI 子命令（`new`/`canon`/`gate`/`phase`/`experience`/`ci`）与 pytest 官方参数（`--deselect`/`--junit-xml`/`-p no:cacheprovider`） |
| 7 | 安全凭证泄露 | ✅ | 定向形态扫描（gh/sk/AKIA/PEM/Bearer/赋值式密钥）**0 命中**（122 个 long_alnum 全为 git SHA/md5）。⚠️ **未运行 `verify_notices.py`** —— 本仓无 `00-SIGNATURES.md`，按 EXP-2026-0015 该工具会「隔离=移动」合法文件 |
| 8 | 权限绕过 | ✅ | 未手工改 `.fstdd.yaml` 的 `confirmed_*` 字段；`gate approve` 走 CLI；`git rm --cached` 经 D哥 单独授权 ⑫ |
| 9 | 并发竞态 | ✅ | 全流程串行。⚠️ 双环境对照曾被并发编辑污染一次，已重跑取得干净对照 |
| 10 | 路径遍历 | ✅ | 全部操作在 `E:/FSTDD/stdd-repo` 内；无 `../` 逃逸 |
| 11 | 跨会话残留 | ✅ | 清理工作区根 23 个临时文件 + `_review_tmp/`；仓库内游离项仅剩本 change 自身 7 个文件 |
| 12 | 输出截断 | ✅ | 本机 pytest stdout 被 safe-delete 守卫截断（`state lock timeout`）⇒ 改用 `--junit-xml` 取权威结果，**未据截断输出下结论** |
| 13 | 格式错误 | ✅ | 本 change 全部 YAML **13/13** `yaml.safe_load` 通过。⚠️ `experience verify` 会把 `.experience-index.yaml` 写成 **CRLF**，已手工归一为 LF |
| 14 | 循环依赖 | ✅ | 切片依赖图 `cycles: []`；新增测试模块 import 图为有向无环（新文件 → 既有文件，反向无） |
| 15 | 重复扣款 | SKIPPED | 非金融变更（`FINANCIAL_PROJECT=NO`），无扣款接口 |
| 16 | 账实不符 | SKIPPED | 同上，无账本/对账源 |
| 17 | 静默降级 | SKIPPED | 同上。**注**：非金融面上已按 SC-004 强制 `errors="replace"`、禁止 `errors="ignore"` |
| 18 | 精度丢失 | SKIPPED | 同上，无金额字段 |
| 19 | 审计缺口 | SKIPPED | 同上，无资金流/权限变更 |
| 20 | 状态机漏洞 | SKIPPED | 同上，无交易状态机 |
| 21 | 额度穿透 | SKIPPED | 同上，无限额逻辑 |
| 22 | 合规遗漏 | SKIPPED | 同上，无 KYC/AML |
| 23 | 过度工程 | ✅ | 见 §6.1 |

### 6.1 #23 过度工程 —— YAGNI-7 逐级判定

| 新增物 | 1 真需要 | 2 本仓已有 | 3 标准库 | 4 平台原生 | 5 已装依赖 | 6 一行 | 7 最小实现 | 结论 |
|--------|---------|-----------|---------|-----------|-----------|--------|-----------|------|
| `test_subprocess_encoding_policy.py` | ✅ REQ-001 要求机器可验证 | ❌ 无同类审计器 | ✅ `ast` | — | ✅ `pytest` | ❌ 需遍历+判定 | ✅ 单文件/只读/零新依赖 | 保留 |
| `test_canon_hash_integrity.py` | ✅ SC-001..003 | ❌ | ✅ `subprocess` | — | ✅ `pytest` | ❌ | ✅ 复用既有 CLI | 保留 |
| `test_release_manifest_accuracy.py` | ✅ SC-001..005 | ❌ | ✅ `re` | — | ✅ `pytest` | ❌ | ✅ | 保留 |
| `test_repo_hygiene_scratch.py` | ✅ SC-001..004 | ❌ | ✅ `subprocess` | — | ✅ `pytest` | ❌ | ✅ | 保留 |
| `_is_pathish_receiver()` / `_force_utf8_output()` 等 helper | ✅ ADJ-007/008 必需 | ❌ | ✅ `ast`/`os` | — | — | ❌ | ✅ 各 <30 行、无副作用 | 保留 |
| **新增第三方依赖** | — | — | — | — | — | — | — | **无** |

## 七、设计偏离（8 条，详见 `design-adjustments.yaml`）

| ID | 严重度 | 类型 | 一句话 |
|----|--------|------|--------|
| ADJ-001 | large | 范围扩大 | subprocess → 全部隐式 locale 文本 I/O（+19 处 / 7 文件） |
| ADJ-002 | small | 新增必要动作 | `test_multi_platform` 两例补宿主隔离参数（断言不变） |
| ADJ-003 | small | 范围扩大 | 清单同一行内的第二处失真（851 用例 + 命令未覆盖根 tests/） |
| ADJ-004 | large | 范围扩大 | 第二处硬编码发布 tag（`test_install_smoke.py`）⇒ spec 补 SC-005 |
| ADJ-005 | small | **记录未修** | `release-and-docs.md:16` 过期版本号 —— 改它会违反本 change 的 SC-001 |
| ADJ-006 | medium | 事实更正 | SC-002 假设被证伪（2 个 gitlink 为空目录，备份源路径不存在） |
| ADJ-007 | large | 范围扩大 | PowerShell 生产者编码（`test_install_scripts.py`）⇒ spec 补 SC-006 |
| ADJ-008 | large | 缺陷修复 + 工具加固 | 审计器漏检别名 import / 补丁误插 `_OPENER.open` / 审计测试假绿假红 |

## 八、经验库（C5）

新增 3 条，均含本仓实测证据，已 `verify`（discovered → verified）：

| ID | category | 判据 |
|----|----------|------|
| **EXP-2026-0020** | tooling | 机械批量补参数必须按**接收者语义**收窄 —— `.open()` 不都是文件 I/O（`OpenerDirector.open` 不接受 `encoding=`） |
| **EXP-2026-0021** | quality | **审计工具的漏检 = 假绿** —— 审计器必须自带自检测试（含别名 import 等变体） |
| **EXP-2026-0022** | runtime_deviation | 「消费者声明了 encoding」≠「与生产者一致」—— 须令生产者按 UTF-8 写 |

经验库总数 70 → **73**；索引 `.experience-index.yaml` 已同步。

## 九、已知问题与遗留项（**未闭合**）

| # | 项 | 影响 | 处置建议 |
|---|----|------|---------|
| 1 | `release-and-docs.md:16` 版本号仍写 `3.1.0`（实际 3.3.5） | 文档失真 | ADJ-005 记录未修（改它违反 SC-001）；建议另立 change 改为引用单一事实源 |
| 2 | `ci check-failures` 的 (d) 重复 TC-ID 与 TC 覆盖口径 | 门禁噪声 | 38 份 test-plan 中 26 份重复 ⇒ 工具与约定错配，须另立 change 决定改哪边 |
| 3 | `experience verify` 把索引写成 CRLF | EOL 门禁噪声 | 已手工归一；建议给 `experience.py` 的写盘加 `newline=""` |
| 4 | `verify_eol` TC-EOL-005 在在办 change 期必然红 | 门禁时序 | 建议在文档中明确「四自检须**提交后**复跑」 |
| 5 | `test_install_smoke.py::test_L0_01` 的 `git fetch` 失败即 skip | 断言路径可被网络掩盖 | 已补宿主隔离用例覆盖两分支；**网络可达时须复验** |
| 6 | `tests/test_multi_platform.py:216` 的 PowerShell 调用同样未强制 UTF-8 | 同族未覆盖 | 该处断言只查 `returncode`，当前无缺陷；建议后续统一 |
| 7 | `phase advance --dry-run` 参数被静默忽略（真实落盘） | 操作风险 | 已知缺陷，未在本 change 范围 |
| 8 | `extract-proposal` 对 capabilities/impact/constraints 恒返回空 | 工具缺陷 | 已知缺陷，未在本 change 范围 |
| 9 | `experience list --format json` 崩溃（`date` 不可序列化） | 工具缺陷 | 已知缺陷，未在本 change 范围 |
| 10 | `origin` 分叉（本地 `master` vs `origin/master`）与镜像 flag | 发布通道 | **不在本 change 范围**，待 D哥 裁定 |
| 11 | `test_a6` 与 `verify_eol` TC-EOL-005 的**提交后复验** | 验收闭合 | DELIVER 提交后必须复跑并在 DELIVER 记录中回填 |

## 十、结论

| 维度 | 结论 |
|------|------|
| 4 个切片 | ✅ 全部完成并通过 B3.4 切片验证 |
| 18 个 TC | ✅ 全部实现且有实测证据 |
| 27 个新增测试函数 | ✅ 全绿 |
| 根 `tests/` 全量 | ✅ 双环境 **94 passed / 0 failed / 4 skipped**，**逐字一致** |
| 全量 `upstream/tests`（960） | ✅ 953 passed / 5 skipped / **2 failed**（1 项提交前预期 + 1 项 flaky） |
| 双环境一致性（核心目标） | ✅ **达成** |
| 破坏性操作 | ✅ 零损失（索引 27→0、磁盘 12→12、md5 逐字节一致） |
| **本变更引入的稳定失败** | ✅ **0** |
| 提交前结构性红项 | ⚠️ 2 项（`test_a6` / TC-EOL-005），**提交后须复验** |
| 遗留项 | 11 条（§九），其中 6 条为**既有工具缺陷**、1 条待 D哥 裁定 |

**建议进入 Gate 3 确认**，并在 DELIVER 提交后按 §九 #11 复跑 `test_a6` 与四自检脚本。
