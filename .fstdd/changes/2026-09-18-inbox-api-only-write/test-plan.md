# 2026-09-18-inbox-api-only-write 测试方案与详细案例（分层版）

> 版本：2.0（v2.0 引入「仓库侧可测 / 外部挂账」交付分层）
> 创建日期：2026-09-18；分层修订：2026-10-04
> 对应 Phase 2 Spec（Canonical YAML）：
> - `canonical/specs/code/inbox-api-only-write.yaml`（REQ-001..003 → SC-001..009）
> - `canonical/specs/code/inbox-deploy.yaml`（REQ-101..102 → SC-101..106）
> - `canonical/specs/agent/inbox-api-only-write.yaml`（CP-1..CP-7）
> - `canonical/specs/agent/inbox-deploy.yaml`（CP-11..CP-15）

## 零、交付分层总则（本次收口口径）

本 change 的验收项分两层，对应两种不同的「完成」定义：

| 层 | 定义 | 本机可测 | 收口口径 |
|----|------|---------|---------|
| **A 仓库侧**（repo-side） | 仓库内代码 / 脚本 / 测试的落地与本地验证 | ✅ 可 | 必须全绿才可进入 Gate 3 |
| **B 外部挂账**（external） | 生产服务器端状态与运维动作（需 ssh 生产） | ❌ 不可 | **不阻塞仓库侧收口**；以「挂账清单 + 人工步骤」随交付说明转出 |

> **先例**：`2026-10-04-github-mirror-secret-remediation` —— 纯外部人工项（GitHub unblock / PAT 轮换 / 重推镜像 / Release 补发）列入 CHANGELOG「外部人工待办」，仓库侧加固（凭证门禁测试 + 脱敏脚本）独立闭环。本 change 沿用同一口径。
>
> **本机环境事实**：本机虚拟机与生产服务器 `43.134.236.80`（ssh 别名 `fstdd-hub`）**不互通**，B 层全部步骤无法在本机代跑；只能由持生产 ssh 的 K（归口端）执行并回执。故 B 层以挂账形式交付，其证据在 K 回执后回填 `## 六、证据记录`。

### 分层映射（SC → 层 → TC）

| SC | 验收内容 | 层 | TC | 本机验证手段 / 外部人工步骤 |
|----|---------|----|----|------------------------------|
| SC-001 | 收目录属主与权限 | B | TC-IAOW-001 | 人工：`ssh … namei -l /home/ubuntu/fstdd-inbox` |
| SC-002 | 生产 API 正向落盘 + 计数递增 | B | TC-IAOW-002 | 人工：token POST + 前后 `/health` |
| SC-003 | 只读巡检链路不断 | B | TC-IAOW-003 | 人工：`tail server.log` + `curl /health` |
| SC-004 | scp 直写被拒（负向） | B | TC-IAOW-004 | 人工：`scp` 探测返回 Permission denied |
| SC-005 | quarantine 计数守恒（30） | B | TC-IAOW-005 | 人工：mv 后双向计数 |
| SC-006 | 无 token 非白名单 → 401 | **A** | TC-IAOW-006 | pytest：进程内服务 + `FSTDD_INBOX_TOKEN` |
| SC-007 | 白名单 IP 灰度放行 | **A** | TC-IAOW-007 | pytest：`FSTDD_INBOX_ALLOW_IPS=127.0.0.1/32` |
| SC-008 | 未配 token 保持开放 | **A** | TC-IAOW-008 | pytest：无 token env 重载模块 |
| SC-009 | `/health` 免鉴权 + 计数口径 | **A** | TC-IAOW-009 | pytest：`GET /health` |
| SC-101 | 部署幂等（连续两次一致） | B | TC-IBDP-001 | 人工：连续两次执行部署脚本 |
| SC-102 | env 缺失即中止、不改服务 | **A(静态)**＋B(端上) | TC-IBDP-002 | A：pytest 断言脚本含存在性校验 + 非 0 退出；B：人工端上复核 |
| SC-103 | 单元关键行静态守护 | **A** | TC-IBDP-003 | pytest：读 `tools/deploy_inbox_server.sh` 全文断言 |
| SC-104 | 后置校验四组断言（含负向） | **A(静态)**＋B(端上) | TC-IBDP-004 | A：pytest 断言脚本含 verify 段与负向断言；B：人工端上复核 |
| SC-105 | repo ↔ deployed md5 一致 | B | TC-IBDP-005 | 人工：两端 `md5sum` 比对 |
| SC-106 | 全量回归 + 新增用例通过 | **A** | TC-IBDP-006 | pytest：`upstream/tests` 全量 |

