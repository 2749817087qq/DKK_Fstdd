# 3.3.7+ 测试方案与详细案例 — 归档生命周期收口（解析统一 + 状态自洽）

> 版本：3.3.7（R 轴；本 change 不改版本号，升版在 DELIVER 按 semver 复核）
> 创建日期：2026-10-07
> 对应 Phase 2 Spec：`canonical/specs/code/change-dir-resolution.yaml`（MODIFIED，REQ-001..003 / SC-101..110）、
> `canonical/specs/code/archive-state-consistency.yaml`（NEW，REQ-001..002 / SC-201..205）；
> `canonical/specs/agent/2026-10-07-change-dir-resolution-unify.yaml`（8 个 CP）
> 观测基线：`observed_at=2026-10-07T13:55:34+00:00`、`observed_base_git_sha=f7bf8ec39a9784c7a8812d8b4b4e6238d6fe1b46`

## 一、测试策略

### 1.1 测试金字塔

本 change 修的是 **CLI 的解析口径与状态迁移**，测试重心落在 **CLI 实跑 + 真实归档 change 回归**：

- **CLI 实跑与退出码/文案断言（≈50%）**：每个受影响的命令都对**真实归档 change** 跑一次，
  断言 `rc` / stdout / stderr / 落盘差异 —— 不用「读代码觉得对了」代替（EXP-2026-0021）。
- **静态契约扫描（≈20%）**：全仓「接受 change 名」的模块必须走统一入口；扫描器**自带双向自检**
  （违例能抓 / 合法不误报）。
- **状态文件字段级断言（≈20%）**：C3/C4 的写操作以「白名单字段 + 闸门字段逐字段相等」锚定
  （KG-094：不得抽检）。
- **既有测试面回归（≈10%）**：`test_phase` / `test_gate` / `test_state` / `test_rollback` /
  `test_archive` / `test_finder` / `test_finder_archive_fallback` / `test_changes_dir_consistency` /
  `test_baseline_ops` 全量复跑。

### 1.2 测试原则

1. **断言可逆、不删测**：只做修正，不删除任何既有用例。
2. **静态判据必配行为断言**：模块级扫描有固有上限（EXP-2026-0024，3.3.7 已用真实缺陷验证过），
   故每个静态判据都必须有一条对应的「实跑一次看结果」断言。
3. **审计器自带自检**：契约扫描器必须含「构造违例样本 → 断言能抓到」与「构造合法样本 → 断言不误报」
   （EXP-2026-0021）。
4. **破坏性操作要白名单**：`archive` / `rollback` 都移动目录并写状态文件（EXP-2026-0015），
   断言必须写明「允许变哪几个字段」，而非「不要改错」。
5. **RED 取证在隔离环境**：本 change 触及 `archive` / `rollback` 这类破坏性命令，
   RED 取证必须在临时项目 / 副本中进行，**绝不在仓库根回退后直接跑**（EXP-2026-0023，3.3.7 的教训）。
6. **全量样本回归**：判据变更后对**全仓**模块跑一遍并断言 0 违规，并对历史归档 change 回归
   （EXP-2026-0025）。
7. **执行留痕**：引用实测数据的证据须含 `observed_at`（带时区）与 `observed_base_git_sha`。

### 1.3 已有测试资产（回归面）

| 测试文件 | 行数 | 类型 | 覆盖范围 |
|----------|------|------|----------|
| `upstream/tests/commands/test_phase.py` | 258 | 集成 | `phase` 子命令（advance / set / record-slice / status） |
| `upstream/tests/commands/test_gate.py` | 517 | 集成 | `gate` 子命令（approve / amend-audit / 顺序校验） |
| `upstream/tests/commands/test_state.py` | 124 | 集成 | `state`（查看 / `--resume` / `--set`） |
| `upstream/tests/commands/test_state_coverage.py` | — | 集成 | `state` 补充覆盖 |
| `upstream/tests/commands/test_rollback.py` | 73 | 集成 | `rollback`（**仅断言 `status == active`**，不断言 `current_phase`） |
| `upstream/tests/commands/test_archive.py` | 72 | 集成 | `archive` 归档移动与状态 |
| `upstream/tests/commands/test_finder.py` | 158 | 单元 | `find_change_dir` 解析语义（SC-001..006） |
| `upstream/tests/commands/test_finder_archive_fallback.py` | 201 | 集成 | **前序 change 的归档回退集成测试**（validate / status / canon verify / structure merge 在归档 change 上可用 + 3 条反例守卫；共 7 个用例） |
| `upstream/tests/commands/test_changes_dir_consistency.py` | 313 | 集成 | change 目录命名与解析一致性 |
| `upstream/tests/test_baseline_ops.py` | 255 | 集成 | `baseline` 子命令 |
| `upstream/tests/test_canon_dchash_ops.py` | 323 | 集成 | `canon verify` 的 DC-HASH（含归档回退） |

