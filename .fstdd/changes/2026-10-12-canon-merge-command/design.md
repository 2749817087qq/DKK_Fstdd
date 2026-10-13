# canonical 合并自动化 —— 新增 `fstdd canon merge`，消除 DELIVER 的手工拷贝 - 技术设计

**change**: `2026-10-12-canon-merge-command` ｜ **模式**: standard（复杂度 7）｜ **前置**: Gate 1 ✅
**能力**: `canon-merge-automation`（NEW）｜ **执行模式**: 待定（Phase 2 定）

## Context

### 当前系统状态

DELIVER 的 canonical 合并没有 CLI 命令，全靠人工拷贝。实测（Phase 1 + ① DELIVER 全程复现）：

| 环节 | 现状 | 代价 |
|---|---|---|
| 定位源 | 人工找 `changes/<change>/canonical/{proposals,specs/agent,specs/code}` | 易找错 |
| 拷贝到根 | 人工复制到 `canonical/` 对应目录 | **命名口径分裂**（见下） |
| 登记索引 | 人工编辑 `canonical/.canon-index.yaml`（3 段、缩进不一） | 易漏、易错位 |
| 自证 | 人工跑 `fstdd canon verify <change>` | 忘了跑就不知道不一致 |

**规模**：根 `canonical/` 下 `*.yaml` = **73 个**（proposals 21 / specs.code 34 / specs.agent 18）；
`.canon-index.yaml` 顶层 73 条；`.fstdd/archive/*/canonical/` 累计 **207 个 YAML**。

### 🔴 Phase 2 实拍发现 1：两个根 canonical 目录，代码指向错的那个

| 路径 | 事实 |
|---|---|
| **仓库根 `canonical/`** | **74 个被 git 跟踪的文件**，活跃维护（最近提交 `e6c0b9e`）—— **这才是真身** |
| `.fstdd/canonical/` | `designs`/`proposals`/`specs` 三个**空**子目录，**0 个被跟踪文件、无提交历史** —— 陈旧空骨架 |

而 `canon.py:38` 的 `_get_canon_dir(project_root)`（无 `change_name` 时）**返回 `.fstdd/canonical`**。

⇒ `canon generate --all`（L252）与 `_generate_one` 的「项目级回退」分支（L327）扫的都是**空目录**。
⇒ `test_fstdd_matrix.py:151` 的注释（「全局 `.fstdd/canonical/` 由归档/合并填充」）与事实不符。

**这是本 change 必须先处置的设计前提** —— 否则 `merge` 会继承了同样的错路径。

### 🔴 Phase 2 实拍发现 2：命名口径分裂（量化）

| 目标目录 | 命名 | 计数 | 占比 |
|---|---|---|---|
| `canonical/proposals/` | `meta.change_id` | **21 / 21** | 100% |
| `canonical/specs/agent/` | `meta.change_id` | **16 / 18** | 89%（例外：`inbox-api-only-write` / `inbox-deploy`） |
| `canonical/specs/code/` | `meta.capability` | **23 / 34** | 68%（vs change_id 11 个 / 32%） |

实测依据（源文件元数据）：
- `specs/code/*.yaml` **均含** `meta.capability`（`test-teardown-resilience` / `change-dir-resolution` / `repo-hygiene`…）✅
- `specs/agent/*.yaml` **全为 `None`**，只有 `meta.change_id` ❌
- `proposals/*.yaml` 无 `capability`（预期）

⇒ 「统一成 capability 名」在当前数据模型下**做不到**；正解是**三分法**（见 D2）。

### 技术栈与约束

| 项 | 值 |
|---|---|
| vendored 内核 | `upstream/fstdd/cli/`（K 轴 3.1.0）⇒ **动手前必须先登记 `docs/UPSTREAM_PATCHES.md`** |
| 命令注册点 | `upstream/fstdd/cli/__init__.py` 的 `canon_subs`（L301-307） |
| 既有统一入口 | `finder.find_change_dir(name, root, include_archive=)`（**唯一** change 解析点） |
| 既有写守卫 | `commands/_dryrun.py`（v3.3.7 已统一接入 78 个写点） |
| 既有契约扫描 | 接受 change 名的命令模块必须走统一入口（`test_change_dir_resolution_unify`） |
| **硬约束** | 幂等 · `--dry-run` 不写盘 · 合并后自证 · 不破坏既有行为 · **历史存量命名不在本 change 修正** |

### 经验库交叉检查（Step 2）—— 三条直接命中

