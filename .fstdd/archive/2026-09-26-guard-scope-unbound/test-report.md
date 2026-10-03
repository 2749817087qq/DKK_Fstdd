# test-report：2026-09-26-guard-scope-unbound

**change**：`2026-09-26-guard-scope-unbound`
**日期**：2026-10-02（收口补录 2026-10-03）
**结论**：🟡 归档时仅记录笼统 Gate 3 证据，未留逐 TC 执行明细

> 本 change 归档时 DELIVER 未闭环，无独立 `test-report.md`。以下内容全部据本目录内既有
> `.fstdd.yaml`、`test-plan.md`、`design.md` 如实回填，未新增任何测试数字、命令输出或结论。

---

## 一、归档证据（逐字引用）

`.fstdd.yaml` → `phases.build.confirmed_evidence` 原文：

> 开发总工 self-confirm Gate 3。design.md 重写（3 个实际 bug），test-plan.md 8 TC 全覆盖（P0×3 + P1×3 + P2×2）。修法：Bug 1 guard-fix-loop 例外最小改动，Bug 2 version.yaml 动态读，Bug 3 先审计再修。目标文件 guard.py + version.yaml。

## 二、测试方案（取自本目录 `test-plan.md` 的方案定义，非执行结果）

| Bug | TC-ID | 覆盖点 | 优先级 |
|---|---|---|---|
| Bug 1 guard-fix-loop | TC-GF-001 | guard change understand 阶段放行 guard.py | P0 |
| Bug 1 | TC-GF-002 | guard change understand 阶段仍阻断非 guard.py | P0 |
| Bug 1 | TC-GF-003 | 非 guard change understand 阶段正常阻断 guard.py | P0 |
| Bug 1 | TC-GF-004 | guard change spec 阶段放行 guard.py | P1 |
| Bug 1 | TC-GF-005 | 无 active change 仍阻断 guard.py | P1 |
| Bug 2 version | TC-GF-006 | version.yaml 存在时显示实际版本 | P1 |
| Bug 2 | TC-GF-007 | version.yaml 不存在时 fallback（unknown 不 crash） | P2 |
| Bug 3 lag | TC-GF-008 | 归档 change completed_at 为空时的行为（先审计） | P2 |

> 说明：上表 TC 清单来自 `test-plan.md` 的**方案定义**。`.fstdd.yaml` 仅记录
> 「test-plan.md 8 TC 全覆盖（P0×3 + P1×3 + P2×2）」，**未保留逐 TC 的 PASS/FAIL 执行结果**，
> 故不逐条标注状态。

## 三、修复落点（取自本目录 `test-plan.md` / `design.md`）

- 目标文件：`upstream/fstdd/cli/commands/guard.py` — 主修改；`.fstdd/version.yaml` — 只读。
- Bug 1：Guard-fix-loop 例外（最小改动）。
- Bug 2：Guard status 版本号从 `version.yaml` 动态读取，fallback `unknown`。
- Bug 3：Phase Lag 假阳性，先审计再修（非阻塞）。