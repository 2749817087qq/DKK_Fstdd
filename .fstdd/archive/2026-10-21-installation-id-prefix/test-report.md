# 测试报告 — 2026-10-21-installation-id-prefix

**change**：`2026-10-21-installation-id-prefix`
**模式**：thorough ｜ **task_type**：code ｜ **复杂度**：8 ｜ **锚定**：L2
**基线 commit**：`a48942065c907045da8444a89e1ef24c14d480af`
**生成时间**：2026-10-22T12:45:00+08:00

---

## 1. 结论摘要

| 指标 | 值 |
|---|---|
| 全量回归（框架侧 `upstream/tests`） | **1058 例，1053 passed / 5 skipped / 0 failed**（1067s） |
| 全量回归（仓库侧 `tests/`） | **348 例，342 passed / 6 skipped / 0 failed**（268s） |
| `fstdd ci check-failures` | **0 错误**（8/10 项自动检查；TC 覆盖 14/14） |
| 新增测试 | 44 例（框架侧 40 + 仓库侧 4 追溯性） |
| 修复的假测试 | 3 例（`test_installation_id` 内 2 例重写 + 既有 `test_init.py::test_init_dry_run` 零断言重写） |
| TC 覆盖 | 14 / 14 = 100%（IID 7 + EID 7） |
| 判别力 | 27 / 40 对 baseline 判红；13 例为回归护栏/边界（已在 §3 标注） |
| 新增吞异常点 | **0**（审计活表 25 点零漂移） |
| 阻塞级评审发现 | 3（全部已修，见 `design-adjustments.yaml` ADJ-001~003） |
| 已知缺口 | 4（见 §6） |

---

## 2. 测试执行

### 2.1 全量回归

```
# 框架侧
cd E:/FSTDD/stdd-repo/upstream && python -m pytest tests/ -q
→ 1053 passed, 5 skipped in 1067.04s

# 仓库侧（release validation / 卫生 / 追溯性）
cd E:/FSTDD/stdd-repo && python -m pytest tests/ -q
→ 342 passed, 6 skipped in 267.77s
```

对比基线（本 change 开始时）：框架侧 `1032 例 / 2 failed`（两个失败由本 change 新增的
`except Exception:` 触发审计门禁，已通过收窄异常类型 + 刷新审计活表消除）。
当前两侧均 `0 failed`。

### 2.1b CI 失败模式检查（`fstdd ci check-failures`）

```
✅ 通过 6 项：(a) 必需文件 / (d) TC-ID 唯一(14) / (f) THEN 含 SHALL /
             (k) 契约一致(2 capabilities) / TC 实现覆盖 14/14 / (l) non-critical
⚠ 警告 2 项：(g) AND 数量 13/14（见下）/ (b) 范围蔓延 24 文件（启发式假阳性，见下）
⏭ 跳过 2 项：(j) 无 coverage.json / 无切片完成记录
❌ 错误 0 项
```

**关于 (g) AND 超限**：判据是「单个 spec.md 内 `**AND**` 出现 >5 次即告警」。
本 change 的 spec 把评审发现逐条落成可测断言（如「写入后既有字段保持不变」
「不合法时告警而非 exit 1」），AND 多是有意的 —— 合并会丢失断言粒度。
接受该告警，不做削减。

**关于 (b) 范围蔓延**：判据只认 `.fstdd/`、`tests/`、`docs/`、`.github/`
以及 `specs/<capability>/`、`commands/<capability>` 路径；本 change 是**框架源码改动**
（`upstream/fstdd/cli/...`、`tools/...`），结构性不适用该启发式。
与「TC 覆盖假红」同源（`ci.py` 的检查假设了「项目级 change」而非「框架自身 change」）。
已由仓库级测试 `tests/test_installation_id_traceability.py` 固化这一已知缺陷。

**关于 (j) 跳过**：本仓从未有 `coverage.json`，仓库级覆盖率门禁处于未启用状态
（非本 change 引入）。本 change 的覆盖率证据见 §2.3。

### 2.2 定向测试

| 命令 | 结果 |
|---|---|
| `pytest tests/commands/test_installation_id.py` | 40 passed |
| `pytest tests/commands/test_init.py` | 全部 passed（含重写的 dry-run 用例） |
| `pytest tests/test_except_audit.py tests/test_guard_silent_except.py` | 11 passed |
| `pytest tests/commands/test_experience_glob_consistency.py` | 11 passed（扫描范围已扩到 `tools/` + `.fstdd/hooks/`） |
| `pytest tests/test_repo_home.py` | 通过（无遗留 untracked 垃圾） |

