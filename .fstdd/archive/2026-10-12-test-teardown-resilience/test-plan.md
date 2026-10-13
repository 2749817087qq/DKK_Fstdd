# 测试收尾韧性 测试方案与详细案例

> 版本：change 2026-10-12-test-teardown-resilience
> 创建日期：2026-10-12
> 对应 Phase 2 Spec：`canonical/specs/code/test-teardown-resilience.yaml`（5 REQ / 7 SC）+ `canonical/specs/agent/2026-10-12-test-teardown-resilience.yaml`（7 CP）

## 一、测试策略

### 1.1 测试金字塔

- **单元级（主体）**：韧性层的包装行为（捕获/可见/反向守卫）可用 **monkeypatch 直接驱动**，不依赖环境是否恰好触发守卫 ⇒ 用例**确定可复现**，是本 change 的主要覆盖手段。
- **集成级**：`tests/test_verify_notices_default_safe.py` 整文件跑（验证「目录已存在」鲁棒性）。
- **E2E/会话级**：连续 3 次全量 `pytest tests` 比对 failed/errors 数（验证**可判性**这一最终目标）。
- **比例**：单元 7 : 集成 1 : 会话级 1（共 9 TC）。

### 1.2 测试原则

- **不依赖「环境恰好触发守卫」**：判据必须能用 monkeypatch 稳定复现（否则本 change 自身的门禁又变成不可判）。
- **双向断言**：每条「放行」都要配一条「不放行」（如 SC-001 放行 SystemExit ⇄ SC-003 真实异常照抛）。
- **可见性即判据**：捕获必须产生可断言的外部痕迹（warning / 汇总行），不得只测「没崩」。
- **不改 `upstream/`**：全部用例位于 `tests/`。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `tests/conftest.py` | 基线 163 行 → BUILD 后 **372 行**（非用例） | 夹具 | 已有 `pytest_configure` —— 本 change 的安装点 |
| `tests/test_verify_notices_default_safe.py` | 基线 6 → BUILD 后 **7** | 集成 | 受影响文件；L95 / L263 的 `d.mkdir()` 已加固为 `exist_ok=True`（TC-TTR-007） |
| `tests/`（全量） | 基线 204 passed / 6 skipped → BUILD 后 **230 passed / 6 skipped** | 会话级 | 确定性判据的基线（TC-TTR-008） |
| `tests/test_teardown_resilience_*.py`（4 个新增） | **25** | 单元 | 本 change 新增的韧性层/规避层判据（TC-TTR-001..006） |

## 二、详细测试案例

### 功能 1：韧性层（REQ-001）

#### 案例 1.1 — 被包装的删除原语遇 SystemExit 时降级为告警且不向上抛

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-001 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | conftest 的 `pytest_configure` 已包装**全部 6 个**删除入口：`os.remove` / `os.unlink` / `os.rmdir` / `shutil.rmtree` / `pathlib.Path.unlink` / `pathlib.Path.rmdir`（⚠️ 后三个为 BUILD 期实证扩容，见 ADJ-008） |
| **输入** | monkeypatch 让被包装的**原实现**抛出 `SystemExit(1)`，随后调用被包装的删除原语 |
| **预期结果** | 调用**不抛 SystemExit**；返回正常；且产生一条告警（见 TC-TTR-003） |
| **当前状态** | ✅ 已实现 —— `tests/test_teardown_resilience_capture.py`（**9 个用例**：包装面结构核对 ×2 + 纯函数 ×2 + 端到端 ×5，含**非 bypass 路径**的 `Path.unlink`/`Path.rmdir` 判别性判据） |

#### 案例 1.2 — 收尾步骤不被中断（后续步骤照常执行）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-002 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-001（AND） |
| **优先级** | P0 |
| **预置条件** | 同上；构造一个「两步收尾」序列（第 1 步删除、第 2 步置标记） |
| **输入** | 令第 1 步删除抛 `SystemExit` |
| **预期结果** | 第 2 步**仍被执行**（标记被置位）⇒ 证明收尾链未被中断 |
| **当前状态** | ✅ 已实现 —— `tests/test_teardown_resilience_capture.py::test_ttr_002_teardown_chain_not_interrupted` |

