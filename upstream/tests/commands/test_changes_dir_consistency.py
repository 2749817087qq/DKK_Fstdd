"""FSD-018 防漂移门禁：change 目录的「宣称路径」必须等于「实际落点」。

真源约定（由 finder/state/phase/gate/guard/work/canon/index/... 共同实现）::

    <project_root>/.fstdd/changes/<change_name>

历史缺陷：三个位置宣称的是根目录 ``changes``，而 14 个模块实际用的是
``.fstdd/changes``：

* ``new.py``       —— 打印文案 ``changes/{name}``（无 ``.fstdd/`` 前缀）
* ``hooks.py``     —— SessionStart / PreCompact 内嵌脚本读 ``project_root / "changes"``
* ``config.d/project.yaml`` —— ``paths.changes_dir: changes``（零消费点的死配置）

后果：Agent 照文案/配置把 change 建到 ``<root>/changes/``，而 ``guard`` 只扫
``<root>/.fstdd/changes/`` → 找不到活跃 change → 判定「未进入可编辑流程」
→ 无差别阻断项目内**所有**写入（实测 CCREITS 命中）。

本测试确保三处宣称与落点永久一致。
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "fstdd"
CLI = PKG / "cli"

TRUTH_DIR = ".fstdd/changes"

# 裸 `project_root / "changes"` —— 把 change 目录解析到项目根的 bug 签名。
# 例外：`batch_dir / "changes"`（批次内部子目录，基准不是 project_root）。
_BARE_ROOT_JOIN = re.compile(
    r"""(?:project_root|Path\.cwd\(\)|cwd\(\))\s*/\s*["']changes["']"""
)

# 字符串字面量里提到 change 目录却没有 .fstdd/ 前缀。
_UNPREFIXED_IN_TEXT = re.compile(r"(?<!\.fstdd/)changes/")


def _iter_cli_py_files() -> list[Path]:
    return sorted(p for p in CLI.rglob("*.py") if "__pycache__" not in p.parts)


def _make_tmp_dir() -> Path:
    # 本沙箱的 tmp_path fixture 会被 sitecustomize 拦截，故用 mkdtemp。
    return Path(tempfile.mkdtemp(prefix="fstdd_paths_"))


# --------------------------------------------------------------------------
# 1. 代码层：不得出现裸 project_root / "changes"
# --------------------------------------------------------------------------
def test_no_bare_project_root_changes_join() -> None:
    offenders: list[str] = []
    for py in _iter_cli_py_files():
        text = py.read_text(encoding="utf-8")
        for m in _BARE_ROOT_JOIN.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            offenders.append(f"{py.relative_to(REPO)}:{line_no}")

    assert not offenders, (
        "以下位置把 change 目录解析到项目根 changes/，"
        f"必须改为 {TRUTH_DIR}/：\n" + "\n".join(f"  - {o}" for o in offenders)
    )


# --------------------------------------------------------------------------
# 2. 文案层：new.py 提到 change 目录的字符串必须带 .fstdd/ 前缀
# --------------------------------------------------------------------------
def test_new_py_messages_declare_fstdd_prefix() -> None:
    source = (CLI / "commands" / "new.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        # f-string 的静态片段在 JoinedStr.values 里也是 Constant
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _UNPREFIXED_IN_TEXT.search(node.value):
                offenders.append((node.lineno, node.value.strip()[:80]))

    assert not offenders, (
        "new.py 中的输出文案宣称了根目录 changes/（与实际落点 "
        f"{TRUTH_DIR}/ 不符，会误导调用方）：\n"
        + "\n".join(f"  L{i}: {s!r}" for i, s in sorted(offenders))
    )


# --------------------------------------------------------------------------
# 3. 行为层：SessionStart hook 必须能看见 .fstdd/changes 下的活跃 change
# --------------------------------------------------------------------------
def test_session_start_hook_reads_fstdd_changes() -> None:
    from fstdd.cli.commands.hooks import HOOK_SCRIPTS

    tmp = _make_tmp_dir()
    try:
        change = tmp / ".fstdd" / "changes" / "2026-01-01-demo"
        change.mkdir(parents=True)
        (change / ".fstdd.yaml").write_text(
            "change_name: demo\nactive_phase: build\n", encoding="utf-8"
        )

        script = tmp / "session_start.py"
        script.write_text(HOOK_SCRIPTS["session-start"], encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=tmp,
            capture_output=True,
            text=True,
        )

        assert "Active change: demo" in proc.stdout, (
            "SessionStart hook 未能发现 .fstdd/changes/ 下的活跃 change；"
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pre_compact_hook_reads_fstdd_changes() -> None:
    from fstdd.cli.commands.hooks import HOOK_SCRIPTS

    tmp = _make_tmp_dir()
    try:
        change = tmp / ".fstdd" / "changes" / "2026-01-01-demo"
        change.mkdir(parents=True)
        (change / ".fstdd.yaml").write_text(
            "change_name: demo\nactive_phase: build\n", encoding="utf-8"
        )

        script = tmp / "pre_compact.py"
        script.write_text(HOOK_SCRIPTS["pre-compact"], encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=tmp,
            capture_output=True,
            text=True,
        )

        assert "State saved" in proc.stdout, (
            "PreCompact hook 未能发现 .fstdd/changes/ 下的活跃 change；"
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# 4. 配置层：config.d/project.yaml 的 paths.* 不得与真源矛盾
# --------------------------------------------------------------------------
def test_config_paths_changes_dir_matches_truth() -> None:
    cfg_path = REPO / ".fstdd" / "config.d" / "project.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    paths = cfg.get("paths") or {}

    declared = paths.get("changes_dir")
    assert declared == TRUTH_DIR, (
        f"{cfg_path.relative_to(REPO)} 中 paths.changes_dir={declared!r}，"
        f"与代码真源 {TRUTH_DIR!r} 矛盾。"
    )


def test_config_paths_are_self_consistent() -> None:
    """paths.* 各项要么带 .fstdd/ 前缀，要么是项目根下的真实目录名。

    `changes_dir: changes` + `experiences_dir: .fstdd/experiences` 这种混写
    正是漂移的温床，必须禁止。
    """
    cfg_path = REPO / ".fstdd" / "config.d" / "project.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    paths = cfg.get("paths") or {}

    bad = {
        k: v
        for k, v in paths.items()
        if isinstance(v, str) and not v.startswith(".fstdd/")
    }
    assert not bad, (
        "paths.* 中以下条目未使用 .fstdd/ 前缀，与其余条目风格不一致"
        f"（易被误读为项目根相对路径）：{bad}"
    )
