# 经验沉淀 — kline_field_backfill

> 变更：`reits_kline_daily` 字段级回填（daily_return_pct / amount）+ 非交易日脏行清理
> 日期：2026-09-14 ｜ STDD V3.0.5（文件约定式）｜ 模式：standard
> 阶段：Phase 1（Gate 1）→ Phase 2（Gate 2）→ Phase 3（S1–S5 + Part C）

---

## EXP-001 · 先找「真源」，再决定改哪里

**现象**：拿到「`daily_return_pct` 24,643 行为空」的缺陷单，直觉是在 PG 上写 UPDATE。

**关键事实**：`_etl_tmp/build_reits_duckdb.py::create()` 执行
`CREATE OR REPLACE TABLE "tbl" AS SELECT * FROM "_tmp"`，经 `core.duckdb_compat`
落到 **PG business schema**。也就是说：

> **`business.reits_kline_daily` 是 `reits_kline_daily.json` 的纯函数，每天被全量替换。**

**结论**：只改 PG 会被第二天的 build 无痛回滚。正确目标是 JSON；PG 由 build 传播。
**副产品**：避免了「JSON + PG 双写」这个会漂移的第二真源设计。

**可复用检查**：改任何派生表前，先 grep 出谁在 `CREATE OR REPLACE` / `TRUNCATE ... INSERT`
它，确认上游真源与刷新频率。

---

## EXP-002 · 缺口统计必须「按处置路径分层」，否则数字对不上

**现象**：三份旧记录互相矛盾 —— amount 缺口写 178、收益率写 24,643。

**实查**：
| 量 | 旧记录 | 实测 | 差额来源 |
|---|---|---|---|
| `amount` NULL | 178 | **259** | 259 = 178（字段级）+ 81（幽灵日整批） |
| `daily_return_pct` NULL | 24,643 | **24,732** | 24,732 − 24,642（净可填）= 90 |
| 净可填收益率 | 24,643 | **24,642** | 24,643 中 1 行坐在幽灵日上 |

**顺序依赖（自审抓到的坑）**：
- `24,732 − 24,642 = 90`；清理再删掉幽灵行里那 1 个 NULL(180503) → **89**
- `259 − 178 = 81`；清理后 → **0**
- 总行数 `51,567 − 81 = 51,486`

**教训**：当一次修复同时包含「字段回填」和「行删除」时，验收数字必须区分
`*_after_fill_only`（只回填）与 `*_after`（回填+清理）两套，否则预置条件写错、
测试会在错误的状态下 PASS。spec.yaml 的 constants 已按此拆分。

---

## EXP-003 · 判「幽灵交易日」不能只看周末，要三重守卫

**结论性规则**（`plan_purge` 实现）：
一条行集合要被判为脏行并删除，必须**同时**满足：
1. `date` ∉ 交易日历（日历 = `business.tdx_kline_daily` 的 DISTINCT date，实测 0 周末行，洁净）
2. `date` < 日历 `max(date)`（**不删最新一天** —— 可能是当日尚未入库）
3. `date` 是周六/周日 **或** 该日全部标的的 `(close, volume)` 与上一交易日**逐行完全相同**

不满足第 3 条的只 `WARN`，不删。

**本案**：2026-05-03 是周日 + 劳动节（用户确认），`tdx_kline_daily` 该日 0 行，
81 行 `close`+`volume` 与 2026-04-30 逐行完全相同，且是全表**唯一**不在日历内的日期。

**为什么守卫 3 必要**：否则一次误删可能吃掉真实交易日（例如日历本身落后时的当日数据）。

---

## EXP-004 · 「厂商值」是口径背书的最强证据，要用全量而非抽样

**做法**：拿另一个源（sina）已有的 `daily_return_pct` 与自算公式对撞。
**结果**：26,755 / 26,755 = **100%** 吻合（80 处不符**全部**落在幽灵日 2026-05-03 上）。

