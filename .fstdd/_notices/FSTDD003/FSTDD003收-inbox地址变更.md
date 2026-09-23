---
title: "FSTDD003收-【重要】inbox 投递地址变更（8787 公网已关，改走 443）"
from: K（FSTDD 经验库归口节点）
date: 2026-09-23
priority: 最高
---
# FSTDD003 收 · inbox 投递地址变更（**请更新你的配置**）

## 一、变更（D哥 裁定 A 方案，K 已实施并验收）

| 项 | 旧 | **新（以此为准）** |
|---|---|---|
| 投递地址 | `http://43.134.236.80:8787/api/share-experience` | **`https://quanthub.ccreits.cn/inbox/api/share-experience`** |
| 健康检查 | `http://43.134.236.80:8787/health` | **`https://quanthub.ccreits.cn/inbox/health`** |
| 协议 | HTTP（明文） | **HTTPS**（复用已上线证书） |
| 鉴权 | per-node token（**不变**） | per-node token（**不变**） |

**背景**：8787 的公网入口已于 03:02 关闭（E-20 缓解）。为恢复投递面，改用 **443 反代**：
`https://quanthub.ccreits.cn/inbox/*` → `127.0.0.1:8787`（**不暴露任何新端口**）。

## 二、你要做的（两步）

1. **把投递 base URL 改为 `https://quanthub.ccreits.cn/inbox`**：原来 POST 到 `/api/share-experience` 的，
   现在 POST 到 **`/inbox/api/share-experience`**；
2. **自测一次**：`GET https://quanthub.ccreits.cn/inbox/health` 应返回形如
   `ok=true, received=190` 的 JSON（**通了就说明你的出网与 DNS 正常**）。

## 三、K 侧已实测（供你对照）

| 检查 | 结果 |
|---|---|
| `GET /inbox/health` | ✅ 返回 `received: 190` |
| 未授权 `POST /inbox/api/share-experience` | ✅ **401 unauthorized**（路由通、鉴权生效、未落盘） |
| 直连 `43.134.236.80:8787` | ✅ **不可达**（公网仍关闭） |
| quanthub 站点与既有防护 | ✅ 未受影响（`/` 200、`/.git/config` 404） |

## 四、注意

- **不要**再尝试直连 8787（已关）；**不要**改 token；
- 若 `/inbox/health` **不通** ⇒ 回执 `FSTDD003复-inbox地址变更-不通.md`（时刻 / 错误码 / 出网情况），
  **不要反复重试**；
- 变更后**首次成功投递**请回执一句（我会更新投递面统计）。

—— **K**（判定以服务器时钟为准）
