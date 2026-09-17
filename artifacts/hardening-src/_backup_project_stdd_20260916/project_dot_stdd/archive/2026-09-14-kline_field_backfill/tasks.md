# Tasks: kline_field_backfill

> STDD Phase 3 实现任务清单 | 2026-09-14
> 状态标记：`[x]` 已完成并验证 ｜ `[~]` 已实现待验证 ｜ `[ ]` 未开始
> **执行期新增/变更的任务以 `[+]` 标注**（详见 design-adjustments.yaml ADJ-001..010）

## S1｜日历与计划层（纯函数）

- [x] T1.1 建 `repair_kline_fields.py` 骨架：docstring（背景/公式/用法）、常量、`load_env()`、`connect()`
- [x] T1.2 `load_calendar(conn)` → `(calendar:set[str], max_date:str)`；空日历抛错中止（SC-001-002）
- [x] T1.3 `load_amount_source(conn)` → `dict[(code,date)] -> amount`
- [x] T1.4 `plan_purge(kline, calendar, max_date)` → `(to_delete, warn)`；三重守卫（SC-004-001/002/003）
- [x] T1.5 `plan_return_fills(kline, calendar, exclude)` → 未复权公式；排除幽灵键（SC-002-001/004）
- [x] T1.6 `plan_amount_fills(kline, src_map, exclude)` → `(fills, unresolved)`（SC-003-001/002）
- [x] T1.7 `build_plan(doc, calendar, max_date, src_map)` → 联合计划（purge 先算，fill 排除 purge 键）
- [x] T1.8 写 `.stdd/agent_tests/test_kline_field_backfill.py` 的 S1 部分（6 TC）→ **RED**
- [x] T1.9 跑测试确认 RED，再实现至 **GREEN**（6/6，另附 TC-KFB-009a 幽灵日守卫补充断言）
- [+] T1.10 【执行期】`load_pg_kline()` / `plan_pg_purge()`：PG 侧独立重放三重守卫（SC-006-003，ADJ-001）
- [+] T1.11 【执行期】`_normalize_dates()`：归一 `[(code,date)]` 与 `['date']` 两种形状（ADJ-002）
- [+] T1.12 【执行期】`pg_field_gap()`：PG 侧「可回填」行数，供早退判定（ADJ-008）

## S2｜JSON 写入层

- [x] T2.1 `apply_to_json(doc, path, plan, backups_dir)`：备份原文件 → 原地变更 → tmp + os.replace（SC-005-001）
- [x] T2.2 `write_purge_backup(rows, backups_dir)` → `backups/phantom_<ts>.csv`（11 列）（SC-004-004）
- [x] T2.3 `update_coverage(doc, plan)` → 5 个新字段 + 保留既有字段（SC-005-002）
- [x] T2.4 `main()` argparse：默认 dry-run；`--write` / `--purge-phantom` / `--apply-pg` / `--verify` / `--daily` / `--json`
- [x] T2.5 授权门：`--write` 不含 `--purge-phantom` 时不删行并提示（SC-009-002）
- [x] T2.6 幂等：无缺口早退、不产生备份文件（SC-008-001/002）
- [x] T2.7 S2 部分测试（6 TC）→ RED → GREEN
- [+] T2.8 【执行期】`_coverage_target()` 纳入 `fund_count`：修复历史遗留 88 vs 89 不自洽（SC-005-002，ADJ-007 + 复审）
- [+] T2.9 【执行期】幂等判定 `needs_json_write` 后移到 purge 抑制之后（ADJ-008，复审 H4）
- [+] T2.10 【执行期】`main()` 重构为 `_run()` + `_finish()`，连接由 try/finally 统一关闭（复审 H1）
- [+] T2.11 【执行期】`_finish()`：`--verify` MISMATCH 在**所有**分支都以非零码失败（SC-006-002，复审 H2）

## S3｜PG 应用与一致性

