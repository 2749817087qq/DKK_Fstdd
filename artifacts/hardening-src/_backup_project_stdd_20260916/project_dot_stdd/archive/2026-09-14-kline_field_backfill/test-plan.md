# Test Plan: kline_field_backfill

> 版本：v1 | 创建日期：2026-09-14
> 对应 Phase 2 Spec：`.stdd/changes/kline_field_backfill/spec.yaml`（18 Requirements / 24 Scenarios）
> 测试脚本：`.stdd/agent_tests/test_kline_field_backfill.py`

## 一、测试策略

### 1.1 测试金字塔

本变更属 `data-migration` 类型，测试重心压在**纯函数层**与**只读不变量断言层**，对写库路径只做一次受控的显式执行：

| 层次 | 占比 | 内容 | 是否触碰数据 |
|---|---|---|---|
| 单元（纯函数 + fixture） | ~60% | 日历加载、收益率计算、幽灵行三重守卫分类、幂等判定 | ❌ 内存 fixture |
| 集成（只读断言） | ~30% | 在真实 JSON + 真实 PG 上断言三项计数与集合性质 | 只读 |
| 一次性受控执行 | ~10% | `--write` / `--purge-phantom` / `--apply-pg` 各执行一次（带备份） | ✅ 写，需授权 |

### 1.2 测试原则

- **写库只走一次受控路径**：测试套件本身**不**写 PG；写库由显式命令执行，测试套件随后只读验证结果（沿用 `announcement_inventory` 的既有做法）。
- **纯函数用 fixture 隔离**：幽灵行判定等破坏性逻辑用内存构造的小型 JSON 夹具验证，可在任意时刻安全重跑。
- **可测试性参数**：脚本支持 `--json <path>` 覆盖真源路径，使幂等/写入类用例可在临时副本上验证，不触碰生产 JSON。
- **断言必须可证伪**：所有计数断言写成 `== 期望值`，不用「>0」这类弱断言（`announcement_inventory` 的 T2a 用 `>20000` 属反例，本次不重复）。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---|---|---|---|
| `.stdd/agent_tests/test_announcement_inventory.py` | 11 | 集成 | announcements / announcement_files（本变更不涉及，仅作回归基线） |
| `.stdd/agent_tests/test_announcement_sync_all.py` | 8 | 集成 | announcements web 层（本变更不涉及） |
| `.stdd/agent_tests/test_kline_field_backfill.py` | **25（新增）** | 单元 + 集成 | 本变更全部 24 个 Scenario + 1 个除息日语义补充 |

## 二、详细测试案例

### 功能 1：交易日历基准（REQ-001）

#### 案例 1.1 — 日历取数与周末洁净性

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-001 |
| **对应 Spec** | kline_field_backfill → SC-001-001 |
| **优先级** | P0 |
| **预置条件** | `set -a; . .env; set +a` 已执行；`tdx_kline_daily` 有数据 |
| **输入** | `load_calendar(conn)` |
| **预期结果** | 返回 `(calendar, max_date)`；`len(calendar) > 0`；`max_date == max(calendar)`（动态，不硬编码；日历随外部采集推进）；`calendar` 中 `dow ∈ {0,6}` 的天数 == **0** |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 日历为空时保护性中止

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-002 |
| **对应 Spec** | kline_field_backfill → SC-001-002 |
| **优先级** | P0 |
| **预置条件** | 以 monkeypatch 令 `load_calendar` 返回空集合 |
| **输入** | `main(['--write'])` |
| **预期结果** | 进程以非零码退出；输出含中止原因；JSON 的 SHA256 与执行前一致 |
| **当前状态** | ❌ 测试缺 |

### 功能 2：daily_return_pct 回填（REQ-002）

