# Proposal: reits_kline_daily 字段级回填（daily_return_pct + amount）+ 非交易日脏行清理（STDD Change）

- **Change ID**: kline_field_backfill
- **日期**: 2026-09-14
- **作者**: archer (Agent)
- **审批**: 待 D哥 Gate 1 确认
- **取代关系**: 承接 `.stdd/changes/kline_amount_repair/proposal.md`（该提案未过 Gate 1、未实施）；本变更纳入其 amount + 05-03 范围，并把它 §3 中显式推迟的 `daily_return_pct` slice 一并做掉。

## 0. 由来

D哥 2026-09-14 指令：

> 待修复量（只读统计）：`daily_return_pct` 24,643 行 / 89 只；`amount` 178 行 / 89 只 …… 走 stdd

追加确认：

> 2026-05-03 是劳动节假期，所以数据是脏数据

## 1. 问题陈述（基于实证，2026-09-14 实查）

### 1.1 表基线

`business.reits_kline_daily`：**51,567 行 / 89 只 / 2021-06-21 ~ 2026-09-11**，13 列
（fund_code, fund_name, date, open, high, low, close, volume, amount, turnover_rate,
daily_return_pct, nav_premium_rate_pct, source）。`date` 为 **TEXT**。

### 1.2 缺口量测

| 字段 | NULL 行数 | 占比 | 拆解 |
|---|---|---|---|
| `daily_return_pct` | **24,732** | 47.96% | tdx 21,872 / tdx_offline 2,367 / sina 493 |
| `amount` | **259** | 0.50% | 2026-09-10+09-11 共 **178**（tdx 源，字段级缺口）+ 2026-05-03 共 **81**（幽灵日脏行） |

`daily_return_pct` 按年分布：2021 tdx 1,222 / 2022 tdx 3,555 / 2023 tdx 6,568 / 2024 tdx 9,552 /
2025 sina 78 / 2026 sina 414 + tdx 975 + tdx_offline 2,367。

### 1.3 daily_return_pct 的可填性（决定性）

| 校验项 | 结果 |
|---|---|
| 有 prev_close 可推导的行 | **24,643** |
| 其中落在非交易日（2026-05-03）的 | **1** → **净可填 24,642** |
| 无 prev_close 的行 | **89** = 每只标的的首行（构造性无解，保留 NULL）|
| 待填行的 prev_date 落在 tdx 交易日历之外 | **0** |
| `tdx_kline_daily` 含周末行 | **0**（洁净交易日历）|
| 待填行 prev_date 间隔分布 | 1天 19,475 / 2天 95 / 3天 4,581 / 4天 129 / 5天 124 / 6天 75 / 8天 54 / 10天 52 / 11天 58 |

> 间隔 > 5 天的全部是**周末 + 长假**（2023 国庆 09-28→10-09、2024 春节 02-08→02-19），
> **不存在数据空洞**。故 `lag(close)` 恒等于「上一交易日收盘」。

### 1.4 口径验证（本变更的核心依据）

对 `source='sina'` 的 26,835 个已有 prev_close 的行，比对「库内已存值」与「按公式计算值」：

| 指标 | 结果 |
|---|---|
| 完全吻合（\|diff\| < 0.0001） | **26,755** |
| 不吻合 | 80 |
| 80 处不吻合的日期分布 | **全部在 2026-05-03**（幽灵日，其 prev_close 被同日重复行污染）|
| **真实交易日吻合率** | **26,755 / 26,755 = 100%** |

> 结论：该列在库内的既有语义 = **未复权简单收益率** `(close / prev_close − 1) × 100`，
> 已被厂商（sina）自身数据 **100% 背书**。对 tdx / tdx_offline 行套用同一公式，
> 是**补齐列口径一致性**，而非引入新口径。

### 1.5 除息日语义（已知且预期，非缺陷）

待填的 24,642 行中有 **223 行**（64 只标的）落在 `reits_dividend.ex_div_date`。
未复权收益率在这些行会体现分红除权造成的机械跌幅。

实证：填完后 |涨跌幅| > 10%（超出 REITs 非首日 ±10% 涨跌幅限制）的行共 **5 行**，其中 **4 行是除息日**，
另有 1 行为上市次日涨停（508080 中金亦庄产业园REIT 2025-06-27 +10.0113%，该标的序列首行即 2025-06-26）：

