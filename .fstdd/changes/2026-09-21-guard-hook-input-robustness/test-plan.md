# 测试计划：Guard 钩子 stdin 解析健壮性

**change**：2026-09-21-guard-hook-input-robustness

| ID | 场景 | 期望 | 用例 |
|---|---|---|---|
| GHI-001 | 6 种输入（空/非JSON/截断JSON/未转义Windows路径/坏JSON含file_path/完整合法） | **一律返回可解包的 2 元组**，不抛异常 | `test_ghi_001_always_two_tuple`（参数化 6 例） |
| GHI-002 | 完全非法的输入 | 显式 fail-open **`(None, None)`**，不抛 | `test_ghi_002_illegal_input_no_exception` |
| GHI-003 | JSON 坏但含 `file_path` | fallback 恢复路径；`content` 为**空串**（不是缺项） | `test_ghi_003_fallback_recovers_file_path` |
| GHI-004 | 端到端：`--hook-stdin` + 坏 JSON | `cmd_guard_check` **不抛 ValueError**，返回 int | `test_ghi_004_end_to_end_no_valueerror` |
| REG-001 | 既有 guard 哨兵测试 | 不回归 | `tests/test_guard_silent_except.py` |
| REG-002 | 审计活表零漂移 | 不回归 | `tests/test_except_audit.py` |

**判据说明**：GHI-001 的 `len(out) == 2` 即为**该缺陷的守门断言**
（历史写法 `return x,` 必在此失败）。
