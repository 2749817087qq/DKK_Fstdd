# 测试方案：Guard 作用域变量未绑定

## 追溯表

| SC | TC | 测试函数 | 文件 |
|---|---|---|---|
| SC-001 | TC-GHI-005 | `test_ghi_005_block_path_without_active_change_returns_2` | `upstream/tests/test_guard_hook_input.py` |
| SC-002 | TC-GHI-001~003（既有） | `test_ghi_00*` | 同上 |
| SC-003 | TC-GHI-004（既有） | `test_ghi_004_end_to_end_no_valueerror` | 同上 |

## TC-GHI-005

**目标**：无活跃 change 时，拦截分支必须返回 2，不得因作用域变量未绑定而抛异常。

**步骤**：

1. `monkeypatch.chdir(tmp_path)`（空临时目录，无 `.fstdd/`）；
2. `_with_stdin` 注入 `{"file_path": "x.py"}`（**项目内相对路径** —— 与平台无关）；
3. 调用 `guard.cmd_guard_check(_Args())`；
4. 断言 `rc == 2`。

**为什么必须用相对路径**：原 TC-GHI-004 用 Windows 绝对路径，在 Windows 上会被
`_is_inside_project` 提前放行，**永远走不到拦截分支**，因此漏检了本缺陷。

## 回归范围

- 定向：`pytest upstream/tests/test_guard_hook_input.py -q`
- 全量：服务器 `fstdd-hub`（本机全量约 100 分钟，服务器约 2 分钟）
