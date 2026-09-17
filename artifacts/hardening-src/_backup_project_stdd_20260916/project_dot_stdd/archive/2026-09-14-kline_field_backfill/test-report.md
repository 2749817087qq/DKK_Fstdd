# kline_field_backfill 测试报告

> 测试日期：2026-09-14
> 测试环境：Windows / Python 3.13.12（隔离 venv `C:\Users\Administrator\.workbuddy\binaries\python\envs\default`）/ psycopg2-binary 2.9.13 / duckdb 1.5.5
> 被测变更：STDD `kline_field_backfill`（`reits_kline_daily` 字段级回填 + 非交易日脏行清理）
> 被测版本：工作区当前状态（该仓库未对本次变更提交 commit）
> 对应规格：`.stdd/changes/kline_field_backfill/spec.yaml`（18 Requirements / 24 Scenarios）
> 对应测试方案：`.stdd/changes/kline_field_backfill/test-plan.md`（25 TC）

---

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 测试项总数 | **27**（25 个 TC 编号；TC-KFB-009 拆为 S1 的 `009a` 与 S5 的 `009`，另加 K5 补强的 `016b`） |
| 通过 | **27**（S1 7 / S2 6 / S3 5 / S4 1 / S5 8） |
| 失败 | **0** |
| 跳过 | 0 |
| 通过率 | **100%**（`RESULT: PASS — 27/27 全部通过`，退出码 0） |
| 执行方式 | `python .stdd/agent_tests/test_kline_field_backfill.py [--group S1..S5]` |
| 权威日志 | `logs/stdd_kfb_tests_k5_20260914.log`（K5 补强后终态）；`logs/stdd_kfb_tests_20260914.log`（补强前 26/26） |
| 测试脚本是否写生产数据 | **否**。S2 用 `tempfile.mkdtemp()` 副本；TC-021 用真实 JSON 但为 dry-run 只读（并比对 PG 计数快照）；S3/S5 全部为只读 SELECT |

> **K5 补强（本次一并关闭）**：原登记的 6 处弱覆盖断言已全部改为实质断言，详见 §7.2。
> 补强后测试项由 26 增至 27（新增 `TC-KFB-016b`：MISMATCH 非零退出），其余为在既有 TC 内
> 增加实质断言（stdout 文案捕获 / PG 计数快照 / 确定性 fixture），编号不变。

### 1.1 覆盖率诊断（仅变更文件）

> 覆盖率仅作诊断参考，不作为通过/失败门禁。

| 变更文件 | 测试覆盖方式 | 状态 |
|----------|-------------|------|
| `repair_kline_fields.py`（新建，约 660 行） | 直接 import 调用纯函数 + 假连接单元断言 + 真实 PG 只读断言 | ✅ 全部公开函数被至少 1 个 TC 调用 |
| `daily_etl.py`（+38 / −1 行） | 源码文本解析（TC-017 断言 `DAILY_DEFAULT` 顺序） | ✅ 变更面 100% |
| `.stdd/agent_tests/test_kline_field_backfill.py` | 自身即测试件 | N/A |

**未覆盖/弱覆盖说明**：
- `write_pg_purge_backup()` 的真实落盘路径由 TC-024 间接验证（检查 `backups/pg_phantom_*.csv` 存在且 81 行 × 11 列），未在临时目录重放。
- `_finish()` 的 MISMATCH → 非零退出路径未直接断言 rc（见 §五-B 与 §七 K5）。

---

## 二、按切片统计

| 切片 | 模块 | 用例数 | 通过 | 失败 | 说明 |
|------|------|--------|------|------|------|
| S1 | 日历与计划层（纯函数） | 7 | 7 | 0 | 三重守卫 / 空日历中止 / 首行不填 / 幽灵日不进 prev_close 链 / 无源 amount 报告（含文案）/ 最新一天不误删 / 只告警不删 |
| S2 | JSON 写入层（临时副本） | 6 | 6 | 0 | 原子写 + 写前备份 + 无残留 .tmp / coverage 自洽 / 幂等 / 无缺口零备份（含文案）/ 默认 dry-run 零副作用（JSON+PG）/ 无授权不删（含提示） |
| S3 | PG 应用与一致性（只读） | 5 | 5 | 0 | 无可回填缺口 / JSON↔PG 五项一致 / **MISMATCH 非零退出** / PG 侧独立推导 / 三系统一致 |
| S4 | 编排集成 | 1 | 1 | 0 | `sync_kline_json < repair_kline < json` |
| S5 | 执行结果断言（只读） | 8 | 8 | 0 | 全量重算一致 / 厂商值未改写（含确定性 fixture）/ amount 逐行相等 / 备份完整性 / 除息语义 / build 后不回滚 |
| **合计** | | **27** | **27** | **0** | **通过率 100%** |

> 用例数与 `test-plan.md` 的 25 TC 差 2，原因：TC-KFB-009 在 S1（`009a`）与 S5（`009`）各有一处
> 独立断言；`TC-KFB-016b` 为 K5 补强项（SC-006-002），编号挂在 016 之下。测试计划按 25 个编号计。

### 2.1 关键 TC 实测输出（终态，2026-09-14 23:1x，`logs/stdd_kfb_tests_k5_20260914.log`）

