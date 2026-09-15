"""STDD phase constants — single source of truth for the phase model (V3.0.5).

Consolidates the phase order, labels, gate mapping, edit-permission map, and
legacy aliases that were previously duplicated across phase.py / guard.py /
status.py / validate.py / new.py. Keeping the drift out of five copies prevents
the class of bug where `phase4.slices_completed` and `phases.build.slices_completed`
diverge. This module is pure data with no imports of other command modules,
so it cannot introduce an import cycle.
"""

# ── 4-phase model (V3.0.5: SLICE + BUILD + VERIFY merged into one BUILD) ──
PHASE_ORDER = ["understand", "spec", "build", "deliver"]

PHASE_LABELS = {
    "understand": "Phase 1: UNDERSTAND",
    "spec": "Phase 2: SPEC",
    "build": "Phase 3: BUILD",
    "deliver": "Phase 4: DELIVER",
}

# Gate numbering stays 1/2/3 (GATE<N>_APPROVED file tokens depend on it).
# Gate 3 now confirms the merged BUILD phase.
GATE_PHASES = {
    "understand": "Gate 1",
    "spec": "Gate 2",
    "build": "Gate 3",
}

# Phase names that gate before advancing. Order must match GATE_PHASES.
GATE_PHASE_ORDER = ["understand", "spec", "build"]

# Edit permissions per task_type. DELIVER stays editable because it performs
# file writes (spec merges, version bumps, README/CHANGELOG edits).
EDITABLE_PHASES_BY_TYPE = {
    "code": {"build", "deliver"},
    "documentation": {"understand", "spec", "build", "deliver"},
    "configuration": {"understand", "spec", "build", "deliver"},
    "data-migration": {"build", "deliver"},
    "dependency-upgrade": {"build", "deliver"},
}

# Fallback when task_type is unknown.
EDITABLE_PHASES = {"build", "deliver"}

# Legacy 6-phase active states → normalized to the merged 4-phase model.
# Old `.stdd.yaml` state files (archive, bootcamp samples) used slice/verify.
LEGACY_PHASE_MAP = {
    "slice": "build",
    "verify": "build",
}

# Canonical path to per-slice verification evidence.
SLICES_COMPLETED_PATH = ("phases", "build", "slices_completed")
