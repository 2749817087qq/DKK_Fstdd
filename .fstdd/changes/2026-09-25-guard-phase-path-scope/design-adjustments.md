# 设计调整记录 — 2026-09-25-guard-phase-path-scope

> mode: standard | task_type: code
> **收口追溯补记（2026-10-04）**：本文件为 change 收口时按实况重建，用于替代长期缺失的
> 调整记录。内容以仓库既有证据为准。

## 汇总

| 项 | 数值 |
|----|------|
| 大偏离（变更对外接口 / 行为语义 / 架构决策） | **0** |
| 小偏离（实现细节，未改设计基线） | **0** |
| 追补（收口时补全，不属设计偏离） | **2 处测试** |

## 说明

1. **设计基线未变**：`design.md` 的 5 项决策（scope 声明来源 = canonical proposal `scope:` 块、
   无声明维持全局冻结 fail-closed、范围外 warn-only 放行、路径先归一化再匹配、旧修订副本
   排查独立立项）在实现中**逐条落地**，`guard.py` 的判定序与 `design.md` 的 Architecture
   一致（硬阻断 → agent runtime 豁免 → 相位门 → 作用域收窄）。
2. **`4eec636` 已实现后追加的 `V3.0.9` 修补**（作用域变量函数级预置默认值，消除无 active change
   时 `UnboundLocalError` fail-open）属**后续独立修订**，已在 `.fstdd/archive/2026-09-26-guard-scope-unbound`
   收口，不记为本 change 的偏离。
3. **追补 2 处 P0 测试**：`test-plan.md §五` 原列「合并前必补」的 SC-005 / SC-010「已声明 scope」
   变体此前未落地，收口时补 `test_tc_scope_013` / `test_tc_scope_014`。二者属**补齐计划内既有
   要求**，非设计偏离。
