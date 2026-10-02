# Test Plan — 2026-09-26-guard-scope-unbound

## Bug 1: Guard-fix-loop 例外（循环依赖解除）

### TC-GF-001 (P0) — guard change understand 阶段放行 guard.py
**GIVEN**: active change = `2026-09-26-guard-scope-unbound`, phase = understand
**WHEN**: 调用 `fstdd guard check --hook-stdin <guard.py_path>`
**THEN**: exit code = 0, 放行

### TC-GF-002 (P0) — guard change understand 阶段仍阻断非 guard.py
**GIVEN**: active change = `2026-09-26-guard-scope-unbound`, phase = understand
**WHEN**: 调用 `fstdd guard check --hook-stdin <tools/verify_notices.py_path>`
**THEN**: exit code = 2, 阻断 + 提示 "Guard-fix loop override 仅放 guard.py"

### TC-GF-003 (P0) — 非 guard change understand 阶段正常阻断 guard.py
**GIVEN**: active change = `2026-09-19-notices-authenticity-gate`, phase = understand
**WHEN**: 调用 `fstdd guard check --hook-stdin <guard.py_path>`
**THEN**: exit code = 2, 阻断（无 override，正常 understand 封锁）

### TC-GF-004 (P1) — guard change spec 阶段放行 guard.py
**GIVEN**: active change = `2026-09-26-guard-scope-unbound`, phase = spec
**WHEN**: 调用 `fstdd guard check --hook-stdin <guard.py_path>`
**THEN**: exit code = 0

### TC-GF-005 (P1) — 无 active change 仍阻断 guard.py
**GIVEN**: 无 active change (所有 change 都是 completed/archive)
**WHEN**: 调用 `fstdd guard check --hook-stdin <guard.py_path>`
**THEN**: exit code = 2, 完全阻断（无 override）

## Bug 2: Guard status 版本号动态读取

### TC-GF-006 (P1) — version.yaml 存在时显示实际版本
**GIVEN**: `.fstdd/version.yaml` 含 `version: "3.0.5"`
**WHEN**: 调用 `fstdd guard status`
**THEN**: 输出含 `V3.0.5` 不含 `V2.9.4`

### TC-GF-007 (P2) — version.yaml 不存在时 fallback
**GIVEN**: `.fstdd/version.yaml` 被临时移走
**WHEN**: 调用 `fstdd guard status`
**THEN**: 输出含 `unknown` 不含 crash

## Bug 3: Phase Lag 假阳性（非阻塞，先审计）

### TC-GF-008 (P2) — 归档 change completed_at 为空时的行为
**GIVEN**: 归档 change `.fstdd.yaml` 里 `completed_at: ""` 或不存在
**WHEN**: 调用 `fstdd guard status`
**THEN**: （审计后确定）要么不再报 lag 警告，要么提示文案更清晰

---

## 执行矩阵

| Bug | TCs | 优先级 |
|---|---|---|
| Bug 1 (guard-fix-loop) | GF-001..005 | P0: 3, P1: 2 |
| Bug 2 (version) | GF-006, GF-007 | P1: 1, P2: 1 |
| Bug 3 (lag) | GF-008 | P2: 1 |

## 目标文件

- `upstream/fstdd/cli/commands/guard.py` — 主修改
- `.fstdd/version.yaml` — 只读
