import argparse
import sys
import os
import re
import json
import time
import tarfile
import tempfile
import io
import threading
from contextlib import contextmanager
from pathlib import Path
from datetime import date, datetime
from typing import Optional

import yaml
import requests

from ._dryrun import dry_run_preview


def _json_default(o):
    """`json.dumps` 的可序列化归一：`date`/`datetime` → ISO 串，其余 → `str`。

    为什么需要：经验条目的 `exported_at` / `first_seen` 等字段若以**未加引号**日期
    存盘（如 `exported_at: 2026-09-26`），`yaml.safe_load` 会解析成 `datetime.date`，
    而 `json.dumps` 对 date 无原生支持 ⇒ 无过滤列举时抛
    `TypeError: Object of type date is not JSON serializable`（实测 74 条中 57 条命中）。

    为什么不逐处补 `default=str`：本模块有 **5 处** `json.dumps`，逐处补必漏
    （EXP-2026-0020：批量补参数必须按「接收者语义」收口，而非按调用点散补）。
    故统一走本函数，并由 `test_tc_eio_004` 以「集合相等」断言全部调用点已归一。
    """
    if isinstance(o, date):          # datetime 是 date 的子类，一并覆盖
        return o.isoformat()
    return str(o)



VALID_CATEGORIES = [
    "hallucination",
    "scope_creep",
    "cascading_errors",
    "context_loss",
    "tool_misuse",
    "runtime_deviation",
    "pipeline_break",
    "content_quality",
    "instruction_decay",
    "coverage_vacuum",
    "contract_gap",
    # V2.7 new categories
    "anchor_missing",
    "agent_cp_failure",
    "spec_ambiguity",
    # V3.0 new category
    "cross_system_mismatch",
]

CATEGORY_LABELS = {
    "hallucination": "(a) 幻觉行为",
    "scope_creep": "(b) 范围蔓延",
    "cascading_errors": "(c) 级联错误",
    "context_loss": "(d) 上下文丢失",
    "tool_misuse": "(e) 工具误用",
    "runtime_deviation": "(f) 运行时行为偏差",
    "pipeline_break": "(g) 管线断链",
    "content_quality": "(h) 内容质量偏差",
    "instruction_decay": "(i) 指令衰减",
    "coverage_vacuum": "(j) 覆盖真空",
    "contract_gap": "(k) 契约断层",
    "anchor_missing": "(l) 锚定缺失",
    "agent_cp_failure": "(m) Agent CP 失败",
    "spec_ambiguity": "(m-aux) Spec 歧义",
    "cross_system_mismatch": "(n) 跨系统不一致",
}

PROVENANCE_WEIGHTS = {
    "human-reported": 0.95,
    "ci-detected": 0.85,
    "ai-inferred": 0.60,
    "community-imported": 0.50,
}


def _provenance_weight(args) -> float:
    """Get provenance weight from args or default."""
    if hasattr(args, "provenance") and args.provenance:
        return PROVENANCE_WEIGHTS.get(args.provenance, 0.60)
    return PROVENANCE_WEIGHTS.get("ai-inferred", 0.60)

# Valid lifecycle state transitions
# discovered → verified → deposited
#                        → shared → merged
# ANY        → retired
VALID_TRANSITIONS = {
    "discovered": {"verified", "retired"},
    "verified": {"deposited", "shared", "retired"},
    "deposited": {"shared", "retired"},
    "shared": {"merged", "retired"},
    "merged": {"retired"},
    "retired": set(),  # terminal state
}


def _check_transition(current: str, target: str) -> tuple[bool, str]:
    """Validate lifecycle state transition. Returns (valid, error_message)."""
    current = current or "discovered"
    if current == target:
        return True, ""  # idempotent
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        return False, f"Invalid transition: '{current}' → '{target}'. Allowed: {', '.join(sorted(allowed)) if allowed else 'none (terminal)'}"
    return True, ""


def _auto_promote(data: dict) -> str | None:
    """Check and return target state if auto-promotion conditions are met. Returns None if no change."""
    state = data.get("lifecycle_state", "discovered")
    occurrences = data.get("occurrences", 1)
    confidence = data.get("confidence", 0.5)

    if state == "discovered" and occurrences >= 2 and confidence >= 0.7:
        return "verified"
    if state == "verified" and occurrences >= 3 and confidence >= 0.8:
        return "deposited"
    return None


PROJECT_TYPE_MAP = {
    ".py": "python",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "static_site",
    ".html": "static_site",
    ".css": "static_site",
    ".vue": "static_site",
    ".md": "docs",
    ".yaml": "config",
    ".yml": "config",
    ".toml": "config",
    ".json": "config",
}


def _detect_project_type(change_dir: Path) -> str | None:
    """Detect project type from change directory file extensions. Returns None if undetectable."""
    if not change_dir.exists():
        return None
    ext_counts = {}
    for f in change_dir.rglob("*"):
        if f.is_file():
            ext = f.suffix.lower()
            if ext in PROJECT_TYPE_MAP:
                ptype = PROJECT_TYPE_MAP[ext]
                ext_counts[ptype] = ext_counts.get(ptype, 0) + 1
    if not ext_counts:
        return None
    # Return the most common type
    return max(ext_counts, key=ext_counts.get)


