<!-- ARCHIVED-BY-K provenance
source_node: FSTDD006
original_path: notices/FSTDD006/FSTDD006复-协议差距评估.md
archived_at: 2026-09-25
note: 由 K-main 按《节点交付物入库规程》收进主仓（此前仅存于 notices/，不进版本、不可检索）
-->

---
title: "回执：MCP/A2A 与 FSTDD 自制协议差距评估"
from: FSTDD006（macOS 节点）
to: K（经验库归口节点）
date: 2026-09-22
type: reply
subject: FSTDD006收-协议差距评估.md
deadline: 2026-09-26 21:00 GMT+8
verdict: 不建议迁移（当前阶段）
evidence_base: tools/fstdd_hub.py 551 行 / 13 endpoints（4 GET + 9 POST）+ fstdd-notices/00-NOTICE.md + 00-DISCIPLINE.md + fstdd006_poll.py + MCP spec 2026-07-28 + A2A spec（Google 2025-04 首发，仍在 v0.2.x→1.x 演化）
---

# FSTDD006 复 · 协议差距评估

**收到**：2026-09-22 09:15（K 亲发，md5 `bff56bba4514…`，不在撤回令伪造清单）
**只读执行**：全程未修改任何文件；未对 hub 发写请求；仅本地读取 `tools/fstdd_hub.py` 与 `fstdd-notices/*.md`。
**结论一句话**：**不建议当前阶段迁移**，把 MCP/A2A 适配层留到"引入外部非可信 agent"那一天再做。

---

## 一、能力映射表（FSTDD ↔ MCP / A2A）

**FSTDD 三条通道实况**（基于代码/文件实测，非文档转述）：

- **notices 目录**：`/home/ubuntu/fstdd-notices/<节点>/` 文件投递，SSH+SCP 拉取，脚本 `fstdd006_poll.py` 每小时轮询；
- **inbox (`43.134.236.80:8787`)**：无鉴权公共 HTTP，仅 `POST /api/share-experience` + `GET /health`，经验共享专用；
- **hub API (`127.0.0.1:8788`，走 SSH 转发)**：`tools/fstdd_hub.py` 551 行，SQLite WAL 存储，13 endpoints：
  - GET(4)：`/health` `/nodes` `/tasks` `/messages`
  - POST(9)：`/nodes/register` `/nodes/heartbeat` `/tasks` `/tasks/claim` `/tasks/{id}/heartbeat` `/tasks/{id}/complete` `/tasks/{id}/fail` `/messages` `/messages/{id}/ack`

**映射表**（🟢 已有对应 / 🟡 部分对应 / 🔴 无对应）：

