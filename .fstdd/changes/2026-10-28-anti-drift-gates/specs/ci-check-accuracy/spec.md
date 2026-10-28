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
