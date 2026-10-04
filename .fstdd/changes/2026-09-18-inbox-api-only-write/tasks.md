# 2026-09-18-inbox-api-only-write 任务清单

> 交付分层：仅实现 **A 仓库侧**（本机 pytest 可验）；**B 外部挂账**随交付转 K，不在本清单内。
> 契约来源：`canonical/specs/code/inbox-api-only-write.yaml`、`canonical/specs/code/inbox-deploy.yaml`

## 1. inbox-api-only-write（P0）

- [x] 1.1 `tools/inbox_server.py` 补鉴权三态：`FSTDD_INBOX_TOKEN` 配置时校验 `X-FSTDD-Token`，凭证缺失/错误且源 IP 不在 `FSTDD_INBOX_ALLOW_IPS` → 401 + `[inbox] 401 <- <ip>` 日志
- [x] 1.2 白名单 IP 灰度放行：源 IP ∈ `FSTDD_INBOX_ALLOW_IPS` → 放行并记 `legacy-ip` 日志（依赖 #1.1）
- [x] 1.3 未配置 token → 保持开放，启动横幅含 `auth: OFF`（依赖 #1.1）
- [x] 1.4 `/health`、`/healthz` 始终免鉴权，`received` == 收目录根下 `*.md` 数（依赖 #1.1）
- [x] 1.5 新增测试组 TC-IAOW-006/007/008/009（进程内真实 HTTP 服务 + monkeypatch 改 env）

## 2. inbox-deploy（P0）

- [x] 2.1 `tools/deploy_inbox_server.sh` 幂等加固：建 `fstdd-inbox` 系统用户（nologin）、收目录 `chown/chmod`、单元加 `User=` / `EnvironmentFile=` / `UMask=0022`
- [x] 2.2 远端 `inbox.env` 缺失即中止（非 0 退出，不生成/不覆盖/不回显）（依赖 #2.1）
- [x] 2.3 后置校验段：逐条 PASS/FAIL + **负向写入探测**，任一 FAIL 整体非 0 退出（依赖 #2.1）
- [x] 2.4 危险模式缺席：脚本不得含 `pkill -f inbox_server`（依赖 #2.1）
- [x] 2.5 新增静态守护测试组 TC-IBDP-002/003/004

## 3. 测试与验证

- [x] 3.1 切片 1 新增 4 用例通过 + 既有 A/B/C 组无回归
- [x] 3.2 切片 2 新增 3 用例通过
- [x] 3.3 全量 pytest `upstream/tests` 通过（TC-IBDP-006 回归保护）

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- B 层（属主/权限端状态、scp 拒绝、生产落盘、quarantine、部署幂等、md5 一致性）
  为**外部挂账**，对应 TC-IAOW-001..005 与 TC-IBDP-001/002(端上)/004(端上)/005，
  随交付说明转 K 执行并回执，不阻塞 Gate 3。
-->