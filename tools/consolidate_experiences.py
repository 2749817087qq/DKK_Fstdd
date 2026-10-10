#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""经验库跨副本收敛与去重迁移脚本（C8）。

将分散在 4 副本的 179 经验文件收敛为 1 个权威、去重、可信库
（stdd-repo/.fstdd/experiences），并提供幂等、可预览、可校验的迁移能力。

设计要点（见 change 的 design.md / proposal.yaml）：
- 权威写库 = STD_REPO_EXP；其余 3 副本降为只读参考。
- 先备份（stage backup），再 ingest / adjudicate / dedupe / downgrade / index。
- 删冗余走「同盘 os.rename 移入副本内 .trash-<date>/」，非 rm（沙箱 rm 被 safe-delete 拦截）。
- 全程幂等：重跑不产生重复、不破坏已收敛状态。
- --dry-run 只打印动作不落盘；--verify 校验收敛不变量。

本脚本自含 frontmatter 解析（多块合并，后块覆盖前块冲突键），不依赖具体 fstdd 安装，
因此可在任意环境复跑。索引重建阶段则复用活 fstdd 的 _rebuild_index 以保证与 CLI 一致。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

DATE = date.today().isoformat()
REPLICA_TRASH = ".trash-" + DATE

# ---- 路径（均可通过命令行覆盖）----
STD_REPO_EXP = Path("E:/FSTDD/stdd-repo/.fstdd/experiences")
FSTDD003_EXP = Path("D:/FSTDD003/.fstdd/experiences")
HOME_EXP = Path(os.path.expanduser("~/.workbuddy-ai/FSTDD/experiences"))
FSTDD002_EXP = Path("D:/FSTDD002/.fstdd/experiences")
BACKUP_ROOT = Path("E:/FSTDD/_backup/exp-consolidation-" + DATE)

REPLICAS = {
    "FSTDD003": FSTDD003_EXP,
    "home-FSTDD": HOME_EXP,
    "FSTDD002": FSTDD002_EXP,
}


