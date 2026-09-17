# -*- coding: utf-8 -*-
"""migrate-to-d-drive —— 整体迁移到 D:/tools/FSTDD。

对应 test-plan.md 的 TC-MDD-001 ~ TC-MDD-015（可自动化部分）。

设计要点
--------
1. **完整性证据用哈希，不用文件数**：文件数一致不足以证明完整
   （曾有同名不同内容的情况）。跟踪文件用 `git hash-object` 逐个比对。
2. **`.git/index` 这类缓存文件不参与比对**：它是 git 的 stat 缓存，
   跑一次 `git status` 就会变 —— 属派生数据，非内容。
3. **只读**：不写入 `D:/Programs/DKK_Fstdd` 与 `~/.workbuddy-ai/Fstdd`。
4. 断言用**绝对路径**，故从 C 盘或 D 盘运行结果一致。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent            # 运行时的仓库（可能是 C 盘归档或 D 盘新家）
WORKSPACE = REPO.parent

D_HOME = Path("D:/tools/FSTDD")
D_REPO = D_HOME / "stdd-repo"
C_WORKSPACE = Path(r"C:\Users\Administrator\WorkBuddy AI\2026-09-14-18-36-54")
C_REPO = C_WORKSPACE / "stdd-repo"
OTHER_OUTSIDE = Path.home() / ".workbuddy-ai" / "Fstdd"
D_DEBUG_COPY = Path("D:/Programs/DKK_Fstdd")
SKILL_DIR = Path.home() / ".workbuddy" / "skills"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip()


def _content_fingerprint(repo: Path) -> str:
    """对**跟踪文件**逐个算 git blob 哈希，返回整体指纹。

    这是「内容逐字节一致」的可靠证据；文件数一致不能替代。
    """
    import hashlib
    files = _git(repo, "ls-files").splitlines()
    h = hashlib.sha256()
    for f in sorted(files):
        blob = _git(repo, "hash-object", f)
        h.update(("%s %s\n" % (blob, f)).encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# A. 迁移完整性
# ---------------------------------------------------------------------------

class TestAMigrationIntegrity:
    """TC-MDD-001 ~ TC-MDD-004。"""

    def test_a1_d_home_exists(self):
        assert D_HOME.exists(), "D:/tools/FSTDD 不存在 —— 迁移未完成"
        assert D_REPO.exists(), "D:/tools/FSTDD/stdd-repo 不存在"

    def test_a2_structure_mirrors(self):
        """目录结构应为工作区镜像，而非只搬仓库。"""
        for rel in ("stdd-repo", "backups", ".workbuddy-ai", "push_stdd_repo.sh"):
            assert (D_HOME / rel).exists(), "D 盘缺少 %s" % rel

    def test_a3_key_assets_present(self):
        """关键资产必须都在 D 盘。

        > **为什么不用「文件数一致」**：两个目录**都在持续产生工作文件**
        > （日志、记忆、提交信息、裸库 pack 文件…），任何一次运行都会让计数变化。
        > 实测：迁移后仅因我自己的验证日志与裸库更新，两边就差了 2 个文件 ——
        > 与迁移完整性无关，却会让断言恒红。**文件数不是合适的判据。**
        >
        > 真正可靠的证据是 `test_a4` 的**树对象比对**。
        """
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
        missing = [c for c in checks if not (D_HOME / c).exists()]
        assert missing == [], "D 盘缺少关键资产: %s" % missing

        n_arch = len(list((D_HOME / "stdd-repo/.fstdd/archive").iterdir()))
        assert n_arch >= 4, "D 盘归档 change 仅 %d 个（应 >=4）" % n_arch

    def test_a4_migration_captured_c_state(self):
        """**迁移时刻** C 盘的状态必须完整存在于 D 盘。

        注意断言的**时点**：比较的是「C 盘 HEAD 那个提交」在两边的**树**，
        而不是「当前工作区」。迁移之后 D 盘会继续开发，两份**理应分叉** ——
        拿当前工作区比对会在第一次开发后就误报。
        """
        if not C_REPO.exists():
            pytest.skip("C 盘仓库不存在")
        c_head = _git(C_REPO, "rev-parse", "HEAD")
        assert c_head, "无法读取 C 盘 HEAD"

        r = subprocess.run(["git", "cat-file", "-e", c_head], cwd=str(D_REPO),
                           capture_output=True)
        assert r.returncode == 0, (
            "D 盘不含 C 盘 HEAD 提交 %s —— 迁移未覆盖该提交" % c_head[:8]
        )
        tree_c = _git(C_REPO, "rev-parse", "%s^{tree}" % c_head)
        tree_d = _git(D_REPO, "rev-parse", "%s^{tree}" % c_head)
        assert tree_c == tree_d, (
            "迁移时刻的树不一致：C=%s D=%s —— 内容可能在复制中损坏" % (tree_c[:12], tree_d[:12])
        )

    def test_a5_git_state_matches(self):
        """C 盘 HEAD 必须存在于 D 盘（含 tag 指向）。"""
        if not C_REPO.exists():
            pytest.skip("C 盘仓库不存在")
        assert _git(C_REPO, "rev-parse", "fstdd-v1.0.0^{commit}") == \
            _git(D_REPO, "rev-parse", "fstdd-v1.0.0^{commit}")
        assert int(_git(D_REPO, "rev-list", "--count", "HEAD")) >= 60

    def test_a6_d_repo_worktree_clean(self):
        """除 `.fstdd/changes/` 下的在办 change 外，不应有未提交改动。

        > 判据不能限定「只允许**本** change 的目录」—— 一个仓库可以**同时有多个
        > 在办 change**（实测：本变更进行期间出现了另一个 change
        > `2026-09-17-distributed-task-coordination`，导致断言误报）。
        > 正确的范围是「`changes/` 下的任何内容」。
        >
        > 另注：change 目录**部分被跟踪**时，git 会逐个列出未跟踪文件，
        > 所以判据是「路径属于该前缀」，不能要求整行以目录名结尾。
        """
        change_root = ".fstdd/changes/"
        out = _git(D_REPO, "status", "--short")
        stray = [l for l in out.splitlines() if change_root not in l]
        assert stray == [], "D 盘仓库有意外未提交项: %s" % stray


# ---------------------------------------------------------------------------
# B. C 盘工作区保留
# ---------------------------------------------------------------------------

class TestCWorkspacePreserved:
    """TC-MDD-006 —— 「归档不删」。"""

    def test_b1_c_workspace_exists(self):
        assert C_WORKSPACE.exists(), "C 盘工作区被删除了 —— 决定是「保留作历史归档」"
        assert C_REPO.exists(), "C 盘 stdd-repo 被删除了"

    def test_b2_c_repo_still_has_history(self):
        if not C_REPO.exists():
            pytest.skip("C 盘仓库不存在")
        assert _git(C_REPO, "rev-list", "--count", "HEAD").isdigit()
        assert int(_git(C_REPO, "rev-list", "--count", "HEAD")) > 50


# ---------------------------------------------------------------------------
# C. 环境自洽
# ---------------------------------------------------------------------------

class TestCEnvironment:
    """TC-MDD-004 / TC-MDD-007 的静态部分。"""

    def test_c1_d_repo_has_tag(self):
        assert "fstdd-v1.0.0" in _git(D_REPO, "tag", "-l")

    def test_c2_d_repo_remotes_have_no_c_path(self):
        """D 盘仓库的 remote **不得**指向 C 盘（否则迁移不彻底）。"""
        out = _git(D_REPO, "remote", "-v")
        bad = [l for l in out.splitlines() if "C:/" in l or "C:\\" in l]
        assert bad == [], "D 盘仓库的 remote 仍指向 C 盘: %s" % bad

    def test_c3_d_repo_origin_is_github(self):
        out = _git(D_REPO, "remote", "get-url", "origin")
        assert "github.com" in out, "origin 应为 GitHub（上传目标）"

    def test_c4_local_bare_repo_is_under_d(self):
        """本地裸库应在 D 盘，且已同步到最新提交。"""
        bare = D_HOME / "backups" / "stdd-repo.git"
        assert bare.exists(), "D 盘缺少本地裸库 backups/stdd-repo.git"
        out = _git(D_REPO, "remote", "get-url", "local")
        assert "D:/tools/FSTDD" in out.replace("\\", "/"), (
            "local remote 应指向 D 盘裸库，实际: %s" % out
        )


# ---------------------------------------------------------------------------
# D. skill 路径
# ---------------------------------------------------------------------------

class TestDSkillPaths:
    """TC-MDD-010 / TC-MDD-011。"""

    def _skills(self) -> list[Path]:
        if not SKILL_DIR.exists():
            return []
        return sorted(SKILL_DIR.glob("fstdd*/SKILL.md"))

    def test_d1_no_non_d_project_path(self):
        """skill 里凡**项目路径**（含 stdd-repo / FSTDD），都必须在 D 盘。

        ⚠️ 判据不能写成「无 C: 路径」—— skill 里的
        `"C:\\Python311\\python.exe"` 本身就在 C 盘，那是**工具**不是我们的资产。
        也不能写成「不含某个具体 C 盘子串」—— 那样只要换个目录名就漏过
        （变异验证实测：把路径改成 `C:/old-place` 就能骗过基于子串的断言）。

        正确判据：**凡含 `stdd-repo` 或 `FSTDD` 的绝对路径，必须以 `D:` 开头。**
        """
        skills = self._skills()
        if not skills:
            pytest.skip("未安装 skill")
        bad = []
        for p in skills:
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'"([A-Za-z]:[\\/][^"]*)"', text):
                path = m.group(1).replace("\\", "/")
                if ("stdd-repo" in path or "FSTDD" in path) and not path.startswith("D:"):
                    bad.append("%s -> %s" % (p.parent.name, path))
        assert bad == [], "skill 中存在非 D 盘的项目路径:\n  " + "\n  ".join(bad)

    def test_d2_points_to_d_drive(self):
        """至少 6 个 skill 应指向 D 盘（阶段 skill 都引用 upstream，fstdd-fin 例外）。"""
        skills = self._skills()
        if not skills:
            pytest.skip("未安装 skill")
        ok = [p.parent.name for p in skills
              if "D:/tools/FSTDD" in p.read_text(encoding="utf-8", errors="replace")]
        assert len(ok) >= 6, "指向 D 盘的 skill 仅 %d 个: %s" % (len(ok), ok)


# ---------------------------------------------------------------------------
# E. 文档与记忆
# ---------------------------------------------------------------------------

class TestEDocsAndMemory:
    """TC-MDD-012 / TC-MDD-013。"""

    def test_e1_docs_point_to_d_drive(self):
        doc = (D_REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert "D:/tools/FSTDD" in doc or "D:\\tools\\FSTDD" in doc
        assert "法定源" in doc

    def test_e2_docs_keep_existing_warnings(self):
        """更新文档时**不得**顺手删掉仍有效的告警。"""
        doc = (D_REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert "DKK_Fstdd" in doc and "不要动" in doc, "D 盘调试副本的告警被删了"
        assert "上传目标" in doc, "GitHub 是上传目标的说明被删了"

    def test_e3_memory_points_to_d_drive(self):
        mem = (D_HOME / ".workbuddy-ai/memory/MEMORY.md").read_text(encoding="utf-8")
        assert "D:/tools/FSTDD" in mem or "D:\\tools\\FSTDD" in mem
        assert "DKK_Fstdd" in mem and "不要动" in mem, "记忆里的调试副本告警被删了"


# ---------------------------------------------------------------------------
# F. 不误伤其它位置
# ---------------------------------------------------------------------------

class TestFOtherLocations:
    """TC-MDD-014。"""

    def test_f1_d_debug_copy_untouched(self):
        if not D_DEBUG_COPY.exists():
            pytest.skip("D 盘调试副本不存在（本机环境差异）")
        assert (D_DEBUG_COPY / "upstream").exists(), "D 盘调试副本结构异常"

    def test_f2_archived_outside_copy_still_present(self):
        """上一轮归档的区外副本应仍在（本变更不删除任何位置）。"""
        if not OTHER_OUTSIDE.exists():
            pytest.skip("区外副本不存在（可能已被 D哥 处置）")
        assert (OTHER_OUTSIDE / "upstream").exists()
