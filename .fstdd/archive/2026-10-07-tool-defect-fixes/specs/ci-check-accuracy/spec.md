# Spec: ci-check-accuracy

> Change: 2026-10-07-tool-defect-fixes | Auto-generated Human View

## Requirements

### Requirement: `fstdd ci check-failures` 的 (d) TC-ID 唯一性检查 SHALL 按 **TC-ID 的定义点**判定，
SHALL NOT 把正当的重复**引用**判为违规。同一 TC-ID 出现在 ≥2 个定义点时才 SHALL 判 FAIL。
判定 SHALL 基于结构化位置（表格 ID 单元格 / 加粗 ID 行），而非全文文本出现次数。


#### Scenario: SC-011

- **GIVEN** `test-plan.md` 在「案例标题 / 优先顺序 / 回归矩阵 / 证据表」多处引用同一 TC-ID（项目既有约定），且该 ID 只有 1 个定义点
- **WHEN** 执行 `fstdd ci check-failures <change>` 并读取 (d) 项结果
- **THEN** SHALL 判 PASS，SHALL NOT 报「重复 TC-ID」
- **AND** 对 `.fstdd/` 下 41 份既有 test-plan 执行时，报 (d) 重复的份数 SHALL 为 0

#### Scenario: SC-012

- **GIVEN** 构造一份 test-plan 样本，其中同一 TC-ID 出现在 **2 个定义点**（两个 ID 单元格）
- **WHEN** 对该样本执行 (d) 检查
- **THEN** SHALL 判 FAIL 并列出该重复 ID
- **AND** 另构造一份样本：同一 ID 有 1 个定义点 + 多处引用 ⇒ SHALL 判 PASS（正 / 反双向断言）