| 标的 | 日期 | prev_close | close | 计算值 | 除息 |
|---|---|---|---|---|---|
| 508001 | 2024-06-28 | 8.452 | 7.508 | −11.169% | ✅ |
| 508008 | 2024-04-09 | 9.834 | 8.770 | −10.820% | ✅ |
| 180401 | 2023-05-18 | 7.562 | 6.750 | −10.738% | ✅ 每份派 0.727 元 |
| 508096 | 2023-11-13 | 10.943 | 9.798 | −10.463% | ✅ |

> 这是未复权口径的**预期行为**（sina 已有值同样如此）。复权收益率**不在本变更范围**。

### 1.6 amount 缺口的可回填性

| 校验项 | 结果 |
|---|---|
| 09-10/09-11 的 (fund_code,date) 在两表一一对应 | ✅ 89 + 89 全命中 |
| `tdx_kline_daily` 该两日 amount 非空 | ✅ 178/178（`source='tencent+tick_amount'`，逐笔还原，误差 < 0.2%）|
| 可由 `tdx_kline_daily` 直接回填的行数 | **178** |
| 2026-05-03 的 81 行 | ❌ 无源可取（幽灵日），随脏行清理一并消失 |

### 1.7 幽灵交易日判定（2026-05-03）

- 2026-05-03 为**周日**，属**劳动节假期**（D哥确认），A 股休市；
- `tdx_kline_daily` 该日 **0 行**；
- `reits_kline_daily` 中该日 81 行的 `close` + `volume` 与 **2026-04-30 逐行完全相同**，
  fund_code 集合亦完全一致（81 只，无独有代码）→ 判定为 **sina 源整批重复写入**；
- 该日是全表**唯一**不存在于 tdx 交易日历的日期。

### 1.8 根因（为什么缺口会持续复发）

| 事实 | 证据 |
|---|---|
| `reits_kline_daily` 由 `reits_kline_daily.json` **全量重建**，JSON 是唯一真源 | `_etl_tmp/build_reits_duckdb.py` |
| JSON 与 PG 当前**逐字段一致** | 见 §1.9 实测 |
| 每日新增的 tdx 类 bar **一律带 NULL `daily_return_pct`**（源通道不产出该字段） | `sync_kline_json_from_tdx.py` 写入路径；2026-09-07~09-11 五行 ret 全 NULL |
| 编排中的补录脚本**只补缺失键，不补字段 NULL** | `backfill_reits_kline_daily.py:205` 条件 `(c, ds) not in exists` |
| 唯一能补 amount 的脚本**不在编排内**，且只写 `tdx_kline_daily` | `backfill_kline_amount.py:188-194`；`daily_etl.py` 的 `DAILY_DEFAULT` 不含它 |

> 结论：**若不修机制，本次手工补齐会在次日新增数据时重新出现，且下一轮 build 可能把
> 「仅改 PG」的修复回滚。** 故本变更必须同时修 JSON，并把字段级补齐纳入编排。

### 1.9 JSON 真源核对

`D:\项目\数据文件\reits_kline_daily.json`（16.87 MB，generated_at 2026-09-12）：

| 指标 | JSON | PG | 一致 |
|---|---|---|---|
| 标的数 | 89 | 89 | ✅ |
| 总行数 | 51,567 | 51,567 | ✅ |
| `daily_return_pct` NULL | 24,732 | 24,732 | ✅ |
| `amount` NULL | 259 | 259 | ✅ |
| 2026-05-03 行数 | 81 | 81 | ✅ |
| source 分布 | tdx 21,872 / sina 27,328 / tdx_offline 2,367 | 同 | ✅ |

### 1.10 下游依赖核查（改标注前必查）

| 依赖点 | 事实 | 影响 |
|---|---|---|
| `sync_kline_json_from_tdx.py:246` | `WHERE source = 'tdx' AND turnover_rate > 0 AND volume > 0` 反算换手率分母 | 改 `source` 会让这 178 行退出样本 |
| 受影响标的是否会失去全部分母样本 | **0 只**（每只最少 11 个样本，中位数 78） | 实际无破坏，但属无谓副作用 |
| `fetch_tdx_kline.py:91` `SOURCE_PRIORITY` | 仅作用于 `tdx_kline_daily` / `tdx_kline_minute` | **不碰** `reits_kline_daily` |
| `normalize_unknown_source.py` | 有 `source='unknown' → 'tdx_offline'` 改标签先例 | 改标签在本项目有先例，非禁区 |

## 2. 目标

1. **W1｜daily_return_pct 回填**：对 **24,642** 行（剔除幽灵日）填
   `round(((close / prev_close − 1) * 100)::numeric, 4)`；89 只首行保持 NULL。