| 经验 | 内容 | 对本设计的影响 |
|---|---|---|
| **EXP-2026-0027**（high） | 新加的安全守卫用**词法前缀**比较判定「目标是否在禁区目录内」，而输入可含 `..` 逃逸；`fix_template` = ① 比较前两侧 resolve() 归一 ② **输入层**拒分隔符/`..`（双保险）③ 补正/反向测试 | ③ 接受**用户传入的 change 名** ⇒ **必须复用** `find_change_dir`（其 `_resolve_in` 已内置该防护），**不得自建解析器**；并补正/反向测试 |
| **EXP-2026-0032**（high） | 字符白名单看似覆盖，但 `..` 由 `.` 与 `/` 组合而成 ⇒ 路径上跳能通过；`fix_template` = 字符白名单之外必须补**段级判据**，且**同时准备「合法形态必须放行」的正例** | `merge` 的输入校验判据必须**成对**：拒绝 `..`/分隔符 + 放行合法 change 名（否则会误拒带连字符/点的合法名） |
| **EXP-2026-0026**（high） | 审计器判「模块是否合规」只看「模块里有没有出现某个符号」，而模块可以 **import 了统一入口却从不调用** ⇒ 假阴性；`fix_template` = 判据要落到**函数体** | ③ 不得只在 `canon.py` 顶部 `import find_change_dir` 而不调用；**判据必须断言函数体内出现统一入口调用**（否则既有 AST 契约扫描也可能被绕过） |
| KG-092（high，跨项目 17 次） | 钩子失败时 exit 0 且不上报告警 —— 失败静默腐烂 | ⇒ D8：任何失败必须非 0 退出 + 明确文案；部分成功要说明已写哪些 |
| EXP-2026-0034（high） | 沙箱 shim 直接替换 `pathlib.Path.unlink`，非 bypass 分支不经 `os.unlink` | `merge` 只**写**文件（copy），不删除 ⇒ 不触发守卫；但**不得**在实现里加 `unlink/rmtree` 清理动作 |

## Decisions

### 1. 根 canonical 路径收口为**单一事实源**，并修掉 `_get_canon_dir(None)` 的错位

**方案**：新增模块级函数 `_root_canonical_dir(project_root) -> Path`，**唯一**返回
`project_root / "canonical"`（仓库根）；把 `_get_canon_dir(project_root)` 的
无 `change_name` 分支改为**委托**它：

```python
def _root_canonical_dir(project_root: Path) -> Path:
    """根 canonical 的唯一定义点（仓库根 canonical/）。"""
    return project_root / "canonical"


def _get_canon_dir(project_root: Path, change_name: str = None) -> Path:
    if change_name:
        return _resolve_change_dir(project_root, change_name) / "canonical"
    return _root_canonical_dir(project_root)      # ← 原为 .fstdd/canonical
```

**为什么**：
- 「根 canonical 在哪」此前有**两个**互不一致的定义（`_get_canon_dir` 说 `.fstdd/canonical`，
  实践用仓库根 `canonical/`）—— 正是 EXP-2026-0026 说的「多一份定义就多一个假合规面」。
  收口成一个函数，`merge` / `generate --all` / `_generate_one` 回退分支**共用**同一答案。
- 顺带修好两个既有缺陷：`canon generate --all` 与 `_generate_one` 的项目级回退不再扫空目录。

**备选及排除**：
- 备选 A：只在 `merge` 内部硬编码 `project_root / "canonical"`，不动 `_get_canon_dir`
  —— **排除**：那会让「根 canonical 路径」出现第二份定义，与 D1 目的自相矛盾。
- 备选 B：把 `.fstdd/canonical/` 删掉、只保留仓库根 —— **排除**：删目录不在 Gate 1 范围
  （non_goals：只做被问的事）；且该目录 0 个被跟踪文件，删除无收益、有风险。
  **登记为欠账**（见 Risks）。

### 2. 命名口径：**三分法**，唯一依据是源文件元数据

**方案**：

| 源（`changes|archive/<change>/canonical/`） | 目标（`canonical/`） | 命名依据 |
|---|---|---|
| `proposals/<change>.yaml` | `proposals/<same>.yaml` | `meta.change_id` |
| `specs/agent/<change>.yaml` | `specs/agent/<same>.yaml` | `meta.change_id` |
| `specs/code/<cap>.yaml` | `specs/code/<same>.yaml` | `meta.capability` |

**缺字段时的行为**：**告警 + 跳过该文件**，绝不静默改名、绝不启发式推断
（D哥 在 Phase 1 明确「不由人工决定」）。

**为什么是三分法而非统一 capability 名**：实测 `specs/agent/*.yaml` 与 `proposals/*.yaml`
**没有** `meta.capability` 字段 ⇒ 统一成 capability 名在当前数据模型下**做不到**。
强行统一要么造名（不可追溯）要么改 schema（超出范围，已列 non_goal）。

**备选及排除**：
- 备选 A：全部用 change_id 名 —— **排除**：与 `specs/code/` 68% 的 capability 命名主流相悖，
  会把已收敛的口径重新打散。
