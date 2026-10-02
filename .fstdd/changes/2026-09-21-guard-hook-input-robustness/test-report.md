# 测试报告：Guard 钩子 stdin 解析健壮性

**change**：2026-09-21-guard-hook-input-robustness ｜ **日期**：2026-09-21

## 一、执行结果

| 用例 | 结果 |
|---|---|
| `tests/test_guard_hook_input.py`（GHI-001..004） | ✅ **9 passed** |
| `tests/test_guard_silent_except.py`（REG-001） | ✅ passed |
| `tests/test_except_audit.py`（REG-002） | ✅ passed |
| **合计（本次范围）** | ✅ **20 passed / 0 failed** |

## 二、缺陷复现（修前）与验证（修后）

**修前（实证，来自真实日志）**：
```
File ".../guard.py", line 681, in cmd_guard_check
    hook_path, hook_content = _read_hook_input()
ValueError: not enough values to unpack (expected 2, got 1)
Hook exited with non-blocking error code 1: Traceback
```
**等价最小复现**（本次现场验证）：
```
旧写法 return path,  →  ('D:/x.py',)   长度 1
调用方解包          →  ValueError: not enough values to unpack (expected 2, got 1)
```

**修后**：6 种输入全部返回 2 元组；非法输入显式 `(None, None)`；端到端不抛 ValueError。

## 三、未覆盖（见 design.md §4）

- fail-open vs fail-closed 策略（需 D哥 决策）；
- stdin 截断的上游成因（平台侧）；
- guard.py 其余吞异常治理（属另一 change）。

## 四、判据结论

**GHI-001 的 `len(out)==2` 是本缺陷的守门断言** —— 若有人把尾逗号"改回去"，
该测试立即变红。**这正是本次修复的防复发机制。**