```
[PASS] TC-KFB-001 日历取数 + 无周末行              -> len=1272 max=2026-09-14 weekend=0
[PASS] TC-KFB-002 空日历保护性中止                 -> raised=True
[PASS] TC-KFB-006 幽灵日不参与收益率回填 + 计划数=24,642 -> fixture_ok=True ret_fills=0 j_ret_null=89 funds=89 phantom=False
[PASS] TC-KFB-008 无源 amount 显式报告（数据层+输出文案）-> fills=0 unresolved=[('999999','1999-01-04')] rc=0 text_ok=True
[PASS] TC-KFB-010 最新一天不被误删（含 max_date==max(calendar) 集成层）
                                                    -> del=[] warn={'2026-09-12':1} max_eq=True cal_max=2026-09-14
[PASS] TC-KFB-011 未分类非交易日行只告警不删          -> del=[] warn={'2024-10-02': 1}
[PASS] TC-KFB-009a 幽灵日命中删除条件（周末+逐行重复） -> del=[('180101','2026-05-03')] warn={}
[PASS] TC-KFB-021 默认 dry-run 零副作用（JSON + PG）  -> rc=0 hash_same=True pg_same=True pg=(51575,89,89,0)
[PASS] TC-KFB-022 不带 --purge-phantom 时幽灵行保留 + 输出提示 -> rc=0 hint=True
[PASS] TC-KFB-013 原子写 + 写前备份 + 无残留 .tmp    -> json_bak=2 no_tmp=True parse=True
[PASS] TC-KFB-014 coverage 记录口径 + 既有字段自洽   -> missing=set() caliber=unadjusted total_records=3 actual=3
                                                      fund_count=1 actual_funds=1 date_range 一致
[PASS] TC-KFB-019 二次执行逐字节一致（幂等）          -> hash_same=True bak 3->3 rc=0
[PASS] TC-KFB-020 无缺口不产生备份文件 + 早退文案     -> bak 3 -> 3 rc=0 skip=True nover=True
[PASS] TC-KFB-015 无可回填缺口（ret_null=89 首行 / phantom=0 / gap=0）
                                                    -> ret_null=89 amt_null=89(含无源) phantom=0 funds=89 fillable_gap=0
[PASS] TC-KFB-016 JSON↔PG 五项计数一致              -> json=(51575,89,89,0) pg=(51575,89,89,0)
[PASS] TC-KFB-016b MISMATCH 非零退出 / OK 零退出（SC-006-002）
                                                    -> rc_bad=1 MISMATCH_in_out=True rc_ok=0 OK_in_out=True
[PASS] TC-KFB-024 PG 侧待删日期独立推导              -> unit_ok/norm_ok/shape_ok/bak_ok/state_ok 全 True
                                                      bak=pg_phantom_20260914_212712.csv rows=81
[PASS] TC-KFB-025 三系统一致 JSON↔PG↔DuckDB         -> json=(51575,89,89,0) pg=(51575,89,89,0) duckdb=(51575,89,89,0)
[PASS] TC-KFB-017 编排顺序 sync_kline_json < repair_kline < json -> DAILY_DEFAULT 顺序正确
[PASS] TC-KFB-003 全量收益率与独立重算一致           -> checked=51486 mismatches=0
[PASS] TC-KFB-004 NULL 行数=标的数 且全为首行        -> n_null=89 firsts=89 funds=89
[PASS] TC-KFB-005 厂商已有值未被改写（确定性 fixture + 全量公式对撞）
                                                    -> fixture_not_replanned=True sina_deviations=0
[PASS] TC-KFB-007 amount 无可回填缺口 且与源逐行相等  -> amt_null=89(含无源) amt_gap=0 matched=178/178
[PASS] TC-KFB-009 幽灵日零行 + PG行数==JSON行数      -> phantom=0 rows=51575 json_rows=51575
[PASS] TC-KFB-012 幽灵行备份 CSV 11 列 / 81 行       -> phantom_20260914_212012.csv rows=81 missing=set()
[PASS] TC-KFB-023 |涨跌幅|>10% 的行全部可解释        -> n_big=5 n_exdiv=4 unexplained=0 uncorroborated=0
                                                      extra=[('508080','2025-06-27',10.0113,2)]
[PASS] TC-KFB-018 完整 build 后仍无可回填缺口（gap=0） -> ret_null=89 amt_null=89(含无源) phantom=0 fillable_gap=0
```

---

## 三、E2E / 端到端验证结果

> 本变更的 E2E = **完整跑一次 `daily_etl.py`**（D哥在 S5 授权门明确选择「完整 daily_etl」而非仅跑 build 子集）。
> 目的：验证修复不被紧随的 `json`(build) 的 `CREATE OR REPLACE` 回滚（TC-KFB-018），
> 并把修复传播到 DuckDB 副本（TC-KFB-025）。

### 3.1 执行计划（`DAILY_DEFAULT` 全 10 步）

| 步 | 名称 | 与本次修复的关系 |
|---|---|---|
| 1 | `ccreits` | 无关（业务元数据） |
| 2 | `westock_ff` | 无关（资金流） |
| 3 | `backfill_kline` | **关键**：补 `reits_kline_daily` 缺失行（只补缺失键） |
| 4 | `sync_kline_json` | **关键**：主站直连补 `reits_kline_daily.json` 缺失 (code,date) |
| 5 | `repair_kline` | **本次新增步**：字段级回填 + 脏行清理（只写 JSON） |
| 6 | `json`（build） | **关键**：`CREATE OR REPLACE` 把 JSON 传播到 PG（回滚风险点） |
| 7 | `sync_duckdb` | **关键**：PG → DuckDB 副本（三系统一致的传播点） |
| 8 | `pk_guard` | 无关 |
| 9 | `ann` | 无关（公告抓取，近 7 天窗口） |
| 10 | `pre_listing` | 无关（上市前材料增量） |

### 3.2 执行结果

**第一次运行（21:29:33 启动，未跑完）**

