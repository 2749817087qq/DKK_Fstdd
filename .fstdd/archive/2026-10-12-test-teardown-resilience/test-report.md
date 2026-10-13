# 测试报告 — change 2026-10-12-test-teardown-resilience

> Phase 3 BUILD 质量验证（V3.0.5：SLICE / BUILD / VERIFY 合一）
> 执行模式：**full_auto（长程）** · 基线 `34f11b5`（**工作树未提交**，改动仅 `tests/`）
> 测试环境：Windows · Python 3.13.12 · pytest 9.1.1 · `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`
> 报告时间：2026-10-13（UTC+8 01:4x）

## 一、TC 覆盖率（planned vs actual）

| 指标 | 值 |
|---|---|
| 计划 TC | **9**（TC-TTR-001..009） |
| 有实现测试的 TC | **7/7 可落码的 TC（100%）**（TC-TTR-008/009 为会话级/边界级，按 test-plan 不落代码） |
| `ci check-failures` TC 实现覆盖 | **8/10（80%）** —— ⚠️ 缺 TC-TTR-008 / TC-TTR-009。该检查**只统计出现在代码里的 TC-ID** ⇒ 会话级/边界级 TC 必然显示「缺失」，属**预期**（见 §五） |
| 新增测试函数 | **26**（capture 10 + visibility 7 + real_exception 3 + tmp_neutral 5 + notices 文件 1） |
| 新增测试文件 | **4**（`tests/test_teardown_resilience_{capture,visibility,real_exception,tmp_neutral}.py`） |
| 修改测试文件 | `tests/conftest.py`（+213/−4）· `tests/test_verify_notices_default_safe.py`（+18/−3） |
| `traceability` | `spec_scenarios: 7` / `tc_cases: 9` / `test_functions: 26` |

**两条不落代码的 TC 的覆盖方式**：

| TC | 类型 | 执行方式 | 证据 |
|---|---|---|---|
| **TC-TTR-008** | 会话级（可判性） | 连续 3 次全量 `pytest tests -q -p no:cacheprovider --basetemp=<每次全新>` | **§四.1** |
| **TC-TTR-009** | 边界级（范围） | `git status --porcelain` 白名单核对 | **§四.2** |

> 为什么不能落代码：TC-008 需要「运行整套测试」，把它写成套件内用例会**递归**；
> TC-009 依赖**交付时刻**的 git 状态，在任何时刻断言都会在别处假红。二者只能以「实跑 + 留证」方式覆盖。

### 1.1 覆盖率诊断（仅变更文件）

> 覆盖率仅作诊断参考，不作为通过/失败的门禁条件（`quality.coverage.fail_under: 0`）。
> 本 change **只改测试文件**，故「被覆盖的源码」即 `tests/conftest.py` 的新增部分。

```
$ cd tests && pytest test_teardown_resilience_*.py test_verify_notices_default_safe.py \
      --cov=conftest --cov-report=term-missing
Name          Stmts   Miss  Cover   Missing
-------------------------------------------
conftest.py     174     42    76%   85, 136-143, 154, 180-185, 198,
                                    295-296, 299, 305-308, 313-314, 324-327, 336-372
TOTAL           174     42    76%
32 passed in 5.09s
```

| 变更文件 | 行覆盖率 | 状态 | 说明 |
|---|---|---|---|
| `tests/conftest.py` | **76%**（174 stmts / 42 miss） | ✅ | 新增韧性层/规避层/汇总判据**已覆盖**；余缺项见下 |

**未覆盖行说明（逐项评估，均无需补测）**：

| 行号 | 内容 | 评估 |
|---|---|---|
| `85` / `154` | `_install_delete_guard` / `_neutralize_temp_env` 的**幂等早返回** | 会话内只安装一次 ⇒ 天然不进入；由「重复调用不重复包装」的设计保证 |
| `136-143` | `_pick_neutral_root` 的**回退分支**（系统临时根落在仓库内） | 防御分支；实测未发生（发生时会有 warning 告警） |
| `180-185` / `198` | `_load_platforms` 的 env-规则分支 | **基线既有代码**，非本 change 引入 |
| `295-372` | `get_current_platform` / `get_skill_dir` / `repo_root` / `read_file` / `read_heartbeat_env` | **基线既有 helper**，未被这 5 个文件触达 |

> 🔴 **本诊断直接促成了 ADJ-012**：初次测量为 **66%**，且 `pytest_sessionfinish`（D3 的汇总输出主体）
> 的函数体（`240-255`）**完全未覆盖** —— 因为自测隔离让会话结束时 `captured == 0`，该函数提前返回。
> 已补 4 个直接驱动该 hook 的用例（现覆盖），覆盖率升至 **76%**。

