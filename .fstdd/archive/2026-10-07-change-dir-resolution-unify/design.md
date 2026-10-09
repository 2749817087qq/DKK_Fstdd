# 归档生命周期收口：change 目录解析统一 + 归档/恢复状态自洽 — 技术设计

> change：`2026-10-07-change-dir-resolution-unify`（mode `thorough`，complexity_score 9）
> Phase 1 基线：`proposal.yaml`（`source_hash 658c04db4dcce882`）
> 观测基线：`observed_at = 2026-10-07T13:55:34+00:00`、`observed_base_git_sha = f7bf8ec39a9784c7a8812d8b4b4e6238d6fe1b46`（= v3.3.7 发布提交）

---

## Context

### 现状：同一件事有两套以上实现

`upstream/fstdd/cli/finder.py::find_change_dir(name, root, *, include_archive=False)` 是 2026-09-26
建立的**统一解析入口**，语义已有 spec 锚定（`change-dir-resolution` SC-001..013）：

```
name 非空：  changes/<name> → changes/*<name>  ── include_archive=True 时 ──→  archive/<name> → archive/*<name> → None
name 为空：  恒只取 changes/ 下 mtime 最新者（与 include_archive 无关）
```

但实测（@f7bf8ec）**10 处已走统一入口，5 处仍自建**：

| 模块 | 解析器 | archive 回退 | 实测 |
|---|---|---|---|
| `canon` / `ci`(×2) / `dependency_graph` / `diff` / `extract_proposal` / `status` / `structure` / `validate` | `finder.find_change_dir(..., include_archive=True)` | ✅ | rc=0 |
| `archive` / `abort` / `rollback` | `finder.find_change_dir(...)`（**刻意** `include_archive=False`） | 不适用 | rc=0 |
| **`phase.py::_find_change`(20-31)** | 自建（只扫 changes/） | ❌ | **rc≠0** |
| **`gate.py::_find_change_dir`(23-30)** | 自建 | ❌ | 代码确认 |
| **`state.py::_find_change_dir`(17-26)** | 自建 | ❌ | **rc≠0** |
| **`work.py::_find_change`(16-30)** | 自建 | ❌ | **rc≠0** |
| **`baseline.py::_resolve_change`(65-80)** | 自建 | ❌ | 代码确认 |

### 两类可观测的坏后果

1. **误导性报错**：三个模块报 `.fstdd.yaml not found in <name>`（`state` 甚至打印出
   `.fstdd\changes\<name>` 这个「它去错地方找」的路径）。读起来像「change 不存在」，
   实际是「本命令不支持归档区」——**把使用者引向错误的排查方向**。
2. **审计链缺环**：`gate amend-audit` 是**唯一**为「事后追认历史 Gate」设计的通道
   （`--gate` + `--confirmed-by` + `--evidence` 三参必填），却因解析器不支持归档而不可用。

### 同一族的两个状态机缺口

3. **`archive` 不闭合相位**：归档后 `phases.deliver.status` 悬空。实测 3 个历史归档 change：
   `2026-10-04-baseline-failures-zero` → `in_progress`；`2026-10-06-legacy-debt-cleanup` →
   `current_phase: build` + `deliver: pending`；`2026-10-05-upstream-baseline-alignment` → 唯一正确闭合者。
4. **`rollback` 无条件重置相位**：`rollback.py` 写死 `state["current_phase"] = "understand"`，
   而 `phases.*.status` 全部保留 ⇒ 恢复后 `current_phase=understand` 与
   `phases.understand.status=completed` **自相矛盾**，继续推进会回到 `spec` 而非原相位
   （`rollback` 的语义是「恢复」不是「重做」）。

### 约束条件

- `finder.find_change_dir` 的既有语义**不可改**（SC-001..006 已锚定，且 `archive`/`abort`/`rollback`
  依赖 `include_archive=False` 避免「归档的 change 被再次移动」—— SC-011 反例守卫）。
- 归档是 change 的终态；本 change **不为归档 change 开放写操作**（`proposal.yaml` non_goals）。
- 不新增 CLI 参数（YAGNI；`--allow-archived` 的动机已被 C3 消除）。

---

## Decisions

### D1. 单一入口强制化：5 个自建解析器全部替换为 `finder.find_change_dir`

**方案**：删除 `phase.py::_find_change` / `gate.py::_find_change_dir` / `state.py::_find_change_dir` /
`work.py::_find_change` / `baseline.py::_resolve_change`，一律改调
`finder.find_change_dir(name, root, include_archive=True)`。`baseline.py` 原有的「短名后缀匹配」由
`_resolve_in` 提供（精确名 → `*<name>` 后缀），**能力不降级**（其 `_resolve_change` 本来就只支持
精确 + 唯一后缀，`_resolve_in` 是其超集：多命中时取名字倒序首个而非返回 None）。

