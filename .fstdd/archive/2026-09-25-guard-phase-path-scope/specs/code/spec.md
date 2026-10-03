# 行为规格 — phase-gate-path-scope

**Change**: 2026-09-25-guard-phase-path-scope ｜ **Confidence**: high

## REQ-001 · 相位门按 change 作用域判定

- **SC-001** 只读相位 + 已声明 scope + 目标**在范围内** → `exit 2` 拦截，并提示扩展 `scope.paths`
- **SC-002** 只读相位 + 已声明 scope + 目标**在范围外** → warn-only 输出 + `exit 0` 放行

## REQ-002 · 未声明作用域 ⇒ fail-closed

- **SC-003** 无 `scope` 块或 `paths` 为空 → 维持现状全局拦截 `exit 2`（**无行为漂移**）

## REQ-003 · 硬阻断保持全局粒度

- **SC-004** 任何相位写 `GATE<N>_APPROVED` → `exit 2`
- **SC-005** 直接改 `.fstdd.yaml` 的 `confirmed_*` 字段 → `exit 2`

## REQ-004 · 路径先归一化再匹配

- **SC-006** `..` 穿越出项目根（无法 `relative_to`）→ 视为范围外 → warn-only 放行
- **SC-007** 目录模式（`/` 结尾）匹配其下所有文件 → 范围内 → 拦截

## REQ-005 · 既有放行通道不变

- **SC-008** 只读相位编辑 change 内 YAML-first 产物 → `exit 0`（与现状逐字一致）
- **SC-009** 可编辑相位（build/deliver）编辑任意项目文件 → `exit 0`
- **SC-010** `.workbuddy-ai/` 下任意路径 → `exit 0`（agent runtime 豁免不受 scope 影响）

## 判定序（防退化顺序锁）

```
硬阻断(SC-004/005) → agent runtime 豁免(SC-010) → YAML-first 产物(SC-008)
  → 可编辑相位(SC-009) → 【新增】只读相位 + scope 判定(SC-001/002/003/006/007)
```

顺序不得倒置：新增分支必须位于硬阻断与豁免**之后**，否则可把
GATE token 挪进「范围外」而绕过门禁。
