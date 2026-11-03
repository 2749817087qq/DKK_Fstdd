# v3.6.1 测试方案与详细案例（share-scp-tar-packing）

> 版本：v3.6.1（增量）
> 创建日期：2026-10-31
> 对应 Phase 2 Spec：`canonical/specs/code/share-transport-performance.yaml`

## 一、测试策略

### 1.1 测试金字塔

| 层 | 占比 | 内容 |
|---|---|---|
| 单元 | ~85% | `_pack_tar` 打包/扁平化；数量校验；回退分支；安全校验 |
| 集成 | ~15% | `_scp_dir` 端到端（subprocess 全 monkeypatch，不触网） |
| E2E | 0% | 真实 ssh/scp 不进单测（网络与服务器状态不可控） |

### 1.2 测试原则

- **不触网**：所有 `subprocess.run` 用 monkeypatch 替身，断言的是 **argv 形态**而非真实传输。
- **正例 + 反例成对**：数量校验必须测「相符 ⇒ PASS」和「不符 ⇒ FAIL」两侧。
- **安全校验单独测**：`-` 开头文件名 / `..` remote_dir 必须证明「拒绝了**且没启动子进程**」。
- **性能目标只测本地打包**：端到端 <30s 需真实链路，不进单测（记为 SC-03 的人工验证项）。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---|---|---|---|
| `tests/test_share_ssh_transport.py` | 15 | 集成（mock） | 三档降级、审计记录、脱敏、配置读取 |
| `tests/test_share_hardening.py` | — | 集成 | 出站收口、残余判据 |
| `tests/test_share_publish_sanitize.py` | — | 单元 | 脱敏规则 |
| `tests/test_share_disabled_switch.py` | — | 单元 | 开关语义 |

**本轮新增**：`tests/test_share_scp_tar.py`

## 二、详细测试案例

### 功能 1：tar 打包

对应 `share-transport-performance` → REQ-SCP-001

#### 案例 1.1 — 打包往返一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-001 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-001 |
| **优先级** | P0 |
| **预置条件** | tmp 目录含 5 个 .md 文件（内容各不同） |
| **输入** | `_pack_tar(out_dir)` → 解开返回的 tar.gz |
| **预期结果** | 返回非 None；解包后 5 个成员；每个成员内容与源一致 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 子目录文件被扁平化

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-002 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-002 |
| **优先级** | P0 |
| **预置条件** | out_dir 下有 `a/b/EXP-001.md` |
| **输入** | `_pack_tar(out_dir)` → 读成员名 |
| **预期结果** | 成员名为 `EXP-001.md`（不含 `/`） |
| **当前状态** | ❌ 测试缺 |

### 功能 2：单次传输

对应 `share-transport-performance` → REQ-SCP-002

#### 案例 2.1 — scp 只有 1 个源文件

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-003 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-003 |
| **优先级** | P0 |
| **预置条件** | out_dir 含 20 个文件；monkeypatch 捕获 subprocess 调用 |
| **输入** | `_scp_dir(out_dir, ...)` |
| **预期结果** | 捕获到的 scp argv 里，源文件参数恰好 1 个且以 `.tar.gz` 结尾 |
| **当前状态** | ❌ 测试缺 |

### 功能 3：数量校验

对应 `share-transport-performance` → REQ-SCP-003

#### 案例 3.1 — 远端数量不符 ⇒ 失败

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-004 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-004 |
| **优先级** | P0 |
| **预置条件** | 本地 20 个文件；mock 远端计数返回 15 |
| **输入** | `_scp_dir(out_dir, ...)` |
| **预期结果** | 返回 `(False, reason)`；reason 含 `20` 与 `15`；批次目录被清理（有 rm 调用） |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — 远端数量相符 ⇒ 成功

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-005 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-005 |
| **优先级** | P0 |
| **预置条件** | 本地 20 个；mock 远端也返回 20 |
| **输入** | `_scp_dir(out_dir, ...)` |
| **预期结果** | 返回 `(True, "")` |
| **当前状态** | ❌ 测试缺 |

### 功能 4：回退

对应 `share-transport-performance` → REQ-SCP-004

#### 案例 4.1 — 打包异常 ⇒ 回退逐文件

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-006 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-006 |
| **优先级** | P0 |
| **预置条件** | monkeypatch `_pack_tar` 抛 `OSError` |
| **输入** | `_scp_dir(out_dir, ...)`（远端 mock 成功） |
| **预期结果** | 返回 `(True, reason)`；reason 含「回退」；有逐文件 scp 调用 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — 远端无 tar ⇒ 回退逐文件

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-007 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-007 |
| **优先级** | P1 |
| **预置条件** | mock `command -v tar` 返回非 0 |
| **输入** | `_scp_dir(out_dir, ...)` |
| **预期结果** | 回退逐文件；reason 说明远端无 tar；无解包调用 |
| **当前状态** | ❌ 测试缺 |

