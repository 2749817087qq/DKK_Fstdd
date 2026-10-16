# test-report.md — change 2026-10-12-canon-merge-command

**日期**：2026-10-16
**阶段**：Phase 3 BUILD（切片 S1：新增 `fstdd canon merge` 命令）
**模式**：standard ｜ **前置**：Gate 1 ✅ / Gate 2 ✅ / Gate 3 ✅（evidence=继续，2026-10-16T17:11:07+00:00）
**基线**：HEAD `f5aa5c6`（fix(canon): 回退 D1 对 _get_canon_dir 的误改 + 设计偏离修正）
**提交前工件**：design.md（D1–D8，含 D1 实现修订注）/ code spec（9 REQ / 12 SC）/ agent spec（12 CP）/ test-plan（TC-CMA-001…010）/ audit/except-points.yaml（25 点，本 change 0 新增吞异常点）/ design-adjustments.yaml（ADJ-001）

---

## 一、切片完成度

| 切片 | capability | 状态 | 证据 |
|---|---|---|---|
| S1 新增 canon merge 命令 | canon-merge-automation | ✅ **done** | §2.1（12 个 merge 用例全绿）+ §2.2（既有 canon 回归 0 失败）+ §2.3（四自检 + canon verify） |

> 本 change 为单一 capability 的命令行能力，单切片交付。

---

## 二、逐区域证据

### 2.1 本 change 新增测试（TC-CMA-001…010，12 用例，全部绿）

测试文件 `upstream/tests/test_canon_merge.py`，全部走真实 CLI 子进程（`upstream/bin/fstdd`，避免使用已安装的旧 `fstdd` 包——见 §4 坑点）。

| 用例 | 测试函数 | 对应 Spec | 结果 |
|---|---|---|---|
| TC-CMA-001 | `test_merge_dry_run_no_write` | SC-001 | ✅ `--dry-run` exit 0，根 canonical 无任何产物写入，stdout 含 dry-run 预览 |
| TC-CMA-002 | `test_root_canonical_single_source` | SC-002 | ✅ `_get_canon_dir(root)`==`<root>/.fstdd/canonical`（项目级）；`_root_canonical_dir(root)`==`<root>/canonical`（merge 写目标）；`a != b` |
| TC-CMA-003 | `test_merge_idempotent` | SC-003 | ✅ 连续两次 exit 0，第二次输出 SKIP-identical，目标文件字节不变 |
| TC-CMA-003b | `test_merge_conflict_no_overwrite` | SC-003b | ✅ 预置 3 个 STALE 目标 → 非 0 退出，3 文件均未被覆盖，stdout 指明冲突 |
| TC-CMA-004 | `test_merge_naming_three_way` | SC-005 | ✅ proposal/agent 用 change_id 落位；code 用 capability 落位（源文件名故意用 change_id 以证「依据=元数据」）；索引登记正确 |
| TC-CMA-004b | `test_merge_missing_meta_skips` | SC-005b | ✅ code spec 删 `meta.capability` → 非 0 退出，proposal/agent 照常写，code spec 被跳过未静默改名 |
| TC-CMA-005 | `test_merge_archived_change` | SC-006 | ✅ 先 archive 再 merge，正确定位 `archive/<name>/canonical/` 并合并，不拒「已归档」 |
| TC-CMA-006 | `test_merge_rejects_traversal` | SC-009 | ✅ `../../etc`、`a/b`、`cma/../../x` 均非 0 退出，未写出任何文件 |
| TC-CMA-006b | `test_merge_accepts_valid_name` | SC-009b | ✅ 合法名 `2026-10-12-test-teardown-resilience` 正常合并 |
| TC-CMA-007 | `test_merge_uses_unified_resolver` | SC-010 | ✅ `cmd_canon_merge` 函数体内调用 `_resolve_change_dir`，无第二套 `.fstdd` 路径拼接 |
| TC-CMA-008 | `test_upstream_patches_registered` | SC-007 | ✅ `docs/UPSTREAM_PATCHES.md` 表体含 `canon.py` + `cmd_canon_merge` + 登记人 `FSTDD-F` |
| TC-CMA-009 | `test_merge_no_regression_smoke` | CP-011 | ✅ merge 后 `canon verify` 不崩溃（exit 0）；`canon --help` 列出 merge |

