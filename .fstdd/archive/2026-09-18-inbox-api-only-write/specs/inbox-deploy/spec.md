# Spec: inbox-deploy

> Change: 2026-09-18-inbox-api-only-write | Auto-generated Human View

## Requirements

### Requirement: 部署脚本幂等加固：建用户、收权限、显式 env 声明、端状态校验

#### Scenario: SC-101

- **GIVEN** 目标机可能已存在或不存在 fstdd-inbox 用户与既有服务
- **WHEN** 连续两次执行 deploy_inbox_server.sh
- **THEN** 两次 SHALL 均以 exit 0 结束，且端状态一致（服务 active、属主与权限不变）
- **AND** fstdd-inbox 用户 SHALL 存在且 shell 为 nologin
- **AND** 收目录属主 SHALL 为 fstdd-inbox:fstdd-inbox

#### Scenario: SC-102

- **GIVEN** 远端 /home/ubuntu/fstdd-inbox-server/inbox.env 缺失
- **WHEN** 执行部署脚本
- **THEN** 脚本 SHALL 提前中止并以非 0 退出
- **AND** SHALL 打印明确处置指导（先恢复 env 文件，不自动创建、不上传）
- **AND** SHALL 不修改既有 systemd 单元、不重启服务

#### Scenario: SC-103

- **GIVEN** 部署脚本写出 systemd 单元
- **WHEN** 检查单元文件内容
- **THEN** SHALL 含 User=fstdd-inbox
- **AND** SHALL 含 EnvironmentFile= 行
- **AND** SHALL 含 UMask=0022（保证日志文件 other 可读）
- **AND** SHALL 不含 pkill -f inbox_server（会匹配 ssh 命令行自身，历史事故）

#### Scenario: SC-104

- **GIVEN** 部署与重启完成
- **WHEN** 执行后置校验
- **THEN** 权限断言、ubuntu 写入负向探测、API 正向落盘、/health 四组断言 SHALL 逐条输出 PASS/FAIL
- **AND** 任一断言 FAIL SHALL 使校验整体以非 0 退出
- **AND** 校验 SHALL 输出可贴回简报的原文证据（命令 + 输出）

### Requirement: 消除源码-部署漂移，并把漂移防护写进测试

#### Scenario: SC-105

- **GIVEN** 部署完成后
- **WHEN** 比对仓库与服务端文件 md5
- **THEN** tools/inbox_server.py SHALL 与服务端部署版 md5 一致
- **AND** 比对结果 SHALL 写入交付证据（含两处 md5 原文）

#### Scenario: SC-106

- **GIVEN** 仓库内既有 pytest 套件
- **WHEN** 执行 upstream 全量 pytest
- **THEN** 既有用例 SHALL 全绿（无回归）
- **AND** 新增鉴权用例组（SC-006..SC-009 对应）SHALL 通过
- **AND** 新增部署脚本静态守护用例（SC-103 对应）SHALL 通过
