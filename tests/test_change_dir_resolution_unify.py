"""test_change_dir_resolution_unify.py — change 目录解析统一（读放行 / 写拒绝 / 契约扫描）

覆盖 TC-CDR-001..012（capability: change-dir-resolution）
对应 spec：`.fstdd/changes/2026-10-07-change-dir-resolution-unify/canonical/specs/code/change-dir-resolution.yaml`
  → REQ-001 / SC-101..104（读路径支持归档）
  → REQ-002 / SC-105..108（写路径准确拒绝；`gate amend-audit` 例外）
  → REQ-003 / SC-109..110（单一入口 + 扫描器双向自检）

背景（实测 @f7bf8ec）：5 个模块（`phase`/`gate`/`state`/`work`/`baseline`）各留一套自建解析器，
只扫 `.fstdd/changes/`，无 `archive/` 回退 ⇒ 对已归档 change 报 `.fstdd.yaml not found in <name>`
（**误导文案**：读起来像「change 不存在」）。其中 `gate amend-audit` 最刺眼 ——
它的设计用途就是给历史/归档 Gate 追加追认审计，却因解析器不支持归档而用不了。

⚠️ 纪律（EXP-2026-0015 / EXP-2026-0023）：本文件所有 `archive` / `rollback` 调用都在
   **tmp_path 合成项目**内进行；对仓库内的真实 change **只做只读**操作。

⚠️ 契约扫描判据的边界（已知，已登记）：判据为「模块级」的**存在性**检查（curated 清单 +
   函数级泛化检查），无法识别「同一模块内既有统一入口调用、又有一处自建解析」的极端形态
   （EXP-2026-0024）。故本文件同时提供**逐命令行为断言**作第二层防线（TC-CDR-001..008）。
"""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import repo_root

REPO = repo_root()
CLI = REPO / "upstream" / "bin" / "fstdd"
COMMANDS_DIR = REPO / "upstream" / "fstdd" / "cli" / "commands"

ARCH = "2026-01-01-archived-feature"
ARCH_SHORT = "archived-feature"
ACT = "2026-01-02-active-feature"

#: 「接受 change 名」的命令模块（判据 A：显式清单）。
#: 来源：`upstream/fstdd/cli/__init__.py` 中为各子命令声明 change 名参数的位置参数
#: （`name` / `change_name` / `change`）。新增此类命令时须同步加入本清单。
CHANGE_NAME_MODULES = (
    "archive", "abort", "rollback",
    "canon", "ci", "dependency_graph", "diff", "extract_proposal",
    "status", "structure", "validate",
    "phase", "gate", "state", "work", "baseline",
)

#: 统一入口的函数名（`finder.py`）。
#: `_resolve_in` 是 finder 的**解析原语**：当调用方必须扫一个**特定** base_dir
#: （如 `archive/aborted/`，统一入口不覆盖）时复用它，而不是自己写一遍精确/后缀匹配。
UNIFIED_ENTRIES = ("find_change_dir", "require_active_change_dir", "_resolve_in")

#: 自建解析函数的命名特征（判据 B：函数级泛化检查）
SELF_RESOLVER_PREFIXES = ("_find_change", "_resolve_change")


def _mk_state(name: str, status: str, current_phase: str = "deliver") -> dict:
    return {
        "change_id": name,
        "complexity_score": 9,
        "current_phase": current_phase,
        "design_adjustments": {"count": 0},
        "mode": "thorough",
        "phases": {
            "build": {"status": "completed", "confirmed_at": "2026-01-01T03:00:00+00:00",
                      "confirmed_by": "dialog", "confirmed_evidence": "确认"},
            "deliver": {"status": "completed", "confirmed_at": "2026-01-01T04:00:00+00:00",
                        "confirmed_by": "dialog", "confirmed_evidence": "确认"},
            "spec": {"status": "completed", "confirmed_at": "2026-01-01T02:00:00+00:00",
                     "confirmed_by": "dialog", "confirmed_evidence": "确认"},
            "understand": {"status": "completed", "confirmed_at": "2026-01-01T01:00:00+00:00",
                           "confirmed_by": "dialog", "confirmed_evidence": "确认"},
        },
        "score_confidence": "preliminary",
        "status": status,
        "task_type": "code",
        "traceability": {"spec_scenarios": 1, "tc_cases": 1, "test_functions": 1},
        "version": "3.0",
    }


