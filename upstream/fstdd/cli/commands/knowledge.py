"""V3.0: 跨项目知识图谱 — merge / query / predict / fix."""
import argparse
import sys
import os
import json
import re
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from ..timeutil import utc_now_iso
from difflib import SequenceMatcher
from typing import Optional

import yaml
import requests

from .experience import _coerce_numeric_fields, _iter_experience_files


VALID_NODE_TYPES = {"failure_pattern", "design_decision", "fix_template", "language_idiom"}
VALID_EDGE_TYPES = {"causes", "prevented_by", "refines", "appears_in"}


def _get_knowledge_dir(project_root: Path) -> Path:
    from ..utils import read_config
    config = read_config(project_root)
    kconfig = config.get("knowledge", {})
    return project_root / kconfig.get("dir", ".fstdd/knowledge")


def _get_graph_path(project_root: Path) -> Path:
    return _get_knowledge_dir(project_root) / "knowledge-graph.yaml"


def _load_graph(graph_path: Path) -> dict:
    if not graph_path.exists():
        return _empty_graph()
    with open(graph_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or _empty_graph()


def _empty_graph() -> dict:
    return {
        "graph_version": "1.0",
        "last_merged": "",
        "nodes": [],
        "edges": [],
    }


def _save_graph(graph_path: Path, graph: dict) -> None:
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph["last_merged"] = utc_now_iso(timespec="seconds")
    with open(graph_path, "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True, default_flow_style=False)


def _text_similarity(a: str, b: str) -> float:
    """Calculate text similarity (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _next_node_id(graph: dict) -> str:
    """Generate next KG-{NNN} node ID."""
    max_id = 0
    for node in graph.get("nodes", []):
        nid = node.get("id", "")
        match = re.match(r"KG-(\d+)", nid)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"KG-{max_id + 1:03d}"


def _load_experiences(exp_dir: Path) -> list[dict]:
    """Load all non-retired experiences from project."""
    experiences = []
    if not exp_dir.exists():
        return experiences
    for exp_file in _iter_experience_files(exp_dir):
        content = exp_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        data = _coerce_numeric_fields(yaml.safe_load(parts[1]) or {})
        state = data.get("lifecycle_state", "discovered")
        if state in ("deposited", "shared", "merged"):
            data["_file"] = str(exp_file)
            experiences.append(data)
    return experiences


def _exp_to_node(exp: dict, node_id: str, project_name: str) -> dict:
    """Convert an experience to a knowledge graph node."""
    category = exp.get("category", "")
    pattern = exp.get("pattern", "")
    root_cause = exp.get("root_cause", "")
    severity = exp.get("severity", "medium")
    tags = exp.get("tags", [])
    fix_template = exp.get("fix_template", "")

    node = {
        "id": node_id,
        "type": "failure_pattern",
        "title": pattern[:80] if pattern else category,
        "description": pattern,
        "cross_project_count": 1,
        "projects": [project_name],
        "tags": tags,
        "category": category,
        "root_cause": root_cause,
        "fix_template_refs": [],
        "severity": severity,
        "metrics": {
            "occurrence_count": exp.get("occurrences", 1),
            "severity_trend": "stable",
            "last_seen": exp.get("last_seen", ""),
        },
    }

    # If fix_template is non-empty, create a linked fix_template node
    if fix_template:
        fix_id = f"{node_id}-FIX"
        node["fix_template_refs"] = [fix_id]

    return node


def _fetch_community_graph(config: dict) -> Optional[dict]:
    """Fetch knowledge-graph.yaml from community git repo. Returns None on failure.

    Project policy (DKK_Fstdd): experience/knowledge must stay within our own
    repos. The upstream default pointed at the third-party
    `leonai42/stdd-experiences`; that default is gone. An empty/unset `repo`
    means "no community source" and returns immediately — otherwise a blank
    value would fall through to the `gh` clone below and still reach out.
    """
    community = config.get("community", {})
    repo = (community.get("repo") or "").strip()
    if not repo:
        return None
    graph_path_in_repo = community.get("graph_path", "knowledge-graph.yaml")
    timeout = community.get("timeout", 30)

    # Try GitHub API first (fast, no clone needed)
    try:
        url = f"https://raw.githubusercontent.com/{repo}/main/{graph_path_in_repo}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return yaml.safe_load(resp.text) or _empty_graph()
    except Exception:
        pass

    # Fallback: gh CLI
    import shutil
    if shutil.which("gh"):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                r = subprocess.run(
                    ["gh", "repo", "clone", repo, str(tmp / "repo"), "--depth", "1"],
                    capture_output=True, text=True, timeout=60,
                )
                if r.returncode != 0:
                    return None
                graph_file = tmp / "repo" / graph_path_in_repo
                if graph_file.exists():
                    return yaml.safe_load(graph_file.read_text(encoding="utf-8")) or _empty_graph()
        except Exception:
            pass

    return None


# ─── CLI subcommands ───


def cmd_knowledge_merge(args: argparse.Namespace) -> None:
    """Merge community knowledge graph with local experiences."""
    from ..utils import get_logger, read_config
    logger = get_logger()
    project_root = Path.cwd()
    config = read_config(project_root)
    kconfig = config.get("knowledge", {})
    similarity_threshold = kconfig.get("merge", {}).get("similarity_threshold", 0.7)

    graph_path = _get_graph_path(project_root)
    graph = _load_graph(graph_path)

    # 1. Fetch community graph
    community_graph = _fetch_community_graph(config)
    if community_graph:
        print("  社区图谱已拉取")
        # Merge community nodes into local (community nodes override if same ID)
        comm_nodes = {n["id"]: n for n in community_graph.get("nodes", []) if n.get("id")}
        local_nodes = {n["id"]: n for n in graph.get("nodes", []) if n.get("id")}
        # Community nodes that don't exist locally are added
        new_from_comm = 0
        for nid, node in comm_nodes.items():
            if nid not in local_nodes:
                graph.setdefault("nodes", []).append(node)
                new_from_comm += 1
        if new_from_comm > 0:
            print(f"  从社区导入 {new_from_comm} 个新节点")
    else:
        print("  社区图谱不可用，仅生成本地图谱")

    # 2. Scan local experiences
    exp_dir = project_root / ".fstdd" / "experiences"
    experiences = _load_experiences(exp_dir)
    if not experiences:
        print("  本地无待合并经验")
        _save_graph(graph_path, graph)
        return

    proj_cfg = config.get("project", {})
    project_name = proj_cfg.get("name", project_root.name)
    existing_nodes = list(graph.get("nodes", []))
    new_count = 0
    update_count = 0

    for exp in experiences:
        pattern = exp.get("pattern", "")
        # Check for similar existing node
        found = False
        for node in existing_nodes:
            node_pattern = node.get("title", "")
            if _text_similarity(pattern, node_pattern) >= similarity_threshold:
                # Update existing node
                node["cross_project_count"] = node.get("cross_project_count", 0) + 1
                projs = node.get("projects", [])
                if project_name not in projs:
                    projs.append(project_name)
                node["projects"] = projs
                metrics = node.get("metrics", {})
                metrics["occurrence_count"] = metrics.get("occurrence_count", 0) + exp.get("occurrences", 1)
                metrics["last_seen"] = exp.get("last_seen", "")
                node["metrics"] = metrics
                update_count += 1
                found = True
                break

        if not found:
            # Create new node
            node_id = _next_node_id(graph)
            node = _exp_to_node(exp, node_id, project_name)
            graph.setdefault("nodes", []).append(node)
            new_count += 1

    _save_graph(graph_path, graph)
    total = len(graph.get("nodes", []))
    print(f"  知识图谱已更新：+{new_count} 节点，~{update_count} 更新（总计 {total} 节点）")


def cmd_knowledge_query(args: argparse.Namespace) -> None:
    """Query the knowledge graph by keyword."""
    graph_path = _get_graph_path(Path.cwd())
    graph = _load_graph(graph_path)

    keyword = getattr(args, "keyword_or_id", "") or getattr(args, "keyword", "")
    show_related = getattr(args, "related", False)
    fmt = getattr(args, "format", "table")

    if not graph.get("nodes"):
        if fmt == "json":
            print(json.dumps([], ensure_ascii=False))
        else:
            print("  知识图谱为空。运行 'stdd knowledge merge' 创建图谱。")
        return

    # Search nodes
    results = []
    kw = keyword.lower()
    for node in graph.get("nodes", []):
        score = 0.0
        search_text = " ".join([
            node.get("title", ""),
            node.get("description", ""),
            node.get("root_cause", ""),
            " ".join(node.get("tags", [])),
        ]).lower()
        if kw in search_text:
            score = 1.0
            # Boost by exact title match
            if kw in node.get("title", "").lower():
                score += 2.0
        if score > 0:
            results.append({"node": node, "score": score})

    if show_related and results:
        # Also include nodes connected by edges
        result_ids = {r["node"]["id"] for r in results}
        related = []
        for edge in graph.get("edges", []):
            if edge.get("from") in result_ids or edge.get("to") in result_ids:
                related.append(edge)
        results.append({"_related_edges": related})

    results.sort(key=lambda r: r.get("score", 0) if "node" in r else 0, reverse=True)

    if fmt == "json":
        output = []
        for r in results:
            if "node" in r:
                n = r["node"]
                output.append({
                    "id": n.get("id"), "type": n.get("type"), "title": n.get("title"),
                    "cross_project_count": n.get("cross_project_count", 0),
                    "fix_success_rate": n.get("success_rate") if n.get("type") == "fix_template" else None,
                    "severity": n.get("severity"),
                    "projects": n.get("projects", []),
                    "score": r["score"],
                })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        node_results = [r for r in results if "node" in r]
        if not node_results:
            print("  无匹配结果")
            return
        print(f"\n  关键词 '{keyword}' 匹配 {len(node_results)} 个节点:\n")
        for r in node_results[:20]:
            n = r["node"]
            proj_count = n.get("cross_project_count", 0)
            sev = n.get("severity", "?")
            projs = ", ".join(n.get("projects", [])[:3])
            print(f"  {n['id']} [{n.get('type', '?')}] (score: {r['score']:.1f})")
            print(f"    标题: {n.get('title', '')[:100]}")
            print(f"    跨项目: {proj_count} 次 / 项目: {projs}")
            if n.get("type") == "fix_template":
                print(f"    成功率: {n.get('success_rate', 0)*100:.0f}%")
            print()


def cmd_knowledge_predict(args: argparse.Namespace) -> None:
    """Predict risks for a given change based on knowledge graph."""
    from ..utils import read_config
    graph_path = _get_graph_path(Path.cwd())
    graph = _load_graph(graph_path)
    config = read_config(Path.cwd())
    kconfig = config.get("knowledge", {})
    min_matches = kconfig.get("predict", {}).get("min_matches", 3)
    top_k = kconfig.get("predict", {}).get("top_k", 5)

    change_name = getattr(args, "change_name", "")
    if not change_name:
        print("  请指定 change 名称: stdd knowledge predict <change>")
        return

    # Extract features from current change
    # Simplified: use node categories as features
    nodes = graph.get("nodes", [])
    if len(nodes) < min_matches:
        import sys as _sys
        print(f"  ⚠️ 数据不足（仅 {len(nodes)} 个节点，最少需要 {min_matches}），预测仅供参考", file=_sys.stderr)

    # Score nodes by severity × occurrence_count
    scored = []
    for node in nodes:
        if node.get("type") != "failure_pattern":
            continue
        sev_weight = {"high": 3, "medium": 2, "low": 1}.get(node.get("severity", "medium"), 2)
        occ = node.get("metrics", {}).get("occurrence_count", 1)
        proj_count = node.get("cross_project_count", 0)
        score = sev_weight * occ * (1 + proj_count * 0.5)
        confidence = "高" if proj_count >= 5 else ("中" if proj_count >= 3 else "低")
        scored.append({"node": node, "score": score, "confidence": confidence})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]

    if not top:
        print("  无可用预测数据")
        return

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        output = [{
            "id": s["node"]["id"], "title": s["node"]["title"],
            "severity": s["node"].get("severity"),
            "cross_project_count": s["node"].get("cross_project_count", 0),
            "score": round(s["score"], 1), "confidence": s["confidence"],
        } for s in top]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n  🔮 风险预测 Top {len(top)}（Change: {change_name}）:\n")
        for i, s in enumerate(top, 1):
            n = s["node"]
            print(f"  {i}. [{s['confidence']}置信] {n.get('id', '')} {n.get('title', '')[:80]}")
            print(f"     严重程度: {n.get('severity', '?')} | 跨项目出现: {n.get('cross_project_count', 0)} 次")
            root = n.get("root_cause", "")
            if root:
                print(f"     根因: {root[:100]}")
            print()


def cmd_knowledge_fix(args: argparse.Namespace) -> None:
    """Find fix templates for a given experience ID."""
    graph_path = _get_graph_path(Path.cwd())
    graph = _load_graph(graph_path)

    exp_id = getattr(args, "experience_id", "")
    if not exp_id:
        print("  请指定经验 ID: stdd knowledge fix <EXP-ID>")
        return

    # Find the node matching this experience ID
    # Experience IDs are like EXP-2026-0001, nodes are like KG-001
    # We match by searching for the experience pattern in node descriptions
    # First, try to load the actual experience to get its pattern
    exp_dir = Path.cwd() / ".fstdd" / "experiences"
    exp_pattern = ""
    exp_file = exp_dir / f"{exp_id}.md"
    if exp_file.exists():
        content = exp_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) >= 3:
            exp_data = _coerce_numeric_fields(yaml.safe_load(parts[1]) or {})
            exp_pattern = exp_data.get("pattern", "")

    # Search nodes for matching pattern
    target_node = None
    for node in graph.get("nodes", []):
        if exp_pattern and _text_similarity(exp_pattern, node.get("title", "")) >= 0.6:
            target_node = node
            break

    if not target_node:
        # Fallback: search by exp_id in node projects
        for node in graph.get("nodes", []):
            if exp_id in str(node.get("projects", [])) or exp_id in node.get("description", ""):
                target_node = node
                break

    if not target_node:
        print(f"  该经验（{exp_id}）在知识图谱中暂无记录。运行 'stdd knowledge merge' 同步。")
        return

    fix_refs = target_node.get("fix_template_refs", [])
    if not fix_refs:
        print(f"  该经验暂无跨项目修复模板。")
        return

    # Find fix templates
    fix_nodes = []
    for node in graph.get("nodes", []):
        if node.get("id") in fix_refs and node.get("type") == "fix_template":
            fix_nodes.append(node)

    if not fix_nodes:
        print("  关联的修复模板未找到。")
        return

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        output = [{
            "id": n["id"], "steps": n.get("steps", []),
            "success_rate": n.get("success_rate", 0),
            "total_applications": n.get("total_applications", 0),
        } for n in fix_nodes]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n  🔧 {exp_id} 的修复模板:\n")
        for n in fix_nodes:
            rate = n.get("success_rate", 0) * 100
            apps = n.get("total_applications", 0)
            print(f"  {n['id']}: {n.get('title', '')}")
            print(f"  成功率: {rate:.0f}%（{apps} 次应用）")
            steps = n.get("steps", [])
            if steps:
                for j, step in enumerate(steps, 1):
                    print(f"    {j}. {step}")
            print()


# ─── Main dispatcher ───


def cmd_knowledge(args: argparse.Namespace) -> None:
    from ..utils import get_logger
    get_logger()

    subcommand = getattr(args, "subcommand", "query")

    if subcommand == "merge":
        cmd_knowledge_merge(args)
    elif subcommand == "query":
        cmd_knowledge_query(args)
    elif subcommand == "predict":
        cmd_knowledge_predict(args)
    elif subcommand == "fix":
        cmd_knowledge_fix(args)
    else:
        print(f"  未知子命令: {subcommand}")
        print("  可用: merge, query, predict, fix")
        sys.exit(1)
