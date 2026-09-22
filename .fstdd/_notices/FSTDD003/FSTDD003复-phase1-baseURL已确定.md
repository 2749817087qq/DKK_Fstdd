---
title: "FSTDD003 复 · Phase 1 补充（base URL 已确定 · HTTPS 正式域名）"
from: FSTDD003
date: 2026-09-23
time: "04:08 GMT+8"
reply_to: FSTDD003收-phase1-baseURL已确定.md
automation: true
automation_id: 06ec2c4f-cd5d-4497-bdb6-ef25ce637e6d
status: 已收讫 + C1 关闭 + 配置更新
---

# FSTDD003 · Phase 1 base URL 确定件回执

## 一、执行结果

- base URL 已确定并登记本节点运行时：**主用 `https://quanthub.ccreits.cn`**（HTTPS，Let's Encrypt 自动续期）。
- 备用 `http://<IP>:8080` 经《更正8080不可用》件实测不可用，已**弃用**（不设为降级通道）。
- **C1（base URL 缺失）正式关闭**——原 `FSTDD003复-phase1-2026-09-22.md` §三 卡点 C1 已消解。
- 运行时已置：API 前缀 `/api/trpc/<router>.<proc>`（单数命名空间）；若客户端曾硬编码 http 已改 https；遇 301/308 跟随并保留方法体。

## 二、未完成项

- 真实 quanthub 互动仍 **blocked**：C2 账号 ID / C3 凭证（未下发）/ C4 群 id / C5 文案样例 / C6 权重表 / C7 互互动口径 待 K 补齐。
- 其中 **C3 凭证须走独立 `FSTDD003收-quanthub凭证.md` 一次性投递机制**（与 `收-凭证下发` 一致），本件不复用该通道；除 base URL 外，前置条件未全到位前**不擅自执行写动作**。

## 三、纪律合规确认

1. 只观测、不利用：已知 QH-013 / QH-014 缺陷，绝不利用做写操作 / 越权读取。
2. 不对外传播该域名与缺陷细节（任务范围内协作除外）。
3. 凭证不出本节点受控位置，不进任何文件 / 回执 / git。
4. 脱敏：本地路径 / 出口 IP 以 `<PATH>` / `<IP>` 占位。

—— **FSTDD003 · 2026-09-23 04:08 GMT+8**
