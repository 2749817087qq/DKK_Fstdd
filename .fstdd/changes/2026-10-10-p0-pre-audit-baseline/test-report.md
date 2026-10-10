# test-report.md — change 2026-10-10-p0-pre-audit-baseline

**日期**：2026-10-10
**阶段**：Phase 3 BUILD（切片 1–4）
**模式**：standard ｜ **前置**：Gate 1 ✅（外部沙箱 18:26）/ Gate 2 ✅（外部沙箱 18:32）
**基线**：HEAD `0c8d2de8b5e904b55931eb3183438cd910e35197`（tag `fstdd-v3.3.8`）
**范围修正**：AMD-001（切片 3 集成切出）/ AMD-002（46 清单入库）—— 见 `design-adjustments.yaml`

---

## 一、切片完成度

| 切片 | capability | 状态 | 证据 |
|---|---|---|---|
| 1 packaging | toolchain-packaging | ✅ **done** | §2.1（SC-1/2/3 + T1.4 边界全通过） |
| 2 patches-registry | patches-registry | ✅ **done** | §2.2 |
| 3 validate 检查项 | validate-upstream-patches | ⚠️ **partial**（AMD-001 切出集成） | §2.3 |
| 4 审计基线 | audit-baseline | ✅ **done** | §2.4 |

---

## 二、逐切片证据

### 2.1 切片 1 · packaging

| 用例 | 命令 | 结果 |
|---|---|---|
| T1.1 / SC-1 | `python -m venv .venv-test` → `pip install -e ".[test]"` → `fstdd --help` | ✅ 安装成功（`fstdd-3.3.8-0.editable`），`fstdd --help` **exit=0** |
| T1.3 / SC-3 | `python -c "import yaml, jinja2, requests, fstdd"` | ✅ 全部导入成功；`importlib.metadata.version('fstdd')` = **3.3.8** |
| T1.4 边界 | `pip wheel . --no-deps` + `zipfile` 列表 | ✅ wheel 顶层仅 `['fstdd', 'fstdd-3.3.8.dist-info']`（54 条目）；**无** `skills/` `tools/` `docs/` `.fstdd/` |
| T1.2 / SC-2 | venv 内 `pytest upstream/tests` | 见 §3 |

安装明细：`Successfully installed MarkupSafe-3.0.4 certifi-2026.7.22 charset_normalizer-3.5.2 colorama-0.4.6 **fstdd-3.3.8** idna-3.20 iniconfig-2.3.1 jinja2-3.1.6 packaging-26.3 pluggy-1.6.0 pygments-2.21.0 pytest-9.1.1 pyyaml-6.0.3 requests-2.34.2 urllib3-2.8.0`

### 2.2 切片 2 · patches-registry

`docs/UPSTREAM_PATCHES.md`（1074 B）已落盘，内容核对：

| 用例 | 判据 | 结果 |
|---|---|---|
| T2.1 / SC-1 | 基线声明 `E=3.0.5 / K=3.1.0 / R=3.3.8` + 指向 `UPSTREAM_BASELINE.md` | ✅ |
| T2.1 / SC-2 | 表头 8 列（`# / 文件 / 行号 / 修改原因 / 关联上游 issue/PR / 登记日期 / 登记人 / 预期回退版本`） | ✅ |
| T2.2 / SC-3 | 「待登记」区含 `experience.py:428` + CRLF 项标注「走上游 PR，不本地改」 | ✅ |

### 2.3 切片 3 · validate 检查项（**partial**）

| 用例 | 命令 | 结果 |
|---|---|---|
| T3.1–T3.4 / T4.1–T4.3 | `pytest tools/tests -q` | ✅ **15 passed**（交付包 12 + 本 change 新增 3 条 B1 回归断言） |
| 变异自检 | 表头比对临时改 7 列 → T3.1 必须变红 | ✅ 已由评审复现（2 failed），恢复后全绿 |

⚠️ **AMD-001**：`spec-validate-upstream-patches.md` 的 SC 原文写「运行 `fstdd validate`」，但实测
`upstream/fstdd/cli/commands/validate.py` 语义为「校验单个 change 目录」，检查项注册表
`CHECKS` / `@_register_check` 位于 **`upstream/fstdd/cli/commands/ci.py`**（10 项）
⇒ **CLI 集成已切出为独立 change**。本批次仅交付参考实现 `tools/validate_upstream_patches.py`（未集成）。

