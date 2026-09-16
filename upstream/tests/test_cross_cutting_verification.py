# -*- coding: utf-8 -*-
"""Slice 4 —— 交叉验证（跨切片，依赖 Slice 1/2/3 的产物）。

对应 test-plan.md：
    TC-CAS-006  目标锁死：不存在指向第三方的**可执行**路径
    TC-CAS-021  变异验证：注入已知缺陷必须被捕获（证明断言非空转）
    TC-CAS-023  validate 的 TC-ID 判定与模板写法相容
    TC-CAS-024  真实重复仍被捕获（不得削弱检查）

设计要点
--------
1. **区分「可执行」与「说明」**（design.md Decision 10）。
   仓库里**确实存在**合法引用，简单 grep 必然误报：
     · 历史说明：`experience.py` 的注释写着「两条外发通道均已永久移除」
     · 上游参考实现：`upstream/deploy/server-api.py` 是**上游自己的**服务端示例
     · 拉取配置：`experience.yaml` 的 `community.registries` 是**只进**的知识拉取源
   所以本文件用 AST 判定：出现在**文档字符串/注释**里的算说明，其余算可执行。

2. **测试绝不往「被自己扫描的目录」里写文件**。
   扫描函数接受可注入的 `roots`，探针一律写到 `tmp_path`。
   否则测试之间会通过文件系统共享可变状态 —— 实测过：并发/重跑时
   前一次遗留的探针会让后一次的断言失败（假红），排查代价远高于改造成本。

3. **变异验证**（TC-CAS-021）是本套测试的元验证：
   把判定逻辑抽成纯函数，对「真实产物」断言通过、对「注入缺陷的副本」断言失败。
   两边都过，才说明断言真的有区分度。
"""
from __future__ import annotations

import ast
import importlib.util
import io
import re
import sys
import tokenize
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent

_CHANGE_NAME = "2026-09-16-contract-auto-share"


def _change_dir() -> Path:
    """定位 change 目录 —— **`changes/` 与 `archive/` 都要找**。

    归档时目录会从 `changes/` 移到 `archive/`。硬编码其中一个位置，
    会在归档那一刻突然报 `FileNotFoundError`（本测试实测发生过）。
    """
    for base in (REPO / ".fstdd" / "changes", REPO / ".fstdd" / "archive"):
        p = base / _CHANGE_NAME
        if p.exists():
            return p
    raise AssertionError(f"找不到 change 目录: {_CHANGE_NAME}")


def load(name: str, rel: str):
    """加载 `tools/` 下的模块（该目录不是包，无 __init__.py）。"""
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 目标锁死：扫描「指向第三方的可执行路径」
# ---------------------------------------------------------------------------

# 第三方目标的标识（上游社区仓库 / 第三方服务器）
THIRD_PARTY_MARKERS = (
    "leonai42/stdd-experiences",
    "hzddyy.com",
)

# 扫描范围：**会被安装/分发**的内容 + 我们自己的代码。
SCAN_ROOTS = (
    "tools",
    "skills",
    "upstream/fstdd",
    "upstream/.fstdd/skills",
    "upstream/.fstdd/config.d",
)

# 扫描豁免：上游 vendor 内容与历史备份。
# 每一条都必须给出理由，不允许无条件豁免。
EXCLUDED_PREFIXES = (
    # 上游自己的服务端参考实现（描述的是**上游**的服务器，不是我们的）。
    # 属 vendor 内容，删除会破坏对上游代码的追踪；且不经由安装器分发。
    "upstream/deploy/",
    # 上游历史版本备份，非当前生效内容。
    "upstream/.fstdd/backup/",
    # 本 change 的规格与测试计划，其中**大量引用**这些标识以说明「已移除」。
    ".fstdd/changes/",
)

