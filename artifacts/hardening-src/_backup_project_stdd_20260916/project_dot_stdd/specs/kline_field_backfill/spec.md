# Spec: kline_field_backfill

> **reits_kline_daily 字段级回填（daily_return_pct + amount）+ 非交易日脏行清理**

| 项 | 值 |
|---|---|
| capability | `kline_field_backfill` |
| change_id | `kline_field_backfill` |
| task_type | `data-migration` |
| 源变更 | `.stdd/archive/2026-09-14-kline_field_backfill/`（已归档） |
| 合并日期 | 2026-09-15（STDD Phase 4 Step 2） |
| 规模 | 18 Requirements / 24 Scenarios |

> 本 capability 为 **NEW**（项目首个合并进 `specs/` 的 capability）。

## 0. 产物与常量

| 键 | 值 |
|---|---|
| `script` | `repair_kline_fields.py` |
| `test` | `.stdd/agent_tests/test_kline_field_backfill.py` |
| `truth_source` | `reits_kline_daily.json` |
| `target_table` | `business.reits_kline_daily` |
| `calendar_source` | `business.tdx_kline_daily` |
| `backup_dir` | `backups/` |
| `orchestrator` | `daily_etl.py` |

| 常量 | 值 |
|---|---|
| `return_formula` | `round(((close / prev_close - 1) * 100), 4)` |
| `expected_fill_return` | `24642` |
| `expected_null_return_after_fill_only` | `90` |
| `expected_null_return_after` | `89` |
| `expected_fill_amount` | `178` |
| `expected_null_amount_after_fill_only` | `81` |
| `expected_null_amount_after` | `0` |
| `expected_total_rows_after_purge` | `51486` |
| `expected_purged_rows` | `81` |
| `phantom_date` | `2026-05-03` |
| `exdiv_rows_in_fill_set` | `223` |

## 1. 需求清单

### REQ-001-001 · 交易日历基准取数

> 系统 SHALL 以 `business.tdx_kline_daily` 的 DISTINCT date 集合作为交易日历基准， 并同时取出 max(date) 作为「历史边界」；日历集合 SHALL NOT 含任何周六/周日。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-001-001` | 已连接 business schema，`tdx_kline_daily` 有数据 | 加载交易日历 | 系统 SHALL 返回 (calendar:set[str], max_date:str) | calendar 中 SHALL NOT 存在任何周六或周日 | proposal §1.3「tdx_kline_daily 含周末行 = 0」 |

### REQ-001-002 · 日历缺失时保护性中止

> 交易日历为空时系统 SHALL 中止执行并报错，SHALL NOT 执行任何写入或删除。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-001-002` | `tdx_kline_daily` 为空（模拟上游全断） | 加载交易日历 | 系统 SHALL 抛出/返回错误并中止 | SHALL NOT 修改 JSON 与 PG 的任何行 |  |

### REQ-002-001 · daily_return_pct 回填（未复权）

> 对 JSON 中 `daily_return_pct` 为 null、且其同一标的上一交易日的 close 存在且 > 0、 且该行 date 落在交易日历内的行，系统 SHALL 填入 `round(((close / prev_close - 1) * 100), 4)`。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-002-001` | JSON 中某行 daily_return_pct = null，同标的上一行 close = 2.056，本行 close = 2.08 | 执行回填 | 该行 daily_return_pct SHALL = 1.1673 |  | proposal §1.4（sina 真实交易日 26,755/26,755 吻合该公式） |
| `SC-002-002` | 回填与幽灵行清理均已执行完毕 | 统计全表 daily_return_pct IS NULL 的行 | 行数 SHALL = 89（= 标的数） | 这 89 行 SHALL 全部是各标的 date 最小的一行 | proposal §1.3「无 prev_close 的行 = 89 = 每只标的的首行」； 顺序依赖：只回填未清理时为 90（多出幽灵行 180503） |

### REQ-002-002 · 厂商已有值不被改写

> 回填 SHALL 只作用于 null 行；`daily_return_pct` 已有值的行 SHALL 逐字节保持不变。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-002-003` | 某行 daily_return_pct = -0.4883（sina 厂商值，与公式计算结果不同） | 执行回填 | 该行 SHALL 仍为 -0.4883 |  | proposal §1.4（80 处不符全在幽灵日，非 null 行须原样保留） |

### REQ-002-003 · 幽灵日不参与收益率回填