#### 案例 2.1 — 公式正确性（含 sina 真实值交叉验证）

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-003 |
| **对应 Spec** | kline_field_backfill → SC-002-001 |
| **优先级** | P0 |
| **预置条件** | 已 `--write` 修复 JSON |
| **输入** | 用**独立于写库路径**的 Python 实现对全部已填行重算 |
| **预期结果** | 偏差 > 1e-4 的行数 == **0**；且对 `source='sina'` 的 26,755 个真实交易日行，重算值与原厂商值偏差 > 1e-4 的行数 == **0** |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — 回填后 NULL 恰为各标的首行

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-004 |
| **对应 Spec** | kline_field_backfill → SC-002-002 |
| **优先级** | P0 |
| **预置条件** | **回填与幽灵行清理均已执行**（顺序依赖：只回填时为 90，清理删掉幽灵行 180503 的 NULL 后才为 89） |
| **输入** | `SELECT count(*) FROM ... WHERE daily_return_pct IS NULL` + 逐标的 `min(date)` 集合比对 |
| **预期结果** | 计数 == **89**；且这 89 个 `(fund_code, date)` 集合 == 各标的 `min(date)` 集合（完全相等） |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — 厂商已有值不被改写

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-005 |
| **对应 Spec** | kline_field_backfill → SC-002-003 |
| **优先级** | P0 |
| **预置条件** | 执行前先快照全部「非 null」行的 `(fund_code, date, daily_return_pct)` |
| **输入** | `--write` 后逐一比对快照 |
| **预期结果** | 变更行数 == **0**；特别地 `('180101','2026-05-03')` 的 `-0.4883` 若该行存在则必须原样（该行属幽灵行，见 TC-KFB-009） |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.4 — 幽灵日不参与收益率回填

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-006 |
| **对应 Spec** | kline_field_backfill → SC-002-004 |
| **优先级** | P0 |
| **预置条件** | 内存 fixture：含 `180503 / 2026-05-03 / daily_return_pct=null`，日历不含 `2026-05-03` |
| **输入** | `plan_return_fills(fixture, calendar)` |
| **预期结果** | 计划中不含该行；计划条数 == **24,642** |
| **当前状态** | ❌ 测试缺 |

### 功能 3：amount 回填（REQ-003）

#### 案例 3.1 — 178 行全量回填

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-007 |
| **对应 Spec** | kline_field_backfill → SC-003-001 |
| **优先级** | P0 |
| **预置条件** | 已 `--write` + `--apply-pg` |
| **输入** | `SELECT count(*) FROM reits_kline_daily WHERE amount IS NULL` |
| **预期结果** | PG == **0**；JSON 中 `amount is None` 行数 == **0**；2026-09-10/09-11 共 178 行的 `amount` 与 `tdx_kline_daily` 同键值**逐行相等** |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — 无源 amount 显式报告

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-008 |
| **对应 Spec** | kline_field_backfill → SC-003-002 |
| **优先级** | P1 |
| **预置条件** | 内存 fixture：一行 `amount=null` 且源映射中无同键 |
| **输入** | `plan_amount_fills(fixture, src_map)` |
| **预期结果** | 该行保持 null；返回的 `unresolved` 列表含该 `(fund_code, date)`；输出中可见该键 |
| **当前状态** | ❌ 测试缺 |

### 功能 4：幽灵交易日行清理（REQ-004）

#### 案例 4.1 — 2026-05-03 的 81 行被删除

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-009 |
| **对应 Spec** | kline_field_backfill → SC-004-001 |
| **优先级** | P0 |
| **预置条件** | 已执行 `--purge-phantom --write` + `--apply-pg` |
| **输入** | PG 与 JSON 双查 `date = '2026-05-03'` |
| **预期结果** | PG 行数 == **0**；JSON 行数 == **0**；全表总行数 == **51,486**（= 51,567 − 81，且与 `tdx_kline_daily` 行数相等） |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — 最新一天不被误删

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-010 |
| **对应 Spec** | kline_field_backfill → SC-004-002 |
| **优先级** | P0 |
| **预置条件** | 内存 fixture：`date = max(calendar)` 且不在 calendar 中（模拟当日未入库） |
| **输入** | `plan_purge(fixture, calendar, max_date)` |
| **预期结果** | 该行**不在**删除集合中；出现在 warn 集合中 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.3 — 未分类非交易日行只告警

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-011 |
| **对应 Spec** | kline_field_backfill → SC-004-003 |
| **优先级** | P0 |
| **预置条件** | 内存 fixture：一行 `date=2024-10-02`（工作日、不在 calendar、且与上一交易日不重复） |
| **输入** | `plan_purge(fixture, calendar, max_date)` |
| **预期结果** | 该行**不在**删除集合中；在 warn 集合中；日志含该 date 与行数 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.4 — 删除前强制备份完整列

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-012 |
| **对应 Spec** | kline_field_backfill → SC-004-004 |
| **优先级** | P0 |
| **预置条件** | `--purge-phantom --write` 已执行 |
| **输入** | 读取 `backups/phantom_*.csv` |
| **预期结果** | 文件存在；数据行数 == **81**；表头含 `fund_code,date,open,high,low,close,volume,amount,turnover_rate,daily_return_pct,source` 全部 11 列 |
| **当前状态** | ❌ 测试缺 |

