"""时间工具：UTC ISO 时间戳 + EOL 归一（与 tools/verify_eol.py 同口径）。

本模块是 `2026-09-17-time-baseline` 的基础设施：
- `utc_now_iso()`：所有 CLI 新产出时间字段的**唯一**来源（SC-010）。
- `normalize_eol()` / `content_hash()`：C8 的 DC-HASH 改为「EOL 归一后的内容哈希」，
  口径 = git `eol=lf` = 仅 CRLF→LF（与 tools/verify_eol.py:247 一致；孤立 CR 不动）。
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

# SC-010：带时区的 ISO 8601 后缀（+HH:MM / -HH:MM / Z）
_TZ_SUFFIX = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


def utc_now_iso(timespec: str = "seconds") -> str:
    """返回带时区的 UTC ISO 8601 字符串（如 2026-09-17T15:30:00+00:00）。

    禁止返回 naive 时间戳（无时区后缀）——那是本 change 要消灭的缺陷形态。
    """
    return datetime.now(timezone.utc).isoformat(timespec=timespec)


def has_tz(value: object) -> bool:
    """判断一个已序列化的时间字符串是否带时区后缀。"""
    if not isinstance(value, str):
        return False
    return bool(_TZ_SUFFIX.search(value.strip()))


def normalize_eol(data: bytes) -> bytes:
    """CRLF → LF。仅此一步，与 tools/verify_eol.py:247 和 git `eol=lf` 同口径。

    ⚠️ **孤立 CR 不归一**（Slice 2 实现审查修正，2026-09-17）：
    git 的 `text=auto`/`eol=lf` 转换只动 CRLF↔LF，**不动孤立 CR**。
    DC-HASH 必须与 git 同口径 —— 若把孤立 CR 也归一，两个「git 视角内容不同」
    的 blob（一个含孤立 CR、一个不含）会算出相同哈希，verify 在干净克隆上
    假绿，吞掉真实内容差异。
    """
    return data.replace(b"\r\n", b"\n")


def content_hash(data: bytes) -> str:
    """EOL 归一后的内容哈希（C8：DC-HASH 由字节哈希改为内容哈希）。

    只取前 16 个 hex 字符，与 canon.py 既有 DC-HASH 的格式一致。
    """
    return hashlib.sha256(normalize_eol(data)).hexdigest()[:16]
