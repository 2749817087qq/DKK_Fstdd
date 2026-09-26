# 设计：Guard 作用域变量未绑定导致拦截退化为放行

## 1 缺陷

`upstream/fstdd/cli/commands/guard.py` 的 `cmd_guard_check()`：

| 位置 | 缩进 | 作用 |
|---|---|---|
| 871–872 | 12 空格 | `scope_patterns = _load_change_scope(active_dir)` / `scope_in = False` |
| 874 | 16 空格 | `scope_in = _is_in_change_scope(...)` |
| **949** | **4 空格** | `if scope_in and scope_patterns:` ← **在 `if active_dir:` 块外** |

⇒ 871–875 只在「有活跃 change **且** 该 change 有 `.fstdd.yaml`」时执行；而 949 在
「无活跃流程 → 拦截」这条分支上必然到达 ⇒ `UnboundLocalError`。

**为什么严重**：`cmd_guard_check` 自身 docstring 声明
`0 — allowed` / `2 — blocked`。崩溃返回 **1**，既不是 0 也不是 2。
按钩子约定只有 exit 2 才是拦截，其余非零属**非阻塞错误** ⇒ 平台继续执行编辑。
即：**「你还没进入 STDD 流程，不许改代码」这条最核心的守卫，实际是放行的。**

## 2 为什么长期没被发现

1. 该路径**在 Windows 上被绕过**：原用例 TC-GHI-004 喂的是 Windows 绝对路径
   `D:\\tools\\FSTDD\\x.py`，Windows 下 `_is_inside_project` 判为「不在本项目内」
   而提前 `return 0`；Linux 下同一字符串只是一个含反斜杠的**文件名**，相对解析后
   落在项目内，才走到拦截分支。
2. 本机（Windows）全量测试约 **100 分钟**，实际上没人跑；服务器全量只要 **2 分钟**，
   一跑就暴露（`825 passed / 1 failed`）。

## 3 修法（最小改动）

在 `_find_active_change` 之后、`if active_dir:` 之前，**函数级**预置：

```python
scope_patterns: list = []
scope_in = False
```

理由：

- **fail-safe**：空作用域 = 不做作用域归因，拦截判定（2）本身不变；
- 不动 871–875 的既有语义（有活跃 change 时仍会被重新赋值）；
- 不引入新分支、不改任何文案 ⇒ 对 SC-002 / SC-003 零行为漂移。

## 4 验证

| 验证 | 结果 |
|---|---|
| 本机 CLI 复现（修复前） | `UnboundLocalError` at guard.py:949，rc=1 |
| 本机 CLI 复现（修复后） | rc=**2**，输出「⛔ Blocked — 未进入可编辑流程」，无 traceback |
| `test_guard_hook_input.py` | **10 passed**（含新增 TC-GHI-005） |
| 服务器全量 | 见 test-report |
