# Design: kline_field_backfill

> STDD Phase 2 设计文档 | 2026-09-14 周一
> 依赖实证：proposal.md（本轮 9 个只读诊断 SQL）+ `_etl_tmp/build_reits_duckdb.py` 源码核查 + `daily_etl.py` 编排源码核查

## Context

### 数据链路现状（已核实）

```
上游通道 (tdx 离线 .day / tdx 主站直连 / tencent)
        │
        ▼
business.tdx_kline_daily   ← 原始日线（51,486 行，amount 100% 有值，洁净交易日历）
        │  sync_kline_json_from_tdx.py：只补「缺失键」，新行一律带 NULL daily_return_pct
        ▼
reits_kline_daily.json     ← ★ 唯一真源（16.87 MB，与 PG 逐字段一致）
        │  backfill_reits_kline_daily.py：只补「缺失键」(c,ds) not in exists
        ▼
_etl_tmp/build_reits_duckdb.py::create()
        con.execute('CREATE OR REPLACE TABLE "reits_kline_daily" AS SELECT * FROM "_tmp"')
        经 core.duckdb_compat 落到 PG business schema
        ▼
business.reits_kline_daily  ← ★ 每天被 JSON 全量替换（无独立生命周期）
        │  sync_pg_to_duckdb.py
        ▼
D:/duckdb/reits.duckdb      ← 只读副本
```

### 决定性事实

| # | 事实 | 来源 |
|---|---|---|
| F1 | PG 的 `reits_kline_daily` 每天由 JSON **全量 CREATE OR REPLACE**，不是 upsert | `build_reits_duckdb.py:48` + `:122-127` |
| F2 | JSON 与 PG 当前**逐字段一致**（89/51,567/24,732/259/81/ source 分布） | 本轮实测 |
| F3 | 编排中的两个补录脚本**只补缺失键，不补字段 NULL** | `backfill_reits_kline_daily.py:205`；`sync_kline_json_from_tdx.py` NOT EXISTS |
| F4 | 唯一能补 amount 的脚本只写 `tdx_kline_daily`，且**不在** `DAILY_DEFAULT` | `backfill_kline_amount.py:188-194`；`daily_etl.py:615` |
| F5 | 公式 `round(((close/prev_close-1)*100),4)` 在 sina **真实交易日 26,755/26,755** 上完全吻合 | proposal §1.4 |
| F6 | 待填行 prev_date 落在交易日历外 = **0**；日历无周末行 | proposal §1.3 |
| F7 | 2026-05-03 是**唯一**不在日历内的日期，81 行 = 04-30 逐行复制 | proposal §1.7 |
| F8 | `sync_kline_json_from_tdx.py:246` 以 `source='tdx'` 反算换手率分母 | 源码核查 |
| F9 | `fetch_tdx_kline.py:91` 的 `SOURCE_PRIORITY` 只作用于 `tdx_kline_daily`/`tdx_kline_minute` | 源码核查 |
| F10 | `DAILY_DEFAULT` 顺序：… `backfill_kline` → `sync_kline_json` → `json`(build) → `sync_duckdb` → `pk_guard` → … | `daily_etl.py:615-616` |

---

## Decisions

### 1. 修复载体：以 JSON 为唯一写入目标，PG 由 build 传播

**方案**：`repair_kline_fields.py` 的主写入目标是 `reits_kline_daily.json`。PG 的更新走两条路——
（a）**日常路径**：编排里紧随其后的 `json`(build) 步做 `CREATE OR REPLACE`，自动传播；
（b）**一次性路径**：`--apply-pg` 在单事务内做等价 UPDATE/DELETE，避免为一次修复跑全量 build。

**为什么**：
- F1 决定了 PG 没有独立生命周期。既然 PG 是 JSON 的**纯函数**，正确的工程动作是修**函数输入**，而不是修函数输出。
- 双写（JSON + PG 同时改）会造出**第二个真源**，正是这类字段级缺口能长期潜伏的同类土壤（F3/F4 的机制缺陷本质就是"两处各写一半"）。
- 日常路径单写 JSON → 稳态下**由构造保证** JSON↔PG 一致，无需额外对账。
- 一次性路径的 `--apply-pg` 只是**避免跑全量 build** 的性能优化（build 会重建 ~15 张表、走 pandas 全量替换，爆炸半径远大于本次修复需要），不是第二个真源；提交后立即断言三项计数一致（SC-006-002）。

