"""
test_version_consistency.py — 版本声明面同号锚定（5 TC）

立规依据：v3.4.0 发布时 `pyproject.toml` 漏改（停在 3.3.9），而
`.fstdd/version.yaml` / `.fstdd/config.d/project.yaml` / `CHANGELOG.md`
三处均为 3.4.0。既有 `test_L1_11_version_yaml_fstdd_version` 只比对
version.yaml 与 project.yaml **两处**，pyproject.toml 不在判据内 ⇒ 漏检。

本文件把「四处声明面同号」收为单一判据，并**自带负向自检**
（造不一致数据验证判据会红），防止判据本身退化成恒真。

TC-VCON-001  pyproject.toml:version == project.yaml:stdd_version
TC-VCON-002  version.yaml:fstdd_version == project.yaml:stdd_version
TC-VCON-003  CHANGELOG.md 存在 [<stdd_version>] 段
TC-VCON-004  pyproject.toml 版本注释不含过期版本字面量
TC-VCON-005  负向自检：任一声明面不一致时判据必须报错
"""
import re
from pathlib import Path

import pytest

from conftest import repo_root, read_file


ROOT = repo_root()
PROJECT_YAML = ROOT / ".fstdd" / "config.d" / "project.yaml"
VERSION_YAML = ROOT / ".fstdd" / "version.yaml"
PYPROJECT_TOML = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"


# ============================================================
# 解析器（纯函数，可被负向自检复用）
# ============================================================
def parse_project_version(text: str) -> str:
    """从 project.yaml 文本取 stdd_version（唯一事实源）。"""
    m = re.search(r'^stdd_version:\s*["\']?([\d.]+)["\']?', text, re.MULTILINE)
    assert m, "project.yaml 缺 stdd_version（版本唯一事实源不可缺）"
    return m.group(1)


def parse_version_yaml_version(text: str) -> str:
    """从 version.yaml 文本取 fstdd_version。"""
    m = re.search(r'^fstdd_version:\s*["\']?([\d.]+)["\']?', text, re.MULTILINE)
    assert m, "version.yaml 缺 fstdd_version"
    return m.group(1)


def parse_pyproject_version(text: str) -> str:
    """从 pyproject.toml 文本取 [project] 段的 version。

    有 `[project]` 段头时只在段内取（避免命中 [tool.*] 的无关 version 键）；
    无段头时回退全文取 —— 供负向自检传简化文本使用。

    注意：段头正则用 `[ \\t]*$` 而非 `\\s*$` —— `\\s` 含 `\\n`，会跨行吞掉
    后续内容导致段边界算错（本文件 TC-VCON-005 首次实现即踩此坑）。
    """
    header = re.search(r'^\[project\][ \t]*$', text, re.MULTILINE)
    if header is None:
        section = text
    else:
        rest = text[header.end():]
        nxt = re.search(r'^\[', rest, re.MULTILINE)
        section = rest[: nxt.start()] if nxt else rest

    m = re.search(r'^version\s*=\s*["\']([\d.]+)["\']', section, re.MULTILINE)
    assert m, "pyproject.toml [project] 段缺 version"
    return m.group(1)


def parse_changelog_versions(text: str) -> list:
    """从 CHANGELOG 文本取所有二级标题里的版本号。"""
    return re.findall(r'^##\s*\[(\d+\.\d+\.\d+)\]', text, re.MULTILINE)


def find_stale_comment_versions(pyproject_text: str, actual: str) -> list:
    """找出 pyproject.toml 版本注释里写死的、与 actual 不符的版本字面量。

    只扫 `version = ...` 上方紧邻的注释块（R 轴声明处），
    不扫其他无关注释，避免误伤。
    """
    lines = pyproject_text.splitlines()
    stale = []
    for idx, line in enumerate(lines):
        if re.match(r'^version\s*=', line):
            # 向上收集紧邻的注释行
            j = idx - 1
            while j >= 0 and lines[j].lstrip().startswith("#"):
                for found in re.findall(r'\d+\.\d+\.\d+', lines[j]):
                    if found != actual:
                        stale.append((j + 1, found, lines[j].strip()))
                j -= 1
            break
    return stale


def assert_all_surfaces_agree(project_text, version_text, pyproject_text, changelog_text) -> str:
    """四处声明面同号断言。返回唯一事实源版本号。

    唯一事实源 = project.yaml:stdd_version（见 .fstdd/standards/release-and-docs.md §一）。
    """
    canonical = parse_project_version(project_text)

    v_version = parse_version_yaml_version(version_text)
    assert v_version == canonical, (
        f"version.yaml:fstdd_version={v_version} != "
        f"project.yaml:stdd_version={canonical}"
    )

    p_version = parse_pyproject_version(pyproject_text)
    assert p_version == canonical, (
        f"pyproject.toml:version={p_version} != "
        f"project.yaml:stdd_version={canonical}"
    )

    cl_versions = parse_changelog_versions(changelog_text)
    assert canonical in cl_versions, (
        f"CHANGELOG.md 缺 [{canonical}] 段（已有：{cl_versions[:5]}）"
    )

    stale = find_stale_comment_versions(pyproject_text, canonical)
    assert not stale, (
        f"pyproject.toml 版本注释含过期版本字面量（应全部为 {canonical}）：{stale}"
    )

    return canonical


