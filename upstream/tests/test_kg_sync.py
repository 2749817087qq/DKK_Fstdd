"""test_kg_sync.py — kg-autosync 行为测试（24 TC）

Change: 2026-10-03-caveman-kg-sync
TC 映射: .fstdd/changes/2026-10-03-caveman-kg-sync/test-plan.md

RED 阶段：本文件先于 `upstream/fstdd/kg_sync.py` 存在 → import 失败即为 RED。
所有用例都在 tmp_path 构造最小项目，绝不触碰真实 knowledge-graph.yaml。
"""
import hashlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = REPO_ROOT / "upstream"
if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))

from fstdd.kg_sync import (  # noqa: E402
    DEFAULT_EDGE_THRESHOLD,
    ID_RE,
    SCAN_TARGETS,
    diff_path,
    graph_path,
    iter_scan_files,
    load_graph,
    save_graph,
    sync,
)

FSTDD_BIN = UPSTREAM / "bin" / "fstdd"
PY = sys.executable

_SKILL_MD = ".fstdd/skills/build.md"
_FIN_MD = "skills/fstdd-fin/SKILL.md"
_TMPL_MD = ".fstdd/templates/tasks.md"


def _iso(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _project(tmp_path: Path, nodes=None, sources=None, edges=None) -> Path:
    """构造最小项目：5 类 scan 目录各 1 文件 + knowledge-graph.yaml。"""
    for rel in SCAN_TARGETS:
        d = tmp_path / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "anchor.md").write_text("# anchor\n占位锚点\n", encoding="utf-8")
    graph = {"graph_version": "1.1", "last_merged": "", "nodes": nodes or [], "edges": edges or []}
    save_graph(graph_path(tmp_path), graph)
    for rel, content in (sources or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


def _node(nid: str, **kw) -> dict:
    base = {
        "id": nid,
        "type": "failure_pattern",
        "title": nid,
        "description": "",
        "severity": "medium",
        "source_files": [],
        "last_synced_at": "2020-01-01T00:00:00+00:00",
    }
    base.update(kw)
    return base


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _run_cwd(args, cwd: Path):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(cwd))


def _get_node(nodes, nid):
    return next((n for n in nodes if n.get("id") == nid), None)


# ============================================================
# REQ 1: CLI 入口 + dry-run
# ============================================================
def test_KG_TC_001_cli_dry_run_outputs_results(tmp_path):
    """KG-SC-002: kg sync --dry-run → stdout 含 ADD/UPDATE/DEPRECATE/EDGE_BUILD, exit 0"""
    proj = _project(tmp_path, sources={_SKILL_MD: "- FIN-THR-005: 新阈值规则\n"})
    r = _run_cwd([PY, str(FSTDD_BIN), "kg", "sync", "--dry-run"], proj)
    assert r.returncode == 0, r.stderr
    for token in ("ADD", "UPDATE", "DEPRECATE", "EDGE_BUILD"):
        assert token in r.stdout, r.stdout


def test_KG_TC_002_dry_run_does_not_modify_kg(tmp_path):
    """KG-SC-002: --dry-run 不修改 knowledge-graph.yaml（hash 不变）"""
    proj = _project(tmp_path, sources={_SKILL_MD: "- FIN-THR-005: 新规则\n"})
    gp = graph_path(proj)
    before = _sha(gp)
    sync(proj, dry_run=True)
    assert _sha(gp) == before


def test_KG_TC_003_full_sync_updates_kg_and_writes_diff(tmp_path):
    """KG-SC-001: 完整 sync → KG 原地更新 + diff_kg.yaml 生成"""
    proj = _project(tmp_path, sources={_SKILL_MD: "- FIN-THR-005: 新规则\n"})
    sync(proj, dry_run=False)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-005")
    assert node is not None
    assert node.get("first_seen_at")
    assert diff_path(proj).exists()


# ============================================================
# REQ 2: ADD
# ============================================================
def test_KG_TC_004_add_node_with_first_seen_at(tmp_path):
    """KG-SC-005: 新 ID → ADD node + first_seen_at"""
    proj = _project(tmp_path, sources={_SKILL_MD: "- FIN-THR-005: 新规则\n"})
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-005")
    assert node is not None
    assert node["first_seen_at"]


def test_KG_TC_005_source_files_multi_hit(tmp_path):
    """KG-SC-006: 新 ID 多文件命中 → source_files 列表 ≥2"""
    proj = _project(tmp_path, sources={
        _SKILL_MD: "- FIN-THR-006: 规则 A\n",
        _FIN_MD: "- FIN-THR-006: 规则 A 复述\n",
    })
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-006")
    assert len(node["source_files"]) >= 2


