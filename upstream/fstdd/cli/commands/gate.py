"""stdd gate — CLI and file-token based Gate confirmation (V2.5)."""

import argparse
import hashlib
import sys
from pathlib import Path
from datetime import datetime

import yaml


VALID_GATES = [1, 2, 3]
# V3.0.5: Gate 3 now confirms the merged BUILD phase (SLICE+BUILD+VERIFY).
GATE_PHASE_KEY = {
    1: ("understand", "phases", "understand", "confirmed_at"),
    2: ("spec", "phases", "spec", "confirmed_at"),
    3: ("build", "phases", "build", "confirmed_at"),
}


def _find_change_dir(name: str | None, project_root: Path) -> Path | None:
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        return None
    if name:
        return changes_dir / name
    dirs = sorted(changes_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
    return dirs[0] if dirs else None


def _check_gate_order(gate_num: int, change_dir: Path) -> tuple[bool, str]:
    """Check that previous gates are confirmed before confirming gate_num."""
    state_file = change_dir / ".fstdd.yaml"
    if not state_file.exists():
        return False, f".fstdd.yaml not found in {change_dir}"

    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    phases = data.get("phases", {})

    for g in range(1, gate_num):
        prev_label, *prev_path = GATE_PHASE_KEY[g]
        val = phases
        for key in prev_path[1:]:  # skip first element (legacy section name)
            val = val.get(key) if isinstance(val, dict) else None
        if not val:
            return False, f"Gate {gate_num} cannot be confirmed: Gate {g} ({prev_label}) is not yet confirmed"

    return True, ""


def _check_file_token(gate_num: int, change_dir: Path) -> bool:
    """Check if GATE<N>_APPROVED file token exists."""
    token_file = change_dir / f"GATE{gate_num}_APPROVED"
    return token_file.exists()


def _resolve_actor() -> str:
    """V3.0.5: 推断 Gate 确认的发起者（审计链字段 confirmed_actor）。

    优先使用调用上下文信号（环境变量由 hook 注入），缺省按调用链
    无法区分时记录 ai（CLI 由 AI 工具执行是最常见路径）。
    """
    import os as _os
    hook_actor = _os.environ.get("STDD_CONFIRM_ACTOR", "")
    if hook_actor in ("ai", "user"):
        return hook_actor
    return "ai"


def _confirm_gate(gate_num: int, change_dir: Path, confirmed_by: str = "",
                  evidence: str = "") -> str:
    """Write confirmed_at + audit chain to .fstdd.yaml for the given gate.

    V3.0.5: 审计链字段 confirmed_by(通道) + confirmed_actor(发起者) +
    confirmed_evidence(确认证据) + confirmed_at(时间)。幂等分支不改 confirmed_at，
    也不覆盖已存在的审计字段。

    Args:
        gate_num: Gate 编号 1/2/3
        change_dir: change 目录
        confirmed_by: 确认通道（dialog|file_token|cli），无默认值
        evidence: 确认证据（如用户确认原文）
    """
    state_file = change_dir / ".fstdd.yaml"
    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}

    label, section, phase_key, field = GATE_PHASE_KEY[gate_num]
    phases = data.setdefault("phases", {})
    phase_data = phases.setdefault(phase_key, {})

    existing = phase_data.get(field)
    if existing:
        return f"Gate {gate_num} already confirmed at {existing}"

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    phase_data[field] = timestamp
    phase_data["confirmed_by"] = confirmed_by or "cli"
    phase_data["confirmed_actor"] = _resolve_actor()
    if evidence:
        phase_data["confirmed_evidence"] = evidence
    data["phases"][phase_key]["status"] = "completed"

    state_file.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8"
    )
    return f"Gate {gate_num} confirmed for change {change_dir.name}"


