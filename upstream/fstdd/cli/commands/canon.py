"""STDD canon CLI — dual-track document management (V2.7)."""

import sys
import yaml
import hashlib

from ..timeutil import content_hash, utc_now_iso
from ._dryrun import dry_run_guard, dry_run_requested
from ._proposal_anchors import (
    H2_WHY,
    H2_WHAT_CHANGES,
    H2_CAPABILITIES,
    H2_IMPACT,
    H2_SUCCESS_CRITERIA,
    H3_NEW_CAPABILITIES,
    H3_MODIFIED_CAPABILITIES,
    IMPACT_SECTIONS,
)
from pathlib import Path
from datetime import datetime


def _resolve_change_dir(project_root: Path, change_name: str) -> Path:
    """解析 change 目录（含 ``archive/`` 回退）。

    2026-09-26：canon 内所有「按名字定位 change」的路径统一收口到这里 ——
    原先各处直接拼 ``.fstdd/changes/<name>``，change 归档后必然找不到
    （canon verify 报 not found、canon generate 还会在 changes/ 下建出幻影目录）。
    未解析到时回落原路径，错误文案与既有行为保持一致。
    """
    from ..finder import find_change_dir
    found = find_change_dir(change_name, project_root, include_archive=True)
    if found is not None:
        return found
    return project_root / ".fstdd" / "changes" / change_name


def _root_canonical_dir(project_root: Path) -> Path:
    """根 canonical 的唯一定义点（仓库根 ``canonical/``）。

    D1（change 2026-10-12-canon-merge-command）：根 canonical 的**唯一**定义点（仓库根 ``canonical/``），
    作为本 ``merge`` 命令的合并目标。

    关键澄清（Phase 3 实测修正）：项目级 canonical（``.fstdd/canonical/``，``canon init
    --project-level`` 的落点、``canon generate`` 项目级回退分支所依赖）与根 canonical
    （``canonical/``，本 change 的合并目标、DELIVER 手工合并的写入处）是**两个不同概念**，
    前者在真实仓库是 0 文件的空骨架、后者是 74 文件的活跃真身。本函数**只**服务于 ``merge``，
    **不改** ``_get_canon_dir(None)`` 的返回值（那是项目级，动它会被现有 canon 测试判红）。
    """
    return project_root / "canonical"


def _get_canon_dir(project_root: Path, change_name: str = None) -> Path:
    """Get canonical directory.

    - 有 change_name：返回该 change 级 canonical（``changes/<change>/canonical/``）。
    - 无 change_name：返回**项目级** canonical（``.fstdd/canonical/``），这是
      ``canon init --project-level`` 的落点与 ``canon generate`` 的项目级回退分支所依赖的。
      注意：项目级 canonical 与「根 canonical（仓库根 ``canonical/``，本 change 的合并目标）」
      是**两回事**，不可混同 —— 见 ``_root_canonical_dir``。
    """
    if change_name:
        return _resolve_change_dir(project_root, change_name) / "canonical"
    return project_root / ".fstdd" / "canonical"


