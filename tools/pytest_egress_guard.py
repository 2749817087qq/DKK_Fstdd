# -*- coding: utf-8 -*-
"""pytest 会话级**出站守卫**：禁止测试经 ssh/scp/rsync 访问我方生产服务器。

⚠️ **覆盖面边界**：只拦子进程里的 ssh / scp / rsync 到 `PRODUCTION_HOSTS`。
   HTTP 出站（如 `FSTDD_INBOX_URL` 指向的生产端点，走 urllib/requests）**不在
   本守卫范围内** —— 那类测试必须自行覆写 `FSTDD_INBOX_URL` 到 loopback。

为什么需要
----------
2026-10-17/18 实测两起真实泄漏，且两次都是**测试全部通过**的情况下发生的
（断言无法感知，只能事后登服务器发现）：

  ① `tests/` 的 scp 桩未切断真实传输 ⇒ 生产 `/home/ubuntu/fstdd-inbox` 被建出
     20+ 个空批次目录（源码缺陷：Windows scp 不展开通配符）；
  ② `test_publish_stages_when_not_pre_staged` 的打点函数回调了**真实** `_scp_dir`
     ⇒ 把一个测试夹具批次（`EXP-SHT1.md`）真 scp 到了生产 fstdd-inbox。

为什么是一个独立模块而不是写在 conftest 里
------------------------------------------
仓库有**两个 pytest rootdir**：仓库根（`pyproject.toml`）与 `upstream/`
（`upstream/pyproject.toml`）。pytest 的 conftest 链从 rootdir 起算，因此：

    pytest upstream/tests/      → rootdir = upstream/  ⇒ 只加载 upstream/tests/conftest.py
    pytest tests/ upstream/tests/ → rootdir = 仓库根   ⇒ 两棵树的 conftest 都加载

守卫若只写在 `tests/conftest.py`，单跑 `pytest upstream/tests/` 时**根本不安装**
（2026-10-18 审计 F2，已用 `--trace-config` 实证）。把实现抽到本模块、由两侧
conftest 各自 `install()`，才能覆盖所有入口，且规则只有一份、不会漂移。

设计约束
--------
· **只拦 ssh/scp/rsync**，其余程序原样放行（git / python / bash 等不受影响）。
· 目标主机**精确匹配** `PRODUCTION_HOSTS`。不认 `ubuntu@` 这类用户名字面量 ——
  上游 `test_inbox_pull` 等用例刻意用 `ubuntu@<不可达域名>` 驱动失败分支，
  子串匹配会误伤（2026-10-18 首版误伤 3 例）。
· 命中即 `pytest.fail`，**不得静默吞掉**。静默「不打生产」同样是一种失败：
  它意味着用例在测试一个**没跑**的通道。
· 幂等：用函数属性做标记，两侧 conftest 各加载一个模块实例也不会重复包装。
"""

from __future__ import annotations

from pathlib import Path

import pytest

PREFIX = "[no-prod-egress]"

# 我方生产目标主机（**精确**匹配：SSH alias + 公网 IP）
PRODUCTION_HOSTS = frozenset({
    "fstdd-hub",
    "fstdd-hub-f",
    "43.134.236.80",
})

SSH_PROGRAMS = frozenset({"ssh", "scp", "rsync"})

# 统计挂在被包装的函数上（而非模块全局）：两侧 conftest 各有一份模块实例，
# 挂在函数上才能让两侧读到同一份计数。
_STATS_ATTR = "__egress_stats__"
_MARK_ATTR = "__egress_guard__"


def _empty_stats() -> dict:
    return {"blocked": 0, "commands": []}


def _normalize_args(args) -> list:
    """把各种 argv 形态归一成 list。

    2026-10-18 审计 D5-06/F-D1-3：旧实现 `args[0] if isinstance(args,(list,tuple))`
    在传字符串时取到的是**首字符**（`"ssh ..."` → `"s"`），`Path("s").name` 不在
    `SSH_PROGRAMS` 里 ⇒ 恒放行。仓库里确有 `shell=True` 字符串调用
    （`upstream/fstdd/cli/commands/agent.py:44`、`ci.py:699`）。
    """
    if isinstance(args, (list, tuple)):
        return list(args)
    if isinstance(args, bytes):
        args = args.decode("utf-8", "replace")
    if isinstance(args, str):
        import shlex
        try:
            return shlex.split(args, posix=True)
        except ValueError:
            return args.split()
    return [args]