SANITIZE_PATTERNS = [
    (re.compile(r"(/[^\s]*?/[^\s]*?\.[a-z]{2,4})"), "<project>/<module>"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<ip-address>"),
    (re.compile(r"\b[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.(?:com|org|net|io|cn|dev|ai|co|internal|local)\b"), "<domain>"),
]


def _get_experiences_dir(project_root: Path) -> Path:
    from ..utils import read_config
    config = read_config(project_root)
    exp_dir = config.get("experience", {}).get("dir", ".fstdd/experiences")
    return project_root / exp_dir


def _ensure_dir(exp_dir: Path) -> None:
    exp_dir.mkdir(parents=True, exist_ok=True)


def _get_index_path(exp_dir: Path) -> Path:
    return exp_dir / ".experience-index.yaml"


# 进程内重入计数：同一进程连续 _save_index 不应自锁自。
_LOCK_DEPTH = 0
_LOCK_TLS = threading.local()


@contextmanager
def _index_lock(exp_dir: Path, timeout: float = 20.0):
    """跨进程索引互斥锁（可重入）。

    经验索引是「读-改-写」结构：并发 add/verify/deposit/retire 时必须把整个
    读改写周期串起来，否则 last_id 会重号、索引条目会互相覆盖。
    因此这里提供可重入的文件锁，调用方只需包住临界区即可。
    """
    global _LOCK_DEPTH

    if getattr(_LOCK_TLS, "depth", 0) > 0:      # 同线程重入：直接放行
        _LOCK_TLS.depth += 1
        try:
            yield
        finally:
            _LOCK_TLS.depth -= 1
        return

    _ensure_dir(exp_dir)
    lock_path = _get_index_path(exp_dir).with_suffix(".lock")
    deadline = time.time() + timeout
    acquired = False
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            if time.time() >= deadline:
                # 兜底：清理明显的陈旧锁（持有者已崩溃），否则放弃等待
                try:
                    if time.time() - os.path.getmtime(lock_path) > 30:
                        os.remove(lock_path)
                        continue
                except OSError:
                    pass
                print("  警告: 经验索引锁等待超时，继续执行可能冲突。", file=sys.stderr)
                break
            time.sleep(0.02 + 0.01 * (time.time() % 1))

    _LOCK_TLS.depth = getattr(_LOCK_TLS, "depth", 0) + 1
    try:
        yield acquired
    finally:
        _LOCK_TLS.depth -= 1
        if acquired:
            try:
                os.remove(lock_path)
            except OSError:
                pass


def _index_is_stale(exp_dir: Path, index_path: Path) -> bool:
    """索引是否落后于经验库（FSD-025）。

    任一条件成立即判过期：

    1. 索引不存在或不可解析；
    2. 库内条目数与索引 ``total`` 不一致 —— 覆盖外部**新增与删除**；
    3. 存在比索引更新的经验文件 —— 覆盖「增删相互抵消但内容已变」。

    历史缺陷：原实现仅在索引**不存在**时才重建，任何绕过 CLI 的库变更
    （手工落盘、迁移脚本、外部同步）都不会反映。实测库内 15 条而
    ``stats`` 长期报 12 条。
    """
    if not index_path.exists():
        return True
    try:
        idx_mtime = index_path.stat().st_mtime
        with open(index_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return True

    files = _iter_experience_files(exp_dir)
    if len(files) != data.get("total", -1):
        return True

    for p in files:
        try:
            if p.stat().st_mtime > idx_mtime + 1e-6:
                return True
        except OSError:
            continue
    return False


def _load_index(exp_dir: Path, _locked: bool = False) -> dict:
    index_path = _get_index_path(exp_dir)
    if not _index_is_stale(exp_dir, index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"last_id": 0, "total": 0}
    if _locked:
        index = _rebuild_index(exp_dir)
        _save_index(exp_dir, index)
        return index
    with _index_lock(exp_dir):
        return _load_index(exp_dir, _locked=True)


def _save_index(exp_dir: Path, index: dict) -> None:
    """原子落盘索引；自带锁，也可安全地被 _index_lock 包住（重入）。"""
    with _index_lock(exp_dir) as acquired:
        _ensure_dir(exp_dir)
        index_path = _get_index_path(exp_dir)
        tmp_path = index_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                yaml.dump(index, f, allow_unicode=True, default_flow_style=False)
            os.replace(tmp_path, index_path)
        except OSError:
            # 极端并发下 Windows 可能瞬时拒绝 replace，退化为直接写
            with open(index_path, "w", encoding="utf-8", newline="") as f:
                yaml.dump(index, f, allow_unicode=True, default_flow_style=False)
            print("  警告: 索引原子替换失败，已退化为直接写入。", file=sys.stderr)


def _rebuild_index(exp_dir: Path) -> dict:
    index = {
        "last_id": 0,
        "total": 0,
        "by_category": {},
        "by_language": {},
        "by_lifecycle": {},
        "by_severity": {},
    }
    if not exp_dir.exists():
        return index

    # 向后兼容（2026-09-17）：同时认 EXP-*.md 和带 experience_id frontmatter 的任意 .md
    # 背景：从旧 STDD 迁移的经验文件名是语义化的（如 scheduler_daily_queue_not_dropped.md），
    # 不带 EXP- 前缀 → 原 glob("EXP-*.md") 全部忽略 → list/stats 显示 0。
    # 修复：扫所有 .md，优先用 frontmatter 的 experience_id，没有则用文件名 stem。
    for exp_file in _iter_experience_files(exp_dir):
        data = _load_experience(exp_file)
        if data is None:
            continue
        eid = data.get("experience_id", exp_file.stem)
        _index_add_entry(index, eid, data)

    index["total"] = sum(len(v) for v in index.get("by_category", {}).values())
    if index["total"] > 0:
        ids = []
        for v in index.get("by_category", {}).values():
            ids.extend(v)
        # 向后兼容（2026-09-17）：迁移的经验 ID 可能是空串或语义名（非 EXP-<数字>）
        # → int() 会炸。容错：只对纯数字后缀取 max，非数字的跳过。
        numeric_ids = []
        for x in ids:
            try:
                numeric_ids.append(int(x.split("-")[-1]))
            except (ValueError, IndexError):
                continue
        index["last_id"] = max(numeric_ids) if numeric_ids else 0
    return index


def _index_add_entry(index: dict, eid: str, data: dict) -> None:
    cat = data.get("category", "unknown")
    lang = data.get("language") or "unknown"
    lc = data.get("lifecycle_state", "discovered")
    sev = data.get("severity", "medium")

    index.setdefault("by_category", {}).setdefault(cat, []).append(eid)
    index.setdefault("by_language", {}).setdefault(lang, []).append(eid)
    index.setdefault("by_lifecycle", {}).setdefault(lc, []).append(eid)
    index.setdefault("by_severity", {}).setdefault(sev, []).append(eid)


def _read_installation_id(project_root: Path) -> str | None:
    """从 ``.fstdd/version.yaml`` 读取 ``installation_id``（形状校验在 utils 内统一）。

    文件不存在、无字段、或字段值不是合法 ID 形状时返回 None（调用方回落旧格式）。
    非法值会向 stderr 出声：否则「明明配了 ID 却仍产出旧格式」会被当成正常回落。
    """
    from ..utils import read_installation_id

    return read_installation_id(project_root, warn=True)


def _next_id(index: dict, project_root: Path | None = None) -> str:
    """分配下一个经验 ID。

    - ``project_root`` 给定且 ``.fstdd/version.yaml`` 含 ``installation_id``
      → ``{installation_id}-EXP-{year}-{NNNN:04d}``
    - 否则 → ``EXP-{year}-{NNNN:04d}``（旧格式，向后兼容）
    """
    last = index.get("last_id", 0)
    year = datetime.now().year
    next_num = last + 1
    base = f"EXP-{year}-{next_num:04d}"
    install_id = _read_installation_id(project_root)  # project_root=None 时返回 None
    if install_id:
        return f"{install_id}-{base}"
    return base


def _iter_experience_files(exp_dir) -> list:
    """枚举经验库中的经验文件 —— 全模块唯一入口（FSD-004）。

    约定（2026-09-17 起）：库内接受任意 ``*.md``，标识优先取 frontmatter 的
    ``experience_id``，缺失时退回文件名 stem。

    历史缺陷：原实现散布 10 处 ``glob("EXP-*.md")`` 假设，而 STDD→fSTDD 迁移
    来的文件名是语义化的（``scheduler_daily_queue_not_dropped.md``）→
    ``search`` 静默返回空数组 + ``exit=0``（错误结果不可察觉）。

    排除项：隐藏文件（``.`` 开头，如 ``.experience-index.yaml`` 不解但防御性保留）。
    """
    d = Path(exp_dir)
    if not d.exists():
        return []
    return sorted(p for p in d.glob("*.md") if not p.name.startswith("."))


# 数值型 frontmatter 字段：迁移数据里可能被写成带引号的字符串（'0.8'）。
_INT_KEYS = (
    "occurrences",
    "adoption_count",
    "community_votes_useful",
    "community_votes_unuseful",
)
_FLOAT_KEYS = ("confidence", "provenance_weight")
_NUMERIC_KEYS = _INT_KEYS + _FLOAT_KEYS


def _coerce_numeric_fields(data: dict) -> dict:
    """归一化数值字段 —— 读取入口统一收口（FSD-023）。

    背景：迁移脚本把 ``confidence: 0.8`` 写成了 ``confidence: '0.8'``（字符串）。
    原 ``glob("EXP-*.md")`` 漏读这批文件，所以该缺陷从未暴露；修复 glob 后
    ``search`` 立即抛 ``TypeError: can't multiply sequence by non-int``。

    策略：在读取入口统一转换，而非在下游 20+ 处算术里各写容错（必然漏）。
    无法转换时删除该键，让下游 ``.get(key, default)`` 的默认值生效。
    """
    for key in _NUMERIC_KEYS:
        if key not in data:
            continue
        raw = data[key]
        if isinstance(raw, bool) or isinstance(raw, (int, float)):
            continue
        try:
            num = float(str(raw).strip())
        except (ValueError, TypeError):
            data.pop(key, None)
            continue
        data[key] = int(num) if key in _INT_KEYS else num
    return data


def _load_experience(filepath: Path) -> Optional[dict]:
    """解析经验文件并返回合并后的 frontmatter 字典（FSD-026）。

    兼容三类结构：单块（--- 包裹 frontmatter 后接正文）、inbox 双块
    （HTML 注释头 + 第1块导出元数据 + 第2块真身 + 正文）、无 frontmatter。

    实现：按全部 --- 切片，逐段 yaml.safe_load，凡是 dict 就合并进累加器，
    靠后的块覆盖靠前的冲突键 → 真身块优先。空段 / 非 dict 段（HTML 注释头、
    正文）跳过。

    历史缺陷：原 content.split("---", 2)[1] 只取首个块，inbox 双块文件的真身
    （第二块）被静默丢弃，导致 experience list 约 58% 条目 ID 列空白
    （P1 bug，本 change 修复）。
    """
    if not filepath.exists():
        return None
    content = filepath.read_text(encoding="utf-8")
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
            merged.update(loaded)  # 后块覆盖前块冲突键 → 真身块优先
    if not merged:
        return None
    return _coerce_numeric_fields(merged)


def _sanitize(text: str) -> str:
    for pattern, replacement in SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _format_table(experiences: list[dict]) -> str:
    if not experiences:
        return "  (无经验记录)"
    lines = []
    header = f"  {'ID':<16} {'Category':<22} {'Severity':<10} {'Occur':<6} {'Lifecycle':<12} Pattern"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for e in experiences:
        cat_label = CATEGORY_LABELS.get(e.get("category", ""), e.get("category", ""))
        lines.append(
            f"  {e.get('experience_id', ''):<16} "
            f"{cat_label:<22} "
            f"{e.get('severity', ''):<10} "
            f"{e.get('occurrences', 0):<6} "
            f"{e.get('lifecycle_state', ''):<12} "
            f"{e.get('pattern', '')}"
        )
    return "\n".join(lines)


def _cmd_list(args: argparse.Namespace, exp_dir: Path) -> None:
    index = _load_index(exp_dir)
    show_all = getattr(args, "all", False)
    experiences = []
    for exp_file in _iter_experience_files(exp_dir):
        data = _load_experience(exp_file)
        if data is None:
            continue

        # Hide retired by default
        if not show_all and data.get("lifecycle_state") == "retired":
            continue

        if args.category and data.get("category") != args.category:
            continue
        if args.language and data.get("language") != args.language:
            continue
        if args.lifecycle and data.get("lifecycle_state") != args.lifecycle:
            continue
        if args.severity and data.get("severity") != args.severity:
            continue
        # V2.7: provenance filter
        if getattr(args, "provenance", None) and data.get("provenance") != args.provenance:
            continue

        experiences.append(data)

    if args.format == "json":
        print(json.dumps(experiences, ensure_ascii=False, indent=2, default=_json_default))
    elif args.format == "yaml":
        print(yaml.dump(experiences, allow_unicode=True, default_flow_style=False))
    else:
        print()
        print(f"  经验库 ({len(experiences)}/{index.get('total', 0)} 条):")
        print(_format_table(experiences))
        print()


def _cmd_add(args: argparse.Namespace, exp_dir: Path, project_root: Path | None = None) -> None:
    if args.category not in VALID_CATEGORIES:
        print(f" 无效的 category: '{args.category}'")
        print(f" 有效值: {', '.join(VALID_CATEGORIES)}")
        sys.exit(1)

    _ensure_dir(exp_dir)

    # 整个「读索引 → 分配 id → 写经验文件 → 更新索引」必须在同一临界区内完成，
    # 否则并发 add 会分配到重复 id，并互相覆盖索引条目。
    with _index_lock(exp_dir):
        index = _load_index(exp_dir, _locked=True)

        eid = _next_id(index, project_root)
        today = datetime.now().strftime("%Y-%m-%d")

        frontmatter = {
            "experience_id": eid,
            "category": args.category,
            "pattern": args.pattern,
            "root_cause": args.root_cause or "",
            "detection_trigger": args.detection_trigger or "",
            "fix_template": args.fix_template or "",
            "language": args.language,
            "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
            "occurrences": 1,
            "severity": args.severity or "medium",
            "confidence": 0.5,
            "source_change": args.source_change or "manual",
            "source_file": "",
            "lifecycle_state": "discovered",
            "first_seen": today,
            "last_seen": today,
            "community_votes_useful": 0,
            "community_votes_unuseful": 0,
            "adoption_count": 0,
            "project_type": getattr(args, "project_type", None) or _detect_project_type(Path.cwd() / ".fstdd" / "changes"),
            # V2.7: provenance tracking
            "provenance": getattr(args, "provenance", None) or "ai-inferred",
            "provenance_weight": _provenance_weight(args),
        }

        body = args.body or ""
        content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n\n{body}\n"

        exp_file = exp_dir / f"{eid}.md"
        exp_file.write_text(content, encoding="utf-8")

        _index_add_entry(index, eid, frontmatter)
        # 用已分配的 id 推进 last_id，避免与并发写入互相覆盖
        index["last_id"] = max(index.get("last_id", 0), int(eid.split("-")[-1]))
        index["total"] = sum(len(v) for v in index.get("by_category", {}).values())
        _save_index(exp_dir, index)

    print(f" 经验已创建: {eid} ({CATEGORY_LABELS.get(args.category, args.category)})")


def _cmd_stats(args: argparse.Namespace, exp_dir: Path) -> None:
    index = _load_index(exp_dir)

    if args.format == "json":
        print(json.dumps(index, ensure_ascii=False, indent=2, default=_json_default))
        return

    print()
    print("  经验库统计")
    print(f"  {'─' * 40}")
    print(f"  总经验数: {index.get('total', 0)}")

    by_cat = index.get("by_category", {})
    if by_cat:
        print("\n  按失败模式分类:")
        for cat, ids in sorted(by_cat.items(), key=lambda x: -len(x[1])):
            label = CATEGORY_LABELS.get(cat, cat)
            print(f"    {label}: {len(ids)} 条")

    by_lang = index.get("by_language", {})
    if by_lang:
        print("\n  按语言分类:")
        for lang, ids in sorted(by_lang.items(), key=lambda x: -len(x[1])):
            print(f"    {lang}: {len(ids)} 条")

    by_sev = index.get("by_severity", {})
    if by_sev:
        print("\n  按严重程度:")
        for sev, ids in sorted(by_sev.items(), key=lambda x: -len(x[1])):
            print(f"    {sev}: {len(ids)} 条")

    by_lc = index.get("by_lifecycle", {})
    if by_lc:
        print("\n  按生命周期:")
        for lc, ids in sorted(by_lc.items(), key=lambda x: -len(x[1])):
            print(f"    {lc}: {len(ids)} 条")
    print()


def _cmd_export(args: argparse.Namespace, exp_dir: Path) -> None:
    publish = getattr(args, "publish", False)
    no_sanitize = getattr(args, "no_sanitize", False)

    if publish and no_sanitize:
        print("  Warning: exporting without sanitization — review before sharing")

    experiences = []
    for exp_file in _iter_experience_files(exp_dir):
        data = _load_experience(exp_file)
        if data is None:
            continue
        eid = data.get("experience_id", exp_file.stem)

        content = exp_file.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        body = parts[2].strip() if len(parts) >= 3 else ""

        if not no_sanitize:
            body = _sanitize(body)
            for key in ("pattern", "root_cause", "detection_trigger", "fix_template"):
                if key in data and data[key]:
                    data[key] = _sanitize(str(data[key]))
            if "source_file" in data:
                data["source_file"] = _sanitize(str(data["source_file"]))
            if "source_change" in data and data["source_change"]:
                data["source_change"] = _sanitize(str(data["source_change"]))

        if publish:
            data["lifecycle_state"] = "shared"
            full_content = f"---\n{yaml.dump(data, allow_unicode=True, default_flow_style=False)}---\n{body}"
            exp_file.write_text(full_content, encoding="utf-8")

        experiences.append({"frontmatter": data, "body": body})

    if publish:
        # Create tar.gz package
        tar_name = args.output or f"{getattr(args, 'experience_id', 'experiences')}.tar.gz"
        if not tar_name.endswith(".tar.gz"):
            tar_name += ".tar.gz"
        tar_path = Path(tar_name) if os.path.isabs(tar_name) else Path.cwd() / tar_name

        with tarfile.open(tar_path, "w:gz") as tar:
            for exp in experiences:
                eid = exp["frontmatter"]["experience_id"]
                frontmatter_yaml = yaml.dump(exp["frontmatter"], allow_unicode=True, default_flow_style=False)
                exp_content = f"---\n{frontmatter_yaml}---\n\n{exp['body']}"

                info = tarfile.TarInfo(name=f"{eid}.md")
                info.size = len(exp_content.encode("utf-8"))
                tar.addfile(info, io.BytesIO(exp_content.encode("utf-8")))

            # Add index file
            index = _load_index(exp_dir)
            index_content = yaml.dump(index, allow_unicode=True, default_flow_style=False)
            info = tarfile.TarInfo(name=".experience-index.yaml")
            info.size = len(index_content.encode("utf-8"))
            tar.addfile(info, io.BytesIO(index_content.encode("utf-8")))

        print(f"  Exported {len(experiences)} experiences to: {tar_path}")
        # 不外发到第三方：引导使用本项目脚本回传到自有仓库（强制脱敏）
        print("  回传请使用（目标为自有仓库，强制脱敏）:")
        print("    python tools/share_experience.py --export --publish")
    else:
        result = json.dumps(experiences, ensure_ascii=False, indent=2, default=_json_default) if args.format == "json" else yaml.dump(experiences, allow_unicode=True, default_flow_style=False)

        if args.output and not publish:
            Path(args.output).write_text(result, encoding="utf-8")
            print(f" 已导出 {len(experiences)} 条经验到: {args.output}")
        elif not publish:
            print(result)


def _read_community_config(project_root: Path) -> dict:
    from ..utils import read_config
    config = read_config(project_root)
    return config.get("community", {})


def _download_with_fallback(pack_name: str, pack_version: str, config: dict) -> bytes | None:
    """Download pack from registries with priority ordering and timeout fallback.

    Supports two registry types:
      - github (default):  {url}/experience-{pack}-latest.tar.gz
      - gitee:             {url}/{version}/experience-{pack}-{version}.tar.gz
    """
    registries = sorted(config.get("registries", []), key=lambda r: r.get("priority", 99))
    timeout = config.get("fallback_timeout", 5)

    for i, registry in enumerate(registries):
        registry_type = registry.get("type", "github")

        if registry_type == "gitee":
            # Gitee: /releases/download/{tag}/{file} — no /latest/ redirect
            pack_filename = f"experience-{pack_name}-{pack_version}.tar.gz"
            url = f"{registry['url'].rstrip('/')}/{pack_version}/{pack_filename}"
        else:
            # GitHub (default): /releases/latest/download/{file}
            pack_filename = f"experience-{pack_name}-latest.tar.gz"
            url = f"{registry['url'].rstrip('/')}/{pack_filename}"

        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            if i > 0:
                print(f"  [FALLBACK] Switched to {registry['name']} mirror")
            return resp.content
        except requests.Timeout:
            if i < len(registries) - 1:
                source_name = registry['name']
                next_name = registries[i + 1]['name']
                print(f"  [FALLBACK] {source_name} timed out, switched to {next_name} mirror")
        except requests.RequestException as e:
            if i < len(registries) - 1:
                print(f"  [FALLBACK] {registry['name']} unreachable ({e}), switching to {registries[i + 1]['name']} mirror")

    return None


def _cmd_pull(args: argparse.Namespace, exp_dir: Path) -> None:
    project_root = Path.cwd()
    config = _read_community_config(project_root)

    if not config.get("registries"):
        print("  No community registries configured in experience.yaml")
        sys.exit(1)

    pack_name = args.pack_name

    # Look up pack version from config
    pack_version = None
    for pack in config.get("packs", []):
        if pack.get("name") == pack_name:
            pack_version = pack.get("version", "latest")
            break
    if pack_version is None:
        pack_version = "latest"

    print(f"  Pulling experience pack: {pack_name} (version: {pack_version}) ...")

    data = _download_with_fallback(pack_name, pack_version, config)
    if data is None:
        print(f"  Error: all registries unreachable")
        sys.exit(1)

    existing_ids = set()
    for f in _iter_experience_files(exp_dir):
        existing_ids.add(f.stem)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        with tarfile.open(tmp_path, "r:gz") as tar:
            members = tar.getmembers()
            # FSD-004-EXEMPT: 这里过滤的是 tar 包内成员名。pack 由 registry 产出、
            # 遵循 EXP-*.md 命名约定，与「本地库允许语义名」是两回事，故保留前缀判断。
            # 本地库枚举一律走 _iter_experience_files（见 L315）。
            exp_members = [m for m in members if m.name.startswith("EXP-") and m.name.endswith(".md")]
            index_member = None
            for m in members:
                if m.name.endswith(".experience-index.yaml"):
                    index_member = m
                    break

            if not exp_members and index_member is None:
                print(f"  Error: pack '{pack_name}' not found in registry")
                sys.exit(1)

            new_count = 0
            skip_count = 0
            update_count = 0

            for member in exp_members:
                eid = Path(member.name).stem
                dest = exp_dir / f"{eid}.md"

                if dest.exists():
                    print(f"  [SKIP] {eid} already exists locally")
                    skip_count += 1
                    continue

                fobj = tar.extractfile(member)
                if fobj:
                    dest.write_bytes(fobj.read())
                    new_count += 1
                    print(f"  [NEW] {eid} imported")

            # Merge index: add new IDs, update vote metadata for existing IDs
            if index_member:
                fobj = tar.extractfile(index_member)
                if fobj:
                    remote_index = yaml.safe_load(fobj.read()) or {}
                    local_index = _load_index(exp_dir)

                    for cat, ids in remote_index.get("by_category", {}).items():
                        for eid in ids:
                            if eid in existing_ids:
                                # Update vote metadata for existing experience
                                exp_file = exp_dir / f"{eid}.md"
                                local_data = _load_experience(exp_file)
                                if local_data:
                                    # Find the remote experience data for vote sync
                                    for rm in exp_members:
                                        if Path(rm.name).stem == eid:
                                            rf = tar.extractfile(rm)
                                            if rf:
                                                remote_data = _coerce_numeric_fields(yaml.safe_load(rf.read().decode("utf-8").split("---", 2)[1]) or {})
                                                for vk in ("community_votes_useful", "community_votes_unuseful", "adoption_count"):
                                                    if vk in remote_data:
                                                        local_data[vk] = remote_data[vk]
                                                content = exp_file.read_text(encoding="utf-8")
                                                parts = content.split("---", 2)
                                                body = parts[2] if len(parts) >= 3 else ""
                                                new_content = f"---\n{yaml.dump(local_data, allow_unicode=True, default_flow_style=False)}---\n{body}"
                                                exp_file.write_text(new_content, encoding="utf-8")
                                                update_count += 1
                                                break
                            else:
                                local_index.setdefault("by_category", {}).setdefault(cat, []).append(eid)

                    _save_index(exp_dir, local_index)

            total = new_count + update_count
            print(f"  Done: {total} experiences ({new_count} new, {update_count} updated, {skip_count} skipped)")

    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _cmd_verify(args: argparse.Namespace, exp_dir: Path) -> None:
    """Manually verify a discovered experience."""
    exp_file = exp_dir / f"{args.experience_id}.md"
    data = _load_experience(exp_file)
    if data is None:
        print(f"Experience '{args.experience_id}' not found.")
        sys.exit(1)

    current_state = data.get("lifecycle_state", "discovered")
    valid, err = _check_transition(current_state, "verified")
    if not valid:
        print(err)
        sys.exit(1)

    # Update frontmatter
    data["lifecycle_state"] = "verified"
    if "occurrences" in data:
        data["occurrences"] = max(data["occurrences"], 2)
    if "confidence" in data:
        data["confidence"] = max(data["confidence"], 0.7)

    content = exp_file.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    new_content = f"---\n{yaml.dump(data, allow_unicode=True, default_flow_style=False)}---\n{body}"
    exp_file.write_text(new_content, encoding="utf-8")

    # Update index
    index = _load_index(exp_dir, _locked=True)
    _index_remove_entry(index, args.experience_id, current_state)
    _index_add_entry(index, args.experience_id, data)
    _save_index(exp_dir, index)

    print(f"{args.experience_id} verified (discovered → verified)")


def _cmd_deposit(args: argparse.Namespace, exp_dir: Path) -> None:
    """Manually deposit a verified experience (requires occurrences>=3, confidence>=0.8)."""
    exp_file = exp_dir / f"{args.experience_id}.md"
    data = _load_experience(exp_file)
    if data is None:
        print(f"Experience '{args.experience_id}' not found.")
        sys.exit(1)

    current_state = data.get("lifecycle_state", "discovered")
    valid, err = _check_transition(current_state, "deposited")
    if not valid:
        print(err)
        sys.exit(1)

    if data.get("occurrences", 1) < 3:
        print(f"Cannot deposit: occurrences ({data.get('occurrences', 1)}) < 3")
        sys.exit(1)
    if data.get("confidence", 0.5) < 0.8:
        print(f"Cannot deposit: confidence ({data.get('confidence', 0.5)}) < 0.8")
        sys.exit(1)

    data["lifecycle_state"] = "deposited"

    content = exp_file.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    new_content = f"---\n{yaml.dump(data, allow_unicode=True, default_flow_style=False)}---\n{body}"
    exp_file.write_text(new_content, encoding="utf-8")

    index = _load_index(exp_dir, _locked=True)
    _index_remove_entry(index, args.experience_id, current_state)
    _index_add_entry(index, args.experience_id, data)
    _save_index(exp_dir, index)

    print(f"{args.experience_id} deposited (verified → deposited)")


def _cmd_retire(args: argparse.Namespace, exp_dir: Path) -> None:
    """Retire an experience from any lifecycle state."""
    exp_file = exp_dir / f"{args.experience_id}.md"
    data = _load_experience(exp_file)
    if data is None:
        print(f"Experience '{args.experience_id}' not found.")
        sys.exit(1)

    current_state = data.get("lifecycle_state", "discovered")
    valid, err = _check_transition(current_state, "retired")
    if not valid:
        print(err)
        sys.exit(1)

    reason = getattr(args, "reason", "")
    data["lifecycle_state"] = "retired"
    data["retire_reason"] = reason
    data["retired_date"] = datetime.now().strftime("%Y-%m-%d")

    content = exp_file.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    new_content = f"---\n{yaml.dump(data, allow_unicode=True, default_flow_style=False)}---\n{body}"
    exp_file.write_text(new_content, encoding="utf-8")

    index = _load_index(exp_dir, _locked=True)
    _index_remove_entry(index, args.experience_id, current_state)
    _index_add_entry(index, args.experience_id, data)
    _save_index(exp_dir, index)

    print(f"{args.experience_id} retired ({current_state} → retired)")


def _index_remove_entry(index: dict, eid: str, old_state: str) -> None:
    """Remove an entry from all index buckets based on old state. Best-effort cleanup."""
    for bucket in ("by_category", "by_language", "by_lifecycle", "by_severity"):
        for key in list(index.get(bucket, {}).keys()):
            entry_list = index[bucket].get(key, [])
            if eid in entry_list:
                entry_list.remove(eid)
                if not entry_list:
                    del index[bucket][key]



# ── 抽取源（V3.3.9 扩展：C1 / REQ-001）──────────────────────────────────
# 原实现只认 test-report.md；现扩至三类 DELIVER 留痕源。
_EXTRACT_SOURCES = ("test-report", "design-adjustments", "adjudication")

_SOURCE_FILES = {
    "test-report": "test-report.md",
    "design-adjustments": "design-adjustments.md",
    "adjudication": "adjudication-log.tsv",
}

_SOURCE_ALIASES = {
    "test-report": "test-report",
    "test_report": "test-report",
    "design-adjustments": "design-adjustments",
    "design_adjustments": "design-adjustments",
    "adjudication": "adjudication",
    "adjudication-log": "adjudication",
    "adjudication_log": "adjudication",
}

# 设计偏离「调整类型」→ 失败模式类别的映射（首个命中的关键词生效）。
_ADJ_TYPE_CATEGORY = (
    ("scenario", "coverage_vacuum"),
    ("覆盖", "coverage_vacuum"),
    ("接口", "contract_gap"),
    ("契约", "contract_gap"),
    ("技术方案", "cross_system_mismatch"),
    ("设计", "cross_system_mismatch"),
    ("规格", "spec_ambiguity"),
    ("spec", "spec_ambiguity"),
)

_ADJ_HEADING_RE = re.compile(r"^###\s+调整\s*(\d+)\s*[:：]?\s*(.*)$", re.MULTILINE)
_ADJ_FIELD_RE = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*\s*[:：]\s*(.*)$")


def _resolve_extract_sources(args) -> list:
    """从 args 解析抽取源；默认（无 --source/--all）= 仅 test-report（向后兼容）。"""
    if getattr(args, "all", False):
        return list(_EXTRACT_SOURCES)
    src = getattr(args, "source", None)
    if src:
        return [_SOURCE_ALIASES.get(str(src).strip().lower(), "test-report")]
    return ["test-report"]


def _adj_category(text: str) -> str:
    """把设计偏离的「调整类型/标题」映射到失败模式类别。"""
    low = (text or "").lower()
    for kw, cat in _ADJ_TYPE_CATEGORY:
        if kw in low:
            return cat
    return "spec_ambiguity"


def _parse_design_adjustments(text: str) -> list:
    """解析 design-adjustments.md：汇总表（严重程度/调整类型）+ `### 调整 N:` 小节。"""
    meta = {}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) >= 4 and re.fullmatch(r"\d+", cells[0]):
            meta[cells[0]] = cells  # [num, 调整类型, 涉及文档, 严重程度, 调整阶段, 影响TC, 用户已知]

    heads = list(_ADJ_HEADING_RE.finditer(text))
    patterns = []
    for i, m in enumerate(heads):
        num, title = m.group(1), m.group(2).strip()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end]
        fields = {}
        for line in body.splitlines():
            fm = _ADJ_FIELD_RE.match(line)
            if fm:
                fields[fm.group(1).strip()] = fm.group(2).strip()
        cells = meta.get(num, [])
        adj_type = (cells[1] if len(cells) > 1 else "") or fields.get("调整类型", "")
        sev_raw = (cells[3] if len(cells) > 3 else "") or fields.get("严重程度", "")
        severity = "high" if re.search(r"major|严重|高", sev_raw, re.IGNORECASE) else "medium"
        patterns.append({
            "category": _adj_category(f"{adj_type} {title}"),
            "pattern": f"[设计偏离] {title}",
            "root_cause": fields.get("调整原因", ""),
            "detection_trigger": fields.get("原始设计", "") or "design-adjustment",
            "fix_template": fields.get("调整内容", ""),
            "occurrences": 1,
            "severity": severity,
            "tags": ["design-adjustment"],
            "language": "python",
            "source_file": "design-adjustments.md",
        })
    return patterns


