# Spec: mirror-failure-alert

> Change: 2026-09-17-mirror-failure-alert | Auto-generated Human View

## Requirements

### Requirement: 镜像结果必须回显给推送方，且同时保留落盘日志

#### Scenario: SC-001

- **GIVEN** post-receive 钩子已安装
- **WHEN** 一次推送落到服务器裸库
- **THEN** 推送方 SHALL 在 git push 的命令输出中看到镜像结果
- **AND** 同一份输出 SHALL 同时写入 mirror.log
- **AND** 回显 SHALL NOT 要求推送方额外执行任何命令

#### Scenario: SC-002

- **GIVEN** 钩子执行完毕
- **WHEN** 检查推送方输出
- **THEN** 镜像成功与失败 SHALL 在输出中可明确区分
- **AND** 成功 SHALL NOT 与失败共用同一标识

### Requirement: 镜像失败必须输出结构化告警块，不得被误读为成功

#### Scenario: SC-003

- **GIVEN** 镜像失败（目标不可达或非快进）
- **WHEN** 钩子结束
- **THEN** 输出 SHALL 包含结构化告警块
- **AND** 告警块 SHALL 说明「裸库已更新、GitHub 未同步、对外通道滞后」
- **AND** 告警块 SHALL 包含失败项与失败原因
- **AND** 告警块 SHALL NOT 与成功输出混淆

#### Scenario: SC-004

- **GIVEN** 钩子分别推送分支与 tag
- **WHEN** 其中一项失败而另一项成功
- **THEN** 告警 SHALL 明确指出是哪一项失败
- **AND** 成功项 SHALL 仍然被记录为成功

### Requirement: 镜像失败必须留下可被程序读取的故障标记

#### Scenario: SC-005

- **GIVEN** 镜像失败
- **WHEN** 钩子结束
- **THEN** 系统 SHALL 写入故障标记文件 mirror-failed.flag
- **AND** 标记 SHALL 包含时间戳
- **AND** 标记 SHALL 包含失败项

#### Scenario: SC-006

- **GIVEN** 故障标记文件存在
- **WHEN** 一次镜像全部成功
- **THEN** 系统 SHALL 自动清除该标记
- **AND** 清除 SHALL NOT 需要人工介入

#### Scenario: SC-007

- **GIVEN** 故障标记文件已写入
- **WHEN** 以程序方式读取该标记
- **THEN** 标记内容 SHALL 可被结构化解析
- **AND** 解析 SHALL NOT 依赖正则匹配自然语言

### Requirement: 必须提供一条命令的镜像状态巡检，替代人工阅读日志

#### Scenario: SC-008

- **GIVEN** 存在镜像状态巡检命令
- **WHEN** 执行该命令
- **THEN** 系统 SHALL 给出裸库与 GitHub 是否收敛的明确判定
- **AND** 已收敛 SHALL 返回退出码 0
- **AND** 滞后 SHALL 返回非 0 退出码

#### Scenario: SC-009

- **GIVEN** 执行镜像状态巡检命令
- **WHEN** 检查其输出
- **THEN** 输出 SHALL 同时报告裸库 sha、GitHub sha 与故障标记状态
- **AND** 输出 SHALL 可在无人工解读的情况下被判定

### Requirement: 镜像失败必须进入控制面消息流，且不因此产生对控制面的强依赖

#### Scenario: SC-010

- **GIVEN** 控制面 nodes 表为空
- **WHEN** 部署镜像告警能力
- **THEN** 系统 SHALL 注册一个基础设施节点身份
- **AND** 该身份 SHALL 与 agent 节点身份区分
- **AND** 注册 SHALL 幂等：重复执行不报错、不产生重复记录

#### Scenario: SC-011

- **GIVEN** 控制面可达且基础设施节点已注册
- **WHEN** 镜像失败
- **THEN** 系统 SHALL 向控制面投递一条 notice 消息
- **AND** 消息 body SHALL 包含失败项与发生时间
- **AND** 消息 SHALL 可在 GET /messages 中被检索到

#### Scenario: SC-012

- **GIVEN** 控制面不可达
- **WHEN** 镜像失败
- **THEN** 回显与故障标记 SHALL 仍然生效
- **AND** 上报失败 SHALL NOT 改变钩子的退出码
- **AND** 上报失败 SHALL NOT 阻断或延迟推送返回

### Requirement: 钩子必须保持「不阻塞流转」与「非强制推送」两条既有语义

#### Scenario: SC-013

- **GIVEN** 镜像失败
- **WHEN** 钩子结束
- **THEN** 钩子退出码 SHALL 为 0
- **AND** git push SHALL 成功返回
- **AND** 告警 SHALL 通过输出与标记表达，而非退出码

#### Scenario: SC-014

- **GIVEN** 钩子的推送实现
- **WHEN** 审查推送命令
- **THEN** 推送 SHALL NOT 包含 --force 或等价强制选项
- **AND** GitHub 侧分叉时 SHALL 失败并告警，而非覆盖远端提交

### Requirement: 接入文档必须与新告警能力一致

#### Scenario: SC-015

- **GIVEN** 告警能力已落地
- **WHEN** 阅读 DISTRIBUTED_ACCESS.md
- **THEN** 日常操作表 SHALL 包含「查镜像状态」的一条命令
- **AND** 故障处置表 SHALL 包含镜像失败的完整处置路径
- **AND** 文档 SHALL NOT 存在「必须人工 tail 日志才知道镜像失败」的表述

### Requirement: 镜像告警不得破坏既有工程约束

#### Scenario: SC-016

- **GIVEN** 镜像告警变更已完成
- **WHEN** 运行既有工程测试套件
- **THEN** 测试 SHALL 保持全绿
- **AND** 基线为 592 passed

#### Scenario: SC-017

- **GIVEN** 告警能力部署完成
- **WHEN** 审查仓库内容
- **THEN** 仓库中 SHALL NOT 出现任何凭证
- **AND** 控制面访问 SHALL NOT 依赖写入仓库的密钥

### Requirement: 巡检命令必须能被其他节点直接使用，而不是只在作者机器上可跑

#### Scenario: SC-018

- **GIVEN** 巡检命令已提交到仓库
- **WHEN** 另一节点 git pull 后直接执行该命令
- **THEN** 命令 SHALL 在无额外安装步骤的情况下可直接执行
- **AND** 文件 SHALL 带可执行位（Windows 侧创建后须显式恢复 mode 755）
- **AND** 依赖 SHALL 限于 bash 与 git（及 ssh 别名），SHALL NOT 依赖 jq 等非必需工具
- **AND** 缺失前置条件（如 ssh 别名未配置）时 SHALL 给出明确提示，而非静默失败
