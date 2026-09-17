# Test Plan: announcement_sync_all

> Phase 2 测试计划 | 2026-09-14 周一

## 测试策略
联网爬取不可做快速单元测试，故采用「**单只试点驱动 + 全局不变量断言**」：
- 试点（STDD Step 1.4 切片验证）：脚本直接驱动 `sync_single_fund('180101')` + `reconcile_pdf_local_path()`，
  证明 crawl→UPSERT升级→回填关联 端到端闭环可用（约数十秒，真实网络+真实写库）。
- 全局不变量：断言在「仅试点」与「全量跑后」均应成立（试点不破坏这些不变量），故脚本单次运行即可 PASS，
  兼作验收测试；全量后台跑完后再跑一次作为 test-report 证据（覆盖率进一步提升，断言仍 PASS）。

## 用例（.stdd/agent_tests/test_announcement_sync_all.py）

| ID | 类型 | 描述 | 判定 |
|---|---|---|---|
| T0 | pilot | 跑 180101 单只爬取+回填；该标的 `source_url`/`pdf_url` 非空行 ≥1 | PASS/FAIL |
| T1 | inv | `content_hash` 全表唯一（无重复） | COUNT(DISTINCT)=COUNT(*) |
| T2 | inv | `announcement_files` 行数仍 = 29632（不被本 slice 改动） | == 29632 |
| T3 | inv | `announcements` DISTINCT fund_code = 94（覆盖不丢） | == 94 |
| T4 | inv | `disk_scan` 行 `pdf_local_path` 仍全非空（8327，未被 UPSERT 误覆盖） | COUNT(plp)=8327 |
| T5 | cov | web 行（`source IN ('SZSE','SSE')`）`pdf_local_path` 覆盖率 ≥ 80% | ratio≥0.8 |
| T6 | upgrade | 存在 `source='disk_scan'` 但 `source_url` 非空 的行（升级生效证据） | ≥1 |
| T7 | pilot-cov | 180101 试点后该标的 web 行 pdf_local_path 覆盖率 ≥ 80% | ratio≥0.8 |

## 执行
```
python .stdd/agent_tests/test_announcement_sync_all.py
```
- 退出码 0 = 全部 PASS。
- T0 真实联网写库（仅 1 只，安全）；T1–T7 只读断言。

## 全量跑后复验（test-report 证据）
全量 `--all` 后台跑完后，重跑本脚本 + 额外抽查：
- `announcements` 总行数、按 source 分布、按 fund_code 覆盖。
- `reconcile` 前后 web 行 pdf_local_path 空数对比（回升幅度）。
- 抽样 3 只标的 web 行明细（source_url/pdf_url/pdf_local_path 均非空）。
