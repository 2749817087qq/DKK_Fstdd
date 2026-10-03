# CLI canonical 模板加金融领域字段: proposal.yaml / spec.yaml / design.md / test-plan.md

<!-- source_hash: 4b0448c04635bd8a -->
<!-- generated_at: 2026-10-03T02:06:20+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-cli-template-finance-fields.yaml -->

## Why

FSTDD CLI 的 canonical 模板 (proposal.yaml / spec.yaml / test-plan.md)
是通用模板，没有金融领域专属字段。金融项目起草 proposal/spec 时，
critical.risk_assessment.financial=true 是唯一金融标记 —
7 红线覆盖、金融领域标签、4 主线自查、10 维测试等金融专属信息
没有结构化字段承载，只能散落在 constraints/risk_areas 的自由文本里。


## What Changes

- canonical proposal.yaml 模板追加 finance section (domain + redlines + threads)
- canonical spec.yaml 模板追加 finance section (test_dimensions + failure_modes)
- test-plan.md 模板追加金融 10 维测试覆盖章节

### New Capabilities

- **canonical-finance-fields**：proposal/spec/test-plan 模板包含金融领域专属结构化字段

## Success Criteria

- [ ] proposal.yaml 模板追加 finance section (domain/redlines/threads) 带 optional 注释
- [ ] spec.yaml 模板追加 finance section (test_dimensions/failure_modes)
- [ ] test-plan.md 模板追加金融 10 维测试覆盖章节
- [ ] 追加字段与 fstdd-fin SKILL.md 术语一致