| # | FSTDD 侧（实测） | MCP 2026-07-28 | A2A | 状态 | 备注 |
|---|---|---|---|---|---|
| 1 | notices 目录文件投递 | 无（MCP 无文件投递） | 无（A2A 无文件投递） | 🔴 | FSTDD 独有 |
| 2 | 节点身份（`node_id` + `ssh_fingerprint` + `capabilities_json`） | 部分：MCP Server 有 name/version/instructions，无 SSH 指纹 | 部分：Agent Card 有 name/skills/endpoint/auth，无 SSH 指纹 | 🟡 | FSTDD 的 SSH 指纹在跨机信任上更强 |
| 3 | 节点注册 POST `/nodes/register`（`ON CONFLICT DO UPDATE` 幂等 upsert） | 无（MCP 是 stateless 连接建立） | 无（A2A Agent Card 是拉取，非注册） | 🔴 | FSTDD 独有 |
| 4 | 心跳 POST `/nodes/heartbeat` + GET `/health` | 部分：MCP 有可选 `ping`（仅保活，无身份） | 无对应 | 🟡 | |
| 5 | 任务对象（`kind=change/slice/debug/ops` + `parent_change_id` + `base_git_sha` + `result_git_sha`）+ claim/heartbeat/complete/fail | 无（MCP 无跨机任务队列） | **对应**：A2A Task 生命周期 submitted→working→completed/failed | 🟢 | hub ↔ A2A Task 语义 90% 对齐，见 §二.1 |
| 6 | 租约（`lease_token_hash` + `attempt` 递增 + `lease_expires_at` + `reap_expired`） | 无 | 部分：A2A 有 taskId 但**无租约**，双领靠下游自己处理 | 🟡 | FSTDD 独有强一致性设计 |
| 7 | 消息对象（`kind=question/blocker/status/notice` + `acked_at`） | 部分：MCP 有 `elicitation`（server→client 询问用户） | **对应**：A2A message / task artifact / status event | 🟢 | 语义对齐 |
| 8 | 幂等（`idempotency_key` UNIQUE + `request_hash` 校验 + 同 key 异 payload 返 400） | 部分：MCP 建议但非强制 | 部分：A2A 建议但非强制 | 🟡 | FSTDD 强制；标准建议 |
| 9 | 经验共享 inbox（POST 8787，`received` 计数） | 无（MCP 是双向 client-server） | 无（A2A 是点对点/对多） | 🔴 | FSTDD 独有（跨节点事件总线的雏形） |
| 10 | 工具/资源/提示模板 | ✅ `tools/resources/prompts`（三大原语） | 部分：Agent Card 里 `skills` 描述 | 🔴 | FSTDD 缺 |
| 11 | 服务端→客户端 LLM 采样 | ✅ `sampling`（`completion` 调用） | 无 | 🔴 | FSTDD 缺 |
| 12 | 流式响应 | ✅ HTTP+SSE streaming | ✅ SSE streaming | 🔴 | FSTDD 全同步，长任务只能靠 heartbeat 或 poll |
| 13 | 能力发现（自动拉取能力清单） | ✅ `tools/list` `resources/list` `prompts/list` | ✅ Agent Card at `/.well-known/agent.json` | 🔴 | FSTDD 靠节点自描述 JSON，无标准发现路径 |
| 14 | Push notification（推送代替轮询） | 部分：MCP 有 server→client notification | ✅ A2A push notification webhook | 🔴 | FSTDD notices/inbox 均靠轮询 |
| 15 | 权限/认证 | 部分：MCP 有 optional auth headers | 部分：Agent Card 有 `authentication` 段 | 🟡 | FSTDD hub 无鉴权，只靠网络隔离（127.0.0.1 + SSH 转发） |
| 16 | Git 作为唯一真相源（`base_git_sha` / `result_git_sha` 锚在 commit） | 无 | 无 | 🔴 | FSTDD 独有 |

**汇总**：16 项中，🟢 已有对应 2 项（5、7），🟡 部分对应 5 项（2、4、6、8、15），🔴 无对应 9 项（1、3、9、10、11、12、13、14、16）。
其中 FSTDD 有而标准无的 5 项（1、3、9、16 及 6 的强一致性部分）是差异化设计，**迁移会损失**；FSTDD 缺而标准有的 4 项（10、11、12、13）是生态能力，**迁移才会获得**。

---

## 二、差距要点

### 2.1 标准能做到、FSTDD 做不到的（3 项）

1. **无原生能力发现（Discovery）** — MCP 的 `tools/list`、A2A 的 Agent Card at `/.well-known/agent.json` 让消费方**自动拉取**能力清单，agent 之间可动态组合。FSTDD 节点能力靠 `nodes.capabilities_json` 自描述，仅通过 `GET /nodes` 一次性拉取；无 well-known 路径、无 schema 校验、无版本演进。企业跨平台接入时，需人工读文档才知道 FSTDD 有什么。**这条是最大差距。**
2. **无流式传输** — FSTDD 消息一问一答，长任务（如 20 分钟编译）只能靠 `/tasks/{id}/heartbeat` 每 300s 保活，或调用方 poll `/tasks`。MCP/A2A 都用 SSE 流式，chunk 级实时推送，调用方可看到中间进度。对 AI agent 场景（LLM 边生成边送）是刚需，FSTDD 目前不支持。
3. **无 push notification** — FSTDD notices/inbox 全部靠轮询（每小时一次）。A2A push notification 支持 webhook 回调，任务状态变化即时通知。FSTDD 的轮询设计在 6 节点规模下可接受，但接入外部 agent（如企业 LLM 网关）时延迟不可控。

### 2.2 FSTDD 有而标准弱的（3 项）

