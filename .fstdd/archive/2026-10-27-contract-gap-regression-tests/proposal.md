# contract_gap 三类模式回归测试加固

<!-- source_hash: 7955140c90387629 -->
<!-- generated_at: 2026-10-27T02:43:14+00:00 -->
<!-- canonical: canonical/proposals/2026-10-27-contract-gap-regression-tests.yaml -->

## Why

经验库沉淀的 3 条 contract_gap 类 high 经验（EXP-2026-0027 / EXP-2026-0031 /
EXP-2026-0032）都描述了已被代码修复的攻击向量，但**尚无回归测试保护**：
  - EXP-2026-0027: 词法前缀比较判定路径安全（archive 守卫）；已被 `finder.py`
    的 `resolve().relative_to()` + `_resolve_in` 拒绝分隔符修复。
  - EXP-2026-0031: Python 3.11+ 内联 `(?i)` 在多段拼接 regex 中导致 import 崩溃；
    全仓 grep 已 0 残留。
  - EXP-2026-0032: 字符白名单 `[\w./-]+` 允许 `..` 组合逃逸；已被
    `_resolve_in` 的 `Path(name).parts` 段级判据修复。
当前状态：代码修复完成但**无测试锁定** —— 未来重构或新增守卫入口时，任何一处
回退都会静默复活攻击向量。3 条经验因此一直停留在 discovered 生命周期，无法归档。


## What Changes

- 新增 tests/test_contract_gap_regression.py：针对 3 类攻击向量各写 2-3 个用例，
直接调用 finder._resolve_in / 模拟 archive 守卫入口 / 验证 (?i) 拒绝策略。

- 用 parametrize 覆盖 `..`、绝对路径、跨盘符、含 `.` 后缀、Unicode 分隔符等形态；
正例（合法 change 名必须放行）与反例（各种逃逸）成对断言。

- 把 3 条经验 lifecycle_state 从 discovered 推进到 verified（用 `stdd experience
verify` 命令或人工在 frontmatter 里改字段）。

- 在 CI 新增一条 grep 门禁，把「`(?i)` 内联出现在拼接 regex 中」列入 check-failures
检查项（防御未来重犯）。


## Capabilities

### New Capabilities


### Modified Capabilities

- **contract-gap-regression-tests**：新增回归测试套件，锁定 3 类 contract_gap 攻击向量已被挡住：
  - `_resolve_in` 拒绝含分隔符/`..`/绝对路径的 name
  - archive 守卫用 `resolve().relative_to()` 归一化判定
  - 全仓无内联 `(?i)` 拼接 regex


## Success Criteria

- [ ] 新增 tests/test_contract_gap_regression.py 至少 8 个用例，全部通过
- [ ] 3 条经验（EXP-2026-0027/0031/0032）lifecycle_state 推进为 verified
- [ ] ci check-failures 门禁 0 FAIL
- [ ] 全量 pytest 0 failed
- [ ] TDD 用例编号登记在 test-plan.md，形如 TC-CGR-001..TC-CGR-0NN
