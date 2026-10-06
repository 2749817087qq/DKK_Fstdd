"""
test_release_manifest_accuracy.py — 发布清单准确性与版本断言去硬编码
覆盖 TC-RTA-001 / TC-RTA-003 / TC-RTA-005（capability: release-tooling-accuracy）
纯静态，不依赖 install / 网络
"""
import re
from pathlib import Path

import pytest

from conftest import repo_root, read_file


ROOT = repo_root()
MANIFEST = ROOT / ".fstdd" / "standards" / "release-and-docs.md"
VERSION_YAML = ROOT / ".fstdd" / "version.yaml"
PROJECT_YAML = ROOT / ".fstdd" / "config.d" / "project.yaml"
TESTS_DIR = ROOT / "tests"
INSTALL_SMOKE = TESTS_DIR / "test_install_smoke.py"


def _normalize(text: str) -> str:
    """去掉 markdown 强调符与全部空白，便于对「等义表述」做判定。"""
    return re.sub(r"[\s*`]+", "", text)


# 「仓库根没有 tests/」类失真表述的**模式**（作用于归一化文本）。
#
# ⚠️ 首版用固定子串清单，被评审证伪两点，故改为模式 + 上下文豁免：
#   · 漏判：`仓库根目录下没有 tests 目录`、`仓库根下不存在任何 tests 目录` 都不在清单里；
#   · 误报：`旧清单曾误称『仓库根没有 tests/』，本版已更正` 会被误杀。
FALSE_CLAIM_RE = re.compile(
    r"(?:仓库根|根目录)[^。；]{0,8}?(?:没有|无|不存在|未有)[^。；]{0,6}tests"
)
# 出现这些「更正语境」标记时，视为在**引述并纠正**旧表述，不算失真。
CORRECTION_MARKERS = (
    "已更正", "已修正", "已修复", "误称", "原文", "修复前", "旧清单", "旧版",
    "此前", "不再", "曾经", "历史", "反面教材",
)
_CORRECTION_WINDOW = 40


def _false_claims(text: str) -> list:
    """返回归一化文本中「未被更正语境豁免」的失真表述片段。"""
    norm = _normalize(text)
    hits = []
    for m in FALSE_CLAIM_RE.finditer(norm):
        window = norm[max(0, m.start() - _CORRECTION_WINDOW): m.end() + _CORRECTION_WINDOW]
        if any(marker in window for marker in CORRECTION_MARKERS):
            continue
        hits.append(m.group(0))
    return hits


# ============================================================
# TC-RTA-001 — 发布清单不含失真表述，且全量命令覆盖两处 tests
# spec: release-tooling-accuracy / SC-001
# ============================================================
def test_tc_rta_001_manifest_has_no_false_root_tests_claim():
    content = read_file(MANIFEST)
    assert content, f"发布清单不可读或为空: {MANIFEST}"
    hits = _false_claims(content)
    n_py = len(list(TESTS_DIR.glob("*.py")))
    assert not hits, (
        f"发布清单仍含「仓库根没有 tests/」类失真表述: {hits}；"
        f"仓库根 tests/ 实际存在（{n_py} 个 *.py）"
    )


def test_tc_rta_001b_manifest_reflects_root_tests_dir():
    content = read_file(MANIFEST)
    norm = _normalize(content)
    assert "仓库根tests" in norm, "发布清单未反映仓库根 tests/ 的存在"


def test_tc_rta_001c_full_test_command_covers_both_dirs():
    content = read_file(MANIFEST)
    lines = [l for l in content.splitlines() if "pytest" in l]
    assert lines, "发布清单未给出 pytest 全量测试命令"
    joined = " ".join(lines)
    assert "upstream/tests" in joined, "全量测试命令未覆盖 upstream/tests/"
    assert re.search(r"(?:^|[\s`])tests(?:[\s`]|$)", joined), (
        "全量测试命令未覆盖仓库根 tests/（清单须同时跑两处测试目录）"
    )


def test_tc_rta_001d_full_test_command_has_no_hardcoded_case_count():
    """清单不得写死用例数（数字必然漂移，见 ADJ-003：「851 用例」已过期）。

    同一行曾同时含「仓库根没有 tests/」与过期的「851 用例」。
    """
    content = read_file(MANIFEST)
    for line in content.splitlines():
        if "pytest" not in line:
            continue
        m = re.search(r"\d{2,}\s*用例", line)
        assert not m, (
            f"全量测试命令行写死了用例数（会随版本漂移）：{m.group(0)!r} —— {line.strip()}"
        )


