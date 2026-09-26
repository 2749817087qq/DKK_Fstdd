# 3.1.0 测试方案与详细案例 —— change 目录解析增归档回退

> 版本：3.1.0（change `2026-09-26-finder-archive-fallback`）
> 创建日期：2026-09-26
> 对应 Phase 2 Spec：`canonical/specs/code/2026-09-26-finder-archive-fallback.yaml`
> （capability `change-dir-resolution`；REQ-001 ~ REQ-003，SC-001 ~ SC-013）
> 技术设计：`design.md`（5 条 Decision + 调用点 → 语义 → include_archive 对照表）

## 一、测试策略

### 1.1 测试金字塔

| 层级 | 占比 | 本 change 侧重 |
|------|------|----------------|
| 单元 | 约 6 成 | `find_change_dir` 的解析顺序与开关语义（SC-001~006）—— 6 例全部直调函数，不启子进程 |
| 集成 | 约 4 成 | 四条命令归档后可用 + 两条零漂移反例（SC-007~013）—— 以 CLI 子进程跑真实命令 |
| E2E | 无 | 本 change 不涉及用户可见流程，集成层已覆盖全部行为面 |

**为什么单元层要占大头**：本 change 的根因是「**四个各自独立的解析器**」。集中到一处后，
正确性可由函数级穷举穷尽（名字精确/后缀/缺 `.fstdd.yaml`/同名/无 archive/None），
不必每个调用点各跑一遍。

### 1.2 测试原则

- **默认零漂移必须被反例锚定**，不能只测新功能 —— `include_archive` 默认 `False` 若被改成 `True`，
  `stdd archive` 会把已归档目录**再移动一次**（数据丢失）。SC-011 是专门为此设的反例。
- **不破坏既有独立逻辑**：`rollback.py` 有自己的 `archive/` 搜索（`archive/` + `archive/aborted/`），
  本次不改它；SC-012 锚定其既有行为不回归。
- **测试资产零污染**：新用例一律在 `tmp_path` / `mkdtemp` 下自建 `.fstdd/` 骨架，
  不依赖仓库自身的 `.fstdd/changes/` 内容（否则会随仓库归档状态而红）。
- **接口签名即契约**：`include_archive` 必须是**仅关键字参数**（`*` 之后），
  避免既有位置调用被静默改义 —— 由 SC-001 的调用形态间接锚定。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/test_finder.py` | 8 | 单元 | `find_change_dir` 精确/后缀/无匹配/None/缺 `.fstdd.yaml` |
| `upstream/tests/commands/test_archive.py` | 4 | 集成 | `stdd archive` 归档行为 |
| `upstream/tests/commands/test_rollback.py` | 5 | 集成 | `stdd rollback` 归档恢复 |
| `upstream/tests/commands/test_canon.py` | 9 | 集成 | `canon generate / verify` |
| `upstream/tests/commands/test_structure.py` | 9 | 集成 | `structure delta / merge` |
| `upstream/tests/commands/test_validate.py` | 8 | 集成 | `stdd validate` |
| `upstream/tests/commands/test_status.py` | 4 | 集成 | `stdd status` |
| `upstream/tests/commands/test_changes_dir_consistency.py` | 8 | 门禁 | 路径漂移防漂移（**本 change 新增代码须过此门禁**） |

> 新增用例建议落在 `upstream/tests/commands/test_finder_archive_fallback.py`
> （集成）+ 追加至 `upstream/tests/test_finder.py`（单元），共 13 例。

## 二、详细测试案例

### 功能 1：change 目录统一解析（REQ-001）

> 对应 `change-dir-resolution/spec.md` → REQ-001「支持可选归档回退，且默认行为零漂移」。
> 全部为**单元**层：直调 `fstdd.cli.finder.find_change_dir`。

#### 案例 1.1 — 默认不传 include_archive 时归档件不可见

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-001 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-001（默认语义零漂移） |
| **优先级** | P0 |
| **预置条件** | GIVEN：临时根下建 `.fstdd/archive/2026-01-01-archived-only/` 且含 `.fstdd.yaml`；**不建** `.fstdd/changes/` 下任何同名目录 |
| **输入** | WHEN：`find_change_dir("archived-only", root)`（**不传** `include_archive`） |
| **预期结果** | THEN：返回 `None` —— 默认仍是「只查在办」；AND：`.fstdd/archive/` 未被创建/修改（`st_mtime` 不变） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-001` |