#### 案例 1.3 — 捕获可见：warning 含被捕获的删除目标路径

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-003 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 同 TC-TTR-001 |
| **输入** | 令删除抛 `SystemExit`，用 `pytest.warns` 或 `recwarn` 捕获 |
| **预期结果** | 存在一条 warning，其文本**包含被捕获的目标路径** |
| **当前状态** | ✅ 已实现 —— `tests/test_teardown_resilience_visibility.py::test_ttr_003_warning_contains_target_path` |

#### 案例 1.4 — 会话级汇总计数（不得静默）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-004 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-002（AND） |
| **优先级** | P1 |
| **预置条件** | 同 TC-TTR-001 |
| **输入** | 触发 N 次捕获后读取计数器 / 汇总输出 |
| **预期结果** | 计数 = N；汇总行含固定前缀（如 `[teardown-resilience]`） |
| **当前状态** | ✅ 已实现 —— `tests/test_teardown_resilience_visibility.py`（**6 个用例**：计数与记录内容 + **自测隔离接线**（ADJ-011）+ **会话汇总输出**（静默/列出/截断/无 reporter 退化，ADJ-012）） |

#### 案例 1.5 — 反向守卫：真实异常照抛（不得宽捕获）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-005 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 同 TC-TTR-001 |
| **输入** | monkeypatch 让原实现抛 `PermissionError`（非 SystemExit） |
| **预期结果** | 调用**抛出 PermissionError**（不被吞）；同时断言 conftest 源码**不含** `except Exception` / `except BaseException` / 裸 `except:` |
| **当前状态** | ✅ 已实现 —— `tests/test_teardown_resilience_real_exception.py`（**3 个用例**：`PermissionError` / `KeyboardInterrupt` 照抛 + **剥注释后**的源码级结构断言） |

### 功能 2：规避层（REQ-002）

#### 案例 2.1 — TMP/TEMP 指向仓库外中立目录且可写

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-006 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | pytest 会话已启动（`pytest_configure` 已执行） |
| **输入** | 在用例内读取 `os.environ["TMP"]` / `["TEMP"]` / `["TMPDIR"]` |
| **预期结果** | 三者均指向**仓库之外**的目录；该目录 `is_dir()` 且可写（写探针文件成功） |
| **当前状态** | ✅ 已实现 —— `tests/test_teardown_resilience_tmp_neutral.py`（**5 个用例**：设置齐备 / 仓外 / 三者一致 / **停在 shim bypass 根**（核心不变式，见 ADJ-008）/ 可写） |

### 功能 3：症状末端加固（REQ-003）

#### 案例 3.1 — 目标目录已存在时不抛 FileExistsError

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-007 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | `tests/test_verify_notices_default_safe.py` 的 L95 / L263 已改为 `d.mkdir(exist_ok=True)` |
| **输入** | 预先在 `tmp_path` 下创建 `notices` 目录，再运行该文件的用例 |
| **预期结果** | 不抛 `FileExistsError`；用例按其原有断言继续执行 |
| **当前状态** | ✅ 已实现 —— `tests/test_verify_notices_default_safe.py::test_tc_qis_003c_mkdir_tolerates_preexisting_dir`（预置 `notices/` 已存在）+ L95 / L263 两处 `mkdir(exist_ok=True)` |

### 功能 4：可判性（REQ-004）

#### 案例 4.1 — 连续 3 次全量 failed/errors 数一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-008 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | 守卫未触发 |
| **输入** | 连续 3 次 `pytest tests -q -p no:cacheprovider --basetemp=<每次全新>` |
| **预期结果** | 3 次的 `failed` 与 `errors` 数**完全一致**；且均为 0 |
| **当前状态** | ✅ 已执行（Part C，会话级）—— 证据落 `test-report.md` §四（**不落代码**：跑全量套件不能作为套件内用例） |

### 功能 5：范围边界（REQ-005）

#### 案例 5.1 — 未触碰 upstream/