> ⚠️ **`work` 命令当前无任何直接测试** —— 本 change 新增的 `TC-CDR-003` 将是它的首个覆盖。

## 二、详细测试案例

### 功能 1：读路径在归档 change 上不再失败（capability `change-dir-resolution` → REQ-001）

对应 spec：`change-dir-resolution.yaml` → REQ-001（SC-101..104）

#### 案例 1.1 — `phase status` 在归档 change 上正常输出

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-001 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-101 |
| **优先级** | P0 |
| **预置条件** | 存在归档 change `.fstdd/archive/<name>/`（含 `.fstdd.yaml`），`changes/<name>/` 不存在 |
| **输入** | `fstdd phase status <name>` |
| **预期结果** | rc=0；stdout 含该 change 名与相位信息；**不含** `.fstdd.yaml not found` |
| **当前状态** | ❌ 修复前 rc≠0（实测 `.fstdd.yaml not found in <name>`） |

#### 案例 1.2 — `state` 查看在归档 change 上正常输出

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-002 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-102 |
| **优先级** | P0 |
| **预置条件** | 同上 |
| **输入** | `fstdd state <name>`（只读） |
| **预期结果** | rc=0；输出状态摘要；不含 `.fstdd.yaml not found`；不含 `changes\<name>` 这类「去错地方找」的路径 |
| **当前状态** | ❌ 修复前 rc≠0（实测把 `…\changes\<name>` 都打出来了） |

#### 案例 1.3 — `work list` 在归档 change 上正常输出

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-003 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-103 |
| **优先级** | P0 |
| **预置条件** | 同上；change 内 `related_work` 可空 |
| **输入** | `fstdd work list <name>` |
| **预期结果** | rc=0；有记录则列出，无记录则输出「暂无关联工作记录」提示；不含 `.fstdd.yaml not found` |
| **当前状态** | ❌ 修复前 rc≠0（实测同形报错）；⚠️ `work` 此前**无任何测试** |

#### 案例 1.4 — 短名后缀匹配在归档区同样生效

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-004 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-104 |
| **优先级** | P1 |
| **预置条件** | 归档目录为 `YYYY-MM-DD-<短名>`；用户只传 `<短名>` |
| **输入** | `fstdd phase status <短名>` |
| **预期结果** | rc=0，命中 `archive/YYYY-MM-DD-<短名>`；不因「changes/ 下无同名」提前失败 |
| **当前状态** | ❌ 修复前 rc≠0 |

### 功能 2：写路径在归档 change 上准确拒绝（capability `change-dir-resolution` → REQ-002）

对应 spec：`change-dir-resolution.yaml` → REQ-002（SC-105..108）

#### 案例 2.1 — `phase` 写操作拒绝且文案含三要素

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-005 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-105 |
| **优先级** | P0 |
| **预置条件** | 归档 change，且其 `phases.deliver.status` 未闭合 |
| **输入** | `fstdd phase advance <name>`（另跑 `phase set` / `phase record-slice` 同形） |
| **预期结果** | rc≠0；stdout 同时含「已归档」+ `rollback` + `archive/<name>` 实际路径；归档 `.fstdd.yaml` 字节与 mtime **均不变** |
| **当前状态** | ❌ 修复前报「.fstdd.yaml not found」（误导文案） |

#### 案例 2.2 — `state --set` / `work add` / `baseline establish` 同语义拒绝

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-006 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-106 |
| **优先级** | P0 |
| **预置条件** | 归档 change |
| **输入** | `fstdd state <name> --set current_phase=spec`、`fstdd work add <name> --type doc "x"`、`fstdd baseline establish <name>` |
| **预期结果** | 三者均 rc≠0 且 stdout 含「已归档」+ `rollback`；`archive/<name>/` 内**无任何新文件** |
| **当前状态** | ❌ 修复前报误导文案（`work add` / `baseline establish` 为代码确认） |