| 指标 | 数值 |
|------|------|
| 启动时间 | 2026-09-14 21:29:33 |
| 运行锁 | 获取成功（pid 19148）；**并发防护已实测**：第二个实例被锁挡住并 `[SKIP] 退出 |
| 写前全库备份 | `backups/pg_reits.bak.20260914_212933.dump`（21:32:09 完成） |
| 日志 | `logs/stdd_kfb_fulletl_20260914.log` |
| 结果 | **未跑完**：主进程与子进程在 `westock_ff` 阶段因**会话边界**被终止（日志停在 21:32:14；锁文件 pid=19148 已成僵尸锁，22:34:07 被下一轮自动接管并打印 `发现残留运行锁(pid=19148, ...): 进程已不存在, 本次接管`） |

> 归因说明：`westock_ff` = 89 只串行 npx 取数（预算 `WESTOCK_FF_TIMEOUT=2400s` × 最多 2 次尝试），
> 属已知长跑步骤，**不是**脚本缺陷；`run_cmd` 用 `communicate()` 全缓冲，日志只在每步结束时刷出，
> 故长步骤期间无法从日志观察进度。僵尸锁被自动接管这一点本身构成对编排层治理的正向验证。

**第二次运行（22:34:07 启动，已完成）**

| 指标 | 数值 |
|------|------|
| 启动时间 | 2026-09-14 22:34:07（pid 18128） |
| 实际范围 | `--only backfill_kline sync_kline_json repair_kline json sync_duckdb`（**K 线相关链路**） |
| 日志 | `logs/stdd_kfb_klinechain_20260914.log` |
| 写前全库备份 | `backups/pg_reits.bak.20260914_223407.dump` |
| 结果 | `完毕: ok=5 bad=0 total=5`，`EXIT=0` |

**第三次运行（22:56:49 启动，完整 10 步，已完成）**

| 指标 | 数值 |
|------|------|
| 启动 / 结束 | 2026-09-14 22:56:49 → 23:55:25（约 58.6 min，pid 25340） |
| 范围 | **完整 `daily_etl.py`（`DAILY_DEFAULT` 全 10 步）** —— 兑现 D哥在 S5 授权门的原始选择 |
| 日志 | `logs/stdd_kfb_fulletl2_20260914.log` |
| 写前全库备份 | `backups/pg_reits.bak.20260914_225649.dump` |
| 结果 | **`完毕: ok=9 bad=1 total=10`**，`EXIT=0`；唯一红为 `pre_listing`（与本变更无关，见下） |

| 步 | 耗时 | 实测输出 | 对本次修复的意义 |
|---|---|---|---|
| `ccreits` | 2.3s | `funds=94; meta_records=0` | 无关 |
| `westock_ff(2026-09-13)` | **1520.5s（25.3 min）** | `rc=0` | 无关，但见 **K7**（远超历史 155–737s） |
| `backfill_kline` | 4.5s | 0 行 | 无缺失键 |
| `sync_kline_json` | 93.6s | `tdx_kline_daily 51,575` / `直连新增 0 键` / `JSON 缺失 (code,date): 0` / **`无缺口，退出`** | 第二次运行已补齐，本次无新键 |
| **`repair_kline`** | **2.0s** | **`[SKIP] 无缺口，跳过写入（未创建任何备份文件）。`** | ★ **稳态幂等实测**：无缺口 → 零写入、零备份 |
| `json`(build) | 36.4s | `subprocess rc = 0` | **回滚风险点**：`CREATE OR REPLACE` 未回滚修复 |
| `sync_duckdb` | 363.9s | `完毕: total=56 fail=0 pruned=0` | 传播到 DuckDB 副本 |
| `pk_guard` | 4.7s | `8/8 表可安全加主键` | 无关 |
| `ann` | 336.0s | `rc=0` | 无关 |
| `pre_listing` | 1030.9s | **`FAIL rc=1`** | 无关；被 safe-delete 批量确认阈值拦下（见 K8） |

> **`repair_kline` 的 `[SKIP]` 是本变更最有说服力的一次证据**：在真实编排里、在 `sync_kline_json`
> 刚跑完之后，它判定「无缺口」并**一个文件都没写** —— 证明「无缺口即早退且不产生备份」这条
> 幂等性设计在集成层成立（对应 TC-019 / TC-020）。`backups/` 中 `reits_kline_daily_*.json`
> 数量在本次运行前后**未增加**，可独立复核。

> **`pre_listing` 失败的归因（与本变更无关）**：该步在 OCR 完 4/5 份 PDF 后触发
> `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {"count":195,"threshold":195,"scope":"turn"}` ——
> 这是 safe-delete 安全策略在**拦截一次性批量删除 195 个文件**，属**保护机制正常工作**，
> 而非数据或代码缺陷。已登记为 K8，建议单独排期（属 `pre_listing_daily.py` + safe-delete 策略范围）。

**范围偏离声明（现已闭合）**：D哥在 S5 授权门选的是「完整 daily_etl」（全 10 步）。
第一次全量运行在会话边界被杀 → 第二次改跑 K 线链路 5 步（结论等价）→ **第三次已按原范围
补跑完整 10 步并全部完成**。三次运行的结论完全一致：**build 未回滚修复，三系统逐项相等**。

**第二次运行的分步结果（关键路径）**

| 步 | 耗时 | 实测输出 | 意义 |
|---|---|---|---|
| `backfill_kline` | 14.0s | `已插入 0 行` | 无缺失键 |
| `sync_kline_json` | 110.6s | `已补入 89 行 -> reits_kline_daily.json` | **真实生产场景**：TDX 主站直连补入 2026-09-14 当日新行，`amount` 全为 None |
| `repair_kline` | 7.2s | `[JSON] daily_return_pct +89 / amount +0 / 删除 0 行`；`amount 无源: ... 另有 79 行` | **修复按设计工作**：新行收益率立刻补齐；amount 因当日源未到位而**拒绝编造** |
| `json`（build） | 108.0s | `subprocess rc = 0` | **回滚风险点**：`CREATE OR REPLACE` 未回滚修复 |
| `sync_duckdb` | 456.1s | `完毕: total=56 fail=0 pruned=0` | 传播到 DuckDB 副本 |

### 3.3 E2E 关键路径结果

| 路径 | 状态 | 证据 |
|------|------|------|
| 写前全库备份 | ✅ | `pg_reits.bak.20260914_212933.dump` / `..._223407.dump` / `..._225649.dump` |
| 并发防护（运行锁） | ✅ | 第二实例输出 `[SKIP] 已有实例在运行: {'status':'busy','pid':19148}` |
| 僵尸锁自动接管 | ✅ | 第二次运行日志 `发现残留运行锁(pid=19148, started=2026-09-14T21:29:33): 进程已不存在, 本次接管` |
| `repair_kline` 步接入编排 | ✅ | TC-017 断言顺序 `sync_kline_json < repair_kline < json` |
| 新增交易日行被自动补收益率 | ✅ | `sync_kline_json +89 行` → `repair_kline daily_return_pct +89`（第二次运行） |
| **稳态幂等（无缺口零写入零备份）** | ✅ | 第三次运行 `repair_kline → [SKIP] 无缺口，跳过写入（未创建任何备份文件）`；`backups/` 无新增 |
| build 后修复不被回滚（TC-018） | ✅ | 见 §3.4 |
| 三系统一致（TC-025） | ✅ | 见 §3.4 |

### 3.4 E2E 结论

**build 未回滚修复，三系统完全一致。** 终态三项计数（探针脚本 `_etl_tmp/probe_three_system_state.py`，
口径为 `(总行数, 标的数, 收益率 NULL, amount NULL, 幽灵日行数)`）：

| 系统 | 修复前 | 修复后（22:48 终态） | 说明 |
|------|--------|---------------------|------|
| `reits_kline_daily.json` | `(51567, 89, 24732, 259, 81)` | `(51575, 89, 89, 89, 0)` | 51,486 + 89 新交易日 = 51,575 |
| PostgreSQL `business.reits_kline_daily` | `(51567, 89, 24732, 259, 81)` | `(51575, 89, 89, 89, 0)` | 由 `json`(build) 从 JSON 整体重建，与 JSON **逐项相等** |
| DuckDB `D:\duckdb\reits.duckdb` | `(51567, 89, 24732, 259, 81)` | `(51575, 89, 89, 89, 0)` | 由 `sync_duckdb` 自 PG 反向重建，与 PG **逐项相等** |

**三项计数的正确读法（关键，避免误判为回归）**

- `收益率 NULL = 89`：**结构性 NULL**，每个标的首行无 `prev_close`，恰好 89 只 = 89 行。不变量 = `NULL 数 == 标的数`（TC-004）。
- `amount NULL = 89`：**当日新行无源**。2026-09-14 的 89 行由 `sync_kline_json` 直连补入，该通道不产 `amount`，
  且 `tdx_kline_daily` 当日 `amount` 尚未到位 → `repair_kline` 输出 `amount 无源` 并**保持 NULL（不编造）**。
  次日 `tdx_kline_daily` 到位后由同一脚本自愈（源有值 + 表为 NULL 即命中回填）。
  **真实不变量 = 可回填缺口 `pg_field_gap() == 0`**，不是 `amount NULL == 0`（见 ADJ-010）。
- `幽灵日行数 = 0`：2026-05-03 的 81 行在 JSON 与 PG 两侧均已清除，且 **build 未将其复活**（这正是 TC-018 的命题）。

**回滚验证结论**：`json`(build) 是 `CREATE OR REPLACE TABLE ... AS SELECT * FROM _tmp`（JSON 的纯函数）。
若修复被回滚，`pg_field_gap()` 必然 > 0 且 `幽灵日行数` 必然 = 81。实测两者分别为 `0` 与 `0` →
**修复在完整重建后依然成立**。

**完整 10 步 ETL 后的复验（23:56）**

| 检查 | 结果 |
|---|---|
| 三系统探针 | `JSON == PG == DuckDB == (51575, 89, 89, 89, 0)` —— 与第二次运行**逐项相同** |
| 全量测试复跑 | **27/27 PASS**（`logs/stdd_kfb_tests_after_fulletl_20260914.log`） |
| `backups/reits_kline_daily_*.json` 数量 | 运行前后**未增加**（`repair_kline` 走 `[SKIP]`，零备份） |

> 结论：本变更在「一次性修复」「K 线链路重建」「完整 10 步编排」三种执行路径下结论一致，
> 且稳态下不产生任何写入与备份文件。

---

## 四、执行期发现与修复（本变更最重要的部分）

STDD 的价值在本次变更中集中体现在「执行期发现的真实缺口」。以下 9 项均已在 Phase 3 内闭环
（实现已改、测试已补、已复跑验证），完整溯源见 `design-adjustments.yaml` ADJ-001..010。

### 4.1 【Critical 级真实缺口】`--apply-pg` 会漏删 PG 全部脏行（ADJ-001）

- **现象**：第 ③ 步预演输出 `非交易日脏行(JSON) 待删 0 行` 而 `非交易日脏行(PG) 待删 81 行`。
- **根因**：`apply_to_pg` 的待删日期取自 JSON 计划 `plan.purge`。第 ①② 步修完 JSON 后该计划恒为空，
  原实现会**静默跳过 DELETE** → PG 那 81 行 2026-05-03 脏行永远删不掉，且 `verify()` 会 MISMATCH 退出。
- **修法**：幽灵行判定是 `(行集合, 日历, 日历最大日)` 的**纯函数**，对 PG 自身行集合重放一次即可
  → 新增 `load_pg_kline()` / `plan_pg_purge()`，`apply_to_pg(conn, purge_dates, ...)` 改收日期。
- **规格化**：新增 SC-006-003 + TC-KFB-024。
- **通用教训**（已入经验库 EXP-006）：当 A 是 B 的纯函数、而修复脚本要同时改 A 与 B 时，
  **任何「从 A 推导出的计划」都不能直接用于改 B** —— A 修好后计划就空了。
- **影响评估**：若未发现，本次修复会在 PG 留下 81 行幽灵数据且退出码为 1，属**生产数据不完整**。

### 4.2 【High】psycopg2 的 list 参数按元素类型适配（ADJ-002）

- **报错**：`psycopg2.errors.UndefinedFunction: 操作符不存在: text = record`
  （`WHERE date = ANY(ARRAY[('180101','2026-05-03'), ...])`）
- **根因**：`plan_purge` 返回 `[(code, date), ...]`，被直接当日期列表传给 `WHERE date = ANY(%s)`。
- **修法**：`_normalize_dates()` 归一两种形状；`apply_to_pg` 与 `write_pg_purge_backup` 均先归一。
- **影响评估**：事务未开始即报错，**生产库未被改动**（脚本退出码 1，无静默损坏）。

### 4.3 【High】早退条件不完整 → PG 单独落后时永远不修（ADJ-008）

- **现象**：`if not needs_json_write and not pg_purge_dates: SKIP` —— PG 有 NULL 但无幽灵行时会直接 SKIP。
- **修法**：新增 `pg_field_gap(conn)`，只数**真正会被 SQL_RET/SQL_AMT 改写**的行；
  早退条件改为 `not needs_json_write and not (pg_purge_dates or pg_gap > 0)`。
- **为什么不能用「null 行数」**：各标的 89 个首行永久为 NULL（无 prev_close），会让 `--apply-pg` 永不早退。

### 4.4 【High】生产库删行缺少对称留痕（ADJ-003）

- **现象**：JSON 侧删 81 行有 `backups/phantom_<ts>.csv`，PG 侧原先是裸 `DELETE`。
- **修法**：新增 `write_pg_purge_backup()` → `backups/pg_phantom_<ts>.csv`（81 行 × 11 列），路径与行数进 `stats`。
- **依据**：项目红线「生产库写入与删行不得静默执行」。

### 4.5 【High】`coverage.fund_count` 不自洽（ADJ-007 延伸）

- **现象**：JSON `coverage.fund_count = 88` 而 `kline` 实有 **89** 只标的，违反 SC-005-002。
- **修法**：`_coverage_target()` 纳入 `fund_count`；`coverage_needs_refresh()` 自动触发刷新；TC-014 强化断言。
- **注**：该缺陷在执行后复核时发现，属自审漏项，非新引入。

### 4.6 【Medium】`--write` 无 `--purge-phantom` 时非幂等（复审 H4）

- **根因**：`needs_json_write` 在 purge 抑制**之前**计算，`plan.purge` 非空即置真 → 每次执行都重写 JSON。
- **修法**：幂等判定后移到 purge 抑制之后。
- **附带**：新增硬守卫 —— 该组合下若 `--apply-pg` 会删 PG 脏行则直接 `[ABORT]` 退出码 3（避免主动制造不一致）。

### 4.7 【Medium】连接泄漏与 verify 退出码（复审 H1 / H2）

- **H1**：`main()` 仅日历空路径关连接，其余异常路径泄漏 → 重构为 `_run()` + `try/finally` 统一关闭。
- **H2**：dry-run 与 `[SKIP]` 分支打印 `MISMATCH` 后仍 `return 0`，违反 SC-006-002 →
  抽出 `_finish()`，**所有**分支 MISMATCH 一律非零退出。

### 4.8 【Medium】`apply_to_pg` 无回滚（复审 M3）

- 三项改动加 `try/except: conn.rollback(); raise`，失败不留半成品。

### 4.9 【测试件】5 处断言必须去状态依赖（ADJ-004/005/006/010 + 复审）

| TC | 原断言（修复前状态） | 问题 | 改法 |
|---|---|---|---|
| 001 | `max_date == "2026-09-11"` | 外部采集把日历推到 2026-09-14 | `max_date == max(calendar)` |
| 006 | `len(ret_fills) == 24642` | 执行后 JSON 已修复 → 恒为 0 | 确定性 fixture + 终态不变量 |
| 023 | `n_big == 4 and n_exdiv == 4` | 修复前该行收益率为 NULL 未计入 | 「可解释性」：除息日 ∨ 序列前 2 行 + 独立源佐证 |
| 004/007/009 | 硬编码 89 / 178 / 51486 | 完整 ETL 会补入新交易日行 → 假失败 | 改为动态不变量（标的数 / 实际行数 / JSON 行数） |
| **007/015/018** | `amount IS NULL 的行数 == 0` | **第 5 处，执行期实测暴露**：每日新行 amount 天然无源 | 改为「可回填缺口 == 0」（`pg_field_gap()` / 源有值而表为 NULL） |

**第 5 处的完整证据链（ADJ-010，2026-09-14 22:37 实测）**

1. `sync_kline_json` 由 TDX 主站直连补入 **89 行 2026-09-14 当日新行**，该通道不产 `amount` → 全为 `None`。
2. `repair_kline` 立刻补上 `daily_return_pct +89`；`amount` 因 `tdx_kline_daily` 当日 `amount` 尚未到位，
   输出 `amount 无源: 180103 2026-09-14 ... 另有 79 行` 并**保持 NULL（按设计不编造）**。
3. 结果 `amount IS NULL` 由 0 变为 89 → 若断言 `== 0`，测试**在当天就假红**，且此后每个交易日必红。
4. 这不是回归：缺口在次日 `tdx_kline_daily` 当日 `amount` 到位后由**同一脚本自愈**
   （源有值 + 表为 NULL 即命中 `plan_amount_fills`）。真实不变量是「源可提供的值已全部落库」。

> 该判据与 ADJ-008 引入的 `pg_field_gap()` 完全同源 —— 本次只是把同一判据从**实现层**贯彻到**断言层**。

**TC-023 新增的第 5 行**：`508080`（中金亦庄产业园REIT）2025-06-27 = **+10.0113%**。
该标的序列首行即 2025-06-26（`rn=1`，无 prev_close），06-27 是第二行（上市次日涨停），
其两次除息在 2026-04-08 / 2026-09-02；`tdx_kline_daily` 同 (code,date) 的 close/volume 完全一致
→ **真实大跳变，非回填口径错误**。

> ★ **铁律**：一次性数据迁移的验收测试，必须区分「迁移前的期望值」与「迁移后的不变量」。
> 前者只能作 dry-run 预检；写进常驻断言 = 下次跑必红。
>
> ★ **铁律 2（ADJ-010 补充）**：断言「NULL 数 == 0」前必须先问「这个字段**是否总该有值**」。
> 对「源可能缺失」的字段，唯一正确的不变量是「**可回填缺口 == 0**」。

---

## 五、功能/测试覆盖对照

| 规格条目 | 涉及源码 | 覆盖 TC | 实质覆盖度 |
|---|---|---|---|
| REQ-001-001/002 交易日历 | `load_calendar` | 001 / 002 | ✅ 完整 |
| REQ-002-001/002/003 收益率回填 | `plan_return_fills` | 003 / 005 / 006 | ✅ 完整（SC-002-003 已由 TC-005 的确定性 fixture 补强） |
| REQ-003-001/002 amount | `plan_amount_fills` | 007 / 008 | ✅ 完整（SC-003-002 已由 TC-008 的 stdout 文案断言补强） |
| REQ-004-001/002/003 幽灵行三重守卫 | `plan_purge` | 006 / 009 / 010 / 011 / 012 | ✅ 完整（SC-004-002 已由 TC-010 的 `max_date==max(calendar)` 集成层断言补强） |
| REQ-005-001/002 JSON 原子写 + coverage | `apply_to_json` / `update_coverage` | 013 / 014 | ✅ 完整 |
| REQ-006-001 PG 应用 | `apply_to_pg` / `verify` | 015 / 016 / 016b / 024 / 025 | ✅ 完整（SC-006-002 已由 TC-016b 直接断言 rc） |
| REQ-007-001 编排防复发 | `daily_etl.py` | 017 / 018 | ✅ 完整 |
| REQ-008-001/002 幂等 + 早退 | `main` | 019 / 020 | ✅ 完整（SC-008-001/002 已由 TC-020 的早退文案断言补强） |
| REQ-009-001/002 dry-run + 授权 | `main` | 021 / 022 | ✅ 完整（SC-009-001 已由 TC-021 的 PG 计数快照、SC-009-002 由 TC-022 的提示文案补强） |

---

## 五-B、多路并行 Review 结果

> C1 执行：3 个只读审查代理并行（代码质量 / 测试与配置 / 文档与规格一致性）。

### Review 迭代历史

| 轮次 | Critical | High | Medium | Low | 状态 |
|------|----------|------|--------|-----|------|
| 1 | 2（均为文档/测试件，实现侧 0） | 4 | 5 | 6 | 需修复 → **已全部处理或登记** |

### 最终 Review 汇总

| 维度 | Critical | High | Medium | Low | 总计 |
|------|----------|------|--------|-----|------|
| 代码质量（`repair_kline_fields.py` / `daily_etl.py`） | 0 | 2 | 4 | 5 | 11 |
| 测试/配置（测试脚本 + `.stdd.yaml`） | 1 | 3 | 4 | 4 | 12 |
| 文档/规格（change 目录全部文档） | 1 | 2 | 6 | 2 | 11 |

### Review 已修复问题

| # | 严重性 | 文件 | 问题 | 状态 |
|---|--------|------|------|------|
| 1 | H | `repair_kline_fields.py`（`main`） | 异常路径连接泄漏 | ✅ 已修复（`try/finally`） |
| 2 | H | `repair_kline_fields.py`（`_finish`） | `--verify` MISMATCH 未非零退出 | ✅ 已修复 |
| 3 | H | `repair_kline_fields.py`（`_coverage_target`） | `fund_count` 未纳入自洽刷新 | ✅ 已修复（88 → 89） |
| 4 | H | `.stdd.yaml` | S3/S5 状态滞后于实际执行 | ✅ 已修复 |
| 5 | M | `repair_kline_fields.py`（`apply_to_pg`） | 无 rollback | ✅ 已修复 |
| 6 | M | `repair_kline_fields.py`（`main`） | purge 抑制前判幂等 → 非幂等 | ✅ 已修复 |
| 7 | M | `repair_kline_fields.py`（`main`） | `--write --apply-pg` 制造 JSON/PG 不一致 | ✅ 已修复（`[ABORT]` 退出码 3） |
| 8 | M | 测试脚本 | TC-024 断言两态通吃（vacuous） | ✅ 已修复（终态不变量 + 备份文件断言） |
| 9 | M | 测试脚本 | TC-006 状态段恒真 | ✅ 已修复（终态不变量） |
| 10 | M | `design.md` | 脚本结构写 `get_raw_conn`/DictCursor，与实现不符 | ✅ 已修复 |
| 11 | M | `design.md` | 承诺「启动时清理陈旧 .tmp」但未实现 | ✅ 已登记为观察项（YAGNI，TC-013 已证无残留） |
| 12 | M | `proposal.md` / `design.md` / `phase-context.md` | |涨跌幅|>10% 行数 4 → 实为 5 | ✅ 已修复 |
| 13 | M | `test-plan.md` | 表头写「9 REQ / 22 SC」 | ✅ 已修复（18 / 24） |
| 14 | M | `design.md` | 「全表 24,820 个值」表述错误 | ✅ 已修复 |
| 15 | M | `slices.md` | TC 核算 23，S3 未含 024/025 | ✅ 已修复（25） |
| 16 | M | `tasks.md` | 全部未勾选但实际已完成 | ✅ 已修复 |
| 17 | M | `design-adjustments.yaml` | 头部写 7 项 / 仅新增 1 个 SC | ✅ 已修复（10 项 / 2 个 SC） |
| 18 | M | 测试脚本 | 硬编码 `D:\duckdb` 路径 | ✅ 已修复（走 `core.duckdb_path`） |
| 19 | L | 测试脚本 | 未使用变量 `cal` | ✅ 已修复（pyflakes 干净） |
| 20 | L | `spec.yaml` | 4 处 YAML 值以反引号开头（`given: \`tdx_kline_daily\` 为空…`），YAML 无法解析 | ✅ 已修复（加双引号包裹；`yaml.safe_load` 通过，18 REQ / 24 SC 解析正确） |