def _write_state(cd: Path, state: dict) -> None:
    cd.mkdir(parents=True, exist_ok=True)
    (cd / ".fstdd.yaml").write_text(
        yaml.safe_dump(state, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8", newline="",
    )


def _mk_archived(tmp_path: Path, name: str = ARCH) -> Path:
    cd = tmp_path / ".fstdd" / "archive" / name
    _write_state(cd, _mk_state(name, "archived"))
    return cd


def _mk_active(tmp_path: Path, name: str = ACT) -> Path:
    """在办 change：understand 已完成（Gate 1 已确认），其余相位 pending。

    刻意用「fresh」态 —— `phase advance` 的 understand→spec 只需 Gate 1 确认，
    而 build→deliver 还要求 per-slice 证据链（tc_coverage/new_tests/verified_at），
    与「在办 change 上写路径零漂移」这条断言无关，不必构造。
    """
    cd = tmp_path / ".fstdd" / "changes" / name
    state = _mk_state(name, "active", current_phase="understand")
    state["phases"] = {
        "understand": {"status": "completed", "confirmed_at": "2026-01-01T01:00:00+00:00",
                       "confirmed_by": "dialog", "confirmed_evidence": "确认"},
        "spec": {"status": "pending"},
        "build": {"status": "pending"},
        "deliver": {"status": "pending"},
    }
    _write_state(cd, state)
    return cd


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(project), capture_output=True, encoding="utf-8", errors="replace", timeout=120,
    )


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.md5(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def _has_archived_hint(text: str) -> bool:
    return "已归档" in text and "rollback" in text


# ============================================================
# TC-CDR-001 / SC-101 — phase status 在归档 change 上正常
# TC-CDR-002 / SC-102 — state（只读）在归档 change 上正常
# TC-CDR-003 / SC-103 — work list 在归档 change 上正常
# ============================================================
def test_tc_cdr_001_phase_status_works_on_archived(tmp_path):
    """TC-CDR-001 / SC-101：归档 change 上 `phase status` 应 rc=0 且无「.fstdd.yaml not found」。"""
    _mk_archived(tmp_path)
    r = _run(tmp_path, "phase", "status", ARCH)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout[-300:]}\n{r.stderr[-300:]}"
    out = r.stdout + r.stderr
    assert ".fstdd.yaml not found" not in out, f"仍是误导文案：{out[-300:]}"
    assert ARCH in out, f"未输出该 change 的信息：{out[-300:]}"


def test_tc_cdr_002_state_reads_archived(tmp_path):
    """TC-CDR-002 / SC-102：归档 change 上 `state`（只读）应 rc=0。"""
    _mk_archived(tmp_path)
    r = _run(tmp_path, "state", ARCH)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout[-300:]}\n{r.stderr[-300:]}"
    out = r.stdout + r.stderr
    assert ".fstdd.yaml not found" not in out, f"仍是误导文案：{out[-300:]}"
    # 不得再暴露「去 changes/ 找」的路径（修复前的原话含 `.fstdd\changes\<name>`）
    assert ".fstdd\changes" not in out and ".fstdd/changes" not in out, (
        f"仍暴露 changes/ 路径 ⇒ 说明解析器还在错的地方找：{out[-300:]}"
    )
    assert ARCH in out, f"未输出该 change 名：{out[-300:]}"


def test_tc_cdr_003_work_list_works_on_archived(tmp_path):
    """TC-CDR-003 / SC-103：归档 change 上 `work list` 应 rc=0。"""
    _mk_archived(tmp_path)
    r = _run(tmp_path, "work", "list", ARCH)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout[-300:]}\n{r.stderr[-300:]}"
    out = r.stdout + r.stderr
    assert ".fstdd.yaml not found" not in out, f"仍是误导文案：{out[-300:]}"
    assert "关联工作" in out, f"未输出关联工作记录区（应为「暂无关联工作记录」）：{out[-300:]}"


def test_tc_cdr_003b_real_repo_archived_change_is_readable():
    """对**仓库内真实归档 change** 只读访问（不加合成 fixture，验证真实形态）。"""
    archived = sorted((REPO / ".fstdd" / "archive").glob("*/"))
    names = [d.name for d in archived if (d / ".fstdd.yaml").exists()]
    assert names, "仓库内无归档 change，测试失去意义"
    name = names[-1]
    r = _run(REPO, "phase", "status", name)
    assert r.returncode == 0, f"{name}: exit {r.returncode}\n{r.stdout[-300:]}"
    assert ".fstdd.yaml not found" not in (r.stdout + r.stderr)