### 2.4 切片 4 · 审计基线

| 用例 | 命令 | 结果 |
|---|---|---|
| T4.4 / SC-3 | `python tools/audit_experience_baseline.py --repo . --out .fstdd/experiences/audit-2026-10-experience-baseline.json` | ✅ exit=0，产出 71,984 B |
| T4.1 / SC-1/2/3 | 合成夹具全边界（单块/双块/导出块缺真身/无 frontmatter） | ✅ pytest |
| T4.2 / SC-4 | 夹具注入 eid 不一致 → 计入 `eid_mismatch.files` | ✅ pytest |
| T4.3 / SC-5 | 夹具索引缺某 eid → `indexed_false_files` 命中 | ✅ pytest（**含新增的裸列表形态回归**） |
| T4.5 / SC-4 | 与 46 文件清单逐一对账 | ✅ 清单已按 AMD-002 入库（`audit/affected-files-46.md`），条数与 `affected_entries` **一致（46=46）** |
| T4.6 | 复核 `EXP-1BA44745.md` 的 `eid_match` | ⚠️ **未复现评审所述 false** —— 本地实测 `eid_match=true`（三处 eid 均为 `EXP-1BA44745`）。以本地实跑为准并留痕 |

**真实基线关键指标**：

| 指标 | 值 |
|---|---|
| `total_entries` | **79** |
| `dual_block_entries` | **47** |
| `affected_entries` / `affected_ratio` | **46 / 58.2%** |
| `field_loss_counts` | `{experience_id: 46, category: 46, severity: 46}` |
| `index_reconciliation.indexed_true` | **78** |
| `index_reconciliation.indexed_false_files` | **`[]`** |
| `index_reconciliation.unreconciled_files` | `['EXP-009-20260925-TRPC-REVERSE.md']` |
| `index_reconciliation.invariant_ok` | **True** |
| `eid_mismatch` | `{count: 6, files: [EXP-20260918-C1..C6]}` |
| `audit_meta.git_head` | `0c8d2de8b5e904b55931eb3183438cd910e35197` |

---

## 三、仓库门禁（目标仓全量）

| 门禁 | 结果 |
|---|---|
| `pytest upstream/tests`（**干净 venv 内**，SC-2） | 960 tests / **954 passed / 5 skipped / 1 failed** —— 唯一失败 = `test_a6_no_stray_untracked_files`（结构性，commit 后自愈）；**与未打包直跑结果一致** ⇒ SC-2 达标 |
| `pytest tools/tests`（venv 内） | **15 passed**（3.97s） |
| `pytest tests`（根，系统解释器） | 158 tests / **0 failed** / 3 skipped（首跑 1 failed = 编码策略，已修，见 §5） |
| `pytest upstream/tests`（系统解释器） | 960 tests / 951 passed / 5 skipped / 4 failed → 修复后仅剩 `test_a6`（结构性，commit 后自愈） |
| `test_a2_structure_mirrors` | ✅（首跑红 = `push_stdd_repo.sh` 被误删，已恢复，见 §5） |
| `test_aud_002` / `test_grd_001` | ✅（首跑红 = 新文件引入未登记吞异常点，已收窄 except，见 §5） |
| `test_subprocess_encoding_policy` | ✅ 6 passed（首跑红 = 3 处缺 `encoding=`，已修，见 §5） |

---

## 四、B1 修复（落盘前评审阻塞项）

**缺陷**：`load_index_keys` 只匹配 `experience_id: <id>` 形态，而真实 `.experience-index.yaml` 是
`by_category:` 下的**裸列表项**（实测 `experience_id:` 出现 **0 次**、裸项 78 条）⇒ `indexed_true` 恒 0、
全部条目被误判「未入索引」（假阳性洪泛）。

**修复**（3 处，均在白名单文件内）：

1. `load_index_keys`：优先按裸列表项解析（`^\s*-\s*((?:[A-Za-z0-9]+-)?EXP-[\w.-]+)\s*$`），
   无命中回落 `experience_id:` 形态 ⇒ **向后兼容**（交付包原 12 用例全部继续通过）