**为什么**：`finder.find_change_dir` 已有 spec + 测试锚定，是**已存在的正确答案**；5 个自建实现
是历史遗留。删掉重复实现 = 从根上消除「口径分裂」这一类缺陷（EXP-2026-0013 契约断层）。

**备选方案及排除原因**：
- 备选 A：保留自建实现，各自补一段 archive 回退 —— 5 份实现继续并存，下一次加命令时又会漏一处
  （本次缺陷的成因正是「上一次只补了 4 条命令」）。
- 备选 B：把 `find_change_dir` 改成默认 `include_archive=True` —— 会破坏 SC-001（默认语义零漂移）
  且让 `archive`/`abort` 有「解析到归档区后把自己再移动一次」的风险（SC-011）。
- 备选 C：抽一个公共基类 / Mixin 让命令模块继承 —— 本仓命令模块是函数式（`cmd_xxx(args)`），
  引入类层次属过度工程（YAGNI 第 7 级）。

### D2. 读/写语义分层：读放行、写拒绝并指路 `rollback`（`gate amend-audit` 例外）

**方案**：

| 命令 | 读/写 | 归档 change 上的行为 |
|---|---|---|
| `phase status` | 读 | ✅ 放行 |
| `phase advance` / `phase set` / `phase record-slice` | 写 | ❌ 拒绝（rc=1 + 准确文案） |
| `state`（查看 / `--resume`） | 读 | ✅ 放行 |
| `state --set` | 写 | ❌ 拒绝 |
| `work list` | 读 | ✅ 放行 |
| `work add` | 写 | ❌ 拒绝 |
| `baseline` 读路径 | 读 | ✅ 放行 |
| `baseline establish` | 写 | ❌ 拒绝 |
| `gate approve` | 写 | ❌ 拒绝 |
| **`gate amend-audit`** | 写 | ✅ **放行**（其设计用途即「事后追认归档 Gate」） |

**为什么**：归档即终态 ⇒ 写操作必须走 `rollback` 这个**显式**出口，而不是被静默改写。
同时「终态之后仍要能查询、能审计」是刚需 ⇒ 读路径必须放行（这也与既有 4 条命令
validate/status/canon verify/structure 的口径一致）。

**备选方案及排除原因**：
- 备选 A：全部放行（含写）—— 归档 change 可被静默改写，削弱「终态」语义；且 C3 已消除
  「必须写归档 change」的唯一动机。
- 备选 B：全部拒绝（含读）—— 与既有 4 条命令（validate/status/...）的既定口径直接冲突，
  且会把「查一个已交付 change 的状态」这种完全正当的操作也堵死。
- 备选 C：新增 `--allow-archived` 逃生口 —— YAGNI；`rollback` 已是更安全的显式出口
  （它带冲突检查、且把 change 真正恢复到在办态）。

### D3. 把「读/写差异」也收口到统一入口：新增 `require_active_change_dir()`

**方案**：在 `upstream/fstdd/cli/finder.py` 追加**一个**写路径专用入口：

```python
def require_active_change_dir(name=None, project_root=None) -> Path:
    """写路径专用。要求 change 处于在办状态。

    归档 ⇒ 打印准确拒绝文案（含「已归档」+ 归档路径 + rollback 指引）并 sys.exit(1)；
    未找到 ⇒ 打印「未找到」文案并 sys.exit(1)；找到 ⇒ 返回 changes/<name>。
    """
```

5 个模块的**写分支**统一调它，**读分支**统一调 `find_change_dir(..., include_archive=True)`。

**为什么**：若只在 5 个模块各写一遍「判断是否归档 + 打印 + 退出」，就等于**又造了 5 份实现**
—— 正是本 change 要消灭的形态（EXP-2026-0020：批量修改必须按「接收者/入口语义」收口，
而非按调用点散补）。收口到 `finder.py` 后，「什么算可写」只有一个定义点。

**备选方案及排除原因**：
- 备选 A：各模块各写拒绝逻辑 —— 重复 5 份，且文案/退出码必然漂移。
- 备选 B：把守卫下沉到 `find_change_dir` 加 `for_write=True` 参数 —— 会让一个纯解析函数
  带上「打印 + 退出」的副作用，破坏其可测试性（现有 SC-001..006 全靠返回值断言）。
