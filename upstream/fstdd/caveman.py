"""FSTDD-Caveman — 跨节点传讯语体压缩器（独立库）。

设计约束（proposal 2026-10-03-caveman-kg-sync §caveman_compressor）:
  - 独立 Python 库：任何模块可直接 import，**禁止**依赖 multihub 客户端 (hub client) / canon（无循环 import）
  - ``compress`` 必须 deterministic（同输入 = 同输出），结果可用于 git diff
  - ``compress_dict`` 只保留 ``keep_keys``，值不变

公开 API::

    compress(text, max_chars=200) -> str
    compress_dict(d, keep_keys=None) -> dict
"""

from __future__ import annotations

import re

__all__ = ["compress", "compress_dict", "DEFAULT_MAX_CHARS", "DEFAULT_KEEP_KEYS", "FIELD_WEIGHTS"]

DEFAULT_MAX_CHARS = 200

# 字段权重表（weight 越大越该保留；max_chars=0 表示直接砍）
FIELD_WEIGHTS = {
    "summary": {"weight": 10, "max_chars": 60},
    "runner_cmd": {"weight": 8, "max_chars": 80},
    "deadline": {"weight": 7, "max_chars": 30},
    "constraints": {"weight": 5, "max_chars": 40},
    "scope": {"weight": 3, "max_chars": 20},
    "motivation": {"weight": 1, "max_chars": 0},  # 直接砍
}

# multihub 传讯必需字段（调用方可在 keep_keys 上 append）
DEFAULT_KEEP_KEYS = ["runner_cmd", "constraints", "deadline", "task_id", "idempotency_key"]

# output_contract 强制字段（做什么/怎么做/约束；deadline 为「如果有」）
_MANDATORY_FIELDS = ("summary", "runner_cmd", "constraints")

# 英文停用词
_EN_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
    "for", "with", "to", "of", "and", "or", "but",
})

# 中文修饰词：「XX的YY」→ 去掉 '的' 前后各最多 2 个汉字（proposal trim_rules）
_ZH_MODIFIER_RE = re.compile(r"[\u4e00-\u9fff]{0,2}的[\u4e00-\u9fff]{0,2}")

# 句子边界（中英标点 + 换行）
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。．.!?！？\n])")
_LONG_SENTENCE_LIMIT = 30
_LONG_SENTENCE_KEEP = 20