> 系统 SHALL NOT 为 date 不在交易日历内的行计算收益率。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-002-004` | JSON 中存在 180503 于 2026-05-03（非交易日）且 daily_return_pct = null | 执行回填 | 该行 SHALL NOT 被填入任何收益率 |  | proposal §1.3「净可填 24,642（剔除幽灵日 1 行）」 |

### REQ-003-001 · amount 回填

> 对 JSON 中 `amount` 为 null、且 (fund_code, date) 在 `business.tdx_kline_daily` 存在非空 amount 的行，系统 SHALL 填入该值。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-003-001` | JSON 中 2026-09-10/09-11 共 178 行 amount = null；tdx_kline_daily 同键 amount 非空 | 执行回填与幽灵行清理 | 这 178 行 SHALL 全部被填入非空 amount | 全表 amount IS NULL 的行数 SHALL = 0 | proposal §1.6；顺序依赖：只回填未清理时为 81（= 幽灵行数） |

### REQ-003-002 · 无源 amount 显式报告

> 无源可取的 amount 空值行 SHALL 保持 null，且系统 SHALL 报告其数量与键，SHALL NOT 静默吞掉。

- 置信度：`medium` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-003-002` | 某行 amount = null 且 tdx_kline_daily 无同键行或同键 amount 也为 null | 执行回填 | 该行 SHALL 保持 null | 系统 SHALL 在输出中列出该行 (fund_code, date) |  |

### REQ-004-001 · 幽灵交易日行删除（三重守卫）

> 系统 SHALL 删除同时满足以下三条的行：(1) date 不在交易日历内； (2) date < 交易日历最大日期；(3) date 为周六/周日，或该日全部行与「上一交易日」 同标的行在 (close, volume) 上逐行完全相同。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-004-001` | 2026-05-03 的 81 行，为周日且 close+volume 与 2026-04-30 逐行相同 | 执行清理 | 这 81 行 SHALL 被删除 | 全表 SHALL NOT 再存在 date = '2026-05-03' 的行 | proposal §1.7（劳动节假期 + 逐行重复） |
| `SC-004-002` | 某行 date 不在日历内但 date = 日历最大日期（可能是当日尚未入库） | 执行清理 | 该行 SHALL NOT 被删除 | 系统 SHALL 输出告警 |  |

### REQ-004-002 · 未分类的非交易日行只告警不删除

> 不满足删除条件 (3) 的「date 不在日历内且 date < 日历最大日期」的行， 系统 SHALL 只输出 WARNING 并列出明细，SHALL NOT 删除。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-004-003` | 某行 date 不在日历内、date < 日历最大日期，但该行是工作日且不与上一交易日重复 | 执行清理 | 该行 SHALL 保留 | 系统 SHALL 输出 WARNING 含该 date 与行数 |  |

### REQ-004-003 · 删除前强制备份

> 执行任何删除前，系统 SHALL 先把被删行的完整内容写入 `backups/phantom_<timestamp>.csv`。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-004-004` | 待删 81 行 | 执行清理 | `backups/phantom_<ts>.csv` SHALL 存在且行数 = 81 | 该文件 SHALL 含 fund_code/date/open/high/low/close/volume/amount/turnover_rate/daily_return_pct/source 全部列 |  |

### REQ-005-001 · JSON 真源原子写入

> 对 `reits_kline_daily.json` 的写入 SHALL 走「先写 .tmp 再 os.replace」的原子替换， 且写入前 SHALL 备份原文件到 `backups/`。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-005-001` | 执行 `--write` | 写入 JSON | 目录中 SHALL 出现 `backups/reits_kline_daily_<ts>.json` 备份 | 主 JSON SHALL 通过 tmp + os.replace 完成替换（无中间态可见） | proposal §1.8（JSON 是唯一真源） |

### REQ-005-002 · coverage 元数据记录口径

> JSON 的 `coverage` 块 SHALL 记录本次回填的口径与计数： `return_fill_count` / `amount_fill_count` / `purged_rows` / `return_caliber`（未复权）/ `last_repair_at`；且 SHALL 保持既有 coverage 字段不丢。

- 置信度：`medium` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-005-002` | 执行 `--write` | 读取 JSON 的 coverage | coverage SHALL 含上述 5 个新字段 | 既有字段（fund_count/total_records/date_range）SHALL 保持存在且值自洽 |  |

### REQ-006-001 · 一次性 PG 应用（--apply-pg）

