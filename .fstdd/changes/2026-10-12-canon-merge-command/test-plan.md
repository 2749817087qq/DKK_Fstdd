# canonical 合并自动化 测试方案与详细案例

> 版本：change 2026-10-12-canon-merge-command
> 创建日期：2026-10-13
> 对应 Phase 2 Spec：`canonical/specs/code/canon-merge-automation.yaml`（9 REQ / 12 SC）
> + `canonical/specs/agent/2026-10-12-canon-merge-command.yaml`（12 CP）

## 一、测试策略

### 1.1 测试金字塔

- **单元级（主体）**：命名决策 / 幂等决策 / 输入校验 / 根路径解析 —— 用 `tmp_path` 自建 fixture change，
  不碰仓库真实 canonical（**本方案铁律**：fixture 必须是合成目录）。
- **集成级**：真实跑 `fstdd canon merge` 子进程（fixture change），断言文件与索引落位。
- **E2E/会话级**：既有 `canon init/generate/verify` 测试 + 全量根级与框架侧测试 + CLI 冒烟。
- 比例：单元 8 : 集成 4 : E2E 2。

### 1.2 测试原则

- **fixture 隔离**：任何测试不得写入仓库真实的 `.fstdd/changes/`、`canonical/`、`.fstdd/archive/`。
- **双向断言**（EXP-2026-0032：收紧必须配放行）—— 拒 `..`/分隔符 ⇄ 放合法 change 名；
  拒缺 `meta.capability` ⇄ 放有字段的正常命名。
- **判据落到函数体**（EXP-2026-0026）—— 不得只断言「模块顶部 import 了 find_change_dir」。

### 1.3 已有测试资产

| 测试文件 | 类型 | 说明 |
|---|---|---|
| `upstream/tests/test_canon_dchash_ops.py` | 单元 | 既有 canon 的 DC-HASH/DC-FIELD 操作，**必须保持绿** |
| `upstream/tests/test_evidence_ops.py` | 单元 | evidence 操作；引用 canonical 模板 |
| `upstream/tests/test_canonical_in_workspace.py` | 集成 | canonical 在工作区的定位断言 |
| `upstream/tests/test_fstdd_matrix.py` | 矩阵 | 含「全局 canonical」注释断言（见 §四 风险） |
| 仓库根 `tests/`（230 用例） | 会话级 | 全量回归基线 |

## 二、详细测试案例

### 功能 1：根 canonical 路径单一事实源（REQ-002）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-001 |
| **对应 Spec** | canon-merge-automation → SC-002 |
| **优先级** | P0 |
| **预置条件** | `tmp_path` 下建 `canonical/proposals` 等目录 + `.fstdd/changes/<name>/canonical/` 三类文件 + `.fstdd.yaml` |
| **输入** | 调 `_get_canon_dir(root)` 与 `_root_canon_dir(root)` |
| **预期结果** | 两者**同一**路径且等于 `<root>/canonical`；**不得**返回 `.fstdd/canonical` |
| **当前状态** | ❌ 测试缺（Phase 3 新建） |

### 功能 2：dry-run 零写入（REQ-001）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-002 |
| **对应 Spec** | SC-001 |
| **优先级** | P0 |
| **预置条件** | fixture change 含三类 canonical 文件 |
| **输入** | `canon merge <name> --dry-run`；前后各取一次 `git status --porcelain` |
| **预期结果** | exit 0；stdout 含 WRITE 决策清单；前后 `git status` **逐字一致** |
| **当前状态** | ❌ 测试缺 |

