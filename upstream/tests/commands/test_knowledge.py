"""V3.0: tests for stdd knowledge CLI."""
import argparse
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_knowledge_query_empty_graph(temp_project, monkeypatch, capsys):
    """TC-KG-006: query on empty graph shows helpful message."""
    monkeypatch.chdir(temp_project)
    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="query", keyword_or_id="test", verbose=0,
                           related=False, format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "知识图谱为空" in captured.out or "空" in captured.out


def test_knowledge_query_no_match(temp_project, monkeypatch, capsys):
    """TC-KG-007: query with no matching keyword."""
    monkeypatch.chdir(temp_project)
    # Create a minimal graph with one node
    import yaml
    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [{
            "id": "KG-001", "type": "failure_pattern",
            "title": "裸 except 吞异常", "description": "AI uses bare except",
            "cross_project_count": 3, "projects": ["test-project"],
            "category": "cascading_errors", "severity": "high",
            "metrics": {"occurrence_count": 3, "severity_trend": "stable", "last_seen": "2026-07-01"},
        }],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="query", keyword_or_id="XYZZY_NOT_FOUND_12345", verbose=0,
                           related=False, format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "无匹配" in captured.out


def test_knowledge_query_match(temp_project, monkeypatch, capsys):
    """TC-KG-006: query finds matching node."""
    monkeypatch.chdir(temp_project)
    import yaml
    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [
            {
                "id": "KG-001", "type": "failure_pattern",
                "title": "裸 except 吞异常", "description": "AI uses bare except",
                "cross_project_count": 3, "projects": ["p1", "p2", "p3"],
                "category": "cascading_errors", "severity": "high",
                "metrics": {"occurrence_count": 3, "severity_trend": "stable", "last_seen": ""},
            },
            {
                "id": "KG-002", "type": "fix_template",
                "title": "规范异常处理", "description": "Use specific exceptions",
                "cross_project_count": 2, "projects": ["p1"],
                "success_rate": 0.88, "total_applications": 8,
                "steps": ["Step 1", "Step 2"],
                "metrics": {"occurrence_count": 2, "severity_trend": "stable", "last_seen": ""},
            },
        ],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="query", keyword_or_id="except", verbose=0,
                           related=False, format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "KG-001" in captured.out
    assert "裸 except" in captured.out


def test_knowledge_query_json_format(temp_project, monkeypatch, capsys):
    """TC-KG-006: query with JSON output."""
    monkeypatch.chdir(temp_project)
    import yaml, json
    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [{
            "id": "KG-001", "type": "failure_pattern",
            "title": "test pattern", "description": "test",
            "cross_project_count": 1, "projects": ["test"], "category": "scope_creep",
            "severity": "medium",
            "metrics": {"occurrence_count": 1, "severity_trend": "stable", "last_seen": ""},
        }],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="query", keyword_or_id="test", verbose=0,
                           related=False, format="json", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result) >= 1
    assert result[0]["id"] == "KG-001"