def _parse_adjudication_log(text: str) -> list:
    """解析 adjudication-log.tsv：`eid \\t decision \\t versions=N \\t from=[...]`，按 eid 去重。"""
    patterns = []
    seen = set()
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        cells = s.split("\t")
        if len(cells) < 2:
            continue
        eid, decision = cells[0].strip(), cells[1].strip()
        if not eid or eid in seen:
            continue
        seen.add(eid)
        rest = " ".join(c.strip() for c in cells[2:]).strip()
        vm = re.search(r"versions=(\d+)", rest)
        versions = int(vm.group(1)) if vm else 1
        patterns.append({
            "category": "cross_system_mismatch",
            "pattern": f"[多节点漂移] {eid}: {decision} ({rest})".strip(),
            "root_cause": "同一 eid 在多节点/多平台存在多份不一致副本",
            "detection_trigger": "adjudication-log",
            "fix_template": f"按裁决 {decision} 收敛副本",
            "occurrences": versions,
            "severity": "high" if versions >= 3 else "medium",
            "tags": ["adjudication", "multi-node-drift"],
            "language": "python",
            "source_file": "adjudication-log.tsv",
            "experience_id": eid,
        })
    return patterns


def _extract_sources(change_dir: Path, sources: list) -> list:
    """从 change 目录按源列表抽取 pattern（缺失源静默跳过）。"""
    patterns = []
    for src in sources:
        fname = _SOURCE_FILES.get(src)
        if not fname:
            continue
        fp = change_dir / fname
        if not fp.exists():
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        if src == "test-report":
            patterns.extend(_parse_test_report(text))
            patterns.extend(_parse_test_anomalies(text))
        elif src == "design-adjustments":
            patterns.extend(_parse_design_adjustments(text))
        elif src == "adjudication":
            patterns.extend(_parse_adjudication_log(text))
    return patterns