**备选方案及排除原因**：
- 备选 A：只改 PG 不改 JSON → **直接排除**。下次 build（每天跑）会把修复全量回滚。
- 备选 B：JSON + PG 无条件双写（前一轮 `kline_amount_repair` 提案的设想）→ 保留其"防回滚"的正确部分，但去掉"日常也双写"：日常有 build 兜底，双写只是多一条会漂移的写路径。
- 备选 C：把回填逻辑塞进 `sync_kline_json_from_tdx.py` 的写入路径 → 排除。该脚本只处理"新增键"，且要在写 bar 时就查 prev_close，会侵入主写入路径、增加每日 ETL 的失败面；独立后置步更安全且可单独重跑。

### 2. 收益率口径：未复权，与列既有语义对齐

**方案**：`daily_return_pct = round(((close / prev_close - 1) * 100), 4)`，未复权。

**为什么**：F5 是决定性证据——sina 厂商自己填的 26,755 个真实交易日值**全部**等于该公式。即该列在库内的既有语义就是未复权简单收益率。对 tdx 行套用同一公式是**补齐列口径一致性**，不是引入新口径。
本次写入的 24,820 行（24,642 收益率 + 178 amount）与全表既有的 26,755 个厂商值共享同一语义。

**已知且预期的副作用**：223 行落在除息日，会体现分红除权的机械跌幅。其中 5 行 |涨跌幅| > 10%（超出 REITs 非首日 ±10% 限制）：**4 行是除息日**，
另 1 行为上市次日涨停（508080 2025-06-27 +10.0113%，序列首行即 2025-06-26，其除息在 2026 年）：
508001 2024-06-28 −11.169% / 508008 2024-04-09 −10.820% / 180401 2023-05-18 −10.738%（每份派 0.727 元）/ 508096 2023-11-13 −10.463%。
这是未复权口径的正确结果，须在 coverage 元数据与表注释中标注，避免下游误读为暴跌。

**备选方案及排除原因**：
- 备选 A：除息日留 NULL → 排除。会新造 223 个空洞，且与 sina 行（除息日照样有未复权值）自相矛盾。
- 备选 B：除息日算复权收益率 → 排除。会让同一列在不同行上有两种语义，比缺口更糟。复权口径应用 DuckDB 的 `tdx_hfq_factor` 另建列/另建表，属独立 slice。

### 3. 幽灵交易日判定：三重守卫 + 分级处置

**方案**：删除需**同时**满足：
1. `date` ∉ 交易日历（`tdx_kline_daily` 的 DISTINCT date）
2. `date` < 交易日历的 `max(date)`（严格历史，不含最新一天）
3. `date` 是周六/周日 **或** 该日全部行与「上一交易日」同标的行在 `(close, volume)` 上逐行完全相同

不满足第 3 条的「date ∉ 日历」行 → **只 WARNING，不删除**。

**为什么**：
- 守卫 2 防止把「当日尚未入库」误判为幽灵日（这是最危险的误删场景）。
- 守卫 3 防止**日历自身故障**导致误删：若 `tdx_kline_daily` 因上游全断而缺了某个**真实**交易日，守卫 1 会误判；守卫 3 要求"周末或与上一交易日逐行重复"这一强指纹，真实交易日的数据几乎不可能满足。
- 分级处置：能确证的（周末 / 逐行重复）自动清理，防止缺口复发（W5）；不能确证的只告警，把判断权留给人工。**宁可漏删，不可误删。**
- 2026-05-03 同时满足守卫 3 的两条子条件（周日 + 逐行重复），命中确定无疑。

**备选方案及排除原因**：
- 备选 A：只按「不在日历内」删除 → 排除。日历故障时会误删真实交易日。
- 备选 B：保留并改 `source='sina_duplicate'` → D哥 Gate 1 已定案**直接删除**。幽灵交易日留在时间序列里会静默污染所有按交易日的统计（交易日计数、波动率、日历 join），改标记只是让污染变得可识别，并不消除。
- 备选 C：引入外部节假日日历 → 排除（超出本次范围，需联网与维护成本）；守卫 3 已能覆盖已观测到的这一例，未覆盖的类型走 WARNING 人工兜底。

### 4. amount 回填的 `source` 标注：保持 `'tdx'` 不变

**方案**：178 行回填后 `source` 仍为 `'tdx'`。溯源由 JSON `coverage` 元数据 + `backups/` manifest + test-report 承担。

