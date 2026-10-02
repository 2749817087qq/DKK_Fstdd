# -*- coding: utf-8 -*-
"""repo-home —— 法定源 = **工作区内的** `stdd-repo`（canonical spec `canonical-in-workspace`）。

前身是 `test_migrate_to_d_drive.py`，断言「整体迁移到 `D:/tools/FSTDD`」。
2026-09-29 路径口径定稿：该迁移**从未在本机落地**（实测 `D:\\tools` 不存在），
仓库实际位于 `E:\\FSTDD\\stdd-repo` ⇒ 按 SC-001 / SC-009 的通式，法定源 =
**工作区内的 `stdd-repo`**，本机即 `E:/FSTDD/stdd-repo`。

> 为什么整篇改判而不是删：原文件守的是「资产完整、路径自洽、skill 指向法定源」，
> 这些**不变式仍然有效**，作废的只是「工作区位于 D 盘」这一具体假设。
> 删掉它等于丢掉防线；改判它只需把「写死的 D 盘」换成**自定位的工作区**。

设计要点
--------
1. **全部自定位，不写死盘符**：`HOME = 仓库上一级`，随仓库搬到哪都成立。
   写死盘符正是本次修复的对象 —— 它让 13 项断言在换盘后恒红且误导排查。
2. **完整性证据用树对象 / 哈希，不用文件数**：两个目录都在持续产生工作文件
   （日志、记忆、裸库 pack），任何一次运行都会让计数变化 ⇒ 文件数不是合适判据。
3. **只读**：不写入 `D:/Programs/DKK_Fstdd` 与 `~/.workbuddy-ai/Fstdd`。
4. skill 目录由 `tools/_skill_install_env.py`（唯一事实源）解析，不在此处另立一份。
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent
HOME = REPO.parent                     # 工作区（本机 = E:/FSTDD）；自定位，不写死
DRIVE = HOME.drive + "/"               # 本机 = "E:/"

# 历史位置（可能不存在 —— 不存在即 skip，不构成失败）
C_WORKSPACE = Path(r"C:\Users\Administrator\WorkBuddy AI\2026-09-14-18-36-54")
C_REPO = C_WORKSPACE / "stdd-repo"
OTHER_OUTSIDE = Path.home() / ".workbuddy-ai" / "Fstdd"
D_DEBUG_COPY = Path("D:/Programs/DKK_Fstdd")
D_DRIVE_GOAL = Path("D:/tools/FSTDD")  # 未落地的迁移目标（仅用于口径取证）

sys.path.insert(0, str(REPO / "tools"))
from _skill_install_env import resolve_skill_dir  # noqa: E402

SKILL_DIR, SKILL_DIR_WHY = resolve_skill_dir()

# 本仓库**管理**的 skill。判据只对本仓库安装的这 7 个生效 ——
# 机器上还有别的 `fstdd*` / `stdd*` skill（他人或历史产物，如
# `fstdd-experience-archive`），它们的路径不归本仓库负责，混进来会造成
# 「本仓库改一处、他人 skill 报红」的假失败。
MANAGED_SKILLS = {
    "fstdd", "fstdd-understand", "fstdd-spec", "fstdd-build",
    "fstdd-deliver", "fstdd-upgrade", "fstdd-fin",
}


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip()


def _content_fingerprint(repo: Path) -> str:
    """对**跟踪文件**逐个算 git blob 哈希，返回整体指纹（内容逐字节一致的证据）。"""
    files = _git(repo, "ls-files").splitlines()
    h = hashlib.sha256()
    for f in sorted(files):
        blob = _git(repo, "hash-object", f)
        h.update(("%s %s\n" % (blob, f)).encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# A. 工作区完整性
# ---------------------------------------------------------------------------

class TestAWorkspaceIntegrity:
    """SC-001 —— 法定源位于工作区内，开发产物集中在工作区。"""

    def test_a1_home_contains_repo(self):
        assert (HOME / "stdd-repo").is_dir(), (
            "工作区 %s 下没有 stdd-repo —— 法定源必须位于工作区内" % HOME)
        assert (HOME / "stdd-repo").resolve() == REPO.resolve(), (
            "被测仓库 %s 不在工作区 %s 内" % (REPO, HOME))

    def test_a2_structure_mirrors(self):
        """工作区结构：仓库 + 备份 + 记忆 + 推送脚本。"""
        for rel in ("stdd-repo", "backups", ".workbuddy-ai", "push_stdd_repo.sh"):
            assert (HOME / rel).exists(), "工作区缺少 %s" % rel

    def test_a3_key_assets_present(self):
        """关键资产必须都在工作区内（证据用树对象，见 test_a4，不用文件数）。"""
        checks = [
            "stdd-repo/.fstdd/archive",
            "stdd-repo/.fstdd/experiences",
            "stdd-repo/.fstdd/specs",
            "stdd-repo/.fstdd/changes",
            "stdd-repo/tools",
            "stdd-repo/upstream",
            "stdd-repo/docs",
            "backups",
            ".workbuddy-ai/memory",
        ]
        missing = [c for c in checks if not (HOME / c).exists()]
        assert missing == [], "工作区缺少关键资产: %s" % missing

        n_arch = len([p for p in (REPO / ".fstdd/archive").iterdir()])
        assert n_arch >= 4, "仓库归档 change 仅 %d 个（应 >=4）" % n_arch

    def test_a4_archive_captured_state(self):
        """历史 C 盘工作区的 HEAD 必须仍存在于本仓库（资产未在搬迁中丢失）。"""
        if not C_REPO.exists():
            pytest.skip("历史 C 盘工作区不存在（本机已不再是该布局）")
        c_head = _git(C_REPO, "rev-parse", "HEAD")
        assert c_head, "无法读取 C 盘 HEAD"
        r = subprocess.run(["git", "cat-file", "-e", c_head], cwd=str(REPO),
                           capture_output=True)
        assert r.returncode == 0, "本仓库不含 C 盘 HEAD 提交 %s" % c_head[:8]
        assert _git(C_REPO, "rev-parse", "%s^{tree}" % c_head) == \
            _git(REPO, "rev-parse", "%s^{tree}" % c_head), "迁移时刻的树不一致"

    def test_a5_git_history_present(self):
        if not C_REPO.exists():
            pytest.skip("历史 C 盘工作区不存在")
        assert _git(C_REPO, "rev-parse", "fstdd-v1.0.0^{commit}") == \
            _git(REPO, "rev-parse", "fstdd-v1.0.0^{commit}")
        assert int(_git(REPO, "rev-list", "--count", "HEAD")) >= 60

    def test_a6_no_stray_untracked_files(self):
        """除 `.fstdd/changes/` 下的在办 change 外，不应有**未跟踪**垃圾文件。

        > 判据限定「未跟踪」（`??`）而非「任何改动」：在办 change 期间跟踪文件
        > 本来就该处于已修改状态，把「已修改」也算脏会让本用例只在两次 change
        > 之间的瞬间才绿。真正要防的是**遗留垃圾**（临时脚本 / 备份目录被丢在仓库里）。
        """
        change_root = ".fstdd/changes/"
        loose = [l for l in _git(REPO, "status", "--short").splitlines()
                 if l.startswith("??") and change_root not in l]
        assert loose == [], "仓库有未跟踪的遗留项: %s" % loose


# ---------------------------------------------------------------------------
# B. 环境自洽
# ---------------------------------------------------------------------------

class TestBRepoEnvironment:
    """SC-001 / SC-004 的静态部分。"""

    def test_b1_repo_has_tag(self):
        assert "fstdd-v1.0.0" in _git(REPO, "tag", "-l")

    def test_b2_remotes_have_no_c_path(self):
        """remote 不得指向 C 盘工作区（资产已不在那里）。"""
        out = _git(REPO, "remote", "-v")
        bad = [l for l in out.splitlines() if "C:/" in l or "C:\\" in l]
        assert bad == [], "仓库的 remote 仍指向 C 盘: %s" % bad

    def test_b3_origin_is_github(self):
        out = _git(REPO, "remote", "get-url", "origin")
        assert "github.com" in out, "origin 应为 GitHub（上传目标）"

    def test_b4_local_bare_repo_under_home(self):
        """本地裸库应在工作区内，且 `local` remote 指向它。"""
        bare = HOME / "backups" / "stdd-repo.git"
        assert bare.exists(), "工作区缺少本地裸库 backups/stdd-repo.git"
        url = _git(REPO, "remote", "get-url", "local").replace("\\", "/")
        assert HOME.as_posix().lower() in url.lower(), (
            "local remote 应指向工作区内裸库，实际: %s" % url)


# ---------------------------------------------------------------------------
# C. skill 路径
# ---------------------------------------------------------------------------

class TestCSkillPaths:
    """SC-003 —— skill 内固化路径必须指向工作区内的法定源。"""

    def _skills(self) -> list[Path]:
        if not SKILL_DIR.exists():
            return []
        return sorted(p for p in SKILL_DIR.glob("fstdd*/SKILL.md")
                      if p.parent.name in MANAGED_SKILLS)

    def test_c1_no_project_path_outside_home(self):
        """skill 里凡**项目路径**（含 stdd-repo / FSTDD），都必须在工作区盘上。

        ⚠️ 判据不能写成「无 C: 路径」—— skill 里解释器本身可能就在 C 盘，
        那是**工具**不是我们的资产。也不能写成「不含某个具体子串」——
        那样换个目录名就漏过。正确判据：凡含 `stdd-repo` / `FSTDD` 的绝对路径，
        必须以**工作区所在盘**（本机 `E:/`）开头。
        """
        skills = self._skills()
        if not skills:
            pytest.skip("未安装 skill")
        bad = []
        for p in skills:
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'"([A-Za-z]:[\\/][^"]*)"', text):
                path = m.group(1).replace("\\", "/")
                if ("stdd-repo" in path or "FSTDD" in path) and not path.startswith(DRIVE):
                    bad.append("%s -> %s" % (p.parent.name, path))
        assert bad == [], "skill 中存在工作区之外的项目路径:\n  " + "\n  ".join(bad)

    def test_c2_skills_point_to_home_repo(self):
        """至少 6 个 skill 应指向工作区内的 stdd-repo（fstdd-fin 例外）。"""
        skills = self._skills()
        if not skills:
            pytest.skip("未安装 skill")
        want = (HOME / "stdd-repo").as_posix()
        ok = [p.parent.name for p in skills
              if want in p.read_text(encoding="utf-8", errors="replace")]
        assert len(ok) >= 6, "指向 %s 的 skill 仅 %d 个: %s" % (want, len(ok), ok)


# ---------------------------------------------------------------------------
# D. 文档与记忆
# ---------------------------------------------------------------------------

class TestDDocsAndMemory:
    """SC-009 / SC-010 —— 文档与记忆必须反映「法定源 = 工作区内 stdd-repo」。"""

    def test_d1_docs_point_to_home(self):
        doc = (REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert HOME.as_posix() in doc, "文档未写明本机工作区 %s" % HOME.as_posix()
        assert "法定源" in doc and (HOME / "stdd-repo").as_posix() in doc, (
            "文档未把法定源写为工作区内的 stdd-repo")

    def test_d2_docs_mark_d_drive_abandoned(self):
        """未落地的 D 盘迁移目标必须被显式标注为弃用，且既有告警不得被删。"""
        doc = (REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert "D:/tools/FSTDD" in doc and "未落地" in doc, (
            "文档未显式标注 D 盘迁移目标未落地 —— 后来者会再次误用")
        assert "DKK_Fstdd" in doc and "不要动" in doc, "D 盘调试副本的告警被删了"
        assert "上传目标" in doc, "GitHub 是上传目标的说明被删了"

    def test_d3_memory_points_to_home(self):
        mem_file = HOME / ".workbuddy-ai" / "memory" / "MEMORY.md"
        if not mem_file.exists():
            pytest.skip("工作区记忆文件不存在")
        mem = mem_file.read_text(encoding="utf-8", errors="replace")
        assert HOME.as_posix() in mem, "记忆未写明工作区 %s" % HOME.as_posix()
        assert "DKK_Fstdd" in mem and "不要动" in mem, "记忆里的调试副本告警被删了"

    def test_d4_superseded_d_drive_spec_retired(self):
        """被取代的 spec `d-drive-home` 必须已从现行 spec 集移除（2026-09-29 retire）。

        它的 SC-008 / SC-009 仍要求「法定源 SHALL 写为 `D:/tools/FSTDD/stdd-repo`」——
        与该迁移从未落地的事实相反，且与继任 spec `canonical-in-workspace` 冲突。
        留在现行 `.fstdd/specs/` 会被 `fstdd index` 当作活能力（`index.py` 按 spec 目录建索引）。
        历史原文留档于 archive，故不丢证据。
        """
        assert not (REPO / ".fstdd/specs/d-drive-home").exists(), (
            "d-drive-home 仍在现行 specs/ —— 它守着一个从未落地的迁移")
        assert (REPO / ".fstdd/specs/canonical-in-workspace/spec.md").exists(), (
            "继任 spec canonical-in-workspace 丢失")
        assert (REPO / ".fstdd/archive/2026-09-17-migrate-to-d-drive"
                / "specs/d-drive-home/spec.md").exists(), (
            "被 retire 的 spec 历史原文应留档于 archive，不得丢证据")


# ---------------------------------------------------------------------------
# E. 不误伤其它位置
# ---------------------------------------------------------------------------

class TestEOtherLocations:
    """SC-002 —— 本变更不删除任何位置。"""

    def test_e1_d_debug_copy_untouched(self):
        if not D_DEBUG_COPY.exists():
            pytest.skip("D 盘调试副本不存在（本机环境差异）")
        assert (D_DEBUG_COPY / "upstream").exists(), "D 盘调试副本结构异常"

    def test_e2_archived_outside_copy_still_present(self):
        if not OTHER_OUTSIDE.exists():
            pytest.skip("区外副本不存在（可能已被归档处置）")
        assert (OTHER_OUTSIDE / "upstream").exists()

    def test_e3_d_drive_goal_still_not_landed(self):
        """口径哨兵：D 盘迁移目标若**忽然存在**，说明工作区布局已变，
        本文档与测试的「工作区」前提需要重新定稿 —— 宁可红，不要静默漂移。"""
        if D_DRIVE_GOAL.exists():
            pytest.fail(
                "检测到 %s 已存在 —— 工作区布局可能已变更；"
                "请重新核定路径口径（docs/WORKBUDDY_INSTALL_NOTES.md §0）" % D_DRIVE_GOAL)
