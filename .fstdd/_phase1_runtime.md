---
title: "FSTDD003 · Phase 1 运行时配置（节点本地，非 notice，不推送）"
updated: 2026-09-23T04:08 GMT+8
source_notices:
  - FSTDD003收-phase1-baseURL已确定.md
  - FSTDD003收-phase1-更正8080不可用.md
  - FSTDD003收-phase1-平台防护通告.md
  - FSTDD003收-phase1-节奏变更-2小时小闭环.md
  - FSTDD003收-phase1-访问限制已撤除.md
  - FSTDD003收-phase1-通告二-反爬检测与行为约束.md
---

# Phase 1 运行时（节点本地状态，供执行层消费）

## 端点
- base_url: https://quanthub.ccreits.cn   # 唯一入口（HTTPS + 域名）
- api_prefix: /api/trpc/<router>.<proc>    # 单数命名空间
- port8080_disabled: true                  # 308 循环，不可用
- use_domain_not_ip: true                  # IP 走 443 会被 308 循环挡住
- follow_3xx_keep_method: true             # 301/308 跟随保留方法体

## 节奏（2 小时小闭环）
- rhythm: 2h-window
- window_reply_pattern: FSTDD003复-phase1-<YYYY-MM-DD>-<HH>.md   # 窗口结束 15 分钟内
- daily_summary_pattern: FSTDD003复-phase1-<YYYY-MM-DD>.md        # 21:30 前
- active_windows: ["12-14"]                 # 工作日；周末加 ["08-10","20-22"]
- daily_hard_limits: 总<=15 / 赞<=10 / 评<=8 / 新发<=2 / 关注<=3 / 回测<=5
- browse_ratio_min: 0.40

## 前置条件（engagement 可执行需全齐）
- C1 base_url: CLOSED
- C2 账号ID: PENDING
- C3 凭证: PENDING（须走独立 FSTDD003收-quanthub凭证.md，落到 .fstdd/_fstdd003_credential.txt，600，gitignored）
- C4 群id: PENDING
- C5 文案样例: PENDING
- C6 权重表: PENDING
- C7 互互动口径: PENDING
- credential_issued: false
- engagement_runnable: false

## 平台防护约束（对我方行为）
- 搜索引擎封锁: noindex+robots.txt（不影响访问）
- 敏感路径 404: .git/.env/package.json/*.map/*.sql/node_modules//api/docs
- 访问日志: 开（来源IP/UA/路径/状态码/大小/耗时，留168h）
- 每小时反爬检测: 开（按IP汇总，分级 可疑/关注/已知来源/正常）
- 出口IP: 已知来源（按K通告，正常活动免误判；>1000/小时亦告警）
- 观察期: 2026-09-23 ~ 2026-09-30
- 升级触发: T1可疑>=3次/7天 | T2单IP>=5000/小时 | T3敏感路径>=50/天 | T4遍历式批量 | T5服务质量受影响

## 红线（不可破）
- 只观测不利用 QH-013/QH-014（不自行验证能否绕过）
- 不遍历/枚举路径；不批量探测（<500/小时，不同路径<50）；不改UA伪装；不访问已封锁路径
- 不破坏/不刷量/不发真实信息/不涉真实交易建议/不绕过防护（429即停不重试）/不动他人数据
- 凭证不出本节点受控位置，不进任何文件/回执/日志/git
- 卡外想法上报不擅做；卡点先回执说明

## 异常上报
- 异常: FSTDD003复-quanthub-<主题>.md（时间/动作/端点/HTTP码/复现步骤/脱敏摘要）
- 访问受限(403): 已被《访问限制已撤除》撤销，不再需要
- 误判: FSTDD003复-quanthub-访问误判.md
