"""FSD-004 门禁：经验库枚举不得假设 ``EXP-*.md`` 文件名前缀。

真源约定（2026-09-17 起）::

    经验库接受任意 ``*.md``；标识取 frontmatter 的 ``experience_id``，
    缺失时退回文件名 stem。

历史缺陷：STDD → fSTDD 迁移时，旧库文件名是语义化的
（如 ``scheduler_daily_queue_not_dropped.md``），不带 ``EXP-`` 前缀。
代码里散布 10 处 ``glob("EXP-*.md")`` / ``startswith("EXP-")`` 假设，
只修了 3 处（``_rebuild_index`` / ``_cmd_list`` / ``_cmd_stats``），
残留 6 处在 ``experience.py`` 内 —— 其中最致命的是 ``_cmd_search``：

    库实有 12 条 → ``search scheduler`` 返回空数组 + ``exit=0``
    → **静默错误结果**（脚本消费方无从察觉）

本测试同时做「静态防漂移」与「行为端到端」两层校验。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "fstdd"
CLI = PKG / "cli"

# 本地经验库枚举中的 EXP- 前缀假设由 AST 扫描判定（见 _collect_exp_assumptions）。
# 合理例外以行内 `FSD-004-EXEMPT` 注释标注（如 tar 包成员过滤，语义确实不同）。


def _iter_cli_py_files() -> list[Path]:
    return sorted(p for p in CLI.rglob("*.py") if "__pycache__" not in p.parts)


def _make_tmp_dir() -> Path:
    # 本沙箱 tmp_path fixture 会被 sitecustomize 拦截，故用 mkdtemp。
    return Path(tempfile.mkdtemp(prefix="fstdd_exp_"))


_EXP_FRONTMATTER = """---
experience_id: {eid}
category: {category}
pattern: "{pattern}"
root_cause: "{root_cause}"
language: python
severity: medium
lifecycle_state: discovered
tags: [scheduler, test]
---
# {pattern}