- 备选 B：内容启发式推断 capability —— **排除**：不可追溯、会静默造名（违反 D2 缺字段契约）。

### 3. 幂等：以「目标内容与源逐字节相同 + 索引条目相同」为不动作条件

**方案**：对每个待合并文件 ——
① 若目标不存在 ⇒ 写；② 若目标存在且内容与源**逐字节相同** ⇒ 不写（记 `SKIP-identical`）；
③ 若目标存在但内容不同 ⇒ **报错退出**（不覆盖，交由人工裁决，避免静默吞掉差异）。
索引同理：条目已存在且值相同 ⇒ 不动；不同 ⇒ 报错。

**为什么**：SC3 要求「连续执行两次，第二次 `git diff` 为空」。③ 的「内容不同即报错」
比「直接覆盖」更安全 —— 覆盖会静默销毁根 canonical 上的人工修正（如 ① 那次 `stdd`→`fstdd`）。

**备选及排除**：
- 备选 A：一律覆盖（`shutil.copyfile`）—— **排除**：会静默抹掉根侧的人工修订，且失去幂等语义。
- 备选 B：按 mtime 取新者 —— **排除**：多一层不可判据的状态，且测试难稳定构造。

### 4. `--dry-run` 复用既有守卫，不得自造

**方案**：`cmd_canon_merge` 顶部按既有惯例接入 `_dryrun.dry_run_guard` /
`dry_run_requested`（v3.3.7 已统一 15 个命令模块 78 个写点），`--dry-run` 时只打印
「将写哪些文件、索引如何变化」并 `return`，**不落盘**。

**为什么**：`_dryrun.py` 是仓库既有的**唯一** dry-run 定义点，且自带契约扫描测试
（有写操作者必须处理 dry_run）。自造一套 = 立刻被该扫描判红。

**判据**：执行前后 `git status --porcelain` **逐字一致**（SC1）。

### 5. change 名解析：**必须**走 `find_change_dir`，不得自建解析器

**方案**：`merge` 通过既有 `_resolve_change_dir(project_root, change_name)` 取源目录
（它内部调 `find_change_dir(..., include_archive=True)`）。**不新增任何路径拼接逻辑**。

**为什么**：
- `finder._resolve_in`（`finder.py:11-18`）**已内置**穿越防护：
  `name in (".", "..")` 或含 `/`/`\` 或 `..` 在 `Path(name).parts` 中 ⇒ 返回 None。
  这正是 EXP-2026-0027 / 0032 的教训落地处。
- 自建解析器 = ① 引入第二条判据（与统一入口契约冲突，`test_change_dir_resolution_unify`
  的 AST 扫描会判红）② 重新打开路径遍历面。
- EXP-2026-0026 的教训：**顶部 import 不算数，判据要落到函数体** —— 测试必须断言
  `canon.py` 中 merge 路径的解析**调用**了统一入口，而非仅 import。

### 6. 归档 change 必须可用（读源 + 写根，不走 `require_active_change_dir`）

**方案**：`_resolve_change_dir` 已含 `include_archive=True` 回退 ⇒ 归档 change 直接可用。
`merge` **不调用** `require_active_change_dir`（那是**写路径专用**：命中 archive 就 exit 1）。

**为什么**：DELIVER 的时序是「先 `archive` 归档，再合并 canonical」—— ① 的 DELIVER
正是归档后才做合并的。若用 `require_active_change_dir`，`merge` 对自己的主要场景会直接拒绝。
写的是**根 canonical**（不是归档 change），故「归档拒绝写」的语义在此不适用。

### 7. `docs/UPSTREAM_PATCHES.md` 登记前置（动手前第一件事）

**方案**：Phase 3 第一个动作即在该表表体追加本 change 的登记行（8 列齐全：
`# | 文件 | 行号 | 修改原因 | 关联上游 issue/PR | 登记日期 | 登记人 | 预期回退版本`），
把「待登记」区的两条旧项**原样保留**（那是别人的欠账，不动）。

**为什么**：该文件自称「单一事实源：凡对 `upstream/` 内任何文件的修改，**必须**先于修改在此登记」。
本 change 将是**首个**正式登记项（表体现为空）。

### 8. 失败即响：非 0 退出 + 明确文案，部分成功要交代

**方案**：三类失败各自非 0 退出并打印可定位文案：
① 源 change 解析不到（含 `..`/分隔符被拒）② 目标已存在且内容不同（D3③）
③ 源缺 `meta.capability` / `meta.change_id`（D2）。多文件合并时**先汇总后动作**：
任一路径失败 ⇒ 整体退出且**说明已写 / 未写哪些**，不留半成品。

**为什么**：KG-092（钩子失败时 exit 0 且不上报）的教训；且 `merge` 是 DELIVER 的自动步骤，
静默失败会让「canonical 已合并」变成假象。

