# Test Plan: announcement_files + announcements 补全

## 测试策略
数据工程任务，无单元测试框架（pytest 未安装），采用独立 Python 断言脚本（`.stdd/agent_tests/test_announcement_inventory.py`），以真实 PG + 真实磁盘为对象，跑完即断言，退出码 0 = 全过。

## 用例

### T1 表与索引存在（REQ-001-001/002）
- GIVEN build_announcement_inventory.ensure_table() 已执行
- WHEN 查询 pg_indexes / information_schema.columns
- THEN announcement_files 存在且列齐全；索引含 uq_announcement_files_rel_path / idx_fund_code / idx_file_type / idx_abs_path

### T2 扫描入库且计数自洽（REQ-002-001/005-001）
- GIVEN 磁盘 D:\项目\PDF 四个根目录
- WHEN 运行 scan_and_upsert()
- THEN announcement_files 行数 == 重扫磁盘文件数（排除 pre_listing）；rel_path 唯一（无重复）

### T3 pdf→md 关联（REQ-002-002）
- WHEN 检查 md_rel_path 非空比例
- THEN 至少存在若干 pdf 行 md_rel_path 非空（不为恒空）

### T4 announcements 离线回补（REQ-003-001）
- GIVEN announcement_files 含 pdf 行
- WHEN backfill_announcements() 执行
- THEN announcements 行数较回补前显著增加（覆盖全市场 pdf 文件资产）；content_hash 唯一无重复插入

### T5 pdf_local_path 关联校验（REQ-004-001）
- WHEN 归一化 announcements.pdf_local_path 与 announcement_files.abs_path 比对
- THEN 现有 69 行 100% 命中；回补后所有 pdf 来源 announcements 行均命中

## 运行
```
set -a; . /d/项目/数据文件/.env; set +a
python .stdd/agent_tests/test_announcement_inventory.py
```
