# 2026-10-05-upstream-baseline-alignment 测试报告

> 测试日期：2026-10-05
> 测试环境：Windows / Python 3.13.14（workbuddy default env）/ PyYAML 6.0.3 / pytest 9.1.1 / Jinja2 3.1.6
> baseline（observed_base_git_sha）：`1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2`
> 变更属性：mode=standard ｜ task_type=documentation ｜ FINANCIAL_PROJECT=NO

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 规划 TC 数（test-plan 去重唯一 ID） | 21 |
| 其中本变更新增 TC（`tests/` 内实现） | 14（TC-VNOM-001..008 + TC-UBL-001..006） |
| 其中回归闸门 / 既有引用 TC | 7（TC-VNOM-009/010、TC-REG-001/002、TC-EOL-005、TC-PSI-002、TC-EPR-002） |
| 新增测试函数 | **21**（12 + 3 + 6），全绿 |
| 定向测试（3 个新测试文件） | **21 passed, 0 failed** |
| 全量回归（`pytest upstream/tests`） | **906 passed, 54 skipped, 0 failed**（与改动前基线逐字一致） |
| 四自检 | rename **8/8**、eol **7/7**、skill_standards **7/7**、workbuddy_skills **PASS** |
| 本变更引入的失败项 | **0** |

## 二、切片验证状态

| # | 切片 | tc_coverage | new_tests | verified_at | 结果 |
|---|------|-------------|-----------|-------------|------|
| 1 | 活体声明面版本轴显式化 | 5/5 | 12 | 2026-10-05T11:53:05+08:00 | ✅ |
| 2 | 适配层版本字段派生去硬编码 | 3/3 | 3 | 2026-10-05T11:57:00+08:00 | ✅ |
| 3 | 上游基线快照单一事实源 | 6/6 | 6 | 2026-10-05T12:10:00+08:00 | ✅ |

三切片均完成 Step B3.4 切片验证（TC 覆盖 + 产出物核对 + 测试通过）。设计偏离见 `pending-adjustments.yaml`。

## 三、TC 实现覆盖对账（planned vs actual）

| 范围 | 定义 | 实现位置 | 状态 |
|------|------|----------|------|
| TC-VNOM-001..005 | 活体声明面版本轴（NOTICE/README/fstdd-fin/NOTES） | `tests/test_version_nomenclature.py` | ✅ 12 函数 |
| TC-VNOM-006/007/008 | 适配层版本派生（install/verify 端到端） | `tests/test_install_version_derivation.py` | ✅ 3 函数 |
| TC-UBL-001..006 | 上游基线快照静态一致性 | `tests/test_upstream_baseline.py` | ✅ 6 函数 |
| TC-VNOM-009/010 | 既有门禁回归（rename/eol/standards/verify） | `tools/verify_*.py`（不在 `tests/` 扫描面） | ✅ 实跑全绿 |
| TC-REG-001/002 | 四自检 + 全量回归闸门 | CLI 实跑（非测试函数） | ✅ 见第四/五节 |
| TC-EOL-005 | 工作树干净度（既有） | `tools/verify_eol.py:221` | ✅ 7/7 |
| TC-PSI-002 | 上游既有用例（佐证） | `upstream/tests/commands/test_install.py` | ✅ 906 全绿内 |
| TC-EPR-002 | 证据溯源规则（spec 级，非用例） | 见 test-plan §六 | ✅ 已遵循 |

### 3.1 `ci check-failures` TC 覆盖 14/21 (67%) 的说明（扫描面假阴性）

