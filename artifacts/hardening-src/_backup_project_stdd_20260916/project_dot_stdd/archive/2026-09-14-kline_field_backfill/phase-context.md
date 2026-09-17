# Phase Context: kline_field_backfill

> Phase 2 (SPEC) 完成时生成 | 2026-09-14 20:44 +0800
> 供 Phase 3 (BUILD) 起手时快速恢复上下文

## 一句话

把 `business.reits_kline_daily` 的 `daily_return_pct` 补 24,642 行、`amount` 补 178 行、
删掉 2026-05-03 的 81 行幽灵数据；修复落在 **JSON 真源**，PG 由 build 传播。

## 关键决策（8 条，Phase 3 不得静默偏离）

| # | 决策 | 要点 |
|---|---|---|
| 1 | **以 JSON 为唯一写入目标** | PG 是 JSON 的纯函数（`build_reits_duckdb.py::create` = `CREATE OR REPLACE ... AS SELECT *`）。日常路径只写 JSON；`--apply-pg` 仅为一次性修复省掉全量 build |
| 2 | 收益率**未复权** | `round(((close/prev_close-1)*100), 4)`；sina 真实交易日 26,755/26,755 背书 |
| 3 | 幽灵行**三重守卫** | 不在日历 ∧ 严格早于日历最大日 ∧ (周末 ∨ 与上一交易日逐行重复)；未分类只告警 |
| 4 | amount 行 `source` **保持 `'tdx'`** | 因 `sync_kline_json_from_tdx.py:246` 用 `source='tdx'` 反算换手率分母 |
| 5 | 编排插在 `sync_kline_json` 之后、`json` 之前 | 见 `daily_etl.py:615-616` |
| 6 | 新增独立脚本 `repair_kline_fields.py` | 不扩展 `backfill_reits_kline_daily.py`（职责不同） |
| 7 | **不加** provenance 列 | 收益率可由 close 复算 |
| 8 | 支持 `--json <path>` | 让写入类测试在临时副本上跑，不碰生产 JSON |

## 必须遵守的项目约定

- `core/pg.py` 游标是 **DictCursor** → 行用 `r["col"]`，**不要**元组解包（上一变更踩过）
- 凭据从 `D:\项目\数据文件\.env` 读，**禁止硬编码**
- 解释器：`VENV_PY = C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe`
  （注意是 `.workbuddy`，不是 `.workbuddy-ai`）
- Git Bash 给原生 exe 传路径必须用 Windows 格式 `D:\...`
- 中文输出需 `PYTHONIOENCODING=utf-8`
- 断言一律用 `== 期望值`，不用 `>N` 这类弱断言

## 顺序依赖（自审抓到的坑，务必在实现与断言中体现）

```
daily_return_pct :  24,732(初始 NULL) − 24,642(回填) = 90  − 1(幽灵行 180503) = 89
amount           :  259(初始 NULL)    − 178(回填)    = 81  − 81(幽灵行全删)   = 0
总行数            :  51,567 − 81 = 51,486  (== tdx_kline_daily 行数)
```

## 数值锚点（全部来自实测，不得改）

| 量 | 值 |
|---|---|
| 初始总行数 | 51,567 |
| 初始 ret NULL | 24,732 |
| 初始 amount NULL | 259 |
| 回填收益率行数 | 24,642 |
| 回填 amount 行数 | 178 |
| 待删幽灵行 | 81（date = 2026-05-03）|
| 回填后 ret NULL | 89（= 标的数，各标的首行）|
| 除息日落在回填集合 | 223 行 / 64 只 |
| \|涨跌幅\|>10% 行数 | 5（**4 行除息日 + 1 行上市次日涨停**）|

## 产出物清单

| 文件 | 状态 |
|---|---|
| `.stdd/changes/kline_field_backfill/proposal.md` | ✅ 已锁（Gate 1）|
| `.stdd/changes/kline_field_backfill/spec.yaml` | ✅ 已锁（Gate 2）|
| `.stdd/changes/kline_field_backfill/design.md` | ✅ 已锁（Gate 2）|
| `.stdd/changes/kline_field_backfill/test-plan.md` | ✅ 已锁（Gate 2）|
| `.stdd/agent_tests/test_kline_field_backfill.py` | ⬜ Phase 3 产出 |
| `repair_kline_fields.py` | ⬜ Phase 3 产出 |
| `daily_etl.py`（插入 repair_kline 步） | ⬜ Phase 3 产出 |
| `.stdd/changes/kline_field_backfill/test-report.md` | ⬜ Phase 3 产出 |

## Phase 3 附加约束

- 三个写动作（`--write` / `--purge-phantom` / `--apply-pg`）真正执行前必须再次向 D哥展示
  「将影响行数 + 备份路径」并取得确认（高于流程默认，源于项目红线「现库写入须逐表确认」）。
- 严格 RED→GREEN→REFACTOR：先写测试并观察到预期失败。
- `--purge-phantom` 执行前必须确认 `backups/phantom_<ts>.csv` 已落盘且行数 = 81。