**仓库侧（A 层）需在 BUILD 阶段新增/修改的代码与测试**：

1. `tools/inbox_server.py`：补入鉴权逻辑（行为契约见 SC-006/007/008/009）——当前仓库版**无任何鉴权代码**（实测：全文件 grep `FSTDD_INBOX_TOKEN|X-FSTDD-Token|Bearer|unauthorized` 零命中）。
2. `tools/deploy_inbox_server.sh`：加固为幂等部署（建用户 / 收权限 / 显式 `EnvironmentFile` / `UMask` / env 存在性校验 / 后置校验段）——当前脚本 `User=ubuntu` 且单元模板**无 `EnvironmentFile` 行**（见文件 L61-79）。
3. `upstream/tests/test_inbox_endpoint.py`：新增鉴权组（SC-006..009 对应）。
4. 新增部署脚本静态守护测试（SC-103 对应，可在 `test_inbox_endpoint.py` 内新开一组或独立文件）。

## 一、测试策略

### 1.1 测试金字塔

本变更跨「本地可测代码」与「远端端状态」两层；分层后两者**不再混算**：

- **A 层（本地 pytest，本 change 的收口依据）**：鉴权三态分支（401 / legacy-ip 放行 / 开放）、`/health` 免鉴权与计数口径、部署脚本静态守护（关键行齐备、危险模式缺席）、全量回归。
- **B 层（ssh 端状态，外部挂账）**：属主与权限、ubuntu 写入被拒（负向）、生产 API 正向落盘、quarantine 计数守恒、部署幂等。**这些步骤本机无法代跑**，随交付转 K 人工执行并回执。
- 不做 mock 层：本变更的真相在文件系统与 systemd 上；但 A 层对**服务进程行为**用进程内真实 HTTP 服务器验证（非 mock），既真实又可本地复现。

### 1.2 测试原则

