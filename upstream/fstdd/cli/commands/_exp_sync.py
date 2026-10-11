"""中心节点同步引擎（C3 / REQ-003）+ 冲突策略（C5 / REQ-005）。

- 传输层与合并层**解耦**：``push_bundle`` / ``fetch_bundle`` 是传输适配器，
  ``merge_entries`` / ``sync_pull`` 是纯合并逻辑（可离线、可并发测试）。
- 传输适配器：
  * ``hub_dir=<path>`` → **本地目录适配器**（hermetic：测试 / 离线 / 手工中转）；
  * ``hub_dir=None``  → **第一方传输适配器**：push 走 ``tools/share_experience.py``
    （scp fstdd-hub / inbox POST，强制脱敏），pull 走 scp 从 hub ``fstdd-inbox`` 取回。
  两者实现同一接口，故合并语义与传输通道无关。
- 合并策略：``updated_at``（缺则 ``exported_at`` / ``first_seen``）末写胜 + 冲突日志，
  **绝不静默覆盖**（避免重演 `_load_experience` 双块静默丢字段教训）。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

DEFAULT_HUB_SSH_ALIAS = "fstdd-hub"
DEFAULT_HUB_INBOX = "/home/ubuntu/fstdd-inbox"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _entry_body(text: str) -> str:
    """取最后一个 frontmatter 块之后的正文（兼容 inbox 双块结构）。"""
    parts = text.split("\n---\n")
    return parts[-1].strip() if len(parts) > 1 else ""


def load_entries(exp_dir: Path) -> dict:
    """读取经验目录 → ``{eid: {"data": fm, "path": Path, "body": str}}``。

    frontmatter 解析复用 ``experience._load_experience``（双块合并语义与库读取器一致，
    避免 sync 与 list/search 对同一文件给出不同结果）。
    """
    from .experience import _load_experience
    out = {}
    d = Path(exp_dir)
    if not d.exists():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("."):
            continue
        fm = _load_experience(p)
        if fm is None:
            continue
        eid = fm.get("experience_id") or p.stem
        out[eid] = {"data": fm, "path": p, "body": _entry_body(p.read_text(encoding="utf-8"))}
    return out


def _entry_ts(data: dict) -> str:
    for key in ("updated_at", "exported_at", "first_seen"):
        val = data.get(key)
        if val:
            return str(val)
    return ""


def _safe_eid(eid) -> str:
    """eid 落盘安全化：剥离路径分隔符与 `..`，防目录穿越（TC 评审 H-2）。"""
    s = re.sub(r"[^A-Za-z0-9._-]", "_", str(eid)).strip("._")
    if not s:
        raise ValueError(f"非法 experience_id: {eid!r}")
    return s


def _write_entry(exp_dir: Path, eid: str, data: dict, body: str) -> Path:
    exp_dir.mkdir(parents=True, exist_ok=True)
    fm_yaml = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    target = exp_dir / f"{_safe_eid(eid)}.md"
    tmp = target.with_suffix(".md.tmp")
    tmp.write_text(f"---\n{fm_yaml}---\n\n{body}\n", encoding="utf-8")
    tmp.replace(target)          # 原子落盘，避免并发半写
    return target


# 合并判等时忽略的易变字段（时间戳/脱敏标记等，不代表内容差异）
_VOLATILE_KEYS = {"last_seen", "updated_at", "exported_at", "sanitized", "sanitize_hits"}


def _same_content(a: dict, b: dict) -> bool:
    """内容是否等价：比较除易变字段外的**全部** frontmatter + 正文。"""
    da = {k: v for k, v in a["data"].items() if k not in _VOLATILE_KEYS}
    db = {k: v for k, v in b["data"].items() if k not in _VOLATILE_KEYS}
    return da == db and a["body"] == b["body"]


def _log_conflict(log_path: Path, eid: str, winner: dict, loser: dict, winner_src: str,
                  loser_src: str) -> dict:
    rec = {
        "logged_at": _now_iso(), "eid": eid,
        "winner": winner_src, "winner_updated_at": _entry_ts(winner["data"]),
        "loser": loser_src, "loser_updated_at": _entry_ts(loser["data"]),
        "kept_path": str(winner["path"]),
    }
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        header_needed = not log_path.exists()
        with log_path.open("a", encoding="utf-8", newline="") as fh:
            if header_needed:
                fh.write("logged_at\teid\twinner\twinner_updated_at\tloser\t"
                         "loser_updated_at\tkept_path\n")
            fh.write("\t".join([
                rec["logged_at"], rec["eid"], rec["winner"], rec["winner_updated_at"],
                rec["loser"], rec["loser_updated_at"], rec["kept_path"],
            ]) + "\n")
    return rec


def merge_entries(local_dir: Path, remote_dir: Path, conflict_log_path=None,
                  dry_run: bool = False) -> dict:
    """kg_sync 式增量合并：ADD / UPDATE（updated_at LWW）+ 冲突日志。"""
    from .experience import _index_lock  # 延迟导入避免循环依赖

    local_dir = Path(local_dir)
    stats = {"added": 0, "updated": 0, "kept": 0, "conflicts": [], "total_remote": 0}
    remote = load_entries(remote_dir)
    stats["total_remote"] = len(remote)
    if not remote:
        return stats

    local_dir.mkdir(parents=True, exist_ok=True)
    with _index_lock(local_dir):
        local = load_entries(local_dir)
        for eid, rent in remote.items():
            if eid not in local:
                stats["added"] += 1
                if not dry_run:
                    _write_entry(local_dir, eid, rent["data"], rent["body"])
                continue
            lent = local[eid]
            if _same_content(lent, rent):
                stats["kept"] += 1
                continue
            l_ts, r_ts = _entry_ts(lent["data"]), _entry_ts(rent["data"])
            if r_ts > l_ts:                       # 远端更新 → 覆盖本地
                rec = _log_conflict(conflict_log_path, eid, rent, lent, "remote", "local")
                stats["conflicts"].append(rec)
                stats["updated"] += 1
                if not dry_run:
                    _write_entry(local_dir, eid, rent["data"], rent["body"])
            else:                                  # 本地更新或同刻 → 保留本地
                rec = _log_conflict(conflict_log_path, eid, lent, rent, "local", "remote")
                stats["conflicts"].append(rec)
                stats["kept"] += 1
    return stats


def sync_pull(local_dir: Path, remote_dir: Path, conflict_log_path=None,
              dry_run: bool = False) -> dict:
    """拉取腿的纯合并入口（remote_dir 已是本地可见的远端快照）。"""
    return merge_entries(local_dir, remote_dir, conflict_log_path=conflict_log_path,
                         dry_run=dry_run)


# ── 传输适配器 ──────────────────────────────────────────────────────────


def push_bundle(out_dir: Path, *, hub_dir=None, secure: bool = False,
                key_paths=None, dry_run: bool = False) -> tuple:
    """把 out_dir 的经验推到中心节点。

    - ``hub_dir`` 给定 → 本地目录适配器（直接落盘）；
      否则 → 第一方 ``tools/share_experience.py``（其 ``--export --publish`` 自行
      staging + 强制脱敏 + 审计）。
    - ``secure=True`` → 每条**先脱敏、再混合加密**后落 ``<eid>.md.enc``（SC-015）。
    """
    out_dir = Path(out_dir)
    if dry_run:
        return True, "dry-run: 未推送"
    if hub_dir:
        hub = Path(hub_dir)
        hub.mkdir(parents=True, exist_ok=True)
        entries = load_entries(out_dir)
        n = 0
        for eid, ent in entries.items():
            # 出站不变量：明文档同样强制脱敏（与 share_experience 的 stage_sanitized 一致）
            text = _sanitize_text(ent["path"].read_text(encoding="utf-8"))
            if secure:
                from ._exp_crypto import hybrid_encrypt
                pub = (key_paths or default_key_paths())[0]
                (hub / f"{_safe_eid(eid)}.md.enc").write_bytes(
                    hybrid_encrypt(text.encode("utf-8"), pub))
            else:
                (hub / f"{_safe_eid(eid)}.md").write_text(text, encoding="utf-8")
            n += 1
        mode = "secure" if secure else "plain"
        return True, f"local-hub[{mode}]: 推送 {n} 条 → {hub}"
    # 第一方传输：复用既有脚本（scp fstdd-hub / inbox POST，强制脱敏 + 审计）
    script = Path.cwd() / "tools" / "share_experience.py"
    if not script.is_file():
        return False, f"未找到第一方传输脚本: {script}"
    cmd = [sys.executable, str(script), "--export", "--publish"]
    if secure:
        cmd.append("--secure")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode == 0, (proc.stdout or proc.stderr or "").strip()[-200:]


def default_key_paths(project_root=None):
    from ._exp_crypto import default_key_paths as _dkp
    return _dkp(project_root)


_SANITIZE_RULES = (
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "<EMAIL>"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>"),
    (r"\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}\b", "<TOKEN>"),
    (r"(?i)\b(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+", r"\1=<REDACTED>"),
)


def _sanitize_text(text: str) -> str:
    """出站不变量：任何同步出站前**必须先脱敏**（SC-015）。"""
    out = text
    for pat, repl in _SANITIZE_RULES:
        out = re.sub(pat, repl, out)
    return out


def fetch_bundle(dest_dir: Path, *, hub_dir=None) -> tuple:
    """从中心节点取回经验快照到 dest_dir（``.md`` 与 ``.md.enc`` 均取回）。"""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if hub_dir:
        src = Path(hub_dir)
        if not src.exists():
            return True, "local-hub: 远端为空"
        n = 0
        for pat in ("*.md", "*.md.enc"):
            for p in src.glob(pat):
                shutil.copy2(p, dest_dir / p.name)
                n += 1
        return True, f"local-hub: 取回 {n} 条"
    proc = subprocess.run(
        ["scp", "-r", f"{DEFAULT_HUB_SSH_ALIAS}:{DEFAULT_HUB_INBOX}/*", str(dest_dir)],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False, (proc.stderr or "").strip()[-200:]
    return True, "scp: 取回完成"


def decrypt_incoming(snapshot_dir: Path, key_paths=None) -> int:
    """把快照中的 ``<eid>.md.enc`` 解密为 ``<eid>.md``（安全档 pull 腿）。"""
    from ._exp_crypto import hybrid_decrypt
    priv = (key_paths or default_key_paths())[1]
    n = 0
    for enc in Path(snapshot_dir).glob("*.md.enc"):
        blob = enc.read_bytes()
        plain = hybrid_decrypt(blob, priv)
        (Path(snapshot_dir) / enc.name[:-4]).write_bytes(plain)
        n += 1
    return n


def cleanup_dir(p: Path) -> None:
    """尽力清理临时快照目录；删除被沙箱守卫拦截时放弃（不影响主流程）。"""
    try:
        for f in Path(p).iterdir():
            try:
                f.unlink()
            except OSError:
                pass
        Path(p).rmdir()
    except OSError:
        pass