#### 案例 1.2 — 显式开启后归档件可被解析

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-002 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-002（归档回退命中） |
| **优先级** | P0 |
| **预置条件** | GIVEN：`.fstdd/archive/2026-01-01-archived-only/` 存在且含 `.fstdd.yaml`；`changes/` 下无该件 |
| **输入** | WHEN：`find_change_dir("archived-only", root, include_archive=True)` |
| **预期结果** | THEN：返回 `.fstdd/archive/2026-01-01-archived-only`；AND：`(result / ".fstdd.yaml").exists()` 为真；AND：返回值 `is_relative_to(root)` |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-002` |

#### 案例 1.3 — changes/ 与 archive/ 同名时在办优先

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-003 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-003（在办优先于归档） |
| **优先级** | P0 |
| **预置条件** | GIVEN：`.fstdd/changes/2026-01-01-dup/` 与 `.fstdd/archive/2026-01-01-dup/` **同时**存在，各自含 `.fstdd.yaml` |
| **输入** | WHEN：`find_change_dir("dup", root, include_archive=True)` |
| **预期结果** | THEN：返回 `.fstdd/changes/2026-01-01-dup`；AND：`".fstdd/archive" not in str(result)`（不得误取归档副本） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-003` |

#### 案例 1.4 — 后缀匹配在归档区同样生效

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-004 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-004（归档区后缀匹配） |
| **优先级** | P1 |
| **预置条件** | GIVEN：`.fstdd/archive/2026-01-01-archived-feature/` 含 `.fstdd.yaml`；`changes/` 下无 |
| **输入** | WHEN：`find_change_dir("archived-feature", root, include_archive=True)`（短名，省略日期前缀） |
| **预期结果** | THEN：命中 `archive/2026-01-01-archived-feature`；AND：与 `changes/` 分支使用同一后缀匹配规则（`d.name.endswith(name)`） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-004` |

#### 案例 1.5 — 不指定名字时恒只查在办

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-005 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-005（「当前 change」不可能在归档区） |
| **优先级** | P0 |
| **预置条件** | GIVEN：`changes/` 与 `archive/` 下都有含 `.fstdd.yaml` 的 change，且**强制 `archive/` 内那个 `st_mtime` 更新** |
| **输入** | WHEN：`find_change_dir(None, root, include_archive=True)` |
| **预期结果** | THEN：只返回 `changes/` 下最近修改的那个；AND：`".fstdd/archive" not in str(result)` —— `include_archive` **不影响** `name=None` 分支 |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-005` |

#### 案例 1.6 — 无 archive/ 目录时不抛异常

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-006 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-006（缺目录容错） |
| **优先级** | P1 |
| **预置条件** | GIVEN：临时根下只有 `.fstdd/changes/`，**完全没有** `.fstdd/archive/` |
| **输入** | WHEN：`find_change_dir("whatever", root, include_archive=True)` |
| **预期结果** | THEN：正常返回或返回 `None`，**不得抛 `FileNotFoundError` / `StopIteration`**；AND：`.fstdd/archive/` **不被创建**（查询不产生副作用） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-006` |

### 功能 2：归档后四条命令仍可用（REQ-002）

> 对应 REQ-002。全部为**集成**层：以子进程跑真实 CLI，cwd = 临时项目根。
> 共同预置：把 `changes/<name>/` 整体 `shutil.move` 到 `archive/<name>/`，
> 并保留其 `canonical/` 与 `code-structure-delta.md`（与 `stdd archive` 的实际效果一致）。

#### 案例 2.1 — validate 归档后可用

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-007 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-007（validate 归档后 rc=0） |
| **优先级** | P0 |
| **预置条件** | GIVEN：change 已归档至 `.fstdd/archive/<name>/`，`changes/` 下已无该目录 |
| **输入** | WHEN：`stdd validate <name>` |
| **预期结果** | THEN：`returncode == 0`；AND：stdout 不含「找不到 change」；AND：校验项正常输出（修复前 rc=1） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-007` |

