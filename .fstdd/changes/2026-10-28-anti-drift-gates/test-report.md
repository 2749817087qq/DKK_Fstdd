# v3.6.0 测试报告（anti-drift-gates）

> change: `2026-10-28-anti-drift-gates`
> 执行模式：长程（full_auto）· 复杂度 12（thorough）
> 报告生成：2026-10-28

## 一、TC 覆盖率

| 指标 | 值 |
|---|---|
| 计划 TC（test-plan.md） | **24** |
| 实际实现 TC | **24** |
| 覆盖率 | **100%** |
| 新增测试函数 | 31（含参数化展开后 31 个 test 节点） |
| 新增测试文件 | 1（`upstream/tests/test_anti_drift_gates.py`） |

### TC ↔ 测试函数映射

| TC | 测试函数 | 状态 |
|---|---|---|
| TC-ADG-001 | `test_TC_ADG_001_out_of_scope_fails` | ✅ |
| TC-ADG-002 | `test_TC_ADG_002_in_scope_passes` | ✅ |
| TC-ADG-003 | `test_TC_ADG_003_no_scope_warns` | ✅ |
| TC-ADG-004 | `test_TC_ADG_004_strict_promotes_warn` | ✅ |
| TC-ADG-005 | `test_TC_ADG_005_scope_too_broad`（3 组参数） | ✅ |
| TC-ADG-005b | `test_TC_ADG_005b_degenerate_scope_is_warn`（2 组） | ✅ |
| TC-ADG-006 | `test_TC_ADG_006_dotdot_pattern_dropped` | ✅ |
| TC-ADG-007 | `test_TC_ADG_007_new_source_fails` | ✅ |
| TC-ADG-008 | `test_TC_ADG_008_modify_only_passes` | ✅ |
| TC-ADG-009 | `test_TC_ADG_009_allow_late_change_passes` | ✅ |
| TC-ADG-010 | `test_TC_ADG_010_fstdd_new_file_exempt` | ✅ |
| TC-ADG-011 | `test_TC_ADG_011_version_mismatch_fails` | ✅ |
| TC-ADG-012 | `test_TC_ADG_012_consistent_or_absent_passes`（2 组） | ✅ |
| TC-ADG-013 | `test_TC_ADG_013_three_sections` + `test_TC_ADG_013b_fail_exits_nonzero` | ✅ |
| TC-ADG-014 | `test_TC_ADG_014_json_output` | ✅ |
| TC-ADG-015 | `test_TC_ADG_015_missing_tag_rejected` | ✅ |
| TC-ADG-016 | `test_TC_ADG_016_with_tag_passes` | ✅ |
| TC-ADG-017 | `test_TC_ADG_017_amend_audit_not_constrained` | ✅ |
| TC-ADG-018 | `test_TC_ADG_018_backlog_template_identical` + `test_TC_ADG_018b_proposal_template_has_scope` | ✅ |
| TC-ADG-019 | `test_TC_ADG_019_new_does_not_create_discoveries` | ✅ |
| TC-ADG-020 | `test_TC_ADG_020_backlog_open_warns` | ✅ |
| TC-CIA-001 | `test_TC_CIA_001_anchor_not_capname` | ✅ |
| TC-CIA-002 | `test_TC_CIA_002_multi_commit` | ✅ |
| TC-CIA-003 | `test_TC_CIA_003_no_baseline_no_crash` | ✅ |
| TC-CIA-004 | `test_TC_CIA_004_baseline_over_head1` | ✅ |

## 二、切片验证状态

| 切片 | 内容 | TC 数 | 状态 | 关键验证 |
|---|---|---|---|---|
| S1 | 判据锚点与 diff 范围修正 | 4 | ✅ done | 旧实现返回 SKIP（只找 proposal.md），新实现读 canonical YAML |
| S2 | 范围锁四态与边界 | 6 | ✅ done | 过宽检测 3 组、`..` 剔除、退化 scope |
| S3 | DELIVER 冻结 | 5 | ✅ done | A 拦 / M 放、逃生阀回显理由、`.fstdd/` 豁免 |
| S4 | 断言核实 | 2 | ✅ done | 版本矛盾列出两处值 |
| S5 | evidence 事实标签 | 3 | ✅ done | 拒绝是原子的（Gate 未被写入） |
| S6 | check-drift 报告 + 模板 | 5 | ✅ done | 三节输出、strict 升格、双份逐字节一致 |

## 三、失败模式检查（23 类）