#### 案例 2.3 — `gate amend-audit` 对归档 change 放行

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-007 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-107 |
| **优先级** | P0 |
| **预置条件** | 归档 change；Gate 已有确认记录 |
| **输入** | `fstdd gate amend-audit <name> --gate 3 --confirmed-by cli --evidence "补录"` |
| **预期结果** | rc=0；追认审计被追加（`.fstdd.yaml` 对应字段出现该 evidence）；行为与在办 change 上一致 |
| **当前状态** | ❌ 修复前不可用（**该命令的设计用途即归档 Gate 追认**） |

#### 案例 2.4 — 在办 change 上读写行为零漂移

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-008 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-108 |
| **优先级** | P0 |
| **预置条件** | 在办 change（`changes/<name>/`） |
| **输入** | 读：`phase status` / `state` / `work list`；写：`phase advance`（在合成项目内） |
| **预期结果** | 读 rc=0；写正常落盘（状态推进）；**输出不含**「已归档」字样 |
| **当前状态** | ✅ 既有行为（须保持） |

### 功能 3：单一入口防复发（capability `change-dir-resolution` → REQ-003）

对应 spec：`change-dir-resolution.yaml` → REQ-003（SC-109..110）

#### 案例 3.1 — 契约扫描：接受 change 名的模块 100% 走统一入口

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-009 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-109 |
| **优先级** | P0 |
| **预置条件** | 修复后的 `upstream/fstdd/cli/commands/*.py` |
| **输入** | 运行契约扫描（AST 口径） |
| **预期结果** | 违规模块数 = 0；扫描覆盖 `phase` / `gate` / `state` / `work` / `baseline` 五个模块 |
| **当前状态** | ➕ 需新增（防复发契约测试） |

#### 案例 3.2 — 扫描器自检（双向）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-010 |
| **对应 Spec** | change-dir-resolution/spec.md → Scenario: SC-110 |
| **优先级** | P0 |
| **预置条件** | 扫描器实现 |
| **输入** | 对「自建解析器」违例样本、「走统一入口」合法样本、「注释里提到但代码未调用」反例分别扫描 |
| **预期结果** | 违例样本判违规；合法样本不判违规；注释反例**判违规** |
| **当前状态** | ➕ 需新增（EXP-2026-0021 的自检要求） |

#### 案例 3.3 — 无 `archive/` 目录时不抛异常（既有语义回归）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-011 |
| **对应 Spec** | change-dir-resolution/spec.md → SC-104 AND-1（沿用既有 SC-006 语义） |
| **优先级** | P1 |
| **预置条件** | 合成项目只有 `changes/`，无 `archive/` |
| **输入** | `fstdd phase status <在办 change>` |
| **预期结果** | rc=0，不抛异常、不报 archive 相关错误 |
| **当前状态** | ✅ 既有语义（须保持） |

#### 案例 3.4 — 对已归档 change 执行 `archive` 仍拒绝（反例守卫不回归）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CDR-012 |
| **对应 Spec** | change-dir-resolution/spec.md → SC-108 AND-1（承接既有 SC-011 守卫） |
| **优先级** | P0 |
| **预置条件** | change 已归档，`changes/<name>/` 不存在 |
| **输入** | `fstdd archive <name>` |
| **预期结果** | rc≠0；`archive/<name>/` **原地不动**（不得解析到归档区后把自己再移动一次） |
| **当前状态** | ✅ 既有守卫（前序 change 的 `test_finder_archive_fallback.py` 已覆盖「二次 archive 须拒绝」，本 change 不得破坏） |

### 功能 4：`archive` 归档即闭合相位（capability `archive-state-consistency` → REQ-001）

对应 spec：`archive-state-consistency.yaml` → REQ-001（SC-201..202）

#### 案例 4.1 — 归档后 `phases.deliver.status == completed`

| 字段 | 内容 |
|------|------|
| **ID** | TC-ASC-001 |
| **对应 Spec** | archive-state-consistency/spec.md → Scenario: SC-201 |
| **优先级** | P0 |
| **预置条件** | 合成项目中一个 `phases.deliver.status == in_progress` 的在办 change |
| **输入** | `fstdd archive <name>` |
| **预期结果** | `archive/<name>/.fstdd.yaml` 的 `phases.deliver.status == "completed"`；`status == "archived"` |
| **当前状态** | ❌ 修复前悬空（实测 3 个历史 change 分别为 in_progress / pending / 停在 build） |

