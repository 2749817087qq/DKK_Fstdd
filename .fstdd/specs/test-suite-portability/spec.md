# Spec: test-suite-portability

> Change: 2026-10-06-legacy-debt-cleanup | Auto-generated Human View

## Requirements

### Requirement: 所有以文本模式调用子进程的测试与工具代码 SHALL 在**调用点**显式指定 UTF-8 解码，
使解码结果不依赖运行环境的 locale / 控制台代码页；SHALL NOT 依赖 `PYTHONUTF8` /
`PYTHONIOENCODING` 等环境变量的隐式配合。解码失败 SHALL 以可观测方式呈现
（`errors="replace"` 产生 U+FFFD），SHALL NOT 静默丢弃（`errors="ignore"`）。


#### Scenario: SC-001

- **GIVEN** `upstream/tests/`、`tests/`、`tools/` 下存在以 `text=True`（或 `universal_newlines=True`）调用 `subprocess` 且未指定 `encoding=` 的位置（修复前 36 处 / 16 文件）
- **WHEN** 对上述三个目录的 `*.py` 执行 AST 扫描，统计 text-mode 调用中未指定 `encoding=` 的数量
- **THEN** SHALL 使该数量为 0
- **AND** 扫描范围 SHALL 覆盖 `upstream/tests/**`、`tests/**`、`tools/**` 的全部 `*.py`
- **AND** 修复 SHALL 只新增 `encoding=` / `errors=` 关键字参数，SHALL NOT 改动 `args` 列表、`cwd`、`env`、`timeout` 等既有实参

#### Scenario: SC-002

- **GIVEN** `tests/test_multi_platform.py` 的 `test_install_sh_passes_platform` 与 `test_install_ps1_passes_platform` 修复前在非 UTF-8 环境下各以 `UnicodeDecodeError` 失败
- **WHEN** 在**非 UTF-8 环境**（不设 `PYTHONUTF8`，控制台为 GBK）下执行 `pytest tests/test_multi_platform.py`
- **THEN** SHALL 使上述 2 例不再因 `UnicodeDecodeError` 失败
- **AND** 该文件的结果 SHALL 为 `11 passed, 1 skipped`（原 `2 failed, 9 passed, 1 skipped` 的 2 例转绿）
- **AND** 该文件 SHALL NOT 出现任何 `UnicodeDecodeError`

#### Scenario: SC-003

- **GIVEN** 编码修复已完成，且运行于**权威门禁环境**（控制台 UTF-8 + `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`）
- **WHEN** 执行全量 `pytest upstream/tests tests -q`
- **THEN** SHALL 使结果为 `0 failed`
- **AND** 通过数 SHALL 不低于修复前基线 `906 passed`
- **AND** 跳过数 SHALL 不高于修复前基线 `54 skipped`

#### Scenario: SC-004

- **GIVEN** 修复后的 text-mode `subprocess` 调用已带 `errors=` 参数
- **WHEN** 审查全部新增的 `errors=` 取值
- **THEN** SHALL 使取值一律为 `replace`（或 `surrogateescape`），SHALL NOT 出现 `ignore`
- **AND** 修复 SHALL NOT 引入以 `except Exception: pass` / `except: pass` 吞掉解码或调用异常的兜底
- **AND** `errors="replace"` 产生的 U+FFFD SHALL 视为可观测信号，不视为需要抹除的噪声

#### Scenario: SC-006

- **GIVEN** `upstream/tests/test_install_scripts.py` 以 `encoding="utf-8"` 解码 Windows PowerShell 的 stdout，而 PowerShell 5.1 在 stdout 被重定向时按 `[Console]::OutputEncoding`（中文主机 = GBK / CP936）编码
- **WHEN** 在控制台代码页非 UTF-8 的环境下执行 `pytest upstream/tests/test_install_scripts.py`
- **THEN** SHALL 使该文件全部用例通过（3 passed）
- **AND** 调用 SHALL 显式令 PowerShell 以 UTF-8 写出 stdout（`[Console]::OutputEncoding=UTF8`），SHALL NOT 依赖调用方的控制台代码页
- **AND** 对 `pwsh`（PowerShell 7+，默认 UTF-8）SHALL NOT 施加多余包装
- **AND** 包装 SHALL NOT 改变 `param()` 绑定语义（参数名不得被引号化为字符串字面量）

### Requirement: 编码修复 SHALL NOT 改变任何测试的**收集结果**与**断言语义**：用例集合（数量、ID、文件归属）
SHALL 与修复前完全一致，SHALL NOT 新增、删除、改名或跳过任何既有用例。


#### Scenario: SC-005

- **GIVEN** 编码修复前的用例集合已由 `pytest --collect-only -q` 记录
- **WHEN** 在修复后再次执行 `pytest --collect-only -q`，并与修复前的用例清单逐条比对
- **THEN** SHALL 使用例清单完全一致（无新增 / 无删除 / 无改名 / 无新增 skip）
- **AND** `tests/test_multi_platform.py` 的用例数 SHALL 保持 12（11 passed + 1 skipped）
- **AND** 任何用例的 `skip` 理由 SHALL NOT 因本次修复而新增