def _dedup_patterns(patterns: list) -> list:
    """按 experience_id（有则优先）或 pattern 文本去重，保持首次出现顺序。"""
    out, seen = [], set()
    for p in patterns:
        key = (p.get("experience_id") or p.get("pattern", "")).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


_TRUTHY = ("1", "true", "yes", "on")


def _looks_like_project(p: Path) -> bool:
    """判断目录是否是 FSTDD **项目根**（而非全局注册表目录）。

    ⚠️ 实测环境事实（2026-10-18）：`~/.fstdd/` 存在，但里面只有一个
    `projects.yaml`（全局项目注册表），**没有** `config.d/`。若只用
    「目录下有 `.fstdd/`」作判据，从任何 `C:/Users/<user>/` 下的路径向上找都会
    命中它 ⇒ 把用户主目录当成项目根，配置读取指向不存在的路径。
    故要求 `.fstdd/` 下至少有一个真正的项目骨架子目录。
    """
    fstdd = p / ".fstdd"
    if not fstdd.is_dir():
        return False
    return any((fstdd / name).is_dir() for name in ("config.d", "changes", "templates"))


def _find_project_root(start: Path | None = None) -> Path:
    """从 start（缺省 cwd）向上找第一个**像 FSTDD 项目**的目录；找不到返回 start。

    2026-10-18 审计 F7：`_share_disabled()` 原来直接用 `Path.cwd()`。从项目
    **子目录**运行 CLI 时，cwd 下没有 `.fstdd/`，配置读不到 ⇒ 开关被误判成
    「未配置 ⇒ 开启」，与 `tools/share_experience.py` 的判定分叉。
    向上找是 git 的惯例，也最不容易错；判据见 `_looks_like_project()`。
    """
    here = Path(start or Path.cwd()).resolve()
    for cand in (here, *here.parents):
        if _looks_like_project(cand):
            return cand
    return here