`fstdd ci check-failures` 报 `TC 实现覆盖: 14/21 (67%)`（WARN，非 FAIL）。根因：
[`ci.py:536-573 check_tc_implementation_coverage`](file:///e:/FSTDD/stdd-repo/upstream/fstdd/cli/commands/ci.py#L536-L573)
只在 **仓库根 `tests/**/test_*.py`** 内搜 TC-ID，而缺失的 7 个 ID 中：
- `TC-VNOM-009/010` 由 `tools/verify_*.py` 实现（不在扫描面）；
- `TC-REG-001/002` 由 CLI 实跑闸门承载（无测试函数）；
- `TC-EOL-005` 定义在 `tools/verify_eol.py:221`；
- `TC-PSI-002` 属 `upstream/tests/`；`TC-EPR-002` 为 spec 级规则引用。

即：**7 个都不该出现在 `tests/*.py`**，指标受扫描面所限而低估。判为**已知量测假阴性**（同族 EXP-2026-0016），
**不改 test-plan 结构、不往测试文件塞伪 TC-ID 注释去迎合指标**。真实覆盖：14/14 新增 TC 全部有测试函数。

### 3.2 `(d) 重复 TC-ID` 假阳性的反证（grep 证据）

`ci check-failures` 报 `✗ (d) 重复 TC-ID: ['TC-UBL-001','TC-VNOM-001','TC-EOL-005','TC-REG-001',...12 项]`。
根因：[`ci.py:311-324 check_tcid_unique`](file:///e:/FSTDD/stdd-repo/upstream/fstdd/cli/commands/ci.py#L311-L324)
仅读 `test-plan.md` **单文件**、以 `re.findall` 计字面出现次数，>1 即判重复。

反证（grep）：`test-plan.md` 中定义行 `| **ID** | TC-XXX-NNN |` 恰 **18 行、每 ID 各 1 次**；
每个被报「重复」的 ID **定义唯一**，其余出现均为追溯矩阵（§三）/优先级（§五）/证据表（§六）的交叉引用。
`TC-EOL-005` 在本 change 的 test-plan 中只作引用（无定义行），其唯一定义在 `tools/verify_eol.py:221`。
结论：判为**已知假阳性**（EXP-2026-0016 复现，occurrences 1→2），不修改 test-plan。

## 四、四自检门禁（发布门禁证据）

| 命令 | 结果 | 退出码 |
|------|------|--------|
| `python tools/verify_rename.py` | `结果：8/8 通过`（含 TC-RENAME-002 无残留独立 `stdd`） | 0 |
| `python tools/verify_eol.py` | `结果：7/7 通过`（TC-EOL-005 已排除有意改动 6 文件） | 0 |
| `python tools/verify_skill_standards.py` | `结果：7/7 通过` | 0 |
| `python tools/verify_workbuddy_skills.py` | `[PASS] 6 个 skill 全部通过`（1 项 WARN：影子副本，非阻断） | 0 |

> 收尾时 `git ls-files --eol` 检出 4 个 FSTDD CLI 生成的 change 产物（`caveman_summary.txt`、`proposal.md`、`specs/*/spec.md`）为「索引 LF + 工作区 CRLF」混合态 →
> 执行 `tools/verify_eol.py --fix` 归一 4 个后复跑 `verify_eol` = **7/7**，`verify_rename` 复合项 TC-RENAME-006 随之回 **8/8**（属工具既有归一能力，非设计偏离）。

## 五、全量回归

| 命令 | 结果 |
|------|------|
| `python -m pytest upstream/tests -q` | **906 passed, 54 skipped, 0 failed**（407s） |
| `python -m pytest tests/ -q` | 66 passed, 3 skipped, **2 failed（预存，非本变更引入）** |

### 5.1 `tests/` 2 项失败的归属核验（判为预存）

| 现象（最小可复现证据） | 根因 | 归属 |
|------------------------|------|------|
| `test_finance_content.py::test_L1_11_version_yaml_fstdd_version`：`fstdd_version = 3.3.4, expected 3.3.0` | 用例硬编码期望 `3.3.0`，未随 R 轴漂移更新 | **预存** |
| `test_install_smoke.py::test_L0_01_git_pull_to_tag`：`HEAD tag = fstdd-v3.3.4, expected fstdd-v3.1.1` | 用例硬编码期望 tag `fstdd-v3.1.1` | **预存** |

核验手段：`git diff HEAD --name-only` **不含** `tests/test_finance_content.py` / `tests/test_install_smoke.py`；
其输入 `.fstdd/version.yaml`、git tag 均未被本 change 触碰 → 判为**预存失败，非本变更引入**，
超出本 change 范围（文档型变更），**本轮不修**，建议另立 change 刷新这两处硬编码期望。

### 5.2 一次瞬时干扰项的核验（外部并发产物，非本变更引入）

收尾复跑时曾出现 `upstream/tests/test_repo_home.py::TestAWorkspaceIntegrity::test_a6_no_stray_untracked_files` **FAIL**：
`AssertionError: 仓库有未跟踪的遗留项: ['?? .tmp_norm_eol.py']`（该次 905 passed / 1 failed）。核验：

| 维度 | 证据 |
|------|------|
| 判据 | `test_a6` = `git status --short` 中除 `.fstdd/changes/` 外不得含 `??` 行（[test_repo_home.py:132-142](file:///e:/FSTDD/stdd-repo/upstream/tests/test_repo_home.py#L132-L142)） |
| 时序 | 该文件在运行窗口内**瞬时创建又删除**：运行前与运行后两次 `git status --porcelain` 均无此项 |
| 来源 | 全仓 grep `norm_eol\|tmp_norm_eol` **零命中**（`upstream/tests`、`tools/`、`tests/` 均无该字面量命名） |

⇒ 判为**外部并发进程**（另一档/协作 agent 的 EOL 归一化临时脚本）在仓库根投递的瞬时产物，**与本次变更无关**。
复跑核验：单文件 `pytest upstream/tests/test_repo_home.py -q` → `16 passed, 3 skipped`；全量复跑 → **906 passed, 54 skipped, 0 failed**（451s，零失败）。

## 六、C4 失败模式检查（23 类，逐项）

| # | 失败模式 | 结果 | 证据 / 处置 |
|---|----------|------|-------------|
| 1 | 幻觉调用 | ✅ | `install_workbuddy_skills.py` 新增 `_vendored_kernel_version()`，仅用已 import 的 `re`（:15）；无未 import / fake 标识符；实跑安装脚本退出码 0 |
| 2 | 过度信任 LLM | ✅ | 每条断言以实跑退出码/输出为准；CI 两处告警均经源码定位二次验证后判为假阳性，未照单全收 |
| 3 | Prompt 注入 | ✅ | 文档型变更，无 system prompt 承载面；无 `ignore previous` 类注入痕迹 |
| 4 | 记忆污染 | ✅ | 无跨 Session memory 写入；观测值一次采集、单点固化 |
| 5 | 上下文窗溢出 | ✅ | 单文件 edit 均 < 300 行；新增文档 79 行 |
| 6 | 工具参数漂移 | ✅ | 所有 CLI/脚本调用参数与官方 usage 一致（如 `verify_notices.py <dir>`），无自造参数 |
| 7 | 安全凭证泄露 | ✅ | 定向凭证明文扫描（`ghp_`/`github_pat_`/`PRIVATE KEY`/`sk-`）全仓仅命中测试自带 denylist 字面量；快照文档经 TC-UBL-002 forbidden 扫描通过。**附带发现**：为覆盖本项运行 `verify_notices.py .` 触发其破坏性隔离副作用（移走 3 个跟踪文件），已还原并记入 EXP-2026-0015（occurrences 1→2） |
| 8 | 权限绕过 | ✅ | 未手改 `.fstdd.yaml` 确认字段；Gate 1/2 记 `dialog` + 原文 |
| 9 | 并发竞态 | ✅ | 单 change 串行推进；未并发推多 change |
| 10 | 路径遍历 | ✅ | 文件操作均在 `project_root` 内；无 `../` 逃逸 |
| 11 | 跨会话残留 | ✅ | 未新增 `.tmp`/临时目录；误隔离文件已全部还原、`tools/_quarantine` 已删除 |
| 12 | 输出截断 | ✅ | 无大 payload hook 输入面（N/A） |
| 13 | 格式错误 | ✅ | 3 个新 canonical YAML 经 `yaml.safe_load` 通过（TC-UBL-003 实读）；生成 frontmatter 正则匹配通过 |
| 14 | 循环依赖 | ✅ | 无新增模块 / import 图无环 |
| 15–22 | 重复扣款 / 账实不符 / 静默降级 / 精度丢失 / 审计缺口 / 状态机漏洞 / 额度穿透 / 合规遗漏 | SKIPPED | `FINANCIAL_PROJECT = NO`（Step 0.5 判定），本变更不涉及支付/银行/交易/风控等金融数据面 |
| 23 | 过度工程 | ✅ | YAGNI-7 梯子逐项：① 去硬编码为决策 3 真实所需；② 本仓 `_skill_install_env.repo_stdd_version()` 只读 R 轴，无读 K 轴者；③ 标准库 `re` 足够；④–⑥ 无需新依赖；⑦ 落为单文件内 7 行最小函数（docstring 已说明「刻意不外提，YAGNI」）。新增 `docs/UPSTREAM_BASELINE.md` 为单一事实源，非冗余 |

## 七、设计调整说明

本变更 **3 项小偏离**（ADJ-001 / ADJ-002 / ADJ-003，均门禁相容性，见 `design-adjustments.md`），**无重大偏离**。

## 八、已知问题 + 未完成项

| 项 | 名称 | 原因 | 影响 | 补完计划 |
|----|------|------|------|----------|
| 1 | `tests/` 2 项预存失败 | 硬编码期望 `3.3.0` / `fstdd-v3.1.1` 未随 R 轴更新 | 低（不在本 change 范围，且不阻断 `upstream/tests` 闸门） | 另立 change 刷新这两处硬编码期望 |
| 2 | `ci check-failures` (d) 重复 TC-ID 假阳性 | CLI 纯文本扫描（EXP-2026-0016） | 低（已反证） | 上游 CLI 修复：改为结构化映射判唯一性（本仓不改上游判据） |
| 3 | `ci check-failures` TC 覆盖 14/21 (67%) 假阴性 | 扫描面仅 `tests/*.py` | 低（真实新增 TC 覆盖 14/14） | 同上，或把 `tools/verify_*.py` 纳入扫描面 |
| 4 | `ruff` / `mypy` / `pytest-cov` 未安装 | 本机 env 无此三者 | 低 | 记为 **SKIPPED**（lint/类型/覆盖率三项未执行，非通过）；待 env 安装后补跑 |
| 5 | `verify_notices.py` 破坏性副作用 | 对无清单目录默认「隔离=移动」 | 中（有丢失未提交工作风险） | 已记 EXP-2026-0015；建议上游改为默认 dry-run，破坏动作须显式开关 |
| 6 | 一次瞬时 `?? .tmp_norm_eol.py`（外部并发产物） | 另一档/协作 agent 的 EOL 归一化临时脚本投递至仓库根 | 极低（瞬时、已自清、非本变更引入） | 已核验（见 §5.2），复跑零失败；建议各档临时脚本改置于仓库外或 `_scratch/` |

## 九、结论

**可进入 Gate 3。** 本变更引入的失败项 = 0；全量 `upstream/tests` **906 passed / 54 skipped / 0 failed**（与基线逐字一致）；
四自检全绿（8/8、7/7、7/7、PASS）；21 个新增测试函数全通过。
风险等级：**低**。两处 CI 告警均经源码定位判为**已知假阳性/假阴性**并附 grep 证据，未回避、未伪造。
剩余 6 项已知问题均为低风险且已给出补完计划（其中 `tests/` 2 项预存失败与本变更无关，属范围外；第 6 项为外部并发瞬时产物，复跑零失败）。

> 待用户确认 Gate 3 后，方可进入 Phase 4 DELIVER（归档 change、合并 specs、Git commit/tag）。