# -*- coding: utf-8 -*-
"""把归档活表 remap 到当前实况行号，产出本 change 的 audit/except-points.yaml。

策略：按 (file, stmt, handler) 指纹分组，同组内按行号顺序一一配对；
既有的 id / classification / severity / response / detection_path / justification
原样承接（本次 change 未改变这些点的语义，只改变了行号）。
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
OLD = REPO / ".fstdd" / "archive" / "2026-10-12-canon-merge-command" / "audit" / "except-points.yaml"
NEW = REPO / ".fstdd" / "changes" / "2026-10-21-installation-id-prefix" / "audit" / "except-points.yaml"
LIVE_JSON = Path(sys.argv[1])


def fp(d: dict) -> tuple:
    return (str(d.get("file", "")), str(d.get("stmt", "")).strip(), str(d.get("handler", "")).strip())


def main() -> int:
    live = json.loads(LIVE_JSON.read_text(encoding="utf-8"))
    old = yaml.safe_load(OLD.read_text(encoding="utf-8"))
    old_points = old["points"]

    live_groups: dict = defaultdict(list)
    for p in live:
        live_groups[fp(p)].append(int(p["line"]))
    for k in live_groups:
        live_groups[k].sort()

    old_groups: dict = defaultdict(list)
    for i, p in enumerate(old_points):
        old_groups[fp(p)].append(i)

    # 指纹多重性必须一致
    only_live = {k: len(v) for k, v in live_groups.items()
                 if len(v) != len(old_groups.get(k, []))}
    if only_live:
        print("FINGERPRINT_MISMATCH:", json.dumps(
            {str(k): v for k, v in only_live.items()}, ensure_ascii=False, indent=2))
        return 2

    # 逐个指纹按顺序配对
    new_points = [dict(p) for p in old_points]
    for k, idxs in old_groups.items():
        lines = live_groups[k]
        for pos, idx in enumerate(idxs):
            old_line = int(new_points[idx].get("line", 0))
            new_line = lines[pos]
            if old_line != new_line:
                new_points[idx]["line"] = new_line
                new_points[idx]["line_shifted_from"] = old_line

    new = {
        "meta": {
            "title": "全仓裸 except 吞异常点审计表（活表）",
            "change": "2026-10-21-installation-id-prefix",
            "refreshed_from": "2026-10-12-canon-merge-command",
            "observed_at": "2026-10-22T03:55:00+00:00",
            "observed_base_git_sha": "a48942065c907045da8444a89e1ef24c14d480af",
            "scanner": "tools/audit_silent_except.py",
            "refreshed_at": "2026-10-22T11:55:00+08:00",
            "refreshed_reason": (
                "2026-10-21 change installation-id-prefix 刷新：承接归档活表 25 点。"
                "本 change 在 upstream/fstdd/cli/commands/init.py 新增 _generate_installation_id / "
                "_get_prefix / _ensure_installation_id 及 _post_init_self_check 的 installation_id 断言，"
                "并在 experience.py 新增 _read_installation_id + 改造 _next_id；"
                "新增代码一律使用具体异常（OSError / yaml.YAMLError / TypeError），"
                "**新增 0 个吞异常点**。既有 4 处 except Exception: 因 init.py 头部插入约 70 行而整体下移，"
                "本表已按指纹 remap 对齐（continue 200→278，pass 385→463）。"
                "合计 25 点，与实况扫描零漂移。"
            ),
            "total": len(new_points),
            "by_classification": {
                cls: sum(1 for p in new_points if p.get("classification") == cls)
                for cls in sorted({p.get("classification") for p in new_points})
            },
            "note": (
                "活表：置于 active change 下由本 change 维护；归档表不动。"
                "零漂移校验以 (file, stmt, handler) 指纹 + 出现序号为准（±5 行容差）。"
            ),
        },
        "points": new_points,
    }

    NEW.parent.mkdir(parents=True, exist_ok=True)
    NEW.write_text(
        yaml.safe_dump(new, allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8",
    )
    shifted = sum(1 for p in new_points if "line_shifted_from" in p)
    print(f"OK total={len(new_points)} shifted={shifted} -> {NEW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