def _share_disabled() -> bool:
    """静默上传总开关：`FSTDD_NO_SHARE` 优先，`.fstdd/config.d/experience.yaml`
    的 `share.silent.enabled` 次之（语义与 ``tools/share_experience.py`` 一致）。

    `UnicodeDecodeError` 必须显式捕获：它不是 `OSError` 的子类（实测
    `issubclass(UnicodeDecodeError, OSError) is False`），配置文件含非法 UTF-8
    字节时异常会逃逸到 `_cmd_auto_deposit`，可能把 DELIVER 流程带崩 ——
    而本开关的契约是「读不到就按开启处理」，绝不能因为编码问题阻断主流程。
    """
    if os.environ.get("FSTDD_NO_SHARE", "").strip().lower() in _TRUTHY:
        return True
    try:
        cfg = _find_project_root() / ".fstdd" / "config.d" / "experience.yaml"
        if cfg.is_file():
            data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            silent = (data.get("share") or {}).get("silent") or {}
            return not bool(silent.get("enabled", True))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        pass
    return False


def _find_change_dir(changes_dir: Path, wanted_files: list):
    """在 .fstdd/changes 下按目录名倒序找第一个含任一目标源文件的 change。"""
    for d in sorted(changes_dir.iterdir(), reverse=True):
        if d.name.startswith("_") or d.name.startswith("."):
            continue
        if any((d / f).exists() for f in wanted_files):
            return d
    return None


