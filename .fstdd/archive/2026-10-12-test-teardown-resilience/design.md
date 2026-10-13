# 测试收尾韧性 —— 让 fixture teardown 不被沙箱删除守卫的 SystemExit 打断 - 技术设计

**change**: `2026-10-12-test-teardown-resilience` ｜ **模式**: standard（复杂度 6）｜ **前置**: Gate 1 ✅（2026-10-12T21:55+08:00）

## Context

### 当前系统状态

门禁数**不可判**：同一 HEAD、同一命令，不同执行者拿到不同失败数（实测主理人 5 failed/1 error vs 门神 4 failed/17 errors）。
连跑 2 次全量（守卫未触发）均 `204 passed, 6 skipped` ⇒ **抖动的唯一来源是守卫**。

### 技术栈与约束

| 项 | 值 |
|---|---|
| pytest | 9.1.1（`TEST_OUTCOME = (OutcomeException, Exception)` —— **不含 `BaseException`**） |
| 沙箱守卫 | `D:/Program Files/WorkBuddyAI/resources/app.asar.unpacked/cli/vendor/shim/sitecustomize.py`（**仓外，不可改**）；`raise SystemExit(1)` 在 `:848`；`[SAFE_DELETE_BULK_GUARD_ERROR]` 三种上报形态在 `:858/:872/:877`；阈值 `safeDeleteBulkThreshold: 10000` |
| 测试树 | `tests/`（根级；**基线 204 用例 → BUILD 后 230**：本 change 新增 26 个测试函数）与 `upstream/tests/`（框架侧） |
| 根 conftest | `tests/conftest.py`（**基线 163 行 → BUILD 后 372 行**，已有 `pytest_configure`） |
| **硬约束** | **不得触碰 `upstream/`**（vendored 内核）；**不得削弱 safe-delete 语义**；韧性层**不得静默** |

### 🔴 根因有两个位置（本 Phase 新发现，且其中一个在 vendored 内核内）

```
① pytest fixture teardown 的 Path.unlink() / shutil.rmtree()
     → 触发 shim 守卫 → SystemExit(1)
     → pytest TEST_OUTCOME 不含 BaseException ⇒ 收尾中断
     → 临时目录残留 / 状态污染 ⇒ 后续测试 d.mkdir()（无 exist_ok）抛 FileExistsError
     （实测点：tests/test_verify_notices_default_safe.py:95 与 :263）

② upstream/fstdd/cli/commands/experience.py:241
     os.remove(lock_path)
     except OSError:            ← ⚠️ SystemExit 不是 OSError ⇒ 抓不到
     → 进程被杀、pytest 汇总不打印（EXP-2026-0029 原文：「整片报红」）
```

> **② 在 vendored 内核内**，而本 change 的 Gate 1 范围明确「不碰 `upstream/`」⇒ ② 的**代码修改**不在本 change 内。
> 但 D2 选定的机制**能在不修改 ② 的前提下兜住它**（见下）。

### 经验库交叉检查（Step 2）—— **改变了实现方向**

| 经验 | 内容 | 对本设计的影响 |
|---|---|---|
| **EXP-2026-0029**（medium，source=2026-10-11-experience-center-node-sync） | 沙箱 safe-delete 守卫在状态锁被占用时拦截 `os.remove`，导致文件锁释放抛 `SystemExit` 整片报红；`root_cause` 直指 `_index_lock` 释放点；`fix_template` = **测试期避免并发重删除进程 + 把 TMP/TEMP 指向中立目录 + 判据上把「整片红 + 守卫报错」与真实回归区分开** | **① 根因早被记录**（本 change 不是新问题）；② 提示了「TMP/TEMP 中立化」这条**规避**路径 ⇒ 纳入 D1 |
| **EXP-2026-0030**（medium） | 把 TMP/TEMP 指向 agent runtime 目录会让 Guard 把测试临时路径判为「agent runtime dir」而放行 | 佐证「TMP/TEMP 必须指向**仓库外的中立目录**」 |
| **EXP-2026-0014**（medium） | 关键路径插入 best-effort 增强时用 `except Exception: pass` 静默降级 | 直接支撑 D3「**必须可见，不得静默**」；并被 `audit_silent_except` 哨兵强制 |
| KG-092（high，跨项目 17 次） | 钩子失败时 exit 0 且不上报告警 —— 失败静默腐烂 | 同上，支撑 D3 |

## Decisions

### 1. 双轨策略：**规避（治本方向）+ 兜底（韧性）**，而非只做其一

**方案**：D1a 在 conftest 中把测试期 `TMP`/`TEMP`/`TMPDIR` 指向**仓库外的中立目录**（规避 ①：让 pytest 的临时路径不落在被守卫管控/放行的目录里）；
D1b 在 conftest 中为删除原语加**外层包装**，捕获 `SystemExit` 并转为**可见告警**（兜底 ①与②）。

