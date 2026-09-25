"""FSD-025 门禁：经验库索引必须有失效机制。

原实现 ``_load_index``：**索引文件存在就直接读，从不校验是否过期**。

后果：任何绕过 CLI 的库变更（手工新增经验、迁移脚本落盘、外部同步）
都不会反映到索引 —— ``stats`` / ``list`` 的计数与分类长期滞后。

实测：库内 15 条，``stats`` 报 12 条（差值为本轮新增的 3 条）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_TEMPLATE = """---
experience_id: {eid}
category: {category}
pattern: "{pattern}"
root_cause: "rc"
language: python
severity: medium
lifecycle_state: discovered
tags: [t]
---
# {pattern}
"""


def _make_tmp_dir() -> Path:
    # 本沙箱 tmp_path fixture 会被 sitecustomize 拦截，故用 mkdtemp。
    return Path(tempfile.mkdtemp(prefix="fstdd_idx_"))


def _write(directory: Path, name: str, eid: str, category: str = "pitfall",
           pattern: str = "p") -> Path:
    p = directory / name
    p.write_text(_TEMPLATE.format(eid=eid, category=category, pattern=pattern),
                 encoding="utf-8")
    return p


def _cli_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return env


def _stats_total(cwd: Path) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "fstdd", "experience", "stats"],
        cwd=cwd, capture_output=True, text=True, env=_cli_env(),
    )
    assert proc.returncode == 0, proc.stderr
    for line in proc.stdout.splitlines():
        if "总经验数" in line:
            return int(line.split(":")[-1].strip())
    raise AssertionError(f"未找到总经验数行：{proc.stdout!r}")


def test_index_refreshes_after_external_add() -> None:
    """索引建立后，外部新增经验必须被计入。"""
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write(exp, "first_lesson.md", "first_lesson")

        assert _stats_total(tmp) == 1, "首次统计应建立索引并返回 1"

        # 绕过 CLI 直接落盘（模拟迁移脚本 / 外部同步）
        _write(exp, "second_lesson.md", "second_lesson")

        assert _stats_total(tmp) == 2, (
            "索引未随外部新增刷新（典型：索引存在即直接读，无失效判据）"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_index_refreshes_after_external_delete() -> None:
    """外部删除经验后，索引不得残留幽灵条目。"""
    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write(exp, "first_lesson.md", "first_lesson")
        _write(exp, "second_lesson.md", "second_lesson")

        assert _stats_total(tmp) == 2

        (exp / "second_lesson.md").unlink()

        assert _stats_total(tmp) == 1, (
            "索引未随外部删除刷新，计数虚高（幽灵条目）"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_index_is_stale_detects_newer_file() -> None:
    """单元层：_index_is_stale 必须能识别「文件比索引新」。"""
    from fstdd.cli.commands.experience import _index_is_stale, _rebuild_index, _save_index

    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        f = _write(exp, "a.md", "a")
        idx_path = exp / ".experience-index.yaml"
        _save_index(exp, _rebuild_index(exp))

        assert not _index_is_stale(exp, idx_path)

        # 让文件严格晚于索引
        os.utime(f, (f.stat().st_atime, idx_path.stat().st_mtime + 10))

        assert _index_is_stale(exp, idx_path), "文件晚于索引时应判过期"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_index_is_stale_detects_count_mismatch() -> None:
    """单元层：库条目数与索引 total 不一致必须判过期（覆盖删除场景）。"""
    from fstdd.cli.commands.experience import _index_is_stale, _rebuild_index, _save_index

    tmp = _make_tmp_dir()
    try:
        exp = tmp / ".fstdd" / "experiences"
        exp.mkdir(parents=True)
        _write(exp, "a.md", "a")
        idx_path = exp / ".experience-index.yaml"
        _save_index(exp, _rebuild_index(exp))

        _write(exp, "b.md", "b")

        assert _index_is_stale(exp, idx_path), "条目数不一致时应判过期"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
