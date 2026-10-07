"""test_proposal_extraction_fidelity.py — 渲染器 / 解析器锚点契约保真

覆盖 TC-PXF-001..003（capability: proposal-extraction-fidelity）
对应 spec：`.fstdd/changes/2026-10-07-tool-defect-fixes/canonical/specs/code/proposal-extraction-fidelity.yaml`
  → REQ-001 / SC-008（渲染器补出 `## Capabilities` 与 `## Impact`）
  → REQ-002 / SC-009（解析非空 + 无泄漏）、SC-010（历史 h3 形态向后兼容）

缺陷回顾（EXP-2026-0013 契约断层 / KG-093 声明未生效）：
渲染器把 `### New/Modified Capabilities` 挂在 `## What Changes` 之下且**从不输出** `## Impact`
（`grep Impact canon.py` = 0 命中），解析器却找 `## Capabilities` h2 ⇒
`capabilities` / `impact` 恒为空，capability 条目泄漏进 `what_changes`。

隔离原则：合成 change 一律建在 `tmp_path`；对真实归档只做**只读** `extract-proposal`。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import repo_root

REPO = repo_root()
CLI = REPO / "upstream" / "bin" / "fstdd"
ARCHIVE = REPO / ".fstdd" / "archive"

# 直接引用解析器/锚点常量（同源校验用）。
# ⚠️ 用 append 而非 insert(0)：insert(0) 会静默遮蔽同名模块（本项目既有教训）。
if str(REPO / "upstream") not in sys.path:
    sys.path.append(str(REPO / "upstream"))
from fstdd.cli.commands.extract_proposal import (  # noqa: E402
    _parse_capabilities,
    _parse_impact,
    _parse_section,
)
from fstdd.cli.commands._proposal_anchors import (  # noqa: E402
    H2_CAPABILITIES,
    H2_IMPACT,
    H2_WHAT_CHANGES,
    CAPABILITY_H3_ANCHORS,
)

SYNTH = "2026-01-01-pxf-synth"

_SYNTH_YAML = """\
meta:
  change_id: "2026-01-01-pxf-synth"
  title: "合成 change（锚点契约）"
why:
  problem: |
    合成问题陈述。
what_changes:
  - id: C1
    description: "变更项一"
    type: modified
  - id: C2
    description: "变更项二"
    type: modified
capabilities:
  new: []
  modified:
    - name: "cap-alpha"
      description: "能力甲"
    - name: "cap-beta"
      description: "能力乙"
impact:
  code:
    - "upstream/x.py：改一处"
  config:
    - "无"
  infrastructure:
    - "无"
success_criteria:
  - "标准一"
"""

# 历史形态（渲染器改造前的 h3 直挂）：同一份数据的 md 等价体
_H3_FORM_MD = """\
# 合成 change（锚点契约）

<!-- source_hash: deadbeefdeadbeef -->

## Why

合成问题陈述。

## What Changes

- 变更项一
- 变更项二

### New Capabilities

### Modified Capabilities

- **cap-alpha**：能力甲
- **cap-beta**：能力乙

## Impact

**代码层面**：
- upstream/x.py：改一处

**配置层面**：
- 无

**基础设施**：
- 无

## Success Criteria