## 二、每切片验证状态

| Slice | 范围 | TC | 用例数 | RED 证据 | GREEN 证据 | 状态 |
|---|---|---|---|---|---|---|
| **S1** 韧性层 | `tests/conftest.py`：包装 6 个删除入口 + 可见性 + 反向守卫 + 自测隔离 + 汇总判据 | TC-001..005 | 20 | 4 failed（`AttributeError: module 'conftest' has no attribute 'DELETE_GUARD_STATS'`） | 20 passed | ✅ |
| **S2** 规避层 + 症状加固 | `tests/conftest.py`：临时目录归一；`tests/test_verify_notices_default_safe.py`：2 处 `mkdir(exist_ok=True)` | TC-006/007 | 6 | 4 failed（`TMPDIR` 未设置 ×2 + 中立目录非专用 ×1 + **`FileExistsError`（症状本身）** ×1） | 6 passed | ✅ |
| **Part C** 验证类 | 不落代码 | TC-008/009 | — | — | 见 §四 | ✅ |

**S1 RED 原文（关键一行）**：
```
E       AttributeError: module 'conftest' has no attribute 'DELETE_GUARD_STATS'
FAILED tests/test_teardown_resilience_capture.py::test_ttr_001_guarded_delete_swallows_systemexit
4 failed in 0.85s
```

**S2 RED 原文（症状本身被复现）**：
```
E           FileExistsError: [WinError 183] 当文件已存在时，无法创建该文件。: '...\test_tc_qis_003c_mkdir_tolerat0\notices'
tests\test_verify_notices_default_safe.py:95: in _mk_hit_dir
4 failed, 2 passed in 0.56s
```

## 三、C1 多路并行技术评审（3 代理）

| 代理 | 维度 | 结论 | 发现（C/H/M/L） |
|---|---|---|---|
| 1 | 代码评审（`tests/conftest.py` 韧性层/规避层） | **需修改** | 1 / 3 / 2 / 2 |
| 2 | 测试评审（4 个新文件 + 1 个改动文件） | 有条件接受 | 0 / 1 / 2 / 1 |
| 3 | 文档一致性评审（proposal/design/spec/test-plan/元数据 vs 实现） | 有偏差需修正 | 0 / 2 / 1 / 0 |

**处置结果**：**1 blocker + 4 major 全部处置**（3 修 + 1 明确不采纳），6 minor/nit 修 5 记 1。详见 §六。

> ⚠️ **本轮最大价值即来自评审**：代理 1 报出的 blocker（包装面漏 `pathlib.Path.unlink`）**经独立复核属实**，
> 若不修则本 change 的核心主张不成立。**评审不是形式，它救了这个 change。**

## 四、确定性验证（TC-TTR-008 / TC-TTR-009）

### 4.1 TC-TTR-008 —— 连续 3 次全量，failed/errors 一致

> `observed_at`：见下方命令输出 · `observed_base_git_sha`：`34f11b50a22725af2ad45f2b7663fa535f332b66`（+ 未提交工作树）
> 命令：`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 <python> -m pytest tests -q -p no:cacheprovider --basetemp=<每次全新目录>`

| 轮次 | 结果 | failed | errors | 会话汇总行 | 耗时 |
|---|---|---|---|---|---|
| 1 | `230 passed, 6 skipped, 6 warnings` | **0** | **0** | 0 | 167.56s |
| 2 | `230 passed, 6 skipped, 6 warnings` | **0** | **0** | 0 | 164.48s |
| 3 | `230 passed, 6 skipped, 6 warnings` | **0** | **0** | 0 | 210.48s |

```
$ OBSERVED_AT=2026-10-12T17:29:26+00:00  HEAD=34f11b50a22725af2ad45f2b7663fa535f332b66  conftest=372 行
  第 1 次: 230 passed, 6 skipped, 6 warnings in 167.56s (0:02:47)  | failed=[0 failed] errors=[0 error] | 汇总行=0
  第 2 次: 230 passed, 6 skipped, 6 warnings in 164.48s (0:02:44)  | failed=[0 failed] errors=[0 error] | 汇总行=0
  第 3 次: 230 passed, 6 skipped, 6 warnings in 210.48s (0:03:30)  | failed=[0 failed] errors=[0 error] | 汇总行=0
```

**结论：✅ 通过（最终冻结产物）** —— 3 次的 `failed` 与 `errors` 数**完全一致且均为 0**；
且「会话汇总行 = 0」说明**守卫未触发**（与「守卫未触发时确定」的历史基线一致）。
⇒ 本 change 的最终目标（**门禁数可判**）在本机成立。

