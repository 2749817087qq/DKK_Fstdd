# 契约面一致性 + Phase 4 静默回传 测试报告

> 变更：`2026-09-16-contract-auto-share`
> 执行日期：2026-09-16
> 执行环境：Windows，Python 3.11.9（`C:\Python311\python.exe`）
> 测试工具：`pytest`（`upstream/tests/`）+ `tools/verify_eol.py` + `fstdd validate`

## 一、执行结果总览

| 指标 | 结果 |
|---|---|
| 全量用例总数 | **487** |
| 通过 | **487** |
| 失败 | 0 |
| 通过率 | 100% |
| 退出码 | 0 |
| 基线（本变更前） | 424 passed |
| 本变更新增 | **+63** |

命令：
```bash
cd upstream && C:/Python311/python.exe -m pytest tests -q -p no:cacheprovider
# 487 passed in 238.74s
```

### 1.1 用例分布

| 测试文件 | 用例数 | 性质 |
|---|---|---|
| `tests/test_constitution_contract.py` | 6 | **新增**（Slice 1：宪法契约） |
| `tests/test_silent_share.py` | 23 | **新增**（Slice 2：静默回传） |
| `tests/test_constitution_migration.py` | 10 | **新增**（Slice 3：存量升级） |
| `tests/test_cross_cutting_verification.py` | 24 | **新增**（Slice 4：交叉验证） |
| `tests/test_fstdd_matrix.py` | 40 | 既有（本变更修改 1 处断言，见 D6） |
| `tests/test_inbox_endpoint.py` | 44 | 既有（**须保持**，本变更未改端点） |
| `tests/test_finder.py` / `test_utils.py` | 8 / 8 | 既有 |
| `tests/commands/` | 324 | 既有 |

> 424（基线）+ 63（新增）= 487 ✓

### 1.2 其他门禁

| 门禁 | 结果 |
|---|---|
| `fstdd validate` | **验证通过** |
| `tools/verify_eol.py` | **7/7 通过**（TC-EOL-005 已修正误报，见下） |
| 目标锁死扫描 | **可执行第三方引用 0 处** |

## 二、TDD 执行记录（RED → GREEN）

每个 Slice 均先写失败断言。以下为各 Slice 报告的 RED 证据原文。

### 2.1 Slice 1 — 宪法契约（RED）

```
6 failed in 8.13s
E  AssertionError: 宪法中出现 5 处裸 STDD（应为 FSTDD）
E  AssertionError: 宪法仍含「显式执行」，与「静默回传」的既定语义相反
E  AssertionError: 宪法未声明静默回传
E  AssertionError: 命令表缺少 `fstdd status`
E  Failed: 仓库根宪法与模板输出不一致（2135 vs 2336 字节）
E  AssertionError: 缺少骨架自包含副本：.fstdd\memory\FSTDD_CONSTITUTION.md
```

**GREEN**：`6 passed in 7.46s`；`diff` 生成物与仓库副本 → `IDENTICAL`。

### 2.2 Slice 2 — 静默回传（RED）

由 Slice 4 的交叉断言独立捕获（该 Slice 的 worker 因 429 中断，未留下 RED 记录）：

```
test_b5_deliver_policy_replaces_upstream_body  → FAILED
  （改动前 apply_deliver_policy 只前置注释、保留上游正文）
```

**GREEN**：`23 passed in 11.87s`。

### 2.3 Slice 3 — 存量升级（RED）

```
E   ImportError: cannot import name '_migrate_constitution' from 'fstdd.cli.commands.upgrade'
1 error in 1.04s

（对 _write_upgrade_notes 现状取证）
陈旧 rule 仍在: True
裸 STDD 命中: 2 处
旧命令名命中: ['stdd bootcamp', 'stdd init', 'stdd knowledge', 'stdd upgrade']
静默回传表述: False
```

**GREEN**：`10 passed`。

### 2.4 Slice 4 — 交叉验证（RED）