**为什么**：F8 显示 `sync_kline_json_from_tdx.py:246` 用 `WHERE source='tdx' AND turnover_rate>0 AND volume>0` 反算换手率分母。改标注会让这 178 行退出该样本。实测无标的会失去全部分母样本（每只最少 11 个、中位 78 个），**破坏性为零但收益也为零**——`source` 在该表里表达的是"bar 由哪条通道产出"，把它挪用来表达"字段级 provenance"是语义污染。D哥 Gate 1 已定案。

### 5. 编排插入点：`sync_kline_json` 之后、`json`(build) 之前

**方案**：`DAILY_DEFAULT` 改为
`["ccreits", "westock_ff", "backfill_kline", "sync_kline_json", "repair_kline", "json", "sync_duckdb", "pk_guard", "ann", "pre_listing"]`

**为什么**：F10 显示 build 是 JSON→PG 的传播点。修复必须**在 JSON 已含当日全部新行之后**（即 `sync_kline_json` 之后）、**在 build 之前**，才能一次传播到位。放 build 之后则当天白跑；放 `sync_kline_json` 之前则漏掉当天新行。
日常步**只写 JSON**（Decision 1），因此不引入新的 PG 写路径。

### 6. 脚本形态：新增独立脚本 `repair_kline_fields.py`

**方案**：新建根目录脚本，不扩展 `backfill_reits_kline_daily.py`。

**为什么**：
- 职责不同：`backfill_*` 家族补的是**缺失行**，本脚本补的是**已存在行的字段 NULL** 并清理脏行。
- 该脚本**必须**能独立重跑与单独验证（编排里失败可单独补跑），独立文件最小化与既有 441 行脚本的耦合。
- 与既有命名家族区分：不叫 `backfill_kline_*`，避免与 `backfill_kline_amount.py`（写 `tdx_kline_daily`）混淆。

### 7. 不新增 provenance 列

**方案**：不加 `daily_return_src` / `amount_src` 之类标记列。

**为什么**：`daily_return_pct` 可由同行 `close` + 上一行 `close` 完全复算，provenance 是可推导的；加列等于把可推导信息固化成会漂移的状态（且需要 schema 变更 + 下游同步）。amount 的溯源需求见 Decision 4。D哥 Gate 1 已定案。

### 8. 可测试性：`--json <path>` 路径覆盖

**方案**：脚本 SHALL 支持 `--json <path>` 覆盖真源路径（默认 `HERE/reits_kline_daily.json`），
使「幂等」「原子写 + 备份」「删除需显式授权」等**写入类**用例可在**临时副本**上验证，
不触碰生产 JSON。

**为什么**：
- 没有该参数，写入类用例只能直接跑生产 JSON。虽然逻辑上幂等，但测试的失败模式不该包含"测试自己写坏了生产真源"。
- 破坏性用例（删除幽灵行）尤其需要夹具隔离；`--json` 让同一套代码路径既跑生产也跑副本，**测的就是生产代码**，不是另写一份。
- 与 `--apply-pg` 配对使用即可完整覆盖「JSON 侧」与「PG 侧」两条写入路径。

**备选方案及排除原因**：
- 备选 A：测试里 `shutil.copy` 生产 JSON 到临时目录，再用 `monkeypatch` 改模块常量 → 排除。`--json` 是显式接口，比 monkeypatch 内部常量更稳、也更贴近真实调用方式。
- 备选 B：引入影子库 `reits_staging` 跑 PG 侧写入测试 → 暂缓。本机无该库（既有环境事实），且本次 PG 侧只做等价 UPDATE/DELETE，`--verify` 断言 + 事务已足够；建影子库属独立基础设施 slice。

---

## Architecture

### 每日编排（改动后）

```
daily_etl.py  DAILY_DEFAULT
  ├─ ccreits               元数据
  ├─ westock_ff            资金流
  ├─ backfill_kline        backfill_reits_kline_daily.py  → 补缺失「行」→ PG + JSON
  ├─ sync_kline_json       sync_kline_json_from_tdx.py    → 补 JSON 缺失「键」（新行带 NULL ret/amount）
  ├─ repair_kline ★新增     repair_kline_fields.py --daily --write
  │                          ├─ 读交易日历（tdx_kline_daily）
  │                          ├─ W1 填 daily_return_pct NULL（未复权公式）
  │                          ├─ W2 填 amount NULL（取自 tdx_kline_daily）
  │                          ├─ W3 删幽灵行（三重守卫，删前备份）
  │                          ├─ W4 原子写回 JSON（tmp + os.replace，写前备份）
  │                          └─ 无缺口 → 早退，不写任何文件
  ├─ json                  build_reits_duckdb.py  → CREATE OR REPLACE 全量重建 PG
  ├─ sync_duckdb           PG → DuckDB 副本
  └─ pk_guard / ann / pre_listing
```

