"""fstdd extract-proposal — Extract structured data from proposal.md."""
import argparse
import sys
import re
import json
from pathlib import Path

import yaml

from ._proposal_anchors import (
    H2_WHY,
    H2_WHAT_CHANGES,
    H2_CAPABILITIES,
    H2_IMPACT,
    H2_CONSTRAINTS,
    H2_STAKEHOLDERS,
    H2_RISK_AREAS,
    H2_NON_GOALS,
    H2_SUCCESS_CRITERIA,
    H3_NEW_CAPABILITIES,
    H3_MODIFIED_CAPABILITIES,
    CAPABILITY_H3_ANCHORS,
    IMPACT_SECTIONS,
)


def _parse_section(content: str, heading: str, stop_headings: tuple = ()) -> list[str]:
    """Extract bullet list items from a markdown section.

    :param stop_headings: 额外的**截断标题**（h2/h3 均可）。用于 `what_changes`：
        历史形态下 `### New/Modified Capabilities` 落在 `## What Changes` 区间内
        （因当时缺 `## Capabilities` 父标题），必须在此截断，否则 capability 条目泄漏。
    """
    # Find the target heading and the next heading of same or higher level
    heading_pattern = rf"^##\s+{re.escape(heading)}\s*$"
    next_section_pattern = r"^##\s+"
    stop_patterns = [rf"^#{{2,3}}\s+{re.escape(h)}\s*$" for h in stop_headings]
    lines = content.split("\n")
    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if start is None:
            if re.match(heading_pattern, line):
                start = i + 1
            continue
        if re.match(next_section_pattern, line) or any(re.match(p, line) for p in stop_patterns):
            end = i
            break

    if start is None:
        return []

    section = "\n".join(lines[start:end])
    items = re.findall(r"^[ \t]*(?:-|\*)\s+(.+)", section, re.MULTILINE)
    return [item.strip() for item in items]


def _h2_body(content: str, heading: str) -> str | None:
    """返回 `## <heading>` 段的正文（不含标题行）；不存在时返回 None。"""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", content, re.MULTILINE)
    if not m:
        return None
    rest = content[m.end():]
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _h3_body(scope: str, heading: str) -> str:
    """返回 `### <heading>` 段的正文；不存在时返回空串。"""
    m = re.search(rf"^###\s+{re.escape(heading)}\s*$", scope, re.MULTILINE)
    if not m:
        return ""
    rest = scope[m.end():]
    nxt = re.search(r"^#{2,3}\s+", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _parse_capabilities(content: str) -> dict:
    """Parse New and Modified capabilities from proposal.md.

    兼容两种形态（锚点常量与渲染器同源，见 `_proposal_anchors`）：

    * **新形态**：顶层 `## Capabilities` 段，内含 `### New/Modified Capabilities`；
    * **历史形态**（渲染器改造前生成的 41 份归档 proposal.md）：
      无 `## Capabilities` 父标题，两个 h3 直接挂在 `## What Changes` 之下。

    ⇒ 有 h2 父标题时只在该段内查找（避免与正文其它同名 h3 串味）；
      无 h2 时回退到全文按 h3 锚点查找。
    """
    result = {"new": [], "modified": []}

    cap_body = _h2_body(content, H2_CAPABILITIES)
    scope = cap_body if cap_body is not None else content

    for key, h3 in (("new", H3_NEW_CAPABILITIES), ("modified", H3_MODIFIED_CAPABILITIES)):
        body = _h3_body(scope, h3)
        if not body:
            continue
        for name, desc in re.findall(r"-\s*\*\*(.+?)\*\*[：:]\s*(.+)", body):
            result[key].append({"name": name.strip(), "description": desc.strip()})

    return result


def _parse_impact(content: str) -> dict:
    """Parse Impact section from proposal.md."""
    result = {"code": [], "config": [], "infrastructure": []}
    section = _h2_body(content, H2_IMPACT)
    if section is None:
        return result

    # Parse bold-labeled sub-items: **代码层面**：\n- item
    for label, key in IMPACT_SECTIONS:
        sub = re.search(rf"\*\*{re.escape(label)}\*\*[：:]\s*\n((?:(?:-|\*)\s+.+\n?)+)", section)
        if sub:
            items = re.findall(r"(?:-|\*)\s+(.+)", sub.group(1))
            result[key] = [i.strip() for i in items]

    return result


def _parse_risk_areas(content: str) -> list[dict]:
    """Parse Risk Areas section with structured capability mapping.

    Expected format:
    ## Risk Areas
    - capability: <name> — <risk description>
    """
    items = _parse_section(content, H2_RISK_AREAS)
    result = []
    for item in items:
        # Try "capability: <name> — <risk>" format
        m = re.match(r"capability:\s*(\S+)\s*[—\-]\s*(.+)", item)
        if m:
            result.append({"capability": m.group(1), "risk": m.group(2)})
        elif item.startswith("capability:"):
            parts = item.split(":", 1)
            cap_name = parts[1].strip().split("—")[0].strip() if "—" in parts[1] else parts[1].strip().split("-")[0].strip()
            risk = parts[1].split("—", 1)[-1].strip() if "—" in parts[1] else parts[1].split("-", 1)[-1].strip()
            result.append({"capability": cap_name, "risk": risk})
        else:
            result.append({"capability": "", "risk": item})
    return result


def cmd_extract_proposal(args: argparse.Namespace) -> None:
    from ..finder import find_change_dir
    from ..utils import get_logger
    get_logger()

    project_root = Path.cwd()
    change_dir = find_change_dir(args.name, project_root, include_archive=True)
    if change_dir is None:
        print(f" 找不到 change: {args.name or '(无)'}")
        sys.exit(1)

    proposal_path = change_dir / "proposal.md"
    if not proposal_path.exists():
        print(f" 错误: proposal.md 不存在 ({change_dir})")
        sys.exit(1)

    content = proposal_path.read_text(encoding="utf-8")

    # Extract title from first heading
    title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else change_dir.name

    result = {
        "title": title,
        "capabilities": _parse_capabilities(content),
        # ⚠️ 历史形态下 capability 段落在 `## What Changes` 区间内 ⇒ 必须显式截断，
        # 否则 `**<capability>**：…` 条目会混进 what_changes（SC-009 反向断言）。
        "what_changes": _parse_section(
            content, H2_WHAT_CHANGES, stop_headings=CAPABILITY_H3_ANCHORS
        ),
        "success_criteria": _parse_section(content, H2_SUCCESS_CRITERIA),
        "impact": _parse_impact(content),
        # V2.5 new fields — backward compatible (empty if not present)
        "constraints": _parse_section(content, H2_CONSTRAINTS),
        "stakeholders": _parse_section(content, H2_STAKEHOLDERS),
        "risk_areas": _parse_risk_areas(content),
        "non_goals": _parse_section(content, H2_NON_GOALS),
    }

    fmt = getattr(args, "format", "json") or "json"
    if fmt == "yaml":
        print(yaml.dump(result, allow_unicode=True, default_flow_style=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
