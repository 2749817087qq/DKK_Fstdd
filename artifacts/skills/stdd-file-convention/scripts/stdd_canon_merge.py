# -*- coding: utf-8 -*-
"""STDD Phase 4 · Step 2/2.5 规范合并（文件约定式，适用于无 bin/stdd CLI 的项目）

把已归档的 change 合并进项目级规范：
  A) Human View  : specs/<capability>/spec.md
  B) Canonical   : canonical/proposals/<date>-<change>.yaml
                   canonical/specs/<capability>.yaml
                   canonical/specs/agent/<capability>.yaml
  C) 索引        : .canon-index.yaml

用法：
  python stdd_canon_merge.py --project D:/项目/数据文件 --change kline_field_backfill
  python stdd_canon_merge.py --project . --change <id> --capability <cap> --date 2026-09-14

幂等：可重复执行（覆盖同名产物 + 按 change_id upsert 索引条目）。
"""
import argparse
import io
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

CN = timezone(timedelta(hours=8))


def now_iso():
    return datetime.now(CN).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def one_line(s):
    return " ".join(str(s or "").split())


def dump_yaml(path, obj, header):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False, width=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="项目根目录（含 .stdd/）")
    ap.add_argument("--change", required=True, help="change_id")
    ap.add_argument("--capability", default=None, help="capability 名（默认 = change_id）")
    ap.add_argument("--date", default=None, help="归档日期前缀 YYYY-MM-DD（默认自动探测）")
    ap.add_argument("--archive-dir", default=None, help="归档目录（默认自动探测）")
    args = ap.parse_args()

    ROOT = os.path.abspath(args.project)
    BASE = os.path.join(ROOT, ".stdd")
    CHANGE = args.change
    CAP = args.capability or CHANGE

    # ---- 定位归档目录
    arch = args.archive_dir
    if not arch:
        cands = [d for d in os.listdir(os.path.join(BASE, "archive"))
                 if d.endswith("-" + CHANGE) or d == CHANGE]
        if not cands:
            sys.exit("[FATAL] 找不到归档目录: .stdd/archive/*%s" % CHANGE)
        arch = os.path.join(BASE, "archive", sorted(cands)[-1])
    arch = os.path.abspath(arch)
    if not os.path.isdir(arch):
        sys.exit("[FATAL] 归档目录不存在: %s" % arch)

    # ---- 定位 spec.yaml（归档件优先，其次 changes/）
    spec_path = os.path.join(arch, "spec.yaml")
    if not os.path.exists(spec_path):
        alt = os.path.join(BASE, "changes", CHANGE, "spec.yaml")
        if not os.path.exists(alt):
            sys.exit("[FATAL] 找不到 spec.yaml: %s" % spec_path)
        spec_path = alt
    with io.open(spec_path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    DATE = args.date or str(spec.get("date") or os.path.basename(arch)[:10])
    MERGE_AT = now_iso()
    arch_rel = ".stdd/archive/" + os.path.basename(arch)

    # ---- 读 design-adjustments（可选）
    adj = {}
    adj_path = os.path.join(arch, "design-adjustments.yaml")
    if os.path.exists(adj_path):
        with io.open(adj_path, encoding="utf-8") as f:
            adj = yaml.safe_load(f) or {}

    # 归档内 .stdd.yaml（取 supersedes 等元信息）
    meta_yaml = {}
    my = os.path.join(arch, ".stdd.yaml")
    if os.path.exists(my):
        with io.open(my, encoding="utf-8") as f:
            meta_yaml = yaml.safe_load(f) or {}

    n_req = len(spec.get("requirements") or [])
    n_sc = sum(len(r.get("scenarios") or []) for r in (spec.get("requirements") or []))

    # =============================================== A) Human View
    L = []
    w = L.append
    w("# Spec: %s" % CAP)
    w("")
    w("> **%s**" % spec.get("title", ""))
    w("")
    w("| 项 | 值 |")
    w("|---|---|")
    w("| capability | `%s` |" % CAP)
    w("| change_id | `%s` |" % CHANGE)
    w("| task_type | `%s` |" % spec.get("task_type", "code"))
    w("| 源变更 | `%s`（已归档） |" % arch_rel)
    w("| 合并日期 | %s（STDD Phase 4 Step 2） |" % MERGE_AT[:10])
    w("| 规模 | %d Requirements / %d Scenarios |" % (n_req, n_sc))
    w("")
    if spec.get("artifacts"):
        w("## 0. 产物与常量")
        w("")
        w("| 键 | 值 |")
        w("|---|---|")
        for k, v in spec["artifacts"].items():
            w("| `%s` | `%s` |" % (k, v))
        w("")
        if spec.get("constants"):
            w("| 常量 | 值 |")
            w("|---|---|")
            for k, v in spec["constants"].items():
                w("| `%s` | `%s` |" % (k, v))
            w("")
    w("## 1. 需求清单")
    w("")
    for r in (spec.get("requirements") or []):
        w("### %s · %s" % (r["id"], r.get("title", "")))
        w("")
        w("> %s" % one_line(r.get("desc")))
        w("")
        w("- 置信度：`%s` ｜ 验证层级：`%s` ｜ 实现状态：`%s`"
          % (r.get("confidence"), r.get("test"), r.get("code")))
        w("")
        scs = r.get("scenarios") or []
        if scs:
            w("| Scenario | Given | When | Then | And | 证据 / 备注 |")
            w("|---|---|---|---|---|---|")
            for s in scs:
                w("| `%s` | %s | %s | %s | %s | %s |" % (
                    s["id"], one_line(s.get("given")), one_line(s.get("when")),
                    one_line(s.get("then")), "<br>".join(as_list(s.get("and"))),
                    one_line(s.get("evidence") or s.get("note"))))
        else:
            w("_（无 Scenario）_")
        w("")
    w("## 2. 变更历史")
    w("")
    w("| 日期 | change | 动作 |")
    w("|---|---|---|")
    w("| %s | `%s` | Gate 1/2/3 通过；Phase 3 实施 |" % (DATE, CHANGE))
    w("| %s | `%s` | 归档并合并进本文件（Phase 4 Step 2） |" % (MERGE_AT[:10], CHANGE))
    w("")

    hv_path = os.path.join(BASE, "specs", CAP, "spec.md")
    if os.path.exists(hv_path):
        print("[!] MODIFIED capability：specs/%s/spec.md 已存在，请人工确认合并增量 REQ" % CAP)
    os.makedirs(os.path.dirname(hv_path), exist_ok=True)
    with io.open(hv_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    print("[A] Human View     -> specs/%s/spec.md  (%d 行)" % (CAP, len(L)))

    # =============================================== B1) canonical spec
    canon_reqs = []
    for r in (spec.get("requirements") or []):
        scs = []
        for s in (r.get("scenarios") or []):
            item = {
                "id": s["id"],
                "confidence": s.get("confidence", r.get("confidence", "high")),
                "given": one_line(s.get("given")),
                "when": one_line(s.get("when")),
                "then": one_line(s.get("then")),
            }
            ands = as_list(s.get("and"))
            if ands:
                item["and"] = ands
            ev = s.get("evidence") or s.get("note")
            if ev:
                item["evidence"] = one_line(ev)
            scs.append(item)
        canon_reqs.append({
            "id": r["id"],
            "title": r.get("title", ""),
            "description": one_line(r.get("desc")),
            "confidence": r.get("confidence", "high"),
            "test": r.get("test", "unit"),
            "code": r.get("code", "to-implement"),
            "scenarios": scs,
        })

    canon_spec = {
        "meta": {
            "capability": CAP, "change_id": CHANGE, "created": DATE,
            "merged_at": MERGE_AT, "confidence": "high", "status": "archived",
            "task_type": spec.get("task_type", "code"),
            "source_change_path": arch_rel,
            "human_view": "specs/%s/spec.md" % CAP,
        },
        "artifacts": spec.get("artifacts"),
        "constants": spec.get("constants"),
        "requirements": canon_reqs,
    }
    dump_yaml(os.path.join(BASE, "canonical", "specs", "%s.yaml" % CAP), canon_spec,
              "# canonical/specs/%s.yaml — STDD Phase 4 Step 2 合并生成\n"
              "# 生成时间: %s ｜ 来源: %s/spec.yaml\n"
              "# Human View 见 specs/%s/spec.md\n\n" % (CAP, MERGE_AT, arch_rel, CAP))
    print("[B1] Canonical spec -> canonical/specs/%s.yaml" % CAP)

    # =============================================== B2) canonical proposal
    canon_proposal = {
        "meta": {
            "change_id": CHANGE,
            "title": spec.get("title", ""),
            "created": DATE,
            "archived_at": MERGE_AT,
            "status": "completed",
            "supersedes": meta_yaml.get("supersedes"),
        },
        "why": {"problem": "", "motivation": ""},   # ← 请从 proposal.md 补全
        "what_changes": [],
        "capabilities": {"new": [{"name": CAP, "description": spec.get("title", "")}], "modified": []},
        "constraints": [],
        "stakeholders": [],
        "risk_areas": [],
        "non_goals": [],
        "critical": {"is_critical": False,
                     "risk_assessment": {"safety_critical": False, "financial": False, "cross_system": False}},
        "anchoring": {"level": "L2", "reference_changes": [], "anchor_implementations": []},
        "success_criteria": [],
    }
    pp_path = os.path.join(BASE, "canonical", "proposals", "%s-%s.yaml" % (DATE, CHANGE))
    if os.path.exists(pp_path):
        with io.open(pp_path, encoding="utf-8") as f:
            canon_proposal = yaml.safe_load(f) or canon_proposal   # 保留已人工补全的内容
    dump_yaml(pp_path, canon_proposal,
              "# canonical/proposals/%s-%s.yaml — STDD Phase 4 Step 2 合并生成\n"
              "# 生成时间: %s\n"
              "# ⚠️ why / what_changes / constraints / success_criteria 需从 %s/proposal.md 补全\n\n"
              % (DATE, CHANGE, MERGE_AT, arch_rel))
    print("[B2] Canonical proposal -> canonical/proposals/%s-%s.yaml" % (DATE, CHANGE))

    # =============================================== B3) canonical agent_spec
    agent_path = os.path.join(BASE, "canonical", "specs", "agent", "%s.yaml" % CAP)
    if os.path.exists(agent_path):
        print("[B3] agent_spec 已存在，保留（不覆盖人工检查点）-> canonical/specs/agent/%s.yaml" % CAP)
    else:
        dump_yaml(agent_path, {
            "meta": {
                "task_id": CHANGE, "change_id": CHANGE,
                "task_type": spec.get("task_type", "code"),
                "system": "", "preconditions": [],
            },
            "steps": [
                {"id": "CP-1", "description": "测试套件全量通过",
                 "action": "<项目测试命令>",
                 "assertions": [{"type": "exit_code", "expected": 0},
                                {"type": "stdout_contains", "expected": "RESULT: PASS"}]},
                {"id": "CP-2", "description": "<端到端验证>",
                 "action": "<E2E 命令>",
                 "assertions": [{"type": "exit_code", "expected": 0}]},
            ],
            "rollback": {"steps": ["<回滚步骤，失败后由人工确认执行>"]},
            "evidence": {"archive": arch_rel},
        }, "# canonical/specs/agent/%s.yaml — STDD Phase 4 Step 2 生成\n"
           "# ⚠️ action / assertions 需按项目实际命令补全\n"
           "# 生成时间: %s\n\n" % (CAP, MERGE_AT))
        print("[B3] Canonical agent_spec -> canonical/specs/agent/%s.yaml（需补全 action）" % CAP)

    # =============================================== C) 索引
    idx_path = os.path.join(BASE, ".canon-index.yaml")
    if os.path.exists(idx_path):
        with io.open(idx_path, encoding="utf-8") as f:
            idx = yaml.safe_load(f) or {}
    else:
        idx = {}
    idx.setdefault("version", 1)
    idx["generated_at"] = MERGE_AT
    entries = [e for e in (idx.get("entries") or []) if e.get("change_id") != CHANGE]
    entries.append({
        "change_id": CHANGE, "capability": CAP, "status": "archived",
        "archive_path": arch_rel,
        "canonical_proposal": "canonical/proposals/%s-%s.yaml" % (DATE, CHANGE),
        "canonical_spec": "canonical/specs/%s.yaml" % CAP,
        "canonical_agent_spec": "canonical/specs/agent/%s.yaml" % CAP,
        "human_view_spec": "specs/%s/spec.md" % CAP,
        "requirements": n_req, "scenarios": n_sc,
        "design_adjustments": adj.get("total_adjustments", 0),
    })
    idx["entries"] = sorted(entries, key=lambda e: e.get("change_id", ""))
    with io.open(idx_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# .canon-index.yaml — STDD Canonical 双轨索引（Phase 4 Step 2 维护）\n\n")
        yaml.safe_dump(idx, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False, width=120)
    print("[C] Index          -> .canon-index.yaml  (entries=%d)" % len(idx["entries"]))

    # =============================================== 双轨一致性校验
    hv = io.open(hv_path, encoding="utf-8").read()
    hv_req = set(re.findall(r"^### (REQ-[0-9-]+)", hv, re.M))
    c_req = {r["id"] for r in canon_reqs}
    c_sc = {s["id"] for r in canon_reqs for s in r["scenarios"]}
    print("\n--- 双轨一致性校验 ---")
    print("REQ 集合相等 : %s  (canonical=%d, human=%d)" % (c_req == hv_req, len(c_req), len(hv_req)))
    print("SC  总数     : %d  （Human View 正则计数会因表格重复而偏大，比对集合）" % len(c_sc))
    if c_req != hv_req:
        print("!! REQ 集合不一致，请检查")
        sys.exit(2)
    print("\nDONE")


if __name__ == "__main__":
    main()
