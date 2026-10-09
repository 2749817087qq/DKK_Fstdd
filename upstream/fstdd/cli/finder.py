from pathlib import Path
from typing import Optional
import sys


def _resolve_in(base_dir: Path, name: str) -> Optional[Path]:
    """在给定目录内解析 change：先精确名，再后缀匹配（按名倒序取首个）。

    候选目录必须含 ``.fstdd.yaml`` 才算 change —— 与既有判定保持一致。

    ⚠️ ``name`` 必须是**单个目录名**：含路径分隔符或 ``..`` 一律拒绝（返回 None）。
    否则 ``base_dir / name`` 会被 ``..`` 逃逸出 base_dir —— 实测 ``changes/../../.fstdd/archive/x``
    这类输入能解析到归档区，使「归档拒绝写」的判定失效（失败模式 #10 路径遍历）。
    """
    if not name or name in (".", ".."):
        return None
    if "/" in name or "\\" in name or ".." in Path(name).parts:
        return None
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


#: 归档态拒绝写操作的统一文案（2026-10-07 / change-dir-resolution REQ-002 SC-105）。
#: 三要素：①「已归档」状态词 ② 归档实际路径 ③ `rollback` 出口指引。
ARCHIVED_REJECT_TEMPLATE = "  已归档：{name}（{archive_path}）；如需修改请先 fstdd rollback {name}"


def require_active_change_dir(name: Optional[str] = None,
                             project_root: Optional[Path] = None) -> Path:
    """**写路径专用**：要求 change 处于在办（active）状态。

    - 命中 ``changes/`` ⇒ 返回其 ``Path``（调用方继续执行）；
    - 命中 ``archive/`` ⇒ 打印准确拒绝文案（「已归档」+ 归档实际路径 + ``rollback`` 指引）
      并 ``sys.exit(1)``；
    - 都未命中 ⇒ 打印「找不到」并 ``sys.exit(1)``。

    ⚠️ 这是**唯一**的「什么算可写」定义点 —— 不要在命令模块里各写一遍
    （EXP-2026-0020：批量收口必须按「入口语义」做，而非按调用点散补）。

    ⚠️ 与 :func:`find_change_dir` 的分工：后者是**纯解析**（无副作用、返回值可断言），
    本函数带 ``print + sys.exit`` 副作用，故**不得**被读路径调用。

    ⚠️ ``name`` 为空时语义仍是「最近的在办 change」（与 ``find_change_dir`` 一致），
    归档区永远不参与「当前 change」的判定。
    """
    if project_root is None:
        project_root = Path.cwd()

    hit = find_change_dir(name, project_root, include_archive=True)
    if hit is None:
        print(f"  找不到 change: {name or '(未指定)'}")
        sys.exit(1)

    archive_root = project_root / ".fstdd" / "archive"
    # ⚠️ 必须**归一化后**再比：词法前缀比较会被 `..` 绕过（失败模式 #10）。
    # 双保险：`_resolve_in` 已拒绝含分隔符/`..` 的名字，此处再按真实路径判一次。
    try:
        hit.resolve().relative_to(archive_root.resolve())
    except ValueError:
        return hit  # 位于 changes/ 下 ⇒ 在办，放行

    # 归档态：拒绝写操作，并给出可操作出口
    print(ARCHIVED_REJECT_TEMPLATE.format(
        name=hit.name,
        archive_path=(Path(".fstdd") / "archive" / hit.name).as_posix(),
    ))
    sys.exit(1)
