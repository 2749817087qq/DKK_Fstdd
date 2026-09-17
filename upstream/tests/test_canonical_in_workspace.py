# -*- coding: utf-8 -*-
"""canonical-in-workspace —— 法定源收进工作区。

对应 test-plan.md 的 TC-CIW-001 ~ TC-CIW-014（可自动化部分）。

设计要点
--------
1. **断言真实产物**：直接读脚本源码、文档、已安装 skill、归档目录，不构造假输入。
2. **只读**：对 `D:/Programs/DKK_Fstdd` 与区外副本只做存在性/内容检查，不写入。
3. 与 `D:/Programs/DKK_Fstdd` 无关的断言不应因它不存在而失败。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent
WORKSPACE = REPO.parent
BACKUPS = WORKSPACE / "backups"
OUTSIDE = Path.home() / ".workbuddy-ai" / "Fstdd"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# A. 校验脚本的解析顺序：自定位优先
# ---------------------------------------------------------------------------

class TestAResolutionOrder:
    """TC-CIW-003 / TC-CIW-004 / TC-CIW-005。

    原则是「用**安装源自己的** verify 去校验」。安装源现在是**工作区仓库**，
    而脚本就在工作区仓库里 → 自定位即命中安装源。
    """

    def test_a1_self_location_before_outside_copy(self):
        """自定位必须排在区外副本之前。"""
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        i_here = src.find("here,", src.find("cands += ["))
        i_outside = src.find('".workbuddy-ai" / "Fstdd" / "tools"')
        assert i_here != -1 and i_outside != -1
        assert i_here < i_outside, (
            "自定位必须优先 —— 安装源是工作区仓库，而脚本就在其中；"
            "把区外副本放首位会让校验去比对另一份陈旧副本"
        )

    def test_a2_fstdd_inst_dir_still_wins(self):
        """`FSTDD_INST_DIR` 显式覆盖仍须最高优先级。"""
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        i_env = src.find('if os.environ.get("FSTDD_INST_DIR")')
        i_here = src.find("here,", src.find("cands += ["))
        assert 0 <= i_env < i_here

    def test_a3_d_drive_is_last_resort_only(self):
        """D 盘调试副本只作兜底。"""
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        i_d = src.find('Path("D:/Programs/DKK_Fstdd/tools")')
        i_here = src.find("here,", src.find("cands += ["))
        assert i_d != -1 and i_here < i_d

    def test_a4_verify_rename_same_order(self):
        """`verify_rename.py` 必须同顺序。"""
        src = (REPO / "tools/verify_rename.py").read_text(encoding="utf-8")
        i_here = src.find("_here,", src.find("_cands += ["))
        i_outside = src.find('".workbuddy-ai" / "Fstdd" / "tools"')
        assert i_here != -1 and i_outside != -1 and i_here < i_outside

    def test_a5_resolves_to_workspace(self):
        """实际解析结果必须落到工作区仓库的 tools/。"""
        m = _load("_vss_ciw", "tools/verify_skill_standards.py")
        assert m.INSTALLED_TOOLS == (REPO / "tools").resolve(), (
            "INSTALLED_TOOLS 应自定位到工作区仓库，实际: %s" % m.INSTALLED_TOOLS
        )


# ---------------------------------------------------------------------------
# B. 文档反映新架构
# ---------------------------------------------------------------------------

class TestBDocs:
    """TC-CIW-012。"""

    def _doc(self) -> str:
        return (REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")

    def test_b1_canonical_is_workspace(self):
        doc = self._doc()
        assert "**法定源**" in doc
        assert "stdd-repo" in doc
        # 不得再把区外副本描述为法定源
        assert "| `~/.workbuddy-ai/Fstdd` | **法定源**" not in doc

    def test_b2_outside_copy_marked_archived(self):
        """区外副本必须被标注为归档/非权威。

        > 2026-09-17 迁移到 D 盘后，文档措辞由「已归档 + canonical-archived 路径」
        > 改为「更早一轮的归档副本」。断言改为查**实质**（非权威 + 归档），
        > 不绑定具体措辞 —— 否则文档每改一次措辞就要改一次测试。
        """
        doc = self._doc()
        assert "归档" in doc, "文档未说明区外副本已归档"
        assert "不是法定源" in doc or "不再是法定源" in doc, "未说明它已非权威"

    def test_b3_github_still_upload_target(self):
        doc = self._doc()
        assert "上传目标" in doc
        assert "不是源" in doc or "不是权威" in doc

    def test_b4_d_drive_warning_kept(self):
        doc = self._doc()
        assert "另一程序的调试副本" in doc
        assert "不要动" in doc


# ---------------------------------------------------------------------------
# C. 归档完整性（只读检查）
# ---------------------------------------------------------------------------

class TestCArchive:
    """TC-CIW-008 / TC-CIW-009。"""

    def _archive(self) -> Path | None:
        if not BACKUPS.exists():
            return None
        cands = sorted(BACKUPS.glob("canonical-archived-*/Fstdd"))
        return cands[-1] if cands else None

    def test_c1_archive_exists(self):
        a = self._archive()
        assert a is not None, (
            "未找到 backups/canonical-archived-*/Fstdd —— 区外副本必须已归档"
        )

    def test_c2_archive_file_count_matches_source(self):
        a = self._archive()
        if a is None or not OUTSIDE.exists():
            pytest.skip("归档或原目录不存在（可能已被清理）")
        n_src = sum(1 for p in OUTSIDE.rglob("*") if p.is_file())
        n_dst = sum(1 for p in a.rglob("*") if p.is_file())
        assert n_dst == n_src, "归档文件数 %d != 源文件数 %d" % (n_dst, n_src)

    def test_c3_source_not_deleted(self):
        """「归档不删」—— 原目录必须仍在。"""
        assert OUTSIDE.exists(), "区外副本被删除了 —— 决定是「归档不删」"

    def test_c4_d_drive_untouched(self):
        """D 盘调试副本仍在（本变更全程只读）。"""
        d = Path("D:/Programs/DKK_Fstdd")
        if not d.exists():
            pytest.skip("D 盘调试副本不存在（本机环境差异）")
        assert (d / "upstream").exists(), "D 盘调试副本结构异常 —— 本变更不得改动它"


# ---------------------------------------------------------------------------
# D. 已安装 skill 的路径
# ---------------------------------------------------------------------------

class TestDInstalledSkill:
    """TC-CIW-010 —— skill 路径指向工作区。"""

    SKILL_DIR = Path.home() / ".workbuddy" / "skills"

    def _skills(self) -> list[Path]:
        if not self.SKILL_DIR.exists():
            return []
        return sorted(self.SKILL_DIR.glob("fstdd*/SKILL.md"))

    def test_d1_no_outside_path(self):
        skills = self._skills()
        if not skills:
            pytest.skip("未安装 skill（本机环境差异）")
        bad = [p.parent.name for p in skills
               if "workbuddy-ai/Fstdd" in p.read_text(encoding="utf-8", errors="replace")]
        assert bad == [], "以下 skill 仍指向区外副本: %s" % bad

    def test_d2_points_to_workspace(self):
        skills = self._skills()
        if not skills:
            pytest.skip("未安装 skill（本机环境差异）")
        # 至少阶段 skill 应含工作区路径（fstdd-fin 是领域层，可能不引用 upstream）
        with_ws = [p.parent.name for p in skills
                   if "stdd-repo" in p.read_text(encoding="utf-8", errors="replace")]
        assert len(with_ws) >= 5, (
            "指向工作区仓库的 skill 仅 %d 个，偏少: %s" % (len(with_ws), with_ws)
        )


# ---------------------------------------------------------------------------
# E. rename 检查不得被运行产物干扰
# ---------------------------------------------------------------------------

class TestERenameExcludesRuntimeArtifacts:
    """`inbox/` 是 gitignored 运行产物，其中含**历史经验文档**（合法提到旧名）。

    实测：拉回测试数据后 TC-RENAME-002 报「残留 20 处」，全部来自 `inbox/raw/`。
    """

    def test_e1_inbox_is_excluded(self):
        src = (REPO / "tools/verify_rename.py").read_text(encoding="utf-8")
        m = re.search(r"EXCLUDE_DIRS\s*=\s*\{([^}]*)\}", src, re.S)
        assert m is not None, "未找到 EXCLUDE_DIRS"
        dirs = set(re.findall(r'"([^"]+)"', m.group(1)))
        for d in ("inbox", "experiences", "backups"):
            assert d in dirs, "%s 应被排除（gitignored 运行产物）" % d

    def test_e2_runtime_artifacts_are_gitignored(self):
        """这些目录确实被 gitignore —— 佐证「不该参与源码检查」。"""
        gi = (REPO / ".gitignore").read_text(encoding="utf-8")
        for d in ("inbox/", "experiences/"):
            assert d in gi, "%s 应被 gitignore" % d
