"""V3.1.1: `fstdd caveman` — 跨节点传讯语体压缩器 CLI 子命令。"""

import sys
from pathlib import Path

from ...caveman import DEFAULT_MAX_CHARS, compress


def cmd_caveman(args) -> int:
    """压缩 ``args.source`` 指向的文件（``-`` 表示 stdin）并输出精简版。"""
    if args.source == "-":
        text = sys.stdin.read()
    else:
        src = Path(args.source)
        if not src.exists():
            print(f"  caveman: file not found: {args.source}", file=sys.stderr)
            sys.exit(1)
        text = src.read_text(encoding="utf-8")

    out = compress(text, max_chars=args.max)

    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"  caveman → {args.out} ({len(out)} chars)")
    else:
        print(out)
    return 0


def _dispatch(args) -> int:
    return cmd_caveman(args)