- [x] T3.1 `apply_to_pg(...)`：单事务 UPDATE(daily_return_pct) + UPDATE(amount) + DELETE(幽灵行)
- [x] T3.2 `verify(conn, doc)`：三项计数 + 总行数 + 标的数一致；不一致非零退出（SC-006-002）
- [x] T3.3 S3 部分测试（只读断言）→ RED → GREEN
- [+] T3.4 【执行期】`apply_to_pg` 签名改为 `(conn, purge_dates, backups_dir, stamp)`；待删日期取自 PG 自身（ADJ-001）
- [+] T3.5 【执行期】`write_pg_purge_backup()`：PG 删前落盘 `pg_phantom_<ts>.csv`（ADJ-003）
- [+] T3.6 【执行期】`apply_to_pg` 加 try/except rollback，三项改动同生共死（复审 M3）
- [+] T3.7 【执行期】新增 TC-KFB-024（SC-006-003 回归）、TC-KFB-025（SC-006-004 三系统一致）

## S4｜编排集成

- [x] T4.1 `daily_etl.py`：`SOURCES` 新增 `repair_kline` 条目
- [x] T4.2 `daily_etl.py`：新增 `run_repair_kline()`（调 `VENV_PY repair_kline_fields.py --daily --write`）
- [x] T4.3 `daily_etl.py`：`DAILY_DEFAULT` 在 `sync_kline_json` 后、`json` 前插入 `repair_kline`
- [x] T4.4 `daily_etl.py`：主流程加 `if "repair_kline" in active:` 分支
- [x] T4.5 TC-017 测试（`--dry-run` 顺序断言）→ RED → GREEN

## S5｜一次性受控执行与结果断言（**需 D哥确认后执行**）

- [x] T5.0 向 D哥展示「将影响行数 + 备份路径」并取得执行确认（GATE2_APPROVED + UAD-001）
- [x] T5.1 `--write`（修 JSON）→ ret **+24,642** / amount **+178**
- [x] T5.2 `--purge-phantom --write`（删幽灵行；`backups/phantom_20260914_212012.csv` 行数 = 81 ✅）
- [x] T5.3 `--apply-pg --verify`（改 PG + 断言一致）→ `ret_updated 24,642 / amt_updated 178 / deleted 81`，**VERIFY OK**
- [x] T5.4 跑 `daily_etl.py`，验证修复不被 build 回滚（TC-018）
      → 第一次全 10 步运行在 `westock_ff` 阶段因**会话边界**被杀（僵尸锁 pid 19148，22:34:07 被自动接管）；
        第二次改跑 K 线链路 `--only backfill_kline sync_kline_json repair_kline json sync_duckdb`，
        `ok=5 bad=0`、`EXIT=0`；**build 未回滚修复**（`fillable_gap=0`、`phantom=0`）；
        **第三次按原范围补跑完整 10 步**（22:56:49→23:55:25，`ok=9 bad=1`，唯一红为无关的 `pre_listing`），
        `repair_kline → [SKIP] 无缺口，跳过写入（未创建任何备份文件）`，
        三系统仍为 `(51575,89,89,89,0)`，全量测试复跑 **27/27 PASS**。
        第二次运行的范围偏离已如实登记于 `design-adjustments.yaml` UAD-002 的 `actual_execution`。
- [x] T5.5 S5 部分测试（8 TC）全量断言 → GREEN（终态 `rows 51,575`）
- [x] T5.6 【VERIFY 期新增】修掉第 5 处状态依赖断言（`amount IS NULL == 0` → 可回填缺口 == 0），
      TC-007 / 015 / 018 三处改断言 → 全量复跑 **26/26 PASS**（ADJ-010 / EXP-011）
- [x] T5.7 【VERIFY 期新增】关闭 K5：6 处弱覆盖断言全部补强 + 新增 TC-KFB-016b
      → 全量复跑 **27/27 PASS**（EXP-013）

## Part C｜质量验证

