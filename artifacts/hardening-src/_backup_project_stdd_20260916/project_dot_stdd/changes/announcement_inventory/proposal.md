# Proposal: REITs 公告文件资产清单表 + announcements 元数据补全（STDD Change）

- **Change ID**: announcement_inventory
- **日期**: 2026-09-14
- **作者**: archer (Agent)
- **审批**: D哥 已明确授权「两者都做：清单表管文件资产，announcements 管公告元数据，pdf_local_path 关联，走stdd」

## 1. 问题陈述（基于实证）

2026-09-14 实查 PostgreSQL `business` schema（55 表）：

| 资产（磁盘） | 磁盘真实量 | PG 表 | 行数 | 索引 |
|---|---|---|---|---|
| SSE/SZSE 常规 PDF 公告 | 5623 + 2773 = 8396 | ❌ 无 | — | — |
| announcements_md | 10873（排除 pre_listing） | ❌ 无 | — | — |
| announcements_json | 12696（排除 pre_listing） | ❌ 无 | — | — |
| pre-REIT PDF | 1727 | ✅ `pre_listing_files` | 1729 | pkey+唯一+idx |
| pre-REIT 明细 | — | ✅ `pre_listing_file_inventory` | 1189 | pkey+唯一 |
| `announcements`（元数据） | — | ✅ 存在 | **69 / 2 标的** | 5 个索引 |

**核心矛盾**：`raw_json` 中 `backfill_announcement_pdf_0826_result.json` 记录 `announcements` 应有 ~8209 行，但本实例仅 69 行（180101/180102 两只深交所标的）。根因：`backfill_announcement_pdf_0826.py` 依赖 `pipeline` 包（Mac 路径 `/Users/apple/...`），本机 `D:\项目\数据文件` 无该包，故全量同步未在本实例执行——8386 个 PDF 已落盘但元数据仅登记 2 只标的子集。

## 2. 目标架构

```
announcement_files  (文件资产清单)          announcements (公告元数据)
─────────────────────────────────          ─────────────────────────────
id  fund_code  exchange                     id  fund_code  title
file_type(pdf/md/json)  filename           category  publish_date
rel_path (相对 D:\项目\PDF)  abs_path  <─── pdf_local_path (归一化后 JOIN)
file_size  md_rel_path  content_hash        pdf_url  source  confidence
                                          content_hash
```

- `announcement_files`：扫描磁盘、登记**全部**常规公告文件资产（PDF/MD/JSON），排除 `pre_listing` 子树（已由 `pre_listing_files` 覆盖）。
- `announcements`：公告元数据主表；由磁盘 PDF 文件名**离线、幂等**回补缺失元数据（fund_code/publish_date/title），使全市场文件资产均有元数据登记。
- `pdf_local_path` ↔ `announcement_files.abs_path`（均归一化为正斜杠）建立关联。

## 3. 范围边界

- **IN**：`D:\项目\PDF\SSE`（pdf）、`D:\项目\PDF\SZSE`（pdf）、`D:\项目\PDF\announcements_md`（md）、`D:\项目\PDF\announcements_json`（json）。
- **OUT（避免与现有表重复）**：所有含 `pre_listing` 路径段的文件（已由 `pre_listing_files` / `pre_listing_file_inventory` 覆盖）。
- **OUT（非本次）**：经 `announcement_sync --all` 联网全量爬取权威元数据。本变更为离线、确定性补全；联网爬取作为后续 STDD slice，需单独授权（受沙箱网络与反爬限制）。

## 4. 风险

- 批量写：`announcement_files` 约 3.2 万行 upsert；`announcements` 回补约 8300 行 insert。均走批量 + 幂等（ON CONFLICT / content_hash 去重），可重跑。
- 不删不改现有 `pre_listing_*` 表与已有 69 行 announcements。