- **负向断言是硬要求**：权限收口必须验证「写不进去」，只验证「读得到」会产生全绿假象。
- **端状态验证，不看回显**：远端命令会被执行两次（本机实测），一切以 `ls -l` / `namei` 等端状态输出为准。
- **只移不删**：涉及真实数据的步骤一律可逆，断言计数守恒（30 → 30）。
- **分层不混算**：B 层未执行**不等于失败**，也不计为通过；以「挂账」显式记录，避免「本机全绿 = 生产已验证」的错觉。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/test_inbox_endpoint.py` | 45（A29/B5/C10 及扩展） | 集成（进程内真实 HTTP 服务） | 端点协议、限流、客户端分批重试 |
| `upstream/tests/test_inbox_pull.py` | 23 | 集成 | 拉取端 `inbox_pull.py` |
| `tools/verify_workbuddy_skills.py` | — | 静态 | skill 安装与策略哨兵 |

## 二、详细测试案例

### 功能 1：inbox-api-only-write（收目录仅服务用户可写）

对应 spec：`canonical/specs/code/inbox-api-only-write.yaml` → REQ-001 / REQ-002 / REQ-003

#### 案例 1.1 — ubuntu 身份直写被拒 + 属主断言

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-001 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-api-only-write → SC-001 |
| **优先级** | P0 |
| **预置条件** | 服务以 fstdd-inbox 运行；收目录已 chown 且 chmod 755 |
| **输入** | `touch /home/ubuntu/fstdd-inbox/.perm-probe`；`namei -l /home/ubuntu/fstdd-inbox` |
| **预期结果** | touch 退出码 ≠ 0 且输出含 Permission denied；目录无 .perm-probe；属主 fstdd-inbox:fstdd-inbox；权限 0755 |
| **当前状态** | ❌ 待人工（K 部署后执行，证据回填） |

#### 案例 1.2 — API 正向落盘与计数递增

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-002 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-api-only-write → SC-002 |
| **优先级** | P0 |
| **预置条件** | 服务 active；持有效 token（从远端 env 读取，不回显） |
| **输入** | POST 1 条 `EXP-LOCKDOWN-PROBE-1`；前后各取一次 `/health` |
| **预期结果** | 200 且 accepted=1；文件属主 fstdd-inbox；received +1；探测文件事后清理 |
| **当前状态** | ❌ 待人工（K 部署后执行，证据回填） |

#### 案例 1.3 — 只读巡检链路不断

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-003 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-api-only-write → SC-003 |
| **优先级** | P0 |
| **预置条件** | 收目录已收权 |
| **输入** | `tail -3 /home/ubuntu/fstdd-inbox/server.log`；`curl /health` |
| **预期结果** | 两者均成功；server.log 对 other 可读（0644 或更宽） |
| **当前状态** | ❌ 待人工（K 部署后执行，证据回填） |

#### 案例 1.4 — scp 直写被拒（本次要根治的行为）

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-004 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-api-only-write → SC-004 |
| **优先级** | P0 |
| **预置条件** | 以 ubuntu 身份 ssh/scp 可用 |
| **输入** | `scp probe.md fstdd-hub:/home/ubuntu/fstdd-inbox/` |
| **预期结果** | 传输失败（Permission denied）；目录内无该文件；server.log 无 accepted 记录 |
| **当前状态** | ❌ 待人工（K 部署后执行，证据回填） |

#### 案例 1.5 — 试运行文件入 quarantine 且计数守恒

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-005 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-api-only-write → SC-005 |
| **优先级** | P0 |
| **预置条件** | 收目录根下存在 30 个 `EXP-2026091[567]-*.md`（16:41 实测） |
| **输入** | 移动至 `quarantine/` 并双向计数 |
| **预期结果** | 根下残留 0；quarantine 内 30；总量守恒不丢 |
| **已知副作用** | `/health` received 将同步下降约 30（glob 不递归），属预期 —— 须写入节点通知，避免节点误判「数据被删」 |
| **当前状态** | ❌ 待人工（K 部署后执行，证据回填） |

#### 案例 1.6 — 无凭证非白名单来源返回 401

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-006 |
| **层** | **A（仓库侧，本机 pytest）** |
| **对应 Spec** | inbox-api-only-write → SC-006 |
| **优先级** | P0 |
| **预置条件** | 进程内起服务，env 设 `FSTDD_INBOX_TOKEN`，白名单为空 |
| **输入** | POST 不带任何凭证头 |
| **预期结果** | 401 且 body 含 unauthorized；日志出现 `[inbox] 401` |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED；仓库 `inbox_server.py` 当前无鉴权代码） |

#### 案例 1.7 — 白名单 IP 灰度放行

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-007 |
| **层** | **A（仓库侧，本机 pytest）** |
| **对应 Spec** | inbox-api-only-write → SC-007 |
| **优先级** | P1 |
| **预置条件** | env 设 token 且 `FSTDD_INBOX_ALLOW_IPS` 含 `127.0.0.1/32` |
| **输入** | 无凭证 POST（源 IP 127.0.0.1） |
| **预期结果** | 200 accepted=1；日志含 legacy-ip 放行 |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

#### 案例 1.8 — 未配置 token 时保持开放

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-008 |
| **层** | **A（仓库侧，本机 pytest）** |
| **对应 Spec** | inbox-api-only-write → SC-008 |
| **优先级** | P1 |
| **预置条件** | env 无 `FSTDD_INBOX_TOKEN`（需重载模块读 env） |
| **输入** | 任意 POST |
| **预期结果** | 200；启动日志含 `auth: OFF` |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED） |

#### 案例 1.9 — /health 免鉴权且计数口径正确

| 字段 | 内容 |
|------|------|
| **ID** | TC-IAOW-009 |
| **层** | **A（仓库侧，本机 pytest）** |
| **对应 Spec** | inbox-api-only-write → SC-009 |
| **优先级** | P0 |
| **预置条件** | 任意鉴权配置 |
| **输入** | `GET /health` |
| **预期结果** | 200；received == 收目录根下 `*.md` 数（不含 quarantine） |
| **当前状态** | ❌ 部分缺（既有 A1/A1b 覆盖无鉴权场景；须补 token 配置下的免鉴权变体） |

### 功能 2：inbox-deploy（幂等加固部署）

对应 spec：`canonical/specs/code/inbox-deploy.yaml` → REQ-101 / REQ-102

#### 案例 2.1 — 连续两次部署端状态一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-001 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-deploy → SC-101 |
| **优先级** | P0 |
| **预置条件** | 远端 env 存在 |
| **输入** | 连续执行 `deploy_inbox_server.sh` 两次 |
| **预期结果** | 均 exit 0；`is-active=active`；属主与权限两次一致 |
| **当前状态** | ❌ 待人工（K 端上执行） |

#### 案例 2.2 — env 缺失即中止

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-002 |
| **层** | **A(静态)** ＋ B(端上) |
| **对应 Spec** | inbox-deploy → SC-102 |
| **优先级** | P0 |
| **预置条件** | A：本地仓库脚本；B：临时重命名远端 `inbox.env`（测完恢复） |
| **输入** | A：读脚本全文断言含存在性校验与非 0 退出；B：执行部署脚本 |
| **预期结果** | A：脚本含 env 存在性校验 + 缺失即 `exit 1`/中止文案；B：非 0 退出、打印处置指导、不改动既有单元、不重启服务 |
| **当前状态** | ❌ A 缺（BUILD 先 RED）；B 待人工 |

#### 案例 2.3 — 单元关键行静态守护

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-003 |
| **层** | **A（仓库侧，本机 pytest）** |
| **对应 Spec** | inbox-deploy → SC-103 |
| **优先级** | P1 |
| **预置条件** | 本地仓库 |
| **输入** | pytest 读取 `tools/deploy_inbox_server.sh` 全文断言 |
| **预期结果** | 含 `User=fstdd-inbox`、`EnvironmentFile=`、`UMask=0022`；不含 `pkill -f inbox_server` |
| **当前状态** | ❌ 测试缺（BUILD 阶段先 RED；当前脚本 `User=ubuntu` 且无 `EnvironmentFile`，断言必红） |

#### 案例 2.4 — 后置校验逐条输出且失败即非 0

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-004 |
| **层** | **A(静态)** ＋ B(端上) |
| **对应 Spec** | inbox-deploy → SC-104 |
| **优先级** | P0 |
| **预置条件** | A：本地仓库脚本；B：部署完成 |
| **输入** | A：断言脚本含 verify 段（PASS/FAIL 逐条）与负向断言（ubuntu 写探测）；B：执行 verify 段 |
| **预期结果** | A：脚本含四组断言 + 负向写入探测 + 任一 FAIL 非 0 退出；B：逐条 PASS/FAIL 输出 |
| **当前状态** | ❌ A 缺（BUILD 先 RED）；B 待人工 |

#### 案例 2.5 — 源码-部署 md5 一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-005 |
| **层** | B（外部挂账） |
| **对应 Spec** | inbox-deploy → SC-105 |
| **优先级** | P0 |
| **预置条件** | 部署完成（部署脚本会把仓库版上传覆盖，故两端应自然一致） |
| **输入** | 两端 `md5sum` 比对 |
| **预期结果** | 一致（漂移清零）；证据含两处 md5 原文 |
| **当前状态** | ❌ 待人工（K 端上执行） |

#### 案例 2.6 — 既有套件无回归 + 新增用例通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-IBDP-006 |
| **层** | **A（仓库侧，本机 pytest）** |
| **对应 Spec** | inbox-deploy → SC-106 |
| **优先级** | P0 |
| **预置条件** | `upstream` 目录 |
| **输入** | `C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe -m pytest upstream/tests -q` |
| **预期结果** | 既有 45+23 用例全绿；新增鉴权组与脚本守护组通过 |
| **当前状态** | ❌ 新增组缺（BUILD 阶段先 RED） |

## 三、测试执行矩阵

| 功能模块 | A：本地 pytest | B：E2E（ssh 端状态） | 状态 |
|----------|----------------|----------------------|------|
| 鉴权三态分支 | TC-IAOW-006/007/008 | — | 🔴（A 待 BUILD） |
| /health 免鉴权与计数 | TC-IAOW-009 | TC-IAOW-002/005 | 🔴（A 待 BUILD） |
| 收目录权限与属主 | — | TC-IAOW-001/003 | ⬜ B 挂账 |
| scp 直写拒绝 | — | TC-IAOW-004 | ⬜ B 挂账 |
| quarantine 迁移 | — | TC-IAOW-005 | ⬜ B 挂账 |
| 部署脚本静态守护 | TC-IBDP-002(静态)/003/004(静态) | — | 🔴（A 待 BUILD） |
| 部署幂等与端状态 | — | TC-IBDP-001/002(端上)/004(端上)/005 | ⬜ B 挂账 |
| 回归保护 | TC-IBDP-006 | — | 🔴（A 待 BUILD） |

> 图例：🔴 = A 层待 BUILD 实现；⬜ = B 层外部挂账（不阻塞收口）。

## 四、回归风险矩阵

| 风险区域 | 本次改动 | 已有回归保护 | 风险等级 |
|----------|----------|--------------|----------|
| `inbox_server.py` 补入鉴权分支 | 仓库版由「无鉴权」升级为「鉴权三态」 | test_inbox_endpoint.py A/B/C 45 用例 | 🟡 |
| `/health` received 口径 | quarantine 后计数下降约 30 | TC-IAOW-009 显式断言口径 | 🔴（口径变化，须公告节点） |
| 服务重启可用性 | User / EnvironmentFile / UMask 变更 | TC-IBDP-001 + TC-IAOW-002 正向落盘 | 🟡 |
| 巡检只读链路 | 目录权限收紧 | TC-IAOW-003 | 🟡 |
| 节点回传中断 | scp 通道被拒（本次目的） | 无保护 —— 须 K 发通知告知改走 API | 🔴（预期行为，需沟通） |
| 部署脚本重写 | 单元模板与用户/权限逻辑 | TC-IBDP-002/003/004 静态守护 | 🟡 |

## 五、建议补充顺序

1. **第一优先（A 层，BUILD 阶段必做，本机 RED→GREEN）**：
   - TC-IAOW-006、TC-IAOW-007、TC-IAOW-008、TC-IAOW-009（鉴权与 `/health`）
   - TC-IBDP-002(静态)、TC-IBDP-003、TC-IBDP-004(静态)（脚本守护）
   - TC-IBDP-006（全量回归）
2. **第二优先（B 层，外部挂账清单，随交付转 K 人工执行）**：
   - TC-IAOW-001、002、003、004、005；
   - TC-IBDP-001、002(端上)、004(端上)、005。
   - 交付说明须列「外部运维项挂账」表，含逐条人工命令与回执要求。
3. **第三优先（P1，灰度分支覆盖）**：TC-IAOW-007、TC-IAOW-008 —— 不阻塞部署；BUILD 阶段已随切片 1 实现并通过（见 `.fstdd.yaml` slices_completed '1'：tc_coverage 4/4）。

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 收目录属主 ubuntu:ubuntu 模式 0775 | 2026-09-18T08:53:00+00:00 | deployed-2b58b70b | `ssh fstdd-hub "ls -ld /home/ubuntu/fstdd-inbox"` |
| 服务单元 User=ubuntu 且含 EnvironmentFile | 2026-09-18T08:53:00+00:00 | deployed-2b58b70b | `ssh fstdd-hub "systemctl cat fstdd-inbox"` |
| 仓库与部署版 md5 不等（742827d9 vs 2b58b70b） | 2026-09-18T08:53:00+00:00 | deployed-2b58b70b | 两端 `md5sum` |
| 17 文件直写而 received 未同步（88→97） | 2026-09-18T08:41:00+00:00 | deployed-2b58b70b | 16:41 小时简报基线 diff + `/health` |
| 试运行文件计 30 个 | 2026-09-18T08:55:00+00:00 | deployed-2b58b70b | `ssh fstdd-hub "ls /home/ubuntu/fstdd-inbox/EXP-2026091[567]-*.md ｜ wc -l"` |
| 仓库 `inbox_server.py` 无鉴权代码（grep 零命中） | 2026-10-04T02:44:00+00:00 | 155e4c6 | 本机 `grep -iE 'FSTDD_INBOX_TOKEN|X-FSTDD-Token|Bearer|unauthorized' tools/inbox_server.py` |

- `observed_at` 是信息采集时刻，不是文档生成时刻。
- **B 层新增证据（md5、权限、负向断言输出、quarantine 计数）在 K 回执后回填本节**，回填前 B 层状态恒为「挂账（未验证）」。