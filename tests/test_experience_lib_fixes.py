"""FSTDD EXP-0062 / EXP-0055 / EXP-0067 修复验证测试。

Change: 2026-10-26-experience-lib-triage
Task:   code（v3.4.0 增量修复）

覆盖三个已实现的修复：
  - EXP-2026-0062: 关键写入点 fsync 原子落盘（data-integrity）
  - EXP-2026-0055: 知识图谱 edges 幂等去重（data-integrity）
  - EXP-2026-0067: ci check-failures 的 TC planned 只按定义点提取（tooling）

每项包含 3 类用例：正常路径 / 边界 / 回归断言。
"""

import os
import sys
import textwrap
import importlib
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


# ─── 定位 upstream 包 ───────────────────────────────────────────────

# 测试文件位于 tests/，仓库根为父目录；upstream/ 是 FSTDD 包源码位置。
# editable install 已把 fstdd 指向 stdd-repo/upstream，import 直接可用。
_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests → stdd-repo/
_UPSTREAM = _REPO_ROOT / "upstream"
if str(_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM))


# ─── EXP-2026-0062: fsync 原子落盘 ──────────────────────────────────

class TestFsyncAtomicWrite:
    """EXP-2026-0062：_save_index / _save_graph 必须 fsync 文件 + 目录。"""

    def test_save_index_calls_fsync(self, tmp_path, monkeypatch):  # TC-ELT-001
        """[正常路径] TC-ELT-001：_save_index 落盘后必须 fsync 文件本体（保证断电一致性）。

        注：目录 fsync 在 Windows 上因 os.open(dir) 抛 PermissionError 会静默降级，
        本用例只断言文件 fsync 至少 1 次。
        """
        from fstdd.cli.commands.experience import _save_index, _get_index_path

        fsync_calls = []

        def fake_fsync(fd):
            fsync_calls.append(fd)

        with patch("os.fsync", side_effect=fake_fsync):
            _save_index(tmp_path, {"last_id": 1, "total": 0})

        # 文件 fsync 必须至少 1 次
        assert len(fsync_calls) >= 1, (
            f"_save_index 应至少 fsync 文件本体，实际 fsync 次数: {len(fsync_calls)}"
        )
        # 索引文件已生成
        idx = _get_index_path(tmp_path)
        assert idx.exists()
        # 内容合法
        loaded = yaml.safe_load(idx.read_text(encoding="utf-8"))
        assert loaded["last_id"] == 1
        assert loaded["total"] == 0

    def test_save_index_atomic_replace_used(self, tmp_path, monkeypatch):  # TC-ELT-002
        """[边界] TC-ELT-002：_save_index 必须走 os.replace 原子替换，不留 .tmp 残留。"""
        from fstdd.cli.commands.experience import _save_index, _get_index_path

        replace_called = []
        original_replace = os.replace

        def spy_replace(src, dst):
            replace_called.append((src, dst))
            return original_replace(src, dst)

        with patch("os.replace", side_effect=spy_replace):
            _save_index(tmp_path, {"last_id": 2, "total": 1})

        assert replace_called, "_save_index 未使用 os.replace 原子替换"
        # 替换后 .tmp 文件必须已清理
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert not tmp_files, f"残留 .tmp 文件: {[str(t) for t in tmp_files]}"

    def test_save_graph_calls_fsync(self, tmp_path):  # TC-ELT-003
        """[回归] _save_graph 必须 fsync 文件本体保证断电一致性。

        注：目录 fsync 在 Windows 上不支持（os.open(dir) 抛 PermissionError），
        静默降级 —— 本用例只断言文件 fsync 至少 1 次。
        """
        from fstdd.cli.commands.knowledge import _save_graph

        graph_path = tmp_path / "knowledge-graph.yaml"
        graph = {
            "graph_version": "1.0",
            "nodes": [{"id": "KG-001", "title": "t"}],
            "edges": [{"from": "KG-001", "to": "KG-002", "type": "co-occurrence"}],
        }

        fsync_calls = []

        with patch("os.fsync", side_effect=lambda fd: fsync_calls.append(fd)):
            _save_graph(graph_path, graph)

        assert len(fsync_calls) >= 1, (
            f"_save_graph 应 fsync 文件本体，实际: {len(fsync_calls)}"
        )
        assert graph_path.exists()

    def test_atomic_write_text_helper(self, tmp_path):  # TC-ELT-004
        """[回归] 新增的 _atomic_write_text helper 走 tmp+fsync+replace。"""
        from fstdd.cli.commands.experience import _atomic_write_text

        target = tmp_path / "sub" / "out.md"  # 不存在父目录
        content = "---\nfoo: bar\n---\n\n正文\n"
        _atomic_write_text(target, content)
        assert target.exists()
        assert target.read_text(encoding="utf-8") == content


# ─── EXP-2026-0055: edges 幂等去重 ──────────────────────────────────