### 功能 5：JSON 真源写入（REQ-005）

#### 案例 5.1 — 原子写 + 写前备份

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-013 |
| **对应 Spec** | kline_field_backfill → SC-005-001 |
| **优先级** | P0 |
| **预置条件** | 记录执行前 `backups/` 文件列表 |
| **输入** | 在**临时副本**（`--json <tmp>`）上执行 `--write` |
| **预期结果** | 出现 `backups/reits_kline_daily_<ts>.json`；执行后目录内无残留 `.tmp`；副本 JSON 可被 `json.load` 成功解析 |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.2 — coverage 元数据记录口径

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-014 |
| **对应 Spec** | kline_field_backfill → SC-005-002 |
| **优先级** | P1 |
| **预置条件** | 已 `--write` |
| **输入** | 读 JSON `coverage` |
| **预期结果** | 含 `return_fill_count=24642` / `amount_fill_count=178` / `purged_rows=81` / `return_caliber='unadjusted'` / `last_repair_at`；既有 `fund_count=88` / `total_records` / `date_range` 仍在且自洽 |
| **当前状态** | ❌ 测试缺 |

### 功能 6：PG 应用与一致性（REQ-006）

#### 案例 6.1 — 三项计数达标

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-015 |
| **对应 Spec** | kline_field_backfill → SC-006-001 |
| **优先级** | P0 |
| **预置条件** | 已 `--write` + `--purge-phantom --write` + `--apply-pg`（三项操作齐备） |
| **输入** | 三条只读 SQL |
| **预期结果** | `daily_return_pct IS NULL` == **89**；`amount IS NULL` == **0**；`date='2026-05-03'` == **0** |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.2 — JSON↔PG 逐项一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-016 |
| **对应 Spec** | kline_field_backfill → SC-006-002 |
| **优先级** | P0 |
| **预置条件** | 已 `--apply-pg` |
| **输入** | 对 JSON 与 PG 分别算三项计数 + 总行数 + 标的数 |
| **预期结果** | 5 项计数全部相等；不一致时脚本 `--verify` 以非零码退出 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.3 — PG 侧待删日期独立推导（执行期发现的缺口）

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-024 |
| **对应 Spec** | kline_field_backfill → SC-006-003 |
| **优先级** | P0 |
| **预置条件** | 已 `--write` 修复 JSON（`plan.purge` 为空） |
| **输入** | (a) 假连接调用 `apply_to_pg(conn, ["2026-05-03"])`，检查其发出的 SQL；(b) 只读调用 `plan_pg_purge()` 与 `_normalize_dates()` |
| **预期结果** | (a) 恰发 1 条 `DELETE FROM`，参数 == `(['2026-05-03'],)`，事务已提交，且同时发出 UPDATE；(b) `_normalize_dates` 对元组/字符串两种形状均归一为纯日期列表；(c) `load_pg_kline` 形状满足 `plan_purge` 契约，且 `json_purge=0` 时 `plan_pg_purge` 仍能识别 PG 脏行 |
| **当前状态** | ❌ 测试缺 |
| **备注** | 本 TC 因执行期发现的真实缺口而新增：`apply_to_pg` 原从 `plan.purge` 取待删日期，JSON 修好后该计划为空 → PG 脏行永远删不掉。 |

#### 案例 6.4 — 三系统一致性 JSON ↔ PG ↔ DuckDB

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-025 |
| **对应 Spec** | kline_field_backfill → SC-006-004 |
| **优先级** | P0 |
| **预置条件** | 完整跑过一次 `daily_etl.py`（含末尾 `sync_duckdb`） |
| **输入** | 对 JSON / PG / DuckDB 副本分别算四项计数（总行数 / null 收益率 / null amount / 幽灵日） |
| **预期结果** | 三者四项计数完全一致 |
| **当前状态** | ❌ 测试缺 |
| **备注** | 用户报缺陷时即指出「postgresql 与 duckdb 都有数据」。DuckDB 副本由 `sync_pg_to_duckdb.py` 自 PG 反向重建，只验 JSON↔PG 会漏掉副本仍为旧态。 |