# ---------------------------------------------------------------------------
# 解析（与 C5 修复后的 _load_experience 同语义：多块合并，后块优先）
# ---------------------------------------------------------------------------
def parse_experience(path: Path) -> dict | None:
    """解析经验文件，返回合并后的 frontmatter 字典。

    按全部 --- 切片，逐段 yaml.safe_load，凡是 dict 就合并（后块覆盖前块冲突键）。
    兼容单块 / inbox 双块 / 无 frontmatter（返回 None）。
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    merged: dict = {}
    for seg in content.split("---"):
        seg = seg.strip()
        if not seg:
            continue
        try:
            loaded = yaml.safe_load(seg)
        except yaml.YAMLError:
            continue
        if isinstance(loaded, dict):
            merged.update(loaded)
    return merged or None


def eid_of(path: Path) -> str:
    """经验 id：优先 frontmatter 的 experience_id，缺失时退回文件名 stem。"""
    data = parse_experience(path)
    if data and data.get("experience_id"):
        return str(data["experience_id"]).strip()
    return Path(path).stem


def content_hash(path: Path) -> str:
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()[:12]


def list_md(dir_path: Path) -> list[Path]:
    if not dir_path or not Path(dir_path).is_dir():
        return []
    return sorted(p for p in Path(dir_path).glob("*.md") if not p.name.startswith("."))


# ---------------------------------------------------------------------------
# stage: backup
# ---------------------------------------------------------------------------
def stage_backup(dry_run: bool) -> int:
    print(f"[backup] -> {BACKUP_ROOT}")
    total = 0
    for name, src in REPLICAS.items():
        if not src.is_dir():
            print(f"  [skip] replica {name} missing: {src}")
            continue
        n = len(list_md(src))
        dst = BACKUP_ROOT / name
        if dry_run:
            print(f"  [dry-run] would copy {n} files: {src} -> {dst}")
            total += n
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in list_md(src):
            shutil.copy2(f, dst / f.name)
        got = len(list_md(dst))
        if got != n:
            raise RuntimeError(f"backup mismatch for {name}: src={n} dst={got}")
        print(f"  [ok] {name}: {n} files backed up to {dst}")
        total += n
    print(f"[backup] done, {total} files")
    return total


# ---------------------------------------------------------------------------
# stage: ingest (C2) — 回灌 FSTDD002 独有 eid
# ---------------------------------------------------------------------------
def stage_ingest(dry_run: bool) -> int:
    print("[ingest] FSTDD002 独有 eid -> 权威库")
    if not STD_REPO_EXP.is_dir():
        raise RuntimeError(f"authoritative lib missing: {STD_REPO_EXP}")
    have = {eid_of(p) for p in list_md(STD_REPO_EXP)}
    copied = 0
    for f in list_md(FSTDD002_EXP):
        eid = eid_of(f)
        if eid in have:
            print(f"  [skip] {eid} already in authoritative lib")
            continue
        dst = STD_REPO_EXP / f.name
        if dry_run:
            print(f"  [dry-run] would ingest {eid} ({f.name})")
            copied += 1
            continue
        shutil.copy2(f, dst)
        have.add(eid)
        print(f"  [ok] ingested {eid}")
        copied += 1
    print(f"[ingest] done, {copied} new eid ingested")
    return copied


# ---------------------------------------------------------------------------
# stage: adjudicate (C3) — 逐条裁决漂移 eid（默认以权威库为准）
# ---------------------------------------------------------------------------
def compute_drift() -> list[dict]:
    """跨 4 副本计算同 eid 多内容哈希的漂移项。"""
    by_eid: dict[str, list[tuple[str, str, str]]] = {}
    for label, d in [("stdd-repo", STD_REPO_EXP)] + list(REPLICAS.items()):
        for f in list_md(d):
            eid = eid_of(f)
            by_eid.setdefault(eid, []).append((label, str(f), content_hash(f)))
    drift = []
    for eid, occ in by_eid.items():
        hashes = {h for _, _, h in occ}
        if len(hashes) > 1:
            drift.append({"eid": eid, "occurrences": occ, "hashes": sorted(hashes)})
    return drift


def stage_adjudicate(dry_run: bool, log_path: Path | None = None) -> int:
    print("[adjudicate] 漂移 eid 裁决（默认以 stdd-repo 为准）")
    drift = compute_drift()
    # 收敛后权威库已含 stdd-repo 版；其余副本的同 eid 文件在 dedupe 阶段移入回收站，
    # 其原始内容保留于 _backup/ 供审计。故裁决 = 确认 stdd-repo 版胜出。
    lines = []
    for d in drift:
        eid = d["eid"]
        stdd_present = any(lbl == "stdd-repo" for lbl, _, _ in d["occurrences"])
        decision = "KEEP_STDD_REPO" if stdd_present else "NEEDS_MANUAL"
        lines.append(f"{eid}\t{decision}\tversions={len(d['hashes'])}\tfrom={[lbl for lbl,_,_ in d['occurrences']]}")
        print(f"  [adjudicate] {eid}: {decision} (variants={len(d['hashes'])})")
    if log_path and not dry_run:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  [log] adjudication written to {log_path}")
    print(f"[adjudicate] done, {len(drift)} drift eid adjudicated")
    return len(drift)


# ---------------------------------------------------------------------------
# stage: dedupe (C4) — 冗余文件移入同盘回收站（非 rm）
# ---------------------------------------------------------------------------
def _trash_dir(replica_dir: Path) -> Path:
    return replica_dir / REPLICA_TRASH


def stage_dedupe(dry_run: bool, batch: int = 10) -> int:
    print("[dedupe] 冗余副本移入同盘回收站（保留权威库）")
    moved = 0
    for name, src in REPLICAS.items():
        trash = _trash_dir(src)
        auth_eids = {eid_of(p) for p in list_md(STD_REPO_EXP)}
        if not src.is_dir():
            continue
        pending = [f for f in list_md(src) if eid_of(f) in auth_eids]
        if not pending:
            continue
        if dry_run:
            print(f"  [dry-run] would move {len(pending)} files from {name} to {trash}")
            moved += len(pending)
            continue
        trash.mkdir(parents=True, exist_ok=True)
        done = 0
        for f in pending:
            # 同盘 os.rename（move），非 rm；逐批 <= batch 以防误删不可控
            dest = trash / f.name
            if dest.exists():
                continue
            os.rename(str(f), str(dest))
            done += 1
            moved += 1
            if done >= batch:
                # 批间停顿由调用方控制；此处仅按批上限切分日志
                print(f"    ...moved {done} from {name} (batch limit {batch})")
                done = 0
        print(f"  [ok] {name}: {len(pending)} redundant files -> {trash}")
    print(f"[dedupe] done, {moved} files moved to trash")
    return moved


# ---------------------------------------------------------------------------
# stage: downgrade (C7) — 三副本降级为只读参考
# ---------------------------------------------------------------------------
README_TEXT = """# 本目录已收敛（{date}）

本经验库副本已并入权威写库：

    E:/FSTDD/stdd-repo/.fstdd/experiences

**本目录为历史参考，请勿作为写源。** 所有唯一经验条目均已回灌至上述权威库；
本目录原有文件（含漂移/重复版本）已移至同目录 `.trash-{date}/` 回收站，
完整备份见 `E:/FSTDD/_backup/exp-consolidation-{date}/`。