### 2.3 覆盖率（仅变更模块）

| 模块 | Stmts | Miss | Cover |
|---|---|---|---|
| `fstdd/cli/commands/init.py` | 231 | 25 | **89%** |
| `fstdd/cli/utils.py` | 164 | 41 | **75%** |
| `fstdd/cli/commands/upgrade.py` | 374 | 226 | 40% |
| 合计 | 769 | 292 | 62% |

> `upgrade.py` 40% 是**存量**拖累（未覆盖区间 25-28 / 115-611 全是既有的
> registry / lock / check-all 分支，本 change 只碰了 `_read/_write_version_yaml`）。
> 本 change 新增/修改的函数均被 TC-IID-001~007 与 TC-EID-001~007 直接覆盖。
> `init.py` 未覆盖的 173-176 / 325-329 等为既有分支（非本次新增）。
> 本仓 `quality.yaml` 的 `coverage_target: 80` 面向 `app/` 目录，本仓无该目录。

### 2.4 lint

`ruff check`（默认规则集，仓库无 `[tool.ruff]` 配置）：

| 文件 | baseline | 现在 | 说明 |
|---|---|---|---|
| `init.py` | 16 | 16 | 无新增（既有 I001/F541/F401 存量） |
| `experience.py` | 8 | 10 | +2 均为存量 `I001` 行号位移 |
| `cli/__init__.py` | 3 | 3 | 无变化 |
| `test_init.py` | 4 | 4 | 无变化 |
| `test_installation_id.py` | — | 0 | 新文件干净 |

> 新增代码未引入任何 lint 违规；未用 `--fix` 批量改动（避免把存量噪音混进本 change 的 diff）。

---

## 3. TC 覆盖明细

| TC | 测试函数 | 结果 | 判别力（baseline 是否判红） |
|---|---|---|---|
| TC-IID-001 | `test_init_generates_installation_id` / `test_init_keeps_existing_version_fields` | ✅ | 红 |
| TC-IID-002 | `test_init_prefix_override` / `test_invalid_prefix_falls_back_to_project_name` / `test_cli_parser_exposes_prefix_flag` | ✅ | 红 |
| TC-IID-003 | `test_get_prefix_exact_expectations`（6 参数）/ `test_chinese_project_name_falls_back_to_fstdd` / `test_hyphenated_project_name_yields_two_segment_id` / `test_init_prefix_from_project_name` / `test_get_prefix_exact_expectations_cover_all_shapes` | ✅ | 红 |
| TC-IID-004 | `test_upgrade_write_preserves_installation_id` / `test_repeat_init_with_force_preserves_installation_id` | ✅ | 红（前者对覆盖式写入必挂） |
| TC-IID-005 | `test_init_self_check_prints_actual_installation_id` / `test_init_self_check_reports_missing_when_unwritable` | ✅ | 红 |
| TC-IID-006 | `test_bad_existing_installation_id_is_regenerated`（4 参数）/ `test_null_installation_id_regenerates_silently` | ✅ | 红 |
| TC-IID-007 | `test_corrupted_version_yaml_is_not_clobbered` | ✅ | 红 |
| TC-EID-001 | `test_next_id_with_installation_id` / `test_next_id_preserves_numeric_progression` | ✅ | 红 |
| TC-EID-002 | `test_next_id_without_installation_id` / `test_next_id_version_yaml_without_field` / `test_next_id_rejects_malformed_installation_id` | ✅ | 红 |
| TC-EID-003 | `test_next_id_project_root_none` | ✅ | 红（签名不存在 → ImportError/TypeError） |
| TC-EID-004 | `test_add_experience_uses_prefixed_id` | ✅ | 红 |
| TC-EID-005 | `test_iter_and_index_recognize_prefixed_file` | ✅ | 绿（回归护栏） |
| TC-EID-006 | `test_iter_frontmatter_priority` | ✅ | 绿（回归护栏） |
| TC-EID-007 | `test_rebuild_index_mixed_prefix_and_old` / `test_rebuild_index_ignores_hex_tail` | ✅ | 红 |
| dry-run 分支 | `test_dry_run_previews_without_writing` / `test_dry_run_shows_existing_installation_id` | ✅ | 红 |
| 单元兜底 | `test_generate_installation_id_format_and_randomness` / `test_read_installation_id_returns_none_on_missing` | ✅ | 红 |

