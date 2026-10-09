# 3.3.7+ 切片执行计划 — 归档生命周期收口

## Dependency Graph Summary

```
  零依赖节点（两者可并行）                  实测 dependency-graph：
  ┌──────────────────────────────┐          nodes  = 2
  │ S1 archive-state-consistency │          edges  = 0   ← 无任何依赖
  ├──────────────────────────────┤          cycles = []  ← 无环
  │ S2 change-dir-resolution     │          zero_dependency = 两者皆是
  └──────────────────────────────┘
                                             故「并行组」仅表达风险分层，
                                             实际由单 agent 串行执行。
```

**并行化说明**：
- 两者**文件集不相交**（S1 = `archive.py` + `rollback.py`；S2 = `finder.py` + `phase/gate/state/work/baseline.py`）
- 故无人工依赖；**实际执行顺序 = S1 → S2**（风险升序：S1 🟢 中 → S2 🟡 高），
  让较小的切片先跑通「tmp_path 构造 change + 跑 CLI」的测试骨架

## Slice Execution Plan

| # | capability | 优先级 | 风险 | 工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|-----------|--------|------|------|--------|---------|---------|------|
| 1 | archive-state-consistency | P0 | 🟢 中 (3) | M | 组1 | TC-ASC-001..006 | `archive.py` 归档时闭合 `phases.deliver.status`；`rollback.py` 保留原 `current_phase`（老数据兜底） | 无 |
| 2 | change-dir-resolution | P0 | 🟡 高 (4) | L | 组1 | TC-CDR-001..012 | `finder.py` 新增 `require_active_change_dir()`；5 个模块删自建解析器改走统一入口；读放行 / 写拒绝 / `amend-audit` 例外；契约扫描测试 | 无 |

## Rationale

### Slice 1: archive-state-consistency（P0，🟢 中风险）
- **依赖关系**：零依赖（`archive.py` / `rollback.py` 与 `finder` 的解析路径无交集：
  `archive.py` 用 `find_change_dir(..., include_archive=False)`（S2 不改该语义），
  `rollback.py` 直接扫 `archive/` 不调 `finder`）。
- **风险分析**：经验库命中 **EXP-2026-0015**（high，「隔离=移动」的破坏性副作用，+2）；
  Scenario 5（不 >5，+0）；跨模块（`archive` + `rollback`，+1）；NEW（+0）⇒ **3 → 🟢 中**。
  ⚠️ 虽评级为中，但它**直接写 change 状态文件**，写错会破坏**不可逆的闸门审计链**
  ⇒ 验证强度按高风险执行（D8 白名单 + 逐字段相等断言）。
- **工作量估算**：M —— 2 个源文件（各 1 处小改）+ 1 个新测试文件 + 6 个 TC。

### Slice 2: change-dir-resolution（P0，**高风险**）
- **依赖关系**：零依赖（唯一被 S1 触及的 `archive.py`/`rollback.py` 不在本切片文件集内）。
- **风险分析**：经验库命中 **EXP-2026-0013**（high，契约断层，+2）+ **EXP-2026-0021/0024**（high，审计器假绿 / 判据粒度错配，+2，按最高一条计）；
  Scenario 10 > 5（+1）；跨模块（`finder` + 5 个命令模块，+1）；
  MODIFIED 但**接口不变**（新增函数、不改既有签名，+0）⇒ **4 → 🟡 高**。
- **工作量估算**：L —— 6 个源文件（1 新增函数 + 5 模块改解析与加守卫）+ 1 个新测试文件 + 12 个 TC。

## 切片验证口径（B3.4 强制）

每个切片完成后必须同时满足三项，否则不得进入下一切片：

1. **TC 覆盖**：该切片全部 TC-ID 都有对应测试函数（100%）
2. **产出物核对**：`slices.md` 的「实现目标」逐项存在
3. **测试运行**：该切片新增测试 **> 0** 且全部通过；同时跑既有回归
   （`test_phase` / `test_gate` / `test_state` / `test_state_coverage` / `test_rollback` /
   `test_archive` / `test_finder` / `test_finder_archive_fallback` /
   `test_changes_dir_consistency` / `test_baseline_ops` / `test_canon_dchash_ops`）

> ⚠️ **本 change 的两条自设纪律**（因触及破坏性命令）：
> - **所有涉及 `archive` / `rollback` 的测试一律在 `tmp_path` 合成项目内进行**，
>   对仓库内真实 change **只做只读**操作；
> - **RED 取证必须在隔离环境**，不在主工作区回退修复后直接跑（EXP-2026-0023）。