### Review 已知限制（未修复，低优先级）

| # | 严重性 | 文件 | 问题 |
|---|--------|------|------|
| 1 | L | `repair_kline_fields.py`（`verify`） | 幽灵日指标硬编码 `PHANTOM_HINT`；见 §七 K4 |
| 2 | L | 测试脚本 | ~~部分 SC 仅有文案级/弱代理断言~~ | ✅ **已关闭**：6 处全部补强（见 §七 K5 明细），并新增 TC-KFB-016b |
| 3 | L | `daily_etl.py:55` | `import shutil` 未使用（**预存在**，非本次引入）；见 §七 K3 |
| 4 | L | `repair_kline_fields.py` | `excl` 空值哨兵用 `[""]`，可读性略差（无功能影响） |

---

## 六、设计调整说明

详见 [`design-adjustments.yaml`](design-adjustments.yaml)（ADJ-001..010 + spec_deltas + test_plan_deltas + UAD-001/002）。

**摘要**：
- **10 项调整**，`requires_re_spec=false` / `requires_re_build=false`（全部在 Phase 3 内闭环）。
- **新增 2 个 Scenario**：SC-006-003（PG 侧待删日期独立推导）、SC-006-004（三系统一致 JSON↔PG↔DuckDB）。
- **新增 2 个 TC**：TC-KFB-024、TC-KFB-025。
- 规格由 Gate 2 时的 **18 REQ / 22 SC / 23 TC** 变为 **18 REQ / 24 SC / 25 TC**。
- **ADJ-010** 为执行期实测暴露的第 5 处状态依赖断言（`amount IS NULL == 0` → 可回填缺口 == 0）。
- **UAD-001 / UAD-002** 记录 D哥在 S5 授权门的原话选择（「执行全部三步」/「完整 daily_etl」）；
  UAD-002 附 `actual_execution` 字段如实记录第二次运行的范围偏离（见 §3.2）。

