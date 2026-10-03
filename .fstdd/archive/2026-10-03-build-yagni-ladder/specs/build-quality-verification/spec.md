# Spec: build-quality-verification

> Change: 2026-10-03-build-yagni-ladder | Auto-generated Human View

## Requirements

### Requirement: BUILD 阶段 C4 失败模式检查清单 SHALL 由 22 类扩展为 23 类，本地与 upstream 两份 build.md 逐行一致

#### Scenario: SC-BQV-001

- **GIVEN** `.fstdd/skills/build.md` 的 C4 section 含一张 markdown 表
- **WHEN** 统计 '## C4' 到 '## C5' 之间排除 header/separator 的 data row 数
- **THEN** SHALL 等于 23（较既有 22 类 +1）

#### Scenario: SC-BQV-002

- **GIVEN** `upstream/.fstdd/skills/build.md` 与 `.fstdd/skills/build.md` 两份文件
- **WHEN** 分别统计 C4 data row 数并逐行比对
- **THEN** SHALL 均为 23 且两份内容完全一致

### Requirement: C4 第 23 行 SHALL 表示「过度工程（Over-Engineering）」，覆盖方式为 YAGNI-7 梯子

#### Scenario: SC-BQV-003

- **GIVEN** build.md 的 C4 表第 23 行
- **WHEN** 读取该行的失败模式列与覆盖方式列
- **THEN** SHALL 含关键词 'YAGNI'，且覆盖方式列标记为 'YAGNI-7 梯子'

#### Scenario: SC-BQV-004

- **GIVEN** build.md 的 C4 小节标题行
- **WHEN** 读取标题文本
- **THEN** SHALL 显示「23 类失败模式检查清单」（与 23 行数据对齐）

### Requirement: 既有 22 类失败模式 SHALL 保持编号与语义无回归

#### Scenario: SC-BQV-005

- **GIVEN** C4 表第 1 至第 22 行（14 通用 + 8 金融）
- **WHEN** 对比变更前后的编号与文本
- **THEN** SHALL 逐字不变，无重编号、无删改

### Requirement: 静态内容断言 SHALL 与 C4 行数保持同步，保证 release validation L1 全绿

#### Scenario: SC-BQV-006

- **GIVEN** `tests/test_finance_content.py` 的 L1-05 / L1-06 断言
- **WHEN** 运行 `pytest tests/test_finance_content.py --platform workbuddy`
- **THEN** SHALL 全部通过（断言已由 22 更新为 23），无 FAIL/ERROR