def _write_drafts(patterns: list, change_dir: Path, exp_dir_path: Path, proj_lang: str) -> int:
    """把 patterns 落盘为 lifecycle=discovered 草稿，返回条数。

    eid 取自索引 ``last_id``（而非文件计数）—— 库内存在空洞时用计数会重号覆盖既有条目。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    index = _load_index(exp_dir_path)
    next_num = int(index.get("last_id", 0) or 0) + 1
    count = 0
    for p in patterns:
        eid = f"EXP-{datetime.now().year}-{next_num:04d}"
        next_num += 1
        frontmatter = {
            "experience_id": eid, "category": p["category"],
            "pattern": p["pattern"], "root_cause": p.get("root_cause", ""),
            "detection_trigger": p.get("detection_trigger", ""),
            "fix_template": p.get("fix_template", ""),
            "language": p.get("language", proj_lang),
            "tags": p.get("tags", []), "occurrences": p.get("occurrences", 1),
            "severity": p["severity"], "confidence": 0.5,
            "source_change": change_dir.name,
            "source_file": p.get("source_file", ""),
            "lifecycle_state": "discovered",
            "first_seen": today, "last_seen": today,
            "provenance": "ci-detected", "provenance_weight": 0.85,
            "community_votes_useful": 0, "community_votes_unuseful": 0,
            "adoption_count": 0, "project_type": "python",
        }
        body = f"# {p['pattern']}\n\nCategory: {CATEGORY_LABELS.get(p['category'], p['category'])}\n\nRoot Cause: {p.get('root_cause', 'TBD')}\n\nDetection: {p.get('detection_trigger', 'auto-detected')}\n\nFix: {p.get('fix_template', 'TBD')}"
        fm_yaml = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        (exp_dir_path / f"{eid}.md").write_text(f"---\n{fm_yaml}---\n\n{body}", encoding="utf-8")
        count += 1
    _load_index(exp_dir_path)
    return count


def _cmd_extract(args, exp_dir):
    """Auto-extract experience drafts from the current change's留痕源。

    源由 ``--source`` / ``--all`` 决定，默认 ``test-report``（向后兼容，SC-001/SC-005）。
    """
    from ..utils import read_config
    project_root = Path.cwd()
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        print("  No changes/ directory, skipping extraction.")
        return

    sources = _resolve_extract_sources(args)
    wanted = [_SOURCE_FILES[s] for s in sources]
    change_dir = _find_change_dir(changes_dir, wanted)
    if change_dir is None:
        print(f"  No source file found in current change ({', '.join(wanted)}), skipping.")
        return

    print(f"  Extracting from {change_dir.name} ({', '.join(sources)}) ...")
    patterns = _dedup_patterns(_extract_sources(change_dir, sources))
    filtered = [p for p in patterns
                if p["severity"] in ("high", "critical", "medium") or p.get("occurrences", 1) >= 2]
    skipped = len(patterns) - len(filtered)
    if not filtered:
        print(f"  No patterns to deposit. ({len(patterns)} found, {skipped} low-value skipped)")
        return
    exp_dir_path = Path(exp_dir)
    exp_dir_path.mkdir(parents=True, exist_ok=True)
    config = read_config(project_root)
    proj_lang = config.get("project", {}).get("language", "python")
    count = _write_drafts(filtered, change_dir, exp_dir_path, proj_lang)
    print(f"  Generated {count} draft(s) (lifecycle=discovered)")
    if skipped > 0:
        print(f"  {skipped} low-value pattern(s) skipped")
    print("  Run 'fstdd experience review' to confirm drafts")


def _cmd_auto_deposit(args, exp_dir):
    """DELIVER 期**非交互**自动沉淀（C2 / REQ-002）。

    与 ``extract`` 的差别：① 默认抽取**全部三类源**；② 绝不调用交互式 ``input()``；
    ③ 尊重 ``FSTDD_NO_SHARE`` / ``share.silent.enabled`` 总开关（置位即静默跳过）；
    ④ 产物一律 ``lifecycle=discovered``，绝不自动 promote / 外发。
    """
    from ..utils import read_config
    if _share_disabled():
        print("  auto-deposit skipped (FSTDD_NO_SHARE / share disabled)")
        return
    project_root = Path.cwd()
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        print("  No changes/ directory, skipping auto-deposit.")
        return

    sources = list(_EXTRACT_SOURCES)
    wanted = [_SOURCE_FILES[s] for s in sources]
    change_dir = _find_change_dir(changes_dir, wanted)
    if change_dir is None:
        print("  No source file found in current change, skipping auto-deposit.")
        return

    patterns = _dedup_patterns(_extract_sources(change_dir, sources))
    filtered = [p for p in patterns
                if p["severity"] in ("high", "critical", "medium") or p.get("occurrences", 1) >= 2]
    if not filtered:
        print("  No patterns to deposit.")
        return
    exp_dir_path = Path(exp_dir)
    exp_dir_path.mkdir(parents=True, exist_ok=True)
    config = read_config(project_root)
    proj_lang = config.get("project", {}).get("language", "python")
    count = _write_drafts(filtered, change_dir, exp_dir_path, proj_lang)
    print(f"  deposited {count} draft(s) (lifecycle=discovered, 待人工 promote)")


def _cmd_sync(args, exp_dir):
    """中心节点同步（C3 / REQ-003）：``--push`` / ``--pull`` / ``--dry-run`` / ``--secure``。

    传输与合并解耦：``--hub-dir`` 给定时走**本地目录适配器**（离线 / 测试 / 手工中转）；
    否则走**第一方传输**（push = ``tools/share_experience.py``；pull = scp hub ``fstdd-inbox``）。
    """
    from . import _exp_sync
    exp_dir_path = Path(exp_dir)
    action = getattr(args, "action", None)
    if action not in ("push", "pull"):
        action = "pull" if getattr(args, "pull", False) else "push"
    dry = bool(getattr(args, "dry_run", False))
    hub = getattr(args, "hub_dir", None)
    secure = bool(getattr(args, "secure", False))
    conflict_log = exp_dir_path.parent / "sync-conflicts.tsv"

    if action == "push":
        n = len(_exp_sync.load_entries(exp_dir_path))
        if dry:
            print(f"  dry-run: would push {n} entrie(s) to first-party hub (secure={secure})")
            return
        ok, reason = _exp_sync.push_bundle(exp_dir_path, hub_dir=hub, secure=secure)
        print(f"  {'pushed' if ok else 'push FAILED'}: {n} entrie(s) — {reason}")
        if not ok:
            sys.exit(1)
        return

    # pull
    if dry:
        print("  dry-run: would fetch from first-party hub and merge (no writes, no fetch)")
        return
    if hub:
        snapshot = Path(hub)
        temp_snapshot = None
    else:
        snapshot = Path(tempfile.mkdtemp(prefix="fstdd-sync-incoming-"))
        temp_snapshot = snapshot
        ok, reason = _exp_sync.fetch_bundle(snapshot, hub_dir=None)
        if not ok:
            _exp_sync.cleanup_dir(snapshot)
            print(f"  pull FAILED: {reason}")
            sys.exit(1)
    try:
        if secure:
            n = _exp_sync.decrypt_incoming(snapshot)
            print(f"  secure: decrypted {n} entrie(s)")
        stats = _exp_sync.sync_pull(exp_dir_path, snapshot, conflict_log_path=conflict_log)
    finally:
        if temp_snapshot is not None:
            _exp_sync.cleanup_dir(temp_snapshot)
    print(f"  pulled: +{stats['added']} new, ~{stats['updated']} updated, "
          f"={stats['kept']} kept, {len(stats['conflicts'])} conflict(s)")


def _parse_test_report(text):
    """Parse 12 failure mode check results from test-report.md."""
    patterns = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("|") and "|" in line[1:]:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                cat_raw = parts[0].lower().replace("`", "").replace("*", "").replace(" ", "_")
                status = parts[1].lower() if len(parts) > 1 else ""
                desc = parts[2] if len(parts) > 2 else ""
                matched_cat = None
                for vc in VALID_CATEGORIES:
                    if vc in cat_raw or cat_raw in vc:
                        matched_cat = vc
                        break
                if matched_cat and ("fail" in status or "no" in status or "warning" in status
                                    or status in ("x", "✗")):
                    severity = "high" if "fail" in status or status in ("x", "✗") else "medium"
                    patterns.append({
                        "category": matched_cat,
                        "pattern": desc[:120] if desc else f"{matched_cat} check failed",
                        "root_cause": "", "detection_trigger": matched_cat,
                        "fix_template": "", "occurrences": 1,
                        "severity": severity, "tags": [matched_cat],
                        "language": "python", "source_file": "",
                    })
    return patterns


def _parse_test_anomalies(text):
    """Parse test anomalies (flaky, timeout) from test-report."""
    anomalies = []
    for line in text.split("\n"):
        ll = line.lower()
        if "flaky" in ll and ("test" in ll or "fail" in ll):
            anomalies.append({
                "category": "runtime_deviation",
                "pattern": f"Flaky test: {line.strip()[:100]}",
                "root_cause": "Test instability detected",
                "detection_trigger": "flaky_test", "fix_template": "",
                "occurrences": 1, "severity": "medium",
                "tags": ["flaky_test"], "language": "python", "source_file": "",
            })
        if "timeout" in ll and ("test" in ll or "fail" in ll):
            anomalies.append({
                "category": "runtime_deviation",
                "pattern": f"Test timeout: {line.strip()[:100]}",
                "root_cause": "Test timeout detected",
                "detection_trigger": "timeout", "fix_template": "",
                "occurrences": 1, "severity": "medium",
                "tags": ["timeout"], "language": "python", "source_file": "",
            })
    return anomalies


def _cmd_review(args, exp_dir):
    """Interactive review of discovered experience drafts."""
    exp_dir_path = Path(exp_dir)
    if not exp_dir_path.exists():
        print("  Experience library is empty. Run 'fstdd experience extract' first.")
        return
    drafts = []
    for f in _iter_experience_files(exp_dir_path):
        fm = _load_experience(f)
        if fm and fm.get("lifecycle_state") == "discovered":
            drafts.append((f, fm))
    if not drafts:
        print("  No drafts pending review.")
        return
    print(f"\n  Found {len(drafts)} draft(s) for review:\n")
    shared = local = deleted = remaining = 0
    for idx, (filepath, fm) in enumerate(drafts, 1):
        cat_label = CATEGORY_LABELS.get(fm.get("category", ""), fm.get("category", ""))
        pattern = fm.get("pattern", "")[:80]
        severity = fm.get("severity", "medium")
        occurrences = fm.get("occurrences", 1)
        eid = fm.get("experience_id", filepath.stem)
        print(f"  {'-' * 60}")
        print(f"  [{idx}/{len(drafts)}] {eid}")
        print(f"  Category: {cat_label} | Severity: {severity} | Occurrences: {occurrences}")
        print(f"  Pattern: {pattern}")
        root_cause = fm.get("root_cause", "")
        if root_cause:
            print(f"  Root Cause: {root_cause[:100]}")
        print("  [S] Share+Deposit  [L] Local Only  [D] Skip  [A] All Share  [Q] Quit")
        try:
            choice = input("  > ").strip().upper() or "S"
        except (EOFError, KeyboardInterrupt):
            choice = "Q"
        if choice == "A":
            for fp2, fm2 in drafts[idx-1:]:
                _do_deposit(fp2, fm2)
                shared += 1
                _cmd_share_single(fm2.get("experience_id", fp2.stem), exp_dir_path)
            print(f"  -> All {len(drafts)-idx+1} remaining shared+deposited")
            break
        elif choice == "Q":
            remaining = len(drafts) - idx + 1
            print(f"  Quit. {remaining} draft(s) preserved for next review.")
            break
        elif choice == "D":
            filepath.unlink()
            deleted += 1
            print(f"  -> {eid}: Deleted")
        elif choice == "L":
            _do_deposit(filepath, fm)
            local += 1
            print(f"  -> {eid}: Deposited locally")
        else:
            _do_deposit(filepath, fm)
            shared += 1
            ok = _cmd_share_single(eid, exp_dir_path)
            if ok:
                print(f"  -> {eid}: Deposited + Shared")
            else:
                print(f"  -> {eid}: Deposited (share failed, retry later)")
    _load_index(exp_dir)
    print(f"\n  Review complete: {shared} shared, {local} local, {deleted} deleted, {remaining} preserved")


def _do_deposit(filepath, fm):
    """Advance lifecycle to deposited and update file."""
    fm["lifecycle_state"] = "deposited"
    fm["last_seen"] = datetime.now().strftime("%Y-%m-%d")
    body = filepath.read_text(encoding="utf-8").split("---", 2)
    body_content = body[2].strip() if len(body) >= 3 else ""
    fm_yaml = yaml.dump(fm, allow_unicode=True, default_flow_style=False)
    filepath.write_text(f"---\n{fm_yaml}---\n\n{body_content}", encoding="utf-8")


def _cmd_share(args, exp_dir):
    """One-click share experience to community (standalone CLI)."""
    eid = getattr(args, "experience_id", "")
    exp_dir_path = Path(exp_dir)
    ok = _cmd_share_single(eid, exp_dir_path)
    if not ok:
        sys.exit(1)


def _cmd_share_single(eid, exp_dir_path):
    """[已永久禁用] 本项目经验数据不外发到任何第三方社区或服务器。

    历史行为：把经验上传到上游社区仓库 leonai42/stdd-experiences（gh CLI 通道）
    或第三方服务器 hzddyy.com（API 通道）。两条外发代码路径均已永久移除。

    需要回传经验时，使用本项目自带的脚本（目标为自有仓库，且强制脱敏）：
        python tools/share_experience.py --export --publish
    """
    print("  [已永久禁用] FSTDD 经验不外发到第三方。")
    print("    历史上传通道（leonai42/stdd-experiences、hzddyy.com）的代码已移除。")
    print("    如需回传，使用本项目脚本（目标为自有仓库，强制脱敏）：")
    print("      python tools/share_experience.py --export --publish")
    return False




def _share_via_gh(eid, content):
    """[已永久移除] 原为通过 gh CLI 上传到上游社区仓库 leonai42/stdd-experiences。"""
    raise RuntimeError(
        "已永久禁用：FSTDD 经验不外发到第三方社区。"
        "如需回传请使用 tools/share_experience.py（目标为自有仓库）"
    )




def _share_via_api(eid, content):
    """[已永久移除] 原为 POST 到第三方服务器 https://hzddyy.com/stdd/api/share-experience。"""
    raise RuntimeError(
        "已永久禁用：FSTDD 经验不外发到第三方服务器。"
        "如需回传请使用 tools/share_experience.py（目标为自有仓库）"
    )




