# Proposal: reits_kline_daily 成交额缺口回填 + 非交易日重复行清理（STDD Change）

- **Change ID**: kline_amount_repair
- **日期**: 2026-09-14
- **作者**: archer (Agent)
- **审批**: D哥 已授权「要回填，按项目 AGENTS.md 的 enforce_stdd: true，走 STDD 立规格再落库。2026-05-03 那 81 行 sina 源缺口（非交易日却有条目）一并处理」

## 1. 问题陈述（基于实证）

### 1.1 缺口量测（2026-09-14 17:35 实查）

`business.reits_kline_daily`（权威日线，51,567 行，2021-06-21 ~ 2026-09-11）中 `amount IS NULL` 共 **259 行**，拆解：

| 日期 | 行数 | 星期 | source | 性质 |
|---|---|---|---|---|
| 2026-09-10 | 89 | 周四 | tdx | **字段级缺口**（行在、amount 缺） |
| 2026-09-11 | 89 | 周五 | tdx | **字段级缺口**（行在、amount 缺） |
| 2026-05-03 | 81 | **周日** | sina | **非交易日脏行**（整批重复） |

对照 `business.tdx_kline_daily`（51,486 行）：`amount` **100% 非空**，09-10/09-11 各 89 行 `source='tencent+tick_amount'`。

两库（PG / DuckDB `D:/duckdb/reits.duckdb`）在该表上完全一致，**不存在跨库差异**；差异发生在**同一库内的两张表之间**。

### 1.2 字段级缺口的可回填性（已抽样验证）

| 校验项 | 结果 |
|---|---|
| 09-10/09-11 的 (fund_code,date) 键在两表是否一一对应 | ✅ 89 + 89 行全命中 |
| close / volume 是否逐行一致（抽样 6 行） | ✅ 完全一致 |
| tdx 侧 amount 是否非空 | ✅ 178/178 非空 |
| 可由 `tdx_kline_daily` 直接回填的行数 | **178** |

### 1.3 非交易日脏行判定（决定性证据）

- `2026-05-03` 为**周日**，`tdx_kline_daily` 该日 **0 行**（独立交易日历否证）；
- 81 行中有 **81 行（100%）** 其 `close` + `volume` 与 **2026-04-30 逐行完全相同**，且 fund_code 集合完全一致（81 只，无独有代码）→ 判定为 **sina 源整批重复写入**，非真实交易日数据。

### 1.4 机制根因（为什么缺口长期无人发现）

| 事实 | 证据 |
|---|---|
| `reits_kline_daily` 由 `reits_kline_daily.json` **全量重建**，JSON 是唯一真源 | `_etl_tmp/build_reits_duckdb.py:122-128`（`load("reits_kline_daily.json")` → `create(...)`） |
| 每日编排的两步补录**只补"缺失键"，不补"字段 NULL"** | `backfill_reits_kline_daily.py:205` 条件为 `(c, ds) not in exists`；`sync_kline_json_from_tdx.py` 走 `NOT EXISTS` 只补不覆盖 |
| 唯一能补 amount 的脚本**不在编排内**，且只写 `tdx_kline_daily` | `backfill_kline_amount.py:188-194`（`UPDATE business.tdx_kline_daily`）；`daily_etl.py:615` 的 `DAILY_DEFAULT` 不含它 |
| JSON 侧同样带缺口 | `reits_kline_daily.json`（09-12 02:07）：09-10/09-11 各 89 条 `amount=null`；05-03 81 条且与 04-30 逐行相同 |

**结论**：缺口不是单点失误，而是"字段级补齐"环节在编排中**空缺**所致；若不修机制，手动补完下一轮 build 仍可能再被 JSON 回写覆盖（本变更须同时修 JSON）。

## 2. 目标

1. **回填**：`reits_kline_daily` 09-10/09-11 共 178 行的 `amount`，取自 `tdx_kline_daily`（逐笔还原值），并标注来源。
2. **清理**：删除 `reits_kline_daily` 中 2026-05-03 的 81 行重复脏数据（PG + JSON 同步删除）。
3. **同步 JSON**：上述两项同时落到 `reits_kline_daily.json`（唯一真源），防止下次 `build` 回滚。
4. **防复发**：把"字段级 amount 对齐 + 非交易日重复行清理"纳入每日编排（`build` 之前），幂等可重跑。

## 3. 范围边界

- **IN**：`business.reits_kline_daily` 表、`reits_kline_daily.json`、`daily_etl.py` 编排、复用/扩展的补录脚本。
- **OUT**：`business.tdx_kline_daily`（本变更只读它，不改）；其余 K 线相关表（`tdx_kline_minute` 等）。
- **OUT（后续 slice，需单独授权）**：`reits_kline_daily` 其它字段（`turnover_rate` / `daily_return_pct` / `nav_premium_rate_pct`）的历史空缺、`2026-04-28` 等日期的标的数不齐问题、`sina` 源历史数据全面体检。
- **OUT**：DuckDB 副本无需单独处理（`sync_pg_to_duckdb.py` 全量重建自 PG）。

## 4. 风险与处置

| 风险 | 等级 | 处置 |
|---|---|---|
| 误删真实交易日数据 | 高 | 删除前**先备份**该 81 行到 `backups/`（SQL/CSV），并做"04-30 逐行对等"前置断言 |
| 只改 PG 不改 JSON → 下轮 build 回滚 | 高 | 双写并在测试中验证"重跑 build 后缺口不复现" |
| 回填值错误（逐笔还原误差） | 中 | 回填前校验 close/volume 对齐；amount 标注来源以便溯源；已知还原误差 < 0.2% |
| 编排改动影响每日 ETL | 中 | 新增步骤幂等（无缺口即早退）；先 dry-run 验证再落库 |

## 5. 成功标准（可客观验证）

1. `reits_kline_daily` 中 `amount IS NULL` 行数 = **0**。
2. `reits_kline_daily` 不再存在 `2026-05-03` 的任何行。
3. `reits_kline_daily.json` 与 PG 表**逐字段一致**（行数与关键字段抽样比对）。
4. 重跑一次完整 `build` 后，上述 1、2 仍成立（即 JSON 已同步、未被回滚）。
5. 编排中新增的防复发步骤在"无缺口"时**幂等早退**且不改变任何行（跑两次结果一致）。

## 6. 待 D 哥确认的关键决策点

- **D1｜2026-05-03 的 81 行处置方式**：拟**直接删除**（先备份切片到 `backups/`）。备选：保留并改 `source='sina_duplicate'` 标记。请确认取哪种。
- **D2｜amount 来源标注**：拟将回填行 `source` 由 `tdx` 改为 `tdx+tick_amount`（与 `tdx_kline_daily` 口径对齐、可溯源）。备选：保持 `source='tdx'` 不变，仅补 amount。