def egress_targets(args) -> set[str]:
    """从 ssh/scp/rsync argv 提取候选目标主机集合（精确主机名）。

    三种形态：
      · `user@host`（含 `user@host:path`）→ 去 `user@`，再去 `:path`
      · `host:path`（scp/rsync 目标）     → 截掉 `:path`
      · 裸 host token                     → 原样

    跳过 `-` 开头选项与含 `/` 的本地路径（避免把 `/nonexistent/key` 误当主机）。
    选项值如 `ConnectTimeout=5`、`StrictHostKeyChecking=no` 会作为候选进入集合，
    但精确集合匹配不会命中，无害。
    """
    targets: set[str] = set()
    for tok in map(str, _normalize_args(args)):
        if "@" in tok:
            tok = tok.split("@", 1)[1]
        tok = tok.split(":", 1)[0].strip()
        if tok and not tok.startswith("-") and "/" not in tok:
            targets.add(tok)
    return targets


def _prog_name(args) -> str:
    """取程序名，并剥掉 Windows 的 `.exe` 后缀。

    审计 D5-06：`Path("C:/Windows/System32/OpenSSH/ssh.exe").name` = `ssh.exe`，
    旧实现直接比对 `SSH_PROGRAMS` ⇒ 不匹配、放行。
    """
    norm = _normalize_args(args)
    if not norm:
        return ""
    name = Path(str(norm[0])).name
    return name[:-4] if name.lower().endswith(".exe") else name


def is_production_egress(args) -> bool:
    """判断一条命令是否指向我方生产服务器。

    程序名须为 ssh/scp/rsync（`.exe` 后缀已剥），且目标主机**精确命中**
    `PRODUCTION_HOSTS`。
    """
    if _prog_name(args) not in SSH_PROGRAMS:
        return False
    return bool(egress_targets(args) & PRODUCTION_HOSTS)


def install() -> None:
    """安装守卫（幂等，可被多个 conftest 重复调用）。

    打点选在 **`subprocess.run` 与 `subprocess.call`**：
      · `check_output` 内部调 `run`，`check_call` 内部调 `call` ⇒ 二者自动覆盖；
      · 两者都接受 list 与 `shell=True` 字符串 argv，`_normalize_args` 统一归一。

    ⚠️ **已知缺口**：直接 `subprocess.Popen(...)` 不被拦截。
    不能把 `Popen` 换成函数 —— `asyncio.windows_utils` 会 `class Popen(subprocess.Popen)`
    在 import 期继承它，函数不可被继承（实测 `TypeError: function() argument
    'code' must be code, not str`，整个 asyncio 无法加载）。这是取舍，不是遗漏。
    """
    import subprocess

    if getattr(subprocess.run, _MARK_ATTR, False):
        return  # 已安装

    stats = _empty_stats()

    def _wrap(original):
        def _guarded(args, *args_tail, **kwargs):
            if is_production_egress(args):
                stats["blocked"] += 1
                cmd = " ".join(str(a) for a in _normalize_args(args))
                stats["commands"].append(cmd[:160])
                pytest.fail(
                    f"{PREFIX} 测试试图访问生产服务器：{stats['commands'][-1]} —— "
                    "请改用 monkeypatch 打桩"
                    "（见 tests/test_share_ssh_transport.py::_fake_run）"
                )
            return original(args, *args_tail, **kwargs)
        return _guarded

    guarded_run = _wrap(subprocess.run)
    guarded_run.__name__ = "_guarded_run"
    setattr(guarded_run, _MARK_ATTR, True)
    setattr(guarded_run, _STATS_ATTR, stats)
    subprocess.run = guarded_run

    if hasattr(subprocess, "call"):
        guarded_call = _wrap(subprocess.call)
        guarded_call.__name__ = "_guarded_call"
        subprocess.call = guarded_call


def _anchor():
    """返回承载标记与统计的对象（run；未安装时是原实现）。"""
    import subprocess

    return subprocess.run


def stats() -> dict:
    """读取当前守卫的计数（未安装时返回空计数）。"""
    return getattr(_anchor(), _STATS_ATTR, _empty_stats())


def is_installed() -> bool:
    return bool(getattr(_anchor(), _MARK_ATTR, False))


def summary() -> str:
    """会话级汇总行（固定前缀 + 拦截次数）。"""
    return f"{PREFIX} 会话共拦截 {stats()['blocked']} 次生产出站"


def flush(session) -> None:
    """把拦截记录刷到会话日志（可见性）。

    守卫命中时已在测试体内 `pytest.fail`，用例本身已红；这里是**汇总可见性**，
    不额外影响退出码 —— 与删除守卫同一契约。
    """
    st = stats()
    if not st["blocked"]:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    reporter.write_line("")
    reporter.write_line(summary(), red=True)
    for cmd in st["commands"][:10]:
        reporter.write_line(f"  - {cmd}", red=True)
    omitted = max(0, len(st["commands"]) - 10)
    if omitted:
        reporter.write_line(f"  … 其余 {omitted} 条省略")