def test_tc_rta_001e_false_claim_detector_is_not_vacuous():
    """自检：失真表述检测器必须真能抓到变体，且对「引述并更正」的语境放行。

    背景：首版用固定子串清单，被独立评审用反例证伪（漏判 + 误报各一）。
    把这两个反例固化为断言 —— 审计工具的假绿（漏判）与假红（误报）都必须被拦住。
    """
    # 必须抓到（含首版漏判的变体）
    for bad in (
        "注意测试在 upstream/tests/，仓库根没有 tests/",
        "仓库根目录下没有 tests 目录",
        "仓库根下不存在任何 tests 目录",
        "根目录无 tests",
    ):
        assert _false_claims(bad), f"未抓到失真表述: {bad!r}"

    # 必须放行（首版误报的「更正语境」）
    for ok in (
        "旧清单曾误称『仓库根没有 tests/』，本版已更正。",
        "修复前写的是「仓库根没有 tests/」，现已改为覆盖两处目录。",
        "反面教材：此前声称仓库根没有 tests/，实为错误。",
    ):
        assert not _false_claims(ok), f"误报（更正语境被当成失真表述）: {ok!r}"

    # 正确表述不得被误判
    assert not _false_claims("仓库根 tests/ 与 upstream/tests/ 都要跑。")


# ============================================================
# TC-RTA-003 — 版本断言动态性（不依赖任何具体版本字面量）
# spec: release-tooling-accuracy / SC-003
# ============================================================
def test_tc_rta_003_version_assertion_is_dynamic(tmp_path):
    from test_finance_content import _assert_versions_consistent

    # 任意合法版本值都应通过（断言不依赖字面量）
    for ver in ("9.9.9", "0.0.1", "3.3.5"):
        v = tmp_path / "version.yaml"
        p = tmp_path / "project.yaml"
        v.write_text(f'fstdd_version: "{ver}"\n', encoding="utf-8")
        p.write_text(f"stdd_version: {ver}\n", encoding="utf-8")
        _assert_versions_consistent(v, p)

    # 两源不一致 → 必须失败，且给出可定位的差异信息
    v.write_text('fstdd_version: "1.2.3"\n', encoding="utf-8")
    p.write_text("stdd_version: 4.5.6\n", encoding="utf-8")
    with pytest.raises(AssertionError) as ei:
        _assert_versions_consistent(v, p)
    msg = str(ei.value)
    assert "1.2.3" in msg and "4.5.6" in msg, f"差异信息不可定位: {msg!r}"


# ============================================================
# TC-RTA-005 — 仓库根 tests/ 不硬编码发行版 tag 字面量
# spec: release-tooling-accuracy / SC-005
# ============================================================
TAG_LITERAL_RE = re.compile(r"fstdd-v\d")


def test_tc_rta_005_no_hardcoded_release_tag_literal():
    offenders = []
    for path in sorted(TESTS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8-sig")
        for lineno, line in enumerate(text.splitlines(), 1):
            if TAG_LITERAL_RE.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "仓库根 tests/ 含硬编码发布 tag 字面量（须从单一事实源派生）:\n"
        + "\n".join(offenders)
    )


def test_tc_rta_005b_install_smoke_expected_tag_matches_version_yaml():
    from test_finance_content import _read_version
    from test_install_smoke import _expected_release_tag

    ver = _read_version(VERSION_YAML, "fstdd_version")
    assert _expected_release_tag() == f"fstdd-v{ver}", (
        f"test_install_smoke 期望 tag 未从 version.yaml 派生（version={ver}）"
    )


def _patch_git(smoke, monkeypatch, describe_out):
    """把 test_install_smoke 的 _run 替换为宿主隔离的假实现（不触网）。"""

    def _fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "fetch"]:
            return 0, "", ""
        if cmd[:2] == ["git", "describe"]:
            return 0, describe_out, ""
        raise AssertionError(f"unexpected cmd: {cmd}")

    monkeypatch.setattr(smoke, "_run", _fake_run)


def test_tc_rta_005c_head_tag_assertion_holds_when_tag_matches(monkeypatch):
    """模拟 git 可达：HEAD tag 与 version.yaml 声明一致 → 断言成立（不依赖真实网络）。"""
    import test_install_smoke as smoke

    expected = smoke._expected_release_tag()
    _patch_git(smoke, monkeypatch, expected + "\n")
    smoke.test_L0_01_git_pull_to_tag()  # 不抛即通过


def test_tc_rta_005d_head_tag_assertion_rejects_mismatch(monkeypatch):
    """反向：HEAD tag 与声明不一致 → 必须失败（证明断言非空转）。"""
    import test_install_smoke as smoke

    _patch_git(smoke, monkeypatch, "fstdd-v" + "0.0.1\n")
    with pytest.raises(AssertionError):
        smoke.test_L0_01_git_pull_to_tag()
