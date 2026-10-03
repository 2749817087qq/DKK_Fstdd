# Guard 钩子 stdin 解析健壮性 —— 修掉尾逗号导致的 1 元组崩溃

<!-- source_hash: 7190901a9dcaaade -->
<!-- generated_at: 2026-10-03T14:49:01+00:00 -->
<!-- canonical: canonical/proposals/2026-09-21-guard-hook-input-robustness.yaml -->

## Why

upstream/fstdd/cli/commands/guard.py 的 _read_hook_input() 在「stdin JSON
不可用」的 fallback 分支写成 return x,（尾逗号），返回的是 **1 元组**；
调用方 cmd_guard_check（guard.py:681）以
`hook_path, hook_content = _read_hook_input()` 解包 →
ValueError: not enough values to unpack (expected 2, got 1) →
钩子以 exit 1 + Traceback 崩掉。该钩子为非阻塞（fail-open）挂载点，
用户无感，但门禁在该次调用中**等于没生效** —— 属安全相关的静默失效。


## What Changes

- 两处 fallback return 补齐第二元素（""），保证任何路径都返回 2 元组； 非法输入 ⇒ (None, None)（显式 fail-open）；可恢复路径 ⇒ (path, "")
- 修复处注释留痕（历史缺陷 + change 名），防后人「清理」改回
- 新增 upstream/tests/test_guard_hook_input.py（GHI-001..004，含参数化 6 种输入）， GHI-001 的 len(out)==2 为该缺陷的守门断言
- 不改 fail-open 非阻塞语义，不改门禁判据

### New Capabilities

- **guard-hook-input-robustness**：guard 钩子 stdin 解析在任何输入下返回可解包的 2 元组，不再 ValueError 崩溃

### Modified Capabilities

- **cli-guard**：cmd_guard_check 的钩子输入读取不再因尾逗号崩溃（保持 fail-open 非阻塞语义不变）

## Success Criteria

- [ ] GIVEN 6 种 stdin 形态（空/非JSON/截断JSON/未转义Windows路径/坏JSON含file_path/合法）， WHEN _read_hook_input 被调用 THEN 一律返回长度 2 的元组，不抛异常
- [ ] GIVEN 完全非法的输入 WHEN 解析 THEN 显式返回 (None, None)（fail-open），不抛
- [ ] GIVEN JSON 坏但含 file_path WHEN fallback 恢复 THEN 返回 (path, "")，content 为空串而非缺项
- [ ] GIVEN --hook-stdin 传入坏 JSON WHEN 端到端调用 cmd_guard_check THEN 不抛 ValueError，返回 int
- [ ] 既有 tests/test_guard_silent_except.py 与 tests/test_except_audit.py 不回归