---

## 七、修复确认记录与已知问题

### 7.1 执行期缺陷修复确认

| 问题 | 修复文件 | 状态 |
|------|----------|------|
| `--apply-pg` 漏删 PG 全部 81 行脏行 | `repair_kline_fields.py`（`plan_pg_purge` / `apply_to_pg`） | ✅ 已修复并实测（`deleted: 81`） |
| `text = record` 类型混用 | `repair_kline_fields.py`（`_normalize_dates`） | ✅ 已修复并实测 |
| PG 单独落后时早退不修 | `repair_kline_fields.py`（`pg_field_gap`） | ✅ 已修复（二次执行 `pg_gap=0` → `[SKIP]`） |
| PG 删行无留痕 | `repair_kline_fields.py`（`write_pg_purge_backup`） | ✅ 已修复（`pg_phantom_20260914_212712.csv`，81 行） |
| `coverage.fund_count` 88≠89 | `repair_kline_fields.py`（`_coverage_target`） | ✅ 已修复（已刷新为 89） |
| 连接泄漏 / verify 退出码 / 无回滚 | `repair_kline_fields.py`（`_run` / `_finish` / `apply_to_pg`） | ✅ 已修复 |

### 7.2 已知问题（不在本次范围，已登记）

| # | 名称 | 原因 | 影响 | 补完计划 |
|---|------|------|------|---------|
| **K1** | `reits_kline_daily.json` 的 `sample_stats` 陈旧 | 180101 的 `last_date` 停在 2026-08-28 而 kline 已到 2026-09-11；只覆盖 88 只 | 仅影响该元数据块的参考价值，不影响任何数据行 | 独立 slice 重算；陈旧性先于本变更存在 |
| **K2** | ~~`coverage.fund_count` = 88 vs 89~~ | 既有不一致 | — | ✅ **本次已一并修复**（ADJ-007 延伸） |
| **K3** | `daily_etl.py:55` `import shutil` 未使用 | 预存在 | 无功能影响（pyflakes L 级） | 下次触及该文件时顺手删；本次不改以免污染 diff |
| **K4** | `verify()` 幽灵日指标硬编码 `PHANTOM_HINT` | 设计如此 | 无——它只做 JSON↔PG **一致性**对比（两侧同 filter，对称）；「发现新幽灵日」是 `plan_purge` + TC-009 的职责 | 若未来出现第二个幽灵日，改为「非交易日行数」 |
| **K5** | ~~覆盖度弱点（6 处）~~ | 时间与范围约束 | — | ✅ **本次已一并关闭**（见下表） |
| **K6** | 当日新行 `amount` 天然为 NULL（**非缺陷，已知行为**） | `sync_kline_json` 的 TDX 主站直连通道不产 `amount`，且 `tdx_kline_daily` 当日 `amount` 尚未到位 | `amount IS NULL` 每天会新增 89 行，直到次日源到位被 `repair_kline` 自愈 | 无需改代码；如需当日即有值，应让 `fetch_tdx_raw` 当日 `amount` 先于 ETL 到位（源侧调度问题） |
| **K7** | `westock_ff` 耗时严重超预算（实测 **1520.5s = 25.3 min**，历史区间 155–737s） | 89 只串行/半并发 npx 取数；`WESTOCK_FF_TIMEOUT=2400` 未触发 | 该步位于 `repair_kline` **之前** → 拖长每日修复生效时间；若真挂住会吃 40 min × 最多 2 次尝试 | 单独排期优化（并发度 / 超时预算 / 失败快速跳过），**不在本变更范围** |
| **K8** | `pre_listing` 在完整 ETL 中 `rc=1` | `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {"count":195,"threshold":195,"scope":"turn"}` —— safe-delete 策略拦截一次性批量删除 | 该步不产出 MD，但不影响任何 K 线数据；ETL 会因此发失败告警邮件 | 属 `pre_listing_daily.py` + safe-delete 策略范围，建议单独排期；**不在本变更范围** |

