# 测试报告 — change 2026-10-11-share-hardening-audit-fixes

> Phase 3 BUILD 质量验证（V3.0.5：SLICE / BUILD / VERIFY 合一）
> 执行模式：**full_auto（长程）** · 锚定 L3 · 基线 `a4673cc`
> 报告时间：2026-10-12（UTC+8 00:4x）

## 一、TC 覆盖率（planned vs actual）

| 指标 | 值 |
|---|---|
| 计划 TC | **22**（TC-SEG-001..012 + TC-ISR-001..010） |
| 有实现测试的 TC | **22/22（100%）** |
| `ci check-failures` TC 实现覆盖 | **24/24（100%）**（含 2 个既有交叉引用 TC-SOS-001 / TC-EPR-002） |
| 新增测试函数 | **33**（`test_share_hardening.py` 15 + `test_install_script_robustness.py` 15 + `test_share_hardening_tc_traceability.py` 3） |
| 新增测试用例 | **49**（31 + 15 + 3；其中 2 例为 POSIX-only，Windows 跳过） |
| 修改测试文件 | `upstream/tests/test_silent_share.py`（publish 桩 3 处同步 `pre_staged`）、`tests/test_experience_sync_tc_traceability.py`（归档路径回退） |

**两条 suite 级 TC 的覆盖方式**（已在追溯表登记）：
- `TC-SEG-011` —— **实跑** `upstream/tests/test_silent_share.py`（由 `test_seg011_silent_share_suite_is_green` 以子进程执行并断言 rc=0）→ **23 passed**
- `TC-ISR-010` —— 运行全量 `pytest upstream/tests tests`（见 §四）

## 二、每切片验证状态

| Slice | TC 覆盖 | 新增用例 | per-slice 证据 | 状态 |
|---|---|---|---|---|
| 1 脱敏补漏 + 第二层防线同源 | 5/5 | 8 | 新测 8 passed；既有 `test_share_publish_sanitize.py` 16 passed | ✅ |
| 2 scp 注入防护 + token 权限告警 | 3/3 | 19 | 19 用例（2 例 POSIX-only 跳过）；既有 scp/inbox 回归 16 passed | ✅ |
| 3 publish pre_staged + 重命名 + 桩同步 | 4/4 | 4 | 新测 4 passed；`test_silent_share.py` 23 passed（修前 3 红） | ✅ |
| 4 strip_frontmatter + 策略模板化 | 4/4 | 7 | 7 passed；模板渲染与内嵌常量**逐字节等价**（891/748/631 字节全等）；安装链回归 70 passed / 3 skipped | ✅ |
| 5 冒烟超时 + install.sh 参数 + 源根深度 | 4/4 | 6 | 13 passed（含 isr001..008）；utils + 安装链回归 67 passed / 3 skipped | ✅ |
| 6 金融红线 + 不回归 | 2/2 | 2 | TC-ISR-009 / TC-ISR-010 passed；`test_finance_content.py` 17 passed | ✅ |

合计 **46 用例**（+ 追溯性 3 例 = 49）。

## 三、C1 多路并行技术评审（3 代理）

3 个评审代理（代码 / 测试 / 文档一致性）**全部返回**，发现项逐条处置见 **§六**。

## 四、全量回归

- 命令：`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 TMP=E:/FSTDD/_tmp2 <managed-python> -m pytest upstream/tests tests -q -p no:cacheprovider`
- **处置前**（`E:/FSTDD/_probe_backup/full_final.txt`）：**1186 passed / 1 failed / 11 skipped**（11m57s）
- **C1 处置后（最终）**（`E:/FSTDD/_probe_backup/full_final3.txt`）：**1189 passed / 1 failed / 11 skipped**（16m55s）
- **唯一允许的失败**：`upstream/tests/test_repo_home.py::TestAWorkspaceIntegrity::test_a6_no_stray_untracked_files`
  —— 判据为「工作树无 `.fstdd/changes/` 之外的未跟踪文件」；本变更新增的源/测试文件尚未 `git add`，**提交（DELIVER）后即转绿**。与历史 change 同形状，非回归。
- 基线对照：上一 change 收口后为 1142 passed / 1 failed / 9 skipped ⇒ 本 change 净增 **47 passed / +2 skipped（= 49 用例，与新测试收集数完全一致）**；失败项不变（仍仅 `test_a6`）。

### 首次全量回归发现并已处置的 4 类失败（非本 change 逻辑缺陷）

