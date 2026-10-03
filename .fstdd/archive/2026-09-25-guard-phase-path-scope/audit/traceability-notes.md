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

## 追加：2026-09-26 在 new-isolate-flag SPEC 阶段新发现 2 项

> 这两项与上面 3 项同属「CLI 表面可用、实则不可达」家族，一并登记以便合并立项。

| # | 现象 | 证据 |
|---|------|------|
| 4 | `canon generate <change> --type {spec,design}` 的 `--type` 是**死选项**：`cmd_canon_generate` 无条件调 `_generate_one(..., args.type)`，而 `_generate_one` 里 `gen_type` 形参**从未被使用**（全文件仅出现在签名行 `canon.py:285`），函数体恒定读 `canonical/proposals/<change>.yaml` 并写 `proposal.md`。⇒ `--type spec` 会**静默生成 proposal.md**，spec 视图不产出。`_generate_spec` 仅能经 `--all`（项目级 canonical）或 `gate.py:158`（Gate 2）到达，**单 change 路径不可达** | `2026-09-26T00:53+08:00` 实测：`canon generate 2026-09-25-new-isolate-flag --type spec --dry-run` → 输出 `Generated .../proposal.md`；`grep -n gen_type canon.py` 仅 1 行（签名） |
| 5 | 上一条的**连带伤害**：`gate.py:173` 在 spec 生成失败时提示用户「可手动运行 `stdd canon generate` 排查」——而该命令（单 change 形态）恰恰**不具备生成 spec 的能力**（见 #4）。⇒ 错误提示把用户引向一条无效的补救路径 | `gate.py:167-178` 文案 vs `canon.py:237-243` 实际行为 |

**#5 的处置提示**：修 #4 即可同时使 #5 的提示成立，无需单独改文案。

### 附：`stdd validate` 的双视图计数张力（非缺陷，记录为已知取舍）

`validate.py:90` 用 `#### Scenario:` 统计 scenario 数，且遍历 `specs/**/*.md` **全部** md 文件。
本仓约定同时存在两份视图：`specs/<capability>/spec.md`（生成）与 `specs/code/spec.md`（手写精简）。
若精简视图也使用 `#### Scenario:` 头，scenario 数会**翻倍**（20→40），反过来触发
`TC 案例数 < Scenario 数` 的新错误。⇒ 精简视图**必须避免**该标题，代价是恒定产生
一条 `spec.md: 未找到 Scenario` 警告。

已实测确认这不是本 change 的个别问题：**W5（`2026-09-25-guard-phase-path-scope`）在
Gate 2 已确认、已提交的状态下，`stdd validate` 输出完全相同的这一条警告**（`0 error / 1 warning`，exit 0）。
⇒ 属既有约定的固定代价，不阻断验收。