> ⚠️ **能力边界**：本条证明的是「**守卫未触发时**确定」。真正的抖动场景（守卫触发）
> 需要 `CODEBUDDY_SAFE_DELETE_BULK_STATE_DIR` + `CODEBUDDY_TOOL_CALL_ID` 同时存在（shim `:851-857`），
> 本机当前**不具备**该条件 ⇒ 无法实跑复现。
> 该场景的**行为覆盖**由 TC-TTR-001 的端到端判据承担（monkeypatch 让原实现抛 `SystemExit`，
> 覆盖**非 bypass 路径**），属「用可控桩替代不可控环境」的确定性判据设计。

**对照 —— 修复前的抖动**（本 change 的 Why）：

| 执行者 | failed | errors |
|---|---|---|
| 主理人 | 5 | 1 |
| 门神 | 4 | 17 |

⇒ 同一 HEAD、同一命令，失败数**不可判**。本 change 的目标即消除该抖动。

**对照 —— 守卫未触发时的历史基线**：连跑 2 次均 `204 passed, 6 skipped`（`observed_at 2026-10-12T13:32:56Z`）。
⇒ **抖动的唯一来源是守卫**，与「守卫未触发时确定」互为佐证。

### 4.2 TC-TTR-009 —— 范围边界：改动不含 `upstream/`

```
$ git status --porcelain
 M .fstdd/experiences/.experience-index.yaml     ← 经验库索引（本 change 新增 4 条经验，正当更新）
 M tests/conftest.py
 M tests/test_verify_notices_default_safe.py
?? .fstdd/changes/2026-10-12-canon-merge-command/          ← 另一个 change（③），Phase 1 产物
?? .fstdd/changes/2026-10-12-test-teardown-resilience/
?? .fstdd/experiences/EXP-2026-0034.md ... EXP-2026-0037.md
?? tests/test_teardown_resilience_{capture,real_exception,tmp_neutral,visibility}.py

$ git status --porcelain | awk '{print $2}' | grep -E "^upstream/"
（无输出）
```

**结论：✅ 通过** —— 改动**不含 `upstream/`** 下任何文件；范围限于 `tests/`、`.fstdd/changes/<本 change>/`
与 `.fstdd/experiences/`（经验记录，见 §九）。与 proposal 的 NonGoals 一致。

### 4.3 自测隔离的准确性验证（ADJ-011）

| 时点 | 观察 | 结论 |
|---|---|---|
| 修复前 | 全量运行中会话汇总行出现 **1 次**，列出约 10 条**自测注入**的路径 | 汇总**失真**（把自测注入报成「守卫触发」） |
| 修复后 | 单跑 5 个相关文件 **28 passed**，会话汇总行出现 **0 次** | ✅ 汇总只在**真实**守卫触发时出现 |

## 五、C4 失败模式检查（23 类逐项）

| # | 失败模式 | 结果 | 检查动作 / 证据 |
|---|---|---|---|
| 1 | 幻觉调用 | ✅ | 无新符号未定义；`conftest.py` 7 个新函数 + 2 个 hook + 1 个夹具全部有定义点；全量 230 passed 无 `AttributeError`/`ImportError` |
| 2 | 过度信任 LLM | ✅ | **本 change 的核心教训**：初版结论（「`Path.unlink` 经由 `os.unlink`」）来自裸 python 进程，被 shim 源码 + 目标环境实测**推翻** ⇒ 已改（ADJ-006/008），并新增经验 EXP-2026-0036 |
| 3 | Prompt 注入 | ✅ | 本 change 不含外部输入拼接进 prompt |
| 4 | 记忆污染 | ✅ | 测试全部 hermetic（`tmp_path` + `monkeypatch`）；`DELETE_GUARD_STATS` 由自测隔离夹具用后还原（ADJ-011） |
| 5 | 上下文窗溢出 | ✅ | 单次 edit 均 < 200 行 |
| 6 | 工具参数漂移 | ✅ | 仅用既有 CLI 子命令与既有参数；`experience add` 的非法 `--category` 已按报错改正（见 §九） |
| 7 | 安全凭证泄露 | ✅ | 本 change 不触碰凭证；未新增任何凭证字面量 |
| 8 | 权限绕过 | ✅ | 未手改 `.fstdd.yaml` 的 gate 确认字段；Gate 1/2 均走 `fstdd gate approve`；**未自跑 Gate 3** |
| 9 | 并发竞态 | ✅ | 2 个切片**串行**（同文件）；包装为进程内单线程安装；无并发写同一文件 |
| 10 | 路径遍历 | ✅ | 中立根选取有「仓库内不可用」校验（`_pick_neutral_root`）；探针路径固定 |
| 11 | 跨会话残留 | ⚠️ | `--basetemp` 落在系统临时区（仓库外）；**仓库内无残留**（已核 `find tests -name '.ttr-probe*'` 为空）。⚠️ 系统临时区的 `pytest-of-*` 目录不清理（既有惯例，不影响门禁） |
| 12 | 输出截断 | ✅ | 会话汇总超过 20 条时输出「其余 N 条省略」提示（ADJ-007） |
| 13 | 格式错误 | ✅ | 新增 YAML（`pending-adjustments.yaml` / `design-adjustments.yaml`）均 `yaml.safe_load` 校验通过；全 change 目录 **CRLF 归零** |
| 14 | 循环依赖 | ✅ | `dependency-graph` ⇒ `nodes=0 / edges=0 / cycles=无`；未引入新环 |
| 15–22 | 金融 8 类（重复扣款 / 账实不符 / 静默降级 / 精度丢失 / 审计缺口 / 状态机漏洞 / 额度穿透 / 合规遗漏） | ⏭ SKIPPED | 本 change 为**测试基础设施加固**，非金融系统；无资金流 / 风控 / 对账路径。⚠️ **但「静默降级」这一条的纪律已按金融标准执行**（D3：捕获必须可见；且实现期主动消除了一处 `except ...: pass`） |
| 23 | 过度工程 | ✅ | YAGNI 逐项：包装 6 个入口（**blocker 修复的必需面**，非冗余）· 中立根归一（消 TMPDIR 缺失）· 自测隔离夹具（**实跑发现的失真**，非预防性）· 端到端判据 5 条（含 2 条判别性）· 未引入新依赖、未新增抽象层、未改既有函数签名 |