- 备选 C：新开一个 `_change_guard.py` 模块 —— 多一个文件却只有 1 个函数，且与 `finder.py`
  强内聚（都要知道归档路径规则），并入 `finder.py` 更省。

### D4. 拒绝文案契约：统一文案 + 非零退出码

**方案**：归档拒绝文案固定为（单行，含三要素）：

```
  已归档：<name>（.fstdd/archive/<name>）；如需修改请先 fstdd rollback <name>
```

并 **`sys.exit(1)`**。三要素 = ①「已归档」状态词 ② 归档实际路径 ③ `rollback` 出口指引。

**为什么**：SC-002 要求「输出同时含『已归档』与『rollback』字样」；而退出码必须非 0，
否则脚本/门禁无法区分「成功」与「被拒绝」（EXP-2026-0016 的教训：判据要结构化，不能只看文本）。

**备选方案及排除原因**：
- 备选 A：只打印不退出非 0 —— 调用方（如批处理、hook）会以为成功。
- 备选 B：复用「未找到」文案 —— 正是本次要消除的误导（把「已归档」说成「不存在」）。
- 备选 C：抛异常 —— 本仓 CLI 全用 `print + sys.exit`，异常会打出 traceback，破坏 UX 一致性。

### D5. `archive` 归档时闭合相位（只写一个字段）

**方案**：`archive.py` 在 `shutil.move` 成功后，读归档目录的 `.fstdd.yaml`，写
`state["phases"]["deliver"]["status"] = "completed"`，其余字段**一个不碰**。

**为什么**：归档 = 交付终态，`deliver` 相位理应闭合。当前悬空（实测 3 例）会让
`phase status` / `status` 的输出自相矛盾（`status: archived` 却 `deliver: in_progress`），
也让「归档是否真的走完了交付」无法用机器判断。

**备选方案及排除原因**：
- 备选 A：让 `phase advance` 支持归档 change 来手动闭合 —— 与 D2「写路径拒绝」直接矛盾。
- 备选 B：不闭合，只在归档输出里提示「deliver 相位未闭合」—— 治标；且 SC-004 要机器可验证。
- 备选 C：连带把 `current_phase` 也设为 `deliver` —— 超出必要；`current_phase` 的语义由 D6 管。

### D6. `rollback` 保留原相位

**方案**：删除 `rollback.py` 中的 `state["current_phase"] = "understand"`，改为：

1. 若 `.fstdd.yaml` 已有 `current_phase` ⇒ **原样保留**；
2. 若无（老数据）⇒ 回落到「首个非 completed 的相位」，再兜底 `understand`。

同时只写 `state["status"] = "active"`。

**为什么**：`rollback` 的语义是「恢复」（CLI help：「从 archive 恢复已归档的 change」），
不是「重做」。保留原相位后，「归档 → 恢复 → 继续推进」才能接得上；否则会把一个已到
`deliver` 的 change 打回 `understand`，与 `phases.*.status` 形成矛盾态。

**备选方案及排除原因**：
- 备选 A：加 `--reset-phase` 开关 —— YAGNI（真需要重做时应另开 change，而不是复活旧 change）。
- 备选 B：连带重置 `phases.*` 全部为 pending —— **更危险**：会抹掉 Gate 确认记录（审计不可逆损失）。
- 备选 C：保持现状（重置为 understand）—— 与本 change 的 C4 目标直接冲突。

### D7. 防复发：契约扫描（静态）+ 逐命令行为断言（动态）**双层**

**方案**：

1. **静态契约扫描**（新增测试）：遍历 `upstream/fstdd/cli/commands/*.py`，凡「接受 change 名」
   的模块**必须**出现 `finder` 的统一入口调用（`find_change_dir` 或 `require_active_change_dir`）；
   违规即 FAIL。判据用 **AST**（不是子串），并**自带双向自检**：构造「自建解析器」违例样本
   断言能抓到、构造「走统一入口」合法样本断言不误报（EXP-2026-0021）。
2. **动态行为断言**（新增测试）：对**真实归档 change**（本仓 `.fstdd/archive/` 下任一）逐命令实测：
   读必 rc=0、写必 rc=1 且文案含「已归档」与「rollback」、`gate amend-audit` 必放行。

**为什么**：静态判据是**模块级**的，识别不了「模块里既有统一入口调用、又有一处自建解析」
（EXP-2026-0024：判据粒度 = 模块，缺陷粒度 = 调用点）。故必须配行为断言作第二层防线 ——
这是上一版（3.3.7）用真实缺陷换来的教训。

