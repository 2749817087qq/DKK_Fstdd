# 追加 8 类金融特有失败模式到 BUILD C4 检查清单

<!-- source_hash: 0e98411901fe3d3f -->
<!-- generated_at: 2026-10-03T02:02:50+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-finance-failure-modes.yaml -->

## Why

FSTDD V3.0.10 BUILD Phase C4 失败模式检查清单有 14 类通用模式，但零金融特有条目。
上一个 change (2026-10-03-finance-integration) 在 understand/build skill 里加了
金融钩子（7 红线 + 10 维测试），但 BUILD 阶段全量失败模式检查仍只覆盖通用问题
（幻觉/范围蔓延/凭证泄露等），不覆盖金融特有的"重复扣款""账实不符""精度丢失"
等 8 类场景。金融项目到 BUILD 质量验证环节 = 金融失败模式裸奔。


## What Changes

- .fstdd/skills/build.md C4 section 14 类清单后面追加 8 类金融特有模式（同一 Markdown table）
- 每类金融模式标注覆盖方式（skill 引导 / 金融红线联动）+ BUILD 检查动作（具体可执行步骤）

### New Capabilities

- **finance-failure-modes-c4**：BUILD C4 失败模式检查清单新增 8 类金融特有模式，与 14 类通用模式同等强制勾选

### Modified Capabilities

- **build-quality-verification**：BUILD Phase C4 检查清单从 14 类扩展到 22 类（14 通用 + 8 金融）

## Success Criteria

- [ ] .fstdd/skills/build.md C4 section 包含 22 行 table（14 通用 + 8 金融）
- [ ] 8 类金融模式每类有：编号 15-22、中文失败模式名、覆盖方式、具体 BUILD 检查动作
- [ ] 原有 14 类条目一字不改（sha256 对比前 14 行一致）
- [ ] Markdown table 渲染正确（4 列对齐）
- [ ] fstdd validate 通过