# ============================================================
# TC-CDR-004 / SC-104 — 短名后缀匹配在归档区生效
# ============================================================
def test_tc_cdr_004_short_name_suffix_matches_archive(tmp_path):
    _mk_archived(tmp_path)
    r = _run(tmp_path, "phase", "status", ARCH_SHORT)
    assert r.returncode == 0, f"短名未命中归档区：exit {r.returncode}\n{r.stdout[-300:]}"
    assert ARCH in (r.stdout + r.stderr)


# ============================================================
# TC-CDR-005 / SC-105 — phase 写操作拒绝且文案含三要素
# TC-CDR-006 / SC-106 — state --set / work add / baseline establish 同语义拒绝
# ============================================================
@pytest.mark.parametrize("write_args", [
    ("phase", "advance", ARCH),
    ("phase", "set", ARCH, "deliver"),
    ("phase", "record-slice", ARCH, "1", "--tc-coverage", "1/1", "--new-tests", "1"),
])
def test_tc_cdr_005_phase_write_refused_with_accurate_hint(tmp_path, write_args):
    """TC-CDR-005 / SC-105：归档 change 上的 `phase advance` 应 rc≠0，文案含「已归档」+ rollback + 归档路径，且不落盘。"""
    cd = _mk_archived(tmp_path)
    before = _snapshot(cd)
    target = cd / ".fstdd.yaml"
    mtime_before = target.stat().st_mtime_ns

    r = _run(tmp_path, *write_args)
    assert r.returncode != 0, f"{write_args} 对归档 change 的写操作应被拒绝"
    out = r.stdout + r.stderr
    assert _has_archived_hint(out), f"文案缺「已归档」或 rollback 指引：{out[-300:]}"
    assert "archive" in out, f"文案未给出归档实际路径：{out[-300:]}"
    assert target.stat().st_mtime_ns == mtime_before, "被拒绝却仍改写了归档状态文件"
    assert _snapshot(cd) == before, "被拒绝却仍在归档目录内产生了写入"


@pytest.mark.parametrize("args", [
    ("state", ARCH, "--set", "current_phase=spec"),
    ("work", "add", ARCH, "--type", "doc", "x"),
    ("baseline", "establish", ARCH),
])
def test_tc_cdr_006_other_writes_refused(tmp_path, args):
    """TC-CDR-006 / SC-106：`state --set` / `work add` / `baseline establish` 三者的归档拒绝语义。"""
    cd = _mk_archived(tmp_path)
    before = _snapshot(cd)

    r = _run(tmp_path, *args)
    assert r.returncode != 0, f"{args} 对归档 change 应被拒绝"
    out = r.stdout + r.stderr
    assert _has_archived_hint(out), f"{args} 文案缺「已归档」或 rollback：{out[-300:]}"
    assert _snapshot(cd) == before, f"{args} 被拒绝却仍在归档目录内产生了写入"


# ============================================================
# TC-CDR-007 / SC-107 — gate amend-audit 对归档 change 放行
# ============================================================
def test_tc_cdr_007_gate_amend_audit_allows_archived(tmp_path):
    cd = _mk_archived(tmp_path)
    r = _run(tmp_path, "gate", "amend-audit", ARCH,
             "--gate", "3", "--confirmed-by", "cli", "--evidence", "归档后补录追认")
    assert r.returncode == 0, f"amend-audit 应放行归档 change：exit {r.returncode}\n{r.stdout[-300:]}"

    state = yaml.safe_load((cd / ".fstdd.yaml").read_text(encoding="utf-8"))
    amendments = state.get("audit_amendments") or []
    assert any(a.get("gate") == 3 for a in amendments), (
        f"未追加 Gate 3 追认审计：{amendments}"
    )
    # 追认内容必须真的落盘（不能只看「有没有一条 gate=3」）
    blob = yaml.safe_dump(amendments, allow_unicode=True)
    assert "归档后补录追认" in blob, f"追认 evidence 未落盘：{blob[:200]}"
    # 原闸门字段仍不可变
    assert state["phases"]["build"]["confirmed_evidence"] == "确认"


