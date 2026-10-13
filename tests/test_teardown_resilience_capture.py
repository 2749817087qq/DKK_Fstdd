"""TC-TTR-001 / TC-TTR-002 —— 韧性层：捕获 SystemExit 且不中断收尾链。

对应 spec: canonical/specs/code/test-teardown-resilience.yaml → SC-001（含 AND）

设计要点（design.md D2）：
- 被测对象是 `tests/conftest.py` 暴露的**纯包装函数** `_guarded_delete(inner, target)`；
- 并**端到端**验证安装确实覆盖全部删除入口 —— 判据**不依赖环境是否恰好触发沙箱守卫**。

🔴 为什么必须逐入口核对（本 change 的 blocker）：
   shim（sitecustomize.py:1281）会**直接替换** `pathlib.Path.unlink` 为 `_safe_path_unlink`，
   而后者在**非 bypass 分支**直接 `_try_trash()`（:1237），**不经过 `os.unlink`**。
   ⇒ 只包装 `os.*` 会漏掉根因①（仓库内路径走的正是这一支）。
"""
import os
import pathlib
import re
import shutil

import pytest

import conftest as cf

_PREFIX_RE = re.escape(cf.DELETE_GUARD_PREFIX)

# 必须被包装的删除入口（键 = conftest 里的 `__wrapped_key__`）
_DELETE_SURFACES = {
    "os.remove": lambda: os.remove,
    "os.unlink": lambda: os.unlink,
    "os.rmdir": lambda: os.rmdir,
    "shutil.rmtree": lambda: shutil.rmtree,
    "pathlib.Path.unlink": lambda: pathlib.Path.unlink,
    "pathlib.Path.rmdir": lambda: pathlib.Path.rmdir,
}


def _raiser(_target, *args, **kwargs):
    """模拟沙箱守卫：删除时 raise SystemExit。"""
    raise SystemExit(1)


# ---------- 结构性：安装确实覆盖全部删除入口 ----------

def test_ttr_001_all_delete_surfaces_are_wrapped():
    """TC-TTR-001 / SC-001：**每一个**删除入口都必须被韧性层包装。

    这是对 blocker 的判别性判据 —— 少包 `pathlib.Path.unlink` 即失败。
    """
    missing = [
        key for key, getter in _DELETE_SURFACES.items()
        if getattr(getter(), "__wrapped_key__", None) != key
    ]
    assert not missing, (
        f"以下删除入口未被韧性层包装（根因①② 会漏）：{missing}"
    )


def test_ttr_001_originals_are_preserved():
    """TC-TTR-001：包装必须保留原实现（可回退），且不得丢失元信息。"""
    for key in _DELETE_SURFACES:
        assert key in cf._DELETE_GUARD_ORIGINALS, f"未保存 {key} 的原实现"
        assert callable(cf._DELETE_GUARD_ORIGINALS[key]), f"{key} 的原实现不可调用"
    # 元信息保留：__name__ 必须来自被包装的原实现，而不是通用包装名 "_wrapper"。
    # （注：本机 shim 已把 os.remove 换成 _safe_remove，故 __name__ 为 "_safe_remove"
    #   才是**如实**的 —— 断言不能钉死 "remove"。）
    for key, getter in _DELETE_SURFACES.items():
        fn = getter()
        assert fn.__wrapped_key__ == key
        assert fn.__name__ != "_wrapper", (
            f"{key} 元信息丢失：__name__ 仍是通用包装名 '_wrapper'"
        )
        assert fn.__name__ == getattr(cf._DELETE_GUARD_ORIGINALS[key], "__name__", None), (
            f"{key} 的 __name__ 未如实沿用原实现"
        )


# ---------- 单元级：纯函数语义 ----------

def test_ttr_001_guarded_delete_swallows_systemexit(tmp_path):
    """TC-TTR-001 / SC-001：被包装的删除原语遇 SystemExit 时降级为告警且不向上抛。"""
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")

    with pytest.warns(UserWarning, match=_PREFIX_RE):   # 降级必须可见（见 TC-TTR-003）
        result = cf._guarded_delete(_raiser, target)

    assert result is None, "捕获后应正常返回（不向上抛 SystemExit）"


def test_ttr_001_guarded_delete_passthrough(tmp_path):
    """TC-TTR-001（对照）：未触发守卫时，包装层**不得改变**原语语义。"""
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")

    result = cf._guarded_delete(os.remove, target)

    assert result is None
    assert not target.exists(), "包装层不得吞掉正常删除的效果"


# ---------- 端到端：真实删除入口确实经由包装层 ----------

