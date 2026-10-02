# Guard 无活跃 change 时因作用域变量未绑定而崩，导致「拦截」退化为放行

<!-- source_hash: 0da23c3099318cbb -->
<!-- generated_at: 2026-10-02T07:45:04+00:00 -->
<!-- canonical: canonical/proposals/2026-09-26-guard-scope-unbound.yaml -->

## Why

`cmd_guard_check` 中 `scope_patterns` / `scope_in` 只在
`if active_dir:` 且 `.fstdd.yaml` 存在的**嵌套**分支内赋值，而「无活跃流程 → 拦截」
分支（guard.py:949 `if scope_in and scope_patterns:`）在**块外**引用它们。
因此「无活跃 change」这条最核心的路径会抛 `UnboundLocalError`，钩子以 exit 1 结束。
按本函数自身约定（0=放行 / 2=拦截），exit 1 属**非阻塞错误** ⇒ 平台放行编辑，
**Guard 在该路径上形同虚设**。


## What Changes

- `cmd_guard_check` 在 `_find_active_change` 之后、`if active_dir:` 之前，
为 `scope_patterns`（`[]`）与 `scope_in`（`False`）预置**函数级 fail-safe 默认值**。

- 新增回归用例 TC-GHI-005：显式使用**项目内相对路径**，断言无活跃流程时返回 2（拦截），
与平台无关。


### New Capabilities

- **guard-scope-default-binding**：Guard 作用域变量在任何分支下均已绑定；无活跃流程时的拦截判定不再退化为异常

### Modified Capabilities

- **guard-hook-input-robustness**：钩子健壮性覆盖到「无活跃 change + 项目内路径」这条此前未覆盖的分支

## Success Criteria

- [ ] 无活跃 change 时 `guard check --hook-stdin` 返回 2 且无 traceback
- [ ] TC-GHI-005 在 Windows 与 Linux 上均通过（平台无关）
- [ ] 服务器全量测试由 1 failed 转为 0 failed