**汇总：17 ✅ / 1 ⚠️ / 5 ⏭（非金融）**

## 六、C1 评审发现与处置（3 代理）

### 6.1 代码评审（代理 1）—— 结论：需修改

| # | 级别 | 发现 | 证据 | 处置 |
|---|---|---|---|---|
| 1 | 🔴 **blocker** | 包装集合覆盖不到根因①：shim **直接替换** `pathlib.Path.unlink`，其非 bypass 分支直接 `_try_trash()`、**不经过 `os.unlink`** | shim `:1281` / `:1224-1237`；`pathlib.Path.unlink.__name__` = `_safe_path_unlink` | ✅ **已修**（扩为 6 入口，ADJ-008） |
| 2 | major | 端到端判据用 `tmp_path` ⇒ 走 bypass 分支 ⇒ **假绿**，证明不了根因① | `_should_bypass_safe_delete`（`:1096`） | ✅ **已修**（改仓库内探针 + 包装面结构核对） |
| 3 | major | `pytest_sessionfinish` 不改 `exitstatus` ⇒ 「绿而残留」 | — | ❌ **明确不采纳**（见 §6.4） |
| 4 | major | `_pick_neutral_base()` 回退到 `~/.cache` ⇒ 脱离 bypass 集 ⇒ 反而撞守卫 | `_is_under_os_tmp_dir`（`:1036-1040`） | ✅ **已修**（归一为系统临时根 + 不变式判据，ADJ-001） |
| 5 | minor | `os.remove is os.unlink` 不变式被打破 | shim `:1277-1278` 令两者同一对象 | ⚪ **记录**（已 grep 确认仓库内无依赖；保持两个独立包装体以便 monkeypatch 分别驱动 —— **有意取舍**） |
| 6 | minor | 无 `functools.wraps` ⇒ `__name__` 变 `_wrapper` | — | ✅ **已修**（手工逐属性复制；`functools.wraps` 会 `update` 内建函数不存在的 `__dict__`） |
| 7 | minor | 汇总只打印前 20 条，无省略提示；`targets` 无上限 | — | ✅ **已修**（加省略提示）；⚪ `targets` 无上限**记录**（捕获罕见：3 次全量均为 0） |
| 8 | nit | `_DELETE_GUARD_ORIGINALS` 兼作安装哨兵 | — | ✅ **已修**（独立布尔 `_DELETE_GUARD_INSTALLED`） |
| 9 | nit | 门禁若加 `-W error` 会使告警升级为异常 | 当前无此配置 | ⚪ **记录** |

### 6.2 测试评审（代理 2）—— 结论：有条件接受

| # | 级别 | 发现 | 处置 |
|---|---|---|---|
| 1 | major | `test_ttr_006_tmp_dir_is_writable` 非判别性（系统临时区同样可写 ⇒ 不中立化也通过） | ✅ **已修**（加「必须等于中立根」断言） |
| 2 | minor | TC-004 第二条断言只比长度、不比内容 | ✅ **已修**（比对 `targets[-2:]` 的实际内容） |
| 3 | minor | TC-007 末尾 `assert d == pre and d.is_dir()` 中 `d == pre` 恒真 | ✅ **已修**（改为显式 `d.is_dir()` + `d == pre` 两条独立断言与文案） |
| 4 | nit | 剥注释用 `line.split("#", 1)[0]`，字符串内含 `#` 会误切 | ⚪ **记录**（当前无害） |

