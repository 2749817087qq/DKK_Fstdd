# 设计：Guard 钩子 stdin 解析健壮性

**change**：2026-09-21-guard-hook-input-robustness ｜ **任务类型**：code

## 1. 问题（实测，非推测）

`upstream/fstdd/cli/commands/guard.py` 的 `_read_hook_input()` 在
"stdin JSON 不可用"的 fallback 分支写成 **`return x,`（尾逗号）**：

```python
                return json.loads('"%s"' % m.group(1)),      # ← 1 元组
            except Exception:
                return m.group(1).replace("\\\\", "/"),    # ← 1 元组
```

⇒ 调用方 `cmd_guard_check`（`guard.py:681`）：

```python
hook_path, hook_content = _read_hook_input()   # ValueError: expected 2, got 1
```

⇒ 钩子以 **exit 1 + Traceback** 崩掉。因该钩子为 **非阻塞**（fail-open），
用户无感，但**门禁在该次调用中等于没生效** —— **安全相关的静默失效**。

**实证**：`~/.workbuddy-ai/logs/2026-09-18|19|20/fstdd-hub__*.log`
（`Hook exited with non-blocking error code 1: Traceback` 约 74 次/日）。

**历史**：该"尾逗号"缺陷此前已被识别（台账纪律 ⑬），但**未修复**，持续触发。

## 2. 设计（最小修复 + 防复发）

| 项 | 做法 |
|---|---|
| **修复** | 两处 return 补齐第二元素（`""`），保证**任何路径都返回 2 元组** |
| **契约明确** | 非法输入 ⇒ `(None, None)`（显式 fail-open）；可恢复路径 ⇒ `(path, "")` |
| **注释留痕** | 在修复处写明历史缺陷与 change 名，防后人"清理"回去 |
| **回归测试** | 新增 `tests/test_guard_hook_input.py`（9 例，含参数化 6 种输入） |
| **不改** | 不改 fail-open 语义（**保持非阻塞**，只保证不崩）；不改门禁判据 |

## 3. 为什么保持 fail-open 而不改 fail-closed

钩子是非阻塞挂载点：**崩掉 = 不拦**。若改为 fail-closed（崩了即拒），
会在 stdin 偶发不可用时**阻断正常写操作**（可用性风险）。
**本次只修"崩"，不改"拦不拦"** —— 后者属独立决策（见"未覆盖项"）。

## 4. 未覆盖项（明确不做，防范围蔓延）

1. **fail-open vs fail-closed 的策略选择** —— 需 D哥 决策，本 change 不动；
2. `guard.py` 其他 `except` 的吞异常治理 —— 属 `detection-silence-fixes` 范畴，不重复；
3. stdin 大 payload 被截断的**上游成因**（平台侧）—— 非本仓可控，仅做 fallback 恢复。

## 5. 风险与回滚

| 项 | 说明 |
|---|---|
| 风险 | 极低。仅补齐返回元组元素；不改判定逻辑、不改退出码语义（崩→不崩） |
| 回滚 | 单提交可 `git revert` |
