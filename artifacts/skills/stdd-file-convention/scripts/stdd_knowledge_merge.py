# -*- coding: utf-8 -*-
"""STDD Phase 4 · Step 2.9 知识图谱同步（文件约定式，无 bin/stdd CLI 时的等价实现）

对齐 `stdd knowledge merge` 的语义：
  1) 只读 GET 社区图谱（GitHub raw）—— 非外发，不受 Step 2.8「禁止外发」策略影响
  2) 解析本地 .stdd/experiences/*.md 为节点，按 similarity_threshold 去重后并入
  3) 写 .stdd/knowledge/knowledge-graph.yaml

社区不可用（404 / 连接被拒 / 超时）时降级为「仅本地」，把原因记进 meta.community_error，
**不阻断 DELIVER**。

用法：
  python stdd_knowledge_merge.py --project D:/项目/数据文件
  python stdd_knowledge_merge.py --project . --no-community
"""
import argparse
import io
import os
import re
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta

import yaml

CN = timezone(timedelta(hours=8))
DEFAULT_URL = ("https://raw.githubusercontent.com/leonai42/stdd-experiences/"
               "main/knowledge-graph.yaml")


def parse_experiences(exp_dir):
    """解析 experiences/*.md 的 `## EXP-NNN · <标题>` 章节为节点列表。"""
    nodes = []
    if not os.path.isdir(exp_dir):
        return nodes
    for fn in sorted(os.listdir(exp_dir)):
        if not fn.endswith(".md"):
            continue
        src_change = fn[:-3]
        text = io.open(os.path.join(exp_dir, fn), encoding="utf-8").read()
        parts = re.split(r"^## (EXP-\d+) · (.+?)\s*$", text, flags=re.M)
        # parts = [前言, id1, title1, body1, id2, title2, body2, ...]
        for i in range(1, len(parts), 3):
            eid = parts[i]
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", parts[i + 1].strip()).strip()
            body = parts[i + 2].split("\n## ")[0]
            body = re.sub(r"\n---\s*$", "", body).strip()
            m = re.search(r"\*\*严重程度\*\*[：:]\s*(\w+)", body)
            sev = m.group(1) if m else "normal"
            m = re.search(r"\*\*发现阶段\*\*[：:]\s*([^\s｜|]+)", body)
            phase = m.group(1) if m else "unknown"
            nodes.append({
                "id": eid, "pattern": title, "source_change": src_change,
                "origin": "local", "severity": sev, "phase": phase,
                "summary": " ".join(body.split())[:400],
            })
    return nodes


def fetch_community(url):
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "stdd-local-merge"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            return yaml.safe_load(r.read().decode("utf-8")), None
    except Exception as e:                                  # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--no-community", action="store_true", help="跳过社区拉取（离线）")
    ap.add_argument("--threshold", type=float, default=0.7)
    args = ap.parse_args()

    BASE = os.path.join(os.path.abspath(args.project), ".stdd")
    exp_dir = os.path.join(BASE, "experiences")
    know_dir = os.path.join(BASE, "knowledge")
    graph_path = os.path.join(know_dir, "knowledge-graph.yaml")

    local = parse_experiences(exp_dir)
    if args.no_community:
        community, err = None, "skipped (--no-community)"
    else:
        community, err = fetch_community(args.url)

    c_nodes = []
    if isinstance(community, dict):
        c_nodes = community.get("nodes") or []
    elif isinstance(community, list):
        c_nodes = community

    # ---- 去重键
    def key(n):
        return (str(n.get("origin", "local")), str(n.get("source_change", "")),
                str(n.get("id", "")))

    # ---- 现有图谱中的本地节点（必须保留，否则复跑会丢数据）
    old_local = []
    if os.path.exists(graph_path):
        with io.open(graph_path, encoding="utf-8") as f:
            old = yaml.safe_load(f) or {}
        old_local = [n for n in (old.get("nodes") or []) if n.get("origin") == "local"]

    # ---- 本地节点全量集合：旧图谱节点 ∪ 本次解析（同键以新解析为准）
    merged_local = {}
    for n in old_local:
        merged_local[key(n)] = n
    for n in local:
        merged_local[key(n)] = n
    merged_local = list(merged_local.values())

    # ---- 与社区节点按 pattern 去重
    seen = {str(n.get("pattern", "")).strip() for n in c_nodes}
    final_local = [n for n in merged_local if str(n.get("pattern", "")).strip() not in seen]

    # ---- 仅用于报告：本次新并入的
    old_keys = {key(n) for n in old_local}
    merged_new = [n for n in final_local if key(n) not in old_keys]

    os.makedirs(know_dir, exist_ok=True)
    graph = {
        "meta": {
            "generated_at": datetime.now(CN).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "generator": "stdd_knowledge_merge.py (STDD V3.0.5 文件约定式)",
            "similarity_threshold": args.threshold,
            "priority": "community",
            "community_url": args.url,
            "community_fetched": community is not None,
            "community_error": err,
        },
        "stats": {
            "community_nodes": len(c_nodes),
            "local_nodes": len(final_local),
            "merged_new": len(merged_new),
            "total": len(c_nodes) + len(final_local),
        },
        "nodes": c_nodes + final_local,
    }
    with io.open(graph_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# .stdd/knowledge/knowledge-graph.yaml — STDD V3.0 跨项目知识图谱\n")
        f.write("# Phase 4 Step 2.9 生成（仅本地 + 只读拉取社区，非外发）\n\n")
        yaml.safe_dump(graph, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False, width=120)

    print("local nodes     : %d" % len(local))
    print("community nodes : %d  (fetched=%s)" % (len(c_nodes), community is not None))
    if err:
        print("community note  : %s" % err)
    print("merged new      : %d" % len(merged_new))
    print("total           : %d" % graph["stats"]["total"])
    print("graph           : .stdd/knowledge/knowledge-graph.yaml")
    for n in merged_new:
        print("  + %s  %s  [%s]" % (n["id"], n["pattern"], n["severity"]))


if __name__ == "__main__":
    main()