| 失败项 | 根因 | 处置 |
|---|---|---|
| `test_aud_002_table_matches_live_scan` | 本 change 在 `upstream/fstdd/cli/utils.py` 新增 `_find_source_root()`，使该文件 2 处吞异常点行号位移 17 > ±5 容差 | 按既有机制新建 change 级活表 `audit/except-points.yaml`（承接 25 点，指纹未变）→ 复跑 11 passed |
| `test_grd_001_check_passes_on_current_repo` | 同上（哨兵白名单行号失效） | 同上 |
| `tests/test_experience_sync_tc_traceability.py`（3 例） | **上一 change 引入**：硬编码 `.fstdd/changes/<change>` 路径；该 change 已 DELIVER 归档 ⇒ FileNotFoundError | 改为 `changes/` → `archive/` 回退 → 复跑 3 passed |
| `test_a21_post_unknown_path_404` | **flaky**：全量并发下 HTTP 端口竞争 | 单独复跑 `test_inbox_endpoint.py` → **64 passed**；隔离复跑亦通过 |

## 五、C4 失败模式检查（23 类逐项）

| # | 失败模式 | 结果 | 检查动作 / 证据 |
|---|---|---|---|
| 1 | 幻觉调用 | ✅ | ruff 无 F821；新增符号均有定义点（`_validate_remote_path` / `_check_token_file_permissions` / `_render_template` / `_find_source_root` / `_smoke_timeout`） |
| 2 | 过度信任 LLM | ✅ | 每条结论均有实测证据：importlib 实测、`pytest` 输出、`ruff` 实跑、模板字节比对；C1 评审的 medium 发现经**独立复现**后才修（见 §六） |
| 3 | Prompt 注入 | ✅ | 本 change 不含外部输入拼接进 prompt；`SKILL.md` 增补为固定文本 |
| 4 | 记忆污染 | ✅ | 无跨 session 状态注入；新测试全部 hermetic（tmp_path + monkeypatch） |
| 5 | 上下文窗溢出 | ✅ | 单次 edit 均 < 300 行 |
| 6 | 工具参数漂移 | ✅ | 仅用既有 CLI 子命令与既有参数 |
| 7 | 安全凭证泄露 | ✅ | `verify_notices` 扫描；测试夹具凭证**由拼接构造**（`"ghp_" + "A"*36`、AWS 值分两段拼接），不落连续凭证形态；`test_no_plaintext_credentials.py` 保持绿 |
| 8 | 权限绕过 | ✅ | 未手改 `.fstdd.yaml` 的 gate 确认字段；Gate 1/2 均走 `fstdd gate approve` |
| 9 | 并发竞态 | ✅ | 6 切片**串行**执行；无并发写同一文件 |
| 10 | 路径遍历 | ✅ | `_validate_remote_path()` 拒 `..` 段**与**前导 `-`（TC-SEG-006 覆盖）；Guard `_is_inside_project` 未改 |
| 11 | 跨会话残留 | ⚠️ | 仓库外临时目录 `E:/FSTDD/_tmp2`（pytest basetemp）与 `_probe_backup`（证据留档）**保留**；二者均在仓库外、不影响门禁（`test_a6` 只扫仓库内）；DELIVER 后清理 |
| 12 | 输出截断 | ✅ | 未改 Guard stdin 处理 |
| 13 | 格式错误 | ✅ | 新增 YAML（`pending-adjustments.yaml` / `audit/except-points.yaml` / `.j2` 模板）均 `yaml.safe_load` 校验通过 |
| 14 | 循环依赖 | ✅ | 依赖图 `cycles=[]`；未引入新环 |
| 15–22 | 金融 8 类（重复扣款 / 账实不符 / 静默降级 / 精度丢失 / 审计缺口 / 状态机漏洞 / 额度穿透 / 合规遗漏） | ⏭ SKIPPED | 本 change `task_type=code`（工具链加固），非金融系统；无资金流/风控/对账路径 |
| 23 | 过度工程 | ✅ | YAGNI-7 逐项：`_validate_remote_path`(L1 真需要·注入面) / `_check_token_file_permissions`(L1·EXP C6 教训) / `_render_template`(L2 本仓已有 Jinja2 依赖) / 3 个 `.j2`(L2 同源) / `_find_source_root`(L7 最小实现) / `_smoke_timeout`(L7) / 追溯性测试(L2 复用上一 change 同形模式) / 审计活表(L2 本仓既有机制)。**无新依赖、无新抽象层** |

## 六、C1 评审发现与处置（3 代理）

### 6.1 代码评审（代理 1）

