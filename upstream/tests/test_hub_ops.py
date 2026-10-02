"""Static/read-only tests for FSTDD hub operational assets."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return (ROOT / "tools" / name).read_text(encoding="utf-8")


def test_deploy_hub_is_idempotent_and_loopback_only():
    text = read("deploy_hub.sh")
    assert "systemctl enable --now $SERVICE" in text
    assert "systemctl restart $SERVICE" in text
    assert "--host 127.0.0.1" in text
    assert "md5sum" in text
    assert "lsof -t -i:$PORT" in text
    assert "pkill" not in text
    assert "8788" in text


def test_backup_uses_sqlite_online_backup_and_retention():
    text = read("hub_backup.sh")
    assert "conn.backup(out)" in text
    assert "wal_checkpoint" in text
    assert "mtime +14" in text
    assert "rm -rf" not in text


def test_healthcheck_is_read_only():
    text = read("hub_healthcheck.py")
    assert "GET" not in text or "urlopen" in text
    assert "health" in text
    assert "systemctl" not in text
