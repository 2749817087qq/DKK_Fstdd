# -*- coding: utf-8 -*-
"""install-source-repo —— 法定源、校验解析顺序、数据流收敛、文档一致。

对应 test-plan.md 的 TC-ISR-004 ~ TC-ISR-016（可自动化部分）。

设计要点
--------
1. **断言真实产物**，不构造假输入：本日已发现「测试只构造自己的输入、
   从不读真实文件」导致契约与真实产物脱节检测不到（`experience.yaml` 的
   字面 `/n` 就是这么漏过去的）。
2. **区分「可执行」与「说明」**：移除第三方默认值后，文档字符串里仍会提到
   那些标识（说明「已移除」），这是合法的。
3. 与 `D:/Programs/DKK_Fstdd` 无关 —— 本套测试**不读也不写**那个目录。
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent

CANONICAL_TOOLS = Path.home() / ".workbuddy-ai" / "Fstdd" / "tools"


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# A. 校验脚本的安装位置解析顺序
# ---------------------------------------------------------------------------

class TestAResolutionOrder:
    """TC-ISR-005 / TC-ISR-006 —— 解析顺序必须「法定源优先」。"""

    def test_a1_source_declares_canonical_first(self):
        """源码里**自定位**必须排在「区外副本」之前。

        原则是「用**安装源自己的** verify 去校验」（被校验对象是已安装的 skill，
        其内固化路径指向安装源）。安装源自 2026-09-17 起是**工作区仓库**，
        而脚本就在工作区仓库里 → 自定位即命中安装源。

        > 历史注记：2026-09-16 该断言方向相反（当时安装源在区外）。
        > 本 change 把法定源收进工作区后随之反转 —— **不是反复，是同一原则的必然结果**。
        """
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        i_here = src.find("here,", src.find("cands += ["))
        i_outside = src.find('".workbuddy-ai" / "Fstdd" / "tools"')
        assert i_here != -1, "未找到自定位候选"
        assert i_outside != -1, "未找到区外副本候选"
        assert i_here < i_outside, (
            "自定位必须优先 —— 安装源是工作区仓库，而脚本就在其中；"
            "把区外副本放首位会让校验去比对另一份陈旧副本，恒定误报"
        )

    def test_a2_fstdd_inst_dir_still_wins(self):
        """`FSTDD_INST_DIR` 显式覆盖仍须是最高优先级。"""
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        assert 'os.environ.get("FSTDD_INST_DIR")' in src
        i_env = src.find('if os.environ.get("FSTDD_INST_DIR")')
        i_canon = src.find('".workbuddy-ai" / "Fstdd" / "tools"')
        assert 0 <= i_env < i_canon

    def test_a3_d_drive_is_last_resort_only(self):
        """D 盘调试副本只作兜底，不得作首选。"""
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        i_d = src.find('Path("D:/Programs/DKK_Fstdd/tools")')
        i_canon = src.find('".workbuddy-ai" / "Fstdd" / "tools"')
        assert i_d != -1 and i_canon < i_d

    def test_a4_verify_rename_uses_same_order(self):
        """`verify_rename.py` 必须采用同一顺序（自定位优先）。"""
        src = (REPO / "tools/verify_rename.py").read_text(encoding="utf-8")
        i_here = src.find("_here,", src.find("_cands += ["))
        i_outside = src.find('".workbuddy-ai" / "Fstdd" / "tools"')
        assert i_here != -1 and i_outside != -1 and i_here < i_outside

    def test_a5_backup_check_tolerates_absent_backup(self):
        """备份完整性必须容忍「无备份」——合规树不产生备份是合法状态。"""
        src = (REPO / "tools/verify_skill_standards.py").read_text(encoding="utf-8")
        assert "未找到任何 --fix 备份目录" not in src, (
            "仍在无条件要求备份存在 —— 会在合规环境里恒定误报 FAIL"
        )
        assert "属合法状态" in src, "缺少「无备份合法」的显式说明"


# ---------------------------------------------------------------------------
# B. 数据流收敛到自有仓库
# ---------------------------------------------------------------------------

class TestBDataFlow:
    """TC-ISR-010 / TC-ISR-011 —— 第三方来源必须移除。"""

    def test_b1_knowledge_py_has_no_third_party_default(self):
        """`knowledge.py` 不得含硬编码的第三方默认值。"""
        p = REPO / "upstream/fstdd/cli/commands/knowledge.py"
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
        # 文档字符串中的引用属「说明」，合法
        doc_lines = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node, clean=False) and node.body:
                    first = node.body[0]
                    doc_lines.update(range(first.lineno,
                                           (getattr(first, "end_lineno", None)
                                            or first.lineno) + 1))
        offenders = [
            (i, ln.strip()) for i, ln in enumerate(src.splitlines(), 1)
            if "leonai42/stdd-experiences" in ln and i not in doc_lines
        ]
        assert offenders == [], (
            "文档字符串之外的第三方默认值必须移除：%s" % offenders
        )

    def test_b2_knowledge_py_returns_early_on_empty_repo(self):
        """`repo` 为空时必须**提前返回** —— 否则空值会落到 `gh clone` 仍然外联。"""
        src = (REPO / "upstream/fstdd/cli/commands/knowledge.py").read_text(
            encoding="utf-8")
        assert "if not repo:" in src, "缺少空值提前返回"
        assert "return None" in src

    @pytest.mark.parametrize("rel", [
        "upstream/.fstdd/config.d/experience.yaml",
        ".fstdd/config.d/experience.yaml",
    ])
    def test_b3_experience_yaml_is_valid_and_converged(self, rel):
        """`experience.yaml` 必须能被解析、registries 为空、静默开关可读。

        这条断言的存在理由：该文件此前字面写着 `share:/n  silent:/n    enabled: true`
        （**字面的 /n，不是换行**），解析出畸形键，
        导致 `share.silent.enabled` 根本不存在 —— 而测试只构造自己的输入，从未读它。
        """
        p = REPO / rel
        assert p.exists(), f"缺少 {rel}"
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert d["community"]["registries"] == [], f"{rel}: registries 应为空列表"
        silent = (d.get("share") or {}).get("silent") or {}
        assert silent.get("enabled") is True, (
            f"{rel}: share.silent.enabled 必须可读（此前因字面 /n 而失效）"
        )
        # 反向：不得存在畸形键
        assert not any("/n" in str(k) for k in d), f"{rel}: 存在含字面 /n 的畸形键"

    @pytest.mark.parametrize("rel", [
        "upstream/.fstdd/config.d/knowledge.yaml",
        ".fstdd/config.d/knowledge.yaml",
    ])
    def test_b4_knowledge_yaml_repo_is_empty(self, rel):
        """`knowledge.yaml` 的社区源必须为空。"""
        d = yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))
        repo_val = ((d.get("knowledge") or {}).get("community") or {}).get("repo")
        assert not repo_val, f"{rel}: community.repo 应为空，实际 {repo_val!r}"


# ---------------------------------------------------------------------------
# C. 契约面与文档一致
# ---------------------------------------------------------------------------

class TestCContractAndDocs:
    """TC-ISR-012 / TC-ISR-013 —— 白名单与文档。"""

    def test_c1_allowlist_is_empty(self):
        """`ALLOWED_REFS` 必须清空 —— 原条目的理由（拉取源属既定策略）已失效。"""
        src = (REPO / "upstream/tests/test_cross_cutting_verification.py").read_text(
            encoding="utf-8")
        m = re.search(r"ALLOWED_REFS[^=]*=\s*\{([^}]*)\}", src, re.S)
        assert m is not None, "未找到 ALLOWED_REFS 定义"
        body = m.group(1).strip()
        assert body == "", (
            "ALLOWED_REFS 应已清空；留着以「拉取源」为由的条目即白名单腐烂"
        )

    def test_c2_doc_skill_dir_is_workbuddy(self):
        """文档必须写对全局 skill 目录（内核实际加载 `~/.workbuddy/skills`）。"""
        doc = (REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert ".workbuddy\\skills" in doc or "~/.workbuddy/skills" in doc
        assert "装到 `.workbuddy-ai/skills` 等于白装" in doc

    def test_c3_doc_skill_count_and_policy(self):
        """文档的 skill 数量与经验策略必须与事实一致。"""
        doc = (REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert "**7 个**" in doc, "skill 数量应为 7"
        assert "fstdd-fin" in doc
        assert "静默回传到「我方指定位置」" in doc
        assert "经验自动上传：默认禁用" not in doc, "旧的「默认禁用」表述必须已移除"

    def test_c4_doc_states_three_way_relationship(self):
        """文档必须写明 法定源／上传目标 的关系，并说明区外副本已归档。

        > 2026-09-17：法定源收进工作区后，文档不再使用「开发副本」这一角色名
        > （工作区仓库本身就是法定源），改为「已归档」+「上传目标」。
        """
        doc = (REPO / "docs/WORKBUDDY_INSTALL_NOTES.md").read_text(encoding="utf-8")
        assert "法定源" in doc and "上传目标" in doc
        assert "不是源" in doc or "不是权威" in doc, "必须明确 GitHub 不是权威来源"
        assert "已归档" in doc, "必须说明区外副本已归档"
        assert "git push origin master --tags" in doc, "必须给出上传命令"


# ---------------------------------------------------------------------------
# D. 变更管理自身的一致性
# ---------------------------------------------------------------------------

class TestDChangeHygiene:
    """本变更涉及的既有测试卫生问题（归档后路径失效）。"""

    def test_d1_change_dir_lookup_handles_archive(self):
        """change 目录查找必须兼容 `changes/` 与 `archive/`。

        硬编码 `changes/` 会在归档那一刻报 FileNotFoundError（全量套件实测发生过）。
        """
        src = (REPO / "upstream/tests/test_cross_cutting_verification.py").read_text(
            encoding="utf-8")
        assert "_change_dir()" in src
        assert '.fstdd" / "archive"' in src or '.fstdd/archive' in src
        assert 'CHANGE_DIR = REPO' not in src, "不应再硬编码单一 change 路径"