def test_knowledge_merge_local_only(temp_project, monkeypatch, capsys):
    """TC-KG-003: merge creates graph from local experiences."""
    monkeypatch.chdir(temp_project)
    import yaml

    # Set up project config
    config_dir = temp_project / ".stdd" / "config.d"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_dir.joinpath("project.yaml").write_text(
        "project:\n  name: test-project\n  language: python\nsource_dir: app\n", encoding="utf-8")

    # Create experience
    exp_dir = temp_project / ".stdd" / "experiences"
    exp_dir.mkdir(parents=True, exist_ok=True)
    exp_content = """---
experience_id: EXP-2026-0001
category: cascading_errors
pattern: "裸 except 吞异常"
root_cause: "AI defaults to bare except"
fix_template: "Use specific exception types"
language: python
severity: high
occurrences: 2
lifecycle_state: deposited
last_seen: "2026-07-01"
---

# Test experience
"""
    (exp_dir / "EXP-2026-0001.md").write_text(exp_content, encoding="utf-8")

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="merge", verbose=0, dry_run=False)
    # Mock community fetch to return None
    with patch("stdd.cli.commands.knowledge._fetch_community_graph", return_value=None):
        cmd_knowledge(ns)

    captured = capsys.readouterr()
    assert "知识图谱已更新" in captured.out or "已更新" in captured.out

    # Verify graph was created
    graph_path = temp_project / ".stdd" / "knowledge" / "knowledge-graph.yaml"
    assert graph_path.exists()
    with open(graph_path, "r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)
    assert len(saved.get("nodes", [])) >= 1


def test_knowledge_merge_dedup(temp_project, monkeypatch, capsys):
    """TC-KG-004: merge deduplicates similar patterns."""
    monkeypatch.chdir(temp_project)
    import yaml

    # Set up project config
    config_dir = temp_project / ".stdd" / "config.d"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_dir.joinpath("project.yaml").write_text(
        "project:\n  name: test-project\n  language: python\nsource_dir: app\n", encoding="utf-8")

    # Create existing graph with one node
    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    existing_graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [{
            "id": "KG-001", "type": "failure_pattern",
            "title": "裸 except 吞异常导致调试困难", "description": "bare except swallows exceptions making debugging hard",
            "cross_project_count": 2, "projects": ["proj-a", "proj-b"],
            "category": "cascading_errors", "severity": "high",
            "root_cause": "", "fix_template_refs": [], "tags": [],
            "metrics": {"occurrence_count": 2, "severity_trend": "stable", "last_seen": ""},
        }],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(existing_graph, f, allow_unicode=True)

    # Create similar experience
    exp_dir = temp_project / ".stdd" / "experiences"
    exp_dir.mkdir(parents=True, exist_ok=True)
    exp_content = """---
experience_id: EXP-2026-0002
category: cascading_errors
pattern: "裸 except 吞异常导致调试困难"
root_cause: ""
fix_template: ""
language: python
severity: high
occurrences: 1
lifecycle_state: deposited
last_seen: "2026-07-02"
---

# Similar experience
"""
    (exp_dir / "EXP-2026-0002.md").write_text(exp_content, encoding="utf-8")

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="merge", verbose=0, dry_run=False)
    with patch("stdd.cli.commands.knowledge._fetch_community_graph", return_value=None):
        cmd_knowledge(ns)

    captured = capsys.readouterr()
    # Should update existing node, not create new
    graph_path = know_dir / "knowledge-graph.yaml"
    with open(graph_path, "r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)
    nodes = saved.get("nodes", [])
    # cross_project_count should be incremented (2 original + 1 new = 3)
    assert nodes[0]["cross_project_count"] >= 3
    assert "test-project" in nodes[0]["projects"]


def test_knowledge_merge_network_fallback(temp_project, monkeypatch, capsys):
    """TC-KG-005: merge gracefully handles network failure."""
    monkeypatch.chdir(temp_project)

    config_dir = temp_project / ".stdd" / "config.d"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_dir.joinpath("project.yaml").write_text(
        "project:\n  name: test-project\n  language: python\nsource_dir: app\n", encoding="utf-8")

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="merge", verbose=0, dry_run=False)
    with patch("stdd.cli.commands.knowledge._fetch_community_graph", return_value=None):
        cmd_knowledge(ns)

    captured = capsys.readouterr()
    assert "社区图谱不可用" in captured.out or "无待合并" in captured.out


def test_knowledge_predict(temp_project, monkeypatch, capsys):
    """TC-KG-008: predict returns risk predictions."""
    monkeypatch.chdir(temp_project)
    import yaml

    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [
            {
                "id": "KG-001", "type": "failure_pattern",
                "title": "裸 except 吞异常", "description": "bare except",
                "cross_project_count": 5, "projects": ["p1", "p2", "p3", "p4", "p5"],
                "category": "cascading_errors", "severity": "high",
                "metrics": {"occurrence_count": 5, "severity_trend": "rising", "last_seen": ""},
            },
            {
                "id": "KG-002", "type": "failure_pattern",
                "title": "N+1 查询问题", "description": "nplus1",
                "cross_project_count": 3, "projects": ["p1", "p2", "p3"],
                "category": "cascading_errors", "severity": "high",
                "metrics": {"occurrence_count": 3, "severity_trend": "stable", "last_seen": ""},
            },
        ],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="predict", keyword_or_id="", verbose=0,
                           change_name="2026-07-01-test-change", format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "风险预测" in captured.out
    assert "KG-001" in captured.out


def test_knowledge_predict_json(temp_project, monkeypatch, capsys):
    """TC-KG-008: predict with JSON output."""
    monkeypatch.chdir(temp_project)
    import yaml, json

    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [{
            "id": "KG-001", "type": "failure_pattern",
            "title": "test pattern", "description": "test",
            "cross_project_count": 3, "projects": ["p1", "p2", "p3"],
            "category": "scope_creep", "severity": "medium",
            "metrics": {"occurrence_count": 3, "severity_trend": "stable", "last_seen": ""},
        }],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="predict", keyword_or_id="", verbose=0,
                           change_name="test-change", format="json", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result) >= 1
    assert "confidence" in result[0]