> 「回归护栏」两例守护的是 2026-09-17 已修好的「任意 `*.md` 都是经验」约定，
> 对 baseline 不判红 —— 已显式标注，不计入判别力统计（避免虚报）。

---

## 4. 失败模式检查（23 类，逐项实检）

| # | 失败模式 | 检查动作 | 结果 |
|---|---|---|---|
| 1 | 幻觉调用 | AST 静态审查 + 全量 pytest（import 错误会立刻炸）；`ruff F821` 零命中 | ✅ |
| 2 | 过度信任 LLM | 三路评审代理的每条 🔴 都回到源码核实（例：`upgrade._write_version_yaml` 是否真覆盖——读代码 + 写测试确认）；代理报的「无 pyyaml」结论经实测推翻 | ✅ |
| 3 | Prompt 注入 | 本 change 不含 prompt 文件；新增 docstring/注释无 `ignore previous` 类文本 | ✅ |
| 4 | 记忆污染 | 长程模式跨 3 轮评审，每轮重新读磁盘文件而非凭记忆；行号一律重扫 | ✅ |
| 5 | 上下文窗溢出 | 单次 Edit 均 < 300 行；`test_installation_id.py` 整体重写（498 行）分两次写入 | ✅ |
| 6 | 工具参数漂移 | 未新增 MCP/外部工具调用；`secrets.token_hex(4)` / `yaml.safe_load` 均为标准库/既有依赖签名 | ✅ |
| 7 | 安全凭证泄露 | 新增代码无 token/key/DSN；`installation_id` 是随机标识不是凭证；`read_installation_id` 拒绝含 `/` 的值（防路径穿越） | ✅ |
| 8 | 权限绕过 | 未手改 `.fstdd.yaml` 的 gate 确认字段（Gate1/2 有对话原文证据）；本阶段未 `gate approve` | ✅ |
| 9 | 并发竞态 | `_cmd_add` 的 ID 分配仍在 `_index_lock` 临界区内；`_ensure_installation_id` 只在 init 单进程路径执行 | ✅ |
| 10 | 路径遍历 | `INSTALLATION_ID_RE` 限制为 `[A-Z0-9]{2,8}-[0-9A-F]{8}`，ID 会拼进文件名 ⇒ 不可能含 `../`；TC `../etc/passwd` 已覆盖 | ✅ |
| 11 | 跨会话残留 | 临时脚本放 `%TEMP%`，不落仓库；`git status` 仅剩 change 目录未跟踪（`test_a6` 通过） | ✅ |
| 12 | 输出截断 | pytest 输出改走 `--junit-xml` 解析（绕过 safe-delete guard 截断，本会话实际踩过） | ✅ |
| 13 | 格式错误 | 5 个 canonical YAML 全部 `yaml.safe_load` 通过；新增/改写后重跑解析 | ✅ |
| 14 | 循环依赖 | `init → utils`、`experience → utils` 单向；`init ↔ experience` 用函数内 import（既有模式） | ✅ |
| 15 | 重复扣款 | **N/A**（非金融链路，无扣款接口） | — |
| 16 | 账实不符 | **N/A**（无账本/对账） | — |
| 17 | 静默降级 | 本 change 的核心主题：非法值不再静默回落（stderr 出声）、自检不再恒真打 ✅、损坏文件不再静默覆写 | ✅ |
| 18 | 精度丢失 | **N/A**（无金额字段；`last_id` 为整数计数） | — |
| 19 | 审计缺口 | 审计活表 25 点零漂移（`test_aud_002`）；新增代码 0 个吞异常点 | ✅ |
| 20 | 状态机漏洞 | **N/A**（无交易状态机） | — |
| 21 | 额度穿透 | **N/A**（无限额） | — |
| 22 | 合规遗漏 | `installation_id` 为随机安装标识，不含 PII；本 change 不上云任何数据 | ✅ |
| 23 | 过度工程 | YAGNI-7 逐项：① `--prefix` 真需要（中文项目名必须能显式指定）② 本仓无同类实现 ③ 标准库 `secrets` ④ 无平台能力 ⑤ 不新增依赖 ⑥ `_get_prefix` 无法一行完成（清洗 + 兜底 + 告警）⑦ 已是最小实现。**已删除**过度项：`upstream/.fstdd/version.yaml` 模板加空字段（无效改动，已回退）、`_next_id` 的冗余 `project_root is None` 早退 | ✅ |

