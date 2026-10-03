"""KG 自动同步器 — 扫描源码 → re-index 知识图谱（V3.1.1）。

用途（2026-10-03-caveman-kg-sync / Slice 2）：
    源码（skill / template）会引用知识图谱的节点 ID（如 ``FIN-THR-001``）。
    当源码新增、改动或删除这些引用时，知识图谱需要随之更新：
      * ADD       — 源码里出现 KG 尚无的 ID → 追加 node
      * UPDATE    — 同 ID 描述变化 → 覆盖 description + last_synced_at
      * DEPRECATE — 曾在源码出现、现在消失 → 写 last_removed_at；>30 天 → deprecated
      * BUILD_EDGES — 同文档内共现 ≥阈值 的 ID 对 → 写入 diff_kg.yaml（默认不入主文件）

设计约束：
    * 幂等：连续跑两次，第二次 ADD/UPDATE/DEPRECATE/EDGE_BUILD 全为 0
    * --dry-run 绝对安全：不写任何文件
    * 与 caveman 压缩器无耦合（互不 import）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from datetime import datetime, timezone

import yaml

from .cli.timeutil import utc_now_iso


# ── 常量 ──────────────────────────────────────────────────────────────

# 节点 ID 形态：KG-001 / FIN-THR-005 / FIN-FAIL-008 / ANY-PREFIX-123
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,7}(?:-[A-Z0-9]{2,6}){1,3}-\d{2,3}\b")

# 排除 FSTDD 追溯/文档类 ID（TC-XXX-001 / SC-001 / REQ-001 …）——
# 它们与 ID_RE 同形，但并非知识图谱节点；过滤首段以防噪声节点（KG-REQ-002 缓解）。
RESERVED_PREFIXES = frozenset({
    "TC", "SC", "REQ", "AC", "NFR", "FR", "EXP", "EA", "DG", "ST",
    "TASK", "BUG", "US", "ADR", "PR", "EPIC", "ISSUE", "CAVE", "KGSC",
})

DEFAULT_EDGE_THRESHOLD = 2
DEPRECATE_AFTER_DAYS = 30
GRAPH_VERSION = "1.2"

# KG-REQ-008：scan_targets 必须覆盖的 5 类目录
SCAN_TARGETS = [
    ".fstdd/skills",
    "skills/fstdd-fin",
    ".fstdd/templates",
    "upstream/.fstdd/skills",
    "upstream/.fstdd/templates",
]

# 从 ID / 上下文文本推断 node type（KG-SC-005）
TYPE_KEYWORDS = [
    ("fix_template", ("fix", "repair", "修复")),
    ("design_decision", ("decision", "决策", "design")),
    ("language_idiom", ("idiom", "惯用")),
    ("failure_pattern", ("fail", "failure", "失败", "error", "错误", "thr", "threshold")),
]

# 从上下文文本推断 severity（默认 medium，不自动升 high；KG-SC-008）
SEVERITY_KEYWORDS = [
    ("high", ("severity: high", "severity: critical", "critical", "严重", "致命")),
    ("low", ("severity: low", "severity: minor", "minor")),
]

_DEFAULT_TYPE = "failure_pattern"
_DEFAULT_SEVERITY = "medium"


# ── 路径 ──────────────────────────────────────────────────────────────


def graph_path(project_root: Path) -> Path:
    return Path(project_root) / ".fstdd" / "knowledge" / "knowledge-graph.yaml"


def diff_path(project_root: Path) -> Path:
    return Path(project_root) / ".fstdd" / "knowledge" / "diff_kg.yaml"


# ── 存取 ──────────────────────────────────────────────────────────────


def load_graph(path: Path) -> dict:
    if not Path(path).exists():
        return _empty_graph()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    data.setdefault("nodes", [])
    data.setdefault("edges", [])
    return data


def save_graph(path: Path, graph: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(graph, allow_unicode=True, default_flow_style=False, sort_keys=True),
        encoding="utf-8",
    )


def _empty_graph() -> dict:
    return {"graph_version": GRAPH_VERSION, "last_merged": "", "nodes": [], "edges": []}


def load_diff(path: Path) -> dict:
    if not Path(path).exists():
        return {"edges": []}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    data.setdefault("edges", [])
    return data


def save_diff(path: Path, diff: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(diff, allow_unicode=True, default_flow_style=False, sort_keys=True),
        encoding="utf-8",
    )


# ── 扫描 ──────────────────────────────────────────────────────────────


def iter_scan_files(project_root: Path, deep: bool = False) -> list[Path]:
    """返回 SCAN_TARGETS 下存在的源码文件（默认只扫一层，--deep 递归）。"""
    project_root = Path(project_root)
    files: list[Path] = []
    for rel in SCAN_TARGETS:
        d = project_root / rel
        if not d.is_dir():
            continue
        pattern = "**/*.md" if deep else "*.md"
        for f in sorted(d.glob(pattern)):
            if f.is_file() and f not in files:
                files.append(f)
    return files


def _scan(project_root: Path, deep: bool = False):
    """扫描全部文件，返回 (id→文件集, id→描述, 每文件的共现计数, 命中文件列表)。"""
    id_files: dict[str, set[str]] = {}
    id_desc: dict[str, str] = {}
    pair_counts: dict[tuple[str, str], int] = {}

    for f in iter_scan_files(project_root, deep=deep):
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(project_root).as_posix()
        file_pairs: dict[tuple[str, str], int] = {}

        for line in text.splitlines():
            ids = [
                i for i in ID_RE.findall(line)
                if i.split("-", 1)[0] not in RESERVED_PREFIXES
            ]
            if not ids:
                continue
            for nid in ids:
                id_files.setdefault(nid, set()).add(rel)
                if nid not in id_desc:
                    id_desc[nid] = _describe(line, nid)
            uniq = sorted(set(ids))
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    key = (uniq[i], uniq[j])
                    file_pairs[key] = file_pairs.get(key, 0) + 1

        # 同文档内共现：取每个 file 内的计数，跨文件取最大值
        for key, cnt in file_pairs.items():
            pair_counts[key] = max(pair_counts.get(key, 0), cnt)

    return id_files, id_desc, pair_counts


def _describe(line: str, nid: str) -> str:
    """从命中的行里抽取该 ID 后的描述文本（去掉 markdown/yaml 引用符号）。"""
    idx = line.rfind(nid)
    after = line[idx + len(nid):] if idx >= 0 else ""
    after = after.strip().lstrip(":`-*\u3001\t ：").strip()
    if not after:
        after = line.strip().lstrip("`-* ").strip()
    return after[:200]


def _infer_type(nid: str, desc: str) -> str:
    hay = f"{nid} {desc}".lower()
    for type_name, kws in TYPE_KEYWORDS:
        if any(kw in hay for kw in kws):
            return type_name
    return _DEFAULT_TYPE


def _infer_severity(desc: str) -> str:
    low = desc.lower()
    for sev, kws in SEVERITY_KEYWORDS:
        if any(kw in low for kw in kws):
            return sev
    return _DEFAULT_SEVERITY


def _parse_ts(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ── 同步引擎 ──────────────────────────────────────────────────────────


def sync(
    project_root: Path,
    dry_run: bool = False,
    deep: bool = False,
    edge_threshold: int = DEFAULT_EDGE_THRESHOLD,
    full: bool = False,
) -> dict:
    """执行一次 KG 同步。返回统计 dict（含 add/update/deprecate/edge_build）。

    ``full`` 目前为占位开关：本实现始终全量扫描（结果集与增量一致）；
    增量优化（git diff）留待后续 change，已在 design-adjustments 记录。
    """
    project_root = Path(project_root)
    gpath = graph_path(project_root)
    graph = load_graph(gpath)
    nodes: list[dict] = graph.get("nodes", [])
    by_id = {n.get("id"): n for n in nodes if n.get("id")}

    now = utc_now_iso()
    id_files, id_desc, pair_counts = _scan(project_root, deep=deep)

    add = update = deprecate = 0

    # 首次/增量：为所有 node 注入 5 字段（KG-SC-019）
    for node in nodes:
        if not node.get("first_seen_at"):
            node["first_seen_at"] = now
        if not node.get("last_synced_at"):
            node["last_synced_at"] = now
        node.setdefault("source_files", [])
        node.setdefault("deprecated", False)

    # ADD / UPDATE / 复活
    for nid in sorted(id_files):
        node = by_id.get(nid)
        files = sorted(id_files[nid])
        desc = id_desc.get(nid, "")
        if node is None:
            node = {
                "id": nid,
                "type": _infer_type(nid, desc),
                "title": desc or nid,
                "description": desc,
                "severity": _infer_severity(desc),
                "source_files": files,
                "first_seen_at": now,
                "last_synced_at": now,
                "deprecated": False,
            }
            nodes.append(node)
            by_id[nid] = node
            add += 1
            continue

        changed = False
        if node.get("deprecated") or "last_removed_at" in node:
            # 复活：deprecated=false + 清 last_removed_at（KG-SC-014）
            node["deprecated"] = False
            node.pop("last_removed_at", None)
            changed = True
        merged_sources = sorted(set(node.get("source_files", [])) | set(files))
        if merged_sources != node.get("source_files"):
            node["source_files"] = merged_sources
            changed = True
        if desc and desc != node.get("description", ""):
            node["description"] = desc
            changed = True
        if changed:
            node["last_synced_at"] = now
            update += 1
        # 未变 → SKIP（last_synced_at 保持原值，KG-SC-010）

    # DEPRECATE：曾 tracked（有 source_files）但本次扫描消失
    for node in nodes:
        nid = node.get("id")
        if not nid or nid in id_files:
            continue
        if not node.get("source_files"):
            continue  # 从未在源码中出现过 → 不参与废弃判定
        if "last_removed_at" not in node:
            node["last_removed_at"] = now
            deprecate += 1
        ts = _parse_ts(node.get("last_removed_at", ""))
        if ts and (datetime.now(timezone.utc) - ts).days > DEPRECATE_AFTER_DAYS:
            node["deprecated"] = True

    # BUILD_EDGES：共现 ≥阈值 → diff_kg.yaml（默认不入主文件，KG-SC-018）
    dp = diff_path(project_root)
    diff = load_diff(dp)
    existing = {
        (e.get("from"), e.get("to")): e
        for e in diff.get("edges", [])
        if e.get("from") and e.get("to")
    }
    edge_build = 0
    for (a, b), cnt in sorted(pair_counts.items()):
        if cnt < edge_threshold:
            continue
        if (a, b) in existing or (b, a) in existing:
            key = (a, b) if (a, b) in existing else (b, a)
            existing[key]["last_synced_at"] = now
            continue
        edge = {"from": a, "to": b, "type": "co-occurrence", "last_synced_at": now}
        diff.setdefault("edges", []).append(edge)
        existing[(a, b)] = edge
        edge_build += 1

    # edge schema 升级（KG-SC-020）：主图旧 edge 统一补齐 type + last_synced_at
    for edge in graph.get("edges", []):
        if edge.get("from") and edge.get("to"):
            edge.setdefault("type", "co-occurrence")
            edge.setdefault("last_synced_at", now)

    result = {
        "add": add,
        "update": update,
        "deprecate": deprecate,
        "edge_build": edge_build,
        "files_scanned": len(iter_scan_files(project_root, deep=deep)),
        "ids_found": len(id_files),
        "dry_run": dry_run,
    }

    if not dry_run:
        graph["graph_version"] = GRAPH_VERSION
        graph["last_merged"] = now
        save_graph(gpath, graph)
        save_diff(dp, diff)

    return result


# ── CLI ───────────────────────────────────────────────────────────────


def cmd_kg(args) -> None:
    subcommand = getattr(args, "subcommand", None)
    if subcommand not in (None, "sync"):
        print(f"  未知子命令: {subcommand}")
        print("  可用: sync")
        sys.exit(1)

    project_root = Path.cwd()
    dry_run = bool(getattr(args, "dry_run", False))
    result = sync(
        project_root,
        dry_run=dry_run,
        deep=bool(getattr(args, "deep", False)),
        edge_threshold=int(getattr(args, "edge_threshold", DEFAULT_EDGE_THRESHOLD)),
        full=bool(getattr(args, "full", False)),
    )

    mode = " (dry-run)" if dry_run else ""
    print(f"KG sync{mode}")
    print(f"  files scanned: {result['files_scanned']} / ids matched: {result['ids_found']}")
    print(
        f"  ADD {result['add']} / UPDATE {result['update']}"
        f" / DEPRECATE {result['deprecate']} / EDGE_BUILD {result['edge_build']}"
    )
    if dry_run:
        print("  (dry-run: knowledge-graph.yaml 与 diff_kg.yaml 未改动)")
    else:
        print(f"  → {graph_path(project_root)}")
        print(f"  → {diff_path(project_root)}")


def _dispatch(args) -> None:
    cmd_kg(args)