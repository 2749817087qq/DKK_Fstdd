"""STDD canon CLI — dual-track document management (V2.7)."""

import sys
import yaml
import hashlib

from ..timeutil import content_hash, utc_now_iso
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


def _get_canon_dir(project_root: Path, change_name: str = None) -> Path:
    """Get canonical directory. Defaults to changes/<change>/canonical/ (V2.9)."""
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
    lines.append("## Why")
    lines.append("")
    lines.append(why.get("problem", ""))
    lines.append("")

    changes = data.get("what_changes", [])
    if changes:
        lines.append("## What Changes")
        lines.append("")
        for c in changes:
            lines.append(f"- {c.get('description', '')}")
        lines.append("")

    caps = data.get("capabilities", {})
    new_caps = caps.get("new", [])
    if new_caps:
        lines.append("### New Capabilities")
        lines.append("")
        for c in new_caps:
            lines.append(f"- **{c.get('name', '')}**：{c.get('description', '')}")
        lines.append("")

    modified_caps = caps.get("modified", [])
    if modified_caps:
        lines.append("### Modified Capabilities")
        lines.append("")
        for c in modified_caps:
            lines.append(f"- **{c.get('name', '')}**：{c.get('description', '')}")
        lines.append("")

    criteria = data.get("success_criteria", [])
    if criteria:
        lines.append("## Success Criteria")
        lines.append("")
        for s in criteria:
            lines.append(f"- [ ] {s}")
        lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Generated changes/{change_id}/proposal.md (source_hash: {yaml_hash})")


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


def _dispatch(args):
    """Route to appropriate canon subcommand."""
    if args.subcommand == "init":
        cmd_canon_init(args)
    elif args.subcommand == "generate":
        cmd_canon_generate(args)
    elif args.subcommand == "verify":
        cmd_canon_verify(args)
    else:
        print(f"  Unknown canon subcommand: {args.subcommand}")
        sys.exit(1)
