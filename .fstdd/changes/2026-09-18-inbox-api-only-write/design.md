# inbox 收目录收口：仅服务用户可写 — 技术设计

## Context

FSTDD 经验回传的数据面是云服务器上的 `/home/ubuntu/fstdd-inbox`（Python 标准库
HTTP 服务 `fstdd-inbox.service`，监听 0.0.0.0:8787）。当前状态（2026-09-18 16:41 实测）：

- 收目录属主 `ubuntu:ubuntu`，模式 `drwxrwxr-x`；服务单元 `User=ubuntu`
  —— **服务进程与节点 ssh 登录是同一个身份，不存在任何权限边界**。
- 六个节点 agent 均以 `ubuntu` 身份 scp 直写该目录。09-18 一天四次重发试运行数据
  （10:25 / 14:00 / 16:01 等），16:01 一次就有 17 个 `.md` 落盘或刷新，而
  `received` 计数仅 88→97 —— 实证这些写入**绕过了 POST 通道**，服务端限流、
  鉴权、敏感内容拒收在数据面上全部失效。
- 源码漂移：仓库 `tools/inbox_server.py`（md5 `742827d9`）落后于服务端部署版
  （md5 `2b58b70b`，含 09-18 上线的 token 鉴权与 IP 白名单灰度）；而本地
  `deploy_inbox_server.sh` 的单元模板**没有 `EnvironmentFile` 行**，任何时候重跑
  部署脚本都会把鉴权版覆盖成无鉴权旧版并静默丢掉 auth。

约束：服务是生产链路（节点回传唯一通道），不可长时间中断；`inbox.env` 内含
token 与 IP 白名单，属机密；K 的每小时巡检依赖 `ubuntu` 身份**读取** `server.log`。

## Decisions

### 1. 收口手段：文件系统权限（专用服务用户），而非事后对账守卫

**方案**：建系统用户 `fstdd-inbox`（nologin），收目录 `chown -R` 给它、
目录 `chmod 755`，systemd 单元 `User=fstdd-inbox`。节点 scp 以 `ubuntu`
身份写入 → 内核直接 `EACCES`。

**为什么**：这是**拒绝在写入之前**发生，而不是写入之后再发现再清理。
试运行数据四次重发证明「靠节点自律 + K 事后巡检」无效；权限边界是唯一
无需信任对方的结构性约束。API 侧的鉴权/限流/脱敏因此重新获得意义。

**备选方案及排除原因**：
- 备选 A「manifest 对账守卫」：服务落盘时写 `accept.jsonl`（路径 + sha256），
  定时任务把未登记文件移入 quarantine。能发现、但**不能阻止**写入，且
  节点与守卫同属 ubuntu，守卫自身可被篡改，属过度设计 —— 权限收口后已无必要。
- 备选 B「`chattr +a` 目录只追加」：能挡改写但不能挡新建（试运行数据正是新建），
  且与按 EXP-ID 覆盖写的既有语义冲突。
- 备选 C「改成 root 运行服务」：同样有效，但服务以 root 常驻监听公网端口，
  比专用无登录用户风险高。

### 2. 服务运行用户：专用系统用户 fstdd-inbox，而非 root

**方案**：`useradd --system --no-create-home --shell /usr/sbin/nologin fstdd-inbox`。

**为什么**：最小权限。无 shell、无家目录、无登录能力，即便 token 泄露也
换不来一个可交互账号。

**备选方案及排除原因**：root 见决策 1；沿用 ubuntu 则无边界（现状问题本身）。

### 3. 权限收口后保持 ubuntu 只读

**方案**：目录 `0755`，文件 `0644`，单元加 `UMask=0022`；`server.log` 由 systemd
以服务用户追加写，仍对 other 可读。

**为什么**：K 的每小时巡检（hourly 简报）要 `tail server.log`，节点回执流程要
`GET /health`。收口只收**写**，不收**读**，否则巡检链路当场断掉。

