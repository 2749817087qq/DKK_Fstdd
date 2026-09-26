"""测试 _find_change_dir / find_change_dir 函数。"""
import pytest
from pathlib import Path
from datetime import date

from fstdd.cli.finder import find_change_dir


def test_exact_match(sample_change: Path):
    """精确匹配 change 目录名。"""
    result = find_change_dir(sample_change.name, sample_change.parent.parent.parent)
    assert result is not None
    assert result.name == sample_change.name


def test_fuzzy_match(sample_change: Path):
    """模糊匹配（省略日期前缀）。"""
    # 提取名称中日期之后的部分
    name_part = sample_change.name.split("-", 3)[-1] if sample_change.name[0].isdigit() else sample_change.name
    result = find_change_dir(name_part, sample_change.parent.parent.parent)
    assert result is not None
    assert result.name == sample_change.name


def test_no_match(temp_project: Path):
    """无匹配时返回 None。"""
    result = find_change_dir("nonexistent-feature", temp_project)
    assert result is None


def test_no_name_returns_latest(sample_change: Path):
    """不传名称返回最近修改的 change（唯一的那个）。"""
    result = find_change_dir(None, sample_change.parent.parent.parent)
    assert result is not None
    assert result.name == sample_change.name


def test_empty_changes_dir(temp_project: Path):
    """changes/ 目录存在但为空时返回 None。"""
    result = find_change_dir(None, temp_project)
    assert result is None


def test_no_changes_dir(tmp_path: Path):
    """没有 changes/ 目录时返回 None。"""
    result = find_change_dir(None, tmp_path)
    assert result is None


def test_directory_without_state_file(temp_project: Path):
    """目录存在但无 .fstdd.yaml 时不应匹配。"""
    d = temp_project / ".fstdd" / "changes" / "2026-01-01-no-state"
    d.mkdir(parents=True)
    result = find_change_dir("no-state", temp_project)
    assert result is None


def test_exact_match_no_state_file(temp_project: Path):
    """精确匹配但无 .fstdd.yaml 返回 None。"""
    # 创建无状态文件的目录
    d = temp_project / ".fstdd" / "changes" / "2026-01-01-no-state"
    d.mkdir(parents=True)
    result = find_change_dir("2026-01-01-no-state", temp_project)
    assert result is None


# ---------------------------------------------------------------------------
# TC-FAF-001 ~ 006：include_archive 归档回退（change 2026-09-26-finder-archive-fallback）
# spec: specs/change-dir-resolution/spec.md（SC-001 ~ SC-006）
# ---------------------------------------------------------------------------
def _mk(base: Path, name: str) -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".fstdd.yaml").write_text(f"change_id: {name}\n", encoding="utf-8")
    return d


def test_faf_001_default_ignores_archive(temp_project: Path):
    """TC-FAF-001 / SC-001：不传 include_archive 时归档件不可见（默认零漂移）。

    附带锚定「仅关键字参数」契约：第 3 个位置参数必须不被接受，
    否则既有位置调用会被静默改变语义。
    """
    archived = _mk(temp_project / ".fstdd" / "archive", "2026-01-01-archived-only")
    before = archived.stat().st_mtime

    assert find_change_dir("archived-only", temp_project) is None, (
        "默认语义必须只查在办；归档回退需显式开启"
    )
    assert archived.stat().st_mtime == before, "查询不得触碰归档目录"

    with pytest.raises(TypeError):
        find_change_dir("archived-only", temp_project, True)  # type: ignore[misc]


def test_faf_002_archive_hit_when_enabled(temp_project: Path):
    """TC-FAF-002 / SC-002：include_archive=True 时归档件可被解析。"""
    archived = _mk(temp_project / ".fstdd" / "archive", "2026-01-01-archived-only")

    result = find_change_dir("archived-only", temp_project, include_archive=True)

    assert result is not None
    assert result == archived
    assert (result / ".fstdd.yaml").exists()
    assert result.as_posix().endswith(".fstdd/archive/2026-01-01-archived-only")


def test_faf_003_changes_wins_over_archive(temp_project: Path):
    """TC-FAF-003 / SC-003：同名时 changes/ 优先于 archive/。"""
    active = _mk(temp_project / ".fstdd" / "changes", "2026-01-01-dup")
    _mk(temp_project / ".fstdd" / "archive", "2026-01-01-dup")

    result = find_change_dir("dup", temp_project, include_archive=True)

    assert result == active
    assert ".fstdd/archive" not in result.as_posix(), "不得误取归档副本"


def test_faf_004_suffix_match_in_archive(temp_project: Path):
    """TC-FAF-004 / SC-004：短名后缀匹配在归档区同样生效。"""
    _mk(temp_project / ".fstdd" / "archive", "2026-01-01-archived-feature")

    result = find_change_dir("archived-feature", temp_project, include_archive=True)

    assert result is not None
    assert result.name == "2026-01-01-archived-feature"
    assert ".fstdd/archive" in result.as_posix()


def test_faf_005_none_name_never_returns_archived(temp_project: Path):
    """TC-FAF-005 / SC-005：name=None 恒只取 changes/，即使 archive/ 更「新」。"""
    import os as _os

    active = _mk(temp_project / ".fstdd" / "changes", "2026-01-01-active")
    newer_archive = _mk(temp_project / ".fstdd" / "archive", "2026-09-01-archived-newer")

    base = 1_700_000_000.0
    _os.utime(active, (base, base))
    _os.utime(newer_archive, (base + 999, base + 999))

    result = find_change_dir(None, temp_project, include_archive=True)

    assert result is not None
    assert result == active, "「当前 change」不可能位于归档区"
    assert ".fstdd/archive" not in result.as_posix()


def test_faf_006_missing_archive_dir_is_tolerated(temp_project: Path):
    """TC-FAF-006 / SC-006：无 archive/ 目录时不抛异常、不创建目录。"""
    import shutil as _shutil

    _shutil.rmtree(temp_project / ".fstdd" / "archive")
    assert not (temp_project / ".fstdd" / "archive").exists()

    result = find_change_dir("whatever", temp_project, include_archive=True)

    assert result is None
    assert not (temp_project / ".fstdd" / "archive").exists(), "查询不得产生副作用"