| # | 失败模式 | 结果 | 说明 |
|---|---|---|---|
| 1 | 幻觉调用 | ✅ | 新代码无未 import 符号；`_load_change_scope` / `_is_in_change_scope` 从 guard 显式 import |
| 2 | 过度信任 LLM | ✅ | 每条判据都有反例测试（不是只跑 happy path） |
| 3 | Prompt 注入 | SKIPPED | 本 change 不涉及 prompt |
| 4 | 记忆污染 | ✅ | 实测踩到（凭记忆断言版本号），已由 `check_claims` 机制化拦截 |
| 5 | 上下文窗溢出 | ✅ | 单次 Edit 均 < 300 行 |
| 6 | 工具参数漂移 | ✅ | `check-drift` 的 argparse 参数与 `cmd_check_drift` 读取字段一致 |
| 7 | 安全凭证泄露 | ✅ | 无 token/key 硬编码；测试用 tmp 仓库 |
| 8 | 权限绕过 | ✅ | 未手改 `.fstdd.yaml` 确认字段；Gate 走 CLI |
| 9 | 并发竞态 | ✅ | `_iter_changed_files` 只读 git，无写竞态 |
| 10 | 路径遍历 | ✅ | `_sanitize_scope_patterns` 剔除 `..`（EXP-2026-0027）；`_is_in_change_scope` 已 resolve 归一化 |
| 11 | 跨会话残留 | ✅ | 临时脚本已删；`tmp-ci-junit.xml` 在仓库外 |
| 12 | 输出截断 | ✅ | — |
| 13 | 格式错误 | ✅ | 所有 YAML 均 safe_load 验证通过 |
| 14 | 循环依赖 | ✅ | `ci.py → guard.py` 单向；guard 不 import ci |
| 15-22 | 金融 7 红线（重复扣款/账实/降级/精度/审计/状态机/额度/合规） | SKIPPED | 非金融 change |
| 23 | 过度工程 | ✅ | YAGNI-7 逐级：① 真需要（D哥 明确反馈漂移）② 本仓已有（`_load_change_scope` / `_is_in_change_scope` 复用，未新造）③ 标准库（`subprocess` / `re`）④ 平台原生（git）⑤ 已装依赖（PyYAML）⇒ 停在② |

## 四、设计偏离

| # | 偏离 | 原因 | 影响 |
|---|---|---|---|
| ADJ-001 | `_iter_changed_files` 从 `git diff <sha>..HEAD` 改为 `git diff <sha>` + `git status` 补 untracked | BUILD 期实测：用 `..HEAD` 时闸2 恒报「0 个改动文件」（改动都在工作区未提交）⇒ 自查形同虚设 | 正面：BUILD 期范围锁真正生效。已在函数 docstring 记录实测依据 |
| ADJ-002 | evidence 标签校验对 `--confirmed-by file_token` 豁免 | 首版实现后 14 个既有 gate 测试失败；file_token 是机械通道，token 文件本身即凭据 | 正面：既有机调用方不受影响；dialog/cli 通道仍强制 |
| ADJ-003 | 既有 `test_scope_creep_pass` / `test_scope_creep_skip_no_capability_declared` 断言更新 | 二者断言的正是 C1 要废弃的旧行为（SKIP）；SC-ADG-003 明确要求 WARN | 必要：被测行为已变，测试须同步 |
| ADJ-004 | 既有 gate 测试夹具默认 evidence 加 `[F:test-fixture]` | 默认空串被 C5 拒绝（符合设计意图：空串更不算证据） | 必要：夹具提供合法默认值，标签校验本身由专项测试覆盖 |
| ADJ-005 | `.fstdd/skills/deliver.md` 顺手去掉 BOM | 双份 cmp 从第 1 字节就 differ，根因是 BOM | 正面：消除一处假差异；第 41 行既存内容漂移已记 backlog |
| ADJ-006 | proposal 的 `scope.paths` 补 2 条（`cli/__init__.py` / `test_gate.py`） | **范围锁第一次真实拦截**：它抓出我改过但漏声明的 2 个文件 | 正面：机制有效性实证。不改需求，只补范围声明 |

## 五、质量数据

| 项 | 值 |
|---|---|
| 新增/修改测试（3 文件） | 84 passed / 0 failed |
| 全量门禁 | 见下节「全量结果」 |
| `ci check-drift` 自查 | 闸1 PASS · 闸2 PASS（14 条 scope / 26 个改动文件）· 闸3 SKIP（未到 deliver） |
| 四自检 | 见下节 |

## 六、已知问题与未闭合项

| # | 项 | 原因 | 影响 | 计划 |
|---|---|---|---|---|
| 1 | `extract-proposal` 把多行 description 切碎 | 解析器按行切而非按 YAML 列表项聚合 | `what_changes` 从 8 项变 11 碎片 | 已记 backlog，另立 change |
| 2 | `build.md` 双份既存 21 行漂移 | v3.2.0 DA-10 遗留 | 双份内容不一致 | 已记 backlog |
| 3 | `deliver.md` 第 41 行仍有一处差异 | 既存内容漂移 | 同上 | 已记 backlog |
| 4 | 检查项编号 (m) 空缺 | 本轮新增用了 (n)/(o)/(p) | 编号不连续 | 已记 backlog |
| 5 | 单检查子命令无 `--strict` | 与 `check-drift --strict` 口径不统一 | 无实际影响 | 已记 backlog |

## 七、全量结果

（待全量门禁完成后填入）
