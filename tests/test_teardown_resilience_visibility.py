"""TC-TTR-003 / TC-TTR-004 —— 韧性层可见性：告警含目标路径 + 会话汇总计数。

对应 spec: canonical/specs/code/test-teardown-resilience.yaml → SC-002（含 AND）

纪律出处：EXP-2026-0014（`except Exception: pass` 静默降级）+ KG-092（失败静默腐烂）
⇒ 捕获**必须可见、可计数**，不得只测「没崩」。
"""
import re
import warnings

import pytest

import conftest as cf

PREFIX = "[teardown-resilience]"


def _fire_once(tmp_path, name="victim.txt"):
    """触发一次捕获，返回被删目标路径。"""
    target = tmp_path / name
    target.write_text("x", encoding="utf-8")

    def _inner(_p):
        raise SystemExit(1)

    before = dict(cf.DELETE_GUARD_STATS)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cf._guarded_delete(_inner, target)
    return str(target), caught, before


def test_ttr_003_warning_contains_target_path(tmp_path):
    """TC-TTR-003 / SC-002：捕获产生 warning，且文本包含被捕获的删除目标路径。"""
    target_str, caught, _ = _fire_once(tmp_path)

    msgs = [str(w.message) for w in caught if PREFIX in str(w.message)]
    assert msgs, f"未产生含前缀 {PREFIX} 的告警：{[str(w.message) for w in caught]}"
    assert any(target_str in m for m in msgs), (
        f"告警未包含被捕获的目标路径 {target_str}：{msgs}"
    )


def test_ttr_004_session_counter_increments(tmp_path):
    """TC-TTR-004 / SC-002（AND）：计数随捕获次数递增，且**逐条**记录目标路径。

    ⚠️ 断言必须比对**内容**而非仅长度 —— 只比长度无法发现「记录了错的东西」。
    """
    a_str, _, before = _fire_once(tmp_path, "a.txt")
    b_str, _, mid = _fire_once(tmp_path, "b.txt")

    assert cf.DELETE_GUARD_STATS["captured"] == before["captured"] + 2, (
        f"计数未按捕获次数递增：{before} → {mid}"
    )
    assert cf.DELETE_GUARD_STATS["targets"][-2:] == [a_str, b_str], (
        f"记录的目标路径不符：{cf.DELETE_GUARD_STATS['targets'][-2:]} != {[a_str, b_str]}"
    )


def test_ttr_004b_selftest_isolation_is_wired(request):
    """TC-TTR-004 / SC-002（AND）：自测用例必须被「自测隔离」夹具覆盖。

    🔴 为什么要这条：本文件的 SystemExit 是**测试自己注入的桩**，不是守卫真的拦了删除。
    若不隔离，会话汇总会把它报成「守卫触发 N 次」⇒ 汇总**失真**、真信号被淹没。
    本用例守护该夹具的接线（`@pytest.fixture(autouse=True)` 被移除即失败）。
    """
    assert "_isolate_delete_guard_selftest" in request.fixturenames, (
        "自测隔离夹具未生效：会话汇总会把自测注入的捕获误报为守卫触发"
    )


# ---------- 会话汇总（D3 的可见性输出主体）----------
# ⚠️ 必须直接驱动 `pytest_sessionfinish`：因自测隔离生效，全量运行结束时 captured == 0
#    ⇒ 该函数在正常跑测时**提前返回、永不执行**（覆盖率实测：0）。若不补判据，
#    D3 的「汇总必须可见」这一核心交付物将**无任何测试保护**。

class _FakeReporter:
    def __init__(self):
        self.lines = []

    def write_line(self, text, **_kwargs):
        self.lines.append(text)


class _FakeSession:
    """最小 session 替身：只需 `config.pluginmanager.get_plugin("terminalreporter")`。"""

    def __init__(self, reporter):
        self.config = type("_Cfg", (), {
            "pluginmanager": type("_PM", (), {
                "get_plugin": staticmethod(
                    lambda name: reporter if name == "terminalreporter" else None
                ),
            })(),
        })()


class _capture_stats:
    """临时注入捕获并保证还原（与自测隔离夹具互为双保险）。"""

    def __enter__(self):
        self.captured = cf.DELETE_GUARD_STATS["captured"]
        self.targets = list(cf.DELETE_GUARD_STATS["targets"])
        return self

    def __exit__(self, *_exc):
        cf.DELETE_GUARD_STATS["captured"] = self.captured
        cf.DELETE_GUARD_STATS["targets"][:] = self.targets
        return False


def test_ttr_004c_summary_is_silent_without_captures():
    """TC-TTR-004 / SC-002：无捕获时**不得**输出汇总（避免噪声）。"""
    rep = _FakeReporter()
    with _capture_stats():
        cf.DELETE_GUARD_STATS["captured"] = 0
        cf.DELETE_GUARD_STATS["targets"].clear()
        cf.pytest_sessionfinish(_FakeSession(rep), 0)
    assert rep.lines == [], f"无捕获时不应输出任何汇总行：{rep.lines}"


def test_ttr_004c_summary_lists_targets():
    """TC-TTR-004 / SC-002：有捕获时必须输出「前缀 + 计数 + 目标路径」。"""
    rep = _FakeReporter()
    with _capture_stats():
        cf.DELETE_GUARD_STATS["captured"] = 2
        cf.DELETE_GUARD_STATS["targets"][:] = ["X:/demo/a.txt", "X:/demo/b.txt"]
        cf.pytest_sessionfinish(_FakeSession(rep), 0)

    joined = "\n".join(rep.lines)
    assert cf.DELETE_GUARD_PREFIX in joined, f"汇总缺固定前缀：{rep.lines}"
    assert "2" in joined, f"汇总缺捕获次数：{rep.lines}"
    assert "X:/demo/a.txt" in joined and "X:/demo/b.txt" in joined, (
        f"汇总未逐条列出目标路径：{rep.lines}"
    )


def test_ttr_004c_summary_marks_truncation():
    """TC-TTR-004 / SC-002（AND）：超过 20 条时须给出「其余 N 条省略」提示（不得静默截断）。"""
    rep = _FakeReporter()
    with _capture_stats():
        cf.DELETE_GUARD_STATS["captured"] = 23
        cf.DELETE_GUARD_STATS["targets"][:] = [f"X:/demo/t{i}.txt" for i in range(23)]
        cf.pytest_sessionfinish(_FakeSession(rep), 0)

    joined = "\n".join(rep.lines)
    assert "其余 3 条省略" in joined, f"截断未给出省略提示：{joined}"
    listed = [ln for ln in rep.lines if ln.strip().startswith("- ")]
    assert len(listed) == 20, f"应只列前 20 条，实得 {len(listed)}"


def test_ttr_004c_summary_falls_back_to_warning_without_reporter():
    """TC-TTR-004 / SC-002（AND）：取不到 terminalreporter 时须退化为 warning，不得静默丢弃。"""
    with _capture_stats():
        cf.DELETE_GUARD_STATS["captured"] = 1
        cf.DELETE_GUARD_STATS["targets"][:] = ["X:/demo/a.txt"]
        with pytest.warns(UserWarning, match=re.escape(cf.DELETE_GUARD_PREFIX)):
            cf.pytest_sessionfinish(_FakeSession(None), 0)
