---
title: "FSTDD003收-phase1 通告：quanthub 已加**反爬与信息泄露防护**（对你无影响）"
from: K（FSTDD 经验库归口节点）
date: 2026-09-23
priority: 中
---
# FSTDD003 收 · 平台侧防护通告

D哥 授权、K 已执行（2026-09-23 02:1x）：`quanthub.ccreits.cn` 增加**反爬与信息泄露防护**。

| 项 | 内容 |
|---|---|
| 搜索引擎 | `X-Robots-Tag: noindex, nofollow, noarchive` + `/robots.txt` = `Disallow: /` |
| 敏感路径 | `.git` / `.env` / `package.json` / `docker-compose*` / `*.sql` / `*.map` / `node_modules/` / **`/api/docs`** → **一律 404** |
| 跨站取资源 | `Cross-Origin-Resource-Policy: same-origin` |
| **访问** | **不受限制**（网站与 MCP 均公开可达） |

## 对你的影响（两条）
1. **正常使用不受影响**：站点、`/assets/*` 静态资源、`/api/trpc/*` 业务端点均照常；
2. ⚠️ **`/api/docs` 已不可访问**（原用于列举全部 procedure）。若你的实现依赖它，**改用任务卡 §1.2 的动作白名单**（那是权威清单）；**不要**试图绕过 404 去获取该清单。

—— **K**（判定以服务器时钟为准）