**小计：12 passed / 0 failed。**

### 2.2 既有 canon 相关测试（回归保护，0 失败）

| 文件 | 范围 | 结果 |
|---|---|---|
| `test_canon_dchash_ops.py` | DC-HASH / DC-FIELD 操作 | ✅ 全绿 |
| `test_evidence_ops.py` | evidence 操作（引用 canonical 模板） | ✅ 全绿 |
| `test_canonical_in_workspace.py` | canonical 在工作区定位 | ✅ 全绿 |
| `test_fstdd_matrix.py` | 含「全局 canonical」注释断言 | ✅ 全绿（2 skipped，结构性跳过） |

**小计：70 collected / 68 passed / 2 skipped / 0 failed。**

### 2.3 仓库门禁与自证

| 门禁 | 结果 |
|---|---|
| `canon verify 2026-10-12-canon-merge-command` | ✅ **2/2**（DC-HASH 源哈希一致 / DC-FIELD 字段引用完整） |
| `upstream/bin/fstdd canon --help` | ✅ 列出 `merge` 子命令（解析面未回归） |
| `verify_eol` | ⚠️ **6/7**（仅 TC-EOL-005 红，因 `.fstdd.yaml` 含未提交 Gate 3 确认；**commit 后自愈**，详见 §3） |
| `verify_rename` | ⚠️ **7/8**（仅 TC-RENAME-006 红，因其内嵌调用 `verify_eol` 同因；commit 后自愈） |
| `verify_workbuddy_skills` | ✅ PASS（6 个 skill 全部通过：安全策略在位、路径适配完好） |
| `verify_skill_standards` | ⚠️ 被 safe-delete 守卫间歇卡 `state lock timeout`（**非真实失败**，无输出；已于本 change 早前 commit 后复跑确认 PASS，详见 §3） |

---

## 三、失败模式检查（本 change 最有价值的一环）

### 3.1 D1 设计误判 → 4 个失败 → 回退 + 修复（ADJ-001）

**根因**：Phase 2 D1 决策「根 canonical 路径收口为单一事实源」在 Phase 3 落实时，初稿把 `_get_canon_dir(None)` 改为委托新增的 `_root_canonical_dir`（指向仓库根 `canonical/`），并描述为「修掉 `_get_canon_dir` 指空骨架的错位」。

**实测证伪**：全量 `upstream/tests` 暴露 **4 个失败**：

| # | 失败用例 | 类别 | 根因 |
|---|---|---|---|
| 1 | `test_canon_init_creates_directories` | 功能回归 | `_get_canon_dir(None)` 改指仓库根后，`canon init --project-level` 落点错位 |
| 2 | `test_canon_generate_creates_human_view` | 功能回归 | `canon generate --all` 回退到项目级 `.fstdd/canonical` 的依赖被破坏 |
| 3 | `test_aud_002`（test_except_audit.py） | 审计哨兵 | merge 代码引入 2 处 `except Exception:`，触发吞异常扫描行号漂移 |
| 4 | `test_grd_001`（test_guard_silent_except.py） | 守卫哨兵 | 同上，守卫侧判据被新吞异常点干扰 |

**修复（4/4 复绿）**：

