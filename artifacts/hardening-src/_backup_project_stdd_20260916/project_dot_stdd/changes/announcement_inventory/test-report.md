# Test Report: announcement_files + announcements 补全（STDD Change announcement_inventory）

- **日期**: 2026-09-14
- **运行**: `python .stdd/agent_tests/test_announcement_inventory.py`（set -a; . .env）
- **结果**: ✅ PASS — 11/11 断言通过，退出码 0

## 断言明细

| 用例 | 断言 | 结果 | 证据 |
|---|---|---|---|
| T1a | announcement_files 列齐全 | PASS | 12 列全在 |
| T1b | 索引齐全 | PASS | pkey + uq_rel_path + idx_fund_code + idx_file_type + idx_abs_path |
| T2a | 扫描到文件资产 | PASS | expected=29632 (>20000) |
| T2b | 表行数==磁盘文件数 | PASS | table=29632 disk=29632 |
| T2c | rel_path 唯一 | PASS | 重复:0 |
| T3  | pdf→md 关联非空 | PASS | pdf_with_md=8396 |
| T4a | announcements 覆盖全市场 pdf | PASS | after=8396 / pdf_in_files=8396 |
| T4b | content_hash 无重复 | PASS | 重复:0 |
| T5a | 现有 announcements 全链接 | PASS | 8396/8396 |
| T5b | 回补 pdf 行全链接 | PASS | 8327/8327 |
| T5c | 无孤儿 pdf_local_path | PASS | orphan=0 |

## 生产运行报告（build_announcement_inventory.py -- 全量）

```json
{
  "files":   {"total": 29632, "inserted": 29632},
  "backfill":{"inserted": 0, "skipped": 8396},
  "linkage": {"existing_total": 8396, "existing_linked": 8396, "orphan": 0,
              "pdf_rows_total": 8327, "pdf_rows_linked": 8327},
  "elapsed_sec": 22.1
}
```

## 覆盖率抽查（实查 PG）

- `announcement_files`: 29632 行，distinct fund_code = **94**（全市场）
- `announcements`: 8396 行，distinct fund_code = **94**（原仅 2：180101/180102）
- 按类型: pdf 8396 / md 8540 / json 12696
- 按交易所(fund_code 非空): SSE 21316 / SZSE 8209

## 修复记录（RED→GREEN 过程中）

1. `core.pg` 游标为 **DictCursor**：所有 `cur.fetchall()` 行须用 `r["col"]` 访问，非 `r[0]`（元组解包会取到列名字符串，导致回补仅写入 1 行垃圾）。
2. `PDF_ROOT` 初版误写为 `REPO/PDF`（`D:\项目\数据文件\PDF`），实际公告库在 **`D:\项目\PDF`**（与 workspace 平级）。已改正为绝对路径。
3. `content_hash` 唯一约束冲突：回补哈希公式对齐 `announcement_sync` 的 `md5(fund_code:publish_date:title)`（原为 `|` 分隔），并改用 `ON CONFLICT (content_hash) DO NOTHING` 幂等跳过跨目录同名 PDF。

## 结论

目标架构已落地并实证：
- `announcement_files` 管**文件资产**（全市场 94 标的 / 29632 文件 / 带索引）
- `announcements` 管**公告元数据**（全市场 94 标的 / 8396 行，原仅 2 标的）
- `pdf_local_path` ↔ `announcement_files.abs_path` 关联 100% 可达，无孤儿

未覆盖（已知边界，非本次）：经 `announcement_sync --all` 联网爬取权威 web 元数据（标题/分类/置信度更优）作为后续 STDD slice，受沙箱网络与反爬限制，需单独授权。