# ============================================================
# TC-CDR-008 / SC-108 — 在办 change 上读写零漂移
# ============================================================
def test_tc_cdr_008_active_change_read_write_unchanged(tmp_path):
    _mk_active(tmp_path)
    for args in (("phase", "status", ACT), ("state", ACT), ("work", "list", ACT)):
        r = _run(tmp_path, *args)
        assert r.returncode == 0, f"{args} 在办 change 上失败：{r.stdout[-200:]}"
        assert "已归档" not in (r.stdout + r.stderr), f"{args} 在办 change 上误报「已归档」"

    # 写路径 1：在办 change 上 work add 正常落盘
    r = _run(tmp_path, "work", "add", ACT, "--type", "doc", "在办记录")
    assert r.returncode == 0, f"在办 change 上 work add 应成功：{r.stdout[-200:]}"
    state = yaml.safe_load((tmp_path / ".fstdd" / "changes" / ACT / ".fstdd.yaml").read_text(encoding="utf-8"))
    assert state.get("related_work"), "在办 change 上 work add 未落盘"
    assert state["related_work"][0]["description"] == "在办记录"
    assert state["related_work"][0]["type"] == "doc"

    # 写路径 2：在办 change 上 phase advance 正常推进（test-plan TC-CDR-008 的原定动作）
    # fixture 为 fresh 态（understand 已完成）⇒ 从 understand 推到 spec
    r = _run(tmp_path, "phase", "advance", ACT)
    assert r.returncode == 0, f"在办 change 上 phase advance 应成功：{r.stdout[-300:]}"
    state = yaml.safe_load((tmp_path / ".fstdd" / "changes" / ACT / ".fstdd.yaml").read_text(encoding="utf-8"))
    assert state["current_phase"] == "spec", f"未推进：{state['current_phase']}"
    assert "已归档" not in (r.stdout + r.stderr)


# ============================================================
# TC-CDR-011 / SC-104 AND-1 — 无 archive/ 目录时不抛异常
# ============================================================
def test_tc_cdr_011_no_archive_dir_is_safe(tmp_path):
    _mk_active(tmp_path)  # 只有 changes/，没有 archive/
    r = _run(tmp_path, "phase", "status", ACT)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout[-300:]}\n{r.stderr[-300:]}"
    out = r.stdout + r.stderr
    assert "Traceback" not in out, "无 archive/ 时抛异常"
    assert "archive" not in out.lower(), f"无 archive/ 却报 archive 相关错误：{out[-300:]}"


# ============================================================
# TC-CDR-012 / SC-108 AND-1 — 对已归档 change 再 archive 仍拒绝（反例守卫）
# ============================================================
def test_tc_cdr_012_archive_still_refuses_archived(tmp_path):
    cd = _mk_archived(tmp_path)
    before = _snapshot(cd)

    r = _run(tmp_path, "archive", ARCH)
    assert r.returncode != 0, "对已归档 change 执行 archive 必须拒绝（否则会把自己再移动一次）"
    assert cd.is_dir(), "归档目录被移动了"
    assert _snapshot(cd) == before, "归档目录内容被改动"


