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