#### 案例 2.2 — status 归档后可用

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-008 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-008（status 归档后 rc=0） |
| **优先级** | P0 |
| **预置条件** | GIVEN：change 已归档，`.fstdd.yaml` 内 `status: archived` |
| **输入** | WHEN：`stdd status <name>` |
| **预期结果** | THEN：`returncode == 0`；AND：stdout 含该 change 名与归档态信息（修复前 rc=1） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-008` |

#### 案例 2.3 — canon verify 归档后可用

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-009 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-009（canon verify 归档后 rc=0） |
| **优先级** | P0 |
| **预置条件** | GIVEN：change 已归档，其 `canonical/proposals/<name>.yaml` 完整（源哈希与字段引用均一致） |
| **输入** | WHEN：`stdd canon verify <name>` |
| **预期结果** | THEN：`returncode == 0`；AND：stdout 出现通过项（修复前 rc=1「canonical/proposals/... not found」）—— **本 case 是「只改 finder 不够」的直接证据**：`_get_canon_dir` 不走 finder |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-009` |

#### 案例 2.4 — structure merge 归档后读到 delta

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-010 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-010（structure merge 归档后不报 Delta not found） |
| **优先级** | P1 |
| **预置条件** | GIVEN：change 已归档，其 `code-structure-delta.md` 存在 |
| **输入** | WHEN：`stdd structure merge <name>` |
| **预期结果** | THEN：`returncode == 0`；AND：stdout **不含**「Delta not found」；AND：delta 被复制进 `code-structure/deltas/<name>.md`（修复前 rc=1） |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-010` |

### 功能 3：归档相关既有行为零漂移（REQ-003）

> 对应 REQ-003 —— 三个**反例/回归守卫**。这是本 change 最容易被改坏的部分：
> 一旦把 `include_archive` 默认值写成 `True`，案例 3.1 立即变红。

#### 案例 3.1 — 二次 archive 不得自我移动

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-011 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-011（archive 不解析 archive/） |
| **优先级** | P0 |
| **预置条件** | GIVEN：change 已归档至 `archive/<name>/`，`changes/` 下已无该目录；记录 `archive/<name>/` 的 `st_mtime` 与 inode |
| **输入** | WHEN：**再次**执行 `stdd archive <name>` |
| **预期结果** | THEN：`returncode != 0` 且报「找不到 change」；AND：`archive/<name>/` **原地未动**（`st_mtime` 与 inode 均未变，目录未丢失）—— 证明 `archive.py:16` 仍用默认 `include_archive=False` |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-011` |

