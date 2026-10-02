# Spec: guard-scope-default-binding

> Change: 2026-09-26-guard-scope-unbound | Auto-generated Human View

## Requirements

### Requirement: Guard 的作用域归因变量必须在函数级完成绑定，任何分支都不得以异常代替拦截判定

#### Scenario: SC-001

- **GIVEN** 当前目录**没有**活跃 change（无 .fstdd/changes 或该 change 无 .fstdd.yaml）
- **WHEN** 以 --hook-stdin 传入一个**位于本项目内**的目标路径，且该编辑不处于可编辑相位
- **THEN** SHALL 返回 2（拦截），且 SHALL NOT 抛出 UnboundLocalError 或任何未捕获异常

#### Scenario: SC-002

- **GIVEN** 存在活跃 change 且其 canonical/proposals 声明了 scope.paths
- **WHEN** 目标路径落在 scope.paths 之外
- **THEN** SHALL 维持既有行为：warn-only 放行（返回 0），拦截原因文案不变

#### Scenario: SC-003

- **GIVEN** 存在活跃 change 且其 canonical/proposals 声明了 scope.paths
- **WHEN** 目标路径落在 scope.paths 之内且相位不允许编辑
- **THEN** SHALL 返回 2，且拦截原因 SHALL 附带「该文件在 change 作用域 scope.paths 内」说明