**为什么**：两条经验（EXP-0029/0030）都指向「临时目录落点」是触发条件之一，规避可**减少触发面**；
但规避不能保证 100% 不触发（守卫是并发状态锁仲裁，与落点无关的那部分仍在），故必须配兜底。
**兜底选「外层包装删除原语」的关键理由**：它是**唯一能同时兜住 ① 与 ② 的层** ——
conftest 在 pytest 进程内运行，包装 `os.remove`/`os.unlink`/`shutil.rmtree` 后，**框架代码 `experience.py:241` 的 `os.remove` 也会走我们的 wrapper**，
从而在不修改 `upstream/` 的前提下兜住 ②。

**备选方案及排除原因**：
- 备选 A：**只用 pytest hook**（`pytest_runtest_makereport` / `pytest_exception_interact`）—— **排除**：`SystemExit` 从 fixture finalizer 冒泡的路径**不经过**这些 hook，且 hook 拿不到 ②（框架进程内调用）；
- 备选 B：**改 shim**（把 `SystemExit` 降级）—— **排除**：属仓外程序，不在本 change 射程，且会削弱守卫语义；
- 备选 C：**改 `upstream/.../experience.py:241` 的 `except OSError` → `except (OSError, SystemExit)`** —— **排除**：触碰 vendored 内核（违反 Gate 1 范围 + 需 `UPSTREAM_PATCHES` 登记），**登记为已知残留**（见 Risks）；
- 备选 D：**把 `d.mkdir()` 改 `exist_ok=True` 了事** —— **排除**：只治 ① 的症状末端（C2 仍做，但单独做不足以消除抖动）。

### 2. 韧性层的落点：**包在删除原语外层的上下文无关 wrapper**，不依赖 fixture 生命周期

**方案**：在 `tests/conftest.py` 以 `pytest_configure` 为安装点，包装 `os.remove`/`os.unlink`/`shutil.rmtree`；
wrapper 捕获 **`BaseException` 中的 `SystemExit`**，转成「记录 + 告警」后**正常返回**（删除失败 = 目标已不存在或未删掉，对测试语义无害）。

**为什么**：
- 与 fixture 生命周期**解耦** ⇒ 不会因「fixture 自身 teardown 被打断」而失效（这正是 hook 方案的死穴）；
- 安装点在 `pytest_configure`（session 级、最早），确保**所有**测试与框架调用都被覆盖；
- 只在**测试进程内**生效，**不改变生产行为**。

**备选方案及排除原因**：
- 备选：写成 autouse fixture —— **排除**：fixture 自身的 finalizer 同样会被 `SystemExit` 打断，等于没装。

### 3. 可见性契约：**捕获即告警 + 计数 + 汇总**，严禁静默

**方案**：每次捕获都 `warnings.warn(...)`（含被捕获的删除目标路径），并在 session 结束时输出一行汇总
（`[teardown-resilience] 捕获 N 次 SystemExit（守卫触发），已降级为告警`）。

**为什么**：EXP-2026-0014 与 KG-092 都是「静默降级导致失败腐烂」；且本仓有 `audit_silent_except` 哨兵会点名白名单外的吞异常点。
**备选**：静默 pass —— **排除**：会掩盖真实删除失败，且会被哨兵判红。

### 4. 反向守卫：**只放行 `SystemExit`，其余异常一律照常失败**

**方案**：wrapper 内 `except SystemExit: ...` 单独处理；**不写** `except Exception`。
**为什么**：SC3 要求「真实 teardown 异常仍须导致失败」；宽捕获会把资源泄漏、权限错误等真实缺陷一并吞掉。
**备选**：`except BaseException` —— **排除**：会吞掉 `KeyboardInterrupt` 等，且语义过宽。

### 5. 范围边界：**② 的代码不修，但行为被 D2 覆盖**；② 的根因修复登记为独立欠账

**方案**：本 change **不修改** `upstream/fstdd/cli/commands/experience.py`；
在 `test-report.md` 与 `pending-adjustments` 中登记「② 的 `except OSError` 不覆盖 `SystemExit`」为**独立欠账**（建议与 ③ 同类走 `UPSTREAM_PATCHES` 登记后另立 change）。

**为什么**：Gate 1 的 non_goals 明确「不碰 `upstream/`」；且 ② 的真实修法（收窄/扩展异常类型）属框架语义决策，应由独立 change 承载。
**注意**：D2 的 wrapper 已在**行为上**兜住 ②（框架调用也被包装），故本 change 交付后**抖动应消失**；② 的欠账是「语义层面的干净修复」。

### 6. `d.mkdir(exist_ok=True)` 的定位：**必要的症状末端加固**，不作为主方案

**方案**：`tests/test_verify_notices_default_safe.py` 的 L95 / L263 两处 `d.mkdir()` → `d.mkdir(exist_ok=True)`。
**为什么**：D1/D2 生效后目录本不应残留，但**测试应对「残留」具备鲁棒性**（防御性），且该改动零风险。
**备选**：不改 —— **排除**：一旦守卫在更早的 session 触发并留下残留，该测试仍会红，属不必要的脆弱。

### 决策 ↔ What Changes ↔ Capability 映射