def _auto_generate_human_views(project_root: Path, change_dir: Path, gate_num: int) -> None:
    """V3.0.5 (YAML-first): At Gate confirmation, auto-generate Human View MD from Canonical YAML.

    - Gate 1 → proposal.md from changes/<change>/canonical/proposals/<change>.yaml
    - Gate 2 → specs/<cap>/spec.md from changes/<change>/canonical/specs/code/*.yaml

    Silently skips when no Canonical YAML exists (pure-MD legacy flow keeps working).
    """
    change_id = change_dir.name
    canon_dir = change_dir / "canonical"
    if not canon_dir.is_dir():
        return

    from .canon import _generate_one, _generate_spec

    try:
        if gate_num == 1:
            proposal_yaml = canon_dir / "proposals" / f"{change_id}.yaml"
            if proposal_yaml.exists():
                _generate_one(project_root, change_id, "proposal",
                              canon_dir=canon_dir, output_dir=change_dir)
                print(f"    ✨ 自动生成 Human View: {change_dir.name}/proposal.md (YAML-first)")
        elif gate_num == 2:
            specs_code_dir = canon_dir / "specs" / "code"
            if specs_code_dir.is_dir():
                generated = 0
                for yf in sorted(specs_code_dir.glob("*.yaml")):
                    # 跳过 new.py scaffold 的模板占位（capability 仍为 TODO）—
                    # 占位名含冒号，Windows 路径非法，且无真实需求内容
                    try:
                        spec_data = yaml.safe_load(yf.read_text(encoding="utf-8"))
                        cap = (spec_data.get("meta", {}) or {}).get("capability", "") or ""
                        if "TODO" in cap:
                            continue
                    except Exception:
                        continue
                    _generate_spec(project_root, yf, output_dir=change_dir)
                    generated += 1
                if generated:
                    print(f"    ✨ 自动生成 {generated} 个 spec.md Human View (YAML-first)")
    except SystemExit:
        pass  # YAML malformed — silent; user can run `stdd canon generate` manually


def _read_gates_config(project_root: Path) -> dict:
    """Read gates.yaml config with defaults."""
    config_path = project_root / ".fstdd" / "config.d" / "gates.yaml"
    if not config_path.exists():
        return {"confirmation": {"channels": ["dialog", "file_token", "cli"]}}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _amend_audit(change_dir: Path, gate_num: int, confirmed_by: str,
                  evidence: str) -> str:
    """Append a user ratification without rewriting the original Gate audit.

    The original confirmation remains immutable. A second amendment for the same
    Gate is allowed only when it is the exact same idempotent request.
    """
    if not evidence or not evidence.strip():
        raise ValueError("追认 evidence 不能为空")

    state_file = change_dir / ".fstdd.yaml"
    if not state_file.exists():
        raise ValueError(f".fstdd.yaml not found in {change_dir}")
    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    phase_key = GATE_PHASE_KEY[gate_num][2]
    original = (data.get("phases", {}).get(phase_key, {}) or {})
    if not original.get("confirmed_at"):
        raise ValueError(f"Gate {gate_num} 尚未确认，不能追加追认")

    evidence = evidence.strip()
    evidence_hash = hashlib.sha256(evidence.encode("utf-8")).hexdigest()[:16]
    idempotency_key = f"{data.get('change_id', change_dir.name)}:gate{gate_num}:{evidence_hash}"
    amendments = data.setdefault("audit_amendments", [])

    for amendment in amendments:
        if amendment.get("gate") != gate_num:
            continue
        if amendment.get("idempotency_key") == idempotency_key:
            print(f"Gate {gate_num} audit amendment already recorded")
            return "idempotent"
        raise ValueError(f"Gate {gate_num} 已存在不同证据的追认，拒绝覆盖")

    amendments.append({
        "gate": gate_num,
        "original_confirmed_at": original.get("confirmed_at"),
        "original_confirmed_by": original.get("confirmed_by", ""),
        "original_confirmed_actor": original.get("confirmed_actor", ""),
        "original_confirmed_evidence": original.get("confirmed_evidence", ""),
        "amended_actor": "user",
        "amended_by": confirmed_by,
        "amended_evidence": evidence,
        "amended_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "amended_by_tool_version": "3.0",
        "idempotency_key": idempotency_key,
    })
    state_file.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    return "recorded"


