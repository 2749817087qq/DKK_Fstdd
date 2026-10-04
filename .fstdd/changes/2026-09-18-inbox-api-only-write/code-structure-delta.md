# Code Structure Delta — 2026-09-18-inbox-api-only-write
> 生成时间: 2026-10-04T03:01:04+00:00 | Git commit: 155e4c6
> 置信度: 0.70 (AI-generated — 以源代码为准)

## 变更文件

- `tools/inbox_server.py` — 新增鉴权三态：`_auth_token()` / `_allow_ips()` / `_ip_allowed()` / `_authorized()` / `_auth_banner()`；`do_POST` 调整为「先消费请求体 → 再鉴权」；常量 `AUTH_TOKEN_ENV` / `AUTH_ALLOW_IPS_ENV` / `AUTH_HEADER`。
- `tools/deploy_inbox_server.sh` — 加固为幂等部署：建 `fstdd-inbox` 系统用户（nologin）、收目录 `chown/chmod`、单元 `User=`/`EnvironmentFile=`/`UMask=0022`、env 存在性校验、后置校验段（含负向写入探测）。
- `upstream/tests/test_inbox_endpoint.py` — 新增 `TestDAuthGate`（D 组，TC-IAOW-006..009）与 `TestEDeployScriptGuards`（E 组，TC-IBDP-002/003/004）；autouse fixture 增补 token/白名单 env 清理。