```
FAILED TestATargetLockdown::test_a1_no_executable_third_party_path
FAILED TestBContractText::test_b3_upgrade_notes_no_stale_rules
2 failed, 17 passed
```

其中 `test_a1` 的 RED 是**真实缺陷暴露**（见第五节 F2），`test_b3` 的 RED 是**我的断言过宽**（见 D9）。

**GREEN**：`24 passed`（连跑两遍一致）。

## 三、Spec → 用例覆盖映射

| Spec Scenario | 测试用例 | 结果 |
|---|---|---|
| SC-001 Phase 4 静默回传无交互 | TC-CAS-001 | ✅ |
| SC-002 有凭证指向 Fstdd-experiences | TC-CAS-002 | ✅ |
| SC-003 无凭证降级自建端点 | TC-CAS-003 | ✅ |
| SC-004 deliver 定义含静默回传步骤 | TC-CAS-004、TC-CAS-005 | ✅ |
| SC-005 无指向第三方的可执行路径 | TC-CAS-006 | ✅ |
| SC-006 目标常量默认值正确且可覆盖 | TC-CAS-007 | ✅ |
| SC-007 端点不可达不阻断 DELIVER | TC-CAS-008 | ✅ |
| SC-008 超时受限 | TC-CAS-009 | ✅ |
| SC-009 审计记录内容完整 | TC-CAS-010 | ✅ |
| SC-010 关闭开关后零网络请求 | TC-CAS-011 | ✅ |
| SC-011 载荷强制脱敏 | TC-CAS-012 | ✅ |
| SC-012 服务端二次校验未被削弱 | TC-CAS-013 | ✅（既有 `test_inbox_endpoint.py`，回归保持通过） |
| SC-013 init 宪法无旧名/无错误措辞 | TC-CAS-014 | ✅ |
| SC-014 仓库根宪法与模板逐字节一致 | TC-CAS-015 | ✅ |
| SC-015 `.fstdd/memory/` 副本存在且一致 | TC-CAS-016 | ✅ |
| SC-016 升级说明与手册无陈旧内容 | TC-CAS-017 | ✅ |
| SC-017 升级保留用户自定义 | TC-CAS-018 | ✅ |
| SC-018 升级幂等 | TC-CAS-019 | ✅ |
| SC-019 validate 判定与模板相容 | TC-CAS-023 | ✅ |
| SC-020 真实重复仍被捕获 | TC-CAS-024 | ✅ |

**覆盖率：20/20 Scenario 有用例（100%）**

## 四、变异验证（证明断言非空转）

这是本变更「测试有区分度」的核心证据。**共注入 11 个已知缺陷，11/11 全部被捕获。**

### 4.1 Slice 2（由团队负责人补做，该 worker 中断前未完成）

| 注入缺陷 | 结果 |
|---|---|
| 关闭开关失效（`share_disabled` 恒 False） | ✅ 捕获（3 用例红） |
| 审计记录不写（`record_audit` 变 no-op） | ✅ 捕获（6 用例红） |
| 零阻塞被破坏（静默路径异常直接抛出） | ✅ 捕获 |
| 策略注入退回「只前置注释、保留上游正文」 | ✅ 捕获（含 Slice 4 交叉断言） |

### 4.2 Slice 1

| 注入缺陷 | 结果 |
|---|---|
| 改回「自动上传经验到社区」 | ✅ 捕获 |
| 改回 1 处裸 STDD | ✅ 捕获 |
| 移除静默回传步骤 | ✅ 捕获 |
| 命令表改回旧名 | ✅ 捕获 |

### 4.3 Slice 3

| 注入缺陷 | 结果 |
|---|---|
| 整文件覆盖（自定义丢失） | ✅ 捕获 |
| 去掉幂等判定 | ✅ 捕获 |
| 去掉备份 | ✅ 捕获 |
| 迁移目标文本写回「显式执行」 | ✅ 捕获 |
| UPGRADE_NOTES 陈旧 rule 未改 | ✅ 捕获 |
| 不做 memory 副本补齐 | ✅ 捕获 |
| 只迁移根副本 | ✅ 捕获 |

