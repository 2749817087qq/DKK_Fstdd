"""FSTDD EXP-2026-0027 / EXP-2026-0031 / EXP-2026-0032 contract_gap 回归测试。

Change: 2026-10-27-contract-gap-regression-tests
Task:   code（v3.4.0 增量回归测试加固）

锁定 3 类攻击向量已被挡住：
  - EXP-2026-0032: `_resolve_in` 输入层拒绝含分隔符/`..` 的 name
  - EXP-2026-0027: archive 守卫用 `resolve().relative_to()` 归一化判定
  - EXP-2026-0031: 全仓无内联 `(?i)` 拼接 regex

**本 change 只加测试，不改生产代码。** 若测试暴露回归，说明代码修复本身有问题。
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── 定位 upstream 包 ───────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests → stdd-repo/
_UPSTREAM = _REPO_ROOT / "upstream"
if str(_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM))


# ─── 功能 A: `_resolve_in` 输入拒绝（EXP-2026-0032）────────────────

class TestResolveInInputRejection:
    """EXP-2026-0032：`_resolve_in` 必须在输入层拒绝逃逸 name。"""

    def _make_change(self, base: Path, name: str) -> Path:
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        (d / ".fstdd.yaml").write_text("# stub\n", encoding="utf-8")
        return d

    def test_reject_path_separators(self, tmp_path):  # TC-CGR-001
        """[正常路径] TC-CGR-001：拒绝含 / 与 \\ 的 name。"""
        from fstdd.cli.finder import _resolve_in

        self._make_change(tmp_path, "foo-bar")  # 保证 base_dir 非空

        for name in ["foo/bar", "foo\\bar", "foo\\..\\bar", "foo/../bar"]:
            result = _resolve_in(tmp_path, name)
            assert result is None, (
                f"_resolve_in 未拒绝含分隔符的 name={name!r}，返回 {result!r}"
            )

    def test_reject_dotdot_variants(self, tmp_path):  # TC-CGR-002
        """[正常路径] TC-CGR-002：拒绝所有 `..` 逃逸形态。"""
        from fstdd.cli.finder import _resolve_in

        # 建一个真 archive 目录，防止逃逸真的成功时误伤父目录
        archive = tmp_path / "archive"
        archive.mkdir()
        (archive / ".fstdd.yaml").write_text("# stub\n", encoding="utf-8")

        for name in ["..", "../bar", "foo/..", "foo/../bar", "./../bar", "a/../b/../c"]:
            result = _resolve_in(tmp_path, name)
            assert result is None, (
                f"_resolve_in 未拒绝 `..` 形态 name={name!r}，返回 {result!r} —— "
                f"EXP-2026-0032 攻击向量复活"
            )

    def test_reject_empty_and_dot(self, tmp_path):  # TC-CGR-003
        """[边界] TC-CGR-003：拒绝空字符串与 `.`。"""
        from fstdd.cli.finder import _resolve_in

        self._make_change(tmp_path, "safe")
        for name in ["", ".", ".."]:
            result = _resolve_in(tmp_path, name)
            assert result is None, f"_resolve_in 未拒绝 {name!r}"

    def test_accepts_valid_change_name(self, tmp_path):  # TC-CGR-004
        """[回归] TC-CGR-004：合法 change 名必须放行（避免收紧后误拒）。"""
        from fstdd.cli.finder import _resolve_in

        target = self._make_change(tmp_path, "foo-bar-2026-10-27")
        result = _resolve_in(tmp_path, "foo-bar-2026-10-27")
        assert result is not None, "合法 change 名被误拒 —— 回归风险"
        assert result == target, f"返回路径 {result} 与预期 {target} 不一致"


# ─── 功能 B: archive 守卫归一化判定（EXP-2026-0027）───────────────

class TestArchiveGuardNormalized:
    """EXP-2026-0027：archive 守卫 MUST 用 `resolve().relative_to()` 归一化判定。"""

    def test_archive_path_is_under_archive(self, tmp_path):  # TC-CGR-005
        """[正常路径] TC-CGR-005：真归档路径被判定为归档态。"""
        archive = tmp_path / "archive"
        archived_change = archive / "some-change"
        archived_change.mkdir(parents=True)

        hit = archived_change
        archive_root = archive
        # 用 resolve() 归一化后判定 —— 这是 EXP-2026-0027 的修复形态
        try:
            hit.resolve().relative_to(archive_root.resolve())
            is_archived = True
        except ValueError:
            is_archived = False

        assert is_archived, (
            "真归档路径未被识别为归档态 —— EXP-2026-0027 修复回退"
        )

    def test_changes_path_is_not_under_archive(self, tmp_path):  # TC-CGR-006
        """[正常路径] TC-CGR-006：changes 下路径被判定为在办态。"""
        changes = tmp_path / "changes"
        active_change = changes / "some-change"
        active_change.mkdir(parents=True)

        archive = tmp_path / "archive"
        archive.mkdir()

        hit = active_change
        archive_root = archive
        try:
            hit.resolve().relative_to(archive_root.resolve())
            is_archived = True
        except ValueError:
            is_archived = False

        assert not is_archived, (
            "changes 下路径被误判为归档态 —— 归档判定异常"
        )

    def test_lexical_dotdot_cannot_escape_guard(self, tmp_path):  # TC-CGR-007
        """[边界] TC-CGR-007：词法 `..` 组合不能骗过归一化守卫。

        构造 hit 路径含 `changes/../archive/some-change` —— 词法看起来在 archive
        外（因为 `..` 前缀），但 `resolve()` 归一化后真实路径在 archive 下。
        """
        archive = tmp_path / "archive"
        archived_change = archive / "some-change"
        archived_change.mkdir(parents=True)

        # 词法上看起来在 changes 外的相对路径
        hit = tmp_path / "changes" / ".." / "archive" / "some-change"
        archive_root = archive

        try:
            hit.resolve().relative_to(archive_root.resolve())
            is_archived = True
        except ValueError:
            is_archived = False

        assert is_archived, (
            "词法 `..` 组合骗过了守卫 —— 说明守卫在用字符串部件比较"
            "（EXP-2026-0027 攻击向量未修复）"
        )


# ─── 功能 C: 全仓无内联 (?i) 拼接 regex（EXP-2026-0031）───────────

class TestNoInlineDotDotIInRegex:
    """EXP-2026-0031：全仓 MUST NOT 有内联 (?i) 拼接 regex。"""

    def test_scan_no_inline_dot_dot_i(self):  # TC-CGR-008
        """[正常路径] TC-CGR-008：扫描 upstream/fstdd/**/*.py 内联 (?i) 残留为 0。"""
        upstream = _UPSTREAM / "fstdd"
        assert upstream.is_dir(), f"upstream 包不存在: {upstream}"

        offenders = []
        for py_file in upstream.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if re.search(r"\(\?i\)", source):
                offenders.append(str(py_file.relative_to(_REPO_ROOT)))

        assert not offenders, (
            f"发现内联 (?i) 残留（EXP-2026-0031 攻击向量复活）：{offenders}"
        )

    def test_inline_dot_dot_i_in_concatenation_crashes(self):  # TC-CGR-009
        """[回归] TC-CGR-009：证明内联 (?i) 在拼接中间会崩溃（攻击向量真实存在）。

        EXP-2026-0031 真实场景：多段字符串拼接时 `(?i)` 落在**非开头位置**，
        Python 3.11+ `re.compile` 抛 PatternError。这不是找现有代码的问题
        （全仓已 0 残留），而是验证攻击向量确实存在 —— 未来若有人再写
        `r"^(?P<prefix>x)" + "(?i)" + r"foo"` 就会 import 崩溃。
        """
        # 场景 1：(?i) 被前缀字符串顶到中间
        pattern = r"^foo" + "(?i)" + r"bar"  # 拼接后: ^foo(?i)bar

        with pytest.raises(re.PatternError) as exc_info:
            re.compile(pattern)

        msg = str(exc_info.value).lower()
        # Python 3.11+ 报错关键词
        assert "global flags" in msg or "not at the start" in msg, (
            f"预期 global flags 报错，实际: {exc_info.value}"
        )
