#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FSTDD 经验库审计基线脚本 (P0-pre · Phase 1.1)
==============================================
用途：在真实仓库上量化经验库元数据失真，产出修复前基线 audit JSON。

只读脚本：不修改仓库任何文件。输出写到 --out 指定路径（默认当前目录）。

审计逻辑：
  1. 扫描 <repo>/.fstdd/experiences/*.md，提取全部 YAML frontmatter 块；
  2. 模拟现有解析器行为（experience.py:428 只取第一个块）→ current_view；
  3. 取最后一个块作为真实元数据 → true_view；
  4. 逐文件比对 REQUIRED_META 字段（experience_id/category/severity）；
     真身块锚定 = 含 experience_id 的最后一个块（经 GitHub 镜像 master 实读验证：
     inbox 导入文件为 注释+导出块+注释+真身块 的三段式多块结构）；
  5. 汇总：双块结构数、受影响条目数、逐字段丢失数、分类分布偏差（current vs true）；
  6. 与 .experience-index.yaml 对账（索引中有无该文件条目）。

退出码：0=审计完成；2=仓库路径无效或 experiences 目录不存在。

无第三方依赖（ deliberate：仓库默认解释器缺 yaml，本脚本必须开箱可跑 ）。
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_META = ["experience_id", "category", "severity"]
EXPORT_MARKERS = ("exported_at", "sanitized")  # 导出块特征键

FM_BLOCK_RE = re.compile(r"^---[ \t]*\n(.*?)^---[ \t]*$", re.M | re.S)
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", re.M)


def extract_blocks(text: str):
    """返回 [(block_index, raw_text, key_list)]，按出现顺序。
    按 '---' 分隔线切段：相邻 frontmatter 块共享一条分隔线，
    切段后第 1/3/5... 段即为块内容（自测实证 toggle 法会吞块）。
    已知限制：正文中的 '---' 水平线会干扰切段；经验库文件格式受控，可接受。"""
    segs, cur = [], []
    for ln in text.splitlines(keepends=True):
        if ln.strip() == "---":
            segs.append("".join(cur))
            cur = []
        else:
            cur.append(ln)
    segs.append("".join(cur))
    blocks = []
    for s in segs[1:]:  # segs[0] = 块前导（注释/空）
        if not s.strip():
            continue
        keys = TOP_LEVEL_KEY_RE.findall(s)
        if not keys:
            break  # 首个无键段 = 正文，frontmatter 区到此为止
        blocks.append((len(blocks), s, keys))
    return blocks


def true_block(blocks):
    """锚定真身块：含 experience_id 键的最后一个块。
    真实 inbox 导入文件为 三段式（注释+导出块 / 注释 / 真身块，2026-10-10 经
    GitHub 镜像 master 实读验证），且正文可能出现列首 '键: 值' 行——
    若简单取 blocks[-1]，正文会把真身块挤掉。找不到 experience_id 时回退末块。"""
    for _, raw, keys in reversed(blocks):
        if "experience_id" in keys:
            return raw, keys
    return blocks[-1][1], blocks[-1][2]


def classify(first_keys, last_keys, nblocks):
    """返回 (structure, missing_current, recovered_by_last)。"""
    has_export_marker = any(k in first_keys for k in EXPORT_MARKERS)
    if nblocks >= 2 and has_export_marker:
        structure = "dual_block_import"
    elif has_export_marker:
        structure = "exported_block_only"   # 导出块在，真身块缺失
    elif nblocks == 1:
        structure = "single_block"
    else:
        structure = f"multi_block_{nblocks}"
    missing_current = [k for k in REQUIRED_META if k not in first_keys]
    recovered = [k for k in missing_current if k in last_keys]
    return structure, missing_current, recovered


#: 索引项形态：`by_category:` / `by_lifecycle:` 下的**裸列表项** `- <eid>`
#: （2026-10-10 实测：真实 .experience-index.yaml 中 `experience_id:` 出现 0 次，
#:  78 个条目全部是裸列表项，含 `EXP-` 与 `FSTDD005-` 两种前缀）
INDEX_ITEM_RE = re.compile(r"^\s*-\s*((?:[A-Za-z0-9]+-)?EXP-[\w.-]+)\s*$", re.M)
INDEX_KV_RE = re.compile(r"experience_id\s*:\s*['\"]?([\w.-]+)")


def load_index_keys(index_path: Path):
    """返回索引中登记的 eid 集合；索引文件不存在返回 None。

    ⚠️ 2026-10-10 修复（评审阻塞项 B1）：原实现只匹配 `experience_id: <id>` 形态，
    对真实索引命中 **0** 条 ⇒ `indexed_true` 恒 0、全部条目被误判「未入索引」（假阳性洪泛）。
    现优先按**裸列表项**解析（真实形态），无命中时回退 `experience_id:` 形态（兼容合成/旧索引）。
    """
    if not index_path.exists():
        return None
    text = index_path.read_text(encoding="utf-8", errors="replace")
    keys = set(INDEX_ITEM_RE.findall(text))
    if not keys:
        keys = set(INDEX_KV_RE.findall(text))
    return keys


def main() -> int:
    ap = argparse.ArgumentParser(description="FSTDD experience audit baseline")
    ap.add_argument("--repo", required=True, help="stdd-repo 根目录路径")
    ap.add_argument("--out", default="audit-2026-10-experience-baseline.json",
                    help="审计 JSON 输出路径（默认当前目录）")
    args = ap.parse_args()

    repo = Path(args.repo)
    exp_dir = repo / ".fstdd" / "experiences"
    if not exp_dir.is_dir():
        print(f"[FATAL] experiences 目录不存在: {exp_dir}", file=sys.stderr)
        return 2

    index_keys = load_index_keys(exp_dir / ".experience-index.yaml")
    files = sorted(p for p in exp_dir.glob("*.md") if p.is_file())

    records, field_loss = [], {k: 0 for k in REQUIRED_META}
    cat_current, cat_true = {}, {}
    eid_mismatch_files = []
    n_dual = n_affected = 0

    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        blocks = extract_blocks(text)
        if not blocks:
            # ⚠️ 2026-10-10 修复（评审发现）：原先该分支只写 3 个键，与 design §4 schema 不符，
            # 且因缺 `in_index` 键而被索引对账**静默排除**（既不进 true 也不进 false）。
            # 现补全 schema 键，并以 in_index="unreconciled" 显式归类为第三类。
            records.append({"file": f.name, "structure": "no_frontmatter", "n_blocks": 0,
                            "true_eid": None, "filename_stem": f.stem, "eid_match": None,
                            "first_block_keys": [], "last_block_keys": [],
                            "missing_current": REQUIRED_META[:],
                            "recovered_by_last_block": [],
                            "in_index": "unreconciled"})
            n_affected += 1
            for k in REQUIRED_META:
                field_loss[k] += 1
            continue
        first_keys = blocks[0][2]
        last_raw, last_keys = true_block(blocks)
        structure, missing, recovered = classify(first_keys, last_keys, len(blocks))
        if structure == "dual_block_import":
            n_dual += 1
        if missing:
            n_affected += 1
            for k in missing:
                field_loss[k] += 1
        # 分类分布：current=现有解析器视角, true=最后一块视角
        def _cat(keys, raw):
            m = re.search(r"^category\s*:\s*['\"]?([^'\"\n]+)", raw, re.M)
            return m.group(1).strip() if m else None
        m_eid = re.search(r"^experience_id\s*:\s*['\"]?([\w.-]+)", last_raw, re.M)
        rec_eid = m_eid.group(1) if m_eid else None
        cc, tc = _cat(first_keys, blocks[0][1]), _cat(last_keys, last_raw)
        if cc:
            cat_current[cc] = cat_current.get(cc, 0) + 1
        if tc:
            cat_true[tc] = cat_true.get(tc, 0) + 1
        eid_match = (rec_eid == f.stem) if rec_eid else None
        if eid_match is False:
            eid_mismatch_files.append(f.name)
        rec = {"file": f.name, "structure": structure, "n_blocks": len(blocks),
               "true_eid": rec_eid, "filename_stem": f.stem, "eid_match": eid_match,
               "first_block_keys": first_keys, "last_block_keys": last_keys,
               "missing_current": missing,
               "recovered_by_last_block": recovered,
               "in_index": (rec_eid in index_keys) if (index_keys is not None and rec_eid) else
                          ("index_missing" if index_keys is None else False)}
        records.append(rec)

    affected_files = [r["file"] for r in records if r.get("missing_current")]
    report = {
        "audit_meta": {
            "tool": "audit_experience_baseline.py",
            "repo": str(repo),
            "audited_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "git_head": _git_head(repo),
            "note": "current_view 模拟 experience.py:428 只取首块；true_view=末块",
        },
        "summary": {
            "total_entries": len(files),
            "dual_block_entries": n_dual,
            "affected_entries": n_affected,
            "affected_ratio": round(n_affected / len(files), 4) if files else 0,
            "field_loss_counts": field_loss,
            "category_distribution_current_parser": dict(sorted(cat_current.items())),
            "category_distribution_true": dict(sorted(cat_true.items())),
            "eid_mismatch": {"count": len(eid_mismatch_files), "files": eid_mismatch_files},
            "index_reconciliation": _index_recon(records),
        },
        "affected_files": affected_files,
        "records": records,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                              encoding="utf-8", newline="\n")
    s = report["summary"]
    print(f"[OK] 审计完成: {s['affected_entries']}/{s['total_entries']} 条目受影响 "
          f"({s['affected_ratio']:.1%})，双块结构 {s['dual_block_entries']} 条")
    print(f"[OK] 字段丢失: {s['field_loss_counts']}")
    print(f"[OK] 输出: {args.out}")
    return 0


def _git_head(repo: Path):
    """返回仓库 HEAD 提交号；git 缺失/超时/非 git 仓库时返回 None（不得中断审计）。

    注：此处**刻意收窄**异常类型（而非 `except Exception`）—— `git` 不可用/超时
    由 OSError / SubprocessError 覆盖已足够；宽捕获会被本仓裸 except 审计判为未登记吞异常点。
    """
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _index_recon(records):
    """索引对账（四桶 + 不变式）。

    2026-10-10 修复（评审发现）：原实现只统计 `in_index is True/False` 两桶，
    导致 `no_frontmatter` 记录（无 `in_index` 键）被**静默排除** —— 报告无法被读作
    「全部条目已对账」。现补 `unreconciled_files` / `index_missing_count` 两桶，
    并输出 `invariant_ok` 供回归断言：
        indexed_true + len(indexed_false) + len(unreconciled) + index_missing_count == total
    """
    total = sum(1 for r in records if r.get("in_index") is True)
    missing = [r["file"] for r in records if r.get("in_index") is False]
    unreconciled = [r["file"] for r in records if r.get("in_index") == "unreconciled"]
    index_missing_count = sum(1 for r in records if r.get("in_index") == "index_missing")
    accounted = total + len(missing) + len(unreconciled) + index_missing_count
    return {
        "indexed_true": total,
        "indexed_false_files": missing,
        "eid_mismatch_files": [r["file"] for r in records if r.get("eid_match") is False],
        "unreconciled_files": unreconciled,
        "index_missing_count": index_missing_count,
        "invariant_ok": accounted == len(records),
    }


if __name__ == "__main__":
    sys.exit(main())
