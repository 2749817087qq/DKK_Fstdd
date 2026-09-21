# 2026-09-18-inbox-api-only-write 测试方案与详细案例

> 版本：1.0
> 创建日期：2026-09-18
> 对应 Phase 2 Spec：specs/inbox-api-only-write/spec.md、specs/inbox-deploy/spec.md

## 一、测试策略

### 1.1 测试金字塔

本变更跨「本地可测代码」与「远端端状态」两层，比例刻意倒向后者：

- **单元/契约层（pytest，30%）**：鉴权三态分支（401 / legacy-ip 放行 / 开放）、
  `/health` 免鉴权、部署脚本静态守护（单元关键行不得缺失、不得出现危险模式）。
- **E2E 端状态层（ssh 实测，70%）**：属主与权限、ubuntu 写入被拒（负向）、
  API 正向落盘、quarantine 计数守恒、部署幂等。
- 不做 mock 层：本变更的真相全在文件系统与 systemd 上，mock 它等于自欺。

### 1.2 测试原则

- **负向断言是硬要求**：权限收口必须验证「写不进去」，只验证「读得到」会产生全绿假象。
- **端状态验证，不看回显**：远端命令会被执行两次，一切以 `ls -l` / `namei` 等
  端状态输出为准。
- **只移不删**：涉及真实数据的步骤一律可逆，断言计数守恒（30 → 30）。
- **部署前先备份**：收目录 tar 快照，rollback 路径写进 agent_spec。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/test_inbox_endpoint.py` | 44（A29/B5/C10） | 集成（进程内真实 HTTP 服务） | 端点协议、限流、客户端分批重试 |
| `upstream/tests/test_inbox_pull.py` | — | 集成 | 拉取端 inbox_pull.py |
| `tools/verify_workbuddy_skills.py` | — | 静态 | skill 安装与策略哨兵 |

## 二、详细测试案例

### 功能 1：inbox-api-only-write（收目录仅服务用户可写）

对应 spec：`inbox-api-only-write/spec.md` → REQ-001 / REQ-002 / REQ-003

#### 案例 1.1 — ubuntu 身份直写被拒 + 属主断言

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-001 |
| **对应 Spec** | inbox-api-only-write → SC-001 |
| **优先级** | P0 |
| **预置条件** | 服务以 fstdd-inbox 运行；收目录已 chown 且 chmod 755 |
| **输入** | `touch /home/ubuntu/fstdd-inbox/.perm-probe`；`namei -l /home/ubuntu/fstdd-inbox` |
| **预期结果** | touch 退出码 ≠ 0 且输出含 Permission denied；目录无 .perm-probe；属主 fstdd-inbox:fstdd-inbox；权限 0755 |
| **当前状态** | ❌ 测试缺（部署后执行） |

#### 案例 1.2 — API 正向落盘与计数递增

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-002 |
| **对应 Spec** | inbox-api-only-write → SC-002 |
| **优先级** | P0 |
| **预置条件** | 服务 active；持有效 token（从远端 env 读取，不回显） |
| **输入** | POST 1 条 `EXP-LOCKDOWN-PROBE-1`；前后各取一次 `/health` |
| **预期结果** | 200 且 accepted=1；文件属主 fstdd-inbox；received +1；探测文件事后清理 |
| **当前状态** | ❌ 测试缺（部署后执行） |

#### 案例 1.3 — 只读巡检链路不断

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-003 |
| **对应 Spec** | inbox-api-only-write → SC-003 |
| **优先级** | P0 |
| **预置条件** | 收目录已收权 |
| **输入** | `tail -3 /home/ubuntu/fstdd-inbox/server.log`；`curl /health` |
| **预期结果** | 两者均成功；server.log 对 other 可读（0644 或更宽） |
| **当前状态** | ❌ 测试缺（部署后执行） |

#### 案例 1.4 — scp 直写被拒（本次要根治的行为）

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-004 |
| **对应 Spec** | inbox-api-only-write → SC-004 |
| **优先级** | P0 |
| **预置条件** | 以 ubuntu 身份 ssh/scp 可用 |
| **输入** | `scp probe.md fstdd-hub:/home/ubuntu/fstdd-inbox/` |
| **预期结果** | 传输失败（Permission denied）；目录内无该文件；server.log 无 accepted 记录 |
| **当前状态** | ❌ 测试缺（部署后执行） |

#### 案例 1.5 — 试运行文件入 quarantine 且计数守恒

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-005 |
| **对应 Spec** | inbox-api-only-write → SC-005 |
| **优先级** | P0 |
| **预置条件** | 收目录根下存在 30 个 EXP-2026091[567]-*.md（16:41 实测） |
| **输入** | 移动至 quarantine/ 并双向计数 |
| **预期结果** | 根下残留 0；quarantine 内 30；总量守恒不丢 |
| **已知副作用** | `/health` received 将同步下降约 30（glob 不递归），属预期 —— 须写入节点通知，避免节点误判「数据被删」 |
| **当前状态** | ❌ 测试缺（部署后执行） |

#### 案例 1.6 — 无凭证非白名单来源返回 401

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-006 |
| **对应 Spec** | inbox-api-only-write → SC-006 |
| **优先级** | P0 |
| **预置条件** | 进程内起服务，env 设 FSTDD_INBOX_TOKEN，白名单为空 |
| **输入** | POST 不带任何凭证头 |
| **预期结果** | 401 且 body 含 unauthorized；日志出现 `[inbox] 401` |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

#### 案例 1.7 — 白名单 IP 灰度放行

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-007 |
| **对应 Spec** | inbox-api-only-write → SC-007 |
| **优先级** | P1 |
| **预置条件** | env 设 token 且 FSTDD_INBOX_ALLOW_IPS 含 127.0.0.1/32 |
| **输入** | 无凭证 POST（源 IP 127.0.0.1） |
| **预期结果** | 200 accepted=1；日志含 legacy-ip 放行 |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

#### 案例 1.8 — 未配置 token 时保持开放

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-008 |
| **对应 Spec** | inbox-api-only-write → SC-008 |
| **优先级** | P1 |
| **预置条件** | env 无 FSTDD_INBOX_TOKEN（需重载模块读 env） |
| **输入** | 任意 POST |
| **预期结果** | 200；启动日志含 auth: OFF |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

#### 案例 1.9 — /health 免鉴权且计数口径正确

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-009 |
| **对应 Spec** | inbox-api-only-write → SC-009 |
| **优先级** | P0 |
| **预置条件** | 任意鉴权配置 |
| **输入** | GET /health |
| **预期结果** | 200；received == 收目录根下 *.md 数（不含 quarantine） |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

### 功能 2：inbox-deploy（幂等加固部署）

对应 spec：`inbox-deploy/spec.md` → REQ-101 / REQ-102

#### 案例 2.1 — 连续两次部署端状态一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-001 |
| **对应 Spec** | inbox-deploy → SC-101 |
| **优先级** | P0 |
| **预置条件** | 远端 env 存在 |
| **输入** | 连续执行 deploy_inbox_server.sh 两次 |
| **预期结果** | 均 exit 0；is-active=active；属主与权限两次一致 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — env 缺失即中止

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-002 |
| **对应 Spec** | inbox-deploy → SC-102 |
| **优先级** | P0 |
| **预置条件** | 临时重命名远端 inbox.env（测完恢复） |
| **输入** | 执行部署脚本 |
| **预期结果** | 非 0 退出；打印处置指导；不改动既有单元、不重启服务 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — 单元关键行静态守护

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-003 |
| **对应 Spec** | inbox-deploy → SC-103 |
| **优先级** | P1 |
| **预置条件** | 本地仓库 |
| **输入** | pytest 读取 tools/deploy_inbox_server.sh 全文断言 |
| **预期结果** | 含 `User=fstdd-inbox`、`EnvironmentFile=`、`UMask=0022`；不含 `pkill -f inbox_server` |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

#### 案例 2.4 — 后置校验逐条输出且失败即非 0

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-004 |
| **对应 Spec** | inbox-deploy → SC-104 |
| **优先级** | P0 |
| **预置条件** | 部署完成 |
| **输入** | 执行 verify 段 |
| **预期结果** | 四组断言逐条 PASS/FAIL 输出；任一 FAIL → 整体非 0 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.5 — 源码-部署 md5 一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-005 |
| **对应 Spec** | inbox-deploy → SC-105 |
| **优先级** | P0 |
| **预置条件** | 部署完成 |
| **输入** | 两端 md5sum 比对 |
| **预期结果** | 一致（漂移清零）；证据含两处 md5 原文 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.6 — 既有套件无回归 + 新增用例通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-006 |
| **对应 Spec** | inbox-deploy → SC-106 |
| **优先级** | P0 |
| **预置条件** | upstream 目录 |
| **输入** | `C:/Python311/python.exe -m pytest tests -q` |
| **预期结果** | 既有 44+ 用例全绿；新增鉴权组与脚本守护组通过 |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元/契约(pytest) | E2E(ssh 端状态) | 静态守护 | 状态 |
|----------|------------------|-----------------|----------|------|
| 鉴权三态分支 | TC-IAOW-006/007/008 | — | — | 🔴 |
| /health 免鉴权与计数 | TC-IAOW-009 | TC-IAOW-002/005 | — | 🔴 |
| 收目录权限与属主 | — | TC-IAOW-001/003 | — | 🔴 |
| scp 直写拒绝 | — | TC-IAOW-004 | — | 🔴 |
| quarantine 迁移 | — | TC-IAOW-005 | — | 🔴 |
| 部署幂等与中止 | — | TC-IBDP-001/002/004/005 | TC-IBDP-003 | 🔴 |
| 回归保护 | TC-IBDP-006 | — | — | 🔴 |

## 四、回归风险矩阵

| 风险区域 | 本次改动 | 已有回归保护 | 风险等级 |
|----------|----------|--------------|----------|
| `inbox_server.py` 回灌鉴权分支 | 代码以部署版为准同步进仓库 | test_inbox_endpoint.py A/B/C 44 用例 | 🟡 |
| `/health` received 口径 | quarantine 后计数下降约 30 | TC-IAOW-009 显式断言口径 | 🔴（口径变化，须公告节点） |
| 服务重启可用性 | User / EnvironmentFile / UMask 变更 | TC-IBDP-001 + TC-IAOW-002 正向落盘 | 🟡 |
| 巡检只读链路 | 目录权限收紧 | TC-IAOW-003 | 🟡 |
| 节点回传中断 | scp 通道被拒（本次目的） | 无保护 —— 须 K 发通知告知改走 API | 🔴（预期行为，需沟通） |
| 部署脚本重写 | 单元模板与用户/权限逻辑 | TC-IBDP-003 静态守护 | 🟡 |

## 五、建议补充顺序

1. **第一优先（部署前必补，P0 单元测试）**：TC-IAOW-006、TC-IAOW-009、TC-IBDP-003
   —— 三者可在本地 RED→GREEN，先把鉴权与脚本守护钉死，再动生产。
2. **第二优先（部署当轮执行，P0 E2E）**：TC-IAOW-001、002、003、004、005、
   TC-IBDP-001、002、004、005 —— 部署脚本 verify 段逐条跑并留证据。
3. **第三优先（P1，随后补）**：TC-IAOW-007、TC-IAOW-008 —— 灰度分支覆盖，
   不阻塞部署，但应在本 change 关闭前补齐。

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 收目录属主 ubuntu:ubuntu 模式 0775 | 2026-09-18T08:53:00+00:00 | deployed-2b58b70b | `ssh fstdd-hub "ls -ld /home/ubuntu/fstdd-inbox"` |
| 服务单元 User=ubuntu 且含 EnvironmentFile | 2026-09-18T08:53:00+00:00 | deployed-2b58b70b | `ssh fstdd-hub "systemctl cat fstdd-inbox"` |
| 仓库与部署版 md5 不等（742827d9 vs 2b58b70b） | 2026-09-18T08:53:00+00:00 | deployed-2b58b70b | 两端 `md5sum` |
| 17 文件直写而 received 未同步（88→97） | 2026-09-18T08:41:00+00:00 | deployed-2b58b70b | 16:41 小时简报基线 diff + `/health` |
| 试运行文件计 30 个 | 2026-09-18T08:55:00+00:00 | deployed-2b58b70b | `ssh fstdd-hub "ls /home/ubuntu/fstdd-inbox/EXP-2026091[567]-*.md ｜ wc -l"` |

- `observed_at` 是信息采集时刻，不是文档生成时刻。
- 部署后新增证据（md5、权限、负向断言输出）将在 BUILD 阶段回填本节。