**结论**：`daily_return_pct = round(((close / prev_close − 1) * 100), 4)`，**未复权**。
「未复权」意味着除息日会出现大跳变（实测 4 行 |跌幅| > 10%，全部是除息日），
这是**正确行为**而非缺陷。

**教训**：口径问题不要靠「抽样 8 条看起来对」下结论；找带该字段的第三方源做全量对撞，
并用「不符项是否全部落在一个可疑日期上」反向确认。

---

## EXP-005 · 断言不能绑死「修复前状态」和「外部会变的常量」

Phase 3 执行后暴露 4 处测试脆弱点（全部是测试问题，非实现缺陷）：

| TC | 原断言 | 问题 | 改法 |
|---|---|---|---|
| 001 | `max_date == "2026-09-11"` | 外部采集把日历推到 2026-09-14 | `max_date == max(calendar)` |
| 006 | `len(ret_fills) == 24642` | 执行后 JSON 已修复 → 恒为 0 | 双段：确定性 fixture + 状态段 `∈ {0, 24642}` |
| 023 | `n_big == 4 and n_exdiv == 4` | 修复前该行收益率为 NULL 未计入 | 改「可解释性」：除息日 ∨ 序列前 2 行 + 独立源佐证 |
| 014 | 只查 coverage 新增字段 | 漏查 `total_records` 自洽 | 加 `total_records == 实际行数` |

**TC-023 的新第 5 行**：`508080`（中金亦庄产业园REIT）2025-06-27 = **+10.0113%**。
该标的序列首行即 2025-06-26（rn=1，无 prev_close），06-27 是第二行（上市次日涨停），
两次除息在 2026-04-08 / 2026-09-02；`tdx_kline_daily` 同 (code,date) 的 close/volume 完全一致
→ 真实大跳变。

**通用规则**：一次性数据迁移的验收测试，必须区分
**「迁移前的期望值」**（只能作为 dry-run 的预检）与
**「迁移后的不变量」**（才能作为常驻断言）。前者写进断言 = 下次跑必红。

---

## EXP-006 · 「纯函数计划」不能只对一个输入源求值

**执行期发现的真实缺口**（本变更最有价值的一条）：

`--apply-pg` 的待删日期原本取自 JSON 计划 `plan.purge`。第 ① ② 步修完 JSON 后，
`plan.purge` 恒为空 → **PG 那 81 行脏行永远删不掉**，且 `verify()` 会 MISMATCH 退出。

实测证据：预演输出 `非交易日脏行(JSON) 待删 0 行` / `非交易日脏行(PG) 待删 81 行`。

**修法**：幽灵行判定本就是 `(行集合, 日历, 日历最大日)` 的**纯函数**，
对 PG 自身行集合重放一次即可 —— 新增 `load_pg_kline()` + `plan_pg_purge()`，
`apply_to_pg(conn, purge_dates, ...)` 改为接收日期而非计划对象。

**通用规则**：当 A 是 B 的纯函数、而修复脚本同时要处理 A 与 B 时，
**任何「从 A 推导出的计划」都不能直接用于改 B** —— 一旦 A 已修好，计划就空了。
必须对每个写入目标各自求值一次计划。

---

## EXP-007 · psycopg2 的 list 参数会按元素类型适配，元组会变成 record

**报错**：`psycopg2.errors.UndefinedFunction: 操作符不存在: text = record`
`LINE 4: WHERE date = ANY(ARRAY[('180101', '2026-05-0...`

**原因**：`plan_purge` 返回 `[(code, date), ...]`，被直接当日期列表传给 `WHERE date = ANY(%s)`。
psycopg2 把 list 里的 tuple 适配成 composite/record，于是 `text = record` 无操作符。

**修法**：新增 `_normalize_dates()`，把 `[(code, date), ...]` 与 `['date', ...]` 两种形状
统一归一为去重排序的纯日期列表，两个调用点（DELETE 与删前备份 SELECT）都先归一。

**教训**：给 psycopg2 传 list 参数时，**元素类型必须是数据库能直接比较的标量**；
调用契约要在函数 docstring 里写死，并加一个「两种形状都接受」的归一函数兜底。