| 严重度 | 发现 | 处置 |
|---|---|---|
| **medium** | `_validate_remote_path` 白名单含 `-` 但**未拒前导 `-`** ⇒ `FSTDD_SSH_ALIAS=-F/tmp/evil` 被 ssh/scp 当作**选项**（`-F` 加载攻击者配置 ⇒ `ProxyCommand` 本地命令执行） | ✅ **已修**：新增 `v.startswith("-")` 拒绝 + 说明注释；TC-SEG-006 增 3 个样例（`-F/tmp/evil`、`-oProxyCommand=id`、`-`），参数化 8→11 |
| low | 无写权限降级 PR 成功后 `reason` 未清空 ⇒ 审计写「success + 403 原因」 | ✅ 已修：降级成功时 `reason = ""` |
| low | `FSTDD_SMOKE_TIMEOUT` 在 import 期 `int()`，env 非数字即崩 | ✅ 已修：`_smoke_timeout()` 非法值回落 30 |
| low | Jinja2 未定义变量默认渲染为空串 ⇒ 变量名写错会静默产出空策略段 | ✅ 已修：`StrictUndefined`（写错即抛错 ⇒ 回落内嵌常量） |
| low | `OUTBOUND_RESIDUAL_RE` 注释称新增形态「一律」带负向前视，实际仅 URL 分支 | ✅ 已修注释：说明 AWS/SSH 两条判据天然不命中占位符 |
| low | `pre_staged` 注释未说明 inbox / PR 分支仍各自 stage | ✅ 已修注释（说明它们是独立出站入口，脱敏不可绕过，EXP-2026-0017） |
| — | 命令注入 / 路径遍历 / 正则灾难性回溯 / 凭证明文：无 | — |
| — | `publish(pre_staged=True)` 三分支**确实都跳过** `stage_sanitized`（逐分支核对） | 确认符合 design 决策 4 |
| — | 死代码：无（`SCP_LIKE_RE` 重命名干净、新增符号全部被引用、模板尾字节与回落常量一致） | — |

**结论**：需修复 1 项 medium（已修）+ 5 项 low（已修 4 / 修注释 2）→ **可放行**。

### 6.2 测试评审（代理 2）

| 严重度 | 发现 | 处置 |
|---|---|---|
| 中 | `test_seg011` 只断言源码文本（`"pre_staged" in stub`），未真正跑套件，属 HOW 断言 | ✅ **已修**：改为**子进程实跑** `upstream/tests/test_silent_share.py` 并断言 rc=0（另保留生产调用点 `pre_staged=True` 断言） |
| 低 | `test_seg004` 的 `assert "(?i)" not in pattern` 是实现细节 | 保留为回归护栏（主断言仍是 import 成功 + 三形态命中 + 占位符不误判） |
| 低 | `test_isr008` 的 `assert "3" in msg` 弱，数字可能巧合命中 | ✅ 已修：改断言 `"within 3 levels"` 与 `"possible symlink loop"` |
| 低 | `test_isr003`/`test_isr009` 依赖字面措辞，措辞微调即红 | 接受（内容类 TC 的本质；措辞本身是 spec 的可判定判据） |
| 低 | 三文件各自复制 `_load_*` 样板；`timeout==30` / `0o644` / 深度 `3` 为散落魔法值 | 接受：三文件各自 hermetic 优先于 DRY；抽 `conftest.py` 会引入跨文件共享状态（与「测试隔离」目标冲突） |

**结论**：测试质量 **好**（覆盖完整 22/22、隔离到位、夹具 hermetic、断言基本验证行为）；**不阻塞 Gate 3**。

### 6.3 文档一致性评审（代理 3）

| 严重度 | 发现 | 处置 |
|---|---|---|
| 高 | `agent_spec` 的 CP-2/3/4/5/7/8/9/11 引用了 **7 个不存在的测试文件** ⇒ CP 命令不可运行 | ✅ **已修**：重写 agent_spec —— `action` 全部改为真实文件 + `-k <TC 前缀>`；新增 `meta.test_files`；新增 CP-13（追溯性）；CP 总数 14→15 |
| 高 | C12（`tools/_skill_install_env.py` 补 `# noqa: E501`）未落地 | ✅ **登记 ADJ-006**：实测加该 noqa 会触发 `RUF100 Unused noqa directive (non-enabled: E501)`（本仓未启用 E501 且该行不超长）⇒ 字面判据与目的错配；目的（说明为何拆开拼接）已由既有块注释达成 |
| 高 | C7「删除重复的 `REPO_ROOT` 赋值」未做（`:20` 与 `:106` 双重赋值） | ✅ **已修**：删除 `install_workbuddy_skills.py` 中重复的 `REPO_ROOT = TOOLS_DIR.parent`，保留文件顶部定义并加注说明 |
| 中 | `test-plan.md` 记 `test_share_publish_sanitize.py` 15 用例，实际 16 | ✅ 已修（16，13 函数） |
| 中 | `test-report.md` 计数 27/14 与实际不符；slice3 记 3、slice6 记 1 | ✅ 已修：15 函数/31 用例、15 函数/15 用例；slice 计数改为 8/19/4/7/6/2 |
| 中 | §二「2 个测试」与 §一「3 个新测试文件」自相矛盾 | ✅ 已修 |
| 中 | `code-structure-delta.md` 只列 1 行，与实际 7 改 + 6 新增不符 | ✅ **已修**：人工补全变更文件/产出物/新增符号清单；并登记 **ADJ-007**（CLI 工具判据过窄，历史 change 同形） |
| 中 | `.fstdd.yaml` 的 `traceability` 三项全 0 | ✅ 已修：`spec_scenarios: 22` / `tc_cases: 22` / `test_functions: 33` |
| 中 | §六 C1 处置「待回填」、§十二 C1 标 🔄 | ✅ 本节即回填 |
| 低 | `.fstdd.yaml` traceability（同上） | 同上 |

