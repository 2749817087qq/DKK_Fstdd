# Spec: canonical-hash-integrity

> Change: 2026-10-06-legacy-debt-cleanup | Auto-generated Human View

## Requirements

### Requirement: 每条 canonical proposal SHALL 满足 `content_hash(<change>.yaml) == <proposal.md> 的
source_hash`。以 YAML 为唯一事实源；MD 的 `source_hash` SHALL 是「渲染自哪个 YAML 版本」
的指纹，SHALL NOT 与 YAML 实际内容脱节。


#### Scenario: SC-001

- **GIVEN** `.fstdd/archive/2026-09-18-inbox-api-only-write/proposal.md:3` 的 `source_hash` 为 `16fa0e448d063e2a`，而 `canonical/proposals/2026-09-18-inbox-api-only-write.yaml` 的 `content_hash` 为 `29c0012fe4d0b612`
- **WHEN** 执行 `fstdd canon verify 2026-09-18-inbox-api-only-write`
- **THEN** SHALL 输出 `2/2 通过`（DC-HASH 一致 + DC-FIELD 完整）
- **AND** SHALL 使归档 `proposal.md` 的 `source_hash` 等于 YAML 的 `content_hash` = `29c0012fe4d0b612`
- **AND** SHALL NOT 改动归档 `proposal.md` 的正文内容（除 `source_hash` 注释行外）
- **AND** SHALL NOT 改动该 change 的 canonical YAML 正文

#### Scenario: SC-002

- **GIVEN** 本仓 `canonical/proposals/` 下的全部 proposal YAML 与其对应 MD 均存在
- **WHEN** 对每一条 proposal 执行 `fstdd canon verify <change>`
- **THEN** SHALL 使全部 proposal 的 DC-HASH 一致（不再存在任何 1/2 的欠账条目）
- **AND** 本次修复 SHALL 只补齐既有欠账，SHALL NOT 借机改动其它 proposal 的内容
- **AND** 验证范围 SHALL 至少覆盖根 `canonical/proposals/` 下全部条目

### Requirement: 本 change 自身的 canonical 双轨 SHALL 保持一致：`canon verify 2026-10-06-legacy-debt-cleanup`
SHALL 输出 2/2，且其 proposal / spec YAML 与生成的 MD 指纹一致。


#### Scenario: SC-003

- **GIVEN** 本 change 的 canonical proposal 与各 capability spec YAML 已就绪，且 Human View 已由 `canon generate` 渲染
- **WHEN** 执行 `fstdd canon verify 2026-10-06-legacy-debt-cleanup`
- **THEN** SHALL 输出 `2/2 通过`
- **AND** 新增的 4 个 capability spec SHALL 均在 `.canon-index.yaml` 中登记（无未登记文件）
- **AND** 索引中登记的文件 SHALL 全部真实存在（零缺失）