# ============================================================
# REQ 3: UPDATE / SKIP
# ============================================================
def test_KG_TC_006_update_changed_description(tmp_path):
    """KG-SC-009: 同 ID 描述变 → UPDATE description"""
    proj = _project(
        tmp_path,
        nodes=[_node("FIN-THR-001", description="旧描述", source_files=[_FIN_MD])],
        sources={_FIN_MD: "- FIN-THR-001: 新描述\n"},
    )
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-001")
    assert node["description"] == "新描述"


def test_KG_TC_007_skip_unchanged_last_synced_kept(tmp_path):
    """KG-SC-010: 字段未变 → SKIP，last_synced_at 不变"""
    old_ts = "2020-01-01T00:00:00+00:00"
    proj = _project(
        tmp_path,
        nodes=[_node("FIN-THR-001", description="保持描述",
                     source_files=[_FIN_MD], last_synced_at=old_ts)],
        sources={_FIN_MD: "- FIN-THR-001: 保持描述\n"},
    )
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-001")
    assert node["last_synced_at"] == old_ts


# ============================================================
# REQ 4: DEPRECATE
# ============================================================
def test_KG_TC_008_disappeared_sets_last_removed(tmp_path):
    """KG-SC-011: 源码消失 → 写 last_removed_at"""
    proj = _project(
        tmp_path,
        nodes=[_node("FIN-FAIL-008", source_files=[".fstdd/skills/gone.md"])],
    )
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-FAIL-008")
    assert node.get("last_removed_at")


def test_KG_TC_009_removed_29_days_not_deprecated(tmp_path):
    """KG-SC-012: 消失 29 天 → deprecated 不为 true"""
    proj = _project(
        tmp_path,
        nodes=[_node("FIN-FAIL-008", source_files=[".fstdd/skills/gone.md"],
                     last_removed_at=_iso(29))],
    )
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-FAIL-008")
    assert node.get("deprecated") is not True


def test_KG_TC_010_removed_31_days_deprecated(tmp_path):
    """KG-SC-013: 消失 31 天 → deprecated=true"""
    proj = _project(
        tmp_path,
        nodes=[_node("FIN-FAIL-008", source_files=[".fstdd/skills/gone.md"],
                     last_removed_at=_iso(31))],
    )
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-FAIL-008")
    assert node.get("deprecated") is True


def test_KG_TC_011_reactivated_clears_deprecated(tmp_path):
    """KG-SC-014: deprecated 节点重现 → deprecated=false + 清 last_removed_at"""
    proj = _project(
        tmp_path,
        nodes=[_node("FIN-FAIL-009", deprecated=True,
                     last_removed_at=_iso(40), source_files=[_SKILL_MD])],
        sources={_SKILL_MD: "- FIN-FAIL-009: 回归\n"},
    )
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-FAIL-009")
    assert node.get("deprecated") is False
    assert "last_removed_at" not in node


# ============================================================
# REQ 5: BUILD_EDGES
# ============================================================
def test_KG_TC_012_cooccurrence_ge_threshold_builds_edge(tmp_path):
    """KG-SC-015: 共现 ≥2 次 → edge 入 diff_kg.yaml"""
    pair_doc = "- FIN-THR-001 / FIN-THR-002: 组合\n- FIN-THR-002 & FIN-THR-001: 组合\n"
    proj = _project(tmp_path, sources={_FIN_MD: pair_doc})
    sync(proj)
    diff = yaml.safe_load(diff_path(proj).read_text(encoding="utf-8"))
    pairs = {tuple(sorted((e["from"], e["to"]))) for e in diff.get("edges", [])}
    assert ("FIN-THR-001", "FIN-THR-002") in pairs


def test_KG_TC_013_cooccurrence_below_threshold_no_edge(tmp_path):
    """KG-SC-017: 共现 <2 次 → 不建 edge"""
    proj = _project(tmp_path, sources={_FIN_MD: "- FIN-THR-001 / FIN-THR-002: 仅一次\n"})
    sync(proj)
    diff = yaml.safe_load(diff_path(proj).read_text(encoding="utf-8"))
    assert diff.get("edges", []) == []


def test_KG_TC_014_new_edge_not_in_main_graph(tmp_path):
    """KG-SC-018: 新 edge 默认不入主 knowledge-graph.yaml"""
    pair_doc = "- FIN-THR-001 / FIN-THR-002: a\n- FIN-THR-002 & FIN-THR-001: b\n"
    proj = _project(tmp_path, sources={_FIN_MD: pair_doc})
    sync(proj)
    main = load_graph(graph_path(proj))
    assert main.get("edges", []) == []


# ============================================================
# REQ 7/8/9/10: 幂等 + 覆盖 + dry-run + 增量
# ============================================================
def test_KG_TC_015_second_sync_is_idempotent(tmp_path):
    """KG-SC-021: 第二次 sync → ADD 0 / UPDATE 0 / EDGE_BUILD 0"""
    pair_doc = "- FIN-THR-001 / FIN-THR-002: a\n- FIN-THR-002 & FIN-THR-001: b\n"
    proj = _project(tmp_path, sources={_FIN_MD: pair_doc + "- FIN-THR-005: 新\n"})
    sync(proj)
    second = sync(proj)
    assert second["add"] == 0
    assert second["update"] == 0
    assert second["edge_build"] == 0