### 功能 7：编排防复发（REQ-007）

#### 案例 7.1 — 编排顺序正确

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-017 |
| **对应 Spec** | kline_field_backfill → SC-007-001 |
| **优先级** | P0 |
| **预置条件** | 已改 `daily_etl.py` |
| **输入** | `daily_etl.py --dry-run` |
| **预期结果** | 计划含 `repair_kline`；其下标满足 `idx(sync_kline_json) < idx(repair_kline) < idx(json)` |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.2 — 完整跑后修复不被回滚

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-018 |
| **对应 Spec** | kline_field_backfill → SC-007-002 |
| **优先级** | P0 |
| **预置条件** | 完整执行一次 `daily_etl.py`（含 `repair_kline` 与 `json` build） |
| **输入** | 重跑 TC-KFB-015 三条 SQL |
| **预期结果** | 三项计数仍达标（89 / 0 / 0） |
| **当前状态** | ❌ 测试缺 |

### 功能 8：幂等与无缺口早退（REQ-008）

#### 案例 8.1 — 二次执行逐字节一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-019 |
| **对应 Spec** | kline_field_backfill → SC-008-001 |
| **优先级** | P0 |
| **预置条件** | 在临时副本上已执行一次 `--write` |
| **输入** | 对同一副本再执行一次 `--write`，比较前后 SHA256 |
| **预期结果** | 两次 SHA256 **完全相等**；第二次输出含「无缺口」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 8.2 — 无缺口不产生备份文件

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-020 |
| **对应 Spec** | kline_field_backfill → SC-008-002 |
| **优先级** | P1 |
| **预置条件** | 临时副本已修复（三项缺口 = 0）；记录 `backups/` 文件数 |
| **输入** | 再执行一次 `--write` |
| **预期结果** | `backups/` 文件数**不变**；无新文件产生 |
| **当前状态** | ❌ 测试缺 |

### 功能 9：dry-run 与显式授权（REQ-009）

#### 案例 9.1 — 默认 dry-run 零副作用

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-021 |
| **对应 Spec** | kline_field_backfill → SC-009-001 |
| **优先级** | P0 |
| **预置条件** | 记录 JSON SHA256 与 PG 三项计数 |
| **输入** | 不带 `--write` 执行 |
| **预期结果** | 输出含三项缺口计数（24642 / 178 / 81）；JSON SHA256 与 PG 三项计数**全部不变** |
| **当前状态** | ❌ 测试缺 |

#### 案例 9.2 — 删除需显式授权

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-022 |
| **对应 Spec** | kline_field_backfill → SC-009-002 |
| **优先级** | P0 |
| **预置条件** | 临时副本含幽灵行；未传 `--purge-phantom` |
| **输入** | `--write`（不含 `--purge-phantom`） |
| **预期结果** | 副本中幽灵行**仍存在**；输出含「检测到 N 行待清理，加 --purge-phantom 执行」 |
| **当前状态** | ❌ 测试缺 |

### 功能 10：除息日语义（补充断言，非 Spec Scenario）

#### 案例 10.1 — 超限涨跌幅全部可解释