**结论**：核心加固（C1–C6、C8–C11）与 7 条 ADJ 登记**真实落地且与文档一致**；3 项「高」已全部闭合（2 修 + 1 登记偏离）。

## 七、C3 Diff 审查

- 8 个修改文件 + 6 个新增文件（3 模板 + 3 测试）+ change 目录产出
- 调试残留扫描（白名单外 `print` / TODO / FIXME / breakpoint / pdb）：**零命中**
- 死代码：`SCP_LIKE_RE` 已彻底重命名（`hasattr` 断言保证无残留）；无注释掉的旧逻辑
- ruff：改动文件的规则画像与 HEAD 基线**逐条一致** ⇒ **零新增问题类型**

## 八、C2 全量质量检查

| 项 | 结果 |
|---|---|
| 全量 pytest | 见 §四 |
| `ci check-failures` | ✅ 通过 6 / ⚠ 警告 0 / ❌ 错误 0；TC 实现覆盖 **24/24 (100%)** |
| lint（ruff） | 改动文件零新增问题类型（见 §七）；**因 ADJ-006 未引入 RUF100** |
| coverage | ⏭ 未启用（项目 `quality.yaml` 未配置 `--cov` 门禁；沿用历史 change 口径） |

## 九、C5 经验库

新增 3 条（`source_change=2026-10-11-share-hardening-audit-fixes`）：

| ID | 分类 | 严重度 | 模式 |
|---|---|---|---|
| EXP-2026-0031 | contract_gap | high | 模块级正则常量把内联 `(?i)` 写在多段拼接中间 ⇒ import 即崩 |
| EXP-2026-0032 | contract_gap | high | 字符白名单看似覆盖，但 `..` 由 `.`+`/` 组合而成 ⇒ 路径上跳通过 |
| EXP-2026-0033 | pipeline_break | medium | 第二层防线把脱敏后的占位符误判为残余 ⇒ 正常条目被整条剔除 |

> 注：C1 发现的「前导 `-` 被当选项」已并入 EXP-2026-0032 的 `fix_template`（同一类「字符白名单不等于语义白名单」）。

## 十、C6 设计调整

**7 条**（0 Major / 7 Minor），详见 `design-adjustments.yaml`；明细见 `pending-adjustments.yaml`。

## 十一、已知问题 / 未完成项

| 项 | 原因 | 影响 | 补完计划 |
|---|---|---|---|
| `test_a6_no_stray_untracked_files` 红 | 新文件未 `git add` | 无（结构性红） | DELIVER 提交后转绿 |
| `test_a21` 全量下偶发红 | HTTP 端口竞争（flaky） | 无（隔离复跑 64 passed） | 记录为已知 flaky，不属本 change |
| `install.sh` 的 `[WARN] 未知参数` 后继续走完整安装流程 | SC-019 要求「不中断」 | 低（未知参数被忽略而非静默） | 按 spec 保留 |
| `fstdd structure delta` 判据过窄 | 框架工具缺陷（历史 change 同形） | 低（已人工补全） | 登记 ADJ-007，建议另立 change 改用 `git diff --name-only` / AST |
| 「按 change 名硬编码路径」的测试在归档后失效 | 上一 change 遗留；框架 `finder` 已在上游命令侧统一、测试侧未覆盖 | 中（会随每次归档复发） | 登记于 ADJ-005 `residual_state`，建议另立 change 统一测试侧解析 |

## 十二、Gate 3 前置条件核对

| Step | 名称 | 完成 |
|---|---|:---:|
| C1 | 多路并行技术评审（3 代理） | ✅ 全部返回，发现项逐条处置（§六） |
| C2 | 全量质量检查（pytest + lint + ci） | ✅ |
| C3 | Diff 审查 | ✅ |
| C4 | 失败模式检查（23 类） | ✅（17 ✅ / 1 ⚠ / 5 ⏭ 非金融） |
| C5 | 经验库自动记录 | ✅（EXP-2026-0031/0032/0033） |
| C6 | 汇总设计调整 | ✅（7 Minor） |
| C7 | 生成测试报告 | ✅（本文件） |