- [x] C1 多路并行技术评审（代码 / 测试 / 文档 3 路）→ 12+12+11 项发现（0 Critical 于实现、3 High），已逐条处理或登记
- [x] C2 全量质量检查（测试全量跑 + pyflakes + 语法 + 调试残留 + 死代码）
- [x] C3 Diff 审查（逐文件）→ `daily_etl.py` 38 insertions / 1 deletion，与设计一致
- [x] C4 失败模式检查（12 类，standard 模式）→ 见 test-report.md
- [x] C5 经验库记录（`.stdd/experiences/kline_field_backfill.md`，EXP-001..012）
- [x] C6 汇总设计调整（`design-adjustments.yaml`，ADJ-001..010）
- [x] C7 生成 `test-report.md`（八节完整，E2E 三项计数已回填）→ **待 Gate 3 用户确认**

## 已知问题（不在本次范围，记入 test-report）

- [ ] K1 `reits_kline_daily.json` 的 `sample_stats` 已陈旧（180101 的 `last_date` 停在 2026-08-28，而 kline 已到 2026-09-14），且只覆盖 88 只。本次**不重算**（陈旧性先于本变更存在），但幽灵行删除后其 `rows` 计数会再偏 1。建议独立 slice 处理。
- [x] ~~K2 `coverage.fund_count = 88` 而 `kline` 有 89 只（既有不一致，非本次引入）。~~
      → **本次已一并修复**：`_coverage_target()` 纳入 `fund_count`，已刷新为 89（ADJ-007 延伸）。
- [ ] K3 `daily_etl.py:55` 的 `import shutil` 未使用（**预存在**，非本次引入，pyflakes 报 L 级）。
- [ ] K4 `verify()` 的幽灵日指标硬编码 `PHANTOM_HINT='2026-05-03'`。它只用于 JSON↔PG **一致性**对比（两侧同 filter，对称），
      不承担「发现新幽灵日」职责（那是 `plan_purge` + TC-009 的职责）。如未来出现第二个幽灵日，需把该项改为「非交易日行数」。
- [x] ~~K5 覆盖度弱点（复审发现，非阻塞）~~ → **本次已一并关闭**（6 处全部补强，见 test-report §七 K5 明细）：
      SC-002-003 → TC-005 增确定性 fixture；SC-003-002 → TC-008 增 stdout 文案断言；
      SC-004-002 → TC-010 增 `max_date==max(calendar)` 集成层断言；
      SC-006-002 → 新增 TC-KFB-016b（rc_bad=1 / rc_ok=0）；
      SC-008-001/002 → TC-020 增早退文案断言；SC-009-001/002 → TC-021 增 PG 计数快照、TC-022 增提示文案断言。
      复跑 **27/27 PASS**。补强中另抓出 EXP-013（「源缺失」fixture 用了源表存在的键）。
- [ ] K6 当日新行 `amount` 天然为 NULL（**非缺陷，已知行为**）：`sync_kline_json` 的 TDX 主站直连通道不产 `amount`，
      且 `tdx_kline_daily` 当日 `amount` 尚未到位 → 每天新增 89 行 NULL，次日源到位后由 `repair_kline` 自愈。
      若要当日即有值，应让 `fetch_tdx_raw` 当日 `amount` 先于 ETL 到位（源侧调度问题，不在本变更范围）。
- [ ] K7 `westock_ff` 耗时严重超预算（**实测 1520.5s = 25.3 min**，历史区间 155–737s）：
      该步为 89 只 npx 取数，若挂住会吃掉 40 min（`WESTOCK_FF_TIMEOUT=2400`）× 最多 2 次尝试。
      它位于 `repair_kline` **之前**，一旦超时重试会显著推迟每日修复的生效时间。
      建议：单独排期观察/优化（并发度、超时预算、失败快速跳过），**不在本变更范围**。
- [ ] K8 `pre_listing` 在完整 ETL 中 `rc=1`：`[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]
      {"count":195,"threshold":195,"scope":"turn"}` —— safe-delete 安全策略拦截一次性批量删除 195 个文件
      （属**保护机制正常工作**，非缺陷）。不影响任何 K 线数据，但会让 ETL 发失败告警邮件。
      属 `pre_listing_daily.py` + safe-delete 策略范围，建议单独排期，**不在本变更范围**。
