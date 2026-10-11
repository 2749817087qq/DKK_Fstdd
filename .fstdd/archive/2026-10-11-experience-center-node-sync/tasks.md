# 2026-10-11 任务清单

> change: 2026-10-11-experience-center-node-sync

## 1. experience extract 扩源（C1 / REQ-001，P0）

- [x] 1.1 抽取非交互核心：拆出 `_extract_sources(change_dir, sources)` + `_write_drafts(...)`
- [x] 1.2 新增 `_parse_design_adjustments(text)` 解析器（design-adjustments.md → pattern）
- [x] 1.3 新增 `_parse_adjudication_log(text)` 解析器（adjudication-log.tsv → pattern）
- [x] 1.4 CLI 接线：`experience extract [--source ...] [--all]`
- [x] 1.5 测试 `upstream/tests/commands/test_experience_extract_sources.py`（TC-EEXT-001..005）

## 2. 非交互自动沉淀（C2 / REQ-002，P0，依赖 #1）

- [x] 2.1 新增 `_cmd_auto_deposit(args, exp_dir)`：复用 #1.1 核心 + 非交互入库（lifecycle=discovered）
- [x] 2.2 honor `FSTDD_NO_SHARE=1`（`_share_disabled()`）→ 静默跳过
- [x] 2.3 CLI 接线：`experience auto-deposit`
- [x] 2.4 `fstdd-deliver` 流程内显式调用点（文档接线，不改 hook）
- [x] 2.5 测试 `upstream/tests/commands/test_experience_auto_deposit.py`（TC-EAUT-001..004）

## 3. opt-in 安全档混合加密（C4 / REQ-004，P0）

- [x] 3.1 新增 `upstream/fstdd/cli/commands/_exp_crypto.py`：`hybrid_encrypt` / `hybrid_decrypt`
- [x] 3.2 锁定 OAEP 参数 + 318B 上限走混合加密
- [x] 3.3 出站前先脱敏（`_sanitize_text`）再加密
- [x] 3.4 测试 `upstream/tests/commands/test_exp_crypto.py`（TC-ESEC-001..005）

## 4. 中心节点同步（C3 / REQ-003，P0，依赖 #3）

- [x] 4.1 新增 `_cmd_sync(args, exp_dir)`：`--push` / `--pull` / `--dry-run` / `--secure`
- [x] 4.2 push 腿：复用 `tools/share_experience.py`（scp fstdd-hub / inbox POST）
- [x] 4.3 pull 腿：hub 快照 + kg_sync 式增量合并（`_exp_sync.merge_entries`）
- [x] 4.4 幂等 + `--dry-run` 绝对安全（不写不传）
- [x] 4.5 测试 `upstream/tests/commands/test_experience_sync.py`（TC-ECNS-001..005）

## 5. 同步冲突策略（C5 / REQ-005，P0，依赖 #4）

- [x] 5.1 `updated_at`（缺则 `exported_at`/`first_seen`）末写胜
- [x] 5.2 冲突日志（eid + 双方 updated_at + 落点），绝不静默丢弃
- [x] 5.3 测试 `upstream/tests/commands/test_sync_conflict.py`（TC-ECON-001..003）

## 6. 第三方外发审计（REQ-006，P0）

- [x] 6.1 静态断言：`_cmd_share_single` 禁用分支（leonai42/hzddyy）与注释不变
- [x] 6.2 源码第三方域名审计（AST 判据：docstring/print 语境放行，活跃字面量禁止）
- [x] 6.3 测试 `upstream/tests/commands/test_no_third_party_egress.py`（TC-ESAF-001..002）

## 7. 测试与验证

- [x] 7.1 各切片 per-slice 验证（TC 覆盖 + 产出物核对 + 测试通过）
- [ ] 7.2 全量 pytest 通过（含 upstream 回归）
- [ ] 7.3 C1 多路并行技术评审（代码/测试/文档）
- [ ] 7.4 C2 全量质量检查（pytest + coverage + lint + ci check-failures）
- [ ] 7.5 C4 失败模式检查（23 类逐项）
- [ ] 7.6 C5 经验库自动记录 / C6 design-adjustments / C7 test-report.md
- [ ] 7.7 Gate 3 用户确认

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->
