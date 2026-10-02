"""V3.0.3: Auto-training function for bootcamp --auto mode."""


def auto_train_level(project_root, level, scenario, cert):
    """Auto-run training for a level and grade it."""
    import yaml as _yaml, argparse as _argparse
    wd = project_root / ".fstdd" / "changes" / "_bootcamp" / f"level_{level}" / "work"
    wd.mkdir(parents=True, exist_ok=True)
    cd = wd / ".fstdd" / "changes" / f"bootcamp-lv{level}"
    cd.mkdir(parents=True, exist_ok=True)
    mode = scenario.get("mode", "lightweight")
    phases = {
        "understand": {"status": "completed", "confirmed_at": "2026-07-09"},
        "spec": {"status": "completed", "confirmed_at": "2026-07-09"},
        "slice": {"status": "completed"},
        "build": {"status": "completed", "slices_completed": {"1": {"status": "done", "tc_coverage": "1/1", "new_tests": 1, "verified_at": "2026-07-09"}}},
        "verify": {"status": "completed", "confirmed_at": "2026-07-09"},
        "deliver": {"status": "completed"},
    }
    (cd / ".fstdd.yaml").write_text(_yaml.dump({
        "change_id": f"bootcamp-lv{level}", "current_phase": "deliver",
        "mode": mode, "phases": phases,
    }))

    content_map = {
        1: {".fstdd/proposal.md": "# Fix Typo

Recieve -> Receive
"},
        2: {
            ".fstdd/design.md": "# API Rate Limit Design

## Decisions
### 1. Token bucket
**Why**: Simple.
",
            ".fstdd/specs/api-rate-limit/spec.md": "# Spec

### Req: Rate limit
System SHALL enforce 100 req/min.

#### Scenario: Normal
- **GIVEN** IP has 99 req
- **WHEN** 1 more
- **THEN** SHALL return 200
",
            ".fstdd/proposal.yaml": _yaml.dump({"meta": {"change_id": f"bootcamp-lv{level}"}, "why": {"problem": "no rate limiting"}}),
            ".fstdd/test-plan.md": "# Test Plan
|TC-001|P0|Normal|
",
            ".fstdd/slices.md": "# Slice
|1|P0|TokenBucket|
",
        },
        3: {
            ".fstdd/specs/payment/spec.md": "# Payment

### Req: Alipay
System SHALL support Alipay.

#### Scenario: QR
- **GIVEN** user selects Alipay
- **WHEN** 100 CNY
- **THEN** SHALL generate QR
",
            ".fstdd/test-report.md": "# Report
15/15 passed. 14 FM: all PASS. Slice1: tc=5/5 nt=5
",
        },
        4: {
            ".fstdd/agent_spec.yaml": _yaml.dump({"agent_task_id": "task-001", "checkpoints": [{"id": "CP-1", "assertions": [{"target": "crm.balance", "value": 8000}]}]}),
        },
        5: {
            ".fstdd/specs/dashboard/spec.md": "# Dashboard

### Req: KPI
System SHALL display KPIs.

#### Scenario: Load
- **GIVEN** user has data
- **WHEN** loads
- **THEN** SHALL display
",
        },
    }

    for path, content in content_map.get(level, {}).items():
        fp = cd / path
        fp.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            fp.write_text(content)
        else:
            fp.write_text(content)

    from fstdd.cli.commands.bootcamp import cmd_bootcamp_grade
    ns = _argparse.Namespace(subcommand="grade", level=level, module=None, verbose=0)
    cmd_bootcamp_grade(ns)