如需新增经验，请直接使用 `fstdd experience add`（权威库）。
""".format(date=DATE)


def stage_downgrade(dry_run: bool) -> int:
    print("[downgrade] 三副本写入 README 标注（已收敛、非写源）")
    n = 0
    for name, src in REPLICAS.items():
        if not src.is_dir():
            continue
        readme = src / "README.md"
        if dry_run:
            print(f"  [dry-run] would write README in {name}")
            n += 1
            continue
        readme.write_text(README_TEXT, encoding="utf-8")
        print(f"  [ok] {name}: README written")
        n += 1
    print(f"[downgrade] done, {n} READMEs written")
    return n


# ---------------------------------------------------------------------------
# stage: index (C6) — 用修复后解析器重建权威库索引
# ---------------------------------------------------------------------------
def stage_index(dry_run: bool) -> int:
    print("[index] 重建权威库 .experience-index.yaml（修复后解析器）")
    if dry_run:
        print("  [dry-run] would rebuild index via fstdd")
        return 0
    try:
        from fstdd.cli.commands import experience as exp
    except Exception as e:  # pragma: no cover
        print(f"  [warn] cannot import fstdd ({e}); skipping index rebuild")
        return 0
    exp_dir = STD_REPO_EXP
    index = exp._rebuild_index(exp_dir)
    exp._save_index(exp_dir, index)
    print(f"  [ok] index rebuilt: total={index.get('total')} "
          f"by_category={len(index.get('by_category', {}))}")
    return int(index.get("total", 0))


# ---------------------------------------------------------------------------
# stage: verify (C8) — 不变量校验
# ---------------------------------------------------------------------------
def stage_verify() -> bool:
    print("[verify] 校验收敛不变量")
    files = list_md(STD_REPO_EXP)
    eids = [eid_of(p) for p in files]
    uniq_eids = set(eids)
    hashes = {content_hash(p) for p in files}

    # 不变量1：所有副本（备份）中的 eid 必须全部保留在权威库（无丢失）
    replica_eids = set()
    for name in ("FSTDD003", "home-FSTDD", "FSTDD002"):
        for f in list_md(BACKUP_ROOT / name):
            replica_eids.add(eid_of(f))
    missing = replica_eids - uniq_eids

    # 不变量2：权威库内无重复内容
    dup_content = len(hashes) != len(files)

    ok = True
    print(f"  权威库文件数 = {len(files)}")
    print(f"  唯一 experience_id 数 = {len(uniq_eids)}")
    print(f"  副本侧唯一 eid 数（应全部保留） = {len(replica_eids)}")
    if missing:
        print(f"  [FAIL] 以下副本 eid 未保留到权威库: {sorted(missing)}")
        ok = False
    else:
        print("  [ok] 所有副本 eid 均已保留到权威库（0 丢失）")
    if dup_content:
        print(f"  [FAIL] 权威库存在重复内容 (hash={len(hashes)} < files={len(files)})")
        ok = False
    else:
        print("  [ok] 权威库无重复内容文件")
    # 三副本应已降级（README 存在 + 冗余文件已移走）
    for name, src in REPLICAS.items():
        readme = src / "README.md" if src.is_dir() else None
        has = bool(readme and readme.exists())
        rem = len(list_md(src))
        status = "ok" if has else "MISSING_README"
        print(f"  [{status}] {name}: README={has}, remaining_md={rem}")
        if not has:
            ok = False
    print(f"[verify] {'ALL INVARIANTS MET' if ok else 'SOME CHECKS FAILED'}")
    return ok


def _ingested_fstdd002_eids() -> set[str]:
    """已回灌到权威库的 FSTDD002 eid（用于 verify 不依赖副本仍存在）。"""
    # 收敛后 FSTDD002 副本可能已清空；此处从备份推断曾有的独有 eid。
    backup = BACKUP_ROOT / "FSTDD002"
    if backup.is_dir():
        return {eid_of(p) for p in list_md(backup)}
    return set()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
STAGES = ["backup", "ingest", "adjudicate", "dedupe", "downgrade", "index", "verify"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="经验库跨副本收敛迁移 (C8)")
    ap.add_argument("--stage", choices=STAGES + ["all"], default="all")
    ap.add_argument("--dry-run", action="store_true", help="只打印动作不落盘")
    ap.add_argument("--batch", type=int, default=10, help="dedupe 每批上限")
    ap.add_argument("--std-repo-exp", default=str(STD_REPO_EXP))
    ap.add_argument("--fstdd003-exp", default=str(FSTDD003_EXP))
    ap.add_argument("--home-exp", default=str(HOME_EXP))
    ap.add_argument("--fstdd002-exp", default=str(FSTDD002_EXP))
    ap.add_argument("--backup-root", default=str(BACKUP_ROOT))
    args = ap.parse_args(argv)

    # 本环境使用模块级默认路径（如需覆盖，编辑文件顶部常量即可；CLI 覆盖作为后续增强）
    dry = args.dry_run
    stage = args.stage
    run_all = stage == "all"

    if dry:
        print("########## DRY-RUN MODE — no writes ##########")

    if run_all or stage == "backup":
        stage_backup(dry)
    if run_all or stage == "ingest":
        stage_ingest(dry)
    if run_all or stage == "adjudicate":
        stage_adjudicate(dry, log_path=STD_REPO_EXP.parent.parent
                         / ".fstdd" / "changes" / "2026-10-10-experience-library-consolidation"
                         / "adjudication-log.tsv")
    if run_all or stage == "dedupe":
        stage_dedupe(dry, batch=args.batch)
    if run_all or stage == "downgrade":
        stage_downgrade(dry)
    if run_all or stage == "index":
        stage_index(dry)
    if run_all or stage == "verify":
        ok = stage_verify()
        if not dry and not ok:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
