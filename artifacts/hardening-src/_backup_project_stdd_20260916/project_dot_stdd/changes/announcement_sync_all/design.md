# Design: announcement_sync_all

> Phase 2 设计文档 | 2026-09-14 周一
> 依赖实证：proposal.md 可行性核查 + 本轮 disk_scan 列空值核查 + CollectionOutput.upsert 能力核查

## 目标
运行 `announcement_sync.py --all` 联网爬取全市场 94 只 REIT 公告元数据，使 `business.announcements`：
1. web 为权威层（升级现有 `disk_scan` 行的 `source_url`/`pdf_url`/`category`/`confidence`/`exchange`）；
2. web 独有行回填 `pdf_local_path` 关联 `announcement_files`（保住架构关联）；
3. 不破坏上一 slice 资产（`announcement_files` 29632 行不变、94 标的覆盖不丢）；
4. 一并跑 `sync_pre_listing()`（用户 Gate 1 决策）。

## 实证依据（非推测）
- `save_announcements_to_db` 当前用 `conflict_action="do_nothing"` + 前置 `SELECT(fund_code,title,publish_date)` 命中即 `continue` → 同 content_hash 的 web 行被丢弃，disk_scan 低质量行保留。**必须改 UPSERT。**
- `CollectionOutput().write` 支持 `conflict_action="upsert"`，SET 子句 = `UPDATE SET {c}=excluded.{c} FOR c IN cols NOT IN key_fields`。**只要 web 记录不含 `pdf_local_path`，冲突时该列不被触碰 → disk_scan 关联保留。**（core/fetcher.py:155-164 已读）
- `disk_scan` 行 8327：`source_url`/`pdf_url` 全 NULL（0 行），`pdf_local_path` 全有（8327），`category` 已用同款 `classify_announcement` 填好。`exchange` 仅 16 行缺。→ 升级主补 `source_url`+`pdf_url`（+ 有效 PDF 时 `confidence` 80→90）。
- `announcement_files` PDF 文件名 = `{YYYYMMDD}_{标题}.pdf`；新 web 行 `pdf_local_path` 为空，靠 `fund_code`+`publish_date(去横线)`+`标题子串` 匹配回填。

## 修改 1：save_announcements_to_db → UPSERT（announcement_sync.py）
替换原 `CollectionOutput().write(conflict_action="do_nothing")` 为单条 UPSERT（psycopg2 cur.execute）：

```sql
INSERT INTO business.announcements
  (fund_code,title,category,publish_date,source_url,pdf_url,exchange,source,
   confidence,content_hash,is_generic,source_module)
VALUES (%(fund_code)s,...,%(source_module)s)
ON CONFLICT (content_hash) DO UPDATE SET
  source_url    = excluded.source_url,
  pdf_url       = excluded.pdf_url,
  category      = excluded.category,
  confidence    = GREATEST(business.announcements.confidence, excluded.confidence),
  exchange      = COALESCE(business.announcements.exchange, excluded.exchange),
  source        = excluded.source,
  source_module = excluded.source_module,
  is_generic    = excluded.is_generic,
  updated_at    = now()
```
要点：
- **不含 `pdf_local_path`** → 冲突时原 disk_scan 关联原样保留（满足"升级且保关联"）。
- `confidence=GREATEST` → web 90 升 disk 80；web 70 不降 disk 80（避免降质）。
- `exchange=COALESCE` → 仅补缺，不覆盖已有。
- 移除原前置 `SELECT` 命中即 skip 的逻辑（UPSERT 自管去重）；保留 `is_reits_announcement` 过滤计数与 `check_pdf_validity` 调用。
- 该改动对 `--keyword`/`--code` 路径同样更安全（幂等 upsert），向后兼容。