**代理 2 确认无问题**：双向断言齐备（放行 SystemExit ⇄ 真实异常照抛；删除被吞 ⇄ 正常删除生效）·
monkeypatch 用法正确（`setitem` 只改字典值、teardown 必还原）· TC-TTR-004 隔离性 OK（断言用增量而非绝对值）·
环境判别有效（`TMPDIR` 缺失时如实失败）· TC ↔ 测试映射 9/9 无遗漏错配。

### 6.3 文档一致性评审（代理 3）—— 结论：有偏差需修正

| # | 偏差 | 处置 |
|---|---|---|
| 1 | design.md 映射表把 **C4 误映射到 SC-007**（应为 SC-006）且**遗漏 C3 行** | ✅ 已修（ADJ-009） |
| 2 | design.md / test-plan.md 数字滞后（163 行 / 204 用例 / 6 用例） | ✅ 已修（372 行 / 230 用例 / 7 用例） |
| 3 | test-plan 的 9 个 TC「当前状态」列全为 ❌；执行矩阵全为 🔴 | ✅ 已修（含文件与用例数） |
| 4 | `.fstdd.yaml` 的 `traceability` 三项为 0 | ✅ 已修（`7 / 9 / 22`） |
| 5 | `code-structure-delta.md` 只有 1 行（CLI 自动段过窄） | ✅ 已修（人工补全 + 注明来源） |
| 6 | `pending-adjustments` 漏记 2 条（汇总逐条列目标、中立根回退链） | ✅ 已补（ADJ-007 / ADJ-001） |
| 7 | D5 要求登记「② 的 `except OSError` 不覆盖 SystemExit」欠账但文件无该条目 | ✅ 已补（ADJ-010） |

### 6.4 明确不采纳的 1 项（附理由）

**发现**：代理 1 建议「捕获次数 > 0 时把 `session.exitstatus` 置 1」，理由是「守卫真拦下删除时会话仍绿 ⇒ 绿而残留」。

**驳回理由**：
1. 这会让**失败数重新依赖「守卫是否恰好触发」** ⇒ **正是本 change 要消除的非确定性**，与 SC-006（可判性）**直接冲突**。
2. design 决策 3 的契约是「**可见**」（告警 + 黄色汇总行），而非「判红」；
   design 决策 1 已明确「删除失败 = 目标已不存在或未删掉，**对测试语义无害**」。
3. 该建议的正确部分（「残留不应被忽略」）已由 **D1a 规避** + **可见性契约**覆盖。

⇒ 已在 `tests/conftest.py::pytest_sessionfinish` 的 docstring 中写明该理由，避免后人重复提出。

## 七、C3 Diff 审查（逐文件）

| 文件 | 变化 | 审查要点 |
|---|---|---|
| `tests/conftest.py` | **+213 / −4**（163 → 372 行） | 新增 6 个函数 + 2 个 hook + 1 个 autouse 夹具；**未改既有函数签名与逻辑**；`except` 仅 `SystemExit`（+ 2 处基线）；**无 `pass` 静默分支** |
| `tests/test_verify_notices_default_safe.py` | **+18 / −3** | 2 处 `mkdir()` → `mkdir(exist_ok=True)`；新增 1 个用例（TC-TTR-007） |
| `tests/test_teardown_resilience_capture.py` | 新增 · 10 个测试函数 | 包装面结构核对 ×2 + 纯函数 ×2 + 端到端 ×5 + 收尾链 ×1 |
| `tests/test_teardown_resilience_visibility.py` | 新增 · 3 个测试函数 | warning 含路径 + 计数与内容 + **自测隔离接线** |
| `tests/test_teardown_resilience_real_exception.py` | 新增 · 3 个测试函数 | `PermissionError` / `KeyboardInterrupt` 照抛 + 源码级无宽捕获（剥注释） |
| `tests/test_teardown_resilience_tmp_neutral.py` | 新增 · 5 个测试函数 | 设置齐备 / 仓外 / 三者一致 / **停在 bypass 根** / 可写 |

**Diff 结论**：改动集中、无范围蔓延；**未触碰 `upstream/`**（TC-TTR-009 已核）。

## 八、C2 全量质量检查