# 结构化字段行：``summary: xxx`` / ``- constraints：xxx``
_FIELD_RE = re.compile(
    r"^\s*[-*]\s*(summary|runner_cmd|deadline|constraints|scope|motivation)\s*[:：]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)

# motivation / why 段落标题关键词
_MOTIVATION_KEYS = ("why", "motivation", "rationale", "背景", "动机")

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_MAX_ZH_DROP = 2
_SEPARATOR = " | "


# ------------------------------------------------------------------
# trim_rules
# ------------------------------------------------------------------
def _remove_zh_modifiers(text: str) -> str:
    return _ZH_MODIFIER_RE.sub("", text)


def _remove_en_stopwords(text: str) -> str:
    def repl(m: "re.Match[str]") -> str:
        return "" if m.group(0).lower() in _EN_STOPWORDS else m.group(0)

    return re.sub(r"[A-Za-z]+", repl, text)


def _normalize_ws(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _collapse_repeats(text: str) -> str:
    """连续重复的整段短语（如 ``git pull git pull``）→ 保留一次。"""
    words = text.split()
    n = len(words)
    for size in range(1, n // 2 + 1):
        if n % size:
            continue
        block = words[:size]
        if all(words[i:i + size] == block for i in range(0, n, size)):
            return " ".join(block)
    return text


def _truncate_long_sentences(text: str) -> str:
    out = []
    for part in _SENTENCE_SPLIT_RE.split(text):
        core = part.rstrip("\n")
        tail = part[len(core):]
        if len(core) > _LONG_SENTENCE_LIMIT:
            core = core[:_LONG_SENTENCE_KEEP] + "…"
        out.append(core + tail)
    return "".join(out)


def _dedupe_lines(text: str) -> str:
    seen = set()
    out = []
    for line in text.splitlines():
        key = line.strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(line)
    return "\n".join(out)


def _apply_trim_rules(text: str) -> str:
    t = _remove_zh_modifiers(text)
    t = _remove_en_stopwords(t)
    t = _normalize_ws(t)
    t = _collapse_repeats(t)
    t = _truncate_long_sentences(t)
    t = _dedupe_lines(t)
    t = _normalize_ws(t)
    return t.strip()


# ------------------------------------------------------------------
# motivation 砍除
# ------------------------------------------------------------------
def _strip_motivation(text: str) -> str:
    out = []
    skip_level = None
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip().lower()
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if any(k in title for k in _MOTIVATION_KEYS):
                skip_level = level
                continue
            if skip_level is not None:
                continue
            out.append(line)
            continue
        if skip_level is not None:
            continue
        low = line.strip().lower()
        if any(low.startswith(k + ":") for k in ("why", "motivation", "rationale")):
            continue
        out.append(line)
    return "\n".join(out)


# ------------------------------------------------------------------
# 结构化字段路径
# ------------------------------------------------------------------
def _parse_fields(text: str) -> dict:
    fields: dict = {}
    for m in _FIELD_RE.finditer(text):
        key = m.group(1).lower()
        val = m.group(2).strip()
        fields[key] = f"{fields[key]}; {val}" if key in fields else val
    return fields


def _render(pieces: dict, keys) -> str:
    return _SEPARATOR.join(f"{k}:{pieces[k]}" for k in keys if pieces.get(k))


def _compress_fields(fields: dict, max_chars: int) -> str:
    # 1. motivation 直接砍
    fields = {k: v for k, v in fields.items() if k != "motivation"}

    # 2. 每字段先按自身 cap 裁剪
    trimmed = {}
    for k, v in fields.items():
        v = _apply_trim_rules(v)
        cap = FIELD_WEIGHTS.get(k, {}).get("max_chars", 40)
        trimmed[k] = v[:cap] if cap else ""

    # 3. 按 weight 降序渲染
    order = sorted(trimmed, key=lambda k: (-FIELD_WEIGHTS.get(k, {}).get("weight", 1), k))
    text = _render(trimmed, order)
    if len(text) <= max_chars:
        return text

    # 4. 预算不足 → 截断优先级倒转：mandatory（constraints 等）先入，再按 weight 填
    keep = set()
    mandatory = [k for k in _MANDATORY_FIELDS if trimmed.get(k)]
    budget = max_chars
    for k in mandatory:
        keep.add(k)
        budget -= len(_render(trimmed, [k])) + len(_SEPARATOR)
    for k in order:
        if k in keep:
            continue
        piece = _render(trimmed, [k])
        if len(piece) + len(_SEPARATOR) <= budget:
            keep.add(k)
            budget -= len(piece) + len(_SEPARATOR)

    text = _render(trimmed, [k for k in order if k in keep])
    if len(text) <= max_chars:
        return text
    # 仍超 → 保住 mandatory 的最小集
    return _render(trimmed, mandatory)[:max_chars]


# ------------------------------------------------------------------
# 公开 API
# ------------------------------------------------------------------
def compress(text, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """把长文本/Markdown 压缩为 ≤ ``max_chars`` 的精简版（deterministic）。"""
    if text is None:
        return ""
    if max_chars <= 0:
        return ""

    t = _strip_motivation(str(text))

    fields = _parse_fields(t)
    if len(fields) >= 2:
        return _compress_fields(fields, max_chars)

    t = _apply_trim_rules(t)
    if len(t) <= max_chars:
        return t
    return t[:max_chars]


def compress_dict(d, keep_keys=None) -> dict:
    """只保留 ``keep_keys`` 中的 key，值不变（默认 DEFAULT_KEEP_KEYS）。"""
    if not isinstance(d, dict):
        return {}
    keys = list(DEFAULT_KEEP_KEYS) if keep_keys is None else list(keep_keys)
    return {k: d[k] for k in keys if k in d}