**备选方案及排除原因**：
- 备选 A：只做静态扫描 —— 3.3.7 已证明模块级静态判据会漏判（`canon verify --dry-run` 即因此漏网）。
- 备选 B：只做行为断言 —— 无法防「新命令又自建解析器」（新增模块没有对应行为断言）。
- 备选 C：扫描器判据用正则子串 —— EXP-2026-0016 假阳性 + EXP-2026-0024 漏判，两个方向都错过。

### D8. 破坏性写操作的安全网：白名单字段 + 闸门字段字节级不变

**方案**：C3/C4 的写操作在测试中以「快照对比」断言：

- 允许变化的字段：C3 仅 `phases.deliver.status`；C4 仅 `current_phase` 与 `status`；
- **禁止变化**：`phases.*.confirmed_at` / `confirmed_by` / `confirmed_evidence`（Gate 审计链）
  —— 以「归档前 vs 归档后」「rollback 前 vs rollback 后」的**逐字段相等**断言锚定。

**为什么**：`archive` / `rollback` 都是**移动目录 + 写状态文件**的破坏性操作（EXP-2026-0015：
「隔离=移动」曾造成真实事故）。把「允许动什么」写成白名单，比「不要动错」这种口头约束可靠。

**备选方案及排除原因**：
- 备选 A：只断言「文件存在」—— 无法发现闸门字段被改写。
- 备选 B：整文件哈希相等 —— C3/C4 本来就要改字段，整文件哈希必然不等，断言无意义。
- 备选 C：依赖 `guard.py` 的相位完整性检查 —— 它只查「前序阶段 completed + 闸门 confirmed_at」，
  查不出「闸门 evidence 被改写」。

---

## 决策 → What Changes → Capability 映射

| What Changes | 决策 | Capability |
|---|---|---|
| C1（5 个模块改走统一入口） | D1 + D3 | `change-dir-resolution` |
| C2（写路径准确拒绝 + `amend-audit` 例外） | D2 + D3 + D4 | `change-dir-resolution` |
| C3（`archive` 闭合相位） | D5 + D8 | `archive-state-consistency` |
| C4（`rollback` 保留原相位） | D6 + D8 | `archive-state-consistency` |
| C5（契约扫描 + 行为断言） | D7 | `change-dir-resolution` |

- **`change-dir-resolution`**（MODIFIED）：C1 / C2 / C5 —— 解析口径统一与读写语义分层。
- **`archive-state-consistency`**（NEW）：C3 / C4 —— 归档与恢复两端的相位状态自洽。

---

## Architecture

### 调用链（修复后）

```
CLI 分发（cli/__init__.py）
        │
        ├── 读路径 ──→ finder.find_change_dir(name, root, include_archive=True)
        │                 └─ _resolve_in(changes/, name) → _resolve_in(archive/, name) → None
        │                    ▲
        │                    └── phase status / state(读) / work list / baseline(读)
        │                        gate(查询) / 既有 canon·ci·diff·validate·status·structure…
        │
        └── 写路径 ──→ finder.require_active_change_dir(name, root)     ★ 本 change 新增
                          ├─ 命中 changes/  ⇒ 返回 Path（继续执行）
                          ├─ 命中 archive/  ⇒ 打印「已归档：… 请先 fstdd rollback …」+ exit(1)
                          └─ 都未命中      ⇒ 打印「未找到」+ exit(1)
                             ▲
                             └── phase advance/set/record-slice · state --set · work add
                                 baseline establish · gate approve
                                 （例外：gate amend-audit 走读路径，放行归档）
```

### 归档 / 恢复的状态迁移（C3 / C4）

```
                   ┌──────────────── archive <name> ────────────────┐
   changes/<name>  │  move → archive/<name>                          │  archive/<name>
   status: active  │  status            : active → archived          │  status: archived
   current_phase: P│  phases.deliver    : * → completed   ← C3 新增   │  current_phase: P  ← C4 保留
                   │  phases.*.confirmed_* : 一个不碰                 │
                   └─────────────────────────────────────────────────┘
                                        │
                                        │ rollback <name>
                                        ▼
                   ┌─────────────────────────────────────────────────┐
   changes/<name>  │  move → changes/<name>                          │
   status: active  │  status            : archived → active          │
   current_phase: P│  current_phase     : **保留原值 P**   ← C4 修复  │
                   │  phases.*          : 一个不碰（含闸门字段）      │
                   └─────────────────────────────────────────────────┘
```

### 数据流：拒绝路径（D2/D4）

