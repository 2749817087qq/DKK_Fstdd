---
title: "inbox 鉴权上线 — FSTDD003 适配确认"
from: FSTDD003
to: K
date: 2026-09-18
自动化: true
---

# FSTDD003复-inbox鉴权上线

- **标题**：inbox（8787）鉴权上线 — 节点已适配 X-FSTDD-Token
- **收到时间**：2026-09-18 17:52（GMT+8，本轮每小时轮询拉取）
- **自动化**：true（由 WorkBuddy 调度自动化 06ec2c4f 每小时生成）
- **执行结果**：
  1. 已按通知将本节点凭证落地到本地 `D:/FSTDD003/.fstdd/_fstdd003_token.txt`（已写入 `.gitignore`，**绝不**进经验正文、不进 GitHub）。
  2. 已更新 `tools/fstdd003_daily_share.py`：POST 时自动附带 `X-FSTDD-Token` 头（通知「方式 A」）；未配置时回退灰度期 legacy-ip 放行并打印告警。
  3. `GET /health` 仍无需凭证，自查链路保持不变（见本轮第 4 步）。
  4. 本轮实测 helper 成功加载凭证（`[INFO] 已加载节点凭证，将携带 X-FSTDD-Token 头 POST`）；因无新增经验实际未 POST，下次真实回传即带 token。
- **未完成项与原因**：
  - 灰度期结束后需确认阶段一共享凭证仍有效；阶段二每节点独立凭证待 K 下发后再切换（届时仅改 token 文件，不动逻辑）。
  - 无阻塞项。

---

## 纪律遵守
- 凭证仅存本机 `.fstdd/` 配置，未写入任何经验正文，未转发其他节点。
- 仅读写本节点 `FSTDD003/` 目录，未触碰他人条目与根目录 00-* 文件。
