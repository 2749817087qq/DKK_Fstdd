# -*- coding: utf-8 -*-
"""skill 元数据治理：扫描并（可选）修复 SKILL.md 的 frontmatter 四项。

四项：name / description / version / license

原则：
  - 默认只报告，不修改任何文件（dry-run）
  - --fix 前自动全量备份，备份数 == 待改数才继续
  - 只增删 frontmatter 字段，正文保持字节级不变
  - 未知值一律写 unknown，严禁推测许可协议或编造版本号

用法：
    python tools/check_skill_metadata.py                # 只报告
    python tools/check_skill_metadata.py --fix          # 备份后修复
    python tools/check_skill_metadata.py --revert       # 从最新备份恢复
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path

REQUIRED = ["name", "description", "version", "license"]
UNKNOWN = "unknown"


def backup_root() -> Path:
    """备份根路径。

    项目约定：开发形成的产物一律存放在工作区文件夹内。
    本脚本位于 <工作区>/stdd-repo/tools/，故默认取 <工作区>/backups。
    可用 FSTDD_BACKUP_DIR 覆盖；定位失败时回落到用户目录。
    """
    env = os.environ.get("FSTDD_BACKUP_DIR")
    if env:
        return Path(env)
    try:
        cand = Path(__file__).resolve().parents[2] / "backups"
        if cand.parent.exists():
            return cand
    except IndexError:
        pass
    return Path.home() / ".workbuddy-ai" / "backups"

DEFAULT_DIRS = [
    Path.home() / ".workbuddy-ai" / "skills",
    Path.home() / ".workbuddy" / "skills",
]


def split_fm(text: str) -> tuple[str, str, bool]:
    """返回 (frontmatter, body, has_fm)。正文保持原样，不做规范化。"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            return text[3:end], text[end:], True
    return "", text, False


def fm_has(fm: str, key: str) -> bool:
    return re.search(rf"^{key}:", "\n".join(fm.splitlines()), re.M) is not None


