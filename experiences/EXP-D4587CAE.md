---
experience_id: EXP-D4587CAE
category: process_deviation
severity: medium
occurrences: 1
source_change: 2026-09-15-crlf-eol-governance
title: 5.3 CLI 生成物持续引入 CRLF（根因，已提供自愈手段）
exported_at: 2026-09-15
sanitized: true
---
### 5.3 CLI 生成物持续引入 CRLF（根因，已提供自愈手段）

**现象**：`stdd archive` 之后重跑验证，TC-EOL-003 由 PASS 退化为 FAIL，
出现 4 个新的混合态文件：

```
.stdd/archive/2026-09-15-crlf-eol-governance/.stdd.yaml
.stdd/archive/2026-09-15-crlf-eol-governance/proposal.md
.stdd/archive/2026-09-15-crlf-eol-governance/specs/eol-governance/spec.md
.stdd/specs/eol-governance/spec.md
```

**根因**：STDD CLI（`init` / `new` / `canon generate` / `archive`）生成的文件
**使用 CRLF 行尾**。因此 EOL 治理不是「加一次规则就一劳永逸」，而是每次执行 CLI
之后都可能重新引入混合态。这是原提案未预见到的持续性问题。

**处理**：为 `tools/verify_eol.py` 增加 `--fix` 模式，扫描混合态文件并将其工作区
行尾归一为 LF。实测幂等：第二次执行「归一 0 个」且仍为 7/7。

**结论**：`.gitattributes` 解决的是**入库与检出**的行尾一致性；CLI 生成物的行尾
属于工具侧行为，需靠 `--fix` 周期性自愈，或在未来向上游反馈。
