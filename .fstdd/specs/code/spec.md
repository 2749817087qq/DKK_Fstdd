# 行为规格 — change-isolation

**Change**: 2026-09-25-new-isolate-flag ｜ **Confidence**: high

## REQ-001 · 显式隔离形态，默认零漂移

- **SC-001** `--isolate worktree`（git 仓内）→ 独立 worktree + 显式分支，骨架**落在 worktree 内**，主工作区不被触碰
- **SC-002** 无 `--isolate` 且无配置 → 主工作区建骨架，**不建 worktree、不建分支**（逐字同改动前）
- **SC-003** `--help` → 列出 `--isolate` 与 `none`/`worktree`/`branch`

## REQ-002 · 分支显式命名

- **SC-004** worktree 模式 → `git worktree add -b <branch_prefix><change_dir_name>`，分支名不含路径派生后缀
- **SC-005** branch 模式 → `git checkout -b <branch_prefix><change_dir_name>`，不建 worktree

## REQ-003 · 不静默降级，不留半成品

- **SC-006** 非 git 工作树 + `worktree|branch` → 非 0 退出，**且不创建 change 目录**
- **SC-007** 脏工作区 + `branch` → 非 0 退出并建议 `worktree`，**不切分支**
- **SC-008** 分支名或目标路径已存在 → 创建前检出、非 0 退出、给清理命令，**不自动删除**

## REQ-004 · worktree 不污染被隔离的仓库

- **SC-009** 无配置 → 落在项目根**之外**（`<project_parent>/<project_name>.worktrees/<dir>`），主仓 `git status` 保持干净
- **SC-010** 有 `isolation.worktree_root` → 以该值为父目录

## REQ-005 · 隔离状态可见且不阻塞

- **SC-011** `new` 结束 → 输出一行隔离提示（当前形态 + 隔离命令）
- **SC-012** 全程 → **不调用 `input()`**

## REQ-006 · init 写配置且幂等无害

- **SC-013** `init` 后 `project.yaml` 含 `isolation`（`default`/`worktree_root`/`branch_prefix`）
- **SC-014** 已有 `isolation` 块或用户自定义键 → **原值保留**（只补缺失键）

## REQ-007 · 消费配置默认值，失败回退 none

- **SC-015** `isolation.default: worktree` + 无 `--isolate` → 按 worktree 建
- **SC-016** 配置缺失 / YAML 坏 / 取值非法 → 回退 `none` 并正常建骨架，**不报错**

## REQ-008 · 死代码消除

- **SC-017** `parallel` / `_setup_parallel_worktrees` → 0 命中
- **SC-018** `CHANGELOG` 记录移除

## REQ-009 · 隔离不得让门禁静默失效（**SPEC 阶段新增**）

- **SC-019** 主工作区有 hook 注册 → 一并复制进 worktree（使 worktree 内 guard 可触发）
- **SC-020** 主工作区无 hook 注册 → **明确告警**，不得静默通过

---

## 两条不变式（顺序/方向锁）

### 1. 失败必须先于副作用

```
解析形态 → 校验名 → [git 工作树? → 分支/路径冲突? → 脏树?] → 建 worktree/分支 → 落脚手架 → 复制 hook → 提示
                      └── 任一失败：非 0 退出，.fstdd/changes/<dir> 不得存在 ──┘
```

`worktree` 必须早于脚手架：否则 worktree 创建失败会留下半成品 change（SC-006/008）。

### 2. 配置读取的回落方向 = 最保守

```
显式 --isolate ──> 直接采用（无视配置）
未指定        ──> isolation.default ──缺失/坏/非法──> none（**不是** worktree）
```

回落到 `none` 而非 `worktree`：`none` 对用户仓库零写入，失败时副作用最小。
方向若倒置，一个坏 YAML 会让 `stdd new` 开始悄悄建 worktree。

## 与 W5（相位门作用域）的接口

本 change **不修改** Guard 判定链。worktree 默认位于项目根之外 ⇒ 在主工作区上下文命中
「项目外放行」；在 worktree 自己的上下文里 `project_root` 即 worktree 根，W5 的
`scope.paths` 判定照常生效 —— SC-001 的「各自只冻结自己作用域」由此成立。


<!-- 合并自 2026-09-26-finder-archive-fallback -->
# 行为规格 — change-dir-resolution

**Change**: 2026-09-26-finder-archive-fallback ｜ **Confidence**: high