# ============================================================
# TC-VCON-001..004：真实仓库四处同号
# ============================================================
def test_TC_VCON_001_pyproject_matches_project_yaml():
    """TC-VCON-001：pyproject.toml 的 version 与 project.yaml 的 stdd_version 同号。"""
    canonical = parse_project_version(read_file(PROJECT_YAML))
    assert parse_pyproject_version(read_file(PYPROJECT_TOML)) == canonical


def test_TC_VCON_002_version_yaml_matches_project_yaml():
    """TC-VCON-002：version.yaml 的 fstdd_version 与 project.yaml 的 stdd_version 同号。"""
    canonical = parse_project_version(read_file(PROJECT_YAML))
    assert parse_version_yaml_version(read_file(VERSION_YAML)) == canonical


def test_TC_VCON_003_changelog_has_current_section():
    """TC-VCON-003：CHANGELOG.md 存在当前版本的 [x.y.z] 段。"""
    canonical = parse_project_version(read_file(PROJECT_YAML))
    versions = parse_changelog_versions(read_file(CHANGELOG))
    assert canonical in versions, f"CHANGELOG.md 缺 [{canonical}] 段，已有 {versions[:5]}"


def test_TC_VCON_004_no_stale_version_comment():
    """TC-VCON-004：pyproject.toml 的 R 轴版本注释不含过期版本字面量。

    缺陷原型：v3.4.0 发布后该注释仍写「（当前 3.3.9）」，与 version 键同处一段，
    读的人会误以为版本就是 3.3.9。
    """
    canonical = parse_project_version(read_file(PROJECT_YAML))
    stale = find_stale_comment_versions(read_file(PYPROJECT_TOML), canonical)
    assert not stale, f"版本注释过期（应全为 {canonical}）：{stale}"


# ============================================================
# TC-VCON-005：负向自检（判据本身必须能红）
# ============================================================
@pytest.mark.parametrize(
    "mutate, expect_in_msg",
    [
        ("pyproject", "pyproject.toml:version"),
        ("version_yaml", "version.yaml:fstdd_version"),
        ("changelog", "CHANGELOG.md 缺"),
        ("stale_comment", "过期版本字面量"),
    ],
)
def test_TC_VCON_005_detector_catches_mismatch(mutate, expect_in_msg):
    """TC-VCON-005：四个声明面任一不一致，判据必须报错（不只跑 happy path）。"""
    canonical = "9.9.9"
    project_text = f"stdd_version: '{canonical}'\n"
    version_text = f"fstdd_version: \"{canonical}\"\n"
    pyproject_text = (
        "# R 轴版本，唯一事实源 = project.yaml:stdd_version\n"
        f'version = "{canonical}"\n'
    )
    changelog_text = f"## [{canonical}] - 2026-10-27\n"

    if mutate == "pyproject":
        pyproject_text = pyproject_text.replace(
            f'version = "{canonical}"', 'version = "0.0.1"'
        )
    elif mutate == "version_yaml":
        version_text = 'fstdd_version: "0.0.1"\n'
    elif mutate == "changelog":
        changelog_text = "## [0.0.1] - 2026-10-27\n"
    elif mutate == "stale_comment":
        pyproject_text = (
            "# R 轴版本，须与 version.yaml 一致（当前 0.0.1）\n"
            f'version = "{canonical}"\n'
        )
    else:  # pragma: no cover
        pytest.fail(f"未知变异类型：{mutate}")

    with pytest.raises(AssertionError) as exc:
        assert_all_surfaces_agree(
            project_text, version_text, pyproject_text, changelog_text
        )
    assert expect_in_msg in str(exc.value), (
        f"报错信息未包含 {expect_in_msg!r}，实际：{exc.value}"
    )


def test_TC_VCON_005b_all_agree_passes():
    """TC-VCON-005b：四处全一致时判据必须放行（防判据退化为恒红）。"""
    canonical = "9.9.9"
    assert (
        assert_all_surfaces_agree(
            f"stdd_version: '{canonical}'\n",
            f'fstdd_version: "{canonical}"\n',
            "# R 轴版本，唯一事实源 = project.yaml:stdd_version\n"
            f'version = "{canonical}"\n',
            f"## [{canonical}] - 2026-10-27\n",
        )
        == canonical
    )
