# v3.0.7 测试方案与详细案例 — change-isolation（隔离形态可选且可见）

> 版本：v3.0.7（拟）
> 创建日期：2026-09-26
> 对应 Phase 2 Spec：`canonical/specs/code/2026-09-25-new-isolate-flag.yaml`（REQ-001..009 / SC-001..020）
> 　　　　　　　　　`canonical/specs/agent/2026-09-25-new-isolate-flag.yaml`（端到端验证）
> base_git_sha：`4eec636`

> **格式说明**：案例采用模板规定的**字段式**（`| **ID** | TC-… |`），而非横向汇总表。
> 原因是 `stdd validate` 按 `\*\*ID\*\*\s*\|` 统计 TC 案例数并要求
> `TC 案例数 ≥ Spec Scenario 数`（`upstream/fstdd/cli/commands/validate.py:92-96`）。
> 横向表无法被该模式识别，会直接判 `验证失败`。

## 一、测试策略

### 1.1 测试金字塔

| 层 | 占比 | 本 change 的落点 |
|---|---|---|
| 单元 | ~70% | 参数解析与取值校验、隔离形态解析（含 config 回落）、分支名构造、路径构造、脏树判定、配置 `setdefault` 幂等、死代码已移除的静态断言 |
| 集成 | ~20% | 真 `subprocess` 调 `git`：在**临时沙箱仓**里建 worktree / 切分支，断言端状态（`git worktree list`、`git branch --show-current`、`git status --porcelain`） |
| E2E | ~10% | `canonical/specs/agent/*.yaml` 定义的双 worktree 互不干扰验证（真 CLI + 真 git，须在 BUILD 阶段单独执行并留证） |

**为什么单元层占大头**：本 change 的失败模式集中在「该拒绝时没拒绝」「该回退时回退错方向」「路径算错」，三者都是纯函数级可判定的；真 git 操作只在少数几个用例里必要，且必须放在**沙箱仓**——不能拿 stdd-repo 当试验场，它会污染本仓库，且与 `test_a6_d_repo_worktree_clean`（断言工作区干净）直接冲突。

### 1.2 测试原则

