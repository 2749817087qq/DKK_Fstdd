"""证据时效标注（Slice 5）— observed_at / observed_base_git_sha + 三态时效判定。

对应 TC
-------
- TC-EPR-001  canonical proposal 的 why.evidence 块含 observed_at（带时区）
              与 observed_base_git_sha，两者非空
- TC-EPR-002  spec 模板 evidence 示例能定位观测时刻；test-plan 模板证据条目含 observed_at
- TC-EPR-003  proposal 与 spec 两处模板的证据字段口径一致；含填写示例（非仅字段名）
- TC-EPR-004  时效判定：observed_at vs baseline.at → current / pre_baseline，程序可读
- TC-EPR-005  缺 observed_at → undetermined（**不**当作未过期）；三态可区分

模板三源（EXP-20260915-B2 的扩展实测）：
- `canon.py` 内嵌 CANONICAL_PROPOSAL_TEMPLATE（`fstdd new` 的 scaffold 源）
- `.fstdd/templates/canonical/proposal.yaml`（本仓副本）
- `upstream/.fstdd/templates/canonical/proposal.yaml`（安装源）
三处必须同步改。
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
TZ_SUFFIX = re.compile(r"([+-]\d{2}:\d{2}|Z)$")

TMPL_LOCAL = REPO / ".fstdd" / "templates" / "canonical"
TMPL_UPSTREAM = UPSTREAM / ".fstdd" / "templates" / "canonical"
def _find_repo_proposal_yaml(change_id: str) -> Path:
    """change 归档后 canonical 随目录迁到 archive/，按 changes→archive 顺序解析。"""
    for base in ("changes", "archive"):
        yf = (REPO / ".fstdd" / base / change_id
              / "canonical" / "proposals" / f"{change_id}.yaml")
        if yf.exists():
            return yf
    raise FileNotFoundError(f"changes/ 与 archive/ 均找不到 {change_id} 的 proposal YAML")


PROPOSAL_YAML = _find_repo_proposal_yaml("2026-09-17-time-baseline")


def run_cli(*args: str, cwd: Path):
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def load_baseline_mod():
    spec = importlib.util.spec_from_file_location(
        "_fstdd_baseline", UPSTREAM / "fstdd" / "cli" / "commands" / "baseline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# TC-EPR-001 — 证据块含观测时刻与代码版本
# --------------------------------------------------------------------------- #

def test_epr_001_evidence_block_fields():
    """TC-EPR-001：本仓 proposal 的 why.evidence 含 observed_at（带时区）与
    observed_base_git_sha，两者非空。"""
    data = yaml.safe_load(PROPOSAL_YAML.read_text(encoding="utf-8"))
    ev = (data.get("why") or {}).get("evidence")
    assert isinstance(ev, dict), f"why.evidence 应为结构化块，实际: {type(ev)}"
    observed_at = ev.get("observed_at")
    sha = ev.get("observed_base_git_sha")
    assert observed_at, "observed_at 为空"
    assert sha, "observed_base_git_sha 为空"
    assert TZ_SUFFIX.search(str(observed_at)), f"observed_at 无时区: {observed_at!r}"


def test_epr_001_scaffold_has_evidence_fields(tmp_path):
    """TC-EPR-001 补充：`fstdd new` 的 scaffold 模板即含两字段（新 change 开箱合规）。"""
    proj = tmp_path / "proj"
    proj.mkdir()
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"
    rc, _, err = run_cli("new", "epr", cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    change_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())
    yf = proj / ".fstdd" / "changes" / change_id / "canonical" / "proposals" / f"{change_id}.yaml"
    data = yaml.safe_load(yf.read_text(encoding="utf-8"))
    ev = (data.get("why") or {}).get("evidence")
    assert isinstance(ev, dict), f"scaffold 的 why.evidence 应为结构化块: {data.get('why')}"
    assert "observed_at" in ev, f"scaffold 缺 observed_at: {ev}"
    assert "observed_base_git_sha" in ev, f"scaffold 缺 observed_base_git_sha: {ev}"


# --------------------------------------------------------------------------- #
# TC-EPR-002 — spec 模板示例定位观测时刻；test-plan 模板证据条目含 observed_at
# --------------------------------------------------------------------------- #

def test_epr_002_spec_and_testplan_templates():
    """TC-EPR-002：spec 模板 evidence 示例含观测时刻形态；test-plan 模板含 observed_at。"""
    spec_tmpl = (TMPL_UPSTREAM / "spec.yaml").read_text(encoding="utf-8")
    assert re.search(r"observed_at", spec_tmpl), "spec 模板 evidence 示例缺观测时刻"
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}.*[+-]\d{2}:\d{2}", spec_tmpl), (
        "spec 模板 evidence 示例缺带时区的填写示例"
    )

    tp_tmpl = (UPSTREAM / ".fstdd" / "templates" / "test-plan.md").read_text(encoding="utf-8")
    assert "observed_at" in tp_tmpl, "test-plan 模板证据条目缺 observed_at"


# --------------------------------------------------------------------------- #
# TC-EPR-003 — 两处模板一致 + 含填写示例
# --------------------------------------------------------------------------- #

def test_epr_003_templates_consistent_with_examples():
    """TC-EPR-003：本仓与 upstream 的 proposal/spec 模板一致；证据字段含填写示例。"""
    for name in ("proposal.yaml", "spec.yaml"):
        local = (TMPL_LOCAL / name).read_text(encoding="utf-8")
        ups = (TMPL_UPSTREAM / name).read_text(encoding="utf-8")
        assert local == ups, f"{name}: 两处模板不一致（EXP-20260915-B2）"

    prop = (TMPL_UPSTREAM / "proposal.yaml").read_text(encoding="utf-8")
    assert "observed_at" in prop and "observed_base_git_sha" in prop, (
        "proposal 模板缺证据字段"
    )
    # 含填写示例（非仅字段名）：示例值带时区形态
    assert re.search(r"observed_at:\s*\"?\d{4}-\d{2}-\d{2}T", prop), (
        "proposal 模板的 observed_at 缺填写示例（非仅字段名）"
    )


# --------------------------------------------------------------------------- #
# TC-EPR-004 / TC-EPR-005 — 三态时效判定
# --------------------------------------------------------------------------- #

def test_epr_004_005_freshness_three_states():
    """TC-EPR-004/005：current / pre_baseline / undetermined 三态可区分。"""
    mod = load_baseline_mod()
    classify = getattr(mod, "classify_evidence", None)
    assert classify, "baseline.py 缺 classify_evidence"

    baseline_at = "2026-09-17T15:00:00+00:00"

    # 基线之后观测 → current
    r1 = classify("2026-09-17T16:00:00+00:00", baseline_at)
    assert r1["status"] == "current", r1

    # 早于基线 → pre_baseline（明确标识，非「未过期」）
    r2 = classify("2026-09-17T14:00:00+00:00", baseline_at)
    assert r2["status"] == "pre_baseline", r2
    assert r2.get("reason"), "pre_baseline 应附理由"

    # 缺 observed_at → undetermined（不当未过期）
    r3 = classify(None, baseline_at)
    assert r3["status"] == "undetermined", r3
    r4 = classify("", baseline_at)
    assert r4["status"] == "undetermined", r4

    # 三态可区分（程序可读：JSON 序列化无损）
    statuses = {json.loads(json.dumps(r))["status"] for r in (r1, r2, r3)}
    assert statuses == {"current", "pre_baseline", "undetermined"}, statuses
