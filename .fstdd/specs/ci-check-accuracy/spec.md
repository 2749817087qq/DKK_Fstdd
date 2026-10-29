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


<!-- 合并自 2026-10-28-anti-drift-gates -->
# Spec: ci-check-accuracy

> Change: 2026-10-28-anti-drift-gates | Auto-generated Human View

## Requirements

### Requirement: (b) 范围蔓延检查的判据锚点须是「change 自己声明的 scope.paths」，
不得依赖「capability 名恰好出现在文件路径里」这种巧合。
原实现的 `is_cap = any(f"specs/{c}/" in fp or f"commands/{c}" in fp for c in caps)`
对本仓恒不命中（代码在 upstream/fstdd/cli/commands/<module>.py），导致该检查
从未 FAIL 过一次 —— 属 EXP-2026-0026「判据锚点错配 ⇒ 假阴性」的同类。


#### Scenario: SC-CIA-001

- **GIVEN** capability 名为 'ci-check-accuracy'，而实际被改的文件是 upstream/fstdd/cli/commands/ci.py
- **WHEN** 执行 (b) 检查
- **THEN** 判据 SHALL 依据 scope.paths 判定，SHALL NOT 要求 capability 名出现在路径中
- **AND** 结果 SHALL 不受 capability 命名风格影响（下划线/连字符/缩写均可）

#### Scenario: SC-CIA-002

- **GIVEN** 一个 change 跨 3 个 commit，范围蔓延发生在第 1 个 commit
- **WHEN** 执行 (b) 检查
- **THEN** diff 范围 SHALL 为 baseline.base_git_sha..HEAD（覆盖全部 3 个 commit）
- **AND** 第 1 个 commit 里的越界文件 SHALL 被检出

#### Scenario: SC-CIA-003

- **GIVEN** change 刚创建，仓库只有 1 个 commit（HEAD~1 不存在）
- **WHEN** 执行 (b) 检查
- **THEN** 检查 SHALL NOT 因 git 报错而静默 SKIP
- **AND** baseline 缺失时 SHALL 返回 WARN 说明「无法确定 change 起点」
- **AND** SHALL NOT 抛异常导致整个 check-failures 崩溃

#### Scenario: SC-CIA-004

- **GIVEN** change 的 .fstdd.yaml 含 baseline.base_git_sha == <某个 sha>
- **WHEN** 执行 (b) 检查
- **THEN** diff SHALL 从该 sha 起算，而非从 HEAD~1 或 merge-base
