# Design: announcement_files 文件资产清单表

## 1. 数据模型

```sql
CREATE TABLE IF NOT EXISTS business.announcement_files (
    id            BIGSERIAL PRIMARY KEY,
    fund_code     TEXT,                       -- NULL 允许（_generic / 无 code 目录）
    exchange      TEXT,                       -- SSE / SZSE / NULL
    file_type     TEXT NOT NULL,              -- 'pdf' | 'md' | 'json'
    filename      TEXT NOT NULL,
    rel_path      TEXT NOT NULL,              -- 相对 D:\项目\PDF，正斜杠
    abs_path      TEXT NOT NULL,              -- 归一化正斜杠绝对路径（用于 JOIN announcements.pdf_local_path）
    file_size     BIGINT,
    md_rel_path   TEXT,                       -- pdf 行对应的 MD rel_path（可空）
    content_hash  TEXT,                       -- 可空
    source_root   TEXT,                       -- 'PDF/SSE' | 'PDF/SZSE' | 'announcements_md' | 'announcements_json'
    created_at    TIMESTAMP DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_announcement_files_rel_path ON business.announcement_files(rel_path);
CREATE INDEX IF NOT EXISTS idx_announcement_files_fund_code ON business.announcement_files(fund_code);
CREATE INDEX IF NOT EXISTS idx_announcement_files_file_type ON business.announcement_files(file_type);
CREATE INDEX IF NOT EXISTS idx_announcement_files_abs_path  ON business.announcement_files(abs_path);
```

## 2. 扫描算法

- 根配置：`[('PDF/SSE','pdf'), ('PDF/SZSE','pdf'), ('announcements_md','md'), ('announcements_json','json')]`
- 排除：路径任一分量等于 `pre_listing` 或以 `pre_listing.` 开头（pre_listing.bak_20260910），避免与 `pre_listing_files` 重复。
- fund_code：从任一祖先目录名匹配 `^(\d{6})_` 取首组；无则 NULL。
- exchange：fund_code 以 508→SSE、180→SZSE；否则按根（PDF/SSE→SSE, PDF/SZSE→SZSE），其余 NULL。
- abs_path：`D:/项目/PDF/{rel_path}` 正斜杠。
- md_rel_path：先收集所有 md 行的 `{归一化 basename(去 .md): rel_path}` 字典；pdf 行按同 basename(去 .pdf) 查找，命中则填。

## 3. announcements 回补

- 源：announcement_files 中 file_type='pdf' 的行。
- 文件名解析：`^(\d{8})_(.+)\.pdf$` → publish_date=YYYY-MM-DD，title=去扩展名余部。
- 插入字段：fund_code, title, category=NULL(后续 classifier 可补), publish_date, source_url=NULL, pdf_url=NULL, exchange, source='disk_scan', source_module='announcement_inventory_backfill', confidence=80(日期解析成功)/60, content_hash=md5(fund_code:publish_date:title), pdf_local_path=原生反斜杠 abs（与 announcements 现有风格一致）, pdf_downloaded=True, download_status='disk_scan', pdf_local_path 用于关联。
- 幂等：先取现有 announcements 的 content_hash 集合，跳过已存在；批量 INSERT。

## 4. 关联校验

- announcements.pdf_local_path 存 `D:\项目\PDF\...`（反斜杠）；归一化为正斜杠后与 announcement_files.abs_path 比对。
- 现有 69 行（180101/180102，路径在 SZSE/...）应全部命中。

## 5. 复用

- 连接：`core.pg.get_pg_conn(ensure_schema=True)`（项目约定，已验证可用）。
- 批量写：`psycopg2.extras.execute_values` + `ON CONFLICT (rel_path) DO UPDATE`。
- 不引入新依赖：仅 psycopg2（已装）。