**备选及排除**：
- 备选 A：逐文件 try/except 继续 —— **排除**：会产出半合并状态，且属「静默降级」。

## Architecture

```
fstdd canon merge <change> [--dry-run]
   │
   ├─ D7  UPSTREAM_PATCHES.md 登记（Phase 3 动手前，一次性）
   │
   ├─ 解析源目录：_resolve_change_dir(root, <change>)     ← D5 唯一定义点（含 .. 拒绝）
   │        └─ 命中 archive/ 也放行                       ← D6
   │
   ├─ 枚举源 canonical 三类文件
   │        proposals/*.yaml   → 目标名 = meta.change_id    ┐
   │        specs/agent/*.yaml → 目标名 = meta.change_id    ├ D2 三分法
   │        specs/code/*.yaml  → 目标名 = meta.capability   ┘（缺字段 ⇒ 告警+跳过）
   │
   ├─ 决策每个目标文件（D3）
   │        不存在            → WRITE
   │        存在且逐字节相同   → SKIP-identical（不动作）
   │        存在且内容不同     → ERROR 退出（不覆盖）
   │
   ├─ _root_canonical_dir(root) = <repo>/canonical          ← D1 唯一定义点
   │        └─ _get_canon_dir(None) 委托它（顺带修 generate --all 扫空目录）
   │
   ├─ 维护 canonical/.canon-index.yaml（D3 同规则：同值不动 / 异值报错）
   │
   ├─ --dry-run ⇒ 只打印上述决策，不落盘                  ← D4 复用 _dryrun 守卫
   │
   └─ 退出码：全成 0；任一失败非 0 + 说明已写/未写哪些      ← D8
```

### 决策 ↔ What Changes ↔ Capability 映射

| 决策 | 对应 What Changes | Capability | 对应 SC |
|---|---|---|---|
| D1（根 canonical 路径收口） | C1 | canon-merge-automation | SC-002 |
| D2（命名三分法，元数据为唯一依据） | C2 | canon-merge-automation | SC-005 |
| D3（幂等：同值不动作 / 异值报错） | C1、C3 | canon-merge-automation | SC-003 |
| D4（`--dry-run` 复用 `_dryrun`） | C4 | canon-merge-automation | SC-001 |
| D5（change 名走 `find_change_dir`） | C1 | canon-merge-automation | SC-001、SC-005 |
| D6（归档 change 可用） | C4 | canon-merge-automation | SC-006 |
| D7（UPSTREAM_PATCHES 登记前置） | C5 | canon-merge-automation | SC-007 |
| D8（失败即响） | C1、C3、C4 | canon-merge-automation | SC-001、SC-003 |

> C1–C5 定义见 proposal.md §What Changes：
> C1 新增 `fstdd canon merge <change>`；C2 命名口径单一事实源；C3 幂等维护 `.canon-index.yaml`；
> C4 `--dry-run` 不写盘 + 归档 change 可用 + 合并后自跑 canon verify；C5 登记 `UPSTREAM_PATCHES.md`。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| **D1 改了 `_get_canon_dir(None)` 的返回值** ⇒ `canon init --project-level` 的落点从 `.fstdd/canonical/` 变为仓库根 `canonical/` | ① 该行为当前指向的是**空骨架**（0 个被跟踪文件）⇒ 实际无人依赖；② 全量根级 + 框架侧测试兜底（SC8）；③ CLI 冒烟 |
| `.fstdd/canonical/` 空骨架仍在盘上 ⇒ 后人可能再被误导 | **登记为欠账**（删除/或加 README 说明），不在本 change 动手 |
| `test_fstdd_matrix.py:151` 的注释与事实不符 | 同登记为欠账；本 change 的测试会以**仓库根**为准并显式断言 |
| 命名口径若选错，会把错误命名**自动化**写入根 canonical（比手工更危险） | D2 三分法有实测依据（21/16/23 计数）+ `--dry-run` 先预览 + 缺字段告警跳过；**历史存量不动**（non_goal） |
| 改 vendored 内核 ⇒ fork drift | D7 先登记（8 列齐全，含「预期回退版本」）；改动集中在**新增函数**，既有三命令逻辑零改 |
| 索引 `.canon-index.yaml` 三段缩进不一（proposals 2 空格 / specs 下 4 空格）⇒ 手写插行易错 | ③ 的实现用**结构化读写**（yaml.safe_load → 改 dict → dump），不按行插；同时补「读回后键数 +3」的断言 |
| 改 `cli/__init__.py` 影响 CLI 解析面 | 只在既有 `canon` 子解析器下加一个子命令；CLI 冒烟 + 全量测试 |
| 上游若已实现同名 `canon merge` ⇒ 冲突 | 登记时在「关联上游 issue/PR」列注明；同步时按「预期回退版本」逐条核对 |
