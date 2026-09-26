# change 目录解析增归档回退 - 技术设计

## Context

- **技术栈**：Python 3.11，FSTDD CLI（`upstream/fstdd/cli/`），pytest 838 例全量套件。
- **当前系统状态**：change 目录有两处落点 —— 在办 `.fstdd/changes/<name>/`、归档 `.fstdd/archive/<name>/`。
  `stdd archive` 会把目录从前者 `shutil.move` 到后者，并把 `state["status"]` 置为 `archived`。
- **约束**：本 change 属上游 vendor 代码（`upstream/`）的修改，须保持向后兼容；既有 9 个
  `find_change_dir` 调用点与 `rollback` 的独立 archive 搜索逻辑**均不得回归**。
- **实测问题**（见 proposal 证据）：归档后 `validate` / `status` / `canon verify` /
  `structure merge` 四条命令 rc=1。根因是**四个各自独立的解析器**都只认 `changes/`。

## Decisions

### 1. 归档回退放在统一解析器，用**关键字参数**按调用点语义选择

**方案**：`finder.find_change_dir(name=None, project_root=None, *, include_archive=False)`。
`include_archive=True` 时解析顺序为
`changes/ 精确 → changes/ 后缀 → archive/ 精确 → archive/ 后缀`。

**为什么**：
- **默认 `False` 保证零漂移** —— 9 个既有调用点中，未显式传参的（`archive`、`abort`）行为逐字不变。
- 用**关键字参数**而非位置参数，避免既有位置调用被静默改变语义。
- 集中一处 ⇒ 可被单测穷举覆盖，不会出现「第 N 个解析器」再次漏掉归档。

**备选方案及排除原因**：
- **备选 A：把 `find_change_dir` 改成默认含归档** —— 排除。`archive.py` 会因此解析到
  `archive/<name>` 并把**它自己再移动一次**（自我移动，目录丢失）；且 9 个调用点语义被静默改变。
- **备选 B：在各调用点各自补 `if not found: 查 archive`** —— 排除。重复逻辑、易漏、无法集中测试，
  正是「四个解析器」这一根因的翻版。
- **备选 C：只改 DELIVER skill 的步骤顺序**（把归档挪到 canon/structure 之后）—— 排除。
  只能绕开 `canon verify` / `structure merge` 的**执行时机**问题，无法覆盖
  「归档后**查询**」这一合法语义（`validate` / `status` / `canon verify` 本就该能查归档件）；
  且「顺序正确」不应成为工具正确性的前提。

### 2. `canon._get_canon_dir` 改走统一解析（而非自己再补一段回退）

**方案**：`_get_canon_dir(project_root, change_name)` 在 `change_name` 非空时调用
`find_change_dir(change_name, project_root, include_archive=True)`，取其 `canonical/` 子目录。

**为什么**：它是 `canon verify` 失败的**直接原因** —— 纯路径拼接、**根本不走 finder**。
若只改 `finder`，`canon verify` 仍然 rc=1（实测证据见 proposal）。

**备选方案及排除原因**：
- **备选：只改 finder.py** —— 排除，对 `canon verify` 无效（已实测）。
- **备选：给 canon 单独写一份 archive 回退** —— 排除，制造第 5 个解析器。

### 3. `name=None` 时**始终**只查在办（`changes/`）

**方案**：`include_archive` 只影响「按名字解析」的路径；`name` 为空时无论参数取值，
都只在 `changes/` 取最近修改的那个。

**为什么**：「当前 change」语义上**不可能**位于归档区（归档即终态）。若允许，
`stdd status`（无参）会显示一个已归档件，严重误导。

**备选方案及排除原因**：**备选：None 时也含归档** —— 排除，语义错误。

### 4. 同名时 `changes/` 优先于 `archive/`

**为什么**：`stdd rollback` 会把归档件恢复回 `changes/`，而 archive 侧可能残留副本
（`archive/aborted/` 等）。「在办优先」符合直觉，也避免误操作刚恢复的件。

### 5. 本次**不**统一 `gate.py` / `state.py` 的重复解析器

**方案**：这两个模块内的 `_find_change_dir` 保持原样（只查 `changes/`）。

**为什么**：Gate 只能确认**在办** change 的 Gate，`state` 只读写在办 change 的 resume 上下文
—— 二者**无归档需求**。改动面越小越好，纯重构另立 change。

**备选方案及排除原因**：**备选：顺手统一** —— 排除，无 bug 收益却扩大回归面。

## Architecture

调用点 → 语义 → 是否含归档：

```
调用点                              语义                 include_archive
────────────────────────────────────────────────────────────────────────
archive.py       :16               归档（只能看在办）     False（默认）
abort.py         :16               中止（只能看在办）     False（默认）
validate.py      :16               校验（查归档合法）     True
status.py        :13               查询（查归档合法）     True
ci.py            :242 / :515       查询                 True
diff.py          :14               查询                 True
dependency_graph.py :169           查询                 True
extract_proposal.py :111           查询                 True
canon._get_canon_dir :12           定位 canonical        True（内部走统一解析）
structure.cmd_structure_merge      读 code-structure-delta True
gate.py / state.py                 在办专用（本次不动）    —
```

解析顺序（`find_change_dir`）：

```
name 非空:
  include_archive=False:
    changes/<name>            （须含 .fstdd.yaml）
    changes/*<name>           （后缀匹配，按名倒序取首个）
    → None
  include_archive=True:
    上述两条
    archive/<name>            （须含 .fstdd.yaml）
    archive/*<name>           （后缀匹配，按名倒序取首个）
    → None

name 为空:
  恒在 changes/ 取 st_mtime 最大者（始终，与 include_archive 无关）
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| `archive` 误解析到 `archive/` ⇒ 目录自我移动、数据丢失 | 默认 `include_archive=False`；TC-FAF-011 反例锚定 |
| 归档区里没有 `.fstdd.yaml` 的杂目录被误判为 change | 复用既有校验（目录须含 `.fstdd.yaml`）；TC-FAF-006 覆盖 |
| `rollback` 的独立 archive 逻辑被回归 | 不改 `rollback.py`；TC-FAF-012 锚定既有行为 |
| `changes/` 与 `archive/` 同名导致误取 | `changes/` 优先；TC-FAF-003 锚定 |
| 哨兵 `audit_silent_except.py` 行号漂移（本 change 会**插入**代码到多个含吞异常点的文件） | 每片收尾跑 `audit_silent_except.py --check`（见 skill §8.1） |
| 双视图 spec 使 scenario 计数翻倍 ⇒ `validate` 报 TC < Scenario | 精简视图 `specs/code/spec.md` **不用** `#### Scenario:` 标题（用 `- **SC-xxx**`） |
| `find_change_dir` 成为热点被后续 change 继续加分支 | 本次即把它收敛为**唯一**解析入口；`canon` 已回归 |