### 功能 3：命名三分法（REQ-004）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-003 |
| **对应 Spec** | SC-005 |
| **优先级** | P0 |
| **预置条件** | fixture：proposals/agent spec 仅含 `meta.change_id`；code spec 含 `meta.capability` |
| **输入** | `canon merge <name>` |
| **预期结果** | proposal/agent 用 change_id 名落位；code spec 用 capability 名落位 |
| **当前状态** | ❌ 测试缺 |

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-003b（反向） |
| **对应 Spec** | SC-005b |
| **优先级** | P0 |
| **输入** | fixture 的 code spec **删掉** `meta.capability` |
| **预期结果** | 该文件被**跳过**并输出含路径的告警；不静默改名；退出码非 0 |
| **当前状态** | ❌ 测试缺 |

### 功能 4：幂等与冲突（REQ-003）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-004 |
| **对应 Spec** | SC-003 |
| **优先级** | P0 |
| **输入** | 连续执行 `canon merge <name>` 两次 |
| **预期结果** | 第二次 exit 0 且 `git diff` 为空；已存在文件不被重写 |
| **当前状态** | ❌ 测试缺 |

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-004b（反向） |
| **对应 Spec** | SC-003b |
| **优先级** | P0 |
| **输入** | 先合并一次，再**篡改**根侧目标文件尾部，然后重跑 merge |
| **预期结果** | exit 非 0；目标文件**未被覆盖**（篡改内容仍在）；stdout 指明冲突路径与已写/未写清单 |
| **当前状态** | ❌ 测试缺 |

### 功能 5：归档 change 可用（REQ-005）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-005 |
| **对应 Spec** | SC-006 |
| **优先级** | P0 |
| **输入** | fixture change 先 `archive`，再 `canon merge` |
| **预期结果** | 正确定位 `archive/<name>/canonical/` 并合并；**不**以「已归档」拒绝 |
| **当前状态** | ❌ 测试缺 |

### 功能 6：输入校验双向（REQ-008）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-006（反向） |
| **对应 Spec** | SC-009 |
| **优先级** | P0 |
| **输入** | `canon merge "../../x"` 与 `canon merge "a/b"` |
| **预期结果** | 均 exit 非 0 且报「找不到 change」；未写入任何文件 |
| **当前状态** | ❌ 测试缺 |

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-006b（正向） |
| **对应 Spec** | SC-009b |
| **优先级** | P0 |
| **输入** | 合法 change 名（含连字符/点/数字） |
| **预期结果** | 正常解析并合并，不误拒 |
| **当前状态** | ❌ 测试缺 |

### 功能 7：判据落到函数体（REQ-009）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-007 |
| **对应 Spec** | SC-010 |
| **优先级** | P0 |
| **输入** | AST 解析 `canon.py` |
| **预期结果** | merge 路径函数体内出现 `find_change_dir`/`_resolve_change_dir` **调用**；不存在第二套自行拼接 `.fstdd/changes/<name>` 的解析逻辑 |
| **当前状态** | ❌ 测试缺 |

### 功能 8：UPSTREAM_PATCHES 登记（REQ-006）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-008 |
| **对应 Spec** | SC-007 |
| **优先级** | P0 |
| **输入** | 读 `docs/UPSTREAM_PATCHES.md` 表体 |
| **预期结果** | 表体 >= 1 行且 8 列非空；「待登记」区既有两条原样保留 |
| **当前状态** | ❌ 测试缺 |

### 功能 9：合并后自证（proposal C4）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-009 |
| **对应 Spec** | agent spec CP-011 |
| **优先级** | P1 |
| **输入** | fixture 合并后跑 `canon verify <name>` |
| **预期结果** | 2/2 通过（DC-HASH / DC-FIELD） |
| **当前状态** | ❌ 测试缺 |

### 功能 10：既有行为不回归（REQ-007）

