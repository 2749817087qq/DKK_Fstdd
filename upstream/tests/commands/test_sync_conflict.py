"""Slice 5 契约测试：同步冲突策略（C5 / REQ-005，TC-ECON-001..003）。

对应 spec：
- SC-020 同 eid 多节点编辑 → 以 updated_at 较新者为胜出版本
- SC-021 被覆盖的旧版本写入冲突日志（含 eid / 双方 updated_at / 落点），绝不静默丢弃
- SC-022 并发合并经索引锁保证不出现半写索引或竞争损坏
"""
import threading
from pathlib import Path

import yaml


def _write_exp(d: Path, eid: str, *, pattern, updated_at):
    d.mkdir(parents=True, exist_ok=True)
    fm = {
        "experience_id": eid, "category": "tooling", "severity": "medium",
        "pattern": pattern, "occurrences": 1, "lifecycle_state": "deposited",
        "updated_at": updated_at, "first_seen": "2026-09-01", "last_seen": "2026-10-01",
    }
    (d / f"{eid}.md").write_text(
        f"---\n{yaml.dump(fm, allow_unicode=True)}---\n\nbody\n", encoding="utf-8")


def _pattern_of(d: Path, eid: str):
    p = d / f"{eid}.md"
    fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1]) or {}
    return fm.get("pattern")


def test_econ001_lww_newer_wins(tmp_path):
    """TC-ECON-001 / SC-020：updated_at 较新者胜出。"""
    from fstdd.cli.commands import _exp_sync

    local = tmp_path / "local"
    remote = tmp_path / "remote"
    _write_exp(local, "EXP-X", pattern="old-version", updated_at="2026-10-01T00:00:00+00:00")
    _write_exp(remote, "EXP-X", pattern="new-version", updated_at="2026-10-05T00:00:00+00:00")

    stats = _exp_sync.sync_pull(local, remote, conflict_log_path=tmp_path / "conflicts.tsv")
    assert _pattern_of(local, "EXP-X") == "new-version"
    assert stats["updated"] >= 1

    # 反向：远端更旧时本地保持不变
    _write_exp(remote, "EXP-X", pattern="stale-version", updated_at="2026-09-01T00:00:00+00:00")
    _exp_sync.sync_pull(local, remote, conflict_log_path=tmp_path / "conflicts.tsv")
    assert _pattern_of(local, "EXP-X") == "new-version"


def test_econ002_conflict_log_written(tmp_path):
    """TC-ECON-002 / SC-021：冲突旧版本写入冲突日志，不静默丢弃。"""
    from fstdd.cli.commands import _exp_sync

    local = tmp_path / "local"
    remote = tmp_path / "remote"
    log = tmp_path / "conflicts.tsv"
    _write_exp(local, "EXP-X", pattern="old-version", updated_at="2026-10-01T00:00:00+00:00")
    _write_exp(remote, "EXP-X", pattern="new-version", updated_at="2026-10-05T00:00:00+00:00")

    stats = _exp_sync.sync_pull(local, remote, conflict_log_path=log)
    assert stats["conflicts"], "应记录冲突"
    assert log.is_file()
    text = log.read_text(encoding="utf-8")
    assert "EXP-X" in text
    assert "2026-10-01T00:00:00+00:00" in text   # 旧版 updated_at
    assert "2026-10-05T00:00:00+00:00" in text   # 新版 updated_at


def test_econ003_concurrent_merge_no_corruption(tmp_path):
    """TC-ECON-003 / SC-022：并发合并不产生半写/损坏（索引可解析、条目齐全）。"""
    from fstdd.cli.commands import _exp_sync

    local = tmp_path / "local"
    local.mkdir(parents=True, exist_ok=True)
    remotes = []
    for i in range(3):
        r = tmp_path / f"remote{i}"
        _write_exp(r, f"EXP-T{i}", pattern=f"p{i}", updated_at="2026-10-05T00:00:00+00:00")
        remotes.append(r)

    errors = []

    def _worker(r):
        try:
            _exp_sync.sync_pull(local, r, conflict_log_path=tmp_path / "c.tsv")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_worker, args=(r,)) for r in remotes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    eids = set()
    for p in local.glob("EXP-*.md"):
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---"), f"半写文件: {p.name}"
        fm = yaml.safe_load(text.split("---", 2)[1]) or {}
        eids.add(fm.get("experience_id"))
    assert {"EXP-T0", "EXP-T1", "EXP-T2"} <= eids