| 决策 | 对应 What Changes（proposal） | Capability | 对应 SC |
|---|---|---|---|
| D1（双轨：规避 + 兜底） | **C1** conftest teardown 韧性层 | test-teardown-resilience | SC-001、SC-002、SC-004 |
| D2（包装删除原语，`pytest_configure` 安装点） | **C1** | test-teardown-resilience | SC-001 |
| D3（可见性契约：告警 + 计数 + 汇总） | **C1** | test-teardown-resilience | SC-002 |
| D4（反向守卫：只放行 SystemExit） | **C1** | test-teardown-resilience | SC-003 |
| D6（`d.mkdir(exist_ok=True)`） | **C2** | test-teardown-resilience | SC-005 |
| D2/D3/D4（monkeypatch 回归测试：判据不依赖环境恰好触发守卫） | **C3** | test-teardown-resilience | SC-001、SC-002、SC-003 |
| D5（② 不修 → 登记欠账）+ 确定性判定法落 test-report | **C4** | test-teardown-resilience | **SC-006**（可判性）、**SC-007**（范围边界） |

> **C3** 的用例由 TC-TTR-001..007 承载（见 test-plan.md §二）。
> ⚠️ 本表在 BUILD 期修正过：原表把 C4 误映射到 SC-007 且遗漏 C3 行（见 `design-adjustments.yaml` ADJ-009）。

## Architecture

```
pytest session 启动
   │
   ├─ conftest.pytest_configure()          ← D2 安装点（最早）
   │     ├─ D1a: os.environ["TMP"/"TEMP"/"TMPDIR"] = <仓库外中立临时根>（BUILD 期实证：须为系统临时根本身）
   │     └─ D1b: wrap os.remove / os.unlink / os.rmdir / shutil.rmtree
   │                / pathlib.Path.unlink / pathlib.Path.rmdir   ← ⚠️ BUILD 期实证扩容（ADJ-008）
   │              └─ wrapper: try 原实现
   │                          except SystemExit → warn + 计数 → return（降级为告警）
   │                          except Exception  → 原样抛出（D4 反向守卫）
   │
   ├─ 测试执行（tests/ 230 用例）
   │     ├─ ① pytest fixture teardown 的 unlink → 命中 wrapper ✅
   │     └─ ② 框架 experience.py:241 os.remove → 命中 wrapper ✅（无需改 upstream）
   │
   └─ session 结束 → 输出汇总行：[teardown-resilience] 捕获 N 次 SystemExit（守卫触发）
```

### ⚠️ BUILD 期实证修正（详见 `design-adjustments.yaml`）

| # | 原设计 | 实证后 | 依据 |
|---|---|---|---|
| **A** | D1a「让 pytest 临时路径**不落在**被守卫放行的目录里」 | **反向**：须**留在**系统临时根之下（bypass 集内） | shim `_should_bypass_safe_delete`（:1096）判据是「路径在 `_os_tmp_dirs` **之下**」，而 `_os_tmp_dirs` 于 shim import 期固化（:805-825）⇒ **迁出反而撞守卫** |
| **B** | D2 只包装 `os.remove` / `os.unlink` / `shutil.rmtree` | **扩为 6 个入口**（+ `os.rmdir` / `pathlib.Path.unlink` / `pathlib.Path.rmdir`） | shim `:1281` **直接替换** `pathlib.Path.unlink` 为 `_safe_path_unlink`，其非 bypass 分支直接 `_try_trash()`（:1237）**不经过 `os.unlink`** ⇒ 原集合**漏掉根因①**（仓库内路径） |

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| **wrapper 吞掉真实删除失败** ⇒ 掩盖资源泄漏 / 权限问题 | D3：捕获即 `warnings.warn`（含目标路径）+ session 汇总计数；D4：**只放行 `SystemExit`**，其余照抛；SC3 反向守卫用例 |
| **`shim` 的拦截层比 `os.remove` 更底层** ⇒ wrapper 挂在外层却拦不到 | Phase 3 以 **RED 实测**验证（monkeypatch 让被 wrap 的原实现抛 `SystemExit`，断言 wrapper 捕获）；若拦不到，退回 D1a 规避 + 记录 |
| **`TMP/TEMP` 中立化影响其它测试的路径假设** | 中立目录须**可写**且**在仓库外**；全量跑对比改动前后 failed/errors 数（SC7）；仅测试进程内设置 |
| **改 `tests/conftest.py` 影响全部根级测试**（面状污染） | 改动集中在 `pytest_configure` 内、不改既有逻辑；跑全量 + 逐项对比 |
| **② 的 `except OSError` 仍在** ⇒ 语义层面欠账未清（仅被行为兜住） | D5：登记为独立欠账，建议与 ③ 同类走 `UPSTREAM_PATCHES` 登记后另立 change；在 test-report 明确**能力边界** |
| **沙箱守卫本身不可控** ⇒ 守卫行为变化会使本 change 的兜底失效 | SC5「连续 3 次全量 failed/errors 一致」作为回归判据；若守卫改版导致新形态，按 EXP-0029 的 `detection_trigger` 识别（stderr 含 `SAFE_DELETE_BULK_GUARD_ERROR`） |
