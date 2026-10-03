# test-report：2026-10-02-failure-mode-coverage-audit

**change**：`2026-10-02-failure-mode-coverage-audit`
**日期**：2026-10-02（收口补录 2026-10-03）
**结论**：🟡 归档时仅记录笼统 Gate 3 证据，未留逐 TC 执行明细

> 归档时 DELIVER 未闭环。`.fstdd.yaml` 的 build 阶段**未记录 `confirmed_evidence` 文本**，
> 仅有切片级统计；本目录 `test-plan.md` 仍为未填充模板。以下内容据既有文件如实回填，未补造。

---

## 一、归档证据（逐字引用）

`.fstdd.yaml` → `phases.build` 原文（本阶段无 `confirmed_evidence` 字段）：

> build:
>     completed_at: '2026-10-02T16:40:00+08:00'
>     slices:
>     - id: slice-1
>       new_tests: 0
>       tc_coverage: 3
>       verified_at: '2026-10-02T16:40:00+08:00'
>     status: completed

`.fstdd.yaml` → `phases.spec.confirmed_evidence` 原文：

> 开发总工 self-confirm Gate 2。审计 14 类失败模式：6 类有实装、5 类仅 skill 引导、3 类仅文字引用。修法：先补 skill build.md 的 C 档 6 类引导段落，再可选加 Guard _check_failure_patterns() 轻量 hook 检测。不搞 CLI detect 子命令（职责分离）。

## 二、测试方案（取自 `design.md`「2 测试计划（概要）」，非执行结果）

| TC | 内容 | 优先级 |
|---|---|---|
| TC-FMC-001 | coverage-report.md 每类有证据文件行号 | P0 |
| TC-FMC-002 | build.md 新增 6 类 skill 引导段落 | P0 |
| TC-FMC-003 | `fstdd guard` 保持原有功能零回归 | P0 |
| TC-FMC-004 | 可选 hook 检测：发现幻觉调用告警不阻断 | P1 |

> 说明：`.fstdd.yaml` 切片记录 `tc_coverage: 3`，而 `design.md` 概要列出 TC-FMC-001~004 共 4 条；
> 两者均为归档时既有记录，本报告如实并列，不作调和。**未保留逐 TC 执行明细**。