- **零漂移优先**：`stdd new x`（无 `--isolate`、无 config）必须先有「行为与改动前一致」的断言（TC-ISO-002），再谈新功能。
- **断言端状态，不断言回显**：worktree/分支是否真的建出来，一律查 `git worktree list` / `git branch --show-current`，不靠 CLI 的 stdout 文本。
- **失败路径必查副作用**：每个失败用例除断言退出码，还要断言 `.fstdd/changes/<dir>` **不存在**（SC-006/007/008 的核心）。
- **沙箱隔离**：所有涉 git 用例在 `tmp_path` 内 `git init`，`monkeypatch.chdir` 进去；禁止在 stdd-repo 内创建 worktree。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/commands/test_new.py` | 11 | 单元 | change 命名校验、日期前缀幂等、dry-run、脚手架落盘 |
| `upstream/tests/commands/test_init.py` | 3 | 单元 | init 目录创建与配置复制 |
| `upstream/tests/commands/test_guard.py` | 51 | 单元+集成 | Guard 判定链（含 W5 新增 scope 12 例） |
| `upstream/tests/commands/test_canon.py` | 9 | 单元 | canonical 双轨生成与校验 |
| `upstream/tests/test_guard_silent_except.py`、`upstream/tests/test_except_audit.py` | 2 文件 | 哨兵 | 吞异常零漂移（配合 `tools/audit_silent_except.py --check`） |

> 全仓 `upstream/tests` 现有 **789** 个 `test_` 函数，分布于 38 个 `commands/` 文件 + 根级文件。
>
> **BUILD 调整（2026-09-26，Slice 7）**：原 `upstream/tests/commands/test_new_coverage.py`
> （2 例，`TC-PAR-001`，V2.8 `--parallel` 专属）已随该死代码一并**删除** ——
> 被测功能不复存在，留着是误导；其 dry-run 覆盖由 `test_new.py::test_new_dry_run` 承担。
> 故 TC-ISO-021 的既有回归例数由 16 降为 **14**（`test_new.py` 11 + `test_init.py` 3）。

## 二、详细测试案例

### 功能 1：隔离形态解析（REQ-001 / REQ-007）

#### 案例 1.1 — worktree 形态建出真 worktree，骨架落在 worktree 内

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-001 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 沙箱 git 仓（含 1 次提交）+ 已 `init` |
| **输入** | `new x --isolate worktree` |
| **预期结果** | exit 0；`git worktree list` 出现第 2 条；分支名 `fstdd/<dir>`；骨架落在 worktree 内；**主仓 `.fstdd/changes/` 不含该 dir** |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 无 --isolate 且无配置时零漂移

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-002 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-002 |
| **优先级** | P0（**本 change 的成败线**） |
| **预置条件** | 沙箱 git 仓，`project.yaml` 无 `isolation` 块 |
| **输入** | `new x`（不带 `--isolate`） |
| **预期结果** | exit 0；主仓建骨架；`git worktree list` 仍 1 条；`git branch --list` 无新增 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.3 — --help 暴露三取值

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-003 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-003 |
| **优先级** | P1 |
| **预置条件** | 任意目录 |
| **输入** | `new --help` |
| **预期结果** | stdout 含 `--isolate` 与 `none`/`worktree`/`branch` 三取值 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.4 — 配置默认值被消费

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-015 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-015 |
| **优先级** | P0 |
| **预置条件** | `project.yaml` 配置 `isolation.default: worktree` |
| **输入** | `new x`（不带 `--isolate`） |
| **预期结果** | 按 worktree 形态创建（`git worktree list` 出现第 2 条） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.5 — 配置读取失败一律回落 none

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-016 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-016 |
| **优先级** | P0 |
| **预置条件** | 三种坏输入分别测：① `project.yaml` 缺失 ② YAML 非法 ③ `isolation.default: banana` |
| **输入** | `new x` |
| **预期结果** | 三种情况均回落 `none`：exit 0 + 正常建骨架，无 worktree、**不抛异常** |
| **当前状态** | ❌ 测试缺 |

### 功能 2：分支命名（REQ-002）

#### 案例 2.1 — worktree 分支名由规则构造，非路径派生

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-004 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | 沙箱 git 仓，分支 `fstdd/<dir>` 不存在 |
| **输入** | `new x --isolate worktree` |
| **预期结果** | 分支名精确等于 `<branch_prefix><change_dir_name>`；**不含** `-explore`/`-research` 等路径派生后缀 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — branch 形态切分支且不建 worktree

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-005 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | 沙箱 git 仓，`git status --porcelain` 为空 |
| **输入** | `new x --isolate branch` |
| **预期结果** | `git branch --show-current` == `fstdd/<dir>`；`git worktree list` 仍 1 条 |
| **当前状态** | ❌ 测试缺 |

### 功能 3：不静默降级 + 不留半成品（REQ-003）

#### 案例 3.1 — 非 git 仓拒绝且不建目录

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-006 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | `tmp_path` 内**无** `.git` |
| **输入** | `new x --isolate worktree` |
| **预期结果** | exit ≠ 0；输出说明「不在 git 工作树内」；**`.fstdd/changes/<dir>` 不存在** |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — 脏工作区拒绝 branch 形态

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-007 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-007 |
| **优先级** | P0 |
| **预置条件** | 沙箱 git 仓 + 1 个**未跟踪**文件 |
| **输入** | `new x --isolate branch` |
| **预期结果** | exit ≠ 0；提示改用 `--isolate worktree`；`git branch --show-current` **未变化** |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.3 — 冲突预检且不自行删除

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-008 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-008 |
| **优先级** | P0 |
| **预置条件** | 两个子场景：① 分支 `fstdd/<dir>` 已存在 ② worktree 目标路径已存在（内含哨兵文件） |
| **输入** | `new x --isolate worktree` |
| **预期结果** | 均 exit ≠ 0 且输出清理命令；① 既有分支未被改动 ② **既有路径及其哨兵文件仍在**（未被删除） |
| **当前状态** | ❌ 测试缺 |

### 功能 4：worktree 位置（REQ-004）

#### 案例 4.1 — 默认落在项目根之外

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-009 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-009 |
| **优先级** | P0 |
| **预置条件** | 沙箱 git 仓，无 `worktree_root` 配置 |
| **输入** | `new x --isolate worktree` |
| **预期结果** | worktree 路径的父目录 = 项目根的**父目录**；主仓 `git status --porcelain` 为空（未被污染） |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — 配置覆盖 worktree 位置

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-010 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-010 |
| **优先级** | P1 |
| **预置条件** | `project.yaml` 配置 `isolation.worktree_root: <tmp>/wt` |
| **输入** | `new x --isolate worktree` |
| **预期结果** | worktree 落在 `<tmp>/wt/<dir>` |
| **当前状态** | ❌ 测试缺 |

### 功能 5：提示可见且不阻塞（REQ-005）

#### 案例 5.1 — 收尾输出隔离提示行

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-011 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-011 |
| **优先级** | P1 |
| **预置条件** | 沙箱 git 仓 |
| **输入** | 分别执行 `new x` 与 `new y --isolate worktree` |
| **预期结果** | 两种形态的 stdout 均含隔离提示行，且分别指明当前形态 |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.2 — 全程不调用 input()

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-012 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-012 |
| **优先级** | P1 |
| **预置条件** | `monkeypatch` 把 `builtins.input` 替换为抛异常的函数 |
| **输入** | `new x` |
| **预期结果** | 全程不触发 `input()`，exit 0 |
| **当前状态** | ❌ 测试缺 |

### 功能 6：init 配置写入（REQ-006）

#### 案例 6.1 — init 写入 isolation 块

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-013 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-013 |
| **优先级** | P0 |
| **预置条件** | 空项目目录 |
| **输入** | `init` |
| **预期结果** | `.fstdd/config.d/project.yaml` 含 `isolation` 块及 `default`/`worktree_root`/`branch_prefix` 三键 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.2 — 既有取值与用户自定义键均保留，且幂等

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-014 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-014 |
| **优先级** | P0 |
| **预置条件** | `project.yaml` 已有 `isolation.default: branch` 与用户键 `project.name: myproj` |
| **输入** | `init`，随后再 `init` 一次 |
| **预期结果** | `isolation.default` **仍为 `branch`**（未被覆盖为 none）；`project.name` 原样保留；第二次 `init` 后文件内容与第一次逐字节相同（幂等） |
| **当前状态** | ❌ 测试缺 |

### 功能 7：死代码移除（REQ-008）

#### 案例 7.1 — parallel 相关代码零残留

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-017 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-017 |
| **优先级** | P1 |
| **预置条件** | 改动后代码库 |
| **输入** | 静态检索 `upstream/fstdd/` 下 `parallel` 与 `_setup_parallel_worktrees` |
| **预期结果** | 0 命中；`new.py` 不再定义或调用该函数 |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.2 — CHANGELOG 留痕

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-018 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-018 |
| **优先级** | P2 |
| **预置条件** | 改动后仓库 |
| **输入** | 读 `CHANGELOG.md` |
| **预期结果** | 含 `--parallel` 移除条目及原因 |
| **当前状态** | ❌ 测试缺 |

### 功能 8：worktree 内门禁保持有效（REQ-009，**SPEC 阶段新增**）

#### 案例 8.1 — hook 注册随 worktree 复制

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-019 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-019 |
| **优先级** | P0 |
| **预置条件** | 主工作区含 `.claude/settings.local.json`（其中含 `guard check` hook） |
| **输入** | `new x --isolate worktree` |
| **预期结果** | worktree 内存在同名文件且内容与主工作区一致 |
| **当前状态** | ❌ 测试缺 |

#### 案例 8.2 — 无 hook 注册时出声告警

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-020 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-020 |
| **优先级** | P0 |
| **预置条件** | 主工作区**无**任何 hook 注册文件 |
| **输入** | `new x --isolate worktree` |
| **预期结果** | stdout 含明确告警（说明该 worktree 内门禁未激活），exit 仍为 0 |
| **当前状态** | ❌ 测试缺 |

### 回归义务（非新增功能）

#### 案例 9.1 — new/init 既有用例全绿

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-021 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 改动后仓库 |
| **输入** | 跑 `test_new.py` / `test_init.py` |
| **预期结果** | 全绿（14 例），证明默认路径零漂移 |
| **当前状态** | ❌ 待跑 |

#### 案例 9.2 — 吞异常零漂移哨兵通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-022 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-017 |
| **优先级** | P0 |
| **预置条件** | 改动后仓库（删除函数会使其后行号前移） |
| **输入** | `tools/audit_silent_except.py --check` + `test_guard_silent_except.py` |
| **预期结果** | 哨兵通过；若行号漂移超 ±5 容差则刷新 `except-points.yaml` 后复验 |
| **当前状态** | ❌ 待跑 |

#### 案例 9.3 — Guard 判定链未被波及

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISO-023 |
| **对应 Spec** | `change-isolation/spec.md` → Scenario: SC-019 |
| **优先级** | P1 |
| **预置条件** | 改动后仓库 |
| **输入** | 跑 `test_guard.py` |
| **预期结果** | 51 例全绿（本 change 不触碰 Guard 判定链） |
| **当前状态** | ❌ 待跑 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 隔离形态解析 / config 回落 | ✅ TC-ISO-001..003, 015, 016 | ⬜ | ⬜ | 🔴 待补 |
| 分支命名 | ✅ TC-ISO-004, 005 | ✅ 真 git 断言 | ⬜ | 🔴 待补 |
| 失败路径无副作用 | ✅ TC-ISO-006..008 | ✅ 真 git 断言 | ⬜ | 🔴 待补 |
| worktree 位置 | ✅ TC-ISO-009, 010 | ✅ `git status` 断言 | ⬜ | 🔴 待补 |
| 提示可见性 | ✅ TC-ISO-011, 012 | ⬜ | ⬜ | 🔴 待补 |
| init 配置幂等 | ✅ TC-ISO-013, 014 | ⬜ | ⬜ | 🔴 待补 |
| 死代码移除 | ✅ TC-ISO-017, 018 | ⬜ | ⬜ | 🔴 待补 |
| worktree 内门禁 | ✅ TC-ISO-019, 020 | ✅ 文件一致性断言 | ⬜ | 🔴 待补 |
| 双 worktree 互不干扰 | ⬜ | ⬜ | ✅ agent_spec | 🔴 待补（E2E） |

## 四、回归风险矩阵

| 风险区域 | v3.0.7 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| `stdd new` 默认行为 | 新增 `--isolate`（默认 None→config→none）；脚手架目标根改为变量 | `test_new.py`(11) + TC-ISO-002/021 | 🟡 中（默认路径被改动，必须有零漂移断言） |
| `canon init` 签名 | 新增可选 `project_root`（向后兼容） | `test_canon.py`(9) + TC-ISO-001 | 🟢 低（不传时行为不变） |
| `stdd init` 配置写入 | 新增 `_post_init_isolation` 写 project.yaml | `test_init.py`(3) + TC-ISO-014 | 🟡 中（写用户文件，幂等与非覆盖是硬要求） |
| Guard 判定链 | **不改** | `test_guard.py`(51) + 哨兵 | 🟢 低 |
| 吞异常零漂移 | 删除函数 ⇒ `new.py` 行号前移 | `tools/audit_silent_except.py --check` + 哨兵测试 | 🟡 中（行号漂移 ±5 容差，见 TC-ISO-022） |
| 仓库整洁度 | worktree 默认建在项目根之外 | `test_a6_d_repo_worktree_clean` | 🟢 低（默认值刻意避开仓内） |

## 五、建议补充顺序

1. **第一优先（BUILD 前段，先红后绿）**：TC-ISO-002（零漂移）、TC-ISO-001、TC-ISO-006、TC-ISO-007、TC-ISO-009 —— 覆盖「默认不变」「worktree 真建出来」「失败不留半成品」「不污染主仓」，是本 change 的成败线。
2. **第二优先（BUILD 后段）**：TC-ISO-003..005、008、010..014、019、020。
3. **第三优先（DELIVER 前）**：TC-ISO-017/018（死代码与 CHANGELOG）、TC-ISO-021..023（回归）、agent_spec 端到端。
4. **E2E 单独执行**：双 worktree 互不干扰必须在 BUILD 阶段以真 CLI + 真 git 单独跑一次并留证，不得用单测结论替代。

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| `stdd new --parallel` 不可达：`error: unrecognized arguments: --parallel` | 2026-09-25T12:20:00+08:00 | `f0af9e8` | proposal `why.evidence`；本次复核注册点 `cli/__init__.py:126-130` 确无 `--parallel` |
| `grep -rn parallel upstream/fstdd/` 仅 4 处命中（1 调用点 + 1 定义 + 2 docstring） | 2026-09-26T00:52+08:00 | `4eec636` | 本次实测（Bash grep） |
| `git worktree list` 仅主工作区一条 ⇒ 隔离从未被使用 | 2026-09-25T12:20:00+08:00 | `f0af9e8` | proposal `why.evidence` |
| Guard 对项目外路径**放行**（exit 0） | 2026-09-26T00:55+08:00 | `4eec636` | 代码阅读 `guard.py:822-827` |
| `guard.exempt_paths` 按**目录名**祖先匹配（钝器，不适合用于仓内 worktree 根） | 2026-09-26T00:55+08:00 | `4eec636` | 代码阅读 `guard.py:386-400` |
| `canon.py` 的 `project_root = Path.cwd()`（cwd 绑定） | 2026-09-26T00:55+08:00 | `4eec636` | 代码阅读 `canon.py:113` |
| `canon verify` 双轨校验 **2/2 通过**（DC-HASH 源哈希一致 / DC-FIELD 字段引用完整） | 2026-09-26T00:56+08:00 | `4eec636` | `stdd canon verify 2026-09-25-new-isolate-flag` |
| `stdd validate` 首跑 **1 error + 1 warning**（TC 案例数 0 < Scenario 20；`specs/code/spec.md` 未找到 Scenario） | 2026-09-26T00:57+08:00 | `4eec636` | `stdd validate` 输出；根因见 `validate.py:92-96` 与 `:48-54` |
| 改动前全量基线：**1 failed / 775 passed / 1064.00s**，唯一失败 `test_a6_d_repo_worktree_clean` | 2026-09-26T00:41+08:00 | `4eec636` | `.workbuddy-ai/tmp/pytest_full.log` |
| ⚠️ 上一条基线**不可采信**：该轮跑在被打补丁脚本截断的 `test_guard.py` 上（26 例缺失） | 2026-09-26T00:44+08:00 | `4eec636` | 见 `2026-09-26.md` 日志「自伤事故」节 |
| 有效全量基线（重跑中，待回填） | _待回填_ | `4eec636` | `.workbuddy-ai/tmp/pytest_full2.log` |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。