### 4. 源码以「服务端部署版」为准回灌仓库

**方案**：把远端 `inbox_server.py`（鉴权版，2b58b70b）同步回
`tools/inbox_server.py`，再在仓库版之上演进；部署脚本重写时保持
`EnvironmentFile` 行。

**为什么**：部署版才是实际生效的行为。若以仓库旧版为准，等于把已上线的鉴权
回退掉 —— 属于「源码落后于契约」的反向漂移，必须清零。

### 5. inbox.env：只校验存在性，绝不生成、绝不覆盖、绝不回显

**方案**：脚本检测远端 `/home/ubuntu/fstdd-inbox-server/inbox.env` 是否存在，
缺失即**中止**（非 0 退出）并打印处置指导；存在则只引用，不把内容读进输出。

**为什么**：token 属机密；`EnvironmentFile` 指向不存在的文件会让 unit 起不来，
必须在部署早期失败，而不是重启后才发现服务挂了。

### 6. 试运行数据：移入 quarantine/，只移不删

**方案**：30 个 `EXP-20260915/16/17-*.md` 移入收目录下 `quarantine/` 子目录。

**为什么**：删除不可逆且违反数据保守原则；留在原地则继续污染每日合并与
`/health` 计数（`received` 按 `*.md` 计数，quarantine 子目录不参与 glob）。
移动可逆，且让 `received` 口径回到真实经验数。

### 7. 验证：端状态断言写进部署脚本，含负向断言

**方案**：部署脚本 verify 段逐条输出 PASS/FAIL：属主断言、`ubuntu` 写入探测
**必须失败**、API 正向落盘、`/health`。任一 FAIL → 整体非 0 退出。

**为什么**：远端命令会被执行两次（本机实测），脚本必须幂等；「测试绿了 ≠
断言有效」在本项目已应验五次，因此强制包含一条**负向断言**（写入必须被拒），
否则权限没真收口也会全绿。

## Architecture

```
变更前（写入通道无边界）                变更后（单写入通道）

节点 agent ──scp──┐                     节点 agent ──scp──✗ EACCES
                  ├──> /home/ubuntu/fstdd-inbox             │
HTTP POST ────────┘      (ubuntu:ubuntu 0775)               │
                                                            ▼
                                             /home/ubuntu/fstdd-inbox
                                             (fstdd-inbox 0755，只读可见)
                                                     ▲
HTTP POST ──> fstdd-inbox.service ──写────────────────┘
              (User=fstdd-inbox)        服务用户独占写权限
              EnvironmentFile=inbox.env

              ubuntu ──读──> server.log / *.md（巡检链路保留）

目录布局（变更后）
  /home/ubuntu/fstdd-inbox/
    ├── *.md            经验文件（仅服务用户可写）
    ├── server.log
    └── quarantine/     30 个试运行文件（只移不删）
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 部署出错导致回传链路中断（生产） | 变更前 tar 快照收目录；脚本幂等；后置校验含 API 正向落盘断言；失败按 rollback 步骤回退属主与单元 |
| chown 后 K 自己也无法直写收目录 | 已知且接受：后续清理走 sudo 或 API；已写入提案 Critical 声明 |
| 服务重启秒级窗口丢回传 | 选低峰执行；重启前连续两次采样 `/health` received 确认无在途批量 |
| inbox.env 丢失导致 unit 起不来 | 脚本早期存在性校验并中止；不删除、不覆盖远端 env |
| 鉴权版代码回灌时手工复制出错 | 双断言：md5 一致 + 端行为（401 行 / legacy-ip 放行行） |
| quarantine 误移真实经验 | 只匹配 `EXP-2026091[567]-*.md` 前缀（试运行命名），移动前先 ls 列清单并计数核对 30 |
| 权限过严导致巡检读不到 | UMask=0022 + 目录 0755 + 日志 0644，CP-4 / CP-5 双向断言覆盖 |