#### 案例 3.2 — rollback 既有 archive 恢复逻辑不回归

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-012 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-012（rollback 恢复不回归） |
| **优先级** | P0 |
| **预置条件** | GIVEN：change 已归档至 `archive/<name>/`（含 `.fstdd.yaml`） |
| **输入** | WHEN：`stdd rollback <name>` |
| **预期结果** | THEN：`returncode == 0`；AND：目录已回到 `.fstdd/changes/<name>/`；AND：`archive/<name>/` 不再存在 —— **本 change 不改 `rollback.py`**，其独立 archive 搜索（`archive/` + `archive/aborted/`）须逐字保留 |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-012`（既有 test_rollback.py 5 例 + 本次补「归档后恢复」路径） |

#### 案例 3.3 — 未归档 change 正常归档（既有行为）

| 字段 | 内容 |
|------|------|
| **ID** | TC-FAF-013 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-013（archive 正向不回归） |
| **优先级** | P1 |
| **预置条件** | GIVEN：change 位于 `.fstdd/changes/<name>/`，未归档 |
| **输入** | WHEN：`stdd archive <name>` |
| **预期结果** | THEN：`returncode == 0`；AND：目录出现在 `.fstdd/archive/<name>/`；AND：`changes/<name>/` 不再存在；AND：`.fstdd.yaml` 内 `status == "archived"` |
| **当前状态** | ✅ 已覆盖 → `TC-FAF-013`（既有 test_archive.py 4 例，作为回归基线） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| `finder.find_change_dir` | TC-FAF-001~006 | — | — | 🔴 待实现（新参数） |
| `validate` | — | TC-FAF-007 | — | 🔴 待实现 |
| `status` | — | TC-FAF-008 | — | 🔴 待实现 |
| `canon verify` | — | TC-FAF-009 | — | 🔴 待实现（需同时改 `_get_canon_dir`） |
| `structure merge` | — | TC-FAF-010 | — | 🔴 待实现 |
| `archive`（反例） | — | TC-FAF-011 / 013 | — | 🟡 013 已覆盖，011 待补 |
| `rollback`（回归） | — | TC-FAF-012 | — | 🟡 部分覆盖，需补归档路径 |

## 四、回归风险矩阵

| 风险区域 | V3.1.0 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| `archive` / `abort` 解析语义 | 二者**不传** `include_archive`（保持 `False`） | `test_archive.py`（4 例）+ TC-FAF-011 | 🟡 |
| `rollback` 的独立 archive 搜索 | **不修改** `rollback.py` | `test_rollback.py`（5 例）+ TC-FAF-012 | 🟡 |
| `gate` / `state` 的重复解析器 | **不修改**（无归档需求） | `test_gate.py` / `test_state.py` | 🟢 |
| 路径漂移门禁（裸 `project_root / "changes"`） | `finder.py` / `canon.py` / `structure.py` **新增代码** | `test_changes_dir_consistency.py`（8 例，含正则扫描） | 🟡 |
| 吞异常哨兵行号漂移 | 三处文件**插入**代码 ⇒ `audit/except-points.yaml` 行号必漂 | `audit_silent_except.py --check` | 🟡 |
| 既有 9 个 `find_change_dir` 调用点 | 6 处显式传 `True`，3 处保持默认 | `test_finder.py`（8 例）+ 全量套件 | 🟡 |

## 五、建议补充顺序

1. **第一优先**（部署前必补，P0）：TC-FAF-001 / 002 / 003 / 005 / 007 / 008 / 009 / 011 / 012
   —— 含全部「默认零漂移」与「归档后可用」的立论点，以及自我移动反例。
2. **第二优先**（部署后尽快补，P1）：TC-FAF-004 / 006 / 010 / 013
   —— 后缀匹配、缺目录容错、structure merge、归档正向基线。
3. **第三优先**：无 P2。

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 归档后 `validate` rc=1「找不到 change」 | 2026-09-26T04:00:45+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | `stdd validate 2026-09-25-new-isolate-flag`（cwd=仓库根） |
| 归档后 `status` rc=1「找不到 change」 | 2026-09-26T04:00:45+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | `stdd status 2026-09-25-new-isolate-flag` |
| 归档后 `canon verify` rc=1「canonical/proposals/... not found」 | 2026-09-26T04:00:45+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | `stdd canon verify 2026-09-25-new-isolate-flag` |
| 归档后 `structure merge` rc=1「Delta not found」 | 2026-09-26T04:00:45+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | `stdd structure merge 2026-09-25-new-isolate-flag` |
| 对照：同一 change 未归档时 `canon verify` **2/2 通过** | 2026-09-26T04:00:45+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | 同上（归档前复跑） |
| 四个独立解析器行号（`finder.py:5` / `canon.py:12` / `gate.py:22` / `state.py:16`） | 2026-09-26T04:00:45+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | `grep -rn "find_change_dir\|_get_canon_dir" upstream/fstdd/cli/` |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。
- 上表全部证据采集于**修复前**的基线 `f3b2713`；修复实现后须追加一行「修复后复跑」证据，
  并保持 `observed_at` 为实际复跑时刻。