# ============================================================
# TC-CDR-009 / SC-109 — 契约扫描：接受 change 名的模块 100% 走统一入口
# ============================================================
def _uses_unified_entry(src: str) -> bool:
    """AST 口径：模块是否调用/导入统一入口。

    覆盖四种写法：`from ..finder import X` / `X(...)` / `finder.X(...)` /
    `getattr(finder, "X")(...)`（后者由 Explore-1 评审指出可绕过，已补）。
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "finder":
            return True
        if isinstance(node, ast.alias) and node.name in UNIFIED_ENTRIES:
            return True
        if isinstance(node, ast.Name) and node.id in UNIFIED_ENTRIES:
            return True
        if isinstance(node, ast.Attribute) and node.attr in UNIFIED_ENTRIES:
            return True
        # `getattr(mod, "find_change_dir")` 形态（字符串常量仅在 getattr 实参位置才算）
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in ("getattr", "hasattr"):
            if any(isinstance(a, ast.Constant) and a.value in UNIFIED_ENTRIES for a in node.args):
                return True
    return False


def _self_built_resolvers(src: str) -> list:
    """判据 B（函数级泛化）：名为 `_find_change*` / `_resolve_change*` 的函数，
    若其函数体内**没有**统一入口调用，即判为「自建解析器」。"""
    tree = ast.parse(src)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith(SELF_RESOLVER_PREFIXES):
            continue
        body_src = ast.get_source_segment(src, node) or ""
        if not _uses_unified_entry(body_src):
            offenders.append(f"{node.name}:{node.lineno}")
    return offenders


def test_tc_cdr_009_all_change_name_modules_use_unified_entry():
    missing = [m for m in CHANGE_NAME_MODULES if not (COMMANDS_DIR / f"{m}.py").is_file()]
    assert not missing, f"清单里的模块文件不存在（清单已腐烂）：{missing}"

    no_entry, self_built = [], []
    for mod in CHANGE_NAME_MODULES:
        src = (COMMANDS_DIR / f"{mod}.py").read_text(encoding="utf-8-sig")
        if not _uses_unified_entry(src):
            no_entry.append(mod)
        offenders = _self_built_resolvers(src)
        if offenders:
            self_built.append(f"{mod}.py -> {offenders}")

    assert not no_entry, (
        "以下「接受 change 名」的模块未走统一入口（会重现归档区不可用 / 误导文案）：\n  "
        + "\n  ".join(no_entry)
    )
    assert not self_built, (
        "以下模块仍保留「自建 change 解析函数」（未调用统一入口）：\n  "
        + "\n  ".join(self_built)
    )


# ============================================================
# TC-CDR-010 / SC-110 — 扫描器双向自检（EXP-2026-0021）
# ============================================================
_VIOLATION_SAMPLE = '''
def _find_change(project_root, name=None):
    changes_dir = project_root / ".fstdd" / "changes"
    if name:
        return changes_dir / name
    return None
'''

_LEGAL_SAMPLE = '''
from ..finder import find_change_dir


def _resolve_change_dir(project_root, name):
    return find_change_dir(name, project_root, include_archive=True)
'''

_COMMENT_ONLY_SAMPLE = '''
# 本模块解析 change 目录：使用 find_change_dir(name, root, include_archive=True)


def _find_change(project_root, name=None):
    return project_root / ".fstdd" / "changes" / name
'''

_DOCSTRING_ONLY_SAMPLE = '''
"""本模块通过 find_change_dir 解析 change 目录。"""


def _find_change(project_root, name=None):
    return project_root / ".fstdd" / "changes" / name
'''


def test_tc_cdr_010_scanner_is_not_vacuous():
    """自检：违例样本必须被抓到；合法样本不得误报；「仅注释/文档串提及」必须判违规。"""
    # 违例：自建解析器
    assert _self_built_resolvers(_VIOLATION_SAMPLE) == ["_find_change:2"], (
        f"扫描器未抓到自建解析器：{_self_built_resolvers(_VIOLATION_SAMPLE)}"
    )
    assert not _uses_unified_entry(_VIOLATION_SAMPLE)

    # 合法：走统一入口
    assert _self_built_resolvers(_LEGAL_SAMPLE) == []
    assert _uses_unified_entry(_LEGAL_SAMPLE)

    # 反例：只在**注释**里提到统一入口 ⇒ 仍须判违规
    assert _self_built_resolvers(_COMMENT_ONLY_SAMPLE) == ["_find_change:5"], (
        "注释里提到 find_change_dir 就判合规 ⇒ 假绿"
    )

    # 反例：只在**docstring** 里提到统一入口 ⇒ 仍须判违规
    assert _self_built_resolvers(_DOCSTRING_ONLY_SAMPLE) == ["_find_change:5"], (
        "docstring 里提到 find_change_dir 就判合规 ⇒ 假绿"
    )

    # 反例：完全无解析函数（不应报违规，避免误伤）
    assert _self_built_resolvers("def cmd_x(args):\n    return 0\n") == []

    # `getattr(mod, "find_change_dir")` 形态必须被认作统一入口（Explore-1 评审指出可绕过）
    assert _uses_unified_entry('import fstdd.cli.finder as f\ngetattr(f, "find_change_dir")(n, r)')


# ============================================================
# TC-CDR-005（附加）/ SC-105 — 路径遍历不得绕过归档写拒绝（失败模式 #10）
# ============================================================
@pytest.mark.parametrize("evil_name", [
    "../archive/" + ARCH,
    "../../.fstdd/archive/" + ARCH,
    "..\\archive\\" + ARCH,
])
def test_tc_cdr_005b_traversal_cannot_bypass_archive_reject(tmp_path, evil_name):
    """TC-CDR-005（附加）/ SC-105：含路径分隔符或 `..` 的「change 名」不得解析到归档区后放行写。

    修复前 `require_active_change_dir` 用**词法**前缀比较判归档（`hit.relative_to(archive_root)`），
    而 `_resolve_in` 直接把用户输入拼进 `base_dir / name` ⇒ `..` 可逃逸出 `changes/`。
    加固：`_resolve_in` 拒绝含分隔符/`..` 的名字 + 判定改按 `resolve()` 归一化后比较。
    """
    cd = _mk_archived(tmp_path)
    before = _snapshot(cd)

    r = _run(tmp_path, "phase", "advance", evil_name)
    assert r.returncode != 0, f"遍历名 {evil_name!r} 竟被放行"
    assert _snapshot(cd) == before, f"遍历名 {evil_name!r} 改动了归档目录"

    # 读路径同样不得因遍历而「意外成功」
    r2 = _run(tmp_path, "phase", "status", evil_name)
    assert r2.returncode != 0, f"读路径不应把遍历名解析为合法 change：{evil_name!r}"