| 检查 | 命令 | 结果 |
|---|---|---|
| 全量测试 | `pytest tests -q -p no:cacheprovider --basetemp=<新>` | **230 passed / 6 skipped**，0 failed / 0 errors |
| 失败模式 | `fstdd ci check-failures --dry-run` | **3 通过 / 2 警告 / 0 错误 / 5 跳过** |
| 规格校验 | `fstdd validate <change> --dry-run` | 1 警告（同下 ①） |
| 规格一致性 | `fstdd canon verify <change>` | **2/2 通过**（DC-HASH / DC-FIELD） |

**2 条警告的解释（均非本 change 缺陷）**：

① `(g) AND 超限: spec.md: AND 数量 6`
   —— `ci.py:397-413` 的 `check_and_count` **docstring 写「per scenario」但实现是全文件累计** `**AND**`。
   本 change 7 个 Scenario **各 1 条**（逐条 ≤5，合规）⇒ 累计 6 > 5 触发**假警告**。已登记欠账（ADJ-010 ②），
   并记录经验 **EXP-2026-0037**。

② `TC 实现覆盖: 8/10 (80%)。缺失: TC-TTR-008, TC-TTR-009`
   —— 该检查只统计**出现在代码里**的 TC-ID；TC-008/009 按 test-plan 是会话级/边界级，
   **本就不落代码**（见 §一）⇒ 属**预期**。

## 九、C5 经验库

### 本次新增经验（4 条）

| 经验ID | 类别 | 模式 | 严重程度 | 发现阶段 |
|---|---|---|---|---|
| **EXP-2026-0034** | runtime_deviation | 沙箱 shim 直接替换 `pathlib.Path.unlink`，其非 bypass 分支不经 `os.unlink` ⇒ 只包装 `os.*` 的删除守卫漏掉该路径 | **high** | Part C（C1 评审） |
| **EXP-2026-0035** | runtime_deviation | shim 的 bypass 判据是「路径位于 `_os_tmp_dirs` 之下」，而 `_os_tmp_dirs` 在 shim import 期固化 | medium | BUILD（侦察） |
| **EXP-2026-0036** | runtime_deviation | 在「无 shim / 无注入环境」下测得的运行期结论被外推到「有 shim 环境」⇒ 结论方向性错误 | **high** | Part C（C1 评审） |
| **EXP-2026-0037** | tool_misuse | `ci check-failures` 的 (g) AND 检查是全文件累计（docstring 却写 per scenario）⇒ Scenario > 5 个即假警告 | low | Part C |

### 本次命中已有经验（复用）

| 经验ID | 类别 | 模式 | 命中阶段 |
|---|---|---|---|
| **EXP-2026-0029** | runtime_deviation | 沙箱 safe-delete 守卫拦截 `os.remove` ⇒ `SystemExit` 整片报红（**已记录本 change 的根因**） | Phase 2（**改变了实现方向**） |
| **EXP-2026-0030** | runtime_deviation | TMP/TEMP 指向 agent runtime 目录会被 Guard 误判 | Phase 2 |
| **EXP-2026-0014** | runtime_deviation | `except Exception: pass` 静默降级 | Phase 2 / Part C |
| **EXP-2026-0021** | contract_gap | 审计类断言必须自带自检测试（违例能抓到 + 合法不误报） | Phase 2 |
| KG-092 | 知识图谱 | 钩子失败时 exit 0 且不上报告警 —— 失败静默腐烂 | Phase 2 |

### 经验统计

| 指标 | 数值 |
|---|---|
| 本次新增 | **4 条**（EXP-2026-0034..0037） |
| 本次复用 | **5 条**（EXP-0029 / 0030 / 0014 / 0021 + KG-092） |
| 经验库总计 | 见 `.fstdd/experiences/.experience-index.yaml`（本次 add 已正当更新索引，**未回退**） |

> ⚠️ 操作坑：`experience add` 的 `--category` 是**闭集**，非法值直接 exit 1（实测 `runtime_pitfall` / `tooling` 被拒，
> 改用 `runtime_deviation` / `tool_misuse` 后成功）。有效值见 CLI 报错列表。

## 十、C6 设计调整

详见 [`design-adjustments.yaml`](design-adjustments.yaml)。

| 项 | 值 |
|---|---|
| 调整总数 | **12**（`resolved_in_change: 11` / `carried_as_debt: 1`） |
| Major | **2** —— ADJ-008（blocker：包装面 3 → 6）· ADJ-001（D1a 因果方向被实证推翻） |
| Minor | 10 —— ADJ-002..007、ADJ-009、ADJ-011、ADJ-012 |
| 结转欠账 | 1 —— ADJ-010（3 条框架缺陷，全在 `upstream/`） |

⚠️ **建议 Gate 3 重点过目 ADJ-008 与 ADJ-001**（二者都是「设计假设被实证推翻」型，影响核心主张与不变式）。