def _cmd_search(args, exp_dir):
    """Full-text search experience library."""
    keyword = getattr(args, "keyword", "")
    fmt = getattr(args, "format", "table")

    def _empty() -> None:
        """无命中时的统一出口：JSON 输出空数组（便于脚本消费），table 给出提示。"""
        if fmt == "json":
            import json
            print(json.dumps([], ensure_ascii=False, indent=2, default=_json_default))
        else:
            print(f"  No results for '{keyword}'")

    exp_dir_path = Path(exp_dir)
    if not _iter_experience_files(exp_dir_path):
        # 库为空时不得往 stdout 打人类可读文案，否则 --format json 无法解析
        print("  Experience library is empty.", file=sys.stderr)
        _empty()
        return
    cat_filter = getattr(args, "category", None)
    lang_filter = getattr(args, "language", None)
    sev_filter = getattr(args, "severity", None)
    fmt = getattr(args, "format", "table")
    results = []
    for filepath in _iter_experience_files(exp_dir_path):
        fm = _load_experience(filepath)
        if not fm:
            continue
        if cat_filter and fm.get("category") != cat_filter:
            continue
        if lang_filter and fm.get("language") != lang_filter:
            continue
        if sev_filter and fm.get("severity") != sev_filter:
            continue
        content = filepath.read_text(encoding="utf-8")
        body = content.split("---", 2)
        body = body[2].strip() if len(body) >= 3 else ""
        pattern = fm.get("pattern", "")
        root_cause = fm.get("root_cause", "")
        kw = keyword.lower()
        # tags 可能是列表，统一转成可检索字符串
        tags = fm.get("tags") or []
        tags_text = " ".join(tags) if isinstance(tags, (list, tuple)) else str(tags)
        score = 0.0
        if kw in pattern.lower():
            score += 3.0
        if kw in root_cause.lower():
            score += 2.0
        if kw in body.lower():
            score += 1.0
        # 类别 / 语言 / 标签也参与检索：用户常直接按类别名找经验
        if kw in str(fm.get("category", "")).lower():
            score += 2.0
        if kw in tags_text.lower():
            score += 2.0
        if kw in str(fm.get("language", "")).lower():
            score += 1.0
        if score > 0:
            score += fm.get("confidence", 0.5) * 0.5
            score += fm.get("adoption_count", 0) * 0.01
            results.append({"score": score, "eid": fm.get("experience_id", filepath.stem), "fm": fm})
    if not results:
        _empty()
        return
    results.sort(key=lambda x: x["score"], reverse=True)
    if fmt == "json":
        import json
        output = []
        for r in results:
            output.append({
                "experience_id": r["eid"], "category": r["fm"].get("category"),
                "pattern": r["fm"].get("pattern"), "severity": r["fm"].get("severity"),
                "language": r["fm"].get("language"),
                "lifecycle_state": r["fm"].get("lifecycle_state"),
                "relevance_score": round(r["score"], 3),
            })
        print(json.dumps(output, ensure_ascii=False, indent=2, default=_json_default))
    else:
        print(f"\n  Keyword '{keyword}' matched {len(results)} experience(s):\n")
        for r in results[:20]:
            fm = r["fm"]
            cat_label = CATEGORY_LABELS.get(fm.get("category", ""), fm.get("category", ""))
            print(f"  {r['eid']} [{cat_label}] (score: {r['score']:.1f})")
            print(f"    Pattern: {fm.get('pattern', '')[:100]}")
            root = fm.get("root_cause", "")
            if root:
                print(f"    Root Cause: {root[:100]}")
            print()
        if len(results) > 20:
            print(f"  ... {len(results)-20} more results, narrow your search.")