| 字段 | 内容 |
|------|------|
| **ID** | TC-KFB-023 |
| **对应 Spec** | proposal §1.5（除息日语义验证） |
| **优先级** | P0 |
| **预置条件** | 已 `--write` + `--apply-pg` |
| **输入** | 查 PG 中 `abs(daily_return_pct) > 10` 的行，带 `row_number() OVER (PARTITION BY fund_code ORDER BY date)`，逐行 join `reits_dividend.ex_div_date` 与 `tdx_kline_daily.close` |
| **预期结果** | 行数 ≥ **4**；命中除息日 == **4**（508001/2024-06-28、508008/2024-04-09、180401/2023-05-18、508096/2023-11-13）；**非除息日的大跳变必须落在该标的序列前 2 行内，且其 close 须被 `tdx_kline_daily` 佐证**；`unexplained` 与 `uncorroborated` 均须为 0 |
| **当前状态** | ❌ 测试缺 |
| **修订说明** | 原断言 `n_big == 4` 是在「24,732 行收益率为 NULL」的修复前状态测得的，回填后必然失效。实测新增的第 5 行为 **508080（中金亦庄产业园REIT）2025-06-27 = +10.0113%**：该标的序列首行即 2025-06-26（rn=1，无 prev_close），06-27 为第二行（上市次日涨停），其两次除息在 2026-04-08 / 2026-09-02，与除息无关；`tdx_kline_daily` 同 (code,date) 的 close 与 volume 完全一致。故断言从「固定行数」改为「可解释性 + 独立源佐证」，既容得下真实大跳变，又能捕捉口径错误。 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 交易日历基准 | TC-001 / TC-002 | — | — | 🔴 |
| daily_return_pct 回填 | TC-006 | TC-003 / TC-004 / TC-005 | — | 🔴 |
| amount 回填 | TC-008 | TC-007 | — | 🔴 |
| 幽灵行清理 | TC-010 / TC-011 | TC-009 / TC-012 | — | 🔴 |
| JSON 写入 | TC-013 | TC-014 | — | 🔴 |
| PG 应用 | — | TC-015 / TC-016 / TC-024 | TC-018 / TC-025 | 🔴 |
| 编排 | — | TC-017 | TC-018 | 🔴 |
| 幂等 / dry-run | — | TC-019 / TC-020 / TC-021 / TC-022 | — | 🔴 |
| 除息日语义 | — | TC-023 | — | 🔴 |

## 四、回归风险矩阵

| 风险区域 | 本次改动 | 已有回归保护 | 风险等级 |
|---|---|---|---|
| `business.reits_kline_daily` 行级内容 | 更新 24,820 行 / 删除 81 行 | TC-004/005/007/009/015/016（计数 + 集合断言） | 🔴 高 |
| `reits_kline_daily.json` 真源 | 原地改写（原子） | TC-013（备份 + 无残留 .tmp）+ TC-019（幂等） | 🔴 高 |
| `daily_etl.py` 每日编排 | 插入 1 步 | TC-017（顺序）+ TC-018（完整跑后不回滚） | 🟡 中 |
| `sync_kline_json_from_tdx.py:246` 换手率分母 | **不改**（D2 决策保持 source='tdx'） | 无（因不改动） | 🟢 低 |
| `business.tdx_kline_daily` | **只读** | 无（因不改动） | 🟢 低 |
| DuckDB 副本 `reits.duckdb` | 不直接改（由 `sync_pg_to_duckdb.py` 自 PG 重建） | TC-018 完整跑覆盖 | 🟢 低 |
| `backfill_reits_kline_daily.py` | **不改** | 既有行为不变 | 🟢 低 |

## 五、建议补充顺序

1. **第一优先（落库前必过）**：TC-KFB-001 / 002 / 003 / 004 / 005 / 006 / 007 / 009 / 010 / 011 / 012 / 015 / 021 / 022
   —— 覆盖全部破坏性路径与核心不变量，缺一不可写库。
2. **第二优先（落库后立即补）**：TC-KFB-008 / 013 / 016 / 017 / 018 / 019 / 023 / 024
   —— 覆盖一致性、编排与幂等。
3. **第三优先（随后补）**：TC-KFB-014 / 020
   —— 元数据与备份文件数的细节断言。

## 六、执行方式

```bash
cd "D:/项目/数据文件"
set -a && . ./.env && set +a
# 与 daily_etl.py 的 VENV_PY 保持一致（项目用的是 .workbuddy，非 .workbuddy-ai）
PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
PYTHONIOENCODING=utf-8 "$PY" .stdd/agent_tests/test_kline_field_backfill.py
```

- 退出码 0 = 全部 PASS。
- 纯函数用例（TC-002/006/008/010/011/013/019/020/022）在临时目录内构造 fixture，可随时安全重跑。
- 集成用例（TC-001/003/004/005/007/009/012/014/015/016/017/018/021/023）只读真实 JSON 与 PG。
- **测试套件本身不写 PG**；写库由一次性受控命令完成，测试随后验证结果。
