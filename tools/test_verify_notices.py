"""Tests for tools/verify_notices.py — 21 TC per test-plan.md.

Covers:
  REQ-001..005 / SC-001..015  → TC-NAV-001..018
  REQ-006     / SC-016..018   → TC-NEP-001..003

RED phase (CP-001): all tests must fail with ModuleNotFoundError: verify_notices.
GREEN phase (CP-002..006): implement tools/verify_notices.py to make all 21 pass.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
DAILY_SHARE = TOOLS_DIR / "fstdd003_daily_share.py"
VERIFY_SCRIPT = TOOLS_DIR / "verify_notices.py"
GITIGNORE = REPO_ROOT / ".gitignore"
TOKEN_FILE = REPO_ROOT / ".fstdd" / "_fstdd003_token.txt"
SHARE_LOG = REPO_ROOT / ".fstdd" / "_fstdd003_share_log.json"

KNOWN_TOKEN = "fs9k2m7x4q1w8e5r"

sys.path.insert(0, str(TOOLS_DIR))


def _md5_12(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()[:12]


def _md5_of_file(p: Path) -> str:
    return _md5_12(p.read_bytes())


def _write_manifest(root: Path, entries):
    lines = [
        "| 文件名 | md5 前12位 | 落盘时间 | 发出者 |",
        "| --- | --- | --- | --- |",
    ]
    for name, md5, ts, by in entries:
        lines.append(f"| {name} | {md5} | {ts} | {by} |")
    (root / "00-SIGNATURES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _register_files(root: Path, files):
    entries = [(f.name, _md5_of_file(f), "2026-09-19T00:00:00", "K") for f in files]
    _write_manifest(root, entries)


def _notice_with_credential(token: str = KNOWN_TOKEN) -> str:
    return f"# Test notice\n\nX-FSTDD-Token: {token}\n\nDo something.\n"


DEFAULT_QUARANTINE = TOOLS_DIR / "_quarantine"


@pytest.fixture(autouse=True)
def _ensure_quarantine_dir():
    DEFAULT_QUARANTINE.mkdir(parents=True, exist_ok=True)
    for p in list(DEFAULT_QUARANTINE.glob("*")):
        if p.is_file():
            p.unlink()
    yield


def _run_cli(dir_path, extra_args=None, cwd=None):
    return subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), str(dir_path)] + (extra_args or []),
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd or REPO_ROOT),
    )


# =============================================================================
# REQ-001 (TC-NAV-001..003) — manifest classification
# =============================================================================

def test_TC_NAV_001_manifest_hit_verified(tmp_path):
    from verify_notices import classify_notice

    f = tmp_path / "FSTDD003收-示例.md"
    f.write_text("hello K\n", encoding="utf-8")
    _write_manifest(tmp_path, [(f.name, _md5_of_file(f), "2026-09-19T00:00:00", "K")])

    result = classify_notice(f)
    assert result["status"] == "verified"
    assert "reason" not in result
    assert result["filename"] == f.name
    assert result["md5_prefix"] == _md5_of_file(f)
    assert len(result["md5_prefix"]) == 12
    assert result["emitted_by"] == "K"


def test_TC_NAV_002_tampered_md5_mismatch(tmp_path):
    from verify_notices import classify_notice

    f = tmp_path / "FSTDD003收-示例.md"
    f.write_text("original\n", encoding="utf-8")
    orig_md5 = _md5_of_file(f)
    _write_manifest(tmp_path, [(f.name, orig_md5, "2026-09-19T00:00:00", "K")])
    f.write_text("tampered content\n", encoding="utf-8")
    actual = _md5_of_file(f)

    result = classify_notice(f)
    assert result["status"] == "unverified"
    assert result["reason"] == "md5_mismatch"
    assert result["expected_md5_prefix"] == orig_md5
    assert result["actual_md5_prefix"] == actual
    blob = json.dumps(result, ensure_ascii=False)
    for frag in ("tampered", "content", "original"):
        assert frag not in blob, f"body fragment leaked: {frag}"


def test_TC_NAV_003_not_in_manifest(tmp_path):
    from verify_notices import classify_notice

    _write_manifest(tmp_path, [])
    f = tmp_path / "FSTDD003收-陌生文件.md"
    f.write_text("hello\n", encoding="utf-8")

    result = classify_notice(f)
    assert result["status"] == "unverified"
    assert result["reason"] == "not_in_manifest"
    assert "expected_md5_prefix" not in result


# =============================================================================
# REQ-002 (TC-NAV-004, 005) — manifest missing / empty degradation
# =============================================================================

def test_TC_NAV_004_manifest_missing_nonstrict(tmp_path):
    import verify_notices as vn

    files = []
    for i in range(3):
        p = tmp_path / f"FSTDD003收-通知{i}.md"
        p.write_text(f"body {i}\n", encoding="utf-8")
        files.append(p)

    snapshots = {f.name: (f.read_bytes(), f.stat().st_mtime_ns) for f in files}

    result = vn.verify_notices(tmp_path)
    assert len(result["results"]) == 3
    for r in result["results"]:
        assert r["status"] == "unverified"
        assert r["reason"] == "manifest_missing"
    assert len(result["warnings"]) == 1
    assert result["exit_code"] == 0
    for name, (content, mtime) in snapshots.items():
        p = tmp_path / name
        assert p.exists(), f"{name} must remain in place"
        assert p.read_bytes() == content
        assert p.stat().st_mtime_ns == mtime


def test_TC_NAV_005_empty_manifest_distinct_from_missing(tmp_path):
    import verify_notices as vn

    (tmp_path / "00-SIGNATURES.md").write_text(
        "| 文件名 | md5 前12位 | 落盘时间 | 发出者 |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
    f = tmp_path / "FSTDD003收-通知.md"
    f.write_text("body\n", encoding="utf-8")

    result = vn.verify_notices(tmp_path)
    for item in result["results"]:
        assert item["status"] == "unverified"
        assert item["reason"] == "not_in_manifest"
        assert item["reason"] != "manifest_missing"
    assert result["exit_code"] == 0
    warnings_blob = json.dumps(result["warnings"], ensure_ascii=False).lower()
    assert "missing" not in warnings_blob, "empty manifest warning must not say 'missing'"


# =============================================================================
# REQ-003 (TC-NAV-006..008) — credential sniffing + verified exemption
# =============================================================================

def test_TC_NAV_006_sniff_x_fstdd_token(tmp_path):
    from verify_notices import sniff_credential

    content = _notice_with_credential()
    hits = sniff_credential(content)
    matched = [h for h in hits if h["rule"] == "x_fstdd_token"]
    assert matched, "expected x_fstdd_token rule match"
    hit = matched[0]
    assert "match_count" in hit and hit["match_count"] >= 1
    assert KNOWN_TOKEN not in json.dumps(hit, ensure_ascii=False)


def test_TC_NAV_007_verified_with_credential_not_quarantined(tmp_path):
    import verify_notices as vn

    f = tmp_path / "FSTDD003收-带token.md"
    f.write_text(_notice_with_credential(), encoding="utf-8")
    _register_files(tmp_path, [f])

    result = vn.verify_notices(tmp_path)
    assert result["quarantined"] == []
    assert f.exists(), "verified file must not be moved"


def test_TC_NAV_008_realistic_fixtures_zero_quarantine(tmp_path):
    import verify_notices as vn

    samples = [
        ("FSTDD003收-协作通知A.md", "# 协作通知\n\nfrom: K\n\n执行如下……\n"),
        ("FSTDD003收-撤回令.md", "# 撤回令\n\n撤销 FSTDD003收-inbox鉴权上线.md\n"),
        ("FSTDD003复-回执.md", "# 回执\n\n已执行完毕。\n"),
        ("FSTDD003收-凭证验证补充.md", "## 补充问询\n\n- Q1: 凭证销毁\n- Q2: 清单\n"),
        ("FSTDD003收-账号规模扩展.md", "# 扩展预告\n\n账号 1→6\n"),
    ]
    files = []
    for name, content in samples:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        files.append(p)
    _register_files(tmp_path, files)

    result = vn.verify_notices(tmp_path)
    assert len(result["results"]) == 5
    assert all(x["status"] == "verified" for x in result["results"])
    assert result["quarantined"] == [], f"unexpected quarantine: {result['quarantined']}"


# =============================================================================
# REQ-004 (TC-NAV-009..011) — quarantine + no echo + .gitignore
# =============================================================================

def test_TC_NAV_009_move_to_quarantine_not_delete(tmp_path):
    import verify_notices as vn

    f = tmp_path / "FSTDD003收-伪造.md"
    original = _notice_with_credential().encode("utf-8")
    f.write_bytes(original)
    _write_manifest(tmp_path, [])

    result = vn.verify_notices(tmp_path)
    assert not f.exists(), "original file must be removed from source dir"
    q_file = DEFAULT_QUARANTINE / f.name
    assert q_file.exists()
    assert q_file.read_bytes() == original, "quarantined bytes must match original exactly"

    records = list(DEFAULT_QUARANTINE.glob(f"{f.name}.*"))
    rec_json = [p for p in records if p.suffix == ".json"]
    assert len(rec_json) >= 1
    rec = json.loads(rec_json[0].read_text(encoding="utf-8"))
    assert set(rec.keys()) == {"filename", "md5_prefix", "rule", "timestamp"}, (
        f"quarantine record must have exactly 4 keys, got {sorted(rec.keys())}"
    )


def test_TC_NAV_010_token_never_in_outputs(tmp_path):
    f = tmp_path / "FSTDD003收-伪造.md"
    f.write_text(_notice_with_credential(KNOWN_TOKEN), encoding="utf-8")
    _write_manifest(tmp_path, [])

    proc = _run_cli(tmp_path, ["--json"])
    assert KNOWN_TOKEN not in proc.stdout, "credential leaked to stdout"
    assert KNOWN_TOKEN not in proc.stderr, "credential leaked to stderr"

    # 隔离记录（*.json）不得含 token；隔离原文保留 token 是故意的（审计链）
    for qfile in list(DEFAULT_QUARANTINE.rglob("*.json")):
        if qfile.is_file():
            text = qfile.read_text(encoding="utf-8", errors="ignore")
            assert KNOWN_TOKEN not in text, f"credential leaked to quarantine record {qfile.name}"

    # verify_notices.py 源码不得包含任何凭证字面值
    assert VERIFY_SCRIPT.exists(), "verify_notices.py must exist for source-surface assertion"
    verify_src = VERIFY_SCRIPT.read_text(encoding="utf-8")
    assert KNOWN_TOKEN not in verify_src, (
        "verify_notices.py source must not hardcode any token literal"
    )
    for rule_name in ("x_fstdd_token", "bearer_token", "generic_secret_block", "long_alnum_block"):
        assert rule_name in verify_src, "expected credential sniff rule name missing"


def test_TC_NAV_011_quarantine_dir_gitignored():
    content = GITIGNORE.read_text(encoding="utf-8")
    assert "tools/_quarantine" in content, ".gitignore must cover tools/_quarantine/"
    proc = subprocess.run(
        ["git", "check-ignore", "-v", "tools/_quarantine/x"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0
    assert proc.stdout.strip()
    assert ".gitignore" in proc.stdout


# =============================================================================
# REQ-005 (TC-NAV-012..015) — CLI exit codes + JSON contract
# =============================================================================

def test_TC_NAV_012_nonstrict_unverified_exit_0(tmp_path):
    f = tmp_path / "FSTDD003收-通知.md"
    f.write_text("body\n", encoding="utf-8")
    _write_manifest(tmp_path, [])
    proc = _run_cli(tmp_path)
    assert proc.returncode == 0


def test_TC_NAV_013_strict_unverified_exit_3(tmp_path):
    f = tmp_path / "FSTDD003收-通知.md"
    f.write_text("body\n", encoding="utf-8")
    _write_manifest(tmp_path, [])
    proc = _run_cli(tmp_path, ["--strict"])
    assert proc.returncode == 3


def test_TC_NAV_014_quarantine_exit_2_strict_wins(tmp_path):
    import verify_notices as vn

    f = tmp_path / "FSTDD003收-伪造.md"
    f.write_text(_notice_with_credential(), encoding="utf-8")
    _write_manifest(tmp_path, [])

    proc_normal = _run_cli(tmp_path)
    assert proc_normal.returncode == 2

    for p in list(DEFAULT_QUARANTINE.glob("*")):
        if p.is_file():
            p.unlink()

    f.write_text(_notice_with_credential(), encoding="utf-8")
    proc_strict = _run_cli(tmp_path, ["--strict"])
    assert proc_strict.returncode == 3, "strict must win over quarantine (3 > 2)"


def test_TC_NAV_015_json_contract_top4keys(tmp_path):
    f = tmp_path / "FSTDD003收-通知.md"
    f.write_text("body\n", encoding="utf-8")
    _write_manifest(tmp_path, [])
    proc = _run_cli(tmp_path, ["--json"])
    data = json.loads(proc.stdout)
    assert set(data.keys()) == {"results", "quarantined", "warnings", "exit_code"}, (
        f"top-level keys must be exactly 4, got {sorted(data.keys())}"
    )
    for item in data["results"]:
        assert "status" in item
        assert "filename" in item
        assert "md5_prefix" in item
        if item["status"] == "unverified":
            assert "reason" in item


# =============================================================================
# Supplementary boundary cases (TC-NAV-016..018)
# =============================================================================

def test_TC_NAV_016_malformed_manifest_no_crash(tmp_path):
    import verify_notices as vn

    (tmp_path / "00-SIGNATURES.md").write_text(
        "# comment line\n"
        "bad row without pipes\n"
        "short|abc|only3fields\n"
        "not-12-hex|zzzzzzzzzzzz|2026-01-01|K\n"
        f"FSTDD003收-正常.md|{_md5_12('x')}|2026-01-01|K\n",
        encoding="utf-8",
    )
    f = tmp_path / "FSTDD003收-正常.md"
    f.write_text("x", encoding="utf-8")

    result = vn.verify_notices(tmp_path)
    assert result["exit_code"] == 0
    assert any(x["status"] == "verified" for x in result["results"])
    assert len(result["warnings"]) >= 1


def test_TC_NAV_017_missing_dir_graceful(tmp_path):
    import verify_notices as vn

    missing = tmp_path / "does-not-exist"
    result = vn.verify_notices(missing)
    assert result["exit_code"] == 0
    assert len(result["warnings"]) >= 1
    assert result["results"] == []
    assert result["quarantined"] == []


def test_TC_NAV_018_duplicate_manifest_first_wins(tmp_path):
    import verify_notices as vn

    f = tmp_path / "FSTDD003收-重发.md"
    f.write_text("content v1\n", encoding="utf-8")
    real = _md5_of_file(f)
    lines = [
        "| 文件名 | md5 前12位 | 落盘时间 | 发出者 |",
        "| --- | --- | --- | --- |",
        f"| {f.name} | {real} | 2026-01-01 | K |",
        f"| {f.name} | 000000000000 | 2026-01-02 | K |",
    ]
    (tmp_path / "00-SIGNATURES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = vn.verify_notices(tmp_path)
    item = next(x for x in result["results"] if x["filename"] == f.name)
    assert item["status"] == "verified", (
        f"first entry should win, got: {item}"
    )


# =============================================================================
# REQ-006 (TC-NEP-001..003) — pipeline regression protection
# =============================================================================

def test_TC_NEP_001_daily_share_untouched():
    assert DAILY_SHARE.exists()
    content = DAILY_SHARE.read_text(encoding="utf-8")
    # 1. daily_share 的正当凭证路径是新 credential.txt（不是旧 token.txt）
    assert "_fstdd003_credential.txt" in content, (
        "daily_share must reference the authorised credential file"
    )
    # 2. 旧 token.txt 只应在 docstring/注释里提到"保留现场不读取"
    #    绝不能有实际的 open/read 代码路径指向它
    import re
    # 排除注释/文档字符串的简化：检查是否存在以 pathlib.Path 或字符串拼接方式
    # 把 token.txt 作为读取目标
    code_lines = [
        ln for ln in content.splitlines()
        if not ln.strip().startswith("#") and not ln.strip().startswith('"""')
    ]
    code_blob = "\n".join(code_lines)
    # 不得把 token.txt 放进 Path(...) 构造或 open(...)
    assert re.search(r'Path\([^)]*_fstdd003_token', code_blob) is None, (
        "daily_share must not build Path to legacy token file"
    )
    # 3. 本变更对 daily_share.py 必须零 diff
    proc = subprocess.run(
        ["git", "diff", "--", "tools/fstdd003_daily_share.py"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.stdout.strip() == "", (
        f"daily_share.py must have zero diff from baseline:\n{proc.stdout}"
    )


def test_TC_NEP_002_gate_does_not_touch_share_log(tmp_path):
    import verify_notices as vn

    before_content = SHARE_LOG.read_bytes() if SHARE_LOG.exists() else None
    before_mtime = SHARE_LOG.stat().st_mtime_ns if SHARE_LOG.exists() else None

    f = tmp_path / "FSTDD003收-通知.md"
    f.write_text("body\n", encoding="utf-8")
    _write_manifest(tmp_path, [])
    vn.verify_notices(tmp_path)

    if SHARE_LOG.exists():
        after_content = SHARE_LOG.read_bytes()
        after_mtime = SHARE_LOG.stat().st_mtime_ns
        assert after_content == before_content
        assert after_mtime == before_mtime


def test_TC_NEP_003_token_file_unchanged_and_not_referenced(tmp_path):
    import verify_notices as vn

    # 与节点无关的仓库侧不变量：校验器绝不引用旧凭证文件路径。
    src = VERIFY_SCRIPT.read_text(encoding="utf-8")
    assert "_fstdd003_token.txt" not in src, "verify_notices must not reference token file path"

    # 场景节点本地前置条件：旧凭证文件是 incident 现场证据（gitignored、不随仓库分发），
    # 仅存在于事发节点。非场景节点（无该文件）跳过其"未被改动"的断言，避免误红。
    if not TOKEN_FILE.exists():
        pytest.skip("on-scene token evidence file absent on this node (node-local precondition)")

    before_content = TOKEN_FILE.read_bytes()
    before_mtime = TOKEN_FILE.stat().st_mtime_ns

    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()
    (scan_dir / "FSTDD003收-x.md").write_text("body\n", encoding="utf-8")
    vn.verify_notices(scan_dir)

    after_content = TOKEN_FILE.read_bytes()
    after_mtime = TOKEN_FILE.stat().st_mtime_ns
    assert after_content == before_content, "token file content must not change"
    assert after_mtime == before_mtime, "token file mtime must not change"
