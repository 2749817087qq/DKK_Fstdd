# v3.6.0 任务清单（anti-drift-gates）

> 24 TC / 6 切片 · 长程模式（full_auto）· 复杂度 12（thorough）

## 1. 判据锚点与 diff 范围修正（P0，ci-check-accuracy）

- [ ] 1.1 新增 `_iter_changed_files(change_dir, project_root, status_filter=None)` —— 从 `baseline.base_git_sha..HEAD` 取 `--name-status`，baseline 缺失时返回 `(None, reason)`
- [ ] 1.2 重写 `check_scope_creep`：数据源改 `_load_change_scope`，判据改 `_is_in_change_scope`（依赖 1.1）
- [ ] 1.3 严格度分界：有 scope → FAIL / 无 scope → WARN（依赖 1.2）
- [ ] 1.4 测试 TC-CIA-001..004（4 个，正反成对）

## 2. 范围锁核心四态与边界（P0，anti-drift-gates）

- [ ] 2.1 豁免白名单 `SCOPE_EXEMPT_PREFIXES` / `SCOPE_EXEMPT_EXACT`（依赖 1.2）
- [ ] 2.2 `_is_scope_too_broad(patterns)` 过宽检测（依赖 2.1）
- [ ] 2.3 scope.paths 含 `..` 时剔除并 WARN（依赖 2.1）
- [ ] 2.4 测试 TC-ADG-001..006（6 个）

## 3. DELIVER 冻结（P0）

- [ ] 3.1 新增 `check_deliver_freeze`：deliver + build completed 时拦 A 状态新增源文件（依赖 1.1）
- [ ] 3.2 `allow_late_change` 逃生阀 + 写 `design_adjustments`
- [ ] 3.3 backlog 未闭合项 WARN（区分本 change / 历史）
- [ ] 3.4 测试 TC-ADG-007..010、020（5 个）

## 4. 断言核实（P0）

- [ ] 4.1 新增 `check_claims`：扫 `baseline..HEAD` commit message 的 `vX.Y.Z` 与 version.yaml 比对
- [ ] 4.2 测试 TC-ADG-011..012（2 个）

## 5. evidence 事实标签（P0）

- [ ] 5.1 `utils.has_fact_tag(text)` 单一判据（`[F]` / `[F:来源]`）
- [ ] 5.2 `gate.approve` 接入校验，缺标签拒绝 + 打印示例
- [ ] 5.3 `amend-audit` 显式豁免
- [ ] 5.4 测试 TC-ADG-015..017（3 个）

## 6. backlog 模板与 check-drift 报告（P0/P1）

- [ ] 6.1 `.fstdd/templates/backlog.md` + `upstream/.fstdd/templates/backlog.md`（双份逐字节一致）
- [ ] 6.2 proposal 模板增 `scope:` 段（双份一致）
- [ ] 6.3 skill 增反漂移硬规则章节（build.md / deliver.md 双份）
- [ ] 6.4 新增 `ci check-drift` 子命令（三闸聚合，`--strict` / `--json`）
- [ ] 6.5 测试 TC-ADG-013..014、018..019（4 个）

## 7. 测试与验证

- [ ] 7.1 24 个 TC 全部实现且正反成对
- [ ] 7.2 全量 `pytest upstream/tests tests` 0 failed
- [ ] 7.3 `ci check-failures` 0 FAIL
- [ ] 7.4 四自检脚本全绿

<!--
依赖：1 → 2 → 3；4 独立；5 独立；6.4 依赖 1/2/3/4
P0：1/2/3/4/5/6；P1：6.4 的 --strict 分支
-->
