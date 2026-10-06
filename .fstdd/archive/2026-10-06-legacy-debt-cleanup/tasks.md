# 3.3.5 任务清单 — 2026-10-06-legacy-debt-cleanup

> 状态：Phase 3 BUILD 全部 4 切片完成（2026-10-06T14:43Z）；Part C 质量验证进行中。

## 1. test-suite-portability（P0）✅ 完成

- [x] 1.1 记录修复前基线：AST 扫描 36 处缺 `encoding=` 的调用清单（16 文件）
- [x] 1.2 记录修复前 `pytest --collect-only -q` 用例清单（供 TC-TSP-005 比对）
- [x] 1.3 新增 `tests/test_subprocess_encoding_policy.py`：AST 审计断言（TC-TSP-001）+ `errors=` 取值审计（TC-TSP-004）→ 确认 RED
- [x] 1.4 为 16 文件 36 处 text-mode `subprocess` 补 `encoding="utf-8", errors="replace"`（只增参数）；另补 19 处文本 I/O `encoding="utf-8"`（ADJ-001）
- [x] 1.5 非 UTF-8 环境跑 `tests/test_multi_platform.py`（TC-TSP-002）→ 11 passed, 1 skipped
- [x] 1.6 权威环境跑全量 pytest（TC-TSP-003）
- [x] 1.7 修复前后用例清单比对（TC-TSP-005）：根 `tests/` 71 → 87（+16 全为本 change 新增），零删除

**B3.4 切片验证**：双环境对照**逐字一致**（`1 failed, 74 passed, 3 skipped, 1 deselected`）⇒ 套件与环境编码解耦。唯一失败为 `test_L1_11`（Slice 2 目标）。

## 2. release-tooling-accuracy（P0，依赖 #1）✅ 完成

- [x] 2.1 新增 `tests/test_release_manifest_accuracy.py`：清单失真表述扫描（TC-RTA-001）→ 确认 RED（6 failed）
- [x] 2.2 修正 `.fstdd/standards/release-and-docs.md` 第 29 行失真表述（其余逐字不动）
- [x] 2.3 改写 `tests/test_finance_content.py::test_L1_11` 为动态读 `version.yaml` + 与 `project.yaml` 比对（TC-RTA-002）
- [x] 2.4 新增动态性测试：构造任意版本值验证不依赖字面量（TC-RTA-003）
- [x] 2.5 跑 `pytest tests/ -q`（TC-RTA-004）→ **83 passed, 4 skipped, 0 failed**
- [x] 2.6 **（新增，ADJ-004）** 修 `tests/test_install_smoke.py` 硬编码 tag 字面量 `fstdd-v3.1.1` → 由 `version.yaml` 派生（TC-RTA-005）；补 2 个宿主隔离用例覆盖「一致/不一致」两分支

## 3. canonical-hash-integrity（P0，可与 #1 并行）✅ 完成

- [x] 3.1 新增 `tests/test_canon_hash_integrity.py`：归档 change `canon verify` 2/2 断言（TC-CHI-001）→ 确认 RED
- [x] 3.2 同步归档 `.fstdd/archive/2026-09-18-inbox-api-only-write/proposal.md` 的 `source_hash` → `29c0012fe4d0b612`
- [x] 3.3 批量核对根 `canonical/proposals/` 全部条目（TC-CHI-002）→ 14 条全部 2/2
- [x] 3.4 核对本 change canonical 双轨一致 + 索引零缺失（TC-CHI-003）→ 2/2

## 4. repo-hygiene（P0，可与 #1 并行 · 破坏性）✅ 完成

- [x] 4.1 **落盘 27 个 `_scratch/` 实体清单**（含 25 个文件 md5 + 2 个 gitlink 目录）→ `audit/scratch-inventory.txt`
- [x] 4.2 新增 `tests/test_repo_hygiene_scratch.py`：索引为空 + gitignore 含规则 + 磁盘实体仍在（TC-RH-001/002/003/004）→ 确认 RED（6 failed / 1 passed）
- [x] 4.3 执行 `git rm -r --cached _scratch/`（仅索引）
- [x] 4.4 `.gitignore` 新增 `_scratch/` 规则
- [x] 4.5 核对磁盘实体数未减 → 索引 27→0、顶层实体 12→12、27 条实体**缺失 0**
- [x] 4.6 跑 `test_a6_no_stray_untracked_files` 回归 → 失败项**仅本 change 新建的 4 个测试文件**（未提交故 `??`）；`_scratch/` 已不在列表 ⇒ DELIVER 提交后即绿

## 5. 测试与验证（全切片后）

- [x] 5.1 权威环境全量 pytest：根 `tests/` **94 passed / 0 failed / 4 skipped**（双环境逐字一致）；`upstream/tests` **953 passed / 5 skipped / 2 failed**（1 项提交前预期 + 1 项 flaky）
- [x] 5.2 四自检脚本：rename 7/8、eol 6/7、skill_standards **7/7**、workbuddy_skills **PASS** —— ⚠️ 前两项因「索引 vs HEAD」判据在提交前结构性红，**提交后须复跑**
- [x] 5.3 多路并行技术评审（C1）：3 代理，报 5 条严重发现 → **2 条证伪、3 条成立并修复**（ADJ-008）
- [x] 5.4 `fstdd ci check-failures`（C2）：4 ✅ / 2 ⚠ / 3 ⏭ / 1 ❌ —— ❌ 为既有工具口径问题（38 份 test-plan 有 26 份重复），非本变更缺陷
- [x] 5.5 Diff 审查（C3）：53 文件改动；**未触碰 `upstream/fstdd` 内核代码**；索引删除 27 条全在 `_scratch/`
- [x] 5.6 失败模式检查 23 项（C4）：**16 ✅ / 7 SKIPPED（非金融）/ 0 ❌**
- [x] 5.7 经验库记录/更新（C5）：新增 **EXP-2026-0020/0021/0022**，均已 verify；库 70 → 73
- [x] 5.8 design-adjustments（C6）：`design-adjustments.yaml` **8 条**（4 large / 1 medium / 3 small）
- [x] 5.9 test-report.md（C7）：已生成，含双环境对照、破坏性操作零损失核验、23 项失败模式、11 条遗留项

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->