**K5 关闭明细（6 处弱覆盖断言 → 实质断言，全部复跑通过）**：

| SC | 原缺口 | 补强方式 |
|---|---|---|
| SC-002-003 | 「已有厂商值不被改写」只有弱代理（公式吻合 ≠ 未被改写） | TC-005 增**确定性 fixture**：两行已有值（1.2345 / 99.0）故意偏离公式，断言二者均不进 `ret_fills`；保留全量对撞 |
| SC-003-002 | 「输出列出无源键」的文案断言未测 | TC-008 增 `run_capture()` 捕获 stdout，断言含 `amount 无源: 999999 1999-01-04` 与 `无源可取 1 行` |
| SC-004-002 | fixture 的 `max_date` 不在 calendar 内，集成层分支不可达 | TC-010 增集成层断言：`max_date == max(calendar)` 且日历最大日永不被删 |
| SC-006-002 | 「不一致时非零退出码」未直接断言 rc | 新增 **TC-KFB-016b**：人为多 1 行的 JSON → `rc_bad=1` 且输出含 `MISMATCH`；同时对真实 JSON 断言 `rc_ok=0` + `VERIFY] OK`（排除「恒非零」的假阳性） |
| SC-008-001/002 | 「无缺口」文案断言未测 | TC-020 捕获 stdout，断言同时出现 `[SKIP]` 与 `无缺口`（证明早退分支确实被走到） |
| SC-009-001 / 009-002 | 「PG 计数不变」未测；「提示加 --purge-phantom」未测 | TC-021 增 `pg_counts()` 前后快照对比；TC-022 捕获 stdout 断言含 `--purge-phantom` |

