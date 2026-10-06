"""TC-TSP-001 / TC-TSP-004 —— 子进程文本调用的编码策略审计。

背景（change 2026-10-06-legacy-debt-cleanup）：
    测试套件原以 `subprocess(..., text=True)` 而不指定 `encoding=`，解码因此走
    `locale.getpreferredencoding()`。在中文 Windows 上这会**双向**出错：
      · 子进程输出 UTF-8 而父进程按 GBK 解 -> UnicodeDecodeError: 'gbk' ...
      · 子进程输出 GBK（PowerShell）而 PYTHONUTF8=1 令父按 UTF-8 解 -> 'utf-8' ...

    本模块把「解码契约写在调用点」固化为**机器可验证**的断言，替代「人记得设环境变量」。

设计取舍：
    · 只扫 `upstream/tests`、`tests`、`tools` 三个目录（本仓测试与工具面）。
    · 按 `utf-8-sig` 读源码以容忍 BOM（`tools/heartbeat.py` 实测带 U+FEFF）。
    · 断言**只增不减**：不检查调用语义，只检查 `encoding=` 是否声明、`errors=` 是否静默。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("upstream/tests", "tests", "tools")
SUBPROCESS_TEXT_APIS = frozenset({"run", "Popen", "check_output", "check_call", "call"})
SILENT_ERROR_POLICIES = frozenset({"ignore"})
ALLOWED_ERROR_POLICIES = frozenset({"replace", "surrogateescape"})

# 属性式 `.open()` 只在接收者「像路径」时才纳入文本 I/O 范围。
#
# ⚠️ 反面教材（本 change BUILD 期实测）：把**任意** `.open()` 都当成文件 I/O 会误伤
#    `urllib.request.OpenerDirector.open()` —— 它不接受 `encoding=`，
#    补上去就是运行时 `TypeError`（实测 tools/fstdd003_daily_share.py:110）。
#    同理 `tarfile.open()` 有自己的 `encoding=` 语义，不属本审计面。
PATHISH_RECEIVER_TOKENS = (
    "path", "file", "dir", "root", "log", "readme", "changelog", "yaml", "json",
)


def _collect_subprocess_bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    """返回 (模块别名集合, 直接导入的 API 名集合)。

    覆盖四种写法（首版只认第 1 种，漏检了第 2 种 —— 见 `test_scanner_binding_selfcheck`）：
        `import subprocess`                 -> 模块名 "subprocess"
        `import subprocess as _sp`          -> 模块别名 "_sp"
        `from subprocess import run`        -> 直接名 "run"
        `from subprocess import run as R`   -> 直接名 "R"
    """
    modules: set[str] = set()
    direct: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    modules.add(alias.asname or "subprocess")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess" and node.level == 0:
                for alias in node.names:
                    direct.add(alias.asname or alias.name)
    return modules, direct


def _iter_subprocess_calls_in_tree(tree: ast.AST):
    """产出 (lineno, kwargs) —— 该 AST 中所有 text-mode 的 subprocess 调用。"""
    modules, direct = _collect_subprocess_bindings(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in SUBPROCESS_TEXT_APIS:
            if not (isinstance(func.value, ast.Name) and func.value.id in modules):
                continue
        elif isinstance(func, ast.Name) and func.id in direct:
            pass
        else:
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        if "text" not in kwargs and "universal_newlines" not in kwargs:
            continue
        yield node.lineno, kwargs


def _iter_text_mode_subprocess_calls():
    """产出 (path, lineno, kwargs) —— 三目录中所有 text-mode 的 subprocess 调用。"""
    for base in SCAN_DIRS:
        root = REPO / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                source = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:  # 解析失败必须出声，不得静默跳过
                pytest.fail(f"无法解析 {path.relative_to(REPO)}: {exc}")
            for lineno, kwargs in _iter_subprocess_calls_in_tree(tree):
                yield path, lineno, kwargs


def test_scanner_binding_selfcheck():
    """扫描器自检：必须识别 `import subprocess as X` 与 `from subprocess import Y`。

    背景：首版只匹配 `subprocess.X`，漏掉 `upstream/tests/commands/test_new_isolate.py`
    的 `import subprocess as _sp` 两处（BUILD 期由独立评审发现）。
    审计工具的漏检 = 假绿，故把「扫描器能识别别名」固化为断言。
    """
    src = (
        "import subprocess as _sp\n"
        "from subprocess import run as _run\n"
        "import subprocess\n"
        "a = _sp.run(['x'], text=True)\n"
        "b = _run(['x'], text=True)\n"
        "c = subprocess.run(['x'], text=True, encoding='utf-8', errors='replace')\n"
        "d = _sp.run(['x'], capture_output=True)\n"  # 非 text 模式，不入范围
    )
    found = list(_iter_subprocess_calls_in_tree(ast.parse(src)))
    assert len(found) == 3, f"应识别 3 处 text-mode 调用，实得 {found}"
    assert sum(1 for _, kw in found if "encoding" not in kw) == 2, (
        "别名导入的两处（a/b）应被判定为「缺 encoding」"
    )


def test_tc_tsp_001_text_mode_subprocess_declares_encoding():
    """TC-TSP-001: text-mode subprocess 调用 SHALL 显式指定 encoding=。"""
    missing = [
        f"{path.relative_to(REPO)}:{lineno}"
        for path, lineno, kwargs in _iter_text_mode_subprocess_calls()
        if "encoding" not in kwargs
    ]
    assert missing == [], (
        f"以下 {len(missing)} 处 text-mode subprocess 调用未指定 encoding=，"
        "解码将依赖运行环境 locale：\n  " + "\n  ".join(missing)
    )


def test_tc_tsp_004_errors_policy_is_observable_not_silent():
    """TC-TSP-004: errors= 取值 SHALL 可观测（replace/surrogateescape），SHALL NOT 静默（ignore）。"""
    silent: list[str] = []
    unexpected: list[str] = []
    for path, lineno, kwargs in _iter_text_mode_subprocess_calls():
        node = kwargs.get("errors")
        if node is None:
            continue
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            unexpected.append(f"{path.relative_to(REPO)}:{lineno} (非字面量)")
            continue
        value = node.value
        if value in SILENT_ERROR_POLICIES:
            silent.append(f"{path.relative_to(REPO)}:{lineno} errors={value!r}")
        elif value not in ALLOWED_ERROR_POLICIES:
            unexpected.append(f"{path.relative_to(REPO)}:{lineno} errors={value!r}")
    assert silent == [], (
        "以下调用使用静默丢弃的解码策略（会掩盖真实失败，见 EXP-2026-0014）：\n  "
        + "\n  ".join(silent)
    )
    assert unexpected == [], (
        "以下调用的 errors= 取值不在允许集合 {replace, surrogateescape} 内：\n  "
        + "\n  ".join(unexpected)
    )


def test_tc_tsp_004b_no_exception_swallowing_in_scanned_dirs():
    """TC-TSP-004（补充）: 扫描面内不得出现裸 `except:` 吞掉一切的分支。"""
    offenders: list[str] = []
    for base in SCAN_DIRS:
        root = REPO / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                source = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert offenders == [], (
        "以下位置存在裸 `except:`（会吞掉包括 KeyboardInterrupt 在内的一切异常）：\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# TC-TSP-001（扩展，对应 ADJ-001）—— 文本 I/O 的隐式 locale 依赖
# ---------------------------------------------------------------------------

TEXT_IO_METHODS = frozenset({"read_text", "write_text"})


def _is_pathish_receiver(node: ast.expr) -> bool:
    """判断属性式 `.open()` 的接收者是否「像路径对象」。

    只对**文件对象**要求 `encoding=`：`Path.open()` 与内置 `open()` 是文本 I/O；
    而 `tarfile.open()` / `urllib.request.OpenerDirector.open()` 等不是 —— 前者有
    自己的 `encoding=` 语义，后者**根本不接受** `encoding=`（补上去即 TypeError）。
    """
    if isinstance(node, ast.Call):
        return "path" in ast.unparse(node.func).lower()
    if isinstance(node, ast.BinOp):
        return True  # `BASE / "x.txt"` 形态的路径拼接
    if isinstance(node, (ast.Name, ast.Attribute)):
        text = ast.unparse(node).lower()
        return any(tok in text for tok in PATHISH_RECEIVER_TOKENS)
    return False


def _iter_text_io_calls():
    """产出 (path, lineno, api, mode, kwargs) —— 文本 I/O 调用；mode 为 None 表示未显式指定。

    `read_text()` / `write_text()` 无 mode 参数（恒为文本模式）。
    内置 `open()` 与「像路径」的 `Path.open()` 需按 mode 判定：含 `b` 者为二进制，
    **不得**指定 encoding。
    """
    for base in SCAN_DIRS:
        root = REPO / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                source = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in TEXT_IO_METHODS:
                    yield path, node.lineno, func.attr, None, {k.arg: k.value for k in node.keywords if k.arg}
                    continue
                if isinstance(func, ast.Attribute) and func.attr == "open":
                    if not _is_pathish_receiver(func.value):
                        continue  # tarfile / OpenerDirector 等，非文件对象
                elif not (isinstance(func, ast.Name) and func.id == "open"):
                    continue
                kwargs = {k.arg: k.value for k in node.keywords if k.arg}
                mode = None
                if "mode" in kwargs and isinstance(kwargs["mode"], ast.Constant):
                    mode = kwargs["mode"].value
                elif node.args and isinstance(node.args[0], ast.Constant):
                    mode = node.args[0].value
                yield path, node.lineno, "open", mode, kwargs


def test_tc_tsp_001_text_io_declares_encoding_when_text_mode():
    """TC-TSP-001（扩展）: 文本模式的 read_text/write_text/open SHALL 显式指定 encoding=。

    > 对应 ADJ-001：仅修 subprocess 不足以实现 REQ-001 的意图 ——
    > `Path.read_text()` 不带 encoding 时同样按 locale 解码，在 GBK 主机上读 UTF-8 源码即抛
    > UnicodeDecodeError。故把同一契约扩展到文本 I/O。
    """
    missing = [
        f"{path.relative_to(REPO)}:{lineno} ({api})"
        for path, lineno, api, mode, kwargs in _iter_text_io_calls()
        if not (isinstance(mode, str) and "b" in mode) and "encoding" not in kwargs
    ]
    assert missing == [], (
        f"以下 {len(missing)} 处文本 I/O 调用未指定 encoding=，解码将依赖运行环境 locale：\n  "
        + "\n  ".join(missing)
    )


def test_tc_tsp_001b_binary_mode_open_must_not_declare_encoding():
    """TC-TSP-001（补充）: 二进制模式的 open() SHALL NOT 指定 encoding=（会 ValueError）。

    > 防回归：机械补齐 encoding 时极易误伤 `open("rb")`，
    > 实测 `open("rb", encoding="utf-8")` 抛 `ValueError: binary mode doesn't take an encoding argument`。
    """
    offenders = [
        f"{path.relative_to(REPO)}:{lineno} mode={mode!r}"
        for path, lineno, api, mode, kwargs in _iter_text_io_calls()
        if isinstance(mode, str) and "b" in mode and "encoding" in kwargs
    ]
    assert offenders == [], (
        "以下二进制模式 open() 被错误地指定了 encoding=：\n  " + "\n  ".join(offenders)
    )