### 一次性修复（本次执行路径）

```
python repair_kline_fields.py                       # dry-run：打印三项缺口 + 计划
python repair_kline_fields.py --write               # 修 JSON（自动备份原文件）
python repair_kline_fields.py --purge-phantom --write   # 删幽灵行（自动备份 81 行到 backups/）
python repair_kline_fields.py --apply-pg --verify   # 单事务改 PG + 断言 JSON↔PG 三项一致
```

### 脚本内部结构

```
repair_kline_fields.py
├─ load_env()                读 D:\项目\数据文件\.env（不硬编码凭据）
├─ connect()                 core.pg.get_pg_conn()    ← RealDictCursor，行用 r["col"]
│                             【坑】get_raw_conn() 是裸 psycopg2、游标返回元组，按列名取数必须用 get_pg_conn()
├─ load_calendar()           交易日历 + max_date          → REQ-001
├─ load_amount_source()      tdx_kline_daily 的 (code,date)→amount 映射
├─ load_json()               reits_kline_daily.json（唯一真源）
├─ plan_return_fills()       W1 计划（只算不改）           → REQ-002
├─ plan_amount_fills()       W2 计划（只算不改）           → REQ-003
├─ plan_purge()              W3 计划（三重守卫 + 分级）     → REQ-004
├─ apply_to_json(plan)       原子写 + 备份 + coverage 元数据 → REQ-005
├─ load_pg_kline()           PG 行集合 → {code:[{date,close,volume}]}（供 plan_pg_purge）
├─ plan_pg_purge()           PG 侧幽灵行判定（重放三重守卫）  → SC-006-003
├─ pg_field_gap()            PG 侧「可回填」行数（早退判定）
├─ write_pg_purge_backup()   PG 删前落盘 pg_phantom_<ts>.csv
├─ apply_to_pg(purge_dates)  单事务 UPDATE×2 + DELETE×1，失败回滚 → REQ-006
│                             ⚠ 签名与 Gate 2 版不同：原 (conn, plan) 会漏删 PG 脏行，
│                               见 design-adjustments.yaml ADJ-001 / ADJ-002 / ADJ-003
├─ verify(json, pg)          三项计数一致断言               → REQ-006
└─ main()                    argparse；默认 dry-run
                              --write / --purge-phantom / --apply-pg / --verify / --daily
                              --json <path>（可测试性覆盖，见 Decision 8）
```

---

## Risks / Trade-offs

| 风险 | 等级 | 缓解措施 |
|---|---|---|
| 误删真实交易日数据 | **高** | 三重守卫（尤其守卫 2「严格历史」+ 守卫 3「周末或逐行重复」）；删前备份 81 行到 `backups/`；未分类行只告警 |
| 只改 JSON 未跑 build → PG 看似没变 | 中 | 一次性路径用 `--apply-pg` 显式改 PG；`--verify` 断言三项计数；编排路径由紧随的 build 保证 |
| 日历自身故障（`tdx_kline_daily` 缺真实交易日）→ 误判幽灵日 | **高** | 守卫 3 要求强指纹（周末/逐行重复）；守卫 2 排除最新一天；未分类只告警 |
| 除息日未复权收益率被误读为暴跌 | 中 | coverage 元数据 + 表注释标注口径；test-plan 断言 223 行除息行全部落在预期集合、|涨跌幅|>10% 的 5 行全部可解释（4 除息 + 1 上市次日） |
| `--apply-pg` 与 JSON 漂移 | 中 | 单事务 + 提交后 `verify()` 三项计数断言，不一致即非零退出 |
| 编排新增步影响每日 ETL | 中 | 幂等 + 无缺口早退；超时预算短；失败不阻断后续 build（沿用既有 `run_cmd` 语义，需在 BUILD 阶段确认） |
| JSON 原子写中断留下 .tmp | 低 | tmp + `os.replace`（同目录同盘，故 replace 原子）。**「启动时清理陈旧 .tmp」未实现**：实测无残留（TC-KFB-013 断言无残留 .tmp），按 YAGNI 不实现，降级为观察项 |
| 内存：JSON 16.87 MB + 51,567 行 | 低 | 全量载入内存（~100 MB 量级）可接受，与既有 `build_reits_duckdb.py` 同量级 |
| 一次性路径跳过 build → 其它 JSON 派生表不同步 | 低 | 本修复只碰 `reits_kline_daily`；其它表由每日 build 正常维护，无需为本次修复重建 |