Root Cause: {root_cause}
"""


def _write_exp(directory: Path, filename: str, eid: str, pattern: str) -> Path:
    p = directory / filename
    p.write_text(
        _EXP_FRONTMATTER.format(
            eid=eid, category="scheduler", pattern=pattern, root_cause="rc-" + pattern
        ),
        encoding="utf-8",
    )
    return p


# --------------------------------------------------------------------------
# 1. 静态防漂移：CLI 源码里不得残留 EXP- 前缀假设
# --------------------------------------------------------------------------
def _collect_exp_assumptions(py: Path) -> list[tuple[int, str]]:
    """AST 扫描：收集对经验库文件名的 EXP- 前缀假设。

    用 AST 而非文本正则，天然排除注释与 docstring 里对该 bug 的叙述性引用。
    """
    import ast

    source = py.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        attr = getattr(node.func, "attr", None)
        first = node.args[0]
        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            continue
        if attr == "glob" and "EXP-*.md" in first.value:
            found.append((node.lineno, f'glob("{first.value}")'))
        elif attr == "startswith" and first.value == "EXP-":
            found.append((node.lineno, 'startswith("EXP-")'))
    return found


def test_no_exp_prefix_assumption_in_cli_sources() -> None:
    offenders: list[str] = []
    for py in _iter_cli_py_files():
        lines = py.read_text(encoding="utf-8").splitlines()
        for line_no, snippet in _collect_exp_assumptions(py):
            # 显式豁免：紧邻上文 5 行内出现 FSD-004-EXEMPT 标记
            # （用于 tar 包成员过滤等语义确实不同的场景）。
            ctx = "\n".join(lines[max(0, line_no - 7) : line_no - 1])
            if "FSD-004-EXEMPT" in ctx:
                continue
            offenders.append(f"{py.relative_to(REPO)}:{line_no}  {snippet}")

    assert not offenders, (
        "以下位置假设了经验库文件名带 EXP- 前缀，会漏掉迁移来的语义名文件"
        "（症状：search 返回空、review 无草稿、next_id 重复）。"
        "本地库枚举请改用 _iter_experience_files；确属不同语义的场景"
        "请在上文加 `FSD-004-EXEMPT` 注释说明：\n"
        + "\n".join(f"  - {o}" for o in offenders)
    )


# --------------------------------------------------------------------------
# 2. 公共迭代器语义
# --------------------------------------------------------------------------
def test_iter_experience_files_covers_semantic_and_prefixed() -> None:
    from fstdd.cli.commands.experience import _iter_experience_files

    tmp = _make_tmp_dir()
    try:
        _write_exp(tmp, "scheduler_daily_queue_not_dropped.md", "scheduler_daily", "queue")
        _write_exp(tmp, "EXP-2026-0001.md", "EXP-2026-0001", "legacy")
        (tmp / "README.md").write_text("not an experience", encoding="utf-8")
        (tmp / ".hidden.md").write_text("hidden", encoding="utf-8")

        names = [p.name for p in _iter_experience_files(tmp)]

        assert "scheduler_daily_queue_not_dropped.md" in names, names
        assert "EXP-2026-0001.md" in names, names
        assert ".hidden.md" not in names, names
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_iter_experience_files_on_missing_dir_returns_empty() -> None:
    from fstdd.cli.commands.experience import _iter_experience_files

    assert _iter_experience_files(Path("/nonexistent/exp-dir-xyz")) == []


# --------------------------------------------------------------------------
# 3. 行为端到端：search / review / stats 都必须看得见语义名经验
# --------------------------------------------------------------------------
def test_search_finds_semantic_named_experience() -> None:
    """FSD-004 的核心症状：库非空但 search 静默返回空。"""
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write_exp(exp, "scheduler_daily_queue_not_dropped.md", "sched_daily", "queue not dropped")

        proc = subprocess.run(
            [sys.executable, "-m", "fstdd", "experience", "search", "queue",
             "--format", "json"],
            cwd=tmp,
            capture_output=True,
            text=True,
            env=_cli_env(),
        )

        assert proc.returncode == 0, proc.stderr
        assert "queue not dropped" in proc.stdout, (
            "search 未命中语义名经验文件（静默返回空）："
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_review_lists_semantic_named_draft() -> None:
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write_exp(exp, "hardcoded_threshold_creates_fatal.md", "hct", "hardcoded threshold")

        proc = subprocess.run(
            [sys.executable, "-m", "fstdd", "experience", "review"],
            cwd=tmp,
            capture_output=True,
            text=True,
            env=_cli_env(),
        )

        assert "hardcoded threshold" in proc.stdout, (
            "review 未把语义名经验识别为待审草稿："
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stats_counts_semantic_named_experiences() -> None:
    """回归保护：stats 是已修的 3 处之一，不得退回。"""
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write_exp(exp, "a_lesson.md", "a_lesson", "pattern a")
        _write_exp(exp, "EXP-2026-0007.md", "EXP-2026-0007", "pattern b")

        proc = subprocess.run(
            [sys.executable, "-m", "fstdd", "experience", "stats"],
            cwd=tmp,
            capture_output=True,
            text=True,
            env=_cli_env(),
        )

        assert proc.returncode == 0, proc.stderr
        assert "2" in proc.stdout, (
            f"stats 未计入语义名经验：stdout={proc.stdout!r}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# 4. session-end hook 与 init 的经验库计数
# --------------------------------------------------------------------------
def test_session_end_hook_counts_semantic_named_experiences() -> None:
    from fstdd.cli.commands.hooks import HOOK_SCRIPTS

    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write_exp(exp, "scheduler_daily_queue_not_dropped.md", "sched_daily", "queue")
        _write_exp(exp, "EXP-2026-0001.md", "EXP-2026-0001", "legacy")

        script = tmp / "session_end.py"
        script.write_text(HOOK_SCRIPTS["session-end"], encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=tmp,
            capture_output=True,
            text=True,
        )

        assert "2 entries" in proc.stdout, (
            "session-end hook 未把语义名经验计入总数："
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_init_reports_experience_count_by_shared_iterator() -> None:
    """init.py 的经验库计数必须走公共语义（不得自带 EXP- 假设）。"""
    source = (CLI / "commands" / "init.py").read_text(encoding="utf-8")
    assert "EXP-*.md" not in source, (
        "init.py 仍以 EXP-*.md 统计经验库，会漏掉语义名文件"
    )


# --------------------------------------------------------------------------
# 5. FSD-023：迁移数据的字符串数值字段不得让检索崩溃
# --------------------------------------------------------------------------
_STRING_NUM_FRONTMATTER = """---
experience_id: {eid}
category: pitfall
pattern: "queue not dropped"
root_cause: "scheduler queue overflow"
language: python
severity: high
lifecycle_state: deposited
confidence: '0.8'
adoption_count: '3'
occurrences: '2'
provenance_weight: '0.85'
community_votes_useful: '5'
tags: [scheduler]
---
# queue not dropped