def test_ttr_001_e2e_path_unlink_repo_internal(monkeypatch):
    """TC-TTR-001 / SC-001：**非 bypass 路径（仓库内）**的 `Path.unlink()` 必须经由包装层。

    这是根因①的**真实失败路径**（shim 的 `_safe_path_unlink` 非 bypass 分支不经过 `os.unlink`）。
    目标文件**不实际创建** —— 若包装缺失，原生 `unlink` 会抛 `FileNotFoundError`，
    判据随之失败；若包装存在，`_raiser` 先于一切文件操作抛 SystemExit 并被捕获。
    故本用例**既具判别性、又不改动仓库**。
    """
    probe = pathlib.Path(__file__).resolve().parent / ".ttr-probe-never-created.tmp"
    monkeypatch.setitem(cf._DELETE_GUARD_ORIGINALS, "pathlib.Path.unlink", _raiser)

    before = cf.DELETE_GUARD_STATS["captured"]
    with pytest.warns(UserWarning, match=_PREFIX_RE):
        probe.unlink()                        # 未包装 ⇒ FileNotFoundError（判据失败）

    assert cf.DELETE_GUARD_STATS["captured"] == before + 1
    assert not probe.exists(), "探针文件不应被创建"


def test_ttr_001_e2e_path_rmdir_repo_internal(monkeypatch):
    """TC-TTR-001 / SC-001：`Path.rmdir()` 同样必须经由包装层。"""
    probe = pathlib.Path(__file__).resolve().parent / ".ttr-probe-never-created-dir"
    monkeypatch.setitem(cf._DELETE_GUARD_ORIGINALS, "pathlib.Path.rmdir", _raiser)

    before = cf.DELETE_GUARD_STATS["captured"]
    with pytest.warns(UserWarning, match=_PREFIX_RE):
        probe.rmdir()

    assert cf.DELETE_GUARD_STATS["captured"] == before + 1


def test_ttr_001_e2e_os_remove_routes_through_guard(tmp_path, monkeypatch):
    """TC-TTR-001 / SC-001：真实 `os.remove()` 必须经由包装层（框架根因②的同一入口）。"""
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")
    monkeypatch.setitem(cf._DELETE_GUARD_ORIGINALS, "os.remove", _raiser)

    before = cf.DELETE_GUARD_STATS["captured"]
    with pytest.warns(UserWarning, match=_PREFIX_RE):
        os.remove(target)

    assert cf.DELETE_GUARD_STATS["captured"] == before + 1


def test_ttr_001_e2e_rmtree_routes_through_guard(tmp_path, monkeypatch):
    """TC-TTR-001 / SC-001：真实 `shutil.rmtree()` 必须经由包装层。"""
    victim = tmp_path / "tree"
    victim.mkdir()
    monkeypatch.setitem(cf._DELETE_GUARD_ORIGINALS, "shutil.rmtree", _raiser)

    before = cf.DELETE_GUARD_STATS["captured"]
    with pytest.warns(UserWarning, match=_PREFIX_RE):
        shutil.rmtree(victim)

    assert cf.DELETE_GUARD_STATS["captured"] == before + 1


def test_ttr_001_e2e_path_unlink_tmp_path(monkeypatch, tmp_path):
    """TC-TTR-001（bypass 路径对照）：系统临时区内的 `Path.unlink()` 同样经由包装层。

    ⚠️ 本用例**不**能证明根因①被覆盖 —— tmp 路径走 shim 的 bypass 分支，
    即使未包装 `pathlib.Path.unlink` 也可能经由被包装的 `os.unlink` 通过。
    根因①的判别性判据见 `test_ttr_001_e2e_path_unlink_repo_internal` 与
    `test_ttr_001_all_delete_surfaces_are_wrapped`。
    """
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")
    monkeypatch.setitem(cf._DELETE_GUARD_ORIGINALS, "os.unlink", _raiser)

    before = cf.DELETE_GUARD_STATS["captured"]
    with pytest.warns(UserWarning, match=_PREFIX_RE):
        target.unlink()

    assert cf.DELETE_GUARD_STATS["captured"] == before + 1


# ---------- 收尾链不被中断 ----------

def test_ttr_002_teardown_chain_not_interrupted(tmp_path, monkeypatch):
    """TC-TTR-002 / SC-001（AND）：第 1 步删除抛 SystemExit 时，第 2 步收尾仍须执行。"""
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")
    marker = tmp_path / "step2.done"
    monkeypatch.setitem(cf._DELETE_GUARD_ORIGINALS, "os.unlink", _raiser)

    with pytest.warns(UserWarning, match=_PREFIX_RE):
        target.unlink()                       # step 1：被守卫中断
        marker.write_text("ok", encoding="utf-8")   # step 2：必须仍被执行

    assert marker.exists(), "收尾链被中断：第 2 步未执行"