2. `no_frontmatter` 分支：补全 design §4 schema 键 + `in_index="unreconciled"`（消除**静默排除**）
3. `_index_recon`：两桶 → **四桶**（`indexed_true` / `indexed_false_files` / `unreconciled_files` /
   `index_missing_count`）+ `eid_mismatch_files` + 不变式 `invariant_ok`

**新增回归断言 3 条**：`test_t43b_bare_list_index_is_parsed` / `test_t43c_bare_list_index_prefix_eid_recognised` /
`test_t43d_no_frontmatter_not_silently_excluded`

---

## 五、落盘后跑仓库门禁暴露的 3 条（评审未覆盖，均已处理）

> 根因：交付包在**无仓库权限**下编写 ⇒ 不知道目标仓的仓库级策略门禁。

1. **编码策略**：3 处 text-mode `subprocess` 缺 `encoding=`（`tools/audit_experience_baseline.py` +
   `tools/tests/test_governance_baseline.py` ×2）⇒ 补 `encoding="utf-8", errors="replace"` ⇒ 6 passed
2. **裸 except 审计表漂移**：新文件引入 1 个未登记吞异常点 ⇒ 扫描器判据为
   `^\s*except\s*(?:Exception|BaseException)\s*:?\s*$`（只认裸 `except`/`except Exception`）
   ⇒ **收窄为 `except (OSError, subprocess.SubprocessError)`** 即合法消除（无需动归档审计表）
3. 🔴 **误删 `push_stdd_repo.sh`**（本任务早先工作区清理所致）：`test_a2_structure_mirrors` 断言
   `E:/FSTDD/push_stdd_repo.sh` 必须存在 ⇒ 已从 `_backup/workspace-cleanup-c-20261009/` 恢复
   （sha256 `91deac360ffe3edc` 与清单登记值逐字节一致）

---

## 六、已知问题与未闭合项

| # | 项 | 处置 |
|---|---|---|
| 1 | **切片 3 CLI 集成未做** | AMD-001：切出为独立 change |
| 2 | **T4.6 未复现**（`EXP-1BA44745` 本地 `eid_match=true`） | 以本地实跑为准；`eid_mismatch` 语义（前缀约定 vs 真损坏）待重定义 |
| 3 | **根 `pyproject.toml` 与 `upstream/pyproject.toml` 同名不同版本**（3.3.8 vs 3.1.0） | 关系待明确；已记入 spec 的 boundaries |
| 4 | `design.md §4` 的 `index_reconciliation.eid_mismatch_files` | ✅ 已补齐 |
| 5 | **SC-6（分类分布双视角）零断言** | 未修（spec 层面，需补用例） |
| 6 | `validate_upstream_patches.py` 表头存在但缺分隔线 ⇒ 畸形表被当空表放行 | 未修（评审 #15，Low） |
| 7 | `--repo` 可路径穿越（存在性 oracle）/ `--out` 无护栏 | 未修（评审 #16/#17，Low/Info） |
| 8 | runbook 命令混 shell（`/tmp`、`unzip` 在 Windows 不可用） | 未修（属交付包文档） |

---

## 七、结论

- 切片 1 / 2 / 4 **完成并实跑验证**；切片 3 参考实现完成、**CLI 集成按 AMD-001 切出**。
- 落盘前评审的 🔴 **B1 已修复并验证**（`indexed_true=78` / `invariain_ok=True`，与评审期望定值一致）。
- B3 已按 AMD-002 处置（46 清单入库，T4.5 对账可执行）。
- 落盘后跑目标仓门禁额外暴露 3 条，**全部修复**。
- 本 change 的核心交付物 —— **修复前量化基线**已产出：**46/79（58.2%）** 条目受首块解析器影响，
  三字段齐丢；该数字与 proposal 口径**完全吻合**。

> ⚠️ 唯一残留门禁红项 `test_a6_no_stray_untracked_files` 为**结构性**（判据排除 `.fstdd/changes/` 外的未跟踪项，
> 而本次新增工件在提交前均为未跟踪）⇒ **commit 后自愈**。