| 字段 | 内容 |
|---|---|
| **ID** | TC-CMA-010 |
| **对应 Spec** | SC-008 |
| **优先级** | P0 |
| **输入** | 既有 canon 测试 + 全量根级/框架侧 + CLI 冒烟 |
| **预期结果** | failed 数与基线一致（0 或逐条归因）；CLI 三冒烟 exit 0 |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E/会话级 | 状态 |
|---|---|---|---|---|
| 根路径单一事实源 | TC-CMA-001 | — | — | 🔴 待实现 |
| dry-run 零写入 | TC-CMA-002 | — | — | 🔴 待实现 |
| 命名三分法（含反向） | TC-CMA-003/003b | — | — | 🔴 待实现 |
| 幂等与冲突（含反向） | TC-CMA-004/004b | — | — | 🔴 待实现 |
| 归档 change | — | TC-CMA-005 | — | 🔴 待实现 |
| 输入校验（双向） | TC-CMA-006/006b | — | — | 🔴 待实现 |
| 函数体判据 | TC-CMA-007 | — | — | 🔴 待实现 |
| UPSTREAM_PATCHES 登记 | TC-CMA-008 | — | — | 🔴 待实现 |
| 合并后自证 | — | TC-CMA-009 | — | 🔴 待实现 |
| 既有行为不回归 | — | — | TC-CMA-010 | 🔴 待实现 |

## 四、回归风险矩阵

| 风险区域 | 本 change 改动 | 已有回归保护 | 风险等级 |
|---|---|---|---|
| `_get_canon_dir(None)` 返回值 | 改指仓库根 `canonical/` | 全量两侧测试 + TC-CMA-001 | 🟡 中 |
| `canon init --project-level` 落点 | 随上一条变为仓库根 | CLI 冒烟 + 既有 canon 测试 | 🟡 中 |
| `canon generate --all` / `_generate_one` 回退 | 扫到**真**根 canonical（原为空） | 既有 canon 测试 | 🟢 低（由坏变好） |
| `cli/__init__.py` 解析面 | 新增一个子命令 | CLI 冒烟 | 🟢 低 |
| 真实 `canonical/` 被测试污染 | fixture 隔离（tmp_path） | TC-CMA-010 + 人工核对 `git status` | 🟡 中 |
| `upstream/`（vendored 内核） | 修改 canon.py + cli/__init__.py | UPSTREAM_PATCHES 登记（TC-CMA-008） | 🟡 中 |

## 五、建议补充顺序

1. **第一优先（P0）**：TC-CMA-001、002、003/003b、004/004b、005、006/006b、007、008、010
2. **第二优先（P1）**：TC-CMA-009

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at | observed_base_git_sha | 来源 |
|---|---|---|---|
| `fstdd canon --help` 仅 init/generate/verify；canon.py 532 行无 merge 函数 | 2026-10-12T13:45+00:00 | 34f11b5 | Phase 1 侦察 |
| 根 canonical YAML 数：proposals 21 / specs.code 34 / specs.agent 18（共 73） | 2026-10-13T01:50+08:00 | 34f11b5 | `ls canonical/**/*.yaml` |
| 归档区累计 207 个 canonical YAML | 2026-10-12T13:45+00:00 | 34f11b5 | `find .fstdd/archive -name '*.yaml'` |
| 两个根 canonical：仓库根 74 个被跟踪 vs `.fstdd/canonical/` 0 个 | 2026-10-13T01:52+08:00 | 34f11b5 | `git ls-files` 两侧对照 |
| `_get_canon_dir(None)` 返回 `.fstdd/canonical` | 2026-10-13T01:52+08:00 | 34f11b5 | canon.py:38-42 只读核对 |
| 命名量化：proposals 21/21 change_id；agent 16/18 change_id；code 23/34 capability | 2026-10-13T01:53+08:00 | 34f11b5 | `ls` + 元数据读取 |
| `finder._resolve_in` 已拒 `..`/分隔符 | 2026-10-13T01:54+08:00 | 34f11b5 | finder.py:11-18 只读核对 |
| UPSTREAM_PATCHES 表体为空（仅待登记 2 条） | 2026-10-12T13:45+00:00 | 34f11b5 | Phase 1 侦察 |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖

> 由 understand.md Step 0.5 判定：**FINANCIAL_PROJECT=NO** ⇒ 本章节跳过。