#### 案例 4.2 — 归档只动两个字段，闸门字段逐字段不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-ASC-002 |
| **对应 Spec** | archive-state-consistency/spec.md → Scenario: SC-202 |
| **优先级** | P0 |
| **预置条件** | Gate 1/2/3 均已确认的在办 change（`phases.*.confirmed_*` 全有值） |
| **输入** | 归档前后各读一次 `.fstdd.yaml`，逐字段对比 |
| **预期结果** | 仅 `phases.deliver.status` 与 `status` 变化；`phases.{understand,spec,build,deliver}` 的 `confirmed_at` / `confirmed_by` / `confirmed_evidence` 逐字段相等；`change_id` / `mode` / `complexity_score` / `traceability` 等逐字段相等 |
| **当前状态** | ➕ 需新增（EXP-2026-0015 / KG-094） |

### 功能 5：`rollback` 恢复保留原相位（capability `archive-state-consistency` → REQ-002）

对应 spec：`archive-state-consistency.yaml` → REQ-002（SC-203..205）

#### 案例 5.1 — 恢复后 `current_phase` 保持归档前值

| 字段 | 内容 |
|------|------|
| **ID** | TC-ASC-003 |
| **对应 Spec** | archive-state-consistency/spec.md → Scenario: SC-203 |
| **优先级** | P0 |
| **预置条件** | 归档时 `current_phase == "deliver"` 的已归档 change；`changes/<name>/` 不存在 |
| **输入** | `fstdd rollback <name>` |
| **预期结果** | 恢复后 `current_phase == "deliver"`（**不是** `understand`）；`status == "active"`；目录位于 `changes/<name>/` |
| **当前状态** | ❌ 修复前无条件重置为 `understand`（`--dry-run` 实测输出已证实） |

#### 案例 5.2 — 恢复后 `phases.*` 与闸门字段零改动

| 字段 | 内容 |
|------|------|
| **ID** | TC-ASC-004 |
| **对应 Spec** | archive-state-consistency/spec.md → Scenario: SC-204 |
| **优先级** | P0 |
| **预置条件** | 已归档且 Gate 已确认的 change |
| **输入** | 恢复前后各读一次 `.fstdd.yaml`，逐字段对比 |
| **预期结果** | `phases.*` 的 `status` 与全部 `confirmed_*` 字段逐字段相等；仅 `status`（与必要时 `current_phase`）变化 |
| **当前状态** | ➕ 需新增 |

#### 案例 5.3 — 归档 → 恢复 → 再归档 往返一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-ASC-005 |
| **对应 Spec** | archive-state-consistency/spec.md → Scenario: SC-205 |
| **优先级** | P1 |
| **预置条件** | 合成项目中 `current_phase == "deliver"` 的在办 change |
| **输入** | `archive` → `rollback` → `archive` 连续三次 |
| **预期结果** | 第二次归档后状态与第一次一致（`deliver: completed`、`current_phase` 不变）；往返过程无「changes/ 与 archive/ 同名并存」残留 |
| **当前状态** | ➕ 需新增 |

#### 案例 5.4 — `rollback` 冲突检查不回归

| 字段 | 内容 |
|------|------|
| **ID** | TC-ASC-006 |
| **对应 Spec** | archive-state-consistency/spec.md → SC-203 AND-2（既有逻辑不回归） |
| **优先级** | P1 |
| **预置条件** | `archive/<name>/` 与 `changes/<name>/` **同时**存在 |
| **输入** | `fstdd rollback <name>` |
| **预期结果** | rc≠0，输出「冲突」类提示；两侧目录均不动 |
| **当前状态** | ✅ 既有逻辑（须保持） |

## 三、测试执行矩阵

| 能力 | 静态审计 | CLI 实跑 | 反向样本 | 既有回归 | 高风险点 |
|------|---------|---------|---------|---------|---------|
| change-dir-resolution（读） | 契约扫描（统一入口） | 归档 change 上 3 条读命令 | 无 `archive/` 时不抛异常 | test_finder / test_finder_archive_fallback / test_changes_dir_consistency | 🔴 后缀匹配在多命中时的取值 |
| change-dir-resolution（写） | 契约扫描（写分支须用 require_*） | 4 类写命令的拒绝 + amend-audit 放行 | 对已归档 change 再 archive 须拒 | test_archive / test_gate / test_phase | 🔴 误伤 archive/abort 的 include_archive=False |
| archive-state-consistency | — | archive / rollback 各跑一次 | 闸门字段零改动（逐字段） | test_rollback / test_archive | 🔴 状态文件写坏（不可逆审计损失） |