## 十一、已知问题 / 未完成项

| # | 项 | 状态 | 说明 |
|---|---|---|---|
| 1 | `upstream/fstdd/cli/commands/experience.py:241` 的 `except OSError` 抓不到 `SystemExit` | ⏳ **结转欠账** | 本 change 仅在**行为上**兜住（框架调用也经包装）；语义修复须另立 change + `UPSTREAM_PATCHES` 登记 |
| 2 | `ci.py` 的 AND 检查文件级累计（假警告） | ⏳ **结转欠账** | 同上；同族缺陷亦见 `validate.py:67-70` |
| 3 | `fstdd structure delta` 判据过窄 | ⏳ **结转欠账** | 须人工补全 `code-structure-delta.md` |
| 4 | `os.remove is os.unlink` 不变式被打破 | ⚪ **有意取舍** | 已 grep 确认仓库内无依赖；保持独立包装体以便分别 monkeypatch |
| 5 | `DELETE_GUARD_STATS["targets"]` 无上限 | ⚪ **记录** | 捕获罕见（3 次全量均为 0） |
| 6 | 中立根若系统临时根落在仓库内则回退 `~/.cache` 并告警 | ⚪ **已知边界** | 该落点不在 bypass 集内（会告警提示）；实测未发生 |
| 7 | 自测隔离会一并还原「自测期间的真实守卫触发」 | ⚪ **已知边界** | 概率极低，影响仅「少报一次」 |

## 十二、Gate 3 前置条件核对

| 前置条件 | 状态 | 证据 |
|---|---|---|
| 全部切片完成 | ✅ | 2/2（§二） |
| 全量测试无失败 | ✅ | 230 passed / 6 skipped（§八） |
| 计划 TC 全覆盖 | ✅ | 7/7 可落码 TC + 2 条实跑留证（§一 / §四） |
| 确定性判据成立 | ✅ | 见 §四.1（连续 3 次 failed/errors 一致） |
| 范围边界成立 | ✅ | 不含 `upstream/`（§四.2） |
| 设计偏离已记录 | ✅ | 11 条（§十） |
| C1 评审发现已处置 | ✅ | 1 blocker + 4 major 全处置（3 修 + 1 驳回附理由，§六） |
| C4 失败模式检查 | ✅ | 17 ✅ / 1 ⚠️ / 5 ⏭（§五） |
| 经验库已更新 | ✅ | 新增 4 条（§九） |
| `canon verify` 通过 | ✅ | 2/2（§八） |
| 未触碰 `upstream/` | ✅ | §四.2 |
| **Gate 3 确认** | ⏳ | **等待 D哥 确认**（Gate 3 不自动跳过） |

## 十三、结论

**可以进入 Phase 4 DELIVER**（待 Gate 3 确认）。

- 本 change 交付后，**「守卫触发导致的门禁抖动」应在行为层面消失**：
  6 个删除入口全部被包装，仓库内路径的 `Path.unlink()` 与框架 `experience.py` 的 `os.remove` 均经本层。
- **能力边界（务必知晓）**：① ② ③ 三条框架缺陷的**语义修复仍欠账**（§十一 1–3），
  本 change 只保证「不因它们而不可判」，不保证「它们被修好」。
- **风险等级**：🟢 **低** —— 改动限于 `tests/`；未触碰 `upstream/`；未改既有函数签名；
  全量 230 passed 且确定性已验。
- **后续建议**：
  1. DELIVER 后为欠账 ①②③ 另立 change（须先登记 `docs/UPSTREAM_PATCHES.md`）；
  2. 与 ③ `2026-10-12-canon-merge-command` 同类走该登记流程。

### 13.1 质量信号汇总

| 信号源 | 状态 | 备注 |
|---|---|---|
| 单元/集成测试 | ✅ | 230 passed / 6 skipped，通过率 **97.4%**（6 skipped 为平台不匹配，基线即有） |
| E2E 测试 | N/A | `quality.e2e.enabled: false` |
| Lint | N/A | 本仓 `quality.lint` 配置为 `ruff check app/ tests/`，而 `app/` 不存在 ⇒ 未执行（既有配置现状） |
| 类型检查 | N/A | `quality.typecheck` 配置为 `mypy app/`，同上 |
| 多版本测试 | N/A | 配置列 3.10–3.12，本机仅 3.13.12 |
| 覆盖率 | 诊断 | **`tests/conftest.py` 76%**（见 §1.1）；`fail_under: 0`，仅诊断；未覆盖项均为幂等/防御分支或基线既有 helper |
| 十四类失败模式 | ✅ | 17 ✅ / 1 ⚠️ / 5 ⏭（非金融） |