### 功能 5：安全校验

对应 `share-transport-performance` → REQ-SCP-005

#### 案例 5.1 — `-` 开头文件名被拒

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-008 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-008 |
| **优先级** | P0 |
| **预置条件** | out_dir 里有 `-oProxyCommand=x.md` |
| **输入** | `_scp_dir(out_dir, ...)` |
| **预期结果** | 返回 `(False, reason)`；reason 含「以 `-` 开头」；**无任何 subprocess 调用** |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.2 — `..` remote_dir 被拒

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-009 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-009 |
| **优先级** | P0 |
| **预置条件** | `remote_dir='../etc'` |
| **输入** | `_scp_dir(out_dir, remote_dir='../etc')` |
| **预期结果** | 返回 `(False, reason)`；**无任何 subprocess 调用** |
| **当前状态** | ❌ 测试缺 |

### 功能 6：布局不变

对应 `share-transport-performance` → REQ-SCP-006

#### 案例 6.1 — 批次目录命名与 tar 清理

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-010 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-010 |
| **优先级** | P0 |
| **预置条件** | `FSTDD_NODE_ID=local`；subprocess 全 mock |
| **输入** | `_scp_dir(out_dir, ...)` |
| **预期结果** | 捕获的 mkdir 命令里批次目录匹配 `local-experiences-\d{8}-\d{6}`；有删 tar 包的调用 |
| **当前状态** | ❌ 测试缺 |

### 功能 7：性能

对应 `share-transport-performance` → REQ-SCP-007

#### 案例 7.1 — 112 个文件打包 < 2s

| 字段 | 内容 |
|------|------|
| **ID** | TC-SCP-011 |
| **对应 Spec** | share-transport-performance → Scenario: SC-SCP-011 |
| **优先级** | P1 |
| **预置条件** | tmp 目录造 112 个 1-5KB 文件 |
| **输入** | `_pack_tar(out_dir)`，计时 |
| **预期结果** | 耗时 < 2.0 秒 |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| tar 打包（TC-SCP-001..002） | ✅ 2 | — | — | ❌ 待实现 |
| 单次传输（TC-SCP-003） | — | ✅ 1 | — | ❌ 待实现 |
| 数量校验（TC-SCP-004..005） | ✅ 2 | — | — | ❌ 待实现 |
| 回退（TC-SCP-006..007） | ✅ 2 | — | — | ❌ 待实现 |
| 安全校验（TC-SCP-008..009） | ✅ 2 | — | — | ❌ 待实现 |
| 布局不变（TC-SCP-010） | — | ✅ 1 | — | ❌ 待实现 |
| 性能（TC-SCP-011） | ✅ 1 | — | — | ❌ 待实现 |

**合计：11 TC**（P0 9 / P1 2）

## 四、回归风险矩阵

| 改动区域 | 风险 | 影响面 | 回归手段 |
|---|---|---|---|
| `_scp_dir` 第 4 步替换 | **高** —— 传输主路径 | 所有 DELIVER 自动回传 | 既有 `test_share_ssh_transport.py` 15 用例全跑；tar 失败必回退 |
| `_scp_dir` 第 5 步增强（数量比对） | 中 —— 从「只打印」变「判失败」 | 可能让原本「假成功」的路径变红 | 正反成对测试；数量相符路径必须 PASS |
| `_pack_tar` 新增 | 低 —— 纯新增函数 | 无 | 单元测试覆盖 |
| 临时目录清理 | 中 —— 泄漏会占磁盘 | 长期运行 | `finally` + `ignore_errors=True`（沿用既有范式） |

## 五、建议补充顺序

| 批次 | 内容 | 理由 |
|---|---|---|
| **P0-A** | TC-SCP-001..002（打包） | 基础能力，后面全靠它 |
| **P0-B** | TC-SCP-003（单次传输） | 核心目标：1 次协商 |
| **P0-C** | TC-SCP-004..005（数量校验） | 防「解包不完整当成功」 |
| **P0-D** | TC-SCP-006..009（回退 + 安全） | 防优化引入新故障 / 安全退化 |
| **P0-E** | TC-SCP-010（布局） | 消费方兼容 |
| **P1** | TC-SCP-011（性能） | 目标验证 |

## 六、证据记录

| 项 | 值 |
|---|---|
| 观测时刻 | 2026-10-31T12:40:02+00:00 |
| 观测基线 | `f7a30b9d14a57161e7b2e03369e67a2fa4f2d4b7` |
| 关键实测 | 112 文件逐文件 scp 耗时 5m19s；三次超时留 13/25/37 个半成品批次而审计全记 failure |
| 环境事实 | 远端 GNU tar 1.35（`/usr/bin/tar`）；本机 Python 3.13.12 |
| 执行环境 | managed venv；`PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` |
