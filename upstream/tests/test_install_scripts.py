# -*- coding: utf-8 -*-
"""一键安装脚本的**参数解析**回归测试（install.sh / install.ps1）。

## 为什么需要这一套

`install.sh` 原用 `for arg in "$@"` 配 `shift` 解析参数。当 `--py` **不是首个参数**
（典型用法 `./install.sh --yes --py /x/python`）时会 `shift` 掉错误元素，
令 `${1}` 落到 `--py` 自身、`PY` 被赋成**字面量 `--py`** —— 随后即报
「未找到可用的 Python 3.10+」，而所给路径其实可用。

该修复（2026-09-29）落下时**没有配套测试** —— 全套测试此前无一处引用
`install.sh` / `install.ps1`。于是这条断言的存在理由就是：让「一键安装能用」
从**人工口头结论**变成**可回归的门禁**。

## 断言方式：真跑，而非读源码

套件里已有一条以「源码字符串断言」守护 bug 的反例（见 `test_install_source.py`
的 `test_a5` 历史注记）。故本套**不 grep 源码**，而是用**可用解释器实跑脚本**、
断言它选中的正是所给解释器、且以 0 退出。

## 反副作用

所有用例都把 `FSTDD_OUT` 指向 pytest 的临时目录，**不写真实用户 skill 目录**。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SH = REPO / "install.sh"
PS1 = REPO / "install.ps1"

# 传给脚本的解释器：用 POSIX 风格斜杠，便于与脚本回显逐字比对。
PY_ARG = sys.executable.replace("\\", "/")


def _usable(exe: str | None, args: list[str]) -> bool:
    """存在**且真能跑**才算可用（存在即用会误判 WSL 启动器桩）。"""
    if not exe or not Path(exe).exists():
        return False
    try:
        return subprocess.run(
            [exe, *args], capture_output=True, timeout=60
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _find_usable_bash() -> str | None:
    """返回实际可用的 bash；不存在、或存在但跑不起来（如未装发行版的 WSL），返回 None。

    与 `test_mirror_alert_ops.py` 的判据同源：Windows 下 `shutil.which("bash")`
    命中的 `C:\\Windows\\system32\\bash.exe` 是 WSL 启动器，未安装发行版时
    `存在却一执行就失败`。故须**真跑一次** `bash -c true` 才采纳；
    另补 Git for Windows 的常见安装位（其 `bash.exe` 通常不在 PATH 上）。
    """
    for cand in (
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if _usable(cand, ["-c", "true"]):
            return cand
    return None


def _find_usable_powershell() -> str | None:
    for name in ("pwsh", "powershell"):
        exe = shutil.which(name)
        if _usable(exe, ["-NoProfile", "-Command", "exit 0"]):
            return exe
    return None


BASH = _find_usable_bash()
POWERSHELL = _find_usable_powershell()


def _run(cmd: list[str], out_dir: Path) -> subprocess.CompletedProcess:
    """在临时 skill 输出目录下真跑安装脚本，避免触碰真实用户目录。"""
    env = dict(os.environ, FSTDD_OUT=str(out_dir))
    env.pop("FSTDD_PY", None)  # 别让外部环境变量掩盖脚本自身的取值逻辑
    return subprocess.run(
        cmd, cwd=str(REPO), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600,
    )


def _ps_quote(s: str) -> str:
    """PowerShell 单引号字符串转义（单引号自身加倍）。"""
    return "'" + str(s).replace("'", "''") + "'"


def _ps_arg(a: str) -> str:
    """参数名（`-Xxx`）原样传递，参数值安全引用。

    ⚠️ 不可把参数名也加引号 —— `'-Yes'` 在 PowerShell 里是**字符串字面量**，
    会退化成位置参数，导致 `param()` 绑定错位（实测 `$Platform` 被赋成 `-Python`）。
    """
    s = str(a)
    if s.startswith("-") and not s[1:2].isdigit():
        return s
    return _ps_quote(s)


def _force_utf8_output(cmd: list[str]) -> list[str]:
    """让 Windows PowerShell 以 UTF-8 写出重定向的 stdout。

    根因：Windows PowerShell 5.1 在 stdout 被重定向时按 `[Console]::OutputEncoding`
    编码（中文主机 = GBK / CP936），与调用点声明的 `encoding="utf-8"` 不一致
    ⇒ 中文输出被解成 U+FFFD，断言失败。此失败**只在控制台非 UTF-8 时出现**
    （权威门禁环境为 UTF-8 控制台，故长期未被发现）—— 属 REQ-001「解码结果不依赖
    控制台代码页」的遗漏点。`pwsh`（PowerShell 7+）默认即 UTF-8，无需包装。
    """
    if os.path.basename(cmd[0]).lower().startswith("pwsh"):
        return cmd
    if "-File" not in cmd:
        return cmd
    i = cmd.index("-File")
    script, rest = cmd[i + 1], cmd[i + 2:]
    inner = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; & "
             + _ps_quote(script))
    if rest:
        inner += " " + " ".join(_ps_arg(a) for a in rest)
    return cmd[:i] + ["-Command", inner]


def _posix(p: Path) -> str:
    return str(p).replace("\\", "/")


@pytest.mark.skipif(BASH is None, reason="本机无可用 bash（不存在或无法执行）")
class TestInstallShArgParse:
    """`install.sh --py` 取值须按**当前位置**读取 —— 与首个参数无关。"""

    def test_install_sh_py_after_yes(self, tmp_path: Path):
        """回归：`--yes --py <解释器>`（`--py` 非首参）必须选中所给解释器。

        修复前 `--py` 会落到字面量 `--py`，脚本报「未找到可用的 Python 3.10+」并以 1 退出。
        """
        r = _run([BASH, _posix(SH), "--yes", "--py", PY_ARG], tmp_path / "skills")
        assert "[FAIL] 未找到可用的 Python" not in r.stdout, (
            "`--py` 非首参时取值错位 —— 又回到了「未找到可用解释器」的老毛病"
        )
        assert f"[1/4] Python: {PY_ARG}" in r.stdout, (
            f"未选中所给解释器；实际输出：\n{r.stdout}"
        )
        assert r.returncode == 0, f"安装脚本非 0 退出（{r.returncode}）：\n{r.stdout}\n{r.stderr}"

    def test_install_sh_py_inline_form(self, tmp_path: Path):
        """`--py=<解释器>` 内联写法行为不变。"""
        r = _run([BASH, _posix(SH), "--yes", f"--py={PY_ARG}"], tmp_path / "skills")
        assert f"[1/4] Python: {PY_ARG}" in r.stdout, r.stdout
        assert r.returncode == 0, f"安装脚本非 0 退出（{r.returncode}）：\n{r.stdout}\n{r.stderr}"


@pytest.mark.skipif(POWERSHELL is None, reason="本机无可用 PowerShell（不存在或无法执行）")
class TestInstallPs1ArgParse:
    """`install.ps1 -Python` 显式指定必须被采纳（与 install.sh 对称）。"""

    def test_install_ps1_explicit_python(self, tmp_path: Path):
        r = _run(
            _force_utf8_output(
                [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(PS1), "-Yes", "-Python", PY_ARG]
            ),
            tmp_path / "skills",
        )
        assert f"使用：{PY_ARG}" in r.stdout, (
            f"未采纳 `-Python` 指定的解释器；实际输出：\n{r.stdout}"
        )
        assert r.returncode == 0, f"安装脚本非 0 退出（{r.returncode}）：\n{r.stdout}\n{r.stderr}"