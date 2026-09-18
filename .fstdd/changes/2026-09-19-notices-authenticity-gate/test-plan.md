# 2026-09-19-notices-authenticity-gate 测试方案与详细案例

> 版本：v1（Gate 2 候选）
> 创建日期：2026-09-19
> 对应 Phase 2 Spec：
>   - `canonical/specs/code/notice-authenticity-verification.yaml`（REQ-001..005 / SC-001..015）
>   - `canonical/specs/code/notice-execution-pipeline.yaml`（REQ-006 / SC-016..018）
>   - `canonical/specs/agent/2026-09-19-notices-authenticity-gate.yaml`（CP-001..006）
> 偏离记录：`design-adjustments.md`（AD-1..AD-5，含 spec 按 capability 拆分 AD-2）
> 说明：本方案的 Scenario→TC 映射以 Canonical YAML 为准（P12：`fstdd extract-proposal` /
> `canon generate` 在 V3.0.5 存在系统性字段丢失，不得采信 CLI 提取结果）。

## 一、测试策略

### 1.1 测试金字塔

本变更仅新增 1 个 Python 模块 + 1 个测试文件，落在 `D:\FSTDD003\tools\` 域，无服务进程、
无网络依赖，因此**不建 E2E 层**，全部落在单元 + 集成两层：

| 层次 | TC 数 | 占比 | 侧重点 |
|------|-------|------|--------|
| 单元测试 | 9 | 43% | `classify_notice()` / 清单解析器 / 凭证形状正则 / 隔离记录结构 —— 纯函数，无文件系统副作用 |
| 集成测试 | 12 | 57% | 真实目录移动、CLI 子进程退出码、`git check-ignore`、真实格式 fixtures、回传链路 diff |
| E2E | 0 | 0% | 不适用：闸门以子进程方式被自动化 `06ec2c4f` 调用，子进程契约由集成层覆盖 |

选择理由：本变更的风险不在函数内部逻辑（纯 stdlib、无 I/O 依赖），而在**外部契约**——
退出码、文件位置、git 历史、以及「不把既有回传链路弄坏」。这些必须用真实文件系统与
真实 `git` 子进程断言，单元测试无法覆盖。

### 1.2 测试原则

- **RED→GREEN 严格留痕**：`tools/test_verify_notices.py` 必须先于
  `tools/verify_notices.py` 存在并跑出全红（`ModuleNotFoundError: verify_notices`），
  不得先写实现再补测试。
- **宁可隔离、不静默丢弃**：凭证嗅探的误判方向固定为「多隔离而非漏隔离」，
  但误隔离上界被 TC-NAV-008 固定为 0（对已知格式通知 100% 不误隔离）。
- **凭证绝不进入任何输出面**：断言同时覆盖 stdout、stderr、隔离记录文件、git 提交对象四个面，
  用已知字面值 `fs9k2m7x4q1w8e5r` 做正向搜索。
- **契约用退出码固定**：0 / 2 / 3 三态写入断言，含「2 与 3 并存时 3 优先」这一非显然规则。
- **回归断言优先于功能断言**：TC-NEP-001/002/003 不验证新功能，只验证「没弄坏旧东西」——
  这是本变更最容易翻车的地方（09-18 已发生一次未授权配置变更）。
- **不建清单文件，不污染正式渠道**：所有清单与 fixtures 置于 `tmp_path`，
  不新建 `00-SIGNATURES.md`（Q2 待 K 裁定），不在真实通知目录上跑破坏性用例。
- **禁止静默失败**：不得在断言里用 `except: pass` / `except: continue` 吞异常
  （直接对应 `EXP-20260918-CODE-1` 与 `EXP-20260918-ARCHIVE-1` 两次同源教训）。

### 1.3 已有测试资产

**关键事实：`tools/` 域当前没有任何测试文件**（2026-09-19 实测：5 个 `.py` 脚本，0 个测试）。
因此不存在既有回归保护，这是本变更必须自带回归断言的直接原因。

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `<无>` | 0 | — | `tools/` 域零测试资产 |
| `tools/test_verify_notices.py`（本变更新增） | 21 | 单元 + 集成 | REQ-001..006 全部 18 个 Scenario + 3 个补充边界用例 |

已实测确认的测试前置条件：

| 前置条件 | 实测状态 |
|----------|----------|
| pytest | `pytest 9.1.1`（隔离 venv `C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default`） |
| `tools/fstdd003_daily_share.py` 基线 | 4623 B，`git diff HEAD -- tools/` 为空 → SC-016 可断言 |
| `.fstdd/_fstdd003_token.txt` 基线 | 65 B，mtime `2026-09-18 17:53` → SC-018 可断言 |
| `.gitignore` 当前内容 | 6 行，**不含** `tools/_quarantine/` → SC-011 需先追加再断言 |

---

## 二、详细测试案例

TC-ID 规则：`TC-<CAPABILITY>-<NNN>`
- **NAV** = `notice-authenticity-verification`（REQ-001..005）
- **NEP** = `notice-execution-pipeline`（REQ-006）

### 功能 1：通知真伪校验闸门（REQ-001..005 / TC-NAV-001..018）

#### 案例 1.1 — 清单命中判定为 verified

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-001 |
| **对应 Spec** | REQ-001 → Scenario SC-001 |
| **优先级** | P0 |
| **预置条件** | `tmp_path` 内造 1 行清单条目，文件名与 `FSTDD003收-示例.md` 一致，摘要为该文件内容 md5 前 12 位 |
| **输入** | `classify_notice(<path>/FSTDD003收-示例.md)` |
| **预期结果** | 返回 `status == "verified"`，且结果中不含任何 `reason` 字段；含 `filename` 与 `md5_prefix`（12 位小写十六进制）；含 `emitted_by`（清单记录的发出者） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 本地内容被篡改判为 md5_mismatch

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-002 |
| **对应 Spec** | REQ-001 → Scenario SC-002 |
| **优先级** | P0 |
| **预置条件** | 清单含该文件条目，但本地文件内容已改写导致 md5 前 12 位不符 |
| **输入** | `classify_notice(<path>/FSTDD003收-示例.md)` |
| **预期结果** | 返回 `status == "unverified"` 且 `reason == "md5_mismatch"`；同时含 `expected_md5_prefix`（清单值）与 `actual_md5_prefix`（本地值）；**不含文件正文任何片段** |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.3 — 不在清单内判为 not_in_manifest

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-003 |
| **对应 Spec** | REQ-001 → Scenario SC-003 |
| **优先级** | P0 |
| **预置条件** | 清单存在但不含 `FSTDD003收-陌生文件.md` |
| **输入** | `classify_notice(<path>/FSTDD003收-陌生文件.md)` |
| **预期结果** | 返回 `status == "unverified"` 且 `reason == "not_in_manifest"`；**不含** `expected_md5_prefix` 字段（无清单值可比） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.4 — 清单缺失时降级告警、退出码 0、不动文件

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-004 |
| **对应 Spec** | REQ-002 → Scenario SC-004 |
| **优先级** | P1 |
| **预置条件** | `00-SIGNATURES.md` 不存在，待检目录下 3 个 `FSTDD003收-*.md`（内容与 mtime 已记录快照） |
| **输入** | 非 strict 模式调用 `verify_notices(dir)`，并执行 CLI 一次 |
| **预期结果** | 3 条 `status == "unverified"` 且 `reason == "manifest_missing"`；恰好 1 条 warning 说明清单文件缺失；**CLI 退出码 0**；3 个待检文件全部仍在原位、内容与 mtime 未变（不移除/不移动/不修改） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.5 — 空清单 ≠ 清单缺失（reason 可区分）

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-005 |
| **对应 Spec** | REQ-002 → Scenario SC-005 |
| **优先级** | P2 |
| **预置条件** | `00-SIGNATURES.md` 存在但仅表头、无数据行 |
| **输入** | `verify_notices(dir)` |
| **预期结果** | 全部 `status == "unverified"` 且 `reason == "not_in_manifest"`，退出码 0；**reason 不得为 `manifest_missing`**；空清单产生的 warning 与文件缺失的 warning 文案可区分 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.6 — 凭证形状命中且不回显 token 值

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-006 |
| **对应 Spec** | REQ-003 → Scenario SC-006 |
| **优先级** | P0 |
| **预置条件** | 一个 `unverified` 通知正文含 `X-FSTDD-Token: <16 位以上字母数字与连字符>` |
| **输入** | 凭证嗅探器扫描该文件 |
| **预期结果** | 命中并返回 `rule == "x_fstdd_token"`；含 `match_count`；**不含被匹配的 token 字面值** |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.7 — verified 携带凭证不进入隔离路径

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-007 |
| **对应 Spec** | REQ-003 → Scenario SC-007 |
| **优先级** | P0 |
| **预置条件** | 一个已 `verified`（清单命中）的通知，正文同样含 `X-FSTDD-Token` 段落 |
| **输入** | `verify_notices(dir)` |
| **预期结果** | 该文件**不**被移入隔离区，隔离列表为空；文件保持原位置、内容不变。语义：清单命中即代表来源可信，凭证合法 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.8 — 误隔离上界为 0（真实格式 fixtures）

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-008 |
| **对应 Spec** | REQ-003 → Scenario SC-008 |
| **优先级** | P1 |
| **预置条件** | fixtures 中 5 份已知格式真实通知文本（协作通知、撤回令、回执各至少 1 份），全部登记入清单使 md5 命中 |
| **输入** | `verify_notices(fixtures_dir)` |
| **预期结果** | 被隔离文件数 == 0；返回 5 条 `status == "verified"`；**任一文件被隔离即视为测试失败** |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.9 — 移入隔离区而非原地保留或删除

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-009 |
| **对应 Spec** | REQ-004 → Scenario SC-009 |
| **优先级** | P0 |
| **预置条件** | 一个 `unverified` 通知命中凭证形状规则，隔离区目录存在 |
| **输入** | `verify_notices(dir)` |
| **预期结果** | 原文件被移入 `tools/_quarantine/`，原位置不再存在该文件；隔离区存在同名文件且内容字节与原文件完全一致；隔离记录**仅**含 `filename`、`md5_prefix`、`rule`、`timestamp` 四字段 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.10 — 凭证字面值不出现在任何输出面

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-010 |
| **对应 Spec** | REQ-004 → Scenario SC-010 |
| **优先级** | P0 |
| **预置条件** | 一个含已知字面值 token（`fs9k2m7x4q1w8e5r`）的 `unverified` 通知 |
| **输入** | 运行 CLI 并捕获 stdout、stderr，同时读取隔离记录文件；再对 git 提交对象做字面搜索 |
| **预期结果** | 该 token 字面值**不出现**在 stdout、stderr 与隔离记录中；隔离记录中出现 `rule` 名但不出现 token 值；git 仓库任何提交对象不含该字面值 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.11 — 隔离区被 .gitignore 覆盖

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-011 |
| **对应 Spec** | REQ-004 → Scenario SC-011 |
| **优先级** | P1 |
| **预置条件** | `.gitignore` 已追加 `tools/_quarantine/` |
| **输入** | `git check-ignore -v tools/_quarantine/x` |
| **预期结果** | 退出码 0 且输出非空，命中行指向 `.gitignore` 的 `tools/_quarantine/` 条目 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.12 — 非 strict 下 unverified 退出码 0

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-012 |
| **对应 Spec** | REQ-005 → Scenario SC-012 |
| **优先级** | P0 |
| **预置条件** | 待检目录存在 `unverified` 文件，未启用 `--strict` |
| **输入** | 执行 CLI |
| **预期结果** | 以退出码 0 结束（不阻断后续执行链路） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.13 — strict 下 unverified 退出码 3

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-013 |
| **对应 Spec** | REQ-005 → Scenario SC-013 |
| **优先级** | P0 |
| **预置条件** | 待检目录存在 `unverified` 文件，启用 `--strict` |
| **输入** | 执行 CLI |
| **预期结果** | 以退出码 3 结束（存在未验证通知应阻断） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.14 — 隔离退出码 2，且 3 优先于 2

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-014 |
| **对应 Spec** | REQ-005 → Scenario SC-014 |
| **优先级** | P1 |
| **预置条件** | 至少一个文件被移入隔离区（另设 2 与 3 并存的组合场景） |
| **输入** | 执行 CLI（两次：普通 / `--strict`） |
| **预期结果** | 发生隔离时退出码 2；当 2 与 3 同时成立时**优先返回 3**（strict 阻断优先于隔离提示） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.15 — --json 机器可读契约

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-015 |
| **对应 Spec** | REQ-005 → Scenario SC-015 |
| **优先级** | P1 |
| **预置条件** | 启用 `--json` |
| **输入** | 执行 CLI |
| **预期结果** | 输出单个可被 `json.loads` 解析的对象；顶层键**恰好**为 `results`、`quarantined`、`warnings`、`exit_code`；`results` 每项含 `status`、`filename`、`md5_prefix`，`unverified` 时含 `reason` |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.16 —（补充）畸形清单条目不抛异常

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-016 |
| **对应 Spec** | 补充用例（无对应 Scenario；支撑 REQ-002 的降级鲁棒性） |
| **优先级** | P1 |
| **预置条件** | 清单含 1 行 md5 前缀长度非 12 位 / 含非法十六进制字符 / 带多余空白与注释的条目 |
| **输入** | `verify_notices(dir)` |
| **预期结果** | 不抛异常；非法行被跳过并计入 warnings；对应文件判为 `not_in_manifest`；退出码 0 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.17 —（补充）待检目录不存在时优雅降级

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-017 |
| **对应 Spec** | 补充用例（无对应 Scenario；支撑 REQ-002 的降级鲁棒性） |
| **优先级** | P1 |
| **预置条件** | 传入的待检目录不存在或不可读 |
| **输入** | 执行 CLI |
| **预期结果** | 不抛未捕获异常、不产生堆栈到 stderr；warnings 记录该事实；退出码 0 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.18 —（补充）清单重复登记同一文件名

| 字段 | 内容 |
|------|------|
| **ID** | TC-NAV-018 |
| **对应 Spec** | 补充用例（无对应 Scenario；覆盖 K 侧重发/撤回后重发场景） |
| **优先级** | P2 |
| **预置条件** | 清单中同一文件名登记两次，摘要不同（对应撤回后重新下发同一文件名） |
| **输入** | `classify_notice(<path>/FSTDD003收-重发.md)` |
| **预期结果** | 取首次条目做比对，warnings 记录重复登记；命中时判 `verified`，不得因存在第二行而误报 `md5_mismatch` |
| **当前状态** | ❌ 测试缺 |

### 功能 2：执行链路零回归（REQ-006 / TC-NEP-001..003）

#### 案例 2.1 — 回传脚本零改动

| 字段 | 内容 |
|------|------|
| **ID** | TC-NEP-001 |
| **对应 Spec** | REQ-006 → Scenario SC-016 |
| **优先级** | P0 |
| **预置条件** | `tools/fstdd003_daily_share.py` 基线 4623 B，`git diff HEAD -- tools/` 当前为空 |
| **输入** | 本变更完成后 diff 该文件；并做两处字面搜索 |
| **预期结果** | diff 为空（内容零改动）；文件不含 `X-FSTDD-Token` 字样；文件不含读取 `_fstdd003_token.txt` 的代码路径 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — 回传计数保持 P17 去重语义

| 字段 | 内容 |
|------|------|
| **ID** | TC-NEP-002 |
| **对应 Spec** | REQ-006 → Scenario SC-017 |
| **优先级** | P1 |
| **预置条件** | `.fstdd/_fstdd003_share_log.json` 记录 submitted 计数与已回传经验 id 集合（副本置于 `tmp_path`，不改真实文件） |
| **输入** | 连续两轮运行校验器与既有回传流程 |
| **预期结果** | `submitted` 计数只增不减且无重复经验 id；第二轮在无新增经验时 `submitted` 保持不变；**闸门自身不写入** `_fstdd003_share_log.json` |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — 凭证现场文件内容 + mtime 均不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-NEP-003 |
| **对应 Spec** | REQ-006 → Scenario SC-018 |
| **优先级** | P1 |
| **预置条件** | `.fstdd/_fstdd003_token.txt` 存在（65 B，mtime `2026-09-18 17:53`），内容与 mtime 已记录（等待 K/S 指定销毁方式，见 Q1） |
| **输入** | 完整运行校验器 CLI 一次（含隔离路径） |
| **预期结果** | 该文件内容与 mtime 均保持不变；`verify_notices` 模块**不含**对该文件路径的任何字符串引用 |
| **当前状态** | ❌ 测试缺 |

---

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 清单比对（REQ-001） | TC-NAV-001..003、016、017、018（6） | — | — | 🔴 全缺 |
| 清单缺失/空清单降级（REQ-002） | TC-NAV-005 | TC-NAV-004 | — | 🔴 全缺 |
| 凭证嗅探 + 误隔离上界（REQ-003） | TC-NAV-006、007 | TC-NAV-008 | — | 🔴 全缺 |
| 隔离区 + 不回显凭证（REQ-004） | — | TC-NAV-009、010、011 | — | 🔴 全缺 |
| CLI 退出码 + JSON 契约（REQ-005） | — | TC-NAV-012..015 | — | 🔴 全缺 |
| 执行链路零回归（REQ-006） | — | TC-NEP-001、002、003 | — | 🔴 全缺 |

补充执行要点：
- 全部 21 个 TC 收敛在单一文件 `tools/test_verify_notices.py`，与
  `tools/verify_notices.py` 同目录，便于 `pytest tools/test_verify_notices.py` 单跑。
- 所有清单与 fixtures 一律建在 pytest `tmp_path`；不得在 `.fstdd/_notices/FSTDD003/`
  真实目录上执行会移动文件的用例（TC-NAV-009/010）。
- TC-NAV-010 的 git 面断言须在本变更提交**之后**再执行一次（对已提交历史做字面搜索），
  该断言安排在 CP-006 收尾阶段复核。

---

## 四、回归风险矩阵

| 风险区域 | V1 改动 | 已有回归保护 | 风险等级 |
|----------|---------|-------------|---------|
| 回传链路 `tools/fstdd003_daily_share.py` | 不改（09-18 曾据伪造通知被未授权改过一次） | **无**（tools 域 0 测试）→ 新增 TC-NEP-001 diff 断言 | 🔴 高 |
| 凭证现场 `.fstdd/_fstdd003_token.txt` | 不改（保留现场等 K 裁定，见 Q1） | **无** → 新增 TC-NEP-003 内容 + mtime 断言 + 源码字符串反查 | 🔴 高 |
| 凭证外泄到 stdout / 隔离记录 / git 历史 | 新增隔离路径（新写入面） | **无** → 新增 TC-NAV-010 四面字面搜索 | 🔴 高 |
| `.gitignore` 覆盖缺口 | 追加 `tools/_quarantine/` | **无** → 新增 TC-NAV-011 `git check-ignore` 断言 | 🟠 中 |
| 协作通知执行链路（自动化 `06ec2c4f`） | 不修改自动化 prompt 与调度 | **无** → TC-NAV-012/014 固定「非 strict 退出码 0」防止闸门误阻断 | 🟠 中 |
| P17 去重语义 `.fstdd/_fstdd003_share_log.json` | 不改 | **无** → 新增 TC-NEP-002 两轮计数断言 | 🟡 低 |
| 既有 `tools/` 其他 4 个脚本 | 不改 | **无** → `git diff HEAD -- tools/` 整体为空断言（CP-005 附带） | 🟡 低 |
| 上游 `~/.workbuddy-ai/FSTDD/upstream/` | 不改 | FSTDD003 仓库范围外 → `git status` 确认 + CP-006 复核 | 🟡 低 |

风险等级说明：本矩阵中所有「已有回归保护」列均为**无**——`tools/` 域零测试资产是
本变更的核心脆弱点。因此回归断言（TC-NEP-001/002/003 + TC-NAV-010/011）的优先级不低于
任何功能断言。

---

## 五、建议补充顺序

21 个 TC 全部标为「❌ 测试缺」，按 P0 → P1 → P2 顺序补充：

1. **第一优先（P0，10 个，RED 阶段必须全红、GREEN 阶段必须全绿）**
   TC-NAV-001、002、003、006、007、009、010、012、013、TC-NEP-001
   —— 覆盖：三条判定路径、凭证嗅探、verified 豁免、隔离、**不回显凭证**、
   两个阻断相关退出码、回传脚本零改动。缺任一即视为闸门不可用。

2. **第二优先（P1，9 个，同一次 GREEN 内完成）**
   TC-NAV-004、008、011、014、015、016、017、TC-NEP-002、003
   —— 覆盖：清单缺失降级、误隔离上界 0、`.gitignore` 覆盖、退出码 2 与优先级规则、
   JSON 契约、两个鲁棒性边界（畸形清单行 / 目录不存在）、P17 计数、凭证现场不变。

3. **第三优先（P2，2 个，可随主流程一并交付）**
   TC-NAV-005（空清单 ≠ 清单缺失）、TC-NAV-018（清单重复登记）
   —— 两个非显然的语义区分点；若实现期发现清单格式约定变化，这两条先改断言口径。

TC 与 agent_spec 检查点对齐：
- **CP-001（RED）**：全部 21 个 TC 先落 `tools/test_verify_notices.py` 并跑出全红
- **CP-002**：TC-NAV-001..005（清单判定 + 降级）
- **CP-003**：TC-NAV-006..011（嗅探 + 隔离 + `.gitignore`）
- **CP-004**：TC-NAV-012..015（CLI 退出码 + JSON）
- **CP-005**：TC-NEP-001..003（回归保护）
- **CP-006**：TC-NAV-016..018（补充边界）+ git 面复核（TC-NAV-010 第三面）