class TestEdgeDedupe:
    """EXP-2026-0055：edges 去重，无向边视为同一条，保留 last_synced_at 最新。"""

    def test_dedupe_drops_duplicates(self):  # TC-ELT-005
        """[正常路径] 相同 (A,B) 边保留 last_synced_at 最新的一条。"""
        from fstdd.cli.commands.knowledge import _dedupe_edges

        edges = [
            {"from": "KG-001", "to": "KG-002", "type": "co-occurrence", "last_synced_at": "2026-10-20T00:00:00Z"},
            {"from": "KG-001", "to": "KG-002", "type": "co-occurrence", "last_synced_at": "2026-10-25T00:00:00Z"},
            {"from": "KG-001", "to": "KG-002", "type": "co-occurrence", "last_synced_at": "2026-10-22T00:00:00Z"},
        ]
        result = _dedupe_edges(edges)
        assert len(result) == 1
        assert result[0]["last_synced_at"] == "2026-10-25T00:00:00Z"

    def test_dedupe_undirected(self):  # TC-ELT-006
        """[边界] (A,B) 与 (B,A) 视为同一条边（无向）。"""
        from fstdd.cli.commands.knowledge import _dedupe_edges

        edges = [
            {"from": "KG-001", "to": "KG-002", "type": "co-occurrence", "last_synced_at": "2026-10-20T00:00:00Z"},
            {"from": "KG-002", "to": "KG-001", "type": "co-occurrence", "last_synced_at": "2026-10-23T00:00:00Z"},
        ]
        result = _dedupe_edges(edges)
        assert len(result) == 1
        assert result[0]["last_synced_at"] == "2026-10-23T00:00:00Z"

    def test_dedupe_ignores_self_loops(self):  # TC-ELT-007
        """[边界] 自环（A→A）与空 from/to 边被丢弃。"""
        from fstdd.cli.commands.knowledge import _dedupe_edges

        edges = [
            {"from": "KG-001", "to": "KG-001"},
            {"from": "", "to": "KG-002"},
            {"from": "KG-003", "to": ""},
            {"from": "KG-004", "to": "KG-005", "type": "co-occurrence", "last_synced_at": "2026-10-26T00:00:00Z"},
        ]
        result = _dedupe_edges(edges)
        assert len(result) == 1
        assert result[0]["from"] == "KG-004"

    def test_save_graph_dedupes_on_write(self, tmp_path):  # TC-ELT-008
        """[回归] _save_graph 落盘前统一去重 edges。"""
        from fstdd.cli.commands.knowledge import _save_graph

        graph_path = tmp_path / "kg.yaml"
        graph = {
            "graph_version": "1.0",
            "nodes": [],
            "edges": [
                {"from": "KG-001", "to": "KG-002", "type": "co-occurrence", "last_synced_at": "2026-10-01T00:00:00Z"},
                {"from": "KG-001", "to": "KG-002", "type": "co-occurrence", "last_synced_at": "2026-10-20T00:00:00Z"},
                {"from": "KG-002", "to": "KG-001", "type": "co-occurrence", "last_synced_at": "2026-10-15T00:00:00Z"},
            ],
        }
        _save_graph(graph_path, graph)
        loaded = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
        # 3 条边去重后只剩 1 条（A↔B 同一条）
        assert len(loaded["edges"]) == 1


# ─── EXP-2026-0067: TC 定义点优先 ───────────────────────────────────

class TestTcidDefinitionPoints:
    """EXP-2026-0067：planned TC 只按定义点提取，引用不算。"""

    def test_extract_form_a_definitions(self):  # TC-ELT-009
        """[正常路径] 形态 A（`| **ID** | TC-… |`）为最高优先级。"""
        from fstdd.cli.commands.ci import _tcid_definition_points

        content = textwrap.dedent("""
            ## TC 定义表

            | **ID** | 描述 |
            | --- | --- |
            | **ID** | TC-FIX-001 |
            | **ID** | TC-FIX-002 |

            参考 TC-OTHER-999（不属于本 change）。
        """)
        ids = _tcid_definition_points(content)
        assert set(ids) == {"TC-FIX-001", "TC-FIX-002"}
        assert "TC-OTHER-999" not in ids

    def test_extract_returns_empty_when_no_tables(self):  # TC-ELT-010
        """[边界] 无标准表格定义行时 _tcid_definition_points 返回空（由调用方 fallback）。

        语义：定义点 API 只返回表格式的 TC-ID 定义，裸文本列表不算定义点。
        check_tc_implementation_coverage 会自行 fallback 到全文扫描（旧格式兼容）。
        """
        from fstdd.cli.commands.ci import _tcid_definition_points

        content = textwrap.dedent("""
            测试用例列表（裸文本，无表格）：
            - TC-OLD-001: 场景描述
            - TC-OLD-002: 场景描述
        """)
        ids = _tcid_definition_points(content)
        # 裸文本列表不属于"定义点"，返回空
        assert ids == [], f"裸文本列表不应视为定义点，实际: {ids}"

    def test_check_coverage_excludes_references(self, tmp_path, monkeypatch):  # TC-ELT-011
        """[回归] check_tc_implementation_coverage 不把引用 TC 算入 planned。"""
        from fstdd.cli.commands.ci import check_tc_implementation_coverage

        change_dir = tmp_path / "change"
        change_dir.mkdir()
        test_plan = textwrap.dedent("""
            # Test Plan

            ## 定义表

            | **ID** | 描述 |
            | --- | --- |
            | **ID** | TC-LOCAL-001 |
            | **ID** | TC-LOCAL-002 |

            ## 回归矩阵（引用其他 change 的 TC）

            参照 TC-EXTERNAL-555 与 TC-EXTERNAL-556 的既有测试。
        """)
        (change_dir / "test-plan.md").write_text(test_plan, encoding="utf-8")

        # 造一个假 tests 目录，其中只含 TC-LOCAL-001
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_impl.py").write_text(
            "def test_a():  # TC-LOCAL-001\n    pass\n", encoding="utf-8",
        )

        # 调用检查；TC-EXTERNAL-555/556 不应算入 planned，只有 TC-LOCAL-002 缺实现
        status, msg = check_tc_implementation_coverage(change_dir, tmp_path)
        # 覆盖 1/2 = 50%
        assert "50%" in msg or "TC-LOCAL-002" in msg, f"未识别到 TC-LOCAL-002 缺失: {msg}"
        assert "TC-EXTERNAL" not in msg, f"引用 TC 被错误算入 planned: {msg}"
