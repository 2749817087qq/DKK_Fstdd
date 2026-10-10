---
title: inbox 投递地址迁移：8787 公网关闭，443 反代 HTTPS 接管
experience_id: FSTDD002-EXP-20260923-INBOX-1
category: process
severity: high
occurrences: 1
exported_at: 2026-09-23
sanitized: true
source: FSTDD002 节点按 K 通知执行配置迁移
---

## 现象

inbox 旧投递地址（IP:8787 明文 HTTP）公网入口被关闭（安全缓解措施），直连超时；节点侧所有经验回传、自检脚本健康检查全部指向旧地址，存在批量投递失败风险。

## 根因

投递端点单点暴露在明文高端口；运维侧关闭公网入口后，改由 443 反向代理承接（/inbox/* → 本机 8787），不暴露新端口，协议升级为 HTTPS，鉴权机制不变。

## 检测触发

K 下发地址变更通知；节点侧 curl 旧地址超时（connection timed out）、新地址 /inbox/health 返回 ok=true 确认切换窗口已到。

## 修复模板

1. 脚本内 inbox/health 两个常量改为 HTTPS 反代地址（新路径前缀 /inbox）；2. 注释中的历史地址保留为迁移说明；3. dry-run 校验后真实 POST 一条经验验证端到端；4. 首次成功投递回执通知归口方；5. 死常量（未引用的旧端口定义）可保留不动。
