#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""待审核池 → 经验库的同步工具（**维护者专属**）。

链路
----
    自建端点 ~/fstdd-inbox/*.md
        │  ssh + scp（维护者凭据）
        ▼
    inbox/raw/      原始取回
    inbox/staging/  归一 + 剥离元数据头 + 脱敏 → 待发布
    inbox/rejected/ 被拒条目（**留痕，不删除**）
    inbox/REVIEW.md 审核表
        │  复用 share_experience.publish()
        ▼
    2749817087qq/Fstdd-experiences

设计要点
--------
1. **发布物整体剥离**服务端元数据头。头里含 `remote_addr`（**投稿者 IP**），
   原样发布到公开仓库等于公开第三方个人信息。整体剥离是**结构性**保证：
   头没了，里面无论有多少字段都不会外泄。
2. **两级去重**：先按 `experience_id` 归一（同 id 取 `received_at` 最新），
   再按正文内容哈希去重（内容相同的不同 id 只留一份）。两级都是确定性的 → 幂等。
3. **零新实现**：脱敏调 `share_experience.sanitize()`，推送调
   `share_experience.publish()` —— 本模块**不定义**任何 publish 实现。
4. 发布物只含经验文件：复用 `export_files()` 的排除规则，剔除 README/SUBMIT。

用法
----
    python tools/inbox_pull.py --pull                 # 从端点取回并归一
    python tools/inbox_pull.py --review               # 输出审核表
    python tools/inbox_pull.py --reject EXP-XXXX      # 移出待发布集合（可多次）
    python tools/inbox_pull.py --publish              # 发布到经验库

可用环境变量
------------
    FSTDD_INBOX_SSH_HOST   默认 ubuntu@43.134.236.80
    FSTDD_INBOX_SSH_KEY    默认 /d/id_ed25519
    FSTDD_INBOX_REMOTE_DIR 默认 /home/ubuntu/fstdd-inbox
    EXP_REPO               默认 2749817087qq/Fstdd-experiences
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "inbox"
RAW_DIR = INBOX_DIR / "raw"
STAGING_DIR = INBOX_DIR / "staging"
REJECTED_DIR = INBOX_DIR / "rejected"
REVIEW_PATH = INBOX_DIR / "REVIEW.md"

DEFAULT_SSH_HOST = os.environ.get("FSTDD_INBOX_SSH_HOST", "ubuntu@43.134.236.80")
DEFAULT_SSH_KEY = os.environ.get("FSTDD_INBOX_SSH_KEY", "/d/id_ed25519")
DEFAULT_REMOTE_DIR = os.environ.get("FSTDD_INBOX_REMOTE_DIR", "/home/ubuntu/fstdd-inbox")

# 服务端落盘的文件名：<experience_id>-<UTC时间戳>.md（同秒重复时追加 -N）
_TIMESTAMP_SUFFIX = re.compile(r"^(?P<eid>.+?)-\d{8}T\d{6}Z(?:-\d+)?$")

# 服务端写入的元数据头。**必须整体匹配**，不能逐字段删（将来加字段会漏）。
_HEADER = re.compile(r"\A\s*<!--\s*fstdd-inbox\s*\n(?P<meta>.*?)\n\s*-->\s*\n?", re.S)


# ---------------------------------------------------------------------------
# 复用 share_experience（tools/ 不是包，无 __init__.py）
# ---------------------------------------------------------------------------

def _load_share():
    path = Path(__file__).resolve().parent / "share_experience.py"
    spec = importlib.util.spec_from_file_location("_share_experience", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_share_experience"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 纯函数：解析 / 归一 / 去重
# ---------------------------------------------------------------------------

def parse_inbox_header(text: str) -> tuple[dict, str]:
    """拆出服务端元数据头与正文。**返回的正文已不含头**。

    容忍无头文件：缺头时返回空 meta 与原文（不报错）。
    """
    m = _HEADER.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group("meta").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def normalize_id(meta: dict, stem: str) -> str:
    """经验标识：优先取头里的 `experience_id`，否则从文件名剥掉时间戳后缀。"""
    eid = str(meta.get("experience_id") or "").strip()
    if eid:
        return eid
    m = _TIMESTAMP_SUFFIX.match(stem)
    return m.group("eid") if m else stem


def read_records(raw_dir: Path) -> list[dict]:
    """读取 raw 目录，返回解析后的记录（**正文已剥离元数据头**）。"""
    records = []
    for f in sorted(raw_dir.glob("*.md")):
        meta, body = parse_inbox_header(f.read_text(encoding="utf-8", errors="replace"))
        records.append({
            "id": normalize_id(meta, f.stem),
            "author": str(meta.get("author") or "").strip(),
            "received_at": str(meta.get("received_at") or "").strip(),
            "remote_addr": str(meta.get("remote_addr") or "").strip(),
            "body": body,
            "source": f.name,
        })
    return records


def dedupe(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """两级去重。返回 `(保留, 被丢弃)`，被丢弃的带 `reason`。

    一级：同 `experience_id` 只留 `received_at` 最新的一条。
    二级：正文哈希相同的不同 id 只留一条（按 id 排序取首个，保证确定性）。
    """
    by_id: dict[str, dict] = {}
    dropped: list[dict] = []
    for r in records:
        cur = by_id.get(r["id"])
        if cur is None:
            by_id[r["id"]] = r
            continue
        if (r["received_at"] or "") > (cur["received_at"] or ""):
            dropped.append({**cur, "reason": "重复（同 id，非最新）"})
            by_id[r["id"]] = r
        else:
            dropped.append({**r, "reason": "重复（同 id，非最新）"})

    kept: list[dict] = []
    seen: dict[str, str] = {}
    for r in sorted(by_id.values(), key=lambda x: x["id"]):
        h = hashlib.sha256(r["body"].encode("utf-8")).hexdigest()
        if h in seen:
            dropped.append({**r, "reason": "重复（正文相同，id 不同）"})
            continue
        seen[h] = r["id"]
        kept.append(r)
    return kept, dropped


def filter_rejected(kept: list[dict], rejected: Path) -> tuple[list[dict], list[dict]]:
    """剔除已被拒绝的 id —— 拒绝必须**跨拉取持久**。

    为什么需要：`--pull` 每次都从 `raw/` 重建 staging。若不剔除已拒条目，
    一次 `--pull` 就会把先前拒掉的东西又带回来，审核判断等于白做（实测发生过）。
    """
    if not rejected.exists():
        return kept, []
    rejected_ids = {p.stem.split(".")[0] for p in rejected.glob("*.md")}
    out: list[dict] = []
    dropped: list[dict] = []
    for r in kept:
        if r["id"] in rejected_ids:
            dropped.append({**r, "reason": "已拒绝（留痕于 rejected/）"})
        else:
            out.append(r)
    return out, dropped


def build_staging(kept: list[dict], staging: Path, sanitize_fn) -> list[dict]:
    """把保留记录写入 staging：**脱敏**后以 `<id>.md` 落盘。

    注意 `newline="\\n"`：Windows 上 `write_text` 默认会把 `\\n` 翻成 CRLF，
    与仓库的行尾政策冲突（本日已踩过）。
    """
    staging.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in kept:
        clean, hits = sanitize_fn(r["body"], True)
        (staging / f"{r['id']}.md").write_text(clean, encoding="utf-8", newline="\n")
        rows.append({**r, "hits": hits, "bytes": len(clean.encode("utf-8"))})
    return rows


def review_table(rows: list[dict], dropped: list[dict]) -> str:
    """构造审核表（Markdown）。"""
    out = ["# 待审核经验", "",
           "> 由 `tools/inbox_pull.py --review` 生成。",
           "> 发布前**整体剥离**服务端元数据头，其中含投稿者 IP，不会进入发布物。", "",
           "## 待发布（%d 条）" % len(rows), "",
           "| ID | 作者 | 接收时间 | 字节 | 脱敏命中 |",
           "|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %d | %s |" % (
            r["id"], r["author"] or "(匿名)", r["received_at"] or "-",
            r["bytes"], "、".join(r["hits"]) or "无"))
    out += ["", "## 已丢弃（%d 条）" % len(dropped), ""]
    if dropped:
        out += ["| ID | 原因 | 来源文件 |", "|---|---|---|"]
        for d in dropped:
            out.append("| %s | %s | %s |" % (d["id"], d["reason"], d["source"]))
    else:
        out.append("（无）")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# 拉取（维护者凭据）
# ---------------------------------------------------------------------------

def _ssh(host: str, key: str, remote_cmd: str, timeout: int = 60):
    return subprocess.run(
        ["ssh", "-i", key, "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=20", host, remote_cmd],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout)


def pull_from_endpoint(host: str, key: str, remote_dir: str,
                       dest: Path) -> tuple[int, str]:
    """从端点取回 `*.md`。返回 `(取回数, 失败原因)`；成功时原因为空串。

    先 ssh 计数再 scp：避免「远端无匹配文件时 scp 报错」被误判为故障。
    """
    r = _ssh(host, key, "ls -1 %s/*.md 2>/dev/null | wc -l" % remote_dir)
    if r.returncode != 0:
        return 0, "无法连接端点: %s" % ((r.stderr or "").strip()[:200] or "ssh 失败")
    try:
        n = int((r.stdout or "0").strip() or 0)
    except ValueError:
        n = 0
    if n == 0:
        return 0, ""

    dest.mkdir(parents=True, exist_ok=True)
    r2 = subprocess.run(
        ["scp", "-i", key, "-o", "StrictHostKeyChecking=no", "-q",
         "%s:%s/*.md" % (host, remote_dir), str(dest)],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180)
    if r2.returncode != 0:
        return 0, "取回失败: %s" % ((r2.stderr or "").strip()[:200] or "scp 失败")
    return len(list(dest.glob("*.md"))), ""


def reject(staging: Path, rejected: Path, ids: list[str]) -> tuple[int, list[str]]:
    """把指定 id 移入 rejected（**留痕，不删除**）。返回 `(移走数, 未找到的 id)`。"""
    rejected.mkdir(parents=True, exist_ok=True)
    moved, missing = 0, []
    for eid in ids:
        src = staging / f"{eid}.md"
        if not src.exists():
            missing.append(eid)
            continue
        dst = rejected / src.name
        if dst.exists():
            dst = rejected / ("%s.%s.md" % (src.stem, datetime.now().strftime("%Y%m%dT%H%M%S")))
        src.replace(dst)
        moved += 1
    return moved, missing


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_pull(args) -> int:
    n, reason = pull_from_endpoint(args.host, args.key, args.remote_dir, RAW_DIR)
    if reason:
        print("[FAIL] %s" % reason)
        return 1
    if n == 0:
        print("[OK] 端点无待审核经验")
        return 0

    share = _load_share()
    records = read_records(RAW_DIR)
    kept, dropped = dedupe(records)
    kept, rejected_out = filter_rejected(kept, REJECTED_DIR)
    dropped += rejected_out
    rows = build_staging(kept, STAGING_DIR, share.sanitize)
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.write_text(review_table(rows, dropped), encoding="utf-8", newline="\n")

    print("[OK] 取回 %d 个文件 → 归一去重后待发布 %d 条，丢弃 %d 条"
          % (n, len(rows), len(dropped)))
    print("     审核表: %s" % REVIEW_PATH.relative_to(REPO_ROOT))
    return 0


def cmd_review(args) -> int:
    share = _load_share()
    records = read_records(RAW_DIR)
    kept, dropped = dedupe(records)
    kept, rejected_out = filter_rejected(kept, REJECTED_DIR)
    dropped += rejected_out
    rows = build_staging(kept, STAGING_DIR, share.sanitize)
    text = review_table(rows, dropped)
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


def cmd_reject(args) -> int:
    moved, missing = reject(STAGING_DIR, REJECTED_DIR, args.reject)
    print("[OK] 已移出 %d 条（留痕于 %s）"
          % (moved, REJECTED_DIR.relative_to(REPO_ROOT)))
    if missing:
        print("     未找到: %s" % ", ".join(missing))
    return 0 if moved else 1


def cmd_publish(args) -> int:
    share = _load_share()
    files = share.export_files(STAGING_DIR)          # 排除 README/SUBMIT
    if not files:
        print("[FAIL] staging 中没有可发布的经验文件")
        return 1
    token = share.find_token()
    if not token:
        print("[FAIL] 未找到 GitHub 凭证（发布到经验库需要写权限）")
        return 1
    ok, reason = share.publish(STAGING_DIR, args.repo, token)
    if not ok:
        print("[FAIL] 发布失败: %s" % reason[:200])
        return 1
    print("[OK] 已发布 %d 条经验 → %s" % (len(files), args.repo))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="待审核池 → 经验库（维护者专属）")
    ap.add_argument("--pull", action="store_true", help="从端点取回并归一")
    ap.add_argument("--review", action="store_true", help="输出审核表")
    ap.add_argument("--reject", nargs="*", default=[], help="移出待发布集合（留痕）")
    ap.add_argument("--publish", action="store_true", help="发布到经验库")
    ap.add_argument("--repo", default=os.environ.get("EXP_REPO", "2749817087qq/Fstdd-experiences"))
    ap.add_argument("--host", default=DEFAULT_SSH_HOST)
    ap.add_argument("--key", default=DEFAULT_SSH_KEY)
    ap.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    args = ap.parse_args()

    if args.pull:
        return cmd_pull(args)
    if args.review:
        return cmd_review(args)
    if args.reject:
        return cmd_reject(args)
    if args.publish:
        return cmd_publish(args)

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