## 修改 2：reconcile_pdf_local_path(conn) —— 新函数（放编排器）
对 `source IN ('SZSE','SSE') AND pdf_local_path IS NULL` 的行：
1. 一次性 `SELECT id,fund_code,abs_path,filename FROM business.announcement_files WHERE file_type='pdf'`，按 `fund_code` 建内存索引（8396 行，轻量）。
2. 逐 web 行：`date_str=publish_date.strftime('%Y%m%d')`；`title_sub=title[:20]`；
   候选 = 同 fund_code 且 `abs_path` 含 `date_str` 且含 `title_sub` 的文件。
3. 候选数==1 → 直接设；>1 → 取 `filename` 与 `title` 重叠度最高者；0 → 留 NULL（web 独有、无本地 PDF，可接受）。
4. `UPDATE business.announcements SET pdf_local_path=%s WHERE id=%s`，批量 commit。

## 修改 3：编排器 run_announcement_sync_all.py
- `main()`：`import announcement_sync; announcement_sync.sync_all_reits(max_count)` → `reconcile_pdf_local_path(conn)` → 打印统计（crawl 新增/升级、reconcile 前 pdf_local_path 空数、回填数、覆盖率）。
- `--pilot-code 180101`：先单只 `sync_single_fund` + reconcile，验证闭环（STDD Step 1.4）。
- `--dry-run`：仅统计现有 NULL 数，不写库（可选）。
- 全量运行耗时预估 30–120 分钟（94 只 × 多页 + 每只新公告 PDF HEAD 校验 + pre_listing 下载），**后台运行**（`run_in_background`），不作前台阻塞。

## 失败模式（STDD 14 类相关）
- **网络限流/超时**：CNInfo `get_announcements` 失败即 break（无重试），可能漏页；接受部分遗漏，可后续 `--code` 单只补。
- **content_hash 重复**：UPSERT 保证唯一，不会因同名跨目录 PDF 冲突（同公式）。
- **pdf_local_path 误覆盖**：UPSERT SET 不含该列 → 不可能误覆盖（已论证）。
- **pre_listing 子同步失败**：`sync_all_reits` 内 try/except 包裹，失败仅记日志，不阻断主同步。

## 验收（详见 test-plan.md）
- 单只 508000 试点（SSE）：爬取写库后该标的 `source_url`/`pdf_url` 非空、pdf_local_path 覆盖率不降。
- 全量后：`announcements` 行数显著增加；`source IN ('SZSE','SSE')` 行存在；`content_hash` 唯一；
  web 行 `pdf_local_path` 覆盖率 ≥ 80%；`announcement_files` 仍 29632；DISTINCT fund_code=94。

## 已知限制与发现（2026-09-14 实证）
- **深交所(180XXX) CNInfo 接口被 WAF 403 封禁**：巨潮主页与 `hisAnnouncement/query` 均返回 403
  （本沙箱出口 IP 被限流；早前 200、探针后变 403，非代码问题）。导致 180XXX 的 web 爬取**当前不可行**。
  → 全量跑时 180XXX 基金优雅跳过（已硬化 `sync_all_reits` 的 `except Exception` 与 `get_announcements` 空响应/异常保护）。
- **上交所(508XXX) SSE 接口正常**：`query.sse.com.cn/commonQuery.do` 返回 200，508000 实测 150–191 条。
  → 508XXX 的 web 补全完全可行，为本 slice 的主要产出。
- **修复的崩溃 bug**：原 `sync_all_reits` 仅 `except (RuntimeError, OSError, ValueError)`，
  CNInfo 403 抛 `urllib.error.HTTPError` 未被捕获 → 首只 180XXX 即让整个 94 只循环崩溃。
  已改为 `except Exception` 并给 `get_announcements` 加 `resp is None` 与 `except Exception` 保护。
- **试点结论**：508000 爬到 191 条，186 条命中原 disk_scan 行被 UPSERT 升级（source→SSE、source_url/pdf_url 填充、
  pdf_local_path 保留），5 条 web 独有新增；测试 10/10 PASS。
- **后续**：180XXX 的 web 补全需待 CNInfo 解封或引入替代数据源（东财/深交所官方披露 API），列为独立 follow-up。