def test_knowledge_predict_insufficient_data(temp_project, monkeypatch, capsys):
    """TC-KG-009: predict with insufficient data shows warning."""
    monkeypatch.chdir(temp_project)
    import yaml

    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    # Only 1 node = insufficient
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [{
            "id": "KG-001", "type": "failure_pattern",
            "title": "test", "description": "test",
            "cross_project_count": 1, "projects": ["p1"],
            "category": "scope_creep", "severity": "medium",
            "metrics": {"occurrence_count": 1, "severity_trend": "stable", "last_seen": ""},
        }],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="predict", keyword_or_id="", verbose=0,
                           change_name="test", format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "数据不足" in captured.err


def test_knowledge_fix_with_template(temp_project, monkeypatch, capsys):
    """TC-KG-010: fix finds associated fix_template."""
    monkeypatch.chdir(temp_project)
    import yaml

    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [
            {
                "id": "KG-001", "type": "failure_pattern",
                "title": "裸 except 吞异常", "description": "bare except",
                "cross_project_count": 3, "projects": ["test-project"],
                "category": "cascading_errors", "severity": "high",
                "fix_template_refs": ["KG-001-FIX"],
                "metrics": {"occurrence_count": 3, "severity_trend": "stable", "last_seen": ""},
            },
            {
                "id": "KG-001-FIX", "type": "fix_template",
                "title": "规范异常处理模板",
                "cross_project_count": 2, "projects": ["p1", "p2"],
                "success_rate": 0.92, "total_applications": 12,
                "steps": ["1. Replace bare except", "2. Add CancelledError", "3. Add lint rule"],
                "metrics": {"occurrence_count": 2, "severity_trend": "stable", "last_seen": ""},
            },
        ],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    # Also create matching experience
    exp_dir = temp_project / ".stdd" / "experiences"
    exp_dir.mkdir(parents=True, exist_ok=True)
    exp_content = """---
experience_id: EXP-2026-0001
category: cascading_errors
pattern: "裸 except 吞异常"
language: python
lifecycle_state: deposited
---

# Test
"""
    (exp_dir / "EXP-2026-0001.md").write_text(exp_content, encoding="utf-8")

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="fix", keyword_or_id="EXP-2026-0001", verbose=0,
                           experience_id="EXP-2026-0001", format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "92%" in captured.out or "0.92" in captured.out


def test_knowledge_fix_no_template(temp_project, monkeypatch, capsys):
    """TC-KG-010: fix when no template exists."""
    monkeypatch.chdir(temp_project)
    import yaml

    know_dir = temp_project / ".stdd" / "knowledge"
    know_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "graph_version": "1.0", "last_merged": "",
        "nodes": [{
            "id": "KG-001", "type": "failure_pattern",
            "title": "test pattern",
            "cross_project_count": 1, "projects": [],
            "category": "scope_creep", "severity": "low",
            "fix_template_refs": [],
            "metrics": {"occurrence_count": 1, "severity_trend": "stable", "last_seen": ""},
        }],
        "edges": [],
    }
    with open(know_dir / "knowledge-graph.yaml", "w", encoding="utf-8") as f:
        yaml.dump(graph, f, allow_unicode=True)

    from stdd.cli.commands.knowledge import cmd_knowledge
    ns = argparse.Namespace(subcommand="fix", keyword_or_id="EXP-2026-0001", verbose=0,
                           experience_id="EXP-2026-0001", format="table", dry_run=False)
    cmd_knowledge(ns)
    captured = capsys.readouterr()
    assert "暂无" in captured.out or "暂无跨项目修复模板" in captured.out


def test_knowledge_help(temp_project, monkeypatch, capsys):
    """Verify knowledge --help works."""
    monkeypatch.chdir(temp_project)
    ret = __import__("os").system("cd " + str(temp_project) +
        " && python -c \"from stdd.cli.commands.knowledge import cmd_knowledge; "
        "import argparse; args=argparse.Namespace(subcommand='query',keyword_or_id='x',verbose=0,related=False,format='table',dry_run=False); "
        "cmd_knowledge(args)\" 2>&1")
    # Just verify no crash