**15/18/20/21 标为 N/A 的理由**：本 change 是框架 CLI 的标识生成逻辑，
不涉及资金流、账本、交易状态机、限额。按 skill 要求「未实际执行的检查必须标注」，
此处以 N/A + 理由标注，而非打勾充数。

---

## 5. 评审发现与处置

三路并行评审（代码 / 测试 / 文档）共提出 **3 条阻塞、4 条主要、3 条次要**，全部处置：

| 严重度 | 发现 | 处置 |
|---|---|---|
| 🔴 | `upgrade._write_version_yaml` 整体覆盖会抹掉 installation_id（设计假设是错的） | 改「读-合并-写」+ `future_field` 反向断言（ADJ-001） |
| 🔴 | 4 处下游 `EXP-*` 通配依赖，其中回传通道会静默漏推 | 全部改任意 `*.md`；FSD-004 门禁扩围（ADJ-002） |
| 🔴 | SC-IID-003「保留连字符 → `MY-P`」与「ID 恒两段」自相矛盾 | 改清洗语义，规格/设计/测试/实现四处同步（ADJ-003） |
| 🟡 | 写入口径 ≠ 读取口径（坏值被打印 ✅ 却不生效） | 正则收归 `utils.INSTALLATION_ID_RE`，写入端告警重写（ADJ-004） |
| 🟡 | 损坏 version.yaml 被覆写（丢 `stdd_version`） | 解析失败即不写 + 告警（ADJ-005） |
| 🟡 | 3 个假测试（含既有 `test_init_dry_run` 零断言） | 全部重写为真判决（ADJ-006） |
| 🟡 | dry-run 分支零覆盖且打印随机假 ID | 改展示实际值/占位符 + 2 个用例（ADJ-007） |
| 🟢 | agent spec 断言恒真、test-plan 名实不符 | agent spec 改值断言；test-plan 重写（ADJ-008） |
| 🟢 | 模板加空字段是无效改动 | 回退（ADJ-009） |

---

## 6. 已知问题与未完成项

| # | 项 | 原因 | 影响 | 补完计划 |
|---|---|---|---|---|
| 1 | 无 installation_id 碰撞检测 | `token_hex(4)` 2^32 空间，未做全局查重 | 极端情况（同前缀 + 同 HEX）仍会撞号 | 后续换 `token_hex(8)`（正则同步放宽 HEX 段），或建全局 registry（proposal 已列为非目标） |
| 2 | `_load_experience` 跳过无 frontmatter 的 `.md` | 2026-09 起既有语义 | 这类文件「被枚举但不进索引」；`_iter_experience_files` docstring 却说「缺失时退回文件名 stem」 | 单开 change 统一文档与实现（FU-002） |
| 3 | `tools/heartbeat.py` 带 UTF-8 BOM | 既有问题 | 任何 `ast.parse(open(...,encoding='utf-8'))` 的静态门禁都会假红 | 本 change 已在 FSD-004 门禁里做 `utf-8-sig` 兼容，未改该文件（FU-003） |
| 4 | 本仓自身仍无 installation_id | stdd-repo 的 version.yaml 未分配 | 本仓新经验仍是 `EXP-2026-0038` 旧格式（与 `FSTDD002-*` 共存） | 需单独决定是否给框架仓自己分配 ID（FU-004） |

---

## 7. 证据清单

| 证据 | 路径 |
|---|---|
| 全量回归 JUnit（框架侧） | `%TEMP%/full4.xml`（1058 tests / 0 failures） |
| 全量回归 JUnit（仓库侧） | `%TEMP%/repo_tests.xml`（348 tests / 0 failures） |
| TC 追溯性测试 | `tests/test_installation_id_traceability.py`（4 例，冻结 14 个 TC） |
| 审计活表（25 点零漂移） | `.fstdd/changes/2026-10-21-installation-id-prefix/audit/except-points.yaml` |
| 审计表 remap 脚本 | `.fstdd/changes/2026-10-21-installation-id-prefix/evidence/build_audit_table.py` |
| 设计偏离汇总 | `.fstdd/changes/2026-10-21-installation-id-prefix/design-adjustments.yaml` |
| 切片执行计划 | `.fstdd/changes/2026-10-21-installation-id-prefix/slices.md` |
| 任务清单 | `.fstdd/changes/2026-10-21-installation-id-prefix/tasks.md` |
| 经验沉淀 | `.fstdd/experiences/EXP-2026-0038.md` / `0039` / `0040` |