> **补强过程中的一个真实踩坑（已入经验库 EXP-013）**：TC-008 最初用 `180101 / 2021-06-21`
> 作为「无源」fixture，但经 `main()` 会加载**真实** `src_map`，该键在源表里**有 amount**
> → `unresolved` 恒为 0、文案断言必然失败。教训：**涉及「源缺失」的 fixture，必须使用
> 真实源中确实不存在的键**，否则测的是「源有值」而不是「无源」。

---

## 七-B、经验库更新

### 本次新增经验

| 经验ID | 类别 | 模式 | 严重程度 | 发现阶段 |
|--------|------|------|---------|---------|
| EXP-001 | architecture | 先找真源再决定改哪里（PG 是 JSON 的纯函数） | high | BUILD |
| EXP-002 | data-migration | 缺口统计必须按处置路径分层（`*_after_fill_only` vs `*_after`） | high | BUILD |
| EXP-003 | data-quality | 判幽灵交易日需三重守卫，不能只看周末 | high | BUILD |
| EXP-004 | validation | 口径用全量厂商对撞而非抽样 | medium | BUILD |
| EXP-005 | testing | 断言不能绑死「修复前状态」与外部可变常量 | high | BUILD / VERIFY |
| EXP-006 | design | 纯函数计划不能只对一个输入源求值（本次最大教训） | **critical** | BUILD |
| EXP-007 | psycopg2 | list 参数按元素类型适配，元组会变 record | medium | BUILD |
| EXP-008 | infra | `core.pg` 双入口游标类型不同 | medium | BUILD |
| EXP-009 | safety | 生产库删行须与 JSON 侧对称留痕 | high | BUILD |
| EXP-010 | orchestration | 编排插入新步时「位置」比「实现」更易错 | medium | BUILD |
| EXP-011 | testing | 「字段 NULL 数 == 0」不是不变量；对可能无源的字段必须断言「可回填缺口 == 0」 | **high** | VERIFY |
| EXP-012 | orchestration | 长跑 ETL 会被会话/终端边界杀掉并留下僵尸锁；锁的自动接管是必要防线，但 E2E 验证应选「覆盖命题真值的最短链路」而非「全量编排」 | medium | VERIFY |
| EXP-013 | testing | 「源缺失」类 fixture 必须使用**真实源中确实不存在**的键；否则经真实入口（会加载真实源）时测的是「源有值」 | **high** | VERIFY |

### 本次命中已有经验（复用）

| 经验ID | 类别 | 模式 | 命中阶段 |
|--------|------|------|---------|
| —（`announcement_inventory` test-report） | testing | 「core.pg 游标为 DictCursor」的记录不完整 → 已在本变更中修正为「仅 `get_pg_conn()` 成立」 | BUILD |
| EXP-005 | testing | 「断言不能绑死修复前状态」在 VERIFY 阶段**第 5 次**命中（ADJ-010），印证该模式的高复发率 | VERIFY |

### 经验统计

| 指标 | 数值 |
|------|------|
| 本次新增 | 13 条（EXP-001..013） |
| 本次复用/修正 | 2 条 |
| 经验库总计 | 13 条（`.stdd/experiences/kline_field_backfill.md`） |

---

## 八、结论

### 8.1 质量信号汇总

