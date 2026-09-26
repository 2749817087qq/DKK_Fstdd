from pathlib import Path
from typing import Optional


def _resolve_in(base_dir: Path, name: str) -> Optional[Path]:
    """在给定目录内解析 change：先精确名，再后缀匹配（按名倒序取首个）。

    候选目录必须含 ``.fstdd.yaml`` 才算 change —— 与既有判定保持一致。
    """
    if not base_dir.exists():
        return None
    exact = base_dir / name
    if exact.exists() and exact.is_dir() and (exact / ".fstdd.yaml").exists():
        return exact
    for d in sorted(base_dir.iterdir(), reverse=True):
        if d.is_dir() and d.name.endswith(name) and (d / ".fstdd.yaml").exists():
            from .utils import get_logger
            get_logger().info("📋 匹配到 change: %s", d.name)
            return d
    return None


def find_change_dir(name: Optional[str] = None, project_root: Optional[Path] = None,
                    *, include_archive: bool = False) -> Optional[Path]:
    """解析 change 目录（统一入口）。

    解析顺序（``name`` 非空时）::

        changes/<name>   →  changes/*<name>
        ── include_archive=True 时继续 ──
        archive/<name>   →  archive/*<name>
        → None

    ``include_archive`` 默认 ``False``：既有调用点（archive / abort）语义逐字不变，
    且避免 ``stdd archive`` 解析到 archive/ 后**把自己再移动一次**。

    ``name`` 为空时**恒**只取 ``changes/`` 内最近修改者（与 ``include_archive`` 无关）：
    「当前 change」语义上不可能位于归档区（归档即终态）。
    """
    if project_root is None:
        project_root = Path.cwd()
    changes_dir = project_root / ".fstdd" / "changes"

    if name:
        hit = _resolve_in(changes_dir, name)
        if hit is not None:
            return hit
        if include_archive:
            return _resolve_in(project_root / ".fstdd" / "archive", name)
        return None
    else:
        if not changes_dir.exists():
            return None
        changes = [d for d in changes_dir.iterdir() if d.is_dir() and (d / ".fstdd.yaml").exists()]
        if not changes:
            return None
        return sorted(changes, key=lambda d: d.stat().st_mtime, reverse=True)[0]