def cmd_experience(args: argparse.Namespace) -> None:
    from ..utils import get_logger
    get_logger()

    project_root = Path.cwd()
    exp_dir = _get_experiences_dir(project_root)

    subcommand = getattr(args, "subcommand", "list")

    # `--dry-run`：写子命令只预览、不落盘（list / stats / search 等读子命令不受影响）
    _WRITE_SUBCOMMANDS = {
        "add", "export", "pull", "verify", "deposit",
        "retire", "extract", "review", "share", "curate", "auto-deposit",
    }
    if subcommand in _WRITE_SUBCOMMANDS and dry_run_preview(args, f"experience {subcommand}"):
        return

    if subcommand == "list":
        _cmd_list(args, exp_dir)
    elif subcommand == "add":
        _cmd_add(args, exp_dir, project_root)
    elif subcommand == "stats":
        _cmd_stats(args, exp_dir)
    elif subcommand == "export":
        _cmd_export(args, exp_dir)
    elif subcommand == "pull":
        _cmd_pull(args, exp_dir)
    elif subcommand == "verify":
        _cmd_verify(args, exp_dir)
    elif subcommand == "deposit":
        _cmd_deposit(args, exp_dir)
    elif subcommand == "retire":
        _cmd_retire(args, exp_dir)
    elif subcommand == "extract":
        _cmd_extract(args, exp_dir)
    elif subcommand == "auto-deposit":
        _cmd_auto_deposit(args, exp_dir)
    elif subcommand == "sync":
        _cmd_sync(args, exp_dir)
    elif subcommand == "review":
        _cmd_review(args, exp_dir)
    elif subcommand == "share":
        _cmd_share(args, exp_dir)
    elif subcommand == "search":
        _cmd_search(args, exp_dir)
    elif subcommand == "curate":
        from .curate import cmd_curate
        cmd_curate(args)
    else:
        print(f" 未知子命令: {subcommand}")
        print(" 可用: list, add, stats, export, pull, verify, deposit, retire, extract, auto-deposit, sync, review, share, search, curate")
        sys.exit(1)