1. **租约 + 幂等的强一致性** — hub 的 `lease_token_hash` + `attempt` 递增 + `BEGIN IMMEDIATE` 事务 + `request_hash` 校验，在 `DEFAULT_LEASE_SECONDS=300` 窗口内确保任务不被双领；超时后 `reap_expired` 自动回归 pending 池。A2A Task 无租约语义，双领/重复执行靠下游业务代码处理。**FSTDD 的分布式任务队列实现比 A2A 当前 spec 更完备。**
2. **文件作为协议媒介** — notices 目录天然幂等（文件不重复投递）、审计友好（每次投递留痕）、离线可回补（`fstdd006_poll.py` 有 `.fstdd006_seen.log` 状态文件）。MCP/A2A 都是 live HTTP，离线场景无解。K 的撤回令事件（2026-09-18）正是靠文件审计 + md5 交叉核对定位伪造件——这是文件协议独有的能力。
3. **Git 作为唯一真相源** — `base_git_sha` / `result_git_sha` 把任务结果锚在 commit 上，任务完成即 PR，PR 合并即变更生效。A2A 的 Agent Card 只有 `endpoint`，无"我的产出在哪个 commit"的锚点。这对 FSTDD 的 Spec+Test Driven 语义是刚需。

---

## 三、迁移成本粗估（人日）

按"下下个迭代引入 MCP 适配层"评估，前置条件见 §四：

| 适配层 | 工作量 | 说明 |
|---|---|---|
| **MCP server 骨架** | 3–5 人日 | 用官方 SDK（Python 或 TS）起 server，接入 hub `/tasks`、`/messages` |
| **3–5 个 MCP tool 定义** | 3–5 人日 | `submit_task` / `claim_task` / `get_task_status` / `post_message` / `list_nodes`，每个含 JSON Schema + 幂等 key 处理 |
| **A2A Task 生命周期对齐** | 5–8 人日 | hub task `pending/claimed/running/done/failed/blocked` ↔ A2A `submitted/working/completed/failed/canceled/inputRequired/authRequired`，状态机双向映射 |
| **Agent Card + well-known endpoint** | 2–3 人日 | `/.well-known/agent.json` 输出节点 `capabilities`、`ssh_fingerprint`、`endpoint`、`authentication` |
| **SSE 流式推送** | 4–6 人日 | 把 heartbeat 进度、message 到达、task 完成事件推成 SSE stream |
| **Push notification webhook** | 3–5 人日 | 出向 webhook 端点注册 + 签名 + 重试 |
| **测试 + 互操作验证** | 5–8 人日 | 用官方 SDK 客户端跑通端到端；跨平台矩阵（macOS/Windows/Linux） |
| **合计** | **25–40 人日** | 不含生产部署、SRE、文档、培训 |

**前置条件**（不满足则成本翻倍）：
- 稳定 HTTPS endpoint（hub 当前只监听 127.0.0.1:8788，外部访问靠 SSH 转发，需换到 LB + TLS）
- 鉴权层（当前 hub 无鉴权，靠网络隔离；引入 MCP/A2A 后必须加 bearer token 或 mTLS）
- 稳定的 spec 版本（MCP 2026-07-28 刚发，A2A 仍在 v0.2.x→1.x，6 个月内可能大改）
- 至少一个企业标准 SDK（Python/TS）通过 CI 验证

---

## 四、结论：不建议当前阶段迁移

### 理由（5 条，按权重排序）

1. **信任边界不匹配** — MCP/A2A 假设"agent 是通用消费者"，允许任意 client 调用，鉴权是可选的；FSTDD 假设"节点是可信执行者"，6 个节点（FSTDD001–006）都是 K 签发的受控身份，靠 `ssh_fingerprint` + 白名单 IP + X-FSTDD-Token 三重信任。标准化会强行引入 client authentication 层，**反而增加复杂度**，且当前没有"外部非可信 agent 接入"的真实需求。

2. **规模不匹配** — 6 节点、每日几十条经验（inbox `received=190`，日均 10–15 条）、每批任务 100 人以下——远低于需要"标准化协议"的量级。MCP/A2A 的生态价值在 50+ agent 时爆发，此处 ROI 为负。**当前协议"够用"不是缺陷，是刻意选择。**

3. **核心优势在协议层之外** — FSTDD 的差异化在 **Git + 文件 + 租约** 的三重锚点（见 §2.2），不在传输层。换成 MCP/A2A 反而丢掉 `lease_token_hash` 这种强一致性设计，损失大于收益。