| 信号源 | 状态 | 备注 |
|--------|------|------|
| 单元/集成测试 | ✅ | **27/27 通过（通过率 100%）**，`RESULT: PASS`，退出码 0 |
| E2E 测试 | ✅ | `daily_etl.py` K 线相关链路 5 步全绿（`ok=5 bad=0`，EXIT=0）；关键步骤与范围偏离见 §三 |
| Lint（pyflakes） | ✅ | `repair_kline_fields.py` / 测试脚本干净；`daily_etl.py` 1 项预存在问题（K3） |
| 语法检查（py_compile） | ✅ | 3 个文件全部通过 |
| 调试残留 / 死代码 | ✅ | 无 `breakpoint` / `TODO` / `FIXME`；死代码 `purge_keep` 已移除 |
| 多版本测试 | N/A | 单运行时（Python 3.13.12） |
| 覆盖率 | N/A | 仅诊断；弱覆盖项见 §七 K5 |
| 十二类失败模式 | ✅ | 12/12 检查完成，0 Critical 命中（见 §8.2） |

### 8.2 十二类失败模式检查结果

| # | 类别 | 结论 | 证据 |
|---|------|------|------|
| a | 边界条件 | ✅ 通过 | 空日历→`CalendarEmptyError`（TC-002）；日历最大日只告警不删（fixture 实测）；晚于 max 的日期只告警（fixture 实测）；首行无 prev_close 不填（TC-004） |
| b | 空值 / None | ✅ 通过 | `prev_close=0` 跳过（不除零，fixture 实测）；`close=None` 只跳过紧随一行、不污染后续链（fixture 实测 + 代码注释）；amount 无源→`unresolved` 显式报告（TC-008） |
| c | 并发 / 竞态 | ✅ 通过 | `daily_etl` 运行锁实测挡住第二实例；`repair_kline` 单写者；JSON 写为 tmp+`os.replace` 原子；新增非法组合硬守卫（`--write --apply-pg` 无 `--purge-phantom` → 退出码 3） |
| d | 资源泄漏 | ✅ 通过（已修） | 复审发现异常路径泄漏 → 重构为 `_run()` + `try/finally` 统一关闭；所有游标均用 `with` |
| e | 错误处理 | ✅ 通过 | 空日历→退出码 2；`--verify` MISMATCH→退出码 1（所有分支）；非法组合→退出码 3；脚本缺失→`skip`；`run_cmd` timeout 600 / retries 1 / backoff 30 |
| f | 幂等性 | ✅ 通过 | TC-019 二次执行逐字节一致；TC-020 无缺口零备份；`--apply-pg` 二次执行 `pg_gap=0` → `[SKIP]` |
| g | 数据一致性 | ✅ 通过 | TC-003 全量独立重算 **51,486 行 0 不一致**；TC-016 JSON↔PG 五项计数相等；TC-014 coverage 三项既有字段自洽 |
| h | 跨系统一致性 | ✅ 通过 | TC-025 JSON ↔ PG ↔ DuckDB 四项计数一致（终态 `51575/89/89/0`，由 `sync_duckdb` 传播，`total=56 fail=0`） |
| i | 性能 / 超时 | ✅ 通过 | `repair_kline` dry-run 实测 **6.6 s**（含 16.9 MB JSON 载入 + 2 次 PG 查询 + 规划），超时预算 600 s，余量 90×；ETL 实测 `backfill_kline 14.0s / sync_kline_json 110.6s / repair_kline 7.2s / build 108.0s / sync_duckdb 456.1s`，均在各步预算内 |
| j | 安全 / 权限 | ✅ 通过 | 无硬编码凭据（`load_env` 读 `.env`）；f-string 仅插值模块级常量 `SCHEMA/TABLE/CAL_TABLE`，全部数据值走 `%s` / `%(excl)s`；删行需显式 `--purge-phantom`（TC-022） |
| k | 可观测性 | ✅ 通过 | 打印计划摘要（含 JSON 侧与 PG 侧对照）、WARN 逐日列出、备份路径、`stats` 明细、`[VERIFY]` 结果；`[ABORT]` / `[SKIP]` / `[PG-ONLY]` / `[COVERAGE]` 分支可区分 |
| l | 回滚 / 恢复 | ✅ 通过 | 原 JSON 备份实测可复原（51,567 行 / ret_null 24,732 / amt_null 259 / phantom 81，与修复前逐项吻合）；JSON 侧与 PG 侧各 81 行 × 11 列 CSV；全库 dump `pg_reits.bak.20260914_212933.dump` |

**命中项数：0 Critical**（复审发现的 2 个 Critical 均落在测试件与文档，非实现代码，且已修复）。

### 8.3 总体评估

- **可以部署**。修复已实际写入生产（JSON 24,642 收益率 + 178 amount；PG 同量 + 删除 81 行），
  并已通过一次完整的 **JSON → build(PG) → sync_duckdb** 重建验证：三系统终态
  `(51575, 89, 89, 89, 0)` **逐项相等**，其中 `51575 = 51,486 + 89` 新交易日行、
  收益率 NULL 89 = 结构性首行、amount NULL 89 = 当日新行无源（次日自愈）、幽灵日 0。
- **回滚验证通过**：`json`(build) 为 `CREATE OR REPLACE`（JSON 的纯函数），实测未回滚修复，
  幽灵日未被复活（TC-018 `fillable_gap=0`、`phantom=0`）。
- **风险等级：低**。全部写入有前置备份；删行走三重守卫 + 两侧留痕；脚本幂等且失败回滚。
- **本变更最大价值不在「填了 24,820 个空」，而在执行期抓出的两个真实缺口**
  （`--apply-pg` 漏删、早退不完整）—— 前者若未发现，会在生产库留下 81 行幽灵数据。
- **次要价值**：验证阶段暴露的第 5 处状态依赖断言（ADJ-010）与 K6 揭示的
  「当日新行 amount 无源」链路特性，都是只有真跑一遍才会浮现的知识。
- **K5 已关闭**：6 处弱覆盖断言全部改为实质断言（确定性 fixture / stdout 文案捕获 /
  PG 计数快照 / rc 直接断言），测试项由 26 增至 27，全部通过。
  补强过程中又抓出一个真实测试缺陷（EXP-013：「源缺失」fixture 用了源表里存在的键）。
- **后续建议**：
  1. 观察下一次 `daily_etl.py` 常规运行（02:00）是否稳定输出 `[SKIP] 无缺口`；
  2. 排期处理 K1（`sample_stats` 重算）与 K5（补 6 处弱覆盖断言）；
  3. 顺手清掉 K3 的未使用 import。

---

> ⚠️ 本报告由 AI 基于实际执行输出与只读查询结果整理，所有计数均来自脚本运行日志或 `psql` / `duckdb` 实测，
> 未使用推算值。完整溯源见 `.stdd/experiences/kline_field_backfill.md` 与 `design-adjustments.yaml`。