> 传入 `--apply-pg` 时，系统 SHALL 在单个 PG 事务内执行与 JSON 等价的 UPDATE（daily_return_pct + amount）与 DELETE（幽灵行），提交后 SHALL 断言 PG 与 JSON 在「null 收益率行数 / null amount 行数 / 幽灵日行数」三项上一致。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-006-001` | 已 `--write` 修复 JSON，PG 尚未更新 | 执行 `--apply-pg` | PG 的 daily_return_pct IS NULL 行数 SHALL = 89 | PG 中 date = '2026-05-03' 的行数 SHALL = 0 |  |
| `SC-006-002` | 已 `--apply-pg` 完成 | 对比 PG 与 JSON | 上述三项计数 SHALL 完全一致 | 不一致时 SHALL 以非零退出码失败 |  |
| `SC-006-003` | JSON 已修复完成（plan.purge 为空），但 PG 仍残留非交易日脏行 | 执行 `--apply-pg` | 系统 SHALL 从 **PG 自身行集合** 重放三重守卫得到待删日期（而非沿用 JSON 计划） | SHALL 严格按该日期集合发 DELETE，且与两项 UPDATE 同处一个事务 | 执行期发现：`plan.purge` 由 JSON 推导，JSON 修好后即为空，若 `--apply-pg` 沿用该空计划则 PG 脏行永远删不掉（2026-09-14 实测 json_purge=0 而 PG 实有 81 行）。 |
| `SC-006-004` | 完整跑过一次 `daily_etl.py`（含 json/build 与末尾的 sync_duckdb） | 对比 JSON / PG / DuckDB 副本三者的四项计数 | 三者 SHALL 完全一致（总行数 / null 收益率行数 / null amount 行数 / 幽灵日行数） |  | 用户报缺陷时即指出「postgresql 与 duckdb 都有数据」。DuckDB 副本 `D:\\duckdb\\reits.duckdb` 由 sync_pg_to_duckdb.py 自 PG 反向重建， 只验 JSON↔PG 会漏掉副本仍停留在旧态的情况。 |

### REQ-007-001 · 编排防复发

> `daily_etl.py` 的 `DAILY_DEFAULT` SHALL 在 `sync_kline_json` 之后、`json`（build）之前 插入 `repair_kline` 步；该步 SHALL 只写 JSON，PG 由紧随其后的 build 全量重建传播。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-007-001` | `daily_etl.py --dry-run` | 打印计划 | 计划中 SHALL 出现 repair_kline，且位置在 sync_kline_json 之后、json 之前 |  |  |
| `SC-007-002` | 完整跑一次 `daily_etl.py`（含 build） | 检查 PG | 三项成功标准 SHALL 仍成立（JSON 修复未被 build 回滚） |  |  |

### REQ-008-001 · 幂等

> 连续执行两次相同命令 SHALL 得到逐字节相同的 JSON，且第二次为空操作（无备份写入、无行变更）。

- 置信度：`high` ｜ 验证层级：`acceptance` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-008-001` | 已执行过一次 `--write` | 再次执行 `--write` | JSON 内容的 SHA256 SHALL 与第一次执行后完全一致 | 输出 SHALL 报告「无缺口，跳过写入」 |  |

### REQ-008-002 · 无缺口早退

> 无任何缺口时，系统 SHALL 早退且 SHALL NOT 创建备份文件或修改任何文件。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-008-002` | 三项缺口均为 0 | 执行 `--write` | 系统 SHALL 输出早退信息 | `backups/` 中 SHALL NOT 新增文件 |  |

### REQ-009-001 · 默认 dry-run

> 不带 `--write` 时，系统 SHALL 只打印缺口统计与执行计划，SHALL NOT 修改任何文件或数据。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-009-001` | 存在缺口 | 不带 `--write` 执行 | 输出 SHALL 含三项缺口计数 | JSON 的 SHA256 与 PG 三项计数 SHALL 保持不变 |  |

### REQ-009-002 · 删除需显式授权

> 删除幽灵行 SHALL 需要显式 `--purge-phantom`，SHALL NOT 由 `--write` 单独触发。

- 置信度：`high` ｜ 验证层级：`unit` ｜ 实现状态：`to-implement`

| Scenario | Given | When | Then | And | 证据 / 备注 |
|---|---|---|---|---|---|
| `SC-009-002` | 存在 81 行幽灵行 | 只传 `--write`（不带 --purge-phantom） | 幽灵行 SHALL 保留 | 系统 SHALL 输出提示「检测到 N 行待清理，加 --purge-phantom 执行」 |  |

## 2. 变更历史

| 日期 | change | 动作 |
|---|---|---|
| 2026-09-14 | `kline_field_backfill` | Gate 1/2 通过；Phase 3 实施；Gate 3 批准 |
| 2026-09-15 | `kline_field_backfill` | 归档并合并进本文件（Phase 4 Step 2） |

## 3. Gate 2 后增量 Scenario（执行期发现）

| Scenario | 说明 | 溯源 |
|---|---|---|
| `SC-006-003` | PG 侧待删日期须从 PG 自身行集合独立推导 | ADJ-001/002/003 |
| `SC-006-004` | 三系统一致性 JSON↔PG↔DuckDB | ADJ-004/005 |