## REQ-001 · 统一解析器，默认零漂移

- **SC-001** 不传 `include_archive` + change 只在 `archive/` → 返回 `None`（默认仍是「只查在办」，既有调用点逐字零漂移）
- **SC-002** 传 `include_archive=True` + change 只在 `archive/` → 返回 `.fstdd/archive/<name>`，且该目录含 `.fstdd.yaml`
- **SC-003** `changes/` 与 `archive/` 同名并存 → 取 `changes/<name>`（在办优先于归档）
- **SC-004** 短名（省略日期前缀）+ 归档件 → 后缀匹配在 `archive/` 同样生效
- **SC-005** `name=None` → 恒取 `changes/` 内 `st_mtime` 最大者；即使 `archive/` 内更「新」，也不取归档件
- **SC-006** 项目只有 `changes/` 没有 `archive/` → 正常返回或返回 `None`，**不抛异常、不创建 `archive/`**

## REQ-002 · 归档后四条命令不再因「找不到 change」失败

- **SC-007** `stdd validate <name>`（change 已归档）→ `rc=0`（修复前 rc=1「找不到 change」）
- **SC-008** `stdd status <name>`（change 已归档）→ `rc=0` 且输出该 change 状态（修复前 rc=1）
- **SC-009** `stdd canon verify <name>`（change 已归档、canonical 完整）→ `rc=0` 并输出通过项（修复前 rc=1「canonical/proposals/... not found」）
- **SC-010** `stdd structure merge <name>`（change 已归档、delta 存在）→ 读到该 delta，不再报「Delta not found」（修复前 rc=1）

## REQ-003 · 归档相关既有行为零漂移（反例守卫）

- **SC-011** 对**已归档** change 再次执行 `stdd archive <name>` → 非 0 退出并报找不到 change；`archive/<name>/` **原地不动**（不得解析到归档后把自己再移动一次）
- **SC-012** `stdd rollback <name>`（change 已归档）→ 仍能把该 change 从 `archive/` 恢复到 `changes/`（既有独立逻辑不回归）
- **SC-013** `stdd archive <name>`（change 未归档）→ 正常归档，`status` 置 `archived`（既有行为不回归）

---

## 两条不变式（顺序 / 方向锁）

### 1. 解析顺序：在办优先，归档只在显式开启时兜底

```
name 非空:
  changes/<name>            （须含 .fstdd.yaml）
  changes/*<name>           （后缀匹配，按名倒序取首个）
  ── include_archive=True 时继续 ──
  archive/<name>            （须含 .fstdd.yaml）
  archive/*<name>           （后缀匹配，按名倒序取首个）
  → None

name 为空:
  恒取 changes/ 内 st_mtime 最大者（**与 include_archive 无关**）
```

`name` 为空时不含归档：归档是终态，「当前 change」语义上不可能位于归档区；
否则 `stdd status`（无参）会显示一个已归档件，严重误导。

### 2. 方向锁：`include_archive` 默认 `False`，且 `archive` / `abort` 不得开启

```
archive.py / abort.py   ──> include_archive=False（默认，逐字不变）
validate / status / ci / diff / dependency_graph / extract_proposal
                        ──> include_archive=True（语义都是「查询某个 change」）
canon._get_canon_dir / structure.cmd_structure_merge
                        ──> 内部走统一解析（含归档回退）
gate.py / state.py      ──> 本次**不动**（只对在办 change 有意义）
```

方向若倒置（默认 `True`），`stdd archive` 会解析到 `archive/<name>` 并把**它自己再移动一次**
⇒ 目录丢失。SC-011 专门锚定此反例。

## 与 `rollback` 的接口

本 change **不修改** `rollback.py`。它已有独立的 `archive/` 搜索（`archive/` + `archive/aborted/`），
与统一解析器**并存而非替代** —— SC-012 锚定其既有行为不回归。
（`rollback.py` 内 `find_change_dir` 为未使用导入，保持原样。）

## 与「四解析器」根因的关系

修复前存在**四个各自独立、都硬编码 `changes/`** 的解析器：
`finder.py:5` / `canon.py:12`（纯路径拼接，**不走 finder**）/ `gate.py:22` / `state.py:16`。
本 change 收敛其中**有归档需求的两处**（finder 与 canon 的 canonical 定位），
`gate` / `state` 按 design Decision 5 保持原样 —— 改动面最小化，纯重构另立 change。