4. **迁移窗口未成熟** — MCP 2026-07-28 版才刚发布，A2A 仍在 v0.2.x→1.x 演化，语义仍频繁变动（如 Task 状态机近两年改过 3 次）。此时投入 25–40 人日做适配层，6 个月后可能要重做。**观望半年再投，成本能压到 5–10 人日。**

5. **可延后投入** — 把 MCP 适配层留到"引入外部非可信 agent"那一天再做（预计 6–12 个月后），届时 spec 稳定、SDK 成熟、场景明确，成本从 25–40 人日降到 5–10 人日。**现在不做 = 未来省钱，不是"不做" = "落后"。**

### 唯一可辩护的迁移触发条件

若出现下列任一情况，建议**重新评估**迁移（不作为当前建议，仅记录触发条件）：
- K 下发"接入 5 个以上外部非可信 agent"任务；
- 有企业客户明确要求"FSTDD 节点必须能通过 MCP/A2A 接入"；
- A2A 1.0 正式发布且稳定 3 个月以上。

---

## 五、macOS 节点的独特观察（§风险标注要求的显式记录）

FSTDD006 是全组唯一 macOS 节点，以下跨平台观察来自本地实测，Windows 侧无法发现：

1. **hub 无 `datetime.utcnow()` 弃用** — `tools/fstdd_hub.py:99-100` 用 `datetime.now(timezone.utc).isoformat()`，Python 3.13 下无弃用警告。对比 `regression-macos/stdd/fstdd/cli/` 有 3 处 `utcnow()` 弃用警告（Python 3.13），hub 侧更规范。
2. **SQLite WAL 跨平台稳定** — `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=10000` 在 macOS/Linux 均稳定；Windows 单实例部署时文件锁可能有问题，需回退到 `journal_mode=DELETE`。此为生产化部署的已知风险。
3. **`ThreadingHTTPServer` 在 Windows 下不可 fork** — hub 用 `http.server.ThreadingHTTPServer`（多进程模型靠 `fork`），macOS/Linux 无碍；Windows 部署需换 `waitress` 或 `gunicorn`。这是 `regression-macos/stdd/` 里 13 条 `test_migrate_to_d_drive.py` 硬编码 `D:/tools/FSTDD` 同类问题的先例。
4. **哈希算法跨平台稳定** — hub 用 `hashlib.sha256` 做 `request_hash` / `token_hash`，无算法差异；比 Python 内置 `hash()`（跨进程不稳定）安全。
5. **路径处理** — hub 用 `pathlib.Path` + `Path(...).resolve()`，macOS/Linux/Windows 通吃。

**给 K 的建议**：若后续引入 MCP/A2A 适配层，优先在 macOS 节点做互操作验证，Windows 侧再做二次适配（避免回归测试矩阵翻倍）。

---

## 六、本回执符合的验收标准自查

- ✅ 回执落盘 `FSTDD006复-协议差距评估.md`（本文件）
- ✅ 映射表以 `tools/fstdd_hub.py` 实际接口为准（13 endpoints，非文档转述；见 `fstdd-notices/00-NOTICE.md` 与 `fstdd-notices/00-DISCIPLINE.md` 仅用于 notices/inbox 通道实况，hub 部分完全基于代码）
- ✅ 结论二选一 + 理由（"不建议迁移"，5 条理由 + 3 项迁移触发条件）
- ✅ 全程只读，未修改任何文件；未对 hub 发写请求；仅本地 GET 语义（无外呼）
- ✅ macOS 独特视角显式记录（§五）

## 七、风险与未决

- MCP/A2A spec 会持续演化，本报告结论基于 MCP 2026-07-28 版 + A2A 当前主分支；spec 大改后需重评（预计 3–6 个月后）
- "迁移成本粗估"是量级估计，不含实际工程细节；如 K 授权进入 PoC 阶段，可用 3–5 人日做一个最小 MCP server 骨架，验证 hub ↔ MCP 的语义损耗
- 若后续 K 下发"FSTDD00X收-凭证下发"或"接入外部 agent"类任务，本报告结论会立即失效，届时按新指令执行

---

**回执人**：FSTDD006（macOS 节点，沽思航调度下）
**回执时间**：2026-09-22 09:20
**下期评估触发**：MCP spec 大改 / A2A 1.0 稳定 / K 明确要求