---

## EXP-008 · core.pg 有两个入口，游标类型不同（会踩）

| 入口 | 返回 | 游标 |
|---|---|---|
| `core.pg.get_raw_conn()` | 裸 psycopg2 连接 | **元组**（供 COPY/批量） |
| `core.pg.get_pg_conn()` | `PgConn` 包装 | **RealDictCursor**（dict 行） |

按列名取数必须用 `get_pg_conn()`。用错报
`TypeError: tuple indices must be integers or slices, not str`。

**本案代价**：S1+S2 13 个 TC 里 8 个红。已在 `get_conn()` docstring 里写明两个入口的区别。

---

## EXP-009 · 生产库删行必须与 JSON 侧对称留痕

JSON 侧删 81 行有 `backups/phantom_<ts>.csv`（11 列），而 PG 侧原先是裸 `DELETE`。
已补 `write_pg_purge_backup()` → `backups/pg_phantom_<ts>.csv`（81 行 × 11 列），
路径与行数一并进 `stats` 打印。

**规则**：任何「生产库删除」路径都要有可复原的落盘留痕，且留痕内容要包含
足以重建被删行的**全部业务字段**（不只主键）。

---

## EXP-010 · 编排插入新步时，「位置」比「实现」更容易错

本步必须落在 `sync_kline_json` **之后**、`json`(build) **之前**：
- 在 `sync_kline_json` 之前 → 当日新行还没进 JSON，回填漏掉它们
- 在 `json` 之后 → 只改了 JSON 而没触发 build，PG 不同步

**且**：该步只写 JSON（`--daily` = `--write --purge-phantom`），**不带 `--apply-pg`**，
因为稳态下 build 的 `CREATE OR REPLACE` 会保证 JSON↔PG 一致。

**`--apply-pg` 只用于一次性追补**。这个区分要写进 `run_repair_kline()` 的注释里，
否则后人会顺手加上 `--apply-pg`，引入第二条会漂移的写路径。

---

## EXP-011 · 「字段 NULL 数 == 0」不是不变量；对可能无源的字段要断言「可回填缺口 == 0」

**严重程度**：high ｜ **发现阶段**：VERIFY（2026-09-14 22:37 实测）

### 现象

`repair_kline` 上线后第一次真实 ETL 运行，断言 `amount IS NULL == 0` 的 3 个 TC
（TC-KFB-007 / 015 / 018）在**当天就变红**：

```
sync_kline_json  [WRITE] 已补入 89 行 -> reits_kline_daily.json   ← 2026-09-14 当日新行
repair_kline     [JSON] daily_return_pct +89 / amount +0 / 删除 0 行
repair_kline     - amount 无源: 180103 2026-09-14  ... 另有 79 行
→ PG/JSON 的 amount IS NULL 由 0 变为 89
```

### 根因

`sync_kline_json` 走 **TDX 主站直连**补当日新行，该通道**不产出 `amount`**；
而 `tdx_kline_daily`（amount 的唯一来源）当日 `amount` 尚未到位。
`repair_kline` 正确地**拒绝编造**，输出「无源」告警并保持 NULL。

于是 `amount IS NULL` 每天都会新增 89 行，直到次日源到位被同一脚本自愈
（源有值 + 表为 NULL → 命中 `plan_amount_fills`）。

### 判据

对「源可能缺失」的字段，**唯一正确的不变量**是：

```sql
-- 可回填缺口：源有值而表为 NULL 的行数，必须 == 0
SELECT count(*) FROM k k JOIN src t ON t.fund_code = k.fund_code AND t.date::text = k.date
 WHERE k.amount IS NULL AND t.amount IS NOT NULL
```

而 `count(*) WHERE amount IS NULL` 只在「该字段总该有值」时才是不变量。

### 这与 EXP-005 是同一模式

