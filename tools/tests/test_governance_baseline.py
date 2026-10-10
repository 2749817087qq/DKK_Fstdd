# -*- coding: utf-8 -*-
"""P3 BUILD 切片 3/4 的自动化测试（test-plan T3.1-T3.4 / T4.1-T4.3）。

入库位置建议：tools/tests/test_governance_baseline.py
夹具全部合成；真实仓库实跑用例（T4.4-T4.6）不在本文件，见 build-runbook.md。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

import audit_experience_baseline as ab  # noqa: E402
import validate_upstream_patches as vp  # noqa: E402

HDR = "| # | 文件 | 行号 | 修改原因 | 关联上游 issue/PR | 登记日期 | 登记人 | 预期回退版本 |"
SEP = "|---|---|---|---|---|---|---|---|"


def _mk_repo(tmp_path, files: dict, registry: str | None = None):
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    if registry is not None:
        rp = tmp_path / "docs" / "UPSTREAM_PATCHES.md"
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(registry, encoding="utf-8", newline="\n")
    return tmp_path


EXP_DIR = ".fstdd/experiences"
SINGLE = "---\nexperience_id: EXP-0001\ncategory: workflow\nseverity: low\n---\n正文。\n"
DUAL = ("<!-- fstdd-inbox\nexperience_id: EXP-0046\n-->\n\n---\nexported_at: 2026-09-26\n"
        "sanitized: true\n---\n<!-- fstdd-inbox\nexperience_id: EXP-0046\nauthor: anonymous\nreceived_at: 2026-09-18\n-->\n\n---\nexperience_id: EXP-0046\ncategory: guard\n"
        "severity: high\n---\n正文。\n")
EID_MISMATCH = ("---\nexported_at: 2026-09-26\n---\n\n---\nexperience_id: EXP-1BE44745\n"
                "category: process_deviation\nseverity: medium\n---\n正文。\n")
EXPORTED_ONLY = "---\nexported_at: 2026-09-26\nsanitized: true\n---\n正文。\n"


# ---------- T4.1 切块与结构分类 ----------

def test_t41_single_block_unaffected(tmp_path):
    repo = _mk_repo(tmp_path, {f"{EXP_DIR}/EXP-0001.md": SINGLE,
                               f"{EXP_DIR}/.experience-index.yaml": "entries:\n  - experience_id: EXP-0001\n"})
    out = tmp_path / "a.json"
    rc = _run_audit(repo, out)
    rep = json.loads(out.read_text(encoding="utf-8"))
    rec = _rec(rep, "EXP-0001.md")
    assert rc == 0 and rec["structure"] == "single_block"
    assert rec["missing_current"] == [] and rec["eid_match"] is True


def test_t41_dual_block_recovers_all_fields(tmp_path):
    repo = _mk_repo(tmp_path, {f"{EXP_DIR}/EXP-0046.md": DUAL,
                               f"{EXP_DIR}/.experience-index.yaml": "entries:\n  - experience_id: EXP-0046\n"})
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    rep = json.loads(out.read_text(encoding="utf-8"))
    rec = _rec(rep, "EXP-0046.md")
    assert rec["structure"] == "dual_block_import"
    assert rec["recovered_by_last_block"] == ["experience_id", "category", "severity"]
    assert rep["summary"]["affected_entries"] == 1


def test_t41_exported_only_detected(tmp_path):
    repo = _mk_repo(tmp_path, {f"{EXP_DIR}/EXP-0009.md": EXPORTED_ONLY})
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    assert _rec(json.loads(out.read_text(encoding="utf-8")), "EXP-0009.md")["structure"] == "exported_block_only"


# ---------- T4.2 eid 不一致 ----------

def test_t42_eid_mismatch_flagged(tmp_path):
    repo = _mk_repo(tmp_path, {f"{EXP_DIR}/EXP-1BA44745.md": EID_MISMATCH,
                               f"{EXP_DIR}/.experience-index.yaml": "entries:\n  - experience_id: EXP-1BA44745\n"})
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["summary"]["eid_mismatch"] == {"count": 1, "files": ["EXP-1BA44745.md"]}
    assert _rec(rep, "EXP-1BA44745.md")["true_eid"] == "EXP-1BE44745"
    assert _rec(rep, "EXP-1BA44745.md")["in_index"] is False  # 真身 eid 对账，非文件名


# ---------- T4.3 索引对账 ----------

def test_t43_index_recon_by_true_eid(tmp_path):
    repo = _mk_repo(tmp_path, {f"{EXP_DIR}/EXP-0046.md": DUAL,
                               f"{EXP_DIR}/.experience-index.yaml": "entries:\n  - experience_id: EXP-0046\n"})
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["summary"]["index_reconciliation"]["indexed_true"] == 1
    assert rep["summary"]["index_reconciliation"]["indexed_false_files"] == []


# ---------- T4.3 追加：真实索引形态回归（评审阻塞项 B1） ----------
# 背景：原 load_index_keys 只匹配 `experience_id: <id>` 形态，而真实
# .experience-index.yaml 是 `by_category:` 下的**裸列表项**（实测 `experience_id:`
# 出现 0 次、78 条裸项，含 EXP- 72 条 + FSTDD005- 前缀 6 条）⇒ 实跑 indexed_true=0、
# 全部条目被误判「未入索引」。下列用例锁死该缺陷不得回归。

SINGLE_99 = SINGLE.replace("EXP-0001", "EXP-0099")
#: 真实形态：by_category 下裸列表项（含非 EXP- 前缀的 eid）
BARE_INDEX = "by_category:\n  - EXP-0046\n  - EXP-0099\n  - FSTDD005-EXP-20260918-C1\n"


def test_t43b_bare_list_index_is_parsed(tmp_path):
    """真实索引形态（裸列表项）必须被正确解析 —— 否则 indexed_true 恒 0。"""
    repo = _mk_repo(tmp_path, {
        f"{EXP_DIR}/EXP-0046.md": DUAL,
        f"{EXP_DIR}/EXP-0099.md": SINGLE_99,
        f"{EXP_DIR}/.experience-index.yaml": BARE_INDEX,
    })
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    r = json.loads(out.read_text(encoding="utf-8"))["summary"]["index_reconciliation"]
    assert r["indexed_true"] == 2, f"裸列表项未被解析（回归 B1）：{r}"
    assert r["indexed_false_files"] == []
    assert r["unreconciled_files"] == []
    assert r["invariant_ok"] is True


def test_t43c_bare_list_index_prefix_eid_recognised(tmp_path):
    """非 EXP- 前缀的 eid（FSTDD005-EXP-…）也必须被索引解析捕获。"""
    repo = _mk_repo(tmp_path, {
        f"{EXP_DIR}/FSTDD005-EXP-20260918-C1.md": SINGLE_99,
        f"{EXP_DIR}/.experience-index.yaml": BARE_INDEX,
    })
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["summary"]["index_reconciliation"]["indexed_true"] == 1, rep["summary"]


def test_t43d_no_frontmatter_not_silently_excluded(tmp_path):
    """无 frontmatter 的文件必须进 unreconciled_files，不得被静默排除于对账之外。"""
    repo = _mk_repo(tmp_path, {
        f"{EXP_DIR}/EXP-0046.md": DUAL,
        f"{EXP_DIR}/EXP-0099.md": "<!-- eid 在注释里，全文无 --- 分隔线 -->\n正文。\n",
        f"{EXP_DIR}/.experience-index.yaml": BARE_INDEX,
    })
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    r = json.loads(out.read_text(encoding="utf-8"))["summary"]["index_reconciliation"]
    assert r["indexed_true"] == 1
    assert r["unreconciled_files"] == ["EXP-0099.md"], r
    assert r["invariant_ok"] is True, f"四桶之和不等于 total（静默排除）：{r}"


# ---------- 审计脚本只读/退出码 ----------

def test_audit_readonly_and_exit2(tmp_path):
    repo = _mk_repo(tmp_path, {f"{EXP_DIR}/EXP-0001.md": SINGLE})
    before = {p.name: p.read_bytes() for p in (repo / EXP_DIR).glob("*")}
    out = tmp_path / "a.json"
    _run_audit(repo, out)
    after = {p.name: p.read_bytes() for p in (repo / EXP_DIR).glob("*")}
    assert before == after  # 全程只读
    r = subprocess.run([sys.executable, str(TOOLS / "audit_experience_baseline.py"),
                        "--repo", str(tmp_path / "nonexistent"), "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2


# ---------- T3.1-T3.4 validate 检查项 ----------

def _reg(rows=""):
    return f"# P\n\n{HDR}\n{SEP}\n{rows}"


def test_t31_registry_ok(tmp_path):
    repo = _mk_repo(tmp_path, {"upstream/fstdd/cli/x.py": "# x"},
                    _reg("\n| 1 | upstream/fstdd/cli/x.py | 1 | r | p | d | a | v |\n"))
    assert vp.main(["--repo", str(repo)]) == 0


def test_t31_empty_registry_ok(tmp_path):
    repo = _mk_repo(tmp_path, {}, _reg())
    assert vp.main(["--repo", str(repo)]) == 0


def test_t32_missing_registered_path_fails(tmp_path):
    repo = _mk_repo(tmp_path, {}, _reg("\n| 1 | upstream/no/such.py | 1 | r | p | d | a | v |\n"))
    assert vp.main(["--repo", str(repo)]) == 1


def test_t33_missing_registry_fails(tmp_path):
    repo = _mk_repo(tmp_path, {})
    assert vp.main(["--repo", str(repo)]) == 1


def test_t33_bad_header_fails(tmp_path):
    repo = _mk_repo(tmp_path, {}, "# P\n\n| 文件 |\n|---|\n| x |\n")
    assert vp.main(["--repo", str(repo)]) == 1


def test_t34_unregistered_upstream_change_passes(tmp_path):
    """T3.4 非行为锁定：存在未登记的 upstream/ 修改时检查仍通过（D-1 边界）。"""
    repo = _mk_repo(tmp_path, {"upstream/fstdd/cli/guard.py": "# 未登记修改"}, _reg())
    assert vp.main(["--repo", str(repo)]) == 0


# ---------- 工具函数 ----------

def _run_audit(repo, out):
    return subprocess.run([sys.executable, str(TOOLS / "audit_experience_baseline.py"),
                           "--repo", str(repo), "--out", str(out)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace").returncode


def _rec(rep, name):
    return next(r for r in rep["records"] if r["file"] == name)
