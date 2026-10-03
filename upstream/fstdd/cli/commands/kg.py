"""V3.1.1: `fstdd kg sync` — 知识图谱自动同步器 CLI 子命令。"""

from ...kg_sync import _dispatch as _kg_dispatch


def cmd_kg(args) -> int:
    """转调 ``fstdd.kg_sync`` 的同步引擎（扫描源码 → re-index 知识图谱）。"""
    _kg_dispatch(args)
    return 0


def _dispatch(args) -> int:
    return cmd_kg(args)