EXP-005 说的是「断言不能绑死修复前状态」；本条的变体是
**「断言不能把『源本身可缺失』误当成『回填失败』」**。
本次是 EXP-005 模式在本变更内的**第 5 次命中**（前 4 次：TC-001 日历、TC-006 计划数、
TC-023 大跳变行数、TC-004/007/009 硬编码常量）→ 该模式复发率极高，写断言时应当作 checklist 逐条过。

### 落地

- 实现层早已有此判据（`pg_field_gap()`，ADJ-008 引入）。
- 本次只是把它**贯彻到断言层**：TC-015 / 018 改用 `mod.pg_field_gap(conn) == 0`；
  TC-007 增加 `k.amount IS NULL AND t.amount IS NOT NULL` 子查询计数。
- 登记为 ADJ-010。

---

## EXP-012 · 长跑 E2E 会被终端/会话边界杀掉；验证要选「覆盖命题真值的最短链路」

**严重程度**：medium ｜ **发现阶段**：VERIFY

### 现象

S5 授权门选了「完整 `daily_etl`」（全 10 步）作为 TC-018 的验证手段。
第一次运行 21:29:33 启动，日志停在 21:32:14 的 `westock_ff` 阶段，
**主进程与子进程在会话边界被终止**，留下 `_etl_tmp/daily_etl.lock`（pid 19148，已死）。

第二次 22:34:07 启动时，`acquire_lock` 打印：

```
[WARN] 发现残留运行锁(pid=19148, started=2026-09-14T21:29:33): 进程已不存在, 本次接管
```

### 两个结论

1. **僵尸锁自动接管是必要防线**。`LOCK_STALE_HOURS=12` + `_pid_alive()` 的组合
   让无人值守场景下「上一轮被强杀」不会永久锁死后续运行。这个能力本身值得保留并定期回归。
2. **E2E 验证应选「覆盖命题真值的最短链路」**，而不是「跑最多的步骤」。
   TC-018 的命题是「修复不被 build 回滚」，其唯一写路径是
   `backfill_kline / sync_kline_json → repair_kline → json(build) → sync_duckdb`；
   `ccreits`（元数据 UPSERT）与 `westock_ff`（资金流，入 `westock_fund_flow_daily`）
   对 `business.reits_kline_daily` **无任何写入路径**，纳入与否不改变命题真值，
   却要付 40+ 分钟网络取数的代价（`westock_ff` = 89 只串行 npx）。

### 附带发现：`run_cmd` 的输出是全缓冲的

`p.communicate(timeout=...)` 只在**子进程结束时**返回全部输出 →
长步骤期间日志文件不增长，无法据此判断「在算 vs 卡死」。
排查时不要只看日志 mtime；应查进程存活（`tasklist /FI "PID eq <pid>"`）
或看该步骤的**副产物 mtime**（如 `reits_kline_daily.json`）。

---

## EXP-013 · 「源缺失」类 fixture 必须用真实源中**确实不存在**的键

**严重程度**：high ｜ **发现阶段**：VERIFY（K5 补强时被自己的测试抓出来）

### 现象

为验证 SC-003-002「输出列出无源 amount 键」，写了 fixture：

```python
doc = mk_doc({"180101": [row("180101", "2021-06-21", 1.0, amount=None)]})
mod.main(["--json", tmp_json])          # ← 经真实入口
```

数据层断言（`plan_amount_fills(doc, {}, set())` 传**空** src_map）通过，
但走 `main()` 后实际输出是：

```
amount : 待填 1 行（无源可取 0 行）      ← 期望「无源可取 1 行」
```

### 根因

`main()` 内部会 `load_amount_source(conn)` 加载**真实**源表；
`(180101, 2021-06-21)` 在 `tdx_kline_daily` 里**确实有 amount** →
该行被判为「可填」而不是「无源」。

即：**同一个 fixture，直接调纯函数（空 src_map）是「无源」，
经真实入口（真 src_map）就变成「有源」**。测的东西变了。

### 判据 / 做法

- 「源缺失」类 fixture 必须用**真实源中不可能存在的键**：
  假代码（`999999`）+ 远早日期（`1999-01-04`）。
