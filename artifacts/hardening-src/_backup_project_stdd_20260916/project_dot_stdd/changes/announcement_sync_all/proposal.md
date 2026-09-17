# STDD Change: announcement_sync_all — 联网全量爬取 REIT 公告元数据

> 状态：Phase 1 (Understand) 完成，待 Gate 1 确认
> 时间基线：2026-09-14 周一 17:47
> 依赖变更：`.stdd/changes/announcement_inventory`（已提交 a4a6bc0，announcement_files + announcements 离线补全）

## 1. 背景与目标

上一 slice（`announcement_inventory`）已把 `business.announcements` 从 2 标的(69行) 离线补全到
**94 标的 / 8396 行**，来源 `source='disk_scan'`（标题/日期由 PDF 文件名解析，confidence 80/60，
无 `source_url`/`pdf_url`/`exchange` 真实分类）。

本 slice 目标：运行 `announcement_sync.py --all`，联网（巨潮 CNInfo + 上交所 SSE）爬取**全市场 94 只
REIT 的权威公告元数据**，写库得到更准的 `category`、真实 `source_url`/`pdf_url`、`exchange`、
更高 `confidence`（90/70），补足 web 侧独有公告的覆盖。

## 2. 可行性实证（本轮已跑，非推测）

| 核查项 | 结果 | 证据 |
|---|---|---|
| import announcement_sync | OK | 关键符号 sync_all_reits/sync_single_fund/save_announcements_to_db/CNInfoCrawler 均在 |
| 依赖 core.fetcher 符号 | OK | ApiFetcher/FundRegistry/PRESET_CONFIGS(含 cninfo,sse)/CollectionOutput 全部可用 |
| pipeline 包依赖 | **无** | 仅 import 本地 core.* + pre_listing_crawler；pipeline 依赖只在 backfill_announcement_pdf_0826.py（不参与本 slice） |
| FundRegistry().get_all_codes() | **94 只** | 含 508(SSE)/180(SZSE)，与前 slice 覆盖一致 |
| CNInfo 主页/PDF 静态 | 200 | 外网可达 |
| SSE 查询接口 | 200 | 外网可达 |
| CNInfo 搜索/公告接口 | GET→500 | 代码用 POST（探测用 GET 故 500），属预期，非连通故障 |

## 3. 运行路径与现有行为

`--all` → `sync_all_reits()`：
- 遍历 `FundRegistry().get_all_codes()`（94 只）
- 深交所 180XXX：CNInfo `hisAnnouncement/query`（POST，pageSize=30，最多20页）
- 上交所 508XXX：SSE `commonQuery.do`（最多10页，带 3 次业务重试）
- 每只 → `save_announcements_to_db()`：经 `is_reits_announcement` 过滤、`classify_announcement` 分类、
  `check_pdf_validity`（urllib HEAD 校验 PDF 魔数）定 confidence，写 `business.announcements`，
  `key_fields=["content_hash"]`, `conflict_action="do_nothing"`
- 末尾还调用 `sync_pre_listing()`（pre_listing_crawler，会下载上市前 PDF，重操作）

## 4. 两个必须决策的设计问题（进 Gate 1）

### 问题 A：合并/升级语义
`content_hash = md5(fund_code:publish_date:title)` 与 disk_scan 回补**同公式**。
→ web 爬到的、磁盘已存的同一条公告，因 content_hash 命中被 `do_nothing` 跳过，
  **保留低置信度、无 source_url 的 disk_scan 行**，web 高质量元数据进不去。

需决策：是否对已存在的 disk_scan 行做"web 元数据升级"（UPDATE source_url/pdf_url/category/
confidence/exchange，保留其 pdf_local_path）。推荐：**升级**（web 为权威层）。

### 问题 B：pdf_local_path 关联断裂
`save_announcements_to_db` 写入时不设 `pdf_local_path` → web 行游离于 `announcement_files` 之外，
破坏"pdf_local_path 关联"架构。

需决策：--all 后是否跑"回填关联"步骤（按 fund_code+publish_date+title 把 web 行 pdf_local_path
指向 announcement_files.abs_path）。推荐：**回填**（保住架构关联）。

### 问题 C：pre_listing 子同步
`sync_all_reits` 末尾调用 `sync_pre_listing()` 会下载大量上市前 PDF（已由 pre_listing_files 表管理）。
是否一并跑？推荐：**跳过**（pre_listing 有独立编排，避免与本 slice 重复下载大文件、拉长工期）。

## 5. 风险

- **工期/限流**：94 只 × 多页 × 每只新公告 HEAD 校验 PDF，预估 30–90 分钟；CNInfo 可能限流（get_announcements 失败即 break，无重试）。
- **外网稳定性**：沙箱需 `dangerouslyDisableSandbox` 放行；中途失败可单只重跑（`--code`）。
- **写入冲突**：`do_nothing` 保证不破坏现有行，安全。

## 6. 拟接受准则（Phase 2 test-plan 草案）

1. `--all` 端到端可跑（单只 180101 试点先行，验证 crawl+write 闭环）。
2. 跑后 `business.announcements` 行数显著增加（web 独有公告新增），`source='SZSE'/'SSE'` 行存在。
3. `content_hash` 仍唯一（无重复）。
4. 若决策"升级"：disk_scan 行的 source_url/pdf_url/category/confidence/exchange 被 web 值覆盖且 pdf_local_path 保留。
5. 若决策"回填"：web 行 pdf_local_path 指向 announcement_files.abs_path 的比例 > 某阈值（如覆盖率≥80%）。
6. 与上一 slice 的 94 标的覆盖一致（无标的丢失）。
