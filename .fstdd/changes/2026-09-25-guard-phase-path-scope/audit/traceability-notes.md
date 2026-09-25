# 审计补记 — Gate 1 追认与 traceability 缺口

> 本文件由 K 在 2026-09-25 手工补记。**原因**：`gate amend-audit` 写入
> `.fstdd.yaml` 的追认记录，在随后 `phase advance` 重写该文件时**被整体丢弃**
> （顶层 `gate1`/`gate2` 键与 amend 条目全部消失），追认无法持久化。

## Gate 1 追认记录（原应存在于 `.fstdd.yaml` amend 条目中）

- **命令**：`fstdd gate amend-audit --gate 1 --confirmed-by dialog --evidence "..."`
- **执行时刻**：2026-09-25T05:00:24+00:00（CLI 报 "Amend audit appended"）
- **追认原文**：D哥 2026-09-25 13:00 确认：Gate 1 已确认时 proposal source_hash=dc91e05e945a59e2；其后为补齐本 change 自身的作用域声明（scope.paths）而重生成 proposal（新 source_hash=2752f7f14a65ec53），D哥 对 scope 块追加内容追认通过，Gate 1 继续有效。
- **结论**：Gate 1 有效，覆盖 scope 块追加后的 proposal.md。

## Gate 2 确认

- **命令**：`fstdd gate approve --gate 2 --confirmed-by dialog`
- **确认时刻**：2026-09-25T05:03:22+00:00（持久化于 `phases.spec.confirmed_*`）
- **evidence**：D哥 2026-09-25 13:05 对话确认：Gate 2 通过（SPEC 产物 design.md + spec.md + test-plan.md 齐全，canon verify 2/2 通过）

## 已确认的 CLI 缺陷（转后续 change）

| # | 现象 | 证据 |
|---|------|------|
| 1 | `gate amend-audit` 的追认条目不持久：`phase advance` 重写 `.fstdd.yaml` 后顶层 `gate1`/`gate2` 键与 amend 条目全部消失 | 12:59 approve 后 `head .fstdd.yaml` 可见 `gate2:` 块；13:05 advance 后 `grep -rn amend` 零命中 |
| 2 | `traceability` 计数恒为 0：spec 已有 10 个 scenario、test-plan 已有 11 个 TC，但 `.fstdd.yaml` 仍记 `spec_scenarios: 0 / tc_cases: 0 / test_functions: 0` | 2026-09-25T05:04 实测读取 |
| 3 | `gate approve` 成功后 `phase advance` 仍报「需要 Gate 2 确认」一次（读到了已被规范化的文件） | 13:03 单次 advance 失败，重试即通过 |

三项均属**审计链完整性**问题（记录写了但保不住），非阻断，不影响本 change 继续
BUILD，但应与本 change 的 scope 逻辑分开立项。
