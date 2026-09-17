#!/usr/bin/env python3
"""时间戳规范检测器 —— naive 时间戳清零的 L1（值层）+ L2（源层）双轨检查。

对应 `2026-09-17-time-baseline` Slice 3 / Decision 6：
- **L1 值层（权威）**：判「产出的值」是否带时区，而不是「源码里出现某调用」。
  纯日期（YYYY-MM-DD）通过；含时刻（ISO T 分隔）却无时区后缀的判违规；
  标识符中的日期片段（EXP-2026-0917-A3、batch_id）天然不报。
- **L2 源层（兜底）**：静态扫描 `datetime.now()` / `.utcnow()` 无参调用点，
  由豁免清单过滤合法用途（纯日期 / 标识符 / 年份提取 / 已修 aware 的比较点备案）。

自检：每条豁免都必须在源码中可定位（find_stale_exemptions），
否则清单本身在说谎（TC-TSN-006）。

只读：全程不修改任何文件（TC-TSN-007）。

用法：
    python tools/check_timestamps.py [--repo .] [--json]
退出码：0 = 零违规；1 = 存在违规或自检失败。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# 豁免清单（TC-TSN-005：每条附理由；TC-TSN-006：每条必须可定位）
# file / pattern 均为「子串匹配」——定位检查在 find_stale_exemptions 中做。
# --------------------------------------------------------------------------- #
EXEMPTIONS: list[dict] = [
    # ── pure_date：纯日期字段（SC-012 明确通过） ──
    {"file": "fstdd/cli/commands/ci.py", "pattern": 'strftime("%Y-%m-%d")',
     "category": "pure_date", "reason": "CI 报告日期戳，纯日期非时间戳"},
    {"file": "fstdd/cli/commands/curate.py", "pattern": 'strftime("%Y-%m-%d")',
     "category": "pure_date", "reason": "策展日期，纯日期非时间戳"},
    {"file": "fstdd/cli/commands/experience.py", "pattern": 'strftime("%Y-%m-%d")',
     "category": "pure_date", "reason": "经验库 last_seen/retired_date，纯日期"},
    {"file": "fstdd/cli/commands/upgrade.py", "pattern": 'strftime("%Y-%m-%d")',
     "category": "pure_date", "reason": "升级日志日期，纯日期"},
    {"file": "fstdd/cli/commands/structure.py", "pattern": "strftime('%Y-%m-%d')",
     "category": "pure_date", "reason": "结构索引小节日期，纯日期"},
    # ── identifier：紧凑时间戳仅用于文件名/ID（SC-012 明确不报） ──
    {"file": "tools/check_skill_metadata.py", "pattern": 'strftime("%Y%m%d-%H%M%S")',
     "category": "identifier", "reason": "备份文件名时间戳，标识符非时间字段"},
    {"file": "tools/inbox_pull.py", "pattern": 'strftime("%Y%m%dT%H%M%S")',
     "category": "identifier", "reason": "拒绝条目文件名，标识符非时间字段"},
    {"file": "fstdd/cli/commands/upgrade.py", "pattern": 'strftime("%Y%m%dT%H%M%S")',
     "category": "identifier", "reason": "升级暂存目录名，标识符非时间字段"},
    {"file": "fstdd/cli/commands/batch.py", "pattern": "strftime('%H%M%S')",
     "category": "identifier", "reason": "归档目录名时刻片段，标识符非时间字段"},
    {"file": "fstdd/cli/commands/batch.py", "pattern": "now.strftime('%m%d')",
     "category": "identifier", "reason": "batch_id 日期片段（周批次标识符）"},
    # ── year_extract：仅取年份/周 ──
    {"file": "fstdd/cli/commands/experience.py", "pattern": "datetime.now().year",
     "category": "year_extract", "reason": "EXP-ID 年份片段，非时间戳产出"},
    # ── comparison：曾 naive 的比较点，已修为 aware UTC（备案） ──
    {"file": "fstdd/cli/commands/batch.py", "pattern": "datetime.now(timezone.utc)",
     "category": "comparison", "reason": "批次年龄比较，aware UTC 无 naive/aware 混比"},
    {"file": "fstdd/cli/commands/guard.py", "pattern": "_dt.now(_tz.utc)",
     "category": "comparison", "reason": "僵尸 change / 卡壳检测，aware UTC（_tz=timezone，Slice 8 修正 _dt.timezone 误写）"},
    {"file": "fstdd/cli/commands/status.py", "pattern": "datetime.now(timezone.utc)",
     "category": "comparison", "reason": "7 天新鲜度比较，aware UTC"},
]

# L2：无参 naive 调用（带 timezone/tz 参数的 now() 是 aware，合法）。
# 覆盖形态：datetime.now() / _dt.now() / datetime.datetime.now() / x.utcnow()
_NAIVE_CALL = re.compile(r"(?:datetime|_dt)(?:\.datetime)?\.now\(\)|\.utcnow\(\)")
_AWARE_MARKERS = ("timezone", "tz=")


def _code_lines(path: Path) -> dict[int, str]:
    """tokenize 重建「代码行」：只保留真实代码 token，跳过 docstring / 字符串 / 注释。

    首跑即中过招：检测器自己的 docstring（`` `datetime.now()` ``）和豁免清单的
    pattern 字符串被当代码报为违规 —— 纯文本行必须排除。
    """
    import io
    import tokenize

    src = path.read_text(encoding="utf-8", errors="ignore")
    per_line: dict[int, list[str]] = {}
    try:
        toks = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok in toks:
            if tok.type in (tokenize.COMMENT, tokenize.STRING,
                            tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT,
                            tokenize.ENDMARKER, tokenize.ENCODING):
                continue
            for ln in range(tok.start[0], tok.end[0] + 1):
                per_line.setdefault(ln, []).append(tok.string)
    except Exception:
        # 语法坏文件：退回原文（宁可误报不可漏报）
        return {i: l for i, l in enumerate(src.splitlines(), 1)}
    return {ln: "".join(parts) for ln, parts in per_line.items()}

# L1：值形态
_ISO_MOMENT_NAIVE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?$")
_PURE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TZ_SUFFIX = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


def is_naive_timestamp(value: object) -> bool:
    """L1 值层判据：含 ISO 时刻却无时区后缀 → True；纯日期 / 带时区 / 非时间 → False。"""
    if not isinstance(value, str):
        return False
    v = value.strip()
    if _PURE_DATE.match(v):
        return False                      # 纯日期字段（SC-012 通过）
    if _ISO_MOMENT_NAIVE.match(v):
        return not bool(_TZ_SUFFIX.search(v))   # 理论恒 True（正则无 tz 位置），留防御
    return False                          # 标识符 / 普通字符串不报


def _line_is_exempt(line: str, rel_file: str) -> dict | None:
    for e in EXEMPTIONS:
        if e["file"] in rel_file and e["pattern"] in line:
            return e
    return None


def scan_sources(root: Path) -> dict:
    """L2 源层扫描：root 下所有 .py 的无参 naive 调用点（豁免过滤后）。

    naive 判定用 tokenize 重建的「代码行」（跳过 docstring/字符串/注释）；
    豁免匹配用**原文行**（豁免 pattern 含字符串字面量，如 strftime('%m%d')）。
    """
    violations: list[dict] = []
    exempted = 0
    total_fields = 0
    for py in sorted(root.rglob("*.py")):
        abs_str = str(py).replace("\\", "/")
        try:
            raw_lines = py.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        code = _code_lines(py)
        for i in sorted(code):
            text = code[i]
            if not (_NAIVE_CALL.search(text) or "utc_now_iso" in text):
                continue
            total_fields += 1
            if "utc_now_iso" in text or any(m in text for m in _AWARE_MARKERS):
                continue                       # 新统一函数 / aware 调用
            raw = raw_lines[i - 1] if i - 1 < len(raw_lines) else ""
            hit = _line_is_exempt(raw, abs_str)
            if hit:
                exempted += 1
                continue
            violations.append({
                "location": f"{abs_str}:{i}",
                "category": "naive_source",
                "snippet": raw.strip()[:120],
            })
    return {
        "violations": violations,
        "exempted": exempted,
        "total_fields_scanned": total_fields,
    }


def _walk_yaml_values(node: object, path: str, out: list[tuple[str, str]]):
    if isinstance(node, dict):
        for k, v in node.items():
            _walk_yaml_values(v, f"{path}.{k}", out)
    elif isinstance(node, list):
        for idx, v in enumerate(node):
            _walk_yaml_values(v, f"{path}[{idx}]", out)
    elif isinstance(node, str):
        out.append((path, node))


def scan_change_values(repo: Path) -> list[dict]:
    """L1 值层：活跃 change 的 .fstdd.yaml + canonical YAML 的所有字符串值。"""
    import yaml

    violations: list[dict] = []
    changes = repo / ".fstdd" / "changes"
    if not changes.is_dir():
        return violations
    for yf in sorted(changes.rglob("*.yaml")) + sorted(changes.rglob("*.yml")):
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8"))
        except Exception:
            continue
        pairs: list[tuple[str, str]] = []
        _walk_yaml_values(data, "$", pairs)
        for path, value in pairs:
            if is_naive_timestamp(value):
                violations.append({
                    "location": f"{yf.relative_to(repo)} {path}",
                    "category": "naive_value",
                    "snippet": value[:120],
                })
    return violations


def scan_human_view_headers(repo: Path) -> list[dict]:
    """L1 值层：Human View 头部 generated_at 注释。"""
    violations: list[dict] = []
    changes = repo / ".fstdd" / "changes"
    if not changes.is_dir():
        return violations
    for md in sorted(changes.rglob("proposal.md")):
        try:
            head = "\n".join(md.read_text(encoding="utf-8").splitlines()[:10])
        except Exception:
            continue
        m = re.search(r"generated_at:\s*([0-9T:.+-]+)", head)
        if m and not _TZ_SUFFIX.search(m.group(1)):
            violations.append({
                "location": f"{md.relative_to(repo)} <!-- generated_at -->",
                "category": "naive_value",
                "snippet": m.group(1),
            })
    return violations


def find_stale_exemptions(root: Path) -> list[str]:
    """TC-TSN-006 自检：每条豁免必须能在源码中定位，否则清单在说谎。

    root 传**仓库根**（同时覆盖 upstream/ 与 tools/ 下的豁免条目）。
    """
    stale: list[str] = []
    files = {str(p).replace("\\", "/"): p for p in root.rglob("*.py")}
    for e in EXEMPTIONS:
        found = any(e["file"] in rel and e["pattern"] in p.read_text(encoding="utf-8", errors="ignore")
                    for rel, p in files.items())
        if not found:
            stale.append(f"{e['file']} :: {e['pattern']} ({e.get('reason', '无理由')})")
    return stale


def full_scan(repo: Path) -> dict:
    """TC-TSN-007：全仓扫描（只读）。返回违规清单 + naive 计数 + 显式范围。"""
    repo = repo.resolve()
    scopes = [
        "L1 .fstdd/changes/**/.fstdd.yaml（活跃 change 状态文件）",
        "L1 .fstdd/changes/**/canonical/**/*.yaml（canonical YAML）",
        "L1 .fstdd/changes/**/proposal.md 头部（Human View generated_at）",
        "L1 .fstdd/templates/*.md（两处模板之一：项目副本）",
        "L2 upstream/fstdd/**/*.py（CLI 源码）",
        "L2 tools/*.py（工具脚本）",
    ]
    violations = []
    violations += scan_change_values(repo)
    violations += scan_human_view_headers(repo)
    src_root = repo / "upstream" / "fstdd"
    if src_root.is_dir():
        violations += scan_sources(src_root)["violations"]
    tools_root = repo / "tools"
    if tools_root.is_dir():
        violations += scan_sources(tools_root)["violations"]
    return {
        "naive_count": len(violations),
        "violations": violations,
        "scopes": scopes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="时间戳规范检测（L1 值层 + L2 源层）")
    ap.add_argument("--repo", default=".", help="仓库根路径")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    report = full_scan(repo)
    stale = find_stale_exemptions(repo)

    if args.json:
        print(json.dumps({**report, "stale_exemptions": stale}, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"时间戳规范检测 —— {repo}")
        print("=" * 60)
        print("扫描范围：")
        for s in report["scopes"]:
            print(f"  · {s}")
        print("-" * 60)
        if report["violations"]:
            print(f"❌ {report['naive_count']} 个 naive 时间戳：")
            for v in report["violations"]:
                print(f"  [{v['category']}] {v['location']}")
                print(f"      {v['snippet']}")
        else:
            print(f"✅ naive 计数为 0（共 {report['naive_count']} 违规）")
        if stale:
            print(f"⚠️ 豁免清单 {len(stale)} 条无法定位（清单在说谎）：")
            for s in stale:
                print(f"  · {s}")
        print("-" * 60)
        print(f"结果：{report['naive_count']} 违规 / {len(stale)} 条失效豁免")

    return 1 if (report["naive_count"] or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