def collect(dirs: list[Path]) -> list[Path]:
    out = []
    for b in dirs:
        if not b.exists():
            continue
        for d in sorted(b.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                out.append(d / "SKILL.md")
    return out


def scan(files: list[Path]) -> tuple[dict, list]:
    have = {k: 0 for k in REQUIRED}
    todo = []  # (path, missing_keys)
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        fm, _, _ = split_fm(text)
        missing = [k for k in REQUIRED if not fm_has(fm, k)]
        for k in REQUIRED:
            if k not in missing:
                have[k] += 1
        if missing:
            todo.append((f, missing))
    return have, todo


def insert_fields(f: Path, missing: list[str]) -> bool:
    """在 frontmatter 末尾插入缺失字段；正文字节保持原样。"""
    text = f.read_text(encoding="utf-8", errors="replace")
    fm, body, has_fm = split_fm(text)
    if not has_fm:  # 没有 frontmatter 就建一个
        new = "---\n" + "".join(f"{k}: {UNKNOWN}\n" for k in missing) + f"---\n{body}"
        f.write_text(new, encoding="utf-8", newline="")
        return True
    lines = fm.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    for k in missing:
        lines.append(f"{k}: {UNKNOWN}")
    new_fm = "\n".join(lines) + "\n"
    f.write_text(f"---{new_fm}{body}", encoding="utf-8", newline="")
    return True


def verify_fm_parsable(f: Path) -> bool:
    """写回后校验 frontmatter 仍可被 YAML 解析。"""
    text = f.read_text(encoding="utf-8", errors="replace")
    fm, _, has_fm = split_fm(text)
    if not has_fm:
        return False
    try:
        import yaml
        yaml.safe_load(fm)
        return True
    except ImportError:
        return True  # 无 yaml 库时跳过该校验
    except Exception:
        return False


def backup(todo: list, ts: str) -> Path | None:
    dest = backup_root() / f"skill-metadata-{ts}"
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f, _ in todo:
        rel = f.relative_to(Path.home())
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        n += 1
    return dest if n == len(todo) else None


def latest_backup() -> Path | None:
    root = backup_root()
    if not root.exists():
        return None
    cands = sorted(root.glob("skill-metadata-*"))
    return cands[-1] if cands else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="append", help="skill 目录（可多次）")
    ap.add_argument("--fix", action="store_true", help="备份后补齐缺失字段")
    ap.add_argument("--backup-only", action="store_true",
                    help="只建立备份快照，不修改任何文件"
                         "（用于 install 重写 skill 后刷新回滚基准）")
    ap.add_argument("--revert", action="store_true", help="从最新备份恢复")
    args = ap.parse_args()

    if args.revert:
        b = latest_backup()
        if not b:
            print("[FAIL] 未找到任何备份")
            return 1
        n = 0
        for src in b.rglob("SKILL.md"):
            rel = src.relative_to(b)
            dst = Path.home() / rel
            if dst.exists():
                shutil.copy2(src, dst)
                n += 1
        print(f"[OK] 已从 {b.name} 恢复 {n} 个文件")
        return 0

    dirs = [Path(d) for d in args.dir] if args.dir else DEFAULT_DIRS
    files = collect(dirs)
    if not files:
        print("[FAIL] 未找到任何 SKILL.md")
        return 1

    have, todo = scan(files)
    total = len(files)
    print("=" * 60)
    print("skill 元数据检查")
    print("=" * 60)
    for k in REQUIRED:
        print(f"  有 {k:<12}: {have[k]:>3}/{total}   缺 {total - have[k]}")
    print()
    print(f"缺失统计: " + ", ".join(f"{k} 缺 {total - have[k]}" for k in REQUIRED))
    print(f"四项齐全: {total - len(todo)}/{total}")

    # --backup-only：安装脚本重写 skill 后，用它刷新回滚基准
    if args.backup_only:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        # backup() 期望 (path, missing_keys) 元组列表；此处全部文件都要备份
        dest = backup([(f, []) for f in files], ts)
        if dest is None:
            print("[FAIL] 备份失败（文件数与扫描数不一致）")
            return 1
        print(f"\n[备份] 已保存当前状态快照（{len(files)} 个文件）→ {dest}")
        print("[说明] 未修改任何文件，仅作为 --revert 的回滚基准")
        return 0

    if not todo:
        print("\n[PASS] 全部 skill 元数据齐全")
        return 0

    print(f"\n待修复 {len(todo)} 个 skill：")
    for f, miss in todo[:15]:
        print(f"  - {f.parent.name}: 缺 {', '.join(miss)}")
    if len(todo) > 15:
        print(f"  ... 其余 {len(todo) - 15} 个略")

    if not args.fix:
        print("\n（dry-run：未修改任何文件。加 --fix 执行修复）")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup(todo, ts)
    if dest is None:
        print("[FAIL] 备份文件数与待改数不一致，已中止（未修改任何文件）")
        return 1
    print(f"\n[备份] 已备份 {len(todo)} 个文件 → {dest}")

    changed, failed = 0, []
    for f, miss in todo:
        before_body = split_fm(f.read_text(encoding="utf-8", errors="replace"))[1]
        try:
            insert_fields(f, miss)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{f.parent.name}: 写入异常 {e}")
            continue
        after_text = f.read_text(encoding="utf-8", errors="replace")
        if split_fm(after_text)[1] != before_body:
            failed.append(f"{f.parent.name}: 正文被改动（已回滚）")
            shutil.copy2(dest / f.relative_to(Path.home()), f)
            continue
        if not verify_fm_parsable(f):
            failed.append(f"{f.parent.name}: frontmatter 解析失败（已回滚）")
            shutil.copy2(dest / f.relative_to(Path.home()), f)
            continue
        changed += 1

    print(f"[修复] 成功 {changed}/{len(todo)}" + (f"，失败 {len(failed)}" if failed else ""))
    for x in failed:
        print(f"  - {x}")
    print(f"[回滚] 如需撤销：python {Path(__file__).name} --revert")

    _, remain = scan(files)
    if remain:
        print(f"\n[FAIL] 仍有 {len(remain)} 个 skill 元数据缺失")
        return 1
    print(f"\n[PASS] 全部 {total} 个 skill 四项元数据齐全")
    print(f"[说明] 缺失值写入 {UNKNOWN}——显式 unknown 优于字段缺失，"
          f"不代表该 skill 采用任何特定协议")
    return 0


if __name__ == "__main__":
    sys.exit(main())