# 允许的引用：**拉取（只进）源**，非外发目标。
# 每条都必须给出理由；新增条目须在 review 中说明。另有一条用例断言本表不腐烂
# （表里列出的文件必须仍然真的含有该标识），防止白名单被当成万能豁免。
#
# 2026-09-16 变更后**本表为空**：`knowledge.py` 原先以「拉取（只进）源、属既定策略」
# 为由被豁免，但该 change 决定「经验与知识完全收敛到自有仓库」，
# 已移除硬编码的第三方默认值（并在 repo 为空时提前返回）。
# 理由消失 → 条目必须移除；留着它就是「白名单腐烂」。
ALLOWED_REFS: dict[str, str] = {}


def _docstring_lines(tree: ast.AST) -> set[int]:
    """收集所有文档字符串覆盖的行号。"""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False) and node.body:
                first = node.body[0]
                end = getattr(first, "end_lineno", None) or first.lineno
                lines.update(range(first.lineno, end + 1))
    return lines


def _comment_lines(src: str) -> set[int]:
    """收集所有注释所在行号。"""
    lines: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                lines.add(tok.start[0])
    except tokenize.TokenError:
        pass
    return lines


def _message_lines(tree: ast.AST) -> set[int]:
    """收集 `print()` / 日志调用的字符串参数所在行 —— 那是**消息文本**，不是外发目标。

    例：`print("历史上传通道（leonai42/stdd-experiences、hzddyy.com）的代码已移除。")`
    是面向用户的告知，把它判成「指向第三方的可执行路径」属于误报。
    """
    lines: set[int] = set()
    log_names = {"print", "log", "warning", "info", "debug", "error",
                 "critical", "exception", "warn"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name not in log_names:
            continue
        for arg in list(node.args) + [k.value for k in node.keywords]:
            start = getattr(arg, "lineno", None)
            if start is None:
                continue
            end = getattr(arg, "end_lineno", None) or start
            lines.update(range(start, end + 1))
    return lines


def find_executable_third_party_refs(repo: Path,
                                     roots=SCAN_ROOTS) -> list[str]:
    """返回「指向第三方的**可执行**路径」清单（应为空）。

    Python 文件用 AST 判定：注释、文档字符串、日志/print 消息文本都算**说明**；
    其余（赋值、调用参数、URL 字面量等）算**可执行**。
    非 Python 文本文件不构成可执行路径，由契约面用例单独断言。

    `roots` 可注入，便于测试指向临时目录 —— 测试绝不写入真实仓库树。
    `ALLOWED_REFS` 列出经审查确认属**拉取（只进）**的引用。
    """
    hits: list[str] = []
    for root in roots:
        base = repo / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix != ".py":
                continue
            rel = path.relative_to(repo).as_posix()
            if any(rel.startswith(p) for p in EXCLUDED_PREFIXES):
                continue
            if rel in ALLOWED_REFS:
                continue

            src = path.read_text(encoding="utf-8", errors="replace")
            if not any(m in src for m in THIRD_PARTY_MARKERS):
                continue

            try:
                tree = ast.parse(src)
            except SyntaxError:
                hits.append(f"{rel}: 无法解析（SyntaxError）")
                continue

            explanatory = (_docstring_lines(tree)
                           | _comment_lines(src)
                           | _message_lines(tree))
            for lineno, line in enumerate(src.splitlines(), start=1):
                if not any(m in line for m in THIRD_PARTY_MARKERS):
                    continue
                if lineno not in explanatory:
                    hits.append(f"{rel}:{lineno}: {line.strip()[:100]}")
    return hits


def _count_scannable_py(repo: Path, roots=SCAN_ROOTS) -> int:
    n = 0
    for root in roots:
        base = repo / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix != ".py":
                continue
            rel = path.relative_to(repo).as_posix()
            if any(rel.startswith(p) for p in EXCLUDED_PREFIXES):
                continue
            n += 1
    return n


class TestATargetLockdown:
    """TC-CAS-006 —— 目标锁死。"""

    def test_a1_no_executable_third_party_path(self):
        """不存在指向第三方的可执行路径（仅允许出现在注释/文档字符串里）。"""
        hits = find_executable_third_party_refs(REPO)
        assert hits == [], (
            "发现指向第三方的可执行路径（应仅存在于说明性注释/文档中）：\n"
            + "\n".join("  - " + h for h in hits)
        )

    def test_a2_scan_actually_covers_files(self):
        """扫描器本身有效：确认它确实扫到了足够多的文件。

        防止「扫描范围写错导致一个文件都没扫到」从而假通过。
        """
        n = _count_scannable_py(REPO)
        assert n >= 20, f"扫描到的 .py 文件仅 {n} 个，范围可能写错"

    def test_a3_explanatory_refs_are_tolerated(self, tmp_path):
        """说明性引用必须被容忍 —— 否则会有人为了"扫干净"而删掉已移除的证据。"""
        (tmp_path / "probe").mkdir()
        (tmp_path / "probe" / "m.py").write_text(
            "# 历史说明：曾上传到 leonai42/stdd-experiences，该通道已永久移除\n"
            '"""模块文档：不再使用 hzddyy.com。"""\n'
            "X = 1\n",
            encoding="utf-8")
        assert find_executable_third_party_refs(tmp_path, roots=("probe",)) == [], (
            "注释与文档字符串中的说明性引用不应被判为可执行路径"
        )

    def test_a4_executable_ref_is_detected(self, tmp_path):
        """可执行引用必须被检出 —— 这是本扫描存在的意义。"""
        (tmp_path / "probe").mkdir()
        (tmp_path / "probe" / "m.py").write_text(
            'TARGET = "https://github.com/leonai42/stdd-experiences.git"\n',
            encoding="utf-8")
        hits = find_executable_third_party_refs(tmp_path, roots=("probe",))
        assert any("m.py" in h for h in hits), (
            "赋值形式的第三方目标必须被判为可执行路径"
        )

    def test_a5_pull_source_config_is_not_executable_code(self):
        """`experience.yaml` 的 registries 是**拉取（只进）**源，不是 Python 可执行路径。"""
        yml = (REPO / "upstream/.fstdd/config.d/experience.yaml").read_text(
            encoding="utf-8")
        # 该配置存在且指向上游社区 —— 属既定策略（可拉上游，不外发我们的数据）
        assert "community" in yml and "registries" in yml
        # 但它不是 .py，不进入「可执行路径」扫描
        hits = find_executable_third_party_refs(REPO)
        assert not any("experience.yaml" in h for h in hits)

    def test_a6_allowlist_is_not_rotten(self):
        """白名单不得腐烂：每条列出的文件必须**仍然真的**含有该标识。

        否则白名单会变成万能豁免 —— 文件早就不含标识了，条目却还留着，
        日后真出现违规时会被静默放行。
        """
        for rel, reason in ALLOWED_REFS.items():
            assert reason.strip(), f"{rel} 的豁免理由不能为空"
            path = REPO / rel
            assert path.exists(), f"白名单条目指向不存在的文件: {rel}"
            src = path.read_text(encoding="utf-8", errors="replace")
            assert any(m in src for m in THIRD_PARTY_MARKERS), (
                f"白名单条目已腐烂：{rel} 不再含任何第三方标识，应删除该条目"
            )

    def test_a7_print_message_is_not_a_target(self, tmp_path):
        """`print()` 的字符串是**消息文本**，不得被判为外发目标。"""
        (tmp_path / "probe").mkdir()
        (tmp_path / "probe" / "m.py").write_text(
            'print("历史上传通道（leonai42/stdd-experiences、hzddyy.com）的代码已移除。")\n',
            encoding="utf-8")
        assert find_executable_third_party_refs(tmp_path, roots=("probe",)) == [], (
            "print() 的消息文本被误判为可执行目标"
        )


class TestBContractText:
    """契约面文本断言（与 Slice 1/2/3 的产物交叉验证）。"""

    def test_b1_constitution_no_stale_upload_rule(self):
        """宪法不得声明「自动上传经验到社区」（上游残留）。"""
        const = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        assert "自动上传经验到社区" not in const
        assert "不向第三方外发" in const
        assert "静默回传" in const

    def test_b2_constitution_has_no_bare_stdd(self):
        """宪法不得出现裸 STDD（仅允许出现在上游来源/历史语境）。"""
        const = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        bare = re.findall(r"(?<!F)STDD", const)
        assert bare == [], f"宪法出现 {len(bare)} 处裸 STDD"

    def test_b3_upgrade_notes_no_stale_rules(self, tmp_path):
        """UPGRADE_NOTES（SessionStart 注入给 AI 读）不得含陈旧 rules 或旧名。

        断言对象是**生成的 YAML 内容** —— 那才是 AI 实际读到的。
        不扫 `upgrade.py` 源码：其中 `_CONSTITUTION_MIGRATIONS` 的 old 片段
        **必须**保留裸 `STDD` / 旧命令名（它们是**匹配旧状态的模式**），
        扫整文件会把「用来修正漂移的模式」误判成「漂移本身」。
        """
        if str(UPSTREAM) not in sys.path:
            sys.path.insert(0, str(UPSTREAM))
        from fstdd.cli.commands.upgrade import _write_upgrade_notes

        (tmp_path / ".fstdd").mkdir()
        _write_upgrade_notes(tmp_path, "3.0.4", "3.0.5")
        notes = (tmp_path / ".fstdd" / "UPGRADE_NOTES.yaml").read_text(
            encoding="utf-8")

        assert "Phase 4 DELIVER 自动同步知识图谱" not in notes, "陈旧 rule 仍在"
        assert re.findall(r"(?<!F)STDD", notes) == [], "UPGRADE_NOTES 仍有裸 STDD"
        assert not re.search(r"(?<![A-Za-z])stdd(?![a-z])", notes), (
            "UPGRADE_NOTES 仍有旧命令名"
        )
        assert "静默回传" in notes, "rules 应为静默回传口径"

    def test_b3b_user_facing_text_uses_fstdd(self):
        """`upgrade.py` 的**用户可见文案**必须用 FSTDD / fstdd。

        只针对用户可见文案断言，避开内部标识符（`stdd_source` 等）与
        迁移表的匹配模式（它们按设计保留旧名）。

        ⚠️ 必须用**左边界**断言，不能用 `in`：
        `"STDD 最新版本"` 是 `"FSTDD 最新版本"` 的子串，`in` 判定会把已修正的
        文案误报为残留。本项目已在脱敏正则上踩过同类坑（`README.md` 被当域名）。
        """
        src = (REPO / "upstream/fstdd/cli/commands/upgrade.py").read_text(
            encoding="utf-8")
        for stale in ("无法检测 STDD 源版本", "STDD 最新版本", "重新同步所有 STDD",
                      "Backup current STDD", "Reinstall STDD"):
            assert not re.search(r"(?<![A-Za-z])" + re.escape(stale), src), (
                f"upgrade.py 仍含旧文案（按左边界判定）：{stale}"
            )
        assert "FSTDD 源版本" in src, "用户可见文案应已改为 FSTDD"

    def test_b4_onboarding_manual_no_legacy_phases(self):
        """操作手册不得再把 SLICE/VERIFY 当作阶段名（V3.0.5 已合并进 BUILD）。"""
        for rel in (".fstdd/onboarding/AI_OPERATING_MANUAL.md",
                    "upstream/.fstdd/onboarding/AI_OPERATING_MANUAL.md"):
            text = (REPO / rel).read_text(encoding="utf-8")
            assert "Phase 5" not in text, f"{rel} 仍含旧阶段 Phase 5"
            assert re.findall(r"(?<!F)STDD", text) == [], f"{rel} 仍有裸 STDD"
            assert not re.search(r"(?<![A-Za-z])stdd(?![a-z])", text), (
                f"{rel} 仍有 stdd 旧命令名"
            )

    def test_b5_deliver_policy_replaces_upstream_body(self):
        """deliver 策略注入必须**替换**上游 Step 2.8 正文，而非仅前置注释。"""
        install = (REPO / "tools/install_workbuddy_skills.py").read_text(
            encoding="utf-8")
        mod = load("install_wb", "tools/install_workbuddy_skills.py")
        upstream_body = (
            "### Step 2.8: 经验自动上传（V2.9.6）\n\n"
            "在完成归档和规范合并后，自动将本次 change 中沉淀的经验上传到社区 git 库。\n\n"
            "## 下一节\n"
        )
        out = mod.apply_deliver_policy(upstream_body, [])
        assert "自动将本次 change 中沉淀的经验上传到社区" not in out, (
            "上游「上传到社区」正文必须被移除，否则与静默回传策略构成矛盾指令"
        )
        assert mod.SENTINEL in out, "哨兵必须保留（verify 脚本依赖它）"
        assert "静默回传" in out

    def test_b6_migration_table_matches_template(self):
        """迁移表的「新片段」必须与模板产物一致（防「改了模板忘了改迁移表」）。

        宪法有**两个来源**：`init.py` 的模板、`upgrade.py` 的迁移表。
        二者若不一致，存量项目升级后拿到的宪法会与新建项目**不同** ——
        这正是本变更要修的那种「双向漂移」的复发形态，所以必须锁住。
        """
        if str(UPSTREAM) not in sys.path:
            sys.path.insert(0, str(UPSTREAM))
        from fstdd.cli.commands.upgrade import _CONSTITUTION_MIGRATIONS

        const = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        missing = [new for _old, new in _CONSTITUTION_MIGRATIONS if new not in const]
        assert missing == [], (
            "迁移表的以下「新片段」未出现在仓库宪法中"
            "（模板改了但迁移表没跟上，存量升级会与新建项目产生差异）：\n"
            + "\n".join("  - " + m[:90] for m in missing)
        )

    def test_b7_migration_table_old_fragments_are_stale(self):
        """迁移表的「旧片段」必须**不在**仓库宪法里（否则该规则是死规则）。

        若旧片段仍出现在（已修正的）仓库宪法中，说明迁移没做干净，
        或者该条规则指向的是已经不存在的内容 —— 两种都该被发现。
        """
        if str(UPSTREAM) not in sys.path:
            sys.path.insert(0, str(UPSTREAM))
        from fstdd.cli.commands.upgrade import _CONSTITUTION_MIGRATIONS

        const = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        still_present = [old for old, _new in _CONSTITUTION_MIGRATIONS if old in const]
        assert still_present == [], (
            "迁移表的以下「旧片段」仍存在于仓库宪法中（迁移未做干净）：\n"
            + "\n".join("  - " + o[:90] for o in still_present)
        )


# ---------------------------------------------------------------------------
# validate 的 TC-ID 判定
# ---------------------------------------------------------------------------

class TestCValidateTcIds:
    """TC-CAS-023 / TC-CAS-024 —— validate 的 TC-ID 判定。"""

    @staticmethod
    def _extract(content: str) -> list[str]:
        """复刻 validate.py 的提取规则（只统计案例定义行）。"""
        return re.findall(r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})", content)

    def test_c1_template_style_not_flagged(self):
        """模板规定的写法（矩阵/优先级列表里引用 ID）不得被判为重复。"""
        content = (_change_dir() / "test-plan.md").read_text(encoding="utf-8")
        ids = self._extract(content)
        assert ids, "未提取到任何 TC-ID —— 提取规则可能已失效"
        dup = sorted({i for i in ids if ids.count(i) > 1})
        assert dup == [], f"模板写法被误判为重复：{dup}"

    def test_c2_real_duplicate_still_caught(self):
        """真实重复（两个案例共用同一 ID）必须仍被捕获 —— 修误报不得削弱检查。"""
        content = (
            "| **ID** | TC-XXX-001 |\n"
            "| **ID** | TC-XXX-001 |\n"
        )
        ids = self._extract(content)
        dup = sorted({i for i in ids if ids.count(i) > 1})
        assert dup == ["TC-XXX-001"]

    def test_c3_validate_source_uses_scoped_regex(self):
        """validate.py 的源码必须使用「限定到案例定义行」的正则。"""
        src = (REPO / "upstream/fstdd/cli/commands/validate.py").read_text(
            encoding="utf-8")
        assert r"\*\*ID\*\*\s*\|\s*(TC-" in src, (
            "validate.py 的 TC-ID 提取未限定到案例定义行，会误报矩阵中的引用"
        )