```
require_active_change_dir("2026-10-07-tool-defect-fixes", root)
   ├─ find_change_dir(..., include_archive=True)
   │     ├─ changes/ 未命中
   │     └─ archive/2026-10-07-tool-defect-fixes 命中
   ├─ 判定：命中路径在 archive/ 下 ⇒ 归档态
   ├─ print("  已归档：2026-10-07-tool-defect-fixes（.fstdd/archive/2026-10-07-tool-defect-fixes）；"
   │         "如需修改请先 fstdd rollback 2026-10-07-tool-defect-fixes")
   └─ sys.exit(1)          ← 修复前：各模块打印 ".fstdd.yaml not found in <name>"
```

---

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| 批量替换 5 个解析器时误伤 `archive`/`abort` 的 `include_archive=False` 语义，造成「归档的 change 被再次移动」 | 不动这三处的调用（约束已写入 proposal）；沿用 SC-011 反例守卫；契约扫描 + 逐命令行为断言双向覆盖 |
| `_resolve_in` 的「多命中取名字倒序首个」与 `baseline._resolve_change` 的「多命中返回 None」语义不同 | 在 design 中显式记录该差异；新增「多命中」场景的行为断言，确认取首个不误伤既有用法 |
| C3/C4 写状态文件时误改闸门字段，破坏审计链（不可逆） | D8 白名单 + 逐字段相等断言；只写 1–2 个字段；对 3 个历史归档 change 做只读回归 |
| 契约扫描是模块级判据，可能漏判「模块内局部自建解析」 | D7 双层：静态扫描 + 真实归档 change 的逐命令行为断言（EXP-2026-0024） |
| 新增的 `require_active_change_dir` 与 `find_change_dir` 双入口可能被误用（写路径用了读入口） | 命名显式（`require_*` 前缀 + docstring 首行写明「写路径专用」）；契约扫描要求写分支必须出现 `require_active_change_dir` |
| 拒绝归档写操作后，若用户确有正当需求（如修正归档 change 的错别字）会被挡住 | 文案直接给出 `rollback` 出口；`rollback` 带冲突检查（`changes/<name>` 已存在则拒绝）且保留原相位（C4），是一条安全可逆的路 |
| 对 `.fstdd/archive/` 下**全部**历史 change 做行为断言可能因老数据形态差异而不稳 | 行为断言只取「最近 1 个归档 change」作样本 + 用 `tmp_path` 构造合成归档 change 覆盖边界（短名后缀、同名冲突、无 `archive/`） |

---

## 经验库 / 知识图谱命中 → 决策映射

| 命中 | 严重度 | 本 change 的落地 |
|---|---|---|
| **EXP-2026-0013** 声明形态 ≠ 实际可匹配形态 | high | **D1 / D3**：统一入口的声明（docstring 说支持 archive 回退）与实际调用面必须一致；扫描器用**声明样例**做参数化输入 |
| **EXP-2026-0015** 隔离=移动的破坏性副作用 | high | **D8**：C3/C4 的白名单字段 + 闸门字段字节级不变断言 |
| **EXP-2026-0016** 纯文本扫描假阳性 | low | **D7**：扫描器判据改 AST 结构化，不用子串 |
| **EXP-2026-0020** 按「方法名」而非「接收者语义」选目标 | high | **D1 / D3**：批量替换按**调用点语义**收窄（`archive`/`abort`/`rollback` 三处必须保持 `include_archive=False`），替换后回扫调用面 |
| **EXP-2026-0021** 审计工具匹配面比声称的窄（假绿） | high | **D7**：契约扫描器自带双向自检（违例样本能抓到 / 合法样本不误报） |
| **EXP-2026-0023** RED 取证即执行旧代码，破坏性行为的取证会造成事故 | high | Phase 3 纪律：RED 取证在隔离副本进行（上一版已固化该教训） |
| **EXP-2026-0024** 模块级静态判据漏判局部漏点 | high | **D7**：静态扫描 + 行为断言**双层**（本 change 的核心防线） |
| **EXP-2026-0025** 放宽判据引入新误判 | medium | **D7**：扫描器上线前对全仓模块跑一遍断言 0 违规，并对历史归档 change 回归 |
| **KG-092** 失败静默腐烂 | high | **D4**：拒绝必须非 0 退出码 + 明确文案，不允许静默 |
| **KG-093** 声明了约束但从未生效 | high | **D1 / D3**：本 change 的根因即此（统一入口存在但 5 个模块从未调用） |
| **KG-094** 断言只覆盖少数几个字段 | critical | **D8**：逐字段相等断言（不是抽检几个字段） |
| **KG-095** 第二层防线不可观测 | medium | **D4**：拒绝文案含三要素，可被 grep / 脚本判断 |
