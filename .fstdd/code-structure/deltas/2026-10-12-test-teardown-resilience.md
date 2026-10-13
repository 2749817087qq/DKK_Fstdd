# Code Structure Delta — 2026-10-12-test-teardown-resilience
> 生成时间: 2026-10-12T16:28:20+00:00 | Git commit: 34f11b5
> 置信度: 0.70 (AI-generated — 以源代码为准)

> ⚠️ **人工补全**：CLI 的自动段（见文末「CLI 原始输出」）只列出 change 目录内的
> `caveman_summary.txt` 一行，与实际改动严重不符（框架工具长期缺陷，上一 change 同形，
> 已登记为 ADJ-007）。以下清单以 `git status --porcelain` + `git diff --stat` 为准。

## 变更文件（本 change 实际改动）

| 文件 | 类型 | 变化 |
|---|---|---|
| `tests/conftest.py` | 修改 | +213 / −4（净 +209 行；163 → 372 行） |
| `tests/test_verify_notices_default_safe.py` | 修改 | +18 / −3（2 处 `mkdir(exist_ok=True)` + 1 个新用例） |
| `tests/test_teardown_resilience_capture.py` | 新增 | 10 个测试函数 |
| `tests/test_teardown_resilience_visibility.py` | 新增 | 7 个测试函数 |
| `tests/test_teardown_resilience_real_exception.py` | 新增 | 3 个测试函数 |
| `tests/test_teardown_resilience_tmp_neutral.py` | 新增 | 5 个测试函数 |

**合计**：新增 26 个测试函数（4 个新文件 25 + `test_verify_notices_default_safe.py` 1）；
全量 `tests/` 由基线 **204 → 230 passed / 6 skipped**。

**范围边界**：仅 `tests/`（+ change 目录）。**未触碰 `upstream/`**（TC-TTR-009 核对通过）。

## 新增公共符号（`tests/conftest.py`）

| 符号 | 类型 | 用途 |
|---|---|---|
| `DELETE_GUARD_PREFIX` | 常量 | 告警/汇总行固定前缀 `[teardown-resilience]` |
| `DELETE_GUARD_STATS` | 模块级 dict | 会话级捕获计数（`captured` / `targets`） |
| `_DELETE_GUARD_SURFACES` | 常量 | 需包装的删除入口清单（6 个） |
| `_DELETE_GUARD_ORIGINALS` | 模块级 dict | 原实现留档（供回退 / monkeypatch 驱动） |
| `_ORIGINAL_TEMP_ROOT` | 常量 | 导入期抓取的系统临时根（bypass 不变式的基准） |
| `_guarded_delete(inner, target, *a, **kw)` | 函数 | 韧性层核心：只放行 `SystemExit` → 告警 + 计数 |
| `_install_delete_guard()` | 函数 | 幂等安装包装（`pytest_configure` 调用） |
| `_delete_guard_summary()` | 函数 | 会话级汇总行 |
| `_pick_neutral_root()` | 函数 | 选仓库外的中立临时根 |
| `_neutralize_temp_env()` | 函数 | 归一 `TMP`/`TEMP`/`TMPDIR`（`pytest_configure` 调用） |
| `pytest_sessionfinish(session, exitstatus)` | hook | 捕获可见化（**不改 exitstatus**，见 design D3） |
| `_isolate_delete_guard_selftest(request)` | fixture（autouse） | 自测用例刻意触发的捕获用后还原 ⇒ 会话汇总不误报（ADJ-011） |

## 依赖 / 结构影响

- **无新增依赖**（仅 stdlib：`functools` / `os` / `pathlib` / `shutil` / `tempfile` / `warnings`）。
- **无新增抽象层**；未改动既有函数签名。
- 依赖图：`dependency-graph` ⇒ `nodes=0 / edges=0 / cycles=无`（本 change 只改 `tests/`，不进代码结构图）。

## CLI 原始输出（未加工）

```
- `caveman_summary.txt`
```