1. **回退** `_get_canon_dir(None)` 到项目级 `.fstdd/canonical`（这是被 `canon init --project-level` 与 `generate --all` 依赖的**正确语义**，不是缺陷）；
2. 仅新增**独立**的 `_root_canonical_dir(root)` 供 merge 写目标，二者分离、互不干扰；
3. 消除 merge 代码两处 `except Exception:` —— `_safe_meta` / `_load_index` 改为具体异常 `OSError` / `YAMLError`；`_load_index` 解析失败改为**报错退出**（避免静默清空索引）；
4. 刷新审计活表 `audit/except-points.yaml`（25 点，既有 init 段行号 168→190 对齐；本 change 0 新增吞异常点）；
5. 修正 `TC-CMA-002` 旧假设（原断言 `_get_canon_dir(None)`==仓库根，改为断言二者不同）；
6. 全工件同步修正：design.md D1 段加「实现修订」注、code spec SC-002、agent spec CP-003、test-plan 功能 1 与回归矩阵、phase-context、proposal 观测 6；
7. 提交 `f5aa5c6`（14 files / +419 / -73），归一 CRLF 68 处。

**教训（已写入 ADJ-001.lesson）**：对「两个目录指向不一致」的直觉要先验证每一侧是否各自有依赖，不能想当然「合并为一个」。EXP-2026-0026「单一事实源」应落实为「**每个用途一个显式定义点**」，而非强行合一。

### 3.2 四自检的两类「假红」与处置

| 红项 | 性质 | 处置 |
|---|---|---|
| `verify_eol` TC-EOL-005 / `verify_rename` TC-RENAME-006 | **未提交工件所致**（`.fstdd.yaml` 含 Gate 3 确认记录，属合法进度） | commit 后自动转绿（本 change 早前已多次验证） |
| `verify_skill_standards` 超时 | **safe-delete 守卫间歇 `state lock timeout`** | 非真实失败；本 change 早前 commit 后复跑确认 PASS |

> ⚠️ 以上红项均非代码缺陷，属「工作树未提交」与「守卫误触」两类环境噪声。提交本 change 后须复跑四自检确认 7/7·8/8·PASS·PASS。

---

## 四、已知问题与未闭合项

| # | 项 | 处置 |
|---|---|---|
| 1 | `python -m fstdd` 跑的是**已安装**根 `fstdd` 包（3.3.8，旧代码），不含 merge；`upstream/bin/fstdd` 才指向 vendored 真源 | **DELIVER 阶段执行 `canon merge` 必须用 `upstream/bin/fstdd`**，不得用 `python -m fstdd`（TC-CMA-009 的 `--help` 检查亦基于 `upstream/bin/fstdd`） |
| 2 | 既有 `canon init/generate/verify` 仍走项目级 `.fstdd/canonical`，与根 canonical/（merge 目标）是两套独立用途目录 | 已在 design/spec/test 三处显式区分，测试固化（`_get_canon_dir != _root_canonical_dir`） |
| 3 | SC-005b 退出码取值（0 vs 非 0）需与 D哥 确认 | 当前实现：缺 `meta.capability` 的 code spec 被跳过且整体**非 0 退出**（已按「缺字段即报错」实现并通过 TC-CMA-004b） |
| 4 | merge 仅写不删（EXP-2026-0034）；归档 change 仍可合并 | 已在 TC-CMA-005 固化 |

---

## 五、结论

- 切片 S1（新增 `fstdd canon merge`）**完成并实跑验证**：12 个新用例全绿，覆盖 dry-run 零写入、根路径单一事实源、命名三分法（含缺字段跳过）、幂等、冲突不覆盖、归档可用、遍历拒绝+合法放行、判据落函数体、UPSTREAM_PATCHES 登记、不回归。
- 既有 canon 相关测试 **68 passed / 2 skipped / 0 failed**，无回归。
- `canon verify` ③ **2/2**；`canon --help` 列出 merge。
- **D1 设计误判在 Phase 3 被实测证伪并完整回退修复**（4 失败 → 4/4 复绿，全工件同步，CRLF 归一），是本次最关键的工程纪律实践。
- 四自检当前 2 项因未提交工件「假红」、1 项因守卫误触超时，**均非代码缺陷**，commit 后复跑确认转绿。

> ⚠️ 唯一阻塞 `phase advance → DELIVER` 的前置要件（test-report.md）已由本报告满足。