Body mentioning scheduler.
"""


def test_search_tolerates_string_numeric_frontmatter() -> None:
    """FSD-023：迁移脚本把数值字段写成了带引号字符串（'0.8'）。

    修复 glob 后这些文件才首次被读到，随即在打分环节抛
    ``TypeError: can't multiply sequence by non-int of type 'float'``
    —— 症状由「静默返回空」变成「直接崩溃」，两者都不可用。
    """
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        (exp / "scheduler_daily_queue_not_dropped.md").write_text(
            _STRING_NUM_FRONTMATTER.format(eid="sched_daily"), encoding="utf-8"
        )

        proc = subprocess.run(
            [sys.executable, "-m", "fstdd", "experience", "search", "scheduler",
             "--format", "json"],
            cwd=tmp,
            capture_output=True,
            text=True,
            env=_cli_env(),
        )

        assert proc.returncode == 0, (
            "字符串数值字段导致 search 崩溃："
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
        assert "queue not dropped" in proc.stdout, proc.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stats_and_list_survive_string_numeric_frontmatter() -> None:
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        (exp / "hardcoded_threshold_fatal.md").write_text(
            _STRING_NUM_FRONTMATTER.format(eid="hct"), encoding="utf-8"
        )

        for sub in ("stats", "list"):
            proc = subprocess.run(
                [sys.executable, "-m", "fstdd", "experience", sub],
                cwd=tmp,
                capture_output=True,
                text=True,
                env=_cli_env(),
            )
            assert proc.returncode == 0, (
                f"experience {sub} 在字符串数值字段下崩溃：{proc.stderr!r}"
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# 6. 数据层：真实经验库不得残留字符串数值字段
# --------------------------------------------------------------------------
_NUMERIC_KEYS = (
    "confidence",
    "adoption_count",
    "occurrences",
    "provenance_weight",
    "community_votes_useful",
    "community_votes_unuseful",
)


def test_live_experience_library_has_numeric_fields() -> None:
    """门禁：本仓库经验库中的数值字段必须是真数值（不是 '0.8' 这类字符串）。

    与 ``test_changes_dir_consistency`` 同属「数据与代码契约对齐」类断言。
    """
    import yaml as _yaml

    exp_dir = REPO / ".fstdd" / "experiences"
    if not exp_dir.exists():
        pytest.skip("经验库不存在")

    bad: list[str] = []
    for p in sorted(exp_dir.glob("*.md")):
        parts = p.read_text(encoding="utf-8").split("---", 2)
        if len(parts) < 3:
            continue
        data = _yaml.safe_load(parts[1]) or {}
        for key in _NUMERIC_KEYS:
            if key in data and isinstance(data[key], str):
                bad.append(f"{p.name}: {key}={data[key]!r}")

    assert not bad, (
        "以下经验的数值字段是字符串，会让检索/排序环节抛 TypeError"
        "（应改为不带引号的数值）：\n" + "\n".join(f"  - {b}" for b in bad)
    )


def _cli_env() -> dict:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return env