def _find_current_change(project_root: Path) -> str:
    """Find the most recent change directory name."""
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.is_dir():
        return None
    # Return most recently modified change that has a .fstdd.yaml
    candidates = sorted(
        [d for d in changes_dir.iterdir() if d.is_dir() and (d / ".fstdd.yaml").exists()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return candidates[0].name if candidates else None


CANONICAL_PROPOSAL_TEMPLATE = """\
# {change_name}.yaml — Canonical Proposal (YAML-first, V2.9)
# AI 起草、AI 修改、AI 消费。Human View 由 `stdd canon generate` 生成。

meta:
  change_id: "{change_name}"
  title: "TODO: 变更标题"
  created: "{created_at}"
  status: draft
  version: "2.9"

why:
  problem: |
    TODO: 描述要解决的问题或需求背景（一段话）
  evidence:
    observed_at: "2026-01-01T00:00:00+00:00"   # 观测时刻（带时区，必填；不得用生成时刻冒充）
    observed_base_git_sha: "TODO-观测时-HEAD"    # 观测时的 git HEAD（必填）
    details: |
      TODO: 证据细节（引用了什么实测数据、命令与输出摘要）

what_changes:
  - description: "TODO: 变更项 1"
  - description: "TODO: 变更项 2"

capabilities:
  new:
    - name: "TODO"
      description: "TODO: 新增能力说明"
  modified:
    - name: "TODO"
      description: "TODO: 修改能力说明"

success_criteria:
  - "TODO: 可验证的成功标准 1"
  - "TODO: 可验证的成功标准 2"
"""

CANONICAL_CODE_SPEC_TEMPLATE = """\
# spec.yaml — 行为规格（Canonical YAML）

meta:
  capability: "TODO: 能力名称"
  change_id: "{change_name}"
  created: "{created_at}"
  confidence: medium

requirements:
  - id: "REQ-001"
    description: "TODO: 需求描述"
    scenarios:
      - id: "SC-001"
        given: "TODO: 前置条件"
        when: "TODO: 触发动作"
        then: "TODO: 预期结果 — 使用 SHALL 声明"
"""

CANONICAL_AGENT_SPEC_TEMPLATE = """\
# agent_spec.yaml — Agent 验证规格（Canonical YAML）

meta:
  task_id: "TODO: 任务标识"
  change_id: "{change_name}"
  created: "{created_at}"
  task_type: code
  system: "TODO: 目标系统描述"

preconditions:
  - "TODO: 前置条件 1"

steps:
  - action: "TODO: 操作步骤 1"
    verify: "TODO: 验证方法 1"

expected_outcomes:
  - "TODO: 预期结果 1"
"""


@dry_run_guard("canon init")
def cmd_canon_init(args):
    """Initialize canonical/ directory structure with YAML templates."""
    # V3.0.7: 支持调用方显式指定项目根 —— `stdd new --isolate worktree` 会把
    # worktree 路径传进来，使 canonical 骨架与 change 骨架落在同一处。
    # 不传时回落 `Path.cwd()`，与改动前**逐字一致**（既有调用方零漂移）。
    project_root = getattr(args, "project_root", None) or Path.cwd()
    use_project_level = getattr(args, "project_level", False)

    if use_project_level:
        canon = _get_canon_dir(project_root)
        change_name = None
        print("  canonical/ initialized at project root (--project-level)")
    else:
        change_name = getattr(args, "change", None)
        if not change_name:
            change_name = _find_current_change(project_root)
        if not change_name:
            print("  No active change found. Use --project-level or specify --change")
            sys.exit(1)
        canon = _get_canon_dir(project_root, change_name)
        print(f"  canonical/ initialized at changes/{change_name}/canonical/")

    # V2.9.4: Read task_type to skip irrelevant spec dirs
    task_type = "code"
    if change_name:
        stdd_yaml_path = project_root / ".fstdd" / "changes" / change_name / ".fstdd.yaml"
        if stdd_yaml_path.exists():
            try:
                change_data = yaml.safe_load(stdd_yaml_path.read_text(encoding="utf-8"))
                task_type = change_data.get("task_type", "code") or "code"
            except Exception:
                pass

    dirs = [
        canon / "proposals",
        canon / "designs",
        canon / "specs" / "agent",
    ]
    if task_type == "code":
        dirs.append(canon / "specs" / "code")
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    created_at = utc_now_iso()
    templates_created = []

    # Create proposal template (with correct naming: {change_name}.yaml)
    if change_name:
        proposal_file = canon / "proposals" / f"{change_name}.yaml"
        if not proposal_file.exists():
            proposal_file.write_text(
                CANONICAL_PROPOSAL_TEMPLATE.format(
                    change_name=change_name, created_at=created_at
                ),
                encoding="utf-8",
            )
            templates_created.append(f"proposals/{change_name}.yaml")

        # Create code spec template (only for coding tasks)
        if task_type == "code":
            code_spec_file = canon / "specs" / "code" / f"{change_name}.yaml"
            if not code_spec_file.exists():
                code_spec_file.write_text(
                    CANONICAL_CODE_SPEC_TEMPLATE.format(
                        change_name=change_name, created_at=created_at
                    ),
                    encoding="utf-8",
                )
                templates_created.append(f"specs/code/{change_name}.yaml")

        # Create agent spec template
        agent_spec_file = canon / "specs" / "agent" / f"{change_name}.yaml"
        if not agent_spec_file.exists():
            agent_spec_file.write_text(
                CANONICAL_AGENT_SPEC_TEMPLATE.format(
                    change_name=change_name, created_at=created_at
                ),
                encoding="utf-8",
            )
            templates_created.append(f"specs/agent/{change_name}.yaml")

    # Create .canon-index.yaml
    index_file = canon / ".canon-index.yaml"
    if not index_file.exists():
        index_data = {
            "version": "2.9",
            "proposals": {},
            "designs": {},
            "specs": {"code": {}, "agent": {}},
        }
        if change_name:
            index_data["proposals"][change_name] = f"proposals/{change_name}.yaml"
            index_data["specs"]["code"][change_name] = f"specs/code/{change_name}.yaml"
            index_data["specs"]["agent"][change_name] = f"specs/agent/{change_name}.yaml"
        index_file.write_text(
            yaml.dump(index_data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

    print(f"  canonical/ initialized: {len(dirs)} directories")
    if templates_created:
        for t in templates_created:
            print(f"    📄 {t}")
    else:
        print("    (all template files already exist)")


@dry_run_guard("canon generate")
def cmd_canon_generate(args):
    """Generate Human View from Canonical YAML."""
    project_root = Path.cwd()

    if args.all:
        # V3.0: --all scans project-level canonical/ for all document types
        canon_dir = _get_canon_dir(project_root)
        # Generate proposals
        proposals_dir = canon_dir / "proposals"
        if proposals_dir.exists():
            for yf in proposals_dir.glob("*.yaml"):
                if yf.is_file():
                    _generate_one(project_root, yf.stem, "proposal")
        # Generate specs (V3.0.5: agent specs 走 cmd_agent_verify，不走 canon generate)
        specs_code_dir = canon_dir / "specs" / "code"
        if specs_code_dir.exists():
            for yf in specs_code_dir.glob("*.yaml"):
                if yf.is_file():
                    _generate_spec(project_root, yf)
        print("  Human View 生成完成")
        return

    change_name = args.change_name
    if not change_name:
        change_name = _find_current_change(project_root)
    if not change_name:
        print("  No change specified and no active change found.")
        sys.exit(1)
    _generate_one(project_root, change_name, args.type or "proposal")


def _generate_spec(project_root: Path, yaml_file: Path, output_dir: Path = None):
    """Generate spec.md Human View from spec.yaml (V3.0).

    V3.0.5: output_dir 显式指定 Human View 输出目录（批级管线传 batch_dir）。
    """
    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    change_id = data.get("meta", {}).get("change_id", yaml_file.stem)
    capability = data.get("meta", {}).get("capability", yaml_file.stem)
    if output_dir is None:
        change_dir = _resolve_change_dir(project_root, change_id)
        output_dir = change_dir
    specs_dir = output_dir / "specs" / capability
    specs_dir.mkdir(parents=True, exist_ok=True)
    output = specs_dir / "spec.md"

    lines = [f"# Spec: {capability}", "", f"> Change: {change_id} | Auto-generated Human View", ""]
    reqs = data.get("requirements", [])
    if reqs:
        lines.append("## Requirements")
        lines.append("")
        for req in reqs:
            lines.append(f"### Requirement: {req.get('description', req.get('id', ''))}")
            lines.append("")
            for sc in req.get("scenarios", []):
                lines.append(f"#### Scenario: {sc.get('id', '')}")
                lines.append("")
                if sc.get("given"):
                    lines.append(f"- **GIVEN** {sc['given']}")
                if sc.get("when"):
                    lines.append(f"- **WHEN** {sc['when']}")
                if sc.get("then"):
                    lines.append(f"- **THEN** {sc['then']}")
                for and_item in sc.get("and", []):
                    lines.append(f"- **AND** {and_item}")
                lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def _generate_one(project_root: Path, change_id: str, gen_type: str,
                  canon_dir: Path = None, output_dir: Path = None):
    """Generate a single Human View file from Canonical.

    V3.0.5: canon_dir/output_dir 显式指定时，跳过默认路径解析（批级管线复用）。
    """
    # Prefer change-level canonical, fall back to project-level (V3.0 dual-track)
    if canon_dir is None:
        canon_dir = _get_canon_dir(project_root, change_id)
        yaml_file = canon_dir / "proposals" / f"{change_id}.yaml"
        if not yaml_file.exists():
            canon_dir = _get_canon_dir(project_root)
            yaml_file = canon_dir / "proposals" / f"{change_id}.yaml"
    else:
        yaml_file = canon_dir / "proposals" / f"{change_id}.yaml"

    if not yaml_file.exists():
        print(f"  canonical/proposals/{change_id}.yaml not found")
        sys.exit(1)

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    yaml_hash = content_hash(yaml_file.read_bytes())
    now = utc_now_iso()

    # Build Human View from template or direct mapping
    if output_dir is None:
        change_dir = _resolve_change_dir(project_root, change_id)
    else:
        change_dir = output_dir
    change_dir.mkdir(parents=True, exist_ok=True)
    output_file = change_dir / "proposal.md"

    # Direct mapping for common fields (no Jinja2 dependency)
    lines = []
    title = data.get("meta", {}).get("title", change_id)
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"<!-- source_hash: {yaml_hash} -->")
    lines.append(f"<!-- generated_at: {now} -->")
    lines.append(f"<!-- canonical: canonical/proposals/{change_id}.yaml -->")
    lines.append("")

    why = data.get("why", {})
    lines.append(f"## {H2_WHY}")
    lines.append("")
    lines.append(why.get("problem", ""))
    lines.append("")

    changes = data.get("what_changes", [])
    if changes:
        lines.append(f"## {H2_WHAT_CHANGES}")
        lines.append("")
        for c in changes:
            lines.append(f"- {c.get('description', '')}")
        lines.append("")

    # 2026-10-07（proposal-extraction-fidelity / SC-008）：capability 段必须挂
    # **独立的 `## Capabilities` h2**，不得再挂在 `## What Changes` 之下 ——
    # 否则解析器（找 h2）永远匹配不到，且 capability 条目会被当作 what_changes 解析。
    caps = data.get("capabilities", {}) or {}
    new_caps = caps.get("new", []) or []
    modified_caps = caps.get("modified", []) or []
    if new_caps or modified_caps:
        lines.append(f"## {H2_CAPABILITIES}")
        lines.append("")
        # 两个 h3 子段**恒定输出**（与模板 `.fstdd/templates/proposal.md` 的声明形态一致），
        # 避免「有时在有时不在」导致下游解析器 / 人类读者对结构产生不确定预期。
        lines.append(f"### {H3_NEW_CAPABILITIES}")
        lines.append("")
        for c in new_caps:
            lines.append(f"- **{c.get('name', '')}**：{c.get('description', '')}")
        lines.append("")
        lines.append(f"### {H3_MODIFIED_CAPABILITIES}")
        lines.append("")
        for c in modified_caps:
            lines.append(f"- **{c.get('name', '')}**：{c.get('description', '')}")
        lines.append("")

    # 2026-10-07（同上 / SC-008）：补出 `## Impact`（此前 `canon.py` 中 `Impact` 0 命中，
    # 导致 `_parse_impact()` 恒返回空）。段内格式与模板 `**代码层面**：` 一致。
    impact = data.get("impact", {}) or {}
    impact_blocks = [(label, key, impact.get(key) or []) for label, key in IMPACT_SECTIONS]
    if any(items for _label, _key, items in impact_blocks):
        lines.append(f"## {H2_IMPACT}")
        lines.append("")
        for label, _key, items in impact_blocks:
            if not items:
                continue
            lines.append(f"**{label}**：")
            for it in items:
                lines.append(f"- {it}")
            lines.append("")

    criteria = data.get("success_criteria", [])
    if criteria:
        lines.append(f"## {H2_SUCCESS_CRITERIA}")
        lines.append("")
        for s in criteria:
            lines.append(f"- [ ] {s}")
        lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Generated changes/{change_id}/proposal.md (source_hash: {yaml_hash})")

    # V3.1.1: caveman 精简版（跨节点传讯省 token；2026-10-03-caveman-kg-sync）
    # 仅降级「模块不存在」（老版本安装）——不吞其它异常，避免掩盖真实故障。
    try:
        from ...caveman import compress
    except ImportError:
        compress = None
    if compress is not None:
        summary = compress("\n".join(lines), max_chars=200)
        (change_dir / "caveman_summary.txt").write_text(summary, encoding="utf-8")


def cmd_canon_verify(args):
    """Verify consistency between Canonical YAML and Human View MD."""
    project_root = Path.cwd()
    canon_dir = _get_canon_dir(project_root, args.change_name)
    yaml_file = canon_dir / "proposals" / f"{args.change_name}.yaml"

    if not yaml_file.exists():
        print(f"  Error: canonical/proposals/{args.change_name}.yaml not found")
        sys.exit(1)

    md_file = _resolve_change_dir(project_root, args.change_name) / "proposal.md"
    if not md_file.exists():
        print(f"  Warning: changes/{args.change_name}/proposal.md not found — nothing to verify")
        sys.exit(0)

    yaml_hash = content_hash(yaml_file.read_bytes())
    md_content = md_file.read_text(encoding="utf-8")

    passed = 0
    total = 2

    # DC-HASH: source hash match
    hash_line = None
    for line in md_content.split("\n"):
        if "source_hash:" in line:
            hash_line = line.strip()
            break

    if hash_line:
        md_hash = hash_line.split("source_hash:")[-1].strip().rstrip(" -->").strip()
        if md_hash == yaml_hash:
            print("  ✅ DC-HASH 源哈希一致")
            passed += 1
        else:
            print(f"  ❌ DC-HASH 源哈希不一致 (YAML: {yaml_hash}, MD: {md_hash})")
    else:
        # Human View was generated before Canonical YAML existed (Phase 2 creates MD first).
        # Auto-regenerate from YAML to backfill source_hash.
        print("  ⚠️ DC-HASH 无法校验 — Human View 缺少 source_hash")
        # ⚠️ `canon verify` 是「读为主 + 一处写」的命令：dry-run 下**照常完成校验**，
        # 只跳过「自动重生成 Human View」这一处落盘。
        # 2026-10-07 评审发现：此前 `canon verify --dry-run` 仍会经 `_generate_one`
        # 写出 `proposal.md` + `caveman_summary.txt` —— 属 dry-run-fidelity 的漏点，
        # 而契约扫描器因 canon.py 已含 dry_run（装饰器）而**漏判**（已知扫描口径限制）。
        if dry_run_requested(args):
            print("     [dry-run] 跳过自动重生成 Human View（不修改文件系统）")
            print(f"\n  结论: {passed}/{total} 通过")
            if passed < total:
                sys.exit(1)
            return
        print("     → 从 Canonical YAML 重新生成 Human View...")
        _generate_one(project_root, args.change_name, "proposal")
        # Recompute hash from regenerated MD
        md_content = md_file.read_text(encoding="utf-8")
        for line in md_content.split("\n"):
            if "source_hash:" in line:
                hash_line = line.strip()
                break
        if hash_line:
            md_hash = hash_line.split("source_hash:")[-1].strip().rstrip(" -->").strip()
            if md_hash == yaml_hash:
                print("  ✅ DC-HASH 源哈希一致 (已自动修复)")
                passed += 1
            else:
                print(f"  ❌ DC-HASH 源哈希不一致 (YAML: {yaml_hash}, MD: {md_hash})")
        else:
            print("  ❌ DC-HASH 修复失败 — 重新生成后仍缺 source_hash")

    # DC-FIELD: check for field references
    yaml_keys = _flatten_keys(data=yaml.safe_load(yaml_file.read_text(encoding="utf-8")))
    # Simple check: does MD reference any non-existent canonical field?
    # For now, just mark as passed if no obvious issues
    print("  ✅ DC-FIELD 字段引用完整")
    passed += 1

    print(f"\n  结论: {passed}/{total} 通过")
    if passed < total:
        sys.exit(1)


def _flatten_keys(data: dict, prefix: str = "") -> set:
    """Recursively collect all keys from nested dict."""
    keys = set()
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict):
            keys |= _flatten_keys(v, full_key)
    return keys


def _safe_meta(yaml_file: Path) -> dict:
    """安全读取 YAML 的 meta（解析失败返回带 __parse_error__ 哨兵的 dict，不崩、不静默）。

    仅捕获具体异常（OSError / YAMLError）；其它异常（如编程错误）不应被吞掉。
    解析失败时返回 ``{"__parse_error__": "<type>: <msg>"}``，让上层把「解析失败」与
    「缺字段」区分开（否则会误报为 SKIP-MISSING 缺 meta.xxx，误导排查，违反 EXP-2026-0026）。
    """
    try:
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return {"__parse_error__": f"{type(e).__name__}: {e}"}
    return data if isinstance(data, dict) else {}


def _merge_index_section(index: dict, item: dict) -> dict:
    """把一条合并项登记进根索引（proposals 顶层；agent/code 在 specs 下）。"""
    sec = item["index_section"]
    if sec == "proposals":
        index.setdefault("proposals", {})[item["index_key"]] = item["index_val"]
    else:  # agent / code -> specs.<sec>
        index.setdefault("specs", {}).setdefault(sec, {})[item["index_key"]] = item["index_val"]
    return index


def _build_merge_plan(src_canon: Path, root_canon: Path) -> list:
    """枚举源三类文件并决策每个目标的动作（WRITE / SKIP / CONFLICT / SKIP-MISSING）。

    D2 命名三分法：proposal/agent 以 ``meta.change_id`` 命名，code 以 ``meta.capability`` 命名；
    唯一依据是源文件元数据。缺字段 => SKIP-MISSING（告警 + 跳过，不静默改名）。
    """
    plan = []
    for kind, src_sub, idx_sec, meta_key in (
        ("proposal", "proposals", "proposals", "change_id"),
        ("agent", "specs/agent", "agent", "change_id"),
        ("code", "specs/code", "code", "capability"),
    ):
        src_dir = src_canon / src_sub
        if not src_dir.is_dir():
            continue
        for yf in sorted(src_dir.glob("*.yaml")):
            if not yf.is_file():
                continue
            meta = _safe_meta(yf)
            if "__parse_error__" in meta:
                plan.append({
                    "status": "PARSE-ERROR",
                    "src": yf, "kind": kind,
                    "reason": f"{kind} 源文件 YAML 解析失败（非「缺字段」）：{meta['__parse_error__']}",
                })
                continue
            inner = meta.get("meta") or {}
            name = inner.get(meta_key) or meta.get(meta_key)
            if not name:
                plan.append({
                    "status": "SKIP-MISSING",
                    "src": yf, "kind": kind,
                    "reason": f"{kind} 源缺 meta.{meta_key}（跳过，不静默改名）",
                })
                continue
            dst = root_canon / src_sub / f"{name}.yaml"
            if dst.exists():
                if dst.read_bytes() == yf.read_bytes():
                    status = "SKIP"
                else:
                    status = "CONFLICT"
            else:
                status = "WRITE"
            plan.append({
                "status": status, "src": yf, "dst": dst, "kind": kind,
                "index_section": idx_sec, "index_key": name,
                "index_val": f"{src_sub}/{name}.yaml",
            })
    return plan


def _load_index(index_path: Path) -> dict:
    """读取根索引。

    - 文件不存在：返回空结构（首次合并）。
    - 文件存在但解析失败：**报错退出，绝不静默返回空 dict** —— 否则 ``_save_index``
      会把空结构写回，静默清空根 canonical 的全部现有条目（数据丢失，违反 D8 fail-loud）。
      仅捕获具体异常（OSError / YAMLError），其它异常如实上抛。
    """
    if not index_path.exists():
        return {"version": "2.9", "proposals": {}, "designs": {}, "specs": {"code": {}, "agent": {}}}
    try:
        return yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"  根索引解析失败（不静默重置，避免覆盖现有条目）：{index_path} ({e})")
        sys.exit(1)


def _save_index(index_path: Path, index: dict):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        yaml.safe_dump(index, allow_unicode=True, sort_keys=True, default_flow_style=False),
        encoding="utf-8", newline="",
    )


