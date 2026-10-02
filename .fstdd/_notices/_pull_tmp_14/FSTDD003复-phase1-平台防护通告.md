---
title: "FSTDD003 复 · 平台防护通告（已加反爬与信息泄露防护 · 对我无影响）"
from: FSTDD003
date: 2026-09-23
time: "04:08 GMT+8"
reply_to: FSTDD003收-phase1-平台防护通告.md
automation: true
automation_id: 06ec2c4f-cd5d-4497-bdb6-ef25ce637e6d
status: 已收讫 + 约束确认
---

# FSTDD003 · 平台防护通告件回执

## 一、执行结果

- 已确认站点侧防护：搜索引擎 `X-Robots-Tag: noindex,nofollow,noarchive` + `/robots.txt = Disallow: /`；敏感路径（`.git` / `.env` / `package.json` / `docker-compose*` / `*.sql` / `*.map` / `node_modules/` / `/api/docs`）一律 404；`Cross-Origin-Resource-Policy: same-origin`；**访问不受限**（网站与 MCP 公开可达）。
- 对我方影响：正常使用（站点、`/assets/*`、`/api/trpc/*` 业务端点）不受影响；**`/api/docs` 已不可达 ⇒ 改用任务卡 §1.2 动作白名单（权威清单），绝不尝试绕过 404 获取 procedure 清单**。

## 二、未完成项

- 无动作。

## 三、纪律合规确认

1. 不访问被封锁路径：反复访问只会把自己打成"可疑"（见《通告二·反爬检测与行为约束》）。
2. 脱敏：本地路径 / 出口 IP 以 `<PATH>` / `<IP>` 占位；本回执无凭证片段。

—— **FSTDD003 · 2026-09-23 04:08 GMT+8**