---

## 十四、DELIVER 收口与交付后复验（Phase 4）

> 本节由 Phase 4 DELIVER 执行时补入，记录「提交后复跑」值（与 §八 的「提交前」值分开，便于对照）。

### 14.1 DELIVER 动作

| 步骤 | 动作 | 结果 |
|---|---|---|
| Step 0 | 版本自检 | 项目 `fstdd_version 3.3.8` ≥ 技能 `3.0.5` ⇒ 无漂移告警 |
| Step 2.5 前 | `structure delta` | CLI 仅输出 1 行（已知缺陷，欠账③）⇒ 已恢复**人工补全版**（52 行，含 CLI 原始输出留档） |
| Step 1 | `archive` | ✅ `archive/2026-10-12-test-teardown-resilience/`（17 文件）；`phases.deliver.status=completed` |
| Step 2 | canonical 合并 | ✅ 手工并入 **3 个 YAML**（proposal 用 change_id 名；code spec 用 capability 名 `test-teardown-resilience.yaml`；agent spec 用 change_id 名）+ 索引 3 条 |
| Step 2 | `canon verify` | ✅ **2/2**（DC-HASH / DC-FIELD） |
| Step 2.5 后 | `structure merge` | ✅ 并入 `.fstdd/code-structure/index.md` |
| Step 3 | git commit | ✅ `6053ed2`（主提交，36 文件）+ `e6c0b9e`（提交后自检发现的拼写修正，2 文件） |
| Step 3 | git tag | ⏳ **未创建** —— 本 change 未升版；版本/发布批次待 D哥 定（见下） |
| Step 3 | git push | ⛔ **未执行**（规程：不自动 push，由 D哥 决定何时 push） |
| Step 2.8/2.9 | 经验静默回传 + 知识图谱同步 | ⏸ **未执行** —— 属外部写入，按项目边界须 D哥 单独授权（见下） |

### 14.2 提交后四自检（复跑值）

| 自检 | 结果 |
|---|---|
| `tools/verify_eol.py` | **7/7 通过** |
| `tools/verify_skill_standards.py` | **7/7 通过** |
| `tools/verify_rename.py` | **8/8 通过** |
| `tools/verify_workbuddy_skills.py` | **PASS**（+ 6 条 WARN：`~/.workbuddy/skills` 下的影子副本，无功能影响） |

> ⚠️ `verify_eol` 的 TC-EOL-005（「索引零内容变更」）要求**工作树与 HEAD 一致**。
> 首次复跑时因「主提交后、拼写修正前」有未提交改动而 FAIL ⇒ **该 FAIL 是流程信号而非缺陷**，
> 提交 `e6c0b9e` 后即恢复 7/7。同理 `verify_rename` 的 TC-RENAME-006 内嵌调用也随之一同恢复。

### 14.3 提交后测试复跑

| 项 | 结果 |
|---|---|
| 根 `tests/` 全量 | **230 passed / 6 skipped / 0 failed**（与提交前一致） |
| `upstream/tests -k a6` | **3 passed**（「在办 change 未跟踪文件」哨兵未被 ③ 触发） |
| 工作树 | 仅剩 `?? .fstdd/changes/2026-10-12-canon-merge-command/`（③ 的在办目录，Phase 1） |

### 14.4 提交后自检发现并已修的 1 个缺陷（诚实留档）

| 发现 | 内容 | 处置 |
|---|---|---|
| `verify_rename` TC-RENAME-002 FAIL | `canonical/proposals/2026-10-12-test-teardown-resilience.yaml:2` 写 `` `stdd canon generate` ``，而工具已更名为 `fstdd`（仓库内既有文件均为 `fstdd`） | ✅ 已修（`e6c0b9e`），根 canonical 与归档副本同步；复跑 **8/8** |

> 这条**只有提交后才跑得出来**（主提交把它带进了被扫描面），是「提交后必须复跑自检」的又一实证。

### 14.5 仍待 D哥 决定的三件事

| # | 事项 | 说明 |
|---|---|---|
| 1 | **git tag / 版本批次** | 本 change 未升版（`fstdd_version` 仍 3.3.8）。是否随 ③ 一起走 3.3.9 发布批次？（此前挂着的问题：发 / 只补 `[Unreleased]` / 暂不动） |
| 2 | **经验静默回传 + 知识图谱同步**（DELIVER Step 2.8/2.9） | 属**外部写入**，按项目边界（执行权未下放）须 D哥 单独授权；且 `FSTDD-F` token 不可达可能使其降级 |
| 3 | **git push** | 三远端（origin / local / server）均未推；钩子镜像 `server` 可用，但 origin 直推仍受 443 阻断 |
