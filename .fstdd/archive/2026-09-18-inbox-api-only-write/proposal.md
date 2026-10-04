# inbox 收目录收口：仅服务用户可写（scp 直写被文件系统拒绝）

<!-- source_hash: 16fa0e448d063e2a -->
<!-- generated_at: 2026-09-18T09:04:43+00:00 -->
<!-- canonical: canonical/proposals/2026-09-18-inbox-api-only-write.yaml -->

## Why

FSTDD 经验 inbox（/home/ubuntu/fstdd-inbox）的写权限对 ssh 登录用户 ubuntu
完全开放，而六个节点 agent 均以 ubuntu 身份 scp 直写该目录。试运行数据
（EXP-20260915/16/17 系列）在 09-18 一天内被四次重发（10:25、14:00、16:01 等），
全部绕过 POST API 的限流、去重与脱敏校验（received 计数未随 17 个文件跳变，
实证为 scp 直写）。API 层的一切防护（鉴权/限流/敏感拒收）在数据面上形同虚设。


## What Changes

- 同步：repo tools/inbox_server.py 吸收服务端鉴权版（含 X-FSTDD-Token/Bearer/IP 白名单灰度），消除源码-部署漂移
- 新增：部署脚本建专用系统用户 fstdd-inbox（nologin），收目录 chown 至该用户并收紧权限；systemd 单元 User=fstdd-inbox + EnvironmentFile 显式声明 + UMask=0022；远端 inbox.env 不存在则中止（绝不覆盖既有凭证）
- 新增：部署后置校验（幂等）——namei 权限断言 + ubuntu 身份写入探测必须 EACCES + API POST 落地成功 + /health 正常
- 运维：现存 EXP-20260915/16/17-* 试运行文件移入收目录内 quarantine/（可逆 mv，不删除），退出每日合并视野

### New Capabilities

- **inbox-api-only-write**：收目录写权限仅属服务运行用户 fstdd-inbox；非服务身份（节点 scp / 人工直写）被文件系统拒绝；ubuntu 只读（server.log 巡检、/health 不受影响）

### Modified Capabilities

- **inbox-deploy**：deploy_inbox_server.sh 从「传代码+起服务」升级为幂等加固部署：建用户/收权限/显式 env 声明/端状态校验，杜绝重部署回退鉴权

## Success Criteria

- [ ] 部署后 namei -l 显示 /home/ubuntu/fstdd-inbox 属主为 fstdd-inbox:fstdd-inbox，目录无 ubuntu 写位
- [ ] 以 ubuntu 身份向收目录 scp/touch 探测文件返回 Permission denied（负向断言，实测输出为证）
- [ ] 带 token POST 1 条测试经验返回 accepted=1 且文件落盘、received 递增；无 token 非白名单 IP POST 返回 401
- [ ] systemctl is-active fstdd-inbox = active，且 EnvironmentFile 行存在于单元中（重跑 deploy 脚本不回退）
- [ ] repo tools/inbox_server.py 与服务端部署版 md5 一致（漂移清零）
- [ ] EXP-20260915/16/17-* 共 30 个文件全部位于 quarantine/（09-18 16:41 实测清单），收目录根下零残留
- [ ] 既有 pytest 套件（含 test_inbox_endpoint.py）全绿，新增鉴权用例（RED→GREEN）入套件