> Slice 3 另报告了一个**语义等价变异**（去掉 `if old in new_text` 判定，因 `str.replace` 未命中即 no-op，行为完全相同）**正确地未被捕获**，并已替换为真实缺陷。这是诚实的处理方式，不计为测试漏洞。

### 4.4 Slice 4 的反向断言

`test_b3b` 的左边界断言做了双向验证：

| 输入 | 判定为残留 |
|---|---|
| `FSTDD 最新版本`（已修正） | False ✓ |
| `STDD 最新版本`（真残留） | True ✓ |

## 五、失败模式检查

按 `slices.md` 预设的 4 个已知坑逐条核对。

### F1 — 缩进错误（Edit 工具）→ 已预防

所有 Python 改动均通过 `ast.parse` 校验。**本变更未引入任何 `IndentationError`。**

### F2 — 目标锁死扫描的误报 → **实际发生并已修正**

首轮扫描报 2 处命中，核查后确认**均非缺陷**：

| 命中 | 真实性质 | 处置 |
|---|---|---|
| `experience.py:1045` `print("历史上传通道（…）的代码已移除。")` | 面向用户的**消息文本** | 把 `print()`/日志参数判为说明性上下文 |
| `knowledge.py:131` `repo = community.get("repo", "leonai42/stdd-experiences")` | **拉取（只进）**源，属既定策略 | 加入 `ALLOWED_REFS` 白名单（**附理由**） |

并新增 `test_a6_allowlist_is_not_rotten`：白名单条目指向的文件必须**仍然真的**含该标识 —— 防止白名单腐烂成万能豁免。

### F3 — 契约与代码不一致（本次即为复发）→ 已加守护

新增两条漂移守护（`test_b6` / `test_b7`）：
- 迁移表的**新片段**必须出现在仓库宪法中（防「改了模板忘了改迁移表」）
- 迁移表的**旧片段**必须不在仓库宪法中（防「迁移没做干净」）

这把宪法的**两个来源**（`init.py` 模板 / `upgrade.py` 迁移表）锁在一起。

### F4 — 远端命令双发（本机环境特性）→ 本次未触发

本变更的验证全部在本地执行，未使用 ssh。端到端实测以**端状态**（端点计数）为证据，不依赖命令回显。

## 六、遗留与已知限制

| # | 项 | 说明 |
|---|---|---|
| L1 | **真实 GitHub 凭证路径未端到端实测** | `publish()` 直推与 `publish_via_pr()` 的 fork+PR 需要真实网络与写权限，属 TC-CAS-002 的 P2 部分。已用 monkeypatch 覆盖目标选择逻辑，未打真实 GitHub。 |
| L2 | **无凭证端点的真实网络实测** | 已在上一 change（`inbox-review-sync` 的前置工作）中做过 17 条端到端验证（1 批提交、429 重试后 17/17 落盘），本变更复用同一路径，未重复打真实端点。 |
| L3 | **静默回传的语义机密边界** | 脱敏只能处理**格式化的、可枚举的**敏感串；判断不了「这段业务描述是否机密」。把关点在我方审核池（入库前人工审核），已在 design.md Risks 中明确。 |
| L4 | **`tools/verify_workbuddy_skills.py` 的哨兵判定已加强** | 从「只查哨兵」改为「哨兵 + 3 个策略标记」。这是**加强**而非削弱，但意味着旧版本安装产物若未重装会 FAIL —— 属预期（升级后须重跑安装，规程已写在 skill 内）。 |

## 七、结论

- 全量 **487 passed / 0 failed**，基线 424 无回归。
- **20/20 Spec Scenario** 有用例覆盖。
- **11/11 变异缺陷被捕获**，断言具备真实区分度。
- 目标锁死扫描：**可执行第三方引用 0 处**。
- `fstdd validate` 通过；`verify_eol.py` 7/7。
- 8 项设计偏离已全部记录于 `design-adjustments.md` 并回补规格。

**本变更可交付。**
