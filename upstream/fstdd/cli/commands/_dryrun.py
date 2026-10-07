"""`--dry-run` 的统一预览守卫。

背景：`--dry-run` 在 `cli/__init__.py` 的父解析器中**全局注册**（help 声明
「预览操作，不实际修改文件系统」），对**所有**子命令可见；但实测 39 个命令模块中
**25 个含写操作**（共 149 个写点），其中 **15 个模块（78 个写点）完全没处理 `dry_run`**
—— 该参数被静默忽略后照常落盘。

（上述数字由 `tests/test_dry_run_fidelity.py` 的同口径扫描器实测，基线 `@0710d54`；
修正前的初稿曾写「28 个模块 / 16 个违规 / 110 个写点」，系口径未收紧所致的失真。）

本模块提供统一守卫，使「有写操作的命令」只需一行装饰器即可获得 dry-run 语义，
避免在 149 个写点逐点插桩（EXP-2026-0020：批量修补必须按「接收者/入口语义」收口，
而非按调用点散补）。

用法::

    from ._dryrun import dry_run_guard

    @dry_run_guard("canon generate")
    def cmd_canon_generate(args):
        ...

    # 「读为主 + 少量写」的命令：只守住写的那一处，读路径照常工作
    from ._dryrun import dry_run_requested

    if dry_run_requested(args):
        print("  [dry-run] 跳过 …（不修改文件系统）")
        return

`phase` 因需给出更具体的预览（`from → to`）而在模块内自行实现，不使用本装饰器。
"""

import functools

__all__ = ["dry_run_requested", "dry_run_preview", "dry_run_guard"]


def dry_run_requested(args) -> bool:
    """`--dry-run` 是否生效（兼容 `args` 为 None 的情形）。"""
    return bool(getattr(args, "dry_run", False))


def dry_run_preview(args, action: str, detail: str = "") -> bool:
    """若 `--dry-run`：打印预览并返回 True（调用方应据此 `return`）。

    否则返回 False（调用方继续正常执行）。
    """
    if not dry_run_requested(args):
        return False
    suffix = f"  {detail}" if detail else ""
    print(f"  [dry-run] {action}：预览模式，未修改文件系统。{suffix}".rstrip())
    return True


def dry_run_guard(action: str, detail_fn=None):
    """装饰器：`--dry-run` 时打印预览并**提前返回**，函数体不执行。

    :param action: 人类可读的动作名（如 ``"canon generate"``）
    :param detail_fn: 可选 ``callable(args) -> str``，用于给出更具体的预览信息
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ns = args[0] if args else kwargs.get("args")
            if not dry_run_requested(ns):
                return fn(*args, **kwargs)
            detail = ""
            if detail_fn is not None:
                try:
                    detail = detail_fn(ns) or ""
                except Exception:      # 预览信息只是锦上添花，不得因此阻断 dry-run
                    detail = ""
            dry_run_preview(ns, action, detail)
            return None

        return wrapper

    return decorator