- 更一般地：**只要被测路径会自行加载外部依赖（DB / 文件 / 网络），
  fixture 就不能只保证「在我传进去的参数下成立」，还要保证「在真实依赖下仍成立」。**
- 反向检查法：补强后**故意**把键换回真实存在的键，测试应当变红 —— 能变红才说明断言有效。

### 与 EXP-011 的关系

两者都在讲「测试的语义必须与命题一致」：
EXP-011 是「别把源缺失误判成回填失败」，本条是「别把源有值误判成源缺失」。互为镜像。

---

## 数字锚点速查（复现本变更时直接对表）

```
初始：  rows 51,567 ｜ ret_null 24,732 ｜ amt_null 259 ｜ phantom 81
日历：  1,272 个交易日（含外部新增的 2026-09-14）｜ 周末行 0 ｜ max = 2026-09-14
公式：  daily_return_pct = round(((close / prev_close - 1) * 100), 4)  ← 未复权
① JSON：ret +24,642 ｜ amount +178 ｜ 删 81 行
③ PG ：ret_updated 24,642 ｜ amt_updated 178 ｜ deleted 81（单事务）
一次性终态：rows 51,486 ｜ ret_null 89（全为各标的首行）｜ amt_null 0 ｜ phantom 0 ｜ funds 89

── 完整 ETL 重建后（2026-09-14 22:34 的 K 线链路 + 22:56 的完整 10 步，权威终态）──
第二次（K 线链路 5 步，ok=5 bad=0）：
  sync_kline_json：+89 行（2026-09-14 当日新行，amount 全空）
  repair_kline   ：ret +89 ｜ amount +0（89 行「无源」，按设计不编造）
  build          ：108.0s  CREATE OR REPLACE 未回滚修复
  sync_duckdb    ：456.1s  total=56 fail=0
第三次（完整 10 步，22:56:49→23:55:25，ok=9 bad=1）：
  westock_ff     ：1520.5s（25.3 min，远超历史 155–737s → K7）
  backfill_kline ：4.5s   0 行
  sync_kline_json：93.6s  直连新增 0 键 / JSON 缺失 0 → 无缺口退出
  repair_kline   ：2.0s   [SKIP] 无缺口，跳过写入（未创建任何备份文件）  ← 稳态幂等
  build          ：36.4s  未回滚修复
  sync_duckdb    ：363.9s total=56 fail=0
  pk_guard 4.7s / ann 336.0s / pre_listing 1030.9s FAIL（safe-delete 批量阈值 → K8）
三系统终态（JSON == PG == DuckDB）：
        rows 51,575 ｜ funds 89 ｜ ret_null 89 ｜ amt_null 89 ｜ phantom 0
        ↑ 51,575 = 51,486 + 89；ret_null 89 = 结构性首行；amt_null 89 = 当日新行无源（次日自愈）
不变量：pg_field_gap() == 0  ← 断言必须用这个，不要用「amount NULL == 0」

备份：  backups/reits_kline_daily_20260914_212012.json（原 JSON，一次性修复前）
        backups/reits_kline_daily_20260914_223742.json（ETL 前）
        backups/phantom_20260914_212012.csv（JSON 侧 81 行）
        backups/pg_phantom_20260914_212712.csv（PG 侧 81 行）
        backups/pg_reits.bak.20260914_212933.dump / pg_reits.bak.20260914_223407.dump（全库）
日志：  logs/stdd_kfb_fulletl_20260914.log（第一次，未跑完）
        logs/stdd_kfb_klinechain_20260914.log（第二次，K 线链路 ok=5 bad=0）
        logs/stdd_kfb_fulletl2_20260914.log（第三次，完整 10 步 ok=9 bad=1）
        logs/stdd_kfb_tests_20260914.log（K5 补强前 26/26 PASS）
        logs/stdd_kfb_tests_k5_20260914.log（K5 补强后 27/27 PASS，权威）
        logs/stdd_kfb_tests_after_fulletl_20260914.log（完整 10 步 ETL 后复跑，仍 27/27）
```
