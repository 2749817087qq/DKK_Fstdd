# 任务清单 — 2026-10-18-share-egress-closure

> 按 8 个提交倒推的执行单元。每项均已在 `test-report.md` 留有验证证据。

## T1 出站收口统一到 `_prepare_outbound()`

- [x] 新增 `_verify_outbound()` / `_prepare_outbound()` / `_audit_skipped()`
- [x] 四个包装器改走 `_prepare_outbound`（scp / inbox / github / pr）
- [x] `pre_staged` 语义改为「只跳过脱敏动作」
- [x] 删掉 `:1225` 的假注释
- 提交：`45d077a`

## T2 出站守卫抽为独立模块

- [x] `tools/pytest_egress_guard.py`（规则唯一事实源）
- [x] `tests/conftest.py` + `upstream/tests/conftest.py` 模块导入期 `install()`
- [x] 幂等靠函数属性；计数挂函数上使两侧共享
- 提交：`2d89223`

## T3 脱敏规则收敛 + 静默开关健壮

- [x] 删除 `_exp_sync._SANITIZE_RULES` 弱化副本（置 None）
- [x] `_load_canonical_sanitizer()` 按路径加载，找不到抛错不降级
- [x] `_share_disabled()` 补 `UnicodeDecodeError`
- [x] 新增 `_looks_like_project()` / `_find_project_root()`
- 提交：`e449900`

## T4 文档同步（三档通道 / 审计分流 / 共享枢纽）

- [x] `docs/WORKBUDDY_INSTALL_NOTES.md` §3
- [x] `README.md` §经验回传
- [x] `.fstdd/config.d/experience.yaml` 注释
- 提交：`00061ab`

## T5 门禁收口（PEM 字面量 + skill 模板）

- [x] `test_exp_sync_sanitize_parity.py` 的 PEM 头改运行时拼接
- [x] skill 模板同步三档策略
- 提交：`1e16df2`

## T6 P0/P1 修复（6 维审计行动项）

- [x] P0-1 残余判据补 4 类形态（**不加通用外网域名**）
- [x] P0-2 `publish()` 入口单次校验 + `prepared=True` 直通
- [x] M4 新增 `PUBLISH_SENT_COUNT` + 审计字段 `sent_count`
- [x] M3 `record_audit` 加跨进程写锁
- [x] D5-03 三处 print 套 `_scrub`
- [x] L1 `sanitized:false` 改用 `parse_frontmatter()`
- [x] 文档口径：三个→四个包装器、SUBMIT 两条→三档
- 提交：`157752d`

## T7 守卫加固 + 覆盖补齐

- [x] `_normalize_args()`（`shlex.split`）+ `_prog_name()`（剥 `.exe`）
- [x] 包 `run` + `call`（放弃 `Popen`，见 ADJ-001）
- [x] 新增仓库根 `conftest.py`（覆盖 `tools/tests/`）
- [x] upstream conftest 补 `pytest_sessionfinish`
- 提交：`70a1af4`

## T8 CHANGELOG + 规则条数更正

- [x] `[Unreleased]` 补完整条目
- [x] 「14 条」→「15 条」四处
- 提交：`ab79632`

---

## 遗留（不在本 change 范围）

- [ ] `collect_local()` 加「已分享」水位线（当前每轮重传全库 89 条）
- [ ] 并发写锁的自动化用例（TC-CLOSURE-008 仅人工探针）
- [ ] 守卫补 `Popen` 直接调用（受 asyncio 继承限制，需换实现思路）
- [ ] `fstdd-inbox` 批次 → 待审核池的摄取脚本（D5-05）
