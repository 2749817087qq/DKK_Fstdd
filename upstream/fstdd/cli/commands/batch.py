"""STDD batch CLI — lightweight change batch management (V2.9.3).

Batch mode solves the "N micro-changes" problem during debugging/hotfix
sessions. Instead of creating a separate change for each small fix, the
user opens a batch, makes all related edits (guard allows them), adds
each fix as an item, then closes and archives a single batch record.

V2.9.3: batch open now validates description scope against guard's
classifier. Descriptions signaling large changes (重构/架构/新模块)
are rejected with a suggestion to use full STDD.

Usage:
    stdd batch open "修复界面展示bug"     # opens a batch
    stdd batch add "fix: fees 展示为负值" # adds item to current batch
    stdd batch close                      # closes the batch
    stdd batch archive                    # archives to archive/
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

# V2.9.3: Import scope classifier from guard
try:
    from fstdd.cli.commands.guard import _classify_description, _SCOPE_LARGE, _SCOPE_MEDIUM
except ImportError:
    # Fallback: guard module not importable (shouldn't happen but be safe)
    def _classify_description(text: str) -> str:
        return "micro"

    _SCOPE_LARGE = "large"
    _SCOPE_MEDIUM = "medium"


def _get_batches_dir(project_root: Path) -> Path:
    """Get _batch directory path."""
    return project_root / ".fstdd" / "changes" / "_batch"


def _find_open_batch(project_root: Path) -> Path:
    """Find the currently open (unclosed) batch directory."""
    import yaml
    batches_dir = _get_batches_dir(project_root)
    if not batches_dir.is_dir():
        return None

    for batch_dir in sorted(
        [d for d in batches_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    ):
        stdd_yaml = batch_dir / ".fstdd.yaml"
        if stdd_yaml.exists():
            data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
            if data and not data.get("closed_at"):
                return batch_dir
    return None


def _read_batch_config(project_root: Path) -> dict:
    """Read batch config from lite.yaml (V3.0.5: max_items 不再硬编码 5)."""
    import yaml
    lite_path = project_root / ".fstdd" / "config.d" / "lite.yaml"
    if not lite_path.exists():
        return {"max_items": 20}
    try:
        data = yaml.safe_load(lite_path.read_text(encoding="utf-8"))
        return (data or {}).get("batch", {}) or {}
    except Exception:
        return {"max_items": 20}


def _create_batch(project_root: Path, strategy: str = "monthly") -> Path:
    """Create a new batch directory."""
    import yaml
    now = datetime.now()
    if strategy == "weekly":
        iso = now.isocalendar()
        batch_id = f"{now.year}-W{iso.week:02d}-{now.strftime('%m%d')}"
    elif strategy == "count_based":
        batches_dir = _get_batches_dir(project_root)
        batches_dir.mkdir(parents=True, exist_ok=True)
        existing = [d for d in batches_dir.iterdir() if d.is_dir() and d.name.startswith("batch-")]
        batch_id = f"batch-{len(existing) + 1:03d}"
    else:  # monthly (default)
        batch_id = now.strftime("%Y-%m-%d")

    batch_dir = _get_batches_dir(project_root) / batch_id

    # Handle same-day collision
    if batch_dir.exists():
        batch_id = now.strftime("%Y-%m-%d-%H%M")
        batch_dir = _get_batches_dir(project_root) / batch_id

    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "items").mkdir(exist_ok=True)

    # V3.0.5: max_items 从 lite.yaml 读取（默认 20）
    batch_cfg = _read_batch_config(project_root)
    max_items = int(batch_cfg.get("max_items", 20) or 20)

    stdd_yaml = batch_dir / ".fstdd.yaml"
    stdd_yaml.write_text(yaml.dump({
        "mode": "batch",
        "batch_type": strategy,
        "batch_id": batch_id,
        "description": "",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "closed_at": None,
        "max_items": max_items,
        "items": [],
        # V3.0.5: 批级 mini-STDD 管线（batch open → proposal → gate 1/2 → child → deliver）
        "current_phase": "understand",
        "phases": {
            "understand": {"status": "pending"},
            "spec": {"status": "pending"},
            "build": {"status": "pending"},
            "deliver": {"status": "pending"},
        },
    }, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    return batch_dir


def _close_batch(batch_dir: Path) -> None:
    """Close a batch and generate archive-summary.md."""
    import yaml
    now = datetime.now().isoformat()

    stdd_yaml = batch_dir / ".fstdd.yaml"
    data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) if stdd_yaml.exists() else {}
    data["closed_at"] = now
    stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    # Generate summary
    desc = data.get("description", "")
    items = data.get("items", [])
    lines = [f"# Batch {batch_dir.name} — 归档摘要", ""]
    if desc:
        lines.append(f"**描述:** {desc}")
        lines.append("")
    lines.append(f"- 闭合时间: {now}")
    lines.append(f"- 变更数量: {len(items)}")
    lines.append(f"- 批次策略: {data.get('batch_type', 'monthly')}")
    lines.append("")
    lines.append("## 变更列表")
    lines.append("")
    for item in items:
        timestamp = item.get("added_at", "")
        description = item.get("description", str(item))
        lines.append(f"- [{timestamp}] {description}")
    lines.append("")

    (batch_dir / "archive-summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ 批次 {batch_dir.name} 已闭合 ({len(items)} 项)")


# ------- new commands (V2.9.3) -------

def _cmd_batch_open(project_root: Path, description: str = "", strategy: str = "monthly") -> None:
    """Open a new batch. Validates scope before opening.

    V2.9.3: Scope validation. If the description signals a large change,
    the batch is rejected and full STDD is recommended.
    """
    # V2.9.3: Validate scope
    if description:
        scope = _classify_description(description)
        if scope == _SCOPE_LARGE:
            print(f"  🚫 batch 不适合大型变更。")
            print(f"     描述 '{description}' 被判定为 {scope} 级别。")
            print(f"     请用 full STDD 流程:")
            print(f"       /stdd-understand")
            return
        if scope == _SCOPE_MEDIUM:
            print(f"  ⚠️  描述 '{description}' 看起来是中等规模变更。")
            print(f"     batch 适合微修复 (<5 文件, <100 行)。")
            print(f"     如果确认只用 batch，请用更小的描述重新 open。")
            print(f"     如果是较大改动，建议: /stdd-understand")
            return

    # V2.9.4: Warn if an active STDD change exists (batch should not replace full flow)
    import yaml as _yaml
    changes_dir = project_root / ".fstdd" / "changes"
    if changes_dir.is_dir():
        for cd in sorted(
            [d for d in changes_dir.iterdir() if d.is_dir() and d.name != "_batch"],
            key=lambda d: d.stat().st_mtime, reverse=True,
        ):
            stdd_yaml = cd / ".fstdd.yaml"
            if stdd_yaml.exists():
                cd_data = _yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
                phase = cd_data.get("current_phase") or cd_data.get("phase", "")
                if phase in ("build", "deliver") and cd_data.get("status") == "active":
                    print(f"  ⚠️  检测到进行中的 change: {cd.name} (phase: {phase})")
                    print(f"     建议在此 change 中完成修改，而非单独开 batch。")
                    print(f"     继续创建 batch 请确认。")
                    break

    # Close existing open batch if any
    existing = _find_open_batch(project_root)
    if existing:
        print(f"  已有打开批次 {existing.name}，先闭合...")
        _close_batch(existing)

    batch_dir = _create_batch(project_root, strategy)

    if description:
        import yaml
        stdd_yaml = batch_dir / ".fstdd.yaml"
        data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
        data["description"] = description
        stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    print(f"  ✅ 批次已打开: {batch_dir.name}")
    if description:
        print(f"     范围判定: {_classify_description(description)}")
        print(f"     {description}")
    print(f"  💡 现在可以直接编辑文件，Guard 已放行。")
    print(f"     用 'stdd batch add <描述>' 记录每次修复")
    print(f"     完成后 'stdd batch close' 闭合批次")


def _cmd_batch_add(project_root: Path, description: str) -> None:
    """Add an item to the current open batch.

    V2.9.4: Refuses if >3 files have been modified since batch opened,
    suggesting upgrade to a full STDD change instead.
    """
    batch = _find_open_batch(project_root)
    if batch is None:
        print("  当前无打开的批次。请先 'stdd batch open \"描述\"'")
        return

    import yaml
    import subprocess
    stdd_yaml = batch / ".fstdd.yaml"
    data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))

    # V2.9.4/V3.0.5: Check git diff scope — >5 warn, >10 block (对齐 guard 5-warn/10-block)
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(project_root), timeout=5,
        )
        if result.returncode == 0:
            changed = [f for f in result.stdout.strip().split("\n") if f]
            if len(changed) > 10:
                print(f"  🚫 已修改 {len(changed)} 个文件，超出 batch 适用范围。")
                print(f"     请用 'stdd new <name>' 创建 change 走完整 STDD 流程。")
                return
            elif len(changed) > 5:
                print(f"  ⚠️  已修改 {len(changed)} 个文件，超过 batch 常规范围 (≤5)。")
                print(f"     如需完整流程请用 'stdd new <name>'；继续 add 请确认。")
    except Exception:
        pass  # git not available — skip check

    items = data.get("items", [])
    max_items = data.get("max_items", 20)
    if len(items) >= max_items:
        print(f"  批次已满 ({max_items} 项)，请升级为 change 或先 close 再 open 新批次。")
        return

    items.append({
        "description": description,
        "added_at": datetime.now().isoformat(),
    })
    data["items"] = items
    stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    print(f"  ✅ [{len(items)}/{max_items}] {description}")


def _cmd_batch_archive(project_root: Path) -> None:
    """Close batch (if open) and archive it to archive/."""
    import yaml

    batch = _find_open_batch(project_root)
    if batch is None:
        # Try to find the most recent closed batch to archive
        batches_dir = _get_batches_dir(project_root)
        if not batches_dir.is_dir():
            print("  无批次可归档")
            return

        closed_batches = []
        for d in batches_dir.iterdir():
            if not d.is_dir():
                continue
            stdd_yaml = d / ".fstdd.yaml"
            if stdd_yaml.exists():
                data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
                if data and data.get("closed_at"):
                    closed_batches.append(d)
        if not closed_batches:
            print("  无已闭合批次可归档。请先 'stdd batch open' 创建批次。")
            return
        batch = max(closed_batches, key=lambda d: d.stat().st_mtime)
        print(f"  选取最近闭合批次: {batch.name}")
    else:
        # Close it first
        _close_batch(batch)

    # Move to archive
    archive_dir = project_root / ".fstdd" / "archive"
    archive_dir.mkdir(exist_ok=True)

    dest = archive_dir / batch.name
    if dest.exists():
        # Add suffix to avoid collision
        dest = archive_dir / f"{batch.name}-{datetime.now().strftime('%H%M%S')}"

    shutil.move(str(batch), str(dest))

    # Generate an archive index entry
    import yaml
    stdd_yaml = dest / ".fstdd.yaml"
    items_count = 0
    if stdd_yaml.exists():
        data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
        items_count = len(data.get("items", []))

    print(f"  ✅ 批次已归档: archive/{dest.name}")
    print(f"     包含 {items_count} 项变更")


# ------- existing commands -------

def _cmd_batch_status(project_root: Path) -> None:
    """Show current batch status."""
    batch = _find_open_batch(project_root)
    if batch is None:
        print("  当前无打开的批次")
        print("  用 'stdd batch open \"描述\"' 开始一个调试/修复批次")
        return

    import yaml
    data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
    items = data.get("items", [])
    desc = data.get("description", "")
    print(f"  批次: {batch.name}")
    if desc:
        print(f"  描述: {desc}")
    print(f"  策略: {data.get('batch_type', 'monthly')}")
    print(f"  创建: {data.get('created_at', '?')}")
    # V3.0.5: 批级 mini-STDD 管线状态
    phase = data.get("current_phase", "")
    gates = data.get("phases", {})
    g1 = "✅" if gates.get("understand", {}).get("status") == "completed" else "○"
    g2 = "✅" if gates.get("spec", {}).get("status") == "completed" else "○"
    g3 = "✅" if gates.get("build", {}).get("status") == "completed" else "○"
    print(f"  管线: {g1} G1(理解)  {g2} G2(规格)  {g3} G3(build)  当前: {phase or 'understand'}")
    print(f"  变更数: {len(items)}/{data.get('max_items', 20)}")
    if items:
        for i, item in enumerate(items, 1):
            ts = item.get("added_at", "")[:16] if isinstance(item, dict) else ""
            desc_text = item.get("description", str(item)) if isinstance(item, dict) else str(item)
            print(f"    {i}. [{ts}] {desc_text}")


def _cmd_batch_list(project_root: Path) -> None:
    """List all batch directories."""
    batches_dir = _get_batches_dir(project_root)
    if not batches_dir.is_dir():
        print("  无批次目录")
        return

    import yaml
    batches = sorted(
        [d for d in batches_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name, reverse=True,
    )
    if not batches:
        print("  无批次")
        return

    print(f"  批次列表 ({len(batches)}):")
    for b in batches:
        stdd_yaml = b / ".fstdd.yaml"
        desc = ""
        n_items = 0
        status = "?"
        if stdd_yaml.exists():
            data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
            if data.get("closed_at"):
                status = "已闭合"
            else:
                status = "进行中"
            desc = data.get("description", "")
            n_items = len(data.get("items", []))
        print(f"    {b.name}  [{status}] ({n_items}项) {desc[:40]}")


def _cmd_batch_close(project_root: Path, force: bool = False) -> None:
    """Close the current open batch.

    V2.9.4: Warns if batch has ≤1 item and has been open <1 hour, unless --force.
    """
    import yaml
    batch = _find_open_batch(project_root)
    if batch is None:
        print("  当前无打开的批次可闭合")
        return

    # V2.9.4: Lightweight guard — warn if closing a near-empty young batch
    if not force:
        stdd_yaml = batch / ".fstdd.yaml"
        if stdd_yaml.exists():
            data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
            items = data.get("items", [])
            created_str = data.get("created_at", "")
            if len(items) <= 1 and created_str:
                try:
                    created = datetime.fromisoformat(created_str)
                    age_minutes = (datetime.now() - created).total_seconds() / 60
                    if age_minutes < 60:
                        print(f"  ⚠️  批次仅 {len(items)} 项、才开了 {int(age_minutes)} 分钟。")
                        print(f"     batch 适合收纳多个小修复，不建议频繁开关。")
                        print(f"     如果确认要闭合，请用 'stdd batch close --force'。")
                        return
                except ValueError:
                    pass

    _close_batch(batch)


# ------- V3.0.5 batch pipeline (mini-STDD) -------

def _read_batch_state(batch: Path) -> dict:
    import yaml
    return yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8")) or {}


def _write_batch_state(batch: Path, data: dict) -> None:
    import yaml
    (batch / ".fstdd.yaml").write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8")


def _update_batch_phase(batch: Path, phase: str) -> None:
    """Set batch current_phase."""
    data = _read_batch_state(batch)
    data["current_phase"] = phase
    _write_batch_state(batch, data)


def _cmd_batch_proposal(project_root: Path, batch: Path, description: str = "") -> None:
    """Write batch-level proposal.yaml + design.md (V3.0.5 pipeline)."""
    batch_id = batch.name
    canon_dir = batch / "canonical"
    proposals_dir = canon_dir / "proposals"
    designs_dir = canon_dir / "designs"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    designs_dir.mkdir(parents=True, exist_ok=True)

    from .canon import CANONICAL_PROPOSAL_TEMPLATE
    now = datetime.now().isoformat()

    proposal_file = proposals_dir / f"{batch_id}.yaml"
    if not proposal_file.exists():
        proposal_file.write_text(
            CANONICAL_PROPOSAL_TEMPLATE.format(change_name=batch_id, created_at=now),
            encoding="utf-8")
        # Fill in description as title if provided
        if description:
            import yaml
            data = yaml.safe_load(proposal_file.read_text(encoding="utf-8"))
            data["meta"]["title"] = description
            proposal_file.write_text(
                yaml.dump(data, allow_unicode=True, default_flow_style=False),
                encoding="utf-8")

    # design.md — copy template if available
    design_md = batch / "design.md"
    if not design_md.exists():
        tmpl = project_root / ".fstdd" / "templates" / "design.md"
        if tmpl.exists():
            shutil.copy2(tmpl, design_md)
        else:
            design_md.write_text(
                f"# Batch {batch_id} — 批级设计\n\n{description}\n", encoding="utf-8")

    if description:
        data = _read_batch_state(batch)
        data["description"] = description
        _write_batch_state(batch, data)

    print(f"  ✅ 批级 proposal 已写入: canonical/proposals/{batch_id}.yaml")
    print(f"     design.md 已就绪")
    print(f"     下一步: stdd batch gate --gate 1  确认 Gate 1（自动生成 proposal.md）")


def _cmd_batch_gate(project_root: Path, batch: Path, gate_num: int,
                    confirmed_by: str = "", evidence: str = "") -> None:
    """Batch-level Gate confirmation (V3.0.5 pipeline).

    V3.0.5: 批级 Gate 强制 confirmed_by 通道声明（省略 → 拒绝，不再静默确认），落审计字段。
    """
    from .gate import _check_gate_order, _confirm_gate, _auto_generate_human_views

    if confirmed_by not in ("dialog", "file_token", "cli"):
        print("  🚫 批级 Gate 需要 confirmed_by 通道声明:")
        print("     stdd batch gate --gate N --confirmed-by dialog --evidence \"用户确认原文\"")
        return

    valid, err = _check_gate_order(gate_num, batch)
    if not valid:
        print(f"  {err}")
        return

    _auto_generate_human_views(project_root, batch, gate_num)
    result = _confirm_gate(gate_num, batch, confirmed_by=confirmed_by, evidence=evidence)
    print(f"  {result}")

    # Advance batch phase
    if gate_num == 1:
        _update_batch_phase(batch, "spec")
        print("  Phase: understand → spec")
        print("     下一步: stdd batch proposal 或确认批级 spec 后 gate 2")
    elif gate_num == 2:
        _update_batch_phase(batch, "build")
        print("  Phase: spec → build")
        print("     下一步: stdd batch child add <name> \"<描述>\" 创建子 change")


def _cmd_batch_child_add(project_root: Path, batch: Path, name: str, description: str) -> None:
    """Create a child change under the batch (V3.0.5 pipeline, starts at build)."""
    import re as _re
    if not _re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9_.]{1,49}\Z", name):
        print(f"  无效的子 change 名称: {name}")
        return

    data = _read_batch_state(batch)
    if data.get("phases", {}).get("spec", {}).get("status") != "completed":
        print(f"  🚫 批级尚未通过 Gate 2。请先:")
        print(f"     stdd batch proposal <描述>  → 写批级 proposal")
        print(f"     stdd batch gate --gate 1    → 确认理解")
        print(f"     stdd batch gate --gate 2    → 确认规格")
        return

    import yaml
    from datetime import date
    today = date.today().isoformat()
    child_dir = batch / "changes" / f"{today}-{name}"
    if child_dir.exists():
        print(f"  子 change 已存在: {child_dir.name}")
        return

    (child_dir / "specs").mkdir(parents=True)
    b_understand = data.get("phases", {}).get("understand", {})
    b_spec = data.get("phases", {}).get("spec", {})

    child_state = {
        "version": "3.0",
        "change_id": f"{today}-{name}",
        "status": "active",
        "current_phase": "build",
        "mode": "standard",
        "task_type": "code",
        "parent_batch": batch.name,          # V3.0.5: 批级子 change 标记
        "description": description,
        "complexity_score": None,
        "score_confidence": None,
        "phases": {
            # V3.0.5: 继承批级 confirmed_at + 审计链（confirmed_by/confirmed_actor），从 build 起步
            "understand": {
                "status": "completed",
                "confirmed_at": b_understand.get("confirmed_at", ""),
                "confirmed_by": b_understand.get("confirmed_by", ""),
                "confirmed_actor": b_understand.get("confirmed_actor", ""),
            },
            "spec": {
                "status": "completed",
                "confirmed_at": b_spec.get("confirmed_at", ""),
                "confirmed_by": b_spec.get("confirmed_by", ""),
                "confirmed_actor": b_spec.get("confirmed_actor", ""),
            },
            "build": {"status": "pending"},
            "deliver": {"status": "pending"},
        },
        "design_adjustments": {"count": 0},
        "traceability": {"spec_scenarios": 0, "tc_cases": 0, "test_functions": 0},
    }
    (child_dir / ".fstdd.yaml").write_text(
        yaml.dump(child_state, allow_unicode=True, default_flow_style=False),
        encoding="utf-8")

    # Scaffold canonical for child (code spec template)
    from .canon import CANONICAL_CODE_SPEC_TEMPLATE
    child_canon = child_dir / "canonical" / "specs" / "code"
    child_canon.mkdir(parents=True)
    spec_file = child_canon / f"{today}-{name}.yaml"
    if not spec_file.exists():
        spec_file.write_text(
            CANONICAL_CODE_SPEC_TEMPLATE.format(
                change_name=f"{today}-{name}",
                created_at=datetime.now().isoformat()),
            encoding="utf-8")

    # Link batch description into child proposal.md (inherited)
    (child_dir / "proposal.md").write_text(
        f"# 子 change: {today}-{name}\n\n"
        f"> 批级: {batch.name} | {description}\n",
        encoding="utf-8")

    print(f"  ✅ 子 change 已创建: {child_dir.name}")
    print(f"     从 build 阶段起步（继承批级 Gate 1/2）")
    print(f"     在子 change 内完成 TDD 实现，证据写入其 .fstdd.yaml")


def _cmd_batch_deliver(project_root: Path, batch: Path,
                       confirmed_by: str = "", evidence: str = "") -> None:
    """Aggregate child change evidence → batch test-report.md → merge specs → close (V3.0.5).

    V3.0.5: Gate 3 确认必须带 confirmed_by 通道声明（省略 → 拒绝），不再静默自动确认。
    """
    import yaml
    # V3.0.5: Gate 3 通道声明必填
    if confirmed_by not in ("dialog", "file_token", "cli"):
        print("  🚫 批级 deliver 需要 Gate 3 确认通道声明:")
        print("     stdd batch deliver --confirmed-by dialog --evidence \"用户确认原文\"")
        return

    children_dir = batch / "changes"
    if not children_dir.is_dir():
        print("  批次下无子 change。先 'stdd batch child add <name> \"<描述>\"'")
        return

    children = sorted([d for d in children_dir.iterdir() if d.is_dir()])
    if not children:
        print("  批次下无子 change。先 'stdd batch child add <name> \"<描述>\"'")
        return

    # Aggregate evidence from each child
    rows = []
    total_tests = 0
    total_new = 0
    incomplete = []
    for child in children:
        stdd_yaml = child / ".fstdd.yaml"
        if not stdd_yaml.exists():
            incomplete.append(child.name)
            continue
        cdata = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
        slices = (cdata.get("phases", {}) or {}).get("build", {}).get("slices_completed", {}) or {}
        child_tests = 0
        child_new = 0
        for sl in slices.values():
            cov = str(sl.get("tc_coverage", "0/0"))
            try:
                child_tests += int(cov.split("/")[-1])
            except (ValueError, IndexError):
                pass
            child_new += int(sl.get("new_tests", 0) or 0)
        # test-report.md exists → build complete
        build_done = (cdata.get("phases", {}) or {}).get("build", {}).get("status") == "completed" \
                     or (child / "test-report.md").exists()
        if not build_done:
            incomplete.append(child.name)
        rows.append((child.name, child_tests, child_new, "✅" if build_done else "⏳"))
        total_tests += child_tests
        total_new += child_new

    if incomplete:
        print("  ⚠️  以下子 change 尚未完成 build：")
        for name in incomplete:
            print(f"     - {name}  (需 Gate 3 确认 或 生成 test-report.md)")
        return

    # Merge child specs into batch-level specs/
    merged_specs = 0
    batch_specs = batch / "specs"
    for child in children:
        child_specs = child / "specs"
        if child_specs.is_dir():
            for cap_dir in child_specs.iterdir():
                if cap_dir.is_dir():
                    dest = batch_specs / cap_dir.name
                    dest.mkdir(parents=True, exist_ok=True)
                    for md in cap_dir.glob("*.md"):
                        shutil.copy2(md, dest / md.name)
                        merged_specs += 1

    # Batch test-report.md
    now = datetime.now().isoformat()
    lines = [f"# Batch {batch.name} — 批级交付报告", "",
             f"- 生成时间: {now}",
             f"- 子 change 数: {len(children)}",
             f"- 累计测试: {total_tests}（新增 {total_new}）",
             f"- 合并 specs: {merged_specs} 个文件", ""]
    lines.append("## 子 change 证据链")
    lines.append("")
    lines.append("| 子 change | 测试数 | 新增 | 状态 |")
    lines.append("| --- | --- | --- | --- |")
    for name, t, n, s in rows:
        lines.append(f"| {name} | {t} | {n} | {s} |")
    lines.append("")
    (batch / "test-report.md").write_text("\n".join(lines), encoding="utf-8")

    # Confirm batch build + set deliver (V3.0.5: 带 confirmed_by 通道声明，落审计字段)
    from .gate import _confirm_gate
    try:
        _confirm_gate(3, batch, confirmed_by=confirmed_by, evidence=evidence)
    except Exception:
        pass
    _update_batch_phase(batch, "deliver")

    print(f"  ✅ 批级交付完成: test-report.md 已生成")
    print(f"     累计 {total_tests} 测试（新增 {total_new}），合并 {merged_specs} 个 spec")
    print(f"     批次当前阶段: deliver")
    print(f"     下一步: stdd batch close 闭合批次")


# ------- dispatcher -------

def cmd_batch(args: argparse.Namespace) -> None:
    """Entry point for batch command."""
    project_root = Path.cwd()
    action = getattr(args, "action", "status")

    if action == "open":
        description = getattr(args, "description", "") or ""
        strategy = getattr(args, "strategy", "monthly") or "monthly"
        _cmd_batch_open(project_root, description, strategy)
    elif action == "add":
        description = getattr(args, "description", None)
        if not description:
            print("  用法: stdd batch add \"修复描述\"")
            return
        _cmd_batch_add(project_root, description)
    elif action == "archive":
        _cmd_batch_archive(project_root)
    elif action == "close":
        _cmd_batch_close(project_root, force=getattr(args, "force", False))
    elif action == "list":
        _cmd_batch_list(project_root)
    # V3.0.5: batch pipeline (mini-STDD) subcommands
    elif action == "proposal":
        batch = _find_open_batch(project_root)
        if batch is None:
            print("  当前无打开的批次。请先 'stdd batch open \"描述\"'")
            return
        _cmd_batch_proposal(project_root, batch, getattr(args, "description", "") or "")
    elif action == "gate":
        batch = _find_open_batch(project_root)
        if batch is None:
            print("  当前无打开的批次。请先 'stdd batch open \"描述\"'")
            return
        gate_num = getattr(args, "gate", None)
        if gate_num not in (1, 2):
            print("  用法: stdd batch gate --gate 1|2 --confirmed-by dialog|file_token|cli")
            return
        _cmd_batch_gate(project_root, batch, gate_num,
                        confirmed_by=getattr(args, "confirmed_by", "") or "",
                        evidence=getattr(args, "evidence", "") or "")
    elif action == "child":
        sub = getattr(args, "child_action", "status")
        batch = _find_open_batch(project_root)
        if batch is None:
            print("  当前无打开的批次。请先 'stdd batch open \"描述\"'")
            return
        if sub == "add":
            name = getattr(args, "name", None)
            if not name:
                print("  用法: stdd batch child add <name> \"<描述>\"")
                return
            _cmd_batch_child_add(project_root, batch, name, getattr(args, "description", "") or "")
        else:
            _cmd_batch_child_list(batch)
    elif action == "deliver":
        batch = _find_open_batch(project_root)
        if batch is None:
            print("  当前无打开的批次。请先 'stdd batch open \"描述\"'")
            return
        _cmd_batch_deliver(project_root, batch,
                           confirmed_by=getattr(args, "confirmed_by", "") or "",
                           evidence=getattr(args, "evidence", "") or "")
    else:  # status
        _cmd_batch_status(project_root)


def _cmd_batch_child_list(batch: Path) -> None:
    """List child changes under the batch (V3.0.5)."""
    import yaml
    children_dir = batch / "changes"
    if not children_dir.is_dir():
        print("  批次下无子 change。用 'stdd batch child add <name> \"<描述>\"' 创建")
        return
    children = sorted([d for d in children_dir.iterdir() if d.is_dir()])
    if not children:
        print("  批次下无子 change。用 'stdd batch child add <name> \"<描述>\"' 创建")
        return
    print(f"  子 change ({len(children)}):")
    for c in children:
        stdd_yaml = c / ".fstdd.yaml"
        phase = "?"
        if stdd_yaml.exists():
            data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
            phase = data.get("current_phase", "?")
        print(f"    - {c.name}  [phase: {phase}]")
