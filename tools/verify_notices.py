"""tools/verify_notices.py — 协作通知真伪校验闸门。

独立子进程调用点：
  python tools/verify_notices.py <notices_dir> [--json] [--strict] [--quarantine]

职责：
  1. 读取 00-SIGNATURES.md 清单（格式：| 文件名 | md5前12位 | 落盘时间 | 发出者 |）
  2. 对目录内通知计算 md5 前 12 位并比对
  3. unverified + 凭证形状命中 → **默认只报告**（计入 would_quarantine，不动文件）；
     显式传入 --quarantine 才移入 tools/_quarantine/（保留原文 + 四键 JSON 记录）
  4. 不回显任何凭证字面值；仅依赖 stdlib

退出码契约：
  0  —— 无阻断（非 strict 模式下 unverified 只告警）
  2  —— 存在凭证形状命中（无论是否实际隔离）
  3  —— --strict 且存在 unverified（3 优先于 2）

无网络调用、**默认**不触碰任何文件（含凭证现场文件）；仅 `--quarantine` 时会写
`tools/_quarantine/`。

⚠️ **默认不移动任何文件** —— 只有显式传入 `--quarantine` 才会写 `tools/_quarantine/`。
   历史教训（EXP-2026-0015 三次命中）：此前「隔离」是**默认**处置，对仓库根跑一次就会把
   带未提交改动的已跟踪文件（如 `README.md` / `CHANGELOG.md`）`shutil.move` 走，
   有丢失未提交工作的风险，且与本模块「不写业务文件」的自述相矛盾。
   现改为「默认报告 + 显式 opt-in 移动」。
   （第三次命中发生于 2026-10-07 本 change 的 BUILD 期间 —— 为取 RED 证据而临时回退本修复，
   随后对仓库根跑了一次旧版，实测移走 3 个已跟踪文件；已全部按字节比对复原。）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUARANTINE_DIR = Path(__file__).resolve().parent / "_quarantine"

MD5_PREFIX_LEN = 12
MANIFEST_NAME = "00-SIGNATURES.md"

NOTICE_GLOB = ("*.md",)

# ---------------------------------------------------------------------------
# 凭证形状嗅探规则（误判方向：宁可隔离）
# ---------------------------------------------------------------------------
# 每条规则：(rule_name, compiled_regex)
# 正则必须**不**捕获 token 字面值到 group(1)，只报告 match_count。
_CREDENTIAL_RULES: list[tuple[str, re.Pattern]] = [
    ("x_fstdd_token", re.compile(r"X-FSTDD-Token:\s*(?:[A-Za-z0-9\-_]{16,})")),
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9\-_]{16,}", re.IGNORECASE)),
    ("generic_secret_block", re.compile(
        r"(?:token|secret|credential|凭证)\s*(?:[:：=]|\n)",
        re.IGNORECASE,
    )),
    ("long_alnum_block", re.compile(
        r"\b[A-Za-z0-9]{16,}\b"
    )),
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _md5_prefix(data: bytes | str, length: int = MD5_PREFIX_LEN) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()[:length]


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _iter_notice_files(directory: Path) -> list[Path]:
    out: list[Path] = []
    for pat in NOTICE_GLOB:
        out.extend(sorted(directory.glob(pat)))
    # 过滤：排除清单自身和隔离记录
    return [p for p in out if p.name != MANIFEST_NAME and ".json" not in p.suffix]


# ---------------------------------------------------------------------------
# 清单解析
# ---------------------------------------------------------------------------

def parse_manifest(manifest_path: Path) -> tuple[dict[str, dict], list[str], bool]:
    """解析 00-SIGNATURES.md。

    Returns:
        (entries_by_name, warnings, file_exists_flag)
        entries_by_name: filename -> {"md5": str, "timestamp": str, "emitted_by": str}
        warnings:        list[str] — 畸形行或重复登记告警
        file_exists_flag: True 表示文件存在（即使为空表）
    """
    warnings: list[str] = []
    if not manifest_path.exists():
        return {}, warnings, False

    text = manifest_path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    entries: dict[str, dict] = {}
    seen_names: dict[str, int] = {}  # filename -> first index

    for raw in lines:
        # 跳过 markdown 表头 / 分隔线 / 纯注释
        stripped = raw.strip("|").strip()
        if not stripped or stripped.startswith("---") or stripped.startswith("#"):
            continue

        parts = [p.strip() for p in raw.strip("|").split("|")]
        if len(parts) < 4:
            warnings.append(f"manifest: skipped malformed row ({parts[:2]}...)")
            continue

        fname, md5p, ts, by = parts[0], parts[1], parts[2], parts[3]

        # md5 前 12 位校验
        if len(md5p) != MD5_PREFIX_LEN or not re.fullmatch(r"[0-9a-fA-F]{12}", md5p):
            warnings.append(f"manifest: skipped row with invalid md5 prefix for {fname}")
            continue
        md5p = md5p.lower()

        # 重复登记：首条有效，后续记录告警
        if fname in entries:
            warnings.append(f"manifest: duplicate entry for {fname}, using first occurrence")
            continue

        entries[fname] = {
            "md5": md5p,
            "timestamp": ts,
            "emitted_by": by,
        }
        seen_names[fname] = len(entries)

    return entries, warnings, True


# ---------------------------------------------------------------------------
# 分类 / 嗅探
# ---------------------------------------------------------------------------

def classify_notice(file_path: Path) -> dict:
    """对单个通知文件做清单比对。

    前置：调用方应已 parse_manifest() 并缓存；此处直接读取同目录清单。
    为了测试友好，也可接受 file_path 是纯字符串。
    """
    file_path = Path(file_path)
    manifest_path = file_path.parent / MANIFEST_NAME
    entries, warnings, manifest_exists = parse_manifest(manifest_path)

    actual = _md5_prefix(_read_bytes(file_path))
    fname = file_path.name

    if not manifest_exists:
        return {
            "status": "unverified",
            "reason": "manifest_missing",
            "filename": fname,
            "md5_prefix": actual,
        }

    if fname not in entries:
        return {
            "status": "unverified",
            "reason": "not_in_manifest",
            "filename": fname,
            "md5_prefix": actual,
        }

    expected = entries[fname]["md5"]
    if actual != expected:
        return {
            "status": "unverified",
            "reason": "md5_mismatch",
            "filename": fname,
            "md5_prefix": actual,
            "expected_md5_prefix": expected,
            "actual_md5_prefix": actual,
        }

    return {
        "status": "verified",
        "filename": fname,
        "md5_prefix": actual,
        "emitted_by": entries[fname]["emitted_by"],
    }


def sniff_credential(content: str | bytes) -> list[dict]:
    """对文本做凭证形状嗅探，返回命中规则列表（不回显字面值）。"""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    hits: list[dict] = []
    for rule_name, pat in _CREDENTIAL_RULES:
        matches = pat.findall(content)
        count = len(matches) if matches else 0
        # 对 bearer_token 和 long_alnum_block，findall 可能返回空元组
        if count == 0:
            continue
        hits.append({"rule": rule_name, "match_count": count})
    return hits


# ---------------------------------------------------------------------------
# 隔离
# ---------------------------------------------------------------------------

def _ensure_quarantine() -> Path:
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    return QUARANTINE_DIR


def _quarantine_file(file_path: Path, rule: str) -> dict:
    """移动文件到隔离区并写四键记录。返回隔离记录 dict。"""
    q_dir = _ensure_quarantine()
    dest = q_dir / file_path.name
    if dest.exists():
        # 同名覆盖：加时间戳后缀避免丢证据
        dest = q_dir / f"{file_path.stem}-{datetime.now().strftime('%H%M%S')}{file_path.suffix}"
    shutil.move(str(file_path), str(dest))

    record = {
        "filename": file_path.name,
        "md5_prefix": _md5_prefix(file_path.name),  # 文件名 md5 前 12 位 → 仅定位用
        "rule": rule,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    rec_path = q_dir / f"{dest.name}.json"
    rec_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def verify_notices(directory: Path | str, strict: bool = False, quarantine: bool = False) -> dict:
    """批量校验目录内通知。

    返回 dict 含**五**键：`results` / `quarantined` / `warnings` / `exit_code` / `would_quarantine`。

    :param strict: 存在 unverified 时以 exit 3 硬阻断（3 优先于 2）
    :param quarantine: **默认 False** —— 命中凭证形状的文件只计入 `would_quarantine`、
        不移动；传 True 才执行 `shutil.move` 到 `tools/_quarantine/`。
    """
    directory = Path(directory)
    warnings: list[str] = []
    results: list[dict] = []
    quarantined: list[dict] = []
    would_quarantine: list[dict] = []

    # 目录不存在 / 不可读 → 优雅降级
    if not directory.exists() or not directory.is_dir():
        warnings.append(f"verify_notices: directory not found or not readable: {directory}")
        return {"results": [], "quarantined": [], "warnings": warnings,
                "exit_code": 0, "would_quarantine": []}

    manifest_path = directory / MANIFEST_NAME
    entries, manifest_warnings, manifest_exists = parse_manifest(manifest_path)
    warnings.extend(manifest_warnings)

    if not manifest_exists:
        warnings.append(f"verify_notices: {MANIFEST_NAME} missing — all files unverified (manifest_missing)")

    files = _iter_notice_files(directory)

    for fpath in files:
        # 跳过隔离区内的文件（极端情况：隔离区与待检目录重叠）
        if QUARANTINE_DIR in fpath.parents:
            continue

        classify = classify_notice(fpath)
        results.append(classify)

        # 嗅探 + 隔离：仅对 unverified 生效
        if classify["status"] == "unverified":
            content = _read_bytes(fpath)
            hits = sniff_credential(content)
            if hits:
                # 取首个规则名记录
                rule_used = hits[0]["rule"]
                if quarantine:
                    rec = _quarantine_file(fpath, rule_used)
                    quarantined.append(rec)
                else:
                    # 默认只报告：不移动、不写隔离记录，保持可观测（KG-095）
                    would_quarantine.append({
                        "filename": fpath.name,
                        "md5_prefix": _md5_prefix(fpath.name),
                        "rule": rule_used,
                        "would_move_to": str(QUARANTINE_DIR / fpath.name),
                    })
                    warnings.append(
                        f"verify_notices: 凭证形状命中 {fpath.name}（规则 {rule_used}）"
                        "—— 默认不移动文件；如需隔离请加 --quarantine"
                    )

    # 退出码
    has_unverified = any(r["status"] == "unverified" for r in results)
    exit_code = 0
    # 只要**命中**凭证形状就非 0（无论是否真的移动）—— 保持告警强度
    if quarantined or would_quarantine:
        exit_code = 2
    if strict and has_unverified:
        exit_code = 3

    return {
        "results": results,
        "quarantined": quarantined,
        "warnings": warnings,
        "exit_code": exit_code,
        "would_quarantine": would_quarantine,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify FSTDD collaboration notices")
    parser.add_argument("directory", type=Path, help="Notices directory (contains 收-*.md)")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output JSON to stdout")
    parser.add_argument("--strict", action="store_true", help="Treat any unverified as hard block (exit 3)")
    parser.add_argument(
        "--quarantine",
        action="store_true",
        help="Actually move credential-shaped hits into tools/_quarantine/ "
             "(default: report only, move nothing)",
    )

    args = parser.parse_args(argv)

    result = verify_notices(args.directory, strict=args.strict, quarantine=args.quarantine)

    if args.json_out:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    else:
        # 人类可读简版
        for item in result["results"]:
            status = item["status"]
            extra = item.get("reason", "")
            print(f"[{status:9s}] {item['filename']}  md5[:12]={item['md5_prefix']}  {extra}")
        if result["quarantined"]:
            print(f"\n隔离 {len(result['quarantined'])} 个文件 → {QUARANTINE_DIR}")
        if result["would_quarantine"]:
            print(
                f"\n[!] {len(result['would_quarantine'])} 个文件命中凭证形状，**默认未移动**"
                f"（如需隔离请加 --quarantine）→ 目标 {QUARANTINE_DIR}"
            )
            for rec in result["would_quarantine"]:
                print(f"    - {rec['filename']}  rule={rec['rule']}")
        if result["warnings"]:
            print(f"\n警告 ({len(result['warnings'])}):")
            for w in result["warnings"]:
                print(f"  - {w}")

    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