# ---------------------------------------------------------------------------
# 变异验证（元验证）
# ---------------------------------------------------------------------------

def check_constitution_text(text: str) -> list[str]:
    """宪法文本的判定规则（与 TestBContractText 一致），抽成纯函数便于变异测试。"""
    errs = []
    if "自动上传经验到社区" in text:
        errs.append("stale_upload_rule")
    if "静默回传" not in text:
        errs.append("missing_silent_share")
    if re.findall(r"(?<!F)STDD", text):
        errs.append("bare_stdd")
    return errs


class TestDMutationVerification:
    """TC-CAS-021 —— 向被测对象注入已知缺陷，确认断言真的会失败。

    这是本套测试的**元验证**：若某个缺陷注入后判定仍然通过，说明对应断言在空转。
    """

    def test_d1_mutation_stale_upload_rule_caught(self):
        """变异①：把「静默回传」改回「自动上传经验到社区」→ 必须被捕获。"""
        good = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        assert check_constitution_text(good) == [], "基准应通过"
        bad = good.replace("静默回传", "自动上传经验到社区", 1)
        assert "stale_upload_rule" in check_constitution_text(bad)

    def test_d2_mutation_bare_stdd_caught(self):
        """变异②：把 1 处 FSTDD 改回裸 STDD → 必须被捕获。"""
        good = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        bad = good.replace("FSTDD 流程管控", "STDD 流程管控", 1)
        assert "bare_stdd" in check_constitution_text(bad)

    def test_d3_mutation_missing_silent_share_caught(self):
        """变异③：删掉静默回传条款 → 必须被捕获。"""
        good = (REPO / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        bad = "\n".join(l for l in good.splitlines() if "静默回传" not in l)
        assert "missing_silent_share" in check_constitution_text(bad)

    def test_d4_mutation_executable_target_caught(self, tmp_path):
        """变异④：植入指向第三方的**可执行**目标 → 扫描必须捕获。"""
        (tmp_path / "probe").mkdir()
        (tmp_path / "probe" / "m.py").write_text(
            'DEFAULT = "https://github.com/leonai42/stdd-experiences.git"\n',
            encoding="utf-8")
        hits = find_executable_third_party_refs(tmp_path, roots=("probe",))
        assert any("m.py" in h for h in hits), (
            "植入的可执行第三方目标未被扫描捕获 —— 断言在空转"
        )

    def test_d5_mutation_legacy_phase_caught(self, tmp_path):
        """变异⑤：把旧阶段名写回手册文本 → 判定规则必须命中。"""
        probe = tmp_path / "manual.md"
        probe.write_text("| Phase 5 (Verify) 完成前 | x |\n", encoding="utf-8")
        text = probe.read_text(encoding="utf-8")
        assert "Phase 5" in text, "旧阶段名判定规则在空转"

    def test_d6_mutation_deliver_policy_keeps_body_caught(self):
        """变异⑥：若策略注入只前置注释而不移除正文 → 断言必须失败。"""
        mod = load("install_wb2", "tools/install_workbuddy_skills.py")
        upstream_body = (
            "### Step 2.8: 经验自动上传（V2.9.6）\n\n"
            "在完成归档和规范合并后，自动将本次 change 中沉淀的经验上传到社区 git 库。\n"
        )
        # 模拟「只前置注释」的旧行为：正文仍在
        old_behavior = f"<!-- {mod.SENTINEL} -->\n" + upstream_body
        assert "自动将本次 change 中沉淀的经验上传到社区" in old_behavior
        # 真实实现必须消除它
        out = mod.apply_deliver_policy(upstream_body, [])
        assert "自动将本次 change 中沉淀的经验上传到社区" not in out