## 四、回归风险矩阵

| 改动区域 | 直接影响 | 回归验证 | 风险 |
|----------|---------|---------|------|
| `upstream/fstdd/cli/finder.py`（新增 `require_active_change_dir`） | 全部命令的解析入口 | test_finder / test_finder_archive_fallback 全量 | 🔴 |
| `phase.py`（删自建解析器 + 写守卫） | 相位推进 | test_phase 258 行 + TC-CDR-001/005/008 | 🔴 |
| `gate.py`（删自建解析器 + amend-audit 放行） | Gate 确认与追认审计 | test_gate 517 行 + TC-CDR-007 | 🔴 |
| `state.py`（删自建解析器 + `--set` 守卫） | 跨 session 状态 | test_state / test_state_coverage + TC-CDR-002/006 | 🟡 |
| `work.py`（删自建解析器 + `add` 守卫） | 关联工作记录 | **无既有测试** + TC-CDR-003/006（本 change 首覆盖） | 🟡 |
| `baseline.py`（`_resolve_change` 换实现） | baseline 建立/读取 | test_baseline_ops 255 行 + TC-CDR-006 | 🟡 |
| `archive.py`（闭合 deliver 相位） | 归档状态 | test_archive + TC-ASC-001/002 | 🔴 |
| `rollback.py`（保留 current_phase） | 恢复状态 | test_rollback + TC-ASC-003/004/006 | 🔴 |
| 全仓 | — | 全量 `pytest upstream/tests` + 根 `tests/` + 四自检 | 🟡 |

## 五、建议补充顺序

1. **第一优先（P0，部署前必补，14 项）**：TC-CDR-001、TC-CDR-002、TC-CDR-003、TC-CDR-005、
   TC-CDR-006、TC-CDR-007、TC-CDR-008、TC-CDR-009、TC-CDR-010、TC-CDR-012、
   TC-ASC-001、TC-ASC-002、TC-ASC-003、TC-ASC-004
2. **第二优先（P1，随后尽快补，4 项）**：TC-CDR-004、TC-CDR-011、TC-ASC-005、TC-ASC-006
3. **第三优先（P2，回归即可）**：全量 pytest 与四自检脚本

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| `fstdd phase status 2026-10-07-tool-defect-fixes` → `.fstdd.yaml not found in 2026-10-07-tool-defect-fixes` | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 本机 CLI 实跑 |
| `fstdd state 2026-10-07-tool-defect-fixes` → `.fstdd.yaml not found in E:\FSTDD\stdd-repo\.fstdd\changes\2026-10-07-tool-defect-fixes` | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 本机 CLI 实跑 |
| `fstdd work list 2026-10-07-tool-defect-fixes` → `.fstdd.yaml not found in 2026-10-07-tool-defect-fixes` | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 本机 CLI 实跑 |
| 对照组 rc=0：`validate` / `status` / `diff` / `canon verify` / `ci check-failures` / `extract-proposal` / `structure merge` | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 本机 CLI 实跑 |
| `fstdd rollback 2026-10-07-tool-defect-fixes --dry-run` → 含 `更新状态: status=active, current_phase=understand` | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 本机 CLI 实跑（dry-run） |
| `grep -rn "find_change_dir" upstream/fstdd/` = 10 处已用统一入口；5 个模块自建 | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 本机 grep |
| 归档态悬空 3 例：`2026-10-04-baseline-failures-zero`=in_progress / `2026-10-06-legacy-debt-cleanup`=build+pending / `2026-10-05-upstream-baseline-alignment`=completed | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 只读读 `.fstdd/archive/*/.fstdd.yaml` |
| `rollback.py` 写死 `state["current_phase"] = "understand"` | 2026-10-07T13:55:34+00:00 | f7bf8ec… | 源码阅读 |
| `test_rollback.py` **只断言** `status == "active"`，不断言 `current_phase` ⇒ C4 不破坏既有用例 | 2026-10-07T14:35:00+00:00 | f7bf8ec… | 源码阅读 |
| `work` 命令**无任何直接测试** | 2026-10-07T14:35:00+00:00 | f7bf8ec… | `grep -rln "cmd_work\|work list" upstream/tests/ tests/` 空结果 |