- [ ] 标准一
"""


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(project),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _mk_change(tmp_path: Path, name: str, yaml_text: str) -> Path:
    cd = tmp_path / ".fstdd" / "changes" / name
    (cd / "canonical" / "proposals").mkdir(parents=True)
    (cd / "canonical" / "proposals" / f"{name}.yaml").write_text(
        yaml_text, encoding="utf-8", newline=""
    )
    (cd / ".fstdd.yaml").write_text(f"change_id: {name}\n", encoding="utf-8", newline="")
    return cd


def _h2_set(md: str) -> list:
    return re.findall(r"^##\s+(.+?)\s*$", md, re.MULTILINE)


def _h2_body(md: str, heading: str) -> str:
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", md, re.MULTILINE)
    if not m:
        return ""
    rest = md[m.end():]
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _leaked_capability_items(what_changes: list, cap_names: set) -> list:
    """从 what_changes 里挑出「形态上是 capability 条目」的项（SC-009 反向断言）。

    刻意只认 `**<name>**：` 形态且名字命中 capability 集合 —— 避免把正文里
    恰好加粗的普通条目误判为泄漏（EXP-2026-0016 假阳性的教训）。
    """
    leaked = []
    for item in what_changes:
        m = re.match(r"\*\*(.+?)\*\*[：:]", item)
        if m and m.group(1).strip() in cap_names:
            leaked.append(item)
    return leaked


# ============================================================
# TC-PXF-001 / SC-008 — 渲染器输出解析器期望的 h2
# ============================================================
def test_tc_pxf_001_renderer_emits_capabilities_and_impact_h2(tmp_path):
    _mk_change(tmp_path, SYNTH, _SYNTH_YAML)

    r = _run(tmp_path, "canon", "generate", SYNTH)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"

    md = (tmp_path / ".fstdd" / "changes" / SYNTH / "proposal.md").read_text(encoding="utf-8")
    h2s = _h2_set(md)

    assert H2_CAPABILITIES in h2s, f"缺少顶层 `## Capabilities`；实得 h2 = {h2s}"
    assert H2_IMPACT in h2s, f"缺少顶层 `## Impact`；实得 h2 = {h2s}"
    assert h2s.index(H2_CAPABILITIES) < h2s.index(H2_IMPACT), "Capabilities 应排在 Impact 之前"

    # 两个 h3 子段必须**嵌套在** `## Capabilities` 之内（不再挂在 What Changes 下）
    cap_body = _h2_body(md, H2_CAPABILITIES)
    assert "### New Capabilities" in cap_body
    assert "### Modified Capabilities" in cap_body
    assert "- **cap-alpha**：能力甲" in cap_body
    assert "- **cap-beta**：能力乙" in cap_body

    # `## What Changes` 段不得再含 capability 条目
    wc_body = _h2_body(md, H2_WHAT_CHANGES)
    assert "- **cap-alpha**" not in wc_body, f"capability 条目仍挂在 What Changes 下：\n{wc_body}"
    assert "- 变更项一" in wc_body

    # Impact 三段形态须与模板一致（`**代码层面**：` + bullet）
    imp_body = _h2_body(md, H2_IMPACT)
    for label in ("代码层面", "配置层面", "基础设施"):
        assert f"**{label}**：" in imp_body, f"Impact 缺 `**{label}**：` 段"


# ============================================================
# TC-PXF-002 / SC-009 — extract-proposal 非空且无泄漏
# ============================================================
def test_tc_pxf_002_extract_returns_nonempty_without_leak(tmp_path):
    _mk_change(tmp_path, SYNTH, _SYNTH_YAML)
    assert _run(tmp_path, "canon", "generate", SYNTH).returncode == 0

    r = _run(tmp_path, "extract-proposal", SYNTH)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"
    data = json.loads(r.stdout)

    assert data["capabilities"]["new"] == []
    assert data["capabilities"]["modified"] == [
        {"name": "cap-alpha", "description": "能力甲"},
        {"name": "cap-beta", "description": "能力乙"},
    ], f"capabilities.modified 解析错误：{data['capabilities']['modified']}"

    assert data["impact"]["code"] == ["upstream/x.py：改一处"]
    assert data["impact"]["config"] == ["无"]
    assert data["impact"]["infrastructure"] == ["无"]

    assert data["what_changes"] == ["变更项一", "变更项二"], (
        f"what_changes 解析错误（可能混入了 capability 段）：{data['what_changes']}"
    )
    cap_names = {"cap-alpha", "cap-beta"}
    assert _leaked_capability_items(data["what_changes"], cap_names) == []


def test_tc_pxf_002b_leak_detector_is_not_vacuous():
    """自检：泄漏检测器必须能抓到真实泄漏形态（EXP-2026-0021）。"""
    leaked = ["**cap-alpha**：能力甲", "变更项一"]
    assert _leaked_capability_items(leaked, {"cap-alpha"}) == ["**cap-alpha**：能力甲"]
    # 反例：名字不命中 capability 集合 ⇒ 不算泄漏
    assert _leaked_capability_items(["**其它**：正文"], {"cap-alpha"}) == []


# ============================================================
# TC-PXF-003 / SC-010 — 历史 h3 形态向后兼容 + 两形态结果一致
# ============================================================
def test_tc_pxf_003a_real_archive_h3_form_still_parses():
    """对真实归档（渲染器改造前的 h3 形态）执行 extract-proposal：不报错且解析非空。"""
    checked = 0
    for p in sorted(ARCHIVE.glob("*/proposal.md")):
        md = p.read_text(encoding="utf-8")
        if "Capabilities" not in md:
            continue
        r = _run(REPO, "extract-proposal", p.parent.name)
        assert r.returncode == 0, f"{p.parent.name}: exit {r.returncode}\n{r.stderr[:300]}"
        data = json.loads(r.stdout)

        caps = data["capabilities"]["new"] + data["capabilities"]["modified"]
        assert caps, f"{p.parent.name}: h3 形态未解析出任何 capability（向后兼容失败）"
        cap_names = {c["name"] for c in caps}
        assert _leaked_capability_items(data["what_changes"], cap_names) == [], (
            f"{p.parent.name}: capability 条目泄漏进 what_changes"
        )
        checked += 1
    assert checked >= 5, f"归档样本太少（{checked}），断言失去意义"


def test_tc_pxf_003b_h2_and_h3_forms_parse_identically(tmp_path):
    """同一份数据：新 h2 形态 与 历史 h3 直挂形态 的解析结果须一致（SC-010）。"""
    name_h2 = "2026-01-02-pxf-h2"
    name_h3 = "2026-01-03-pxf-h3"

    _mk_change(tmp_path, name_h2, _SYNTH_YAML)
    assert _run(tmp_path, "canon", "generate", name_h2).returncode == 0

    cd_h3 = _mk_change(tmp_path, name_h3, _SYNTH_YAML)
    (cd_h3 / "proposal.md").write_text(_H3_FORM_MD, encoding="utf-8", newline="")

    d_h2 = json.loads(_run(tmp_path, "extract-proposal", name_h2).stdout)
    d_h3 = json.loads(_run(tmp_path, "extract-proposal", name_h3).stdout)

    assert d_h3["capabilities"] == d_h2["capabilities"], (
        f"两形态 capabilities 不一致：h3={d_h3['capabilities']} h2={d_h2['capabilities']}"
    )
    assert d_h3["impact"] == d_h2["impact"], (
        f"两形态 impact 不一致：h3={d_h3['impact']} h2={d_h2['impact']}"
    )
    assert d_h3["what_changes"] == d_h2["what_changes"] == ["变更项一", "变更项二"]


def test_tc_pxf_003c_parser_accepts_h3_without_h2_parent():
    """单元级：无 `## Capabilities` 父标题时，仍按 h3 锚点解析（纯历史形态）。"""
    md = _H3_FORM_MD.replace("## Impact\n", "## Impact-REMOVED\n")
    caps = _parse_capabilities(md)
    assert caps["modified"] == [
        {"name": "cap-alpha", "description": "能力甲"},
        {"name": "cap-beta", "description": "能力乙"},
    ]
    # h2 形态下同样解析（同源锚点）
    h2_md = _H3_FORM_MD.replace("### New Capabilities\n", "## Capabilities\n\n### New Capabilities\n")
    assert _parse_capabilities(h2_md) == caps

    # 无 `## Impact` 时不得报错，返回空结构
    assert _parse_impact(md) == {"code": [], "config": [], "infrastructure": []}
    # what_changes 在 capability h3 处截断
    assert _parse_section(md, H2_WHAT_CHANGES, stop_headings=CAPABILITY_H3_ANCHORS) == [
        "变更项一", "变更项二",
    ]


def test_tc_pxf_003d_capability_nonempty_criterion_can_fail():
    """自检：`capabilities 非空` 这条判据（TC-PXF-003a 的核心断言）不得恒真。

    构造一份**有 `### Modified Capabilities` 标题但条目形态不合法**的文档
    （裸 `- foo`，无 `**name**：`），解析器应返回空 ⇒ 证明该判据具备判别力
    （EXP-2026-0021：审计器必须能抓到违例，否则是假绿）。
    """
    bad = (
        "# T\n\n## What Changes\n\n- C1\n\n"
        "### Modified Capabilities\n\n- 裸条目（缺 **名称**：形态）\n\n"
        "## Success Criteria\n\n- [ ] s1\n"
    )
    assert _parse_capabilities(bad) == {"new": [], "modified": []}, (
        "非法形态竟被解析出 capability —— 「非空」判据失去判别力"
    )
    # 同一份文档里 what_changes 仍应正常解析（截断逻辑不依赖 capability 能否解析成功）
    assert _parse_section(bad, H2_WHAT_CHANGES, stop_headings=CAPABILITY_H3_ANCHORS) == ["C1"]