def cmd_gate(args: argparse.Namespace) -> None:
    """CLI entry: gate approval and append-only audit amendments."""
    project_root = Path.cwd()

    subcommand = getattr(args, "subcommand", "approve")
    if subcommand == "amend-audit":
        change_dir = _find_change_dir(getattr(args, "name", None), project_root)
        if change_dir is None or not change_dir.is_dir():
            print(f"  找不到 change: {getattr(args, 'name', '')}")
            sys.exit(1)
        try:
            result = _amend_audit(
                change_dir,
                args.gate,
                args.confirmed_by,
                args.evidence,
            )
        except ValueError as exc:
            print(f"  ❌ {exc}")
            sys.exit(1)
        if result == "recorded":
            print(f"Gate {args.gate} audit amendment recorded for change {change_dir.name}")
        return
    if subcommand != "approve":
        print(f"  Unknown subcommand: {subcommand}. Use: approve or amend-audit")
        sys.exit(1)

    gate_num = getattr(args, "gate", None)
    if gate_num is None or gate_num not in VALID_GATES:
        print(f"  Invalid gate number: {gate_num}. Valid gates: {', '.join(str(g) for g in VALID_GATES)}")
        sys.exit(1)

    # V3.0.5: --confirmed-by 必填（无默认值）。argparse required=True 已保证 CLI 层拦截，
    # 此处再做运行时拦截，覆盖直接构造 Namespace 的调用方。
    confirmed_by = getattr(args, "confirmed_by", None)
    if not confirmed_by:
        print("  Error: --confirmed-by is required (dialog|file_token|cli). Gate confirmation needs an explicit channel declaration.")
        sys.exit(2)
    if confirmed_by not in ("dialog", "file_token", "cli"):
        print(f"  Error: invalid --confirmed-by '{confirmed_by}'. Valid: dialog|file_token|cli")
        sys.exit(2)
    evidence = getattr(args, "evidence", "") or ""

    change_dir = _find_change_dir(getattr(args, "name", None), project_root)
    if change_dir is None:
        print("  No change found.")
        sys.exit(1)

    # Check if file token already confirms this gate
    if _check_file_token(gate_num, change_dir):
        # File token exists — sync it to .fstdd.yaml if not already
        state_file = change_dir / ".fstdd.yaml"
        data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
        label, _, phase_key, field = GATE_PHASE_KEY[gate_num]
        phase_data = data.get("phases", {}).get(phase_key, {})
        if not phase_data.get(field):
            # V3.0.5: file_token 通道同样先过顺序检查
            valid, err = _check_gate_order(gate_num, change_dir)
            if not valid:
                print(f"  {err}")
                sys.exit(1)
            _auto_generate_human_views(project_root, change_dir, gate_num)
            _confirm_gate(gate_num, change_dir, confirmed_by="file_token", evidence=evidence)
            print(f"  Gate {gate_num} confirmed (via file token, confirmed_by=file_token).")
            return
        else:
            print(f"  Gate {gate_num} already confirmed at {phase_data[field]}")
            return

    # V3.0.5: 声明 file_token 通道但无 token 文件 → 拒绝
    if confirmed_by == "file_token":
        print(f"  Error: --confirmed-by file_token but GATE{gate_num}_APPROVED token file not found in {change_dir.name}.")
        sys.exit(2)

    # Validate gate order
    valid, err = _check_gate_order(gate_num, change_dir)
    if not valid:
        print(f"  {err}")
        sys.exit(1)

    _auto_generate_human_views(project_root, change_dir, gate_num)
    result = _confirm_gate(gate_num, change_dir, confirmed_by=confirmed_by, evidence=evidence)
    print(f"  {result}")
