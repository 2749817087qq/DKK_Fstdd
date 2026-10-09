# 3.3.7+ 任务清单 — 2026-10-07-change-dir-resolution-unify

> 执行顺序：**S1 → S2**（风险升序；S1 = archive-state-consistency 先跑通测试骨架，S2 = change-dir-resolution 改动面最大）

## 1. archive-state-consistency（P0，🟢 中 · 先做）✅ 完成 2026-10-07

- [x] 1.1 新增 `tests/test_archive_state_consistency.py`：`archive` 后断言 `phases.deliver.status == completed`（TC-ASC-001）→ 确认 RED
- [x] 1.2 同文件：归档前后逐字段对比，断言闸门字段零改动（TC-ASC-002）
- [x] 1.3 同文件：`rollback` 后断言 `current_phase` 保持归档前值、`status == active`（TC-ASC-003）→ 确认 RED
      （另加 `test_tc_asc_003b`：相位非 deliver 时同样保留）
- [x] 1.4 同文件：`rollback` 前后 `phases.*` 与闸门字段零改动（TC-ASC-004）
- [x] 1.5 同文件：`archive → rollback → archive` 往返一致（TC-ASC-005）
- [x] 1.6 同文件：`rollback` 冲突检查（`changes/` 同名已存在 ⇒ 拒绝）（TC-ASC-006）
- [x] 1.7 `archive.py`：写 `state["phases"]["deliver"]["status"] = "completed"`（只写该字段）
- [x] 1.8 `rollback.py`：删除 `state["current_phase"] = "understand"`，新增 `_kept_current_phase()` 保留原相位
- [x] 1.9 回归：`test_rollback` / `test_archive` / `test_phase` / `test_state` / `test_state_coverage` = **35 passed**

## 2. change-dir-resolution（P0，🟡 高 · 后做）✅ 完成 2026-10-07

- [x] 2.1 新增 `tests/test_change_dir_resolution_unify.py`：真实归档 change 上 3 条读命令（TC-CDR-001/002/003）→ 确认 RED
- [x] 2.2 同文件：短名后缀匹配在归档区生效（TC-CDR-004）
- [x] 2.3 同文件：写命令在归档 change 上拒绝 + 文案三要素 + 落盘不变（TC-CDR-005/006）→ 确认 RED
- [x] 2.4 同文件：`gate amend-audit` 在归档 change 上放行（TC-CDR-007）
- [x] 2.5 同文件：在办 change 上读/写零漂移（TC-CDR-008）
- [x] 2.6 同文件：无 `archive/` 目录时不抛异常（TC-CDR-011）；对已归档 change 再 `archive` 仍拒绝（TC-CDR-012）
- [x] 2.7 契约扫描：接受 change 名的模块必须走统一入口（TC-CDR-009）
- [x] 2.8 扫描器双向自检：违例能抓 / 合法不误报 / 「注释与 docstring 提及」判违规 / `getattr` 形态能认（TC-CDR-010）
- [x] 2.9 `finder.py`：新增 `require_active_change_dir(name, project_root) -> Path`（含 `resolve()` 归一化判定）
- [x] 2.10 `phase.py`：`_find_change` 改走统一入口 + 保留批级兜底；新增 `_resolve_write_change`；`cmd_phase` 读写分层
- [x] 2.11 `gate.py`：`_find_change_dir` 改走统一入口；`approve` 走写入口，`amend-audit` 走读入口
- [x] 2.12 `state.py`：`_find_change_dir` 改走统一入口；`--set` 走写入口
- [x] 2.13 `work.py`：`_find_change` 改走统一入口 + 保留批级兜底；`add` 走写入口
- [x] 2.14 `baseline.py`：`_resolve_change` / `_change_yaml` 改走统一入口；`establish` 走写入口（解析提前到 dry-run 之前）
- [x] 2.15 回归（15 文件）= **136 passed**
- [x] 2.16 ⚠️ **评审追加**：`rollback.py` 删死导入 + 改用 `finder._resolve_in`（复用解析原语，消本地重复匹配）
- [x] 2.17 ⚠️ **评审追加**：路径遍历加固（`_resolve_in` 拒分隔符/`..` + `require_active_change_dir` 归一化比较）+ 新增 `test_tc_cdr_005b`

## 3. 测试与验证（全切片后）

- [x] 3.1 全量 `pytest upstream/tests` —— 见 test-report §一（权威终跑）
- [x] 3.2 根 `tests/` 全量 —— 见 test-report §一
- [x] 3.3 四自检脚本（rename / eol / skill_standards / workbuddy_skills）—— 见 test-report §七
      （rename 7/8 · eol 6/7 为**结构性红**，提交后转绿；skill_standards 因沙箱 safe-delete 守卫 **环境阻塞**未取得结果；workbuddy_skills PASS）
- [x] 3.4 多路并行技术评审（C1，3 代理）—— 报出 3 critical/一般 + 多条提示，逐条处置见 §四
- [x] 3.5 `fstdd ci check-failures`（C2）—— 0 错误；TC 实现覆盖 18/18
- [x] 3.6 Diff 审查（C3）
- [x] 3.7 失败模式检查 23 项（C4）—— 见 test-report §八
- [x] 3.8 经验库记录/更新（C5）—— 新增 **EXP-2026-0026 / 0027**
- [x] 3.9 design-adjustments（C6）—— `design-adjustments.yaml`（8 条）
- [x] 3.10 test-report.md（C7）—— 已生成

## ⚠️ 本 change 自设纪律（因触及破坏性命令）

- [x] 所有 `archive` / `rollback` 测试一律在 `tmp_path` 合成项目内跑；对仓库内真实 change **只做只读**
      （`test_tc_cdr_003b` 是唯一触及真实归档 change 的用例，**只跑 `phase status`**）
- [x] RED 取证在隔离环境（合成项目内），未在主工作区回退修复后直接跑
- [x] 每次跑过 CLI 生成命令后检查并归一新产生的 CRLF 文件

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->