def test_KG_TC_016_scan_covers_five_targets(tmp_path):
    """KG-SC-022: 扫描文件覆盖 5 类目录"""
    proj = _project(tmp_path)
    rels = [f.relative_to(proj).as_posix() for f in iter_scan_files(proj)]
    for target in SCAN_TARGETS:
        assert any(r.startswith(target + "/") for r in rels), target


def test_KG_TC_017_dry_run_hash_identical_to_backup(tmp_path):
    """KG-SC-023: --dry-run 后 KG hash 与备份完全一致"""
    proj = _project(tmp_path, sources={_SKILL_MD: "- FIN-THR-005: x\n"})
    gp = graph_path(proj)
    backup = gp.read_bytes()
    sync(proj, dry_run=True)
    assert gp.read_bytes() == backup


def test_KG_TC_018_first_sync_all_nodes_have_first_seen(tmp_path):
    """KG-SC-019: 首次 sync → 所有 node 有 first_seen_at"""
    nodes = [_node("KG-001"), _node("KG-002"), _node("FIN-THR-001")]
    proj = _project(tmp_path, nodes=nodes, sources={_SKILL_MD: "- KG-001: 说明\n"})
    sync(proj)
    graph = load_graph(graph_path(proj))
    missing = [n["id"] for n in graph["nodes"] if not n.get("first_seen_at")]
    assert missing == []


def test_KG_TC_019_edge_schema_upgraded(tmp_path):
    """KG-SC-020: 旧 edge {from,to} → 升级为 {from,to,type,last_synced_at}"""
    proj = _project(tmp_path, edges=[{"from": "KG-001", "to": "KG-002"}])
    sync(proj)
    edges = load_graph(graph_path(proj))["edges"]
    assert edges
    for e in edges:
        assert set(e.keys()) == {"from", "to", "type", "last_synced_at"}


def test_KG_TC_020_edge_threshold_flag(tmp_path):
    """KG-SC-003: --edge-threshold 3 生效（共现 2 次不建 edge）"""
    pair_doc = "- FIN-THR-001 / FIN-THR-002: a\n- FIN-THR-002 & FIN-THR-001: b\n"
    proj = _project(tmp_path, sources={_FIN_MD: pair_doc})
    sync(proj, edge_threshold=3)
    diff = yaml.safe_load(diff_path(proj).read_text(encoding="utf-8"))
    assert diff.get("edges", []) == []


def test_KG_TC_021_deep_scan_recurses(tmp_path):
    """KG-SC-004: --deep 递归扫描子目录"""
    proj = _project(tmp_path)
    deep_file = proj / ".fstdd" / "skills" / "sub" / "deep.md"
    deep_file.parent.mkdir(parents=True, exist_ok=True)
    deep_file.write_text("- FIN-THR-007: 深层引用\n", encoding="utf-8")

    shallow = [f.name for f in iter_scan_files(proj, deep=False)]
    assert "deep.md" not in shallow
    deep = [f.name for f in iter_scan_files(proj, deep=True)]
    assert "deep.md" in deep


def test_KG_TC_022_backtick_reference_accepted(tmp_path):
    """KG-SC-007: 反引号引用格式 → 接受为真引用（ADD node）"""
    proj = _project(tmp_path, sources={_SKILL_MD: "见 `FIN-THR-010` 规则\n"})
    sync(proj)
    assert _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-010") is not None


def test_KG_TC_023_incidental_id_severity_medium(tmp_path):
    """KG-SC-008: 偶然出现的 ID → severity=medium（不自动升 high）"""
    proj = _project(tmp_path, sources={_SKILL_MD: "这里随便提到 FIN-THR-011 而已\n"})
    sync(proj)
    node = _get_node(load_graph(graph_path(proj))["nodes"], "FIN-THR-011")
    assert node["severity"] == "medium"


def test_KG_TC_024_existing_edge_not_duplicated(tmp_path):
    """KG-SC-016: 同 pair 已存在 → 不重复建 edge"""
    pair_doc = "- FIN-THR-001 / FIN-THR-002: a\n- FIN-THR-002 & FIN-THR-001: b\n"
    proj = _project(tmp_path, sources={_FIN_MD: pair_doc})
    sync(proj)
    sync(proj)
    diff = yaml.safe_load(diff_path(proj).read_text(encoding="utf-8"))
    pairs = [tuple(sorted((e["from"], e["to"]))) for e in diff.get("edges", [])]
    assert pairs.count(("FIN-THR-001", "FIN-THR-002")) == 1