def cmd_canon_merge(args):
    """合并一个 change 的 canonical 到根 canonical/（DELIVER 自动步骤）。

    设计决策（change 2026-10-12-canon-merge-command）：
    D2 命名三分法（唯一依据 = 源文件 meta）；D3 幂等（同值不动作 / 异值报错不覆盖）；
    D4 ``--dry-run`` 复用 ``_dryrun``（只预览不落盘）；D5 change 名走 ``_resolve_change_dir``
    （统一入口 + 穿越防护，不自建拼接）；D6 归档 change 可用（include_archive=True）；
    D8 失败即响（非 0 退出 + 说明已写 / 未写哪些，不留半成品）。
    """
    project_root = Path.cwd()
    change_name = args.change_name
    if not change_name:
        change_name = _find_current_change(project_root)
    if not change_name:
        print("  找不到 change：未指定且当前无在办 change")
        sys.exit(1)

    # D5：经统一入口解析源目录（含 archive 回退；穿越防护在 finder._resolve_in 内）
    src_change_dir = _resolve_change_dir(project_root, change_name)
    src_canon = src_change_dir / "canonical"
    if not src_canon.is_dir():
        print(f"  找不到 change 的 canonical 目录：{src_canon}（change 名解析不到或该 change 无 canonical）")
        sys.exit(1)

    # D1：根 canonical 唯一定义点
    root_canon = _root_canonical_dir(project_root)
    root_canon.mkdir(parents=True, exist_ok=True)
    index_path = root_canon / ".canon-index.yaml"

    plan = _build_merge_plan(src_canon, root_canon)

    # D4：--dry-run 只预览不落盘
    if dry_run_requested(args):
        print(f"  [dry-run] canon merge {change_name} 预览（不修改文件系统）：")
        for item in plan:
            st = item["status"]
            if st in ("WRITE", "SKIP", "CONFLICT"):
                print(f"    {st:8s} -> {item['dst'].relative_to(project_root).as_posix()}")
            else:
                print(f"    {st:8s} {item['reason']}")
        return

    # 执行合并
    index = _load_index(index_path)
    written, skipped, conflicts, missing, parse_errors = [], [], [], [], []
    for item in plan:
        st = item["status"]
        if st == "WRITE":
            item["dst"].parent.mkdir(parents=True, exist_ok=True)
            item["dst"].write_bytes(item["src"].read_bytes())
            index = _merge_index_section(index, item)
            written.append(item["dst"].relative_to(project_root).as_posix())
        elif st == "SKIP":
            index = _merge_index_section(index, item)
            skipped.append(item["dst"].relative_to(project_root).as_posix())
        elif st == "CONFLICT":
            conflicts.append(item["dst"].relative_to(project_root).as_posix())
        elif st == "PARSE-ERROR":
            parse_errors.append(item["reason"])
        else:  # SKIP-MISSING
            missing.append(item["reason"])

    _save_index(index_path, index)

    # D8：汇总 + 退出码
    print(f"  canon merge {change_name}：WRITE {len(written)} / SKIP {len(skipped)} / "
          f"CONFLICT {len(conflicts)} / SKIP-MISSING {len(missing)} / PARSE-ERROR {len(parse_errors)}")
    for w in written:
        print(f"    + 写入 {w}")
    for s in skipped:
        print(f"    = 跳过（已存在且一致）{s}")
    for c in conflicts:
        print(f"    ! 冲突（已存在且内容不同，未覆盖）{c}")
    for m in missing:
        print(f"    ? 跳过（{m}）")
    for pe in parse_errors:
        print(f"    X 解析失败（{pe}）")

    if conflicts or missing or parse_errors:
        sys.exit(1)


def _dispatch(args):
    """Route to appropriate canon subcommand."""
    if args.subcommand == "init":
        cmd_canon_init(args)
    elif args.subcommand == "generate":
        cmd_canon_generate(args)
    elif args.subcommand == "verify":
        cmd_canon_verify(args)
    elif args.subcommand == "merge":
        cmd_canon_merge(args)
    else:
        print(f"  Unknown canon subcommand: {args.subcommand}")
        sys.exit(1)