| 字段 | 内容 |
|------|------|
| **ID** | TC-TTR-009 |
| **对应 Spec** | test-teardown-resilience/spec.yaml → Scenario: SC-007 |
| **优先级** | P0 |
| **预置条件** | 本 change 全部改动完成 |
| **输入** | `git diff --name-only`（相对本 change 起点） |
| **预期结果** | 输出**不含** `upstream/` 前缀的任何文件；改动仅限 `tests/` 与 change 目录 |
| **当前状态** | ✅ 已执行（Part C，边界级）—— 证据落 `test-report.md` §四（**不落代码**：判据依赖交付时的 git 状态） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E/会话级 | 状态 |
|----------|---------|----------|-----------|------|
| 韧性层（捕获/可见/反向） | TC-TTR-001/002/003/004/005 | — | — | ✅ **20 个用例全绿**（capture 10 / visibility 7 / real_exception 3；含 5 个端到端） |
| 规避层（TMP/TEMP） | TC-TTR-006 | — | — | ✅ **5 个用例全绿** |
| 症状末端加固 | — | TC-TTR-007 | — | ✅ **1 个用例全绿**（+ 2 处 `mkdir(exist_ok=True)` 加固） |
| 可判性 | — | — | TC-TTR-008 | ✅ 已执行（3 次全量 failed/errors 一致，见 test-report §四） |
| 范围边界 | — | TC-TTR-009 | — | ✅ 已执行（改动不含 `upstream/`，见 test-report §四） |

## 四、回归风险矩阵

| 风险区域 | 本 change 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| `tests/conftest.py` | 新增 `pytest_configure` 内的包装与环境变量设置 | 全量 `pytest tests`（基线 204 → 现 **230 用例**）逐项对比 failed/errors | 🟡 中（面状影响全部根级测试） |
| `tests/test_verify_notices_default_safe.py` | 2 处 `d.mkdir()` → `exist_ok=True` | 该文件自身 6 → **7** 用例 | 🟢 低 |
| 测试进程的 `TMP/TEMP` | 归一到仓库外中立临时根 | 全量跑（若有测试依赖默认 TMP 会暴露） | 🟡 中 |
| `upstream/` | **不改动** | `git diff --name-only` 白名单核对（TC-TTR-009） | 🟢 低 |
| 框架 `experience.py` 的 lock 释放（根因②） | **不改动**（仅被 D2 的包装在行为上兜住） | 框架侧测试（`upstream/tests/`） | 🟡 中（语义欠账登记，见 design D5） |

## 五、建议补充顺序

1. **第一优先（部署前必补，P0）**：TC-TTR-001、TC-TTR-002、TC-TTR-003、TC-TTR-005、TC-TTR-006、TC-TTR-007、TC-TTR-008、TC-TTR-009
2. **第二优先（随后尽快补，P1）**：TC-TTR-004
3. **第三优先（回归即可，P2）**：全量 `pytest tests` 与 `upstream/tests/` 的确定性复跑

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 同命令不同失败数（主理人 5 failed/1 error vs 门神 4 failed/17 errors） | 2026-10-12T13:32:56+00:00 | 34f11b50a22725af2ad45f2b7663fa535f332b66 | 闭合度验证（`deliverables/gstack/closure-verification-share-hardening-2026-10-12.md`） |
| 守卫未触发时确定：连跑 2 次均 `204 passed, 6 skipped` | 2026-10-12T13:32:56+00:00 | 34f11b50a22725af2ad45f2b7663fa535f332b66 | `pytest tests -q --basetemp=<每次全新>` |
| shim 的 SystemExit 位置 `sitecustomize.py:848`；`_index_lock` 释放点 `experience.py:241` | 2026-10-12T14:0x+00:00 | 34f11b50a22725af2ad45f2b7663fa535f332b66 | 只读源码核对 |
| EXP-2026-0029（同根因已记录，source=2026-10-11-experience-center-node-sync） | 2026-10-11（首次）/ 2026-10-12（复核） | 34f11b50a22725af2ad45f2b7663fa535f332b66 | `.fstdd/experiences/EXP-2026-0029.md` |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖

> 由 understand.md Step 0.5 判定：**FINANCIAL_PROJECT=NO** ⇒ 本章节跳过。