2. **W2｜amount 回填**：2026-09-10 / 09-11 共 **178** 行取自 `tdx_kline_daily`。
3. **W3｜幽灵日清理**：删除 2026-05-03 的 **81** 行（先备份切片到 `backups/`）。
4. **W4｜JSON 双写**：W1–W3 同时落到 `reits_kline_daily.json`，防止下轮 build 回滚。
5. **W5｜防复发**：把「字段级补齐 + 非交易日脏行清理」纳入每日编排（build 之前），幂等可重跑。

## 3. 范围边界

- **IN**：`business.reits_kline_daily`、`reits_kline_daily.json`、`daily_etl.py` 编排、新增/扩展的补录脚本、`.stdd/agent_tests/`。
- **OUT**：`business.tdx_kline_daily`（只读，不改）；`turnover_rate` / `nav_premium_rate_pct` 的历史空缺（另行 slice）。
- **OUT**：复权收益率、分红再投资收益率、`reits_dividend` 的任何写入。
- **OUT**：DuckDB 副本（`sync_pg_to_duckdb.py` 自 PG 全量重建，无需单独处理）。
- **OUT**：`2026-04-28` 等日期标的数不齐问题、sina 源历史数据全面体检。

## 4. 风险与处置

| 风险 | 等级 | 处置 |
|---|---|---|
| 只改 PG 不改 JSON → 下轮 build 回滚 | 高 | 双写；测试断言「重跑 build 后缺口不复现」 |
| 误删真实交易日数据（05-03） | 高 | 删除前先把 81 行备份到 `backups/`，并做「与 04-30 逐行对等」前置断言 |
| 把幽灵日当正常日填出假收益率 | 中 | 填值前用 `tdx_kline_daily` 交易日历过滤（已实测：仅排除 1 行） |
| 除息日未复权收益率被误读为暴跌 | 中 | 在 JSON `coverage` 与表注释记录口径；测试断言 223 行除息行全部落在预期集合 |
| 改 `source` 标注影响下游换手率分母 | 中 | 见 §1.10；决策见 D2 |
| 编排改动影响每日 ETL | 中 | 新增步骤幂等（无缺口即早退）；先 dry-run 再落库 |

## 5. 成功标准（可客观验证）

1. `reits_kline_daily` 中 `daily_return_pct IS NULL` 行数 = **89**（仅每只标的的首行）。
2. `reits_kline_daily` 中 `amount IS NULL` 行数 = **0**。
3. `reits_kline_daily` 不再存在 `2026-05-03` 的任何行。
4. 对新增的 24,642 个收益率值，用**独立于写库路径**的实现（Python，非写库用的 SQL）重算，
   偏差 > 1e-4 的行数 = **0**；且填完后 |涨跌幅| > 10% 的行必须**全部**是除息日。
5. `reits_kline_daily.json` 与 PG 表逐字段一致（行数 + 两个 NULL 计数 + 05-03 行数 = 0）。
6. 重跑一次完整 `build` 后，标准 1–3 仍成立。
7. 编排新增步骤在「无缺口」时幂等早退，跑两次结果完全一致。

## 6. 待 D哥确认的关键决策点

- **D1｜2026-05-03 的 81 行处置**：拟**直接删除**（先备份到 `backups/`）。
  备选：保留并改 `source='sina_duplicate'` 标记。
- **D2｜amount 回填行的 `source` 标注**：拟**保持 `source='tdx'` 不变**——新证据显示
  `sync_kline_json_from_tdx.py:246` 以 `source='tdx'` 反算换手率分母，改标注会让这 178 行
  退出该样本（实测无标的失去全部分母，但属无谓副作用）。溯源改由 JSON `coverage` 元数据 +
  `backups/` manifest + 测试报告承担。
  备选：改为 `tdx+tick_amount`（与 `tdx_kline_daily` 口径对齐）。
- **D3｜变更组织方式**：拟**新建 `kline_field_backfill`**，并标记 `kline_amount_repair`
  为 superseded（旧提案未过 Gate 1、未实施，无损失）。
  备选：直接在 `kline_amount_repair` 上扩范围（ID 会偏窄）。
- **D4｜daily_return_pct 口径**：拟按**未复权**填（与 sina 既有值 100% 一致）。
  备选：除息日留 NULL / 另算复权（会破坏列口径一致性，不推荐）。
- **D5｜是否新增 provenance 列**：拟**不加**新列（收益率可由 close 复算，provenance 由
  `source` 列隐含）；amount 的 provenance 见 D2。
  备选：加 `daily_return_src` / `amount_src` 标记列（需 schema 变更）。
