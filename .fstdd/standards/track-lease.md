# FSTDD 单机双档租约规程 —— 同一 change 单一档主责

> 适用版本：FSTDD 3.3.x+
> 最后更新：2026-10-04
> 来源：2026-10-04 事故 —— `2026-09-19-notices-authenticity-gate` 的 Gate 3 记录被并发档（F-B 心跳档）
> 与主责档（F-A 交互档）**双方写入**，`confirmed_evidence` / 切片 `verified_at` 被覆盖，同一 change 出现双写。
> 关联规格：`distributed-task-coordination`（跨机租约，SC-003/006/007）—— 本规程是其**同机单仓**补充，
> 语义同源（单一 owner、租约 token、TTL、过期接管、无静默覆盖、可审计），作用域降为「一台机器内的并发档」。

## 一、问题（实测）

同一台机器上可同时运行多个助手档（如 A 交互档 / B 心跳档），两档共享同一工作树。
现有 `distributed-task-coordination` 的租约只在**跨机控制面（8788）**生效，**同机两档无仲裁**：
两档都能直接改 `.fstdd/changes/<change>/` 下的记录与 Gate 字段，先写者被执行、后写者覆盖，
且**双方都以为自己主责**。

⇒ 事故形态：同一次 Gate 3 出现两份 `confirmed_evidence`；切片 `verified_at` 从 19:30 被改成 06:30；
一方改动被另一方连同提交（`137dec5`）。**根因不是权限，而是缺「谁主责」的仲裁。**

## 二、术语

| 术语 | 含义 |
|---|---|
| 档（track） | 同一 `node_id` 下并发运行的一个助手实例，以 `F-A` / `F-B` / … 标识 |
| change 租约 | 某档对**一个 change** 的独占写权，落为 `.fstdd/changes/<change>/.lease.yaml` |
| 主责档 | 当前持有有效租约的档，独占该 change 的记录与 Gate 写权 |
| 旁路档 | 未持租的档，对该 change **只读** |
| TTL | 租约有效期；主责档须在 TTL 内续约，超期即失效 |

## 三、租约文件（约定）

**位置**：`.fstdd/changes/<change>/.lease.yaml`（本机本地文件，gitignored，不入库）。
**并发面**：两档共享文件系统，故以「原子创建」为唯一裁决点。

```yaml
change_id: 2026-09-19-notices-authenticity-gate
lease_id: 7b1c…            # 唯一租约 token（uuid4）；接管/续约以此比对
owner_track: F-A           # F-A / F-B / …
owner_node_id: DESKTOP-TBJSBQ5
acquired_at: 2026-10-04T21:40:00+08:00
heartbeat_at: 2026-10-04T21:45:00+08:00
expires_at: 2026-10-04T22:15:00+08:00   # = heartbeat_at + TTL（默认 30min）
intent: deliver            # understand / spec / build / deliver
takeover:
  from_lease_id: null      # 非接管则为 null
  reason: null
```

**事件审计**：`.fstdd/changes/<change>/lease-events.yaml`（本机本地，追加式，只增不改）。
每条至少记 `at / track / lease_id / event(acquire|renew|release|takeover|conflict)`；冲突与接管**必须**入库。

## 四、规则（强制）

| # | 规则 | 说明 |
|---|------|------|
| **R1 单一主责** | 任一时刻同一 change 至多一个**有效**租约 | 对应 `SC-003`「同一任务同时只有一个有效 owner」的同机版 |
| **R2 原子领取** | 创建租约必须 fail-if-exists（`O_CREAT\|O_EXCL` 或等价）；并发领取只有一方成功 | 对应 `SC-007`「并发 claim 单方胜出」的同机版；失败方按旁路档处理 |
| **R3 TTL 与心跳** | 默认 TTL 30min；主责档须在到期前续约（刷新 `heartbeat_at`/`expires_at`） | 超 TTL 未续约 = 租约失效，不得再以主责自居 |
| **R4 过期接管** | 租约失效后他档可接管；接管必须写 `takeover.from_lease_id` + `reason` + 追加 `takeover` 事件 | 对应 `SC-006`；**不得删除历史**，旧 token 回传一律拒绝 |
| **R5 收口即释放** | Gate 3 通过并归档（DELIVER 完成）后，主责档**必须显式释放** | 释放后他档方可领取；不得留悬空租约 |
| **R6 只读旁路** | 旁路档对租约覆盖的 change **只读**：可读、可评论、**不得写** `.fstdd.yaml` / Gate / phase / `tasks.md` / `test-report.md` / canonical | 需要写 → 先领取租约，或交 D 哥裁定 |
| **R7 Gate 不变量** | 租约**不改变** Gate 硬防线（`AGENTS.md` 约束 1、`SC-012`） | 代签**仅限持租档** + D 哥明确授权；evidence 必须写**真实授权来源**，不得伪造 |
| **R8 冲突可见** | 任何 `acquire/renew/release/takeover/conflict` 均写 `lease-events.yaml`，供 D 哥审计「谁在何时持租」 | 静默覆盖 = 违规 |
| **R9 无机制期降级** | 在自动化仲裁未落地前，本条以「约定」先行：**动 change 记录前，先声明主责并广播档标识** | 声明未获回应 ≠ 可双写；发现对方持租即让位 |

## 五、生命周期

```
领取(acquire)──► 主责(write)──┬─续约(renew)──┐
                              │◄─────────────┘   （循环，直到收口）
                              └─释放(release，收口后)
        │ 超 TTL 未续约
        └──► 失效 ──► 他档接管(takeover，记审计) ──► 主责
```

## 六、与既有机制的边界

- **跨机**：仍走 `distributed-task-coordination` 的 8788 控制面（节点注册、心跳、租约、幂等键），本规程不替代。
- **同机**：本规程覆盖；两档共享工作树时，`.lease.yaml` 为唯一裁决点。
- **Gate**：无论同机或跨机，Gate 只认 D 哥明确确认；租约**只分配写权，不授予 Gate 权**。