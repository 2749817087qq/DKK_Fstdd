"""test_caveman.py — caveman-compressor 行为测试（22 TC）

Change: 2026-10-03-caveman-kg-sync
TC 映射: .fstdd/changes/2026-10-03-caveman-kg-sync/test-plan.md

RED 阶段：本文件先于 `upstream/fstdd/caveman.py` 存在 → import 失败即为 RED。
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = REPO_ROOT / "upstream"
TOOLS = REPO_ROOT / "tools"

# 保证 `import fstdd` 解析到 upstream/fstdd（而非任何其它同名包）
for _p in (str(UPSTREAM), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fstdd.caveman import DEFAULT_KEEP_KEYS, compress, compress_dict  # noqa: E402

FSTDD_BIN = UPSTREAM / "bin" / "fstdd"
PY = sys.executable


def _run(args):
    return subprocess.run(args, capture_output=True, text=True, cwd=str(REPO_ROOT))


# ============================================================
# REQ 1: 独立库 API
# ============================================================
def test_CAVE_TC_001_import_api():
    """CAVE-SC-001: 独立库可 import，无循环依赖"""
    assert callable(compress)
    assert callable(compress_dict)


def test_CAVE_TC_002_no_hub_client_dependency():
    """CAVE-SC-001: caveman.py 不依赖 hub_client / canon（无循环 import）"""
    src = (UPSTREAM / "fstdd" / "caveman.py").read_text(encoding="utf-8")
    assert "hub_client" not in src
    assert "import canon" not in src


def test_CAVE_TC_003_compress_within_budget():
    """CAVE-SC-002: compress 输出 ≤ max_chars"""
    text = "summary: " + ("很长的内容" * 100)
    out = compress(text, max_chars=200)
    assert len(out) <= 200


def test_CAVE_TC_004_compress_dict_keep_keys():
    """CAVE-SC-003: compress_dict 只保留 keep_keys，值不变"""
    assert compress_dict({"a": 1, "b": 2}, keep_keys=["a"]) == {"a": 1}


# ============================================================
# REQ 2: 压缩算法
# ============================================================
def test_CAVE_TC_005_motivation_stripped():
    """CAVE-SC-004: motivation/why 段落直接砍"""
    text = "## Why\n因为想省 token 所以做这个\n\n## What\n实现压缩器\n"
    out = compress(text, max_chars=200)
    assert "省 token" not in out
    assert "实现压缩器" in out


def test_CAVE_TC_006_zh_modifier_compression():
    """CAVE-SC-005: 中文修饰词砍除 → 长度显著下降"""
    text = "在 Windows 环境下使用 PowerShell 处理用户要求更新到最新版的请求"
    out = compress(text, max_chars=500)
    assert len(out) < len(text)
    assert len(out) <= len(text) * 0.6


def test_CAVE_TC_007_en_stopwords_removed():
    """CAVE-SC-006: 英文停用词移除"""
    out = compress("The implementation is in the file for testing", max_chars=200)
    words = out.lower().split()
    for sw in ("the", "is", "in", "for"):
        assert sw not in words
    assert "implementation" in out


def test_CAVE_TC_008_over_budget_output_within_limit():
    """CAVE-SC-007: 单字段超限 → trim + 砍最低 weight → 输出 ≤ max_chars"""
    text = (
        "summary: " + ("总" * 100) + "\n"
        "runner_cmd: " + ("a" * 100) + "\n"
        "constraints: " + ("c" * 100) + "\n"
        "scope: " + ("s" * 100)
    )
    out = compress(text, max_chars=120)
    assert len(out) <= 120


# ============================================================
# REQ 3: output_contract — 截断优先级倒转
# ============================================================
def test_CAVE_TC_009_priority_reversal_keeps_constraints():
    """CAVE-SC-008: 预算不足 → 先砍 summary，保住 constraints"""
    text = "summary: " + ("长" * 200) + "\nconstraints: MUST 保持幂等"
    out = compress(text, max_chars=60)
    assert len(out) <= 60
    assert "MUST" in out or "幂等" in out


def test_CAVE_TC_010_constraints_non_empty_after_reversal():
    """CAVE-SC-009: 倒转后 constraints 非空"""
    text = "summary: " + ("长" * 200) + "\nconstraints: MUST 保持幂等"
    out = compress(text, max_chars=60)
    assert "constraints:" in out
    assert out.split("constraints:", 1)[1].strip() != ""


def test_CAVE_TC_011_no_deadline_ok():
    """CAVE-SC-010: 输入无 deadline 不影响其他字段"""
    out = compress("summary: 做X\nconstraints: 无附加约束", max_chars=200)
    assert isinstance(out, str)
    assert "constraints:" in out


def test_CAVE_TC_012_default_keep_keys_include_multihub_fields():
    """CAVE-SC-011: default_keep_keys 含 task_id + idempotency_key"""
    d = {"task_id": "t1", "idempotency_key": "k1", "noise": "x"}
    out = compress_dict(d)
    assert "task_id" in out
    assert "idempotency_key" in out
    assert "noise" not in out


# ============================================================
# REQ 4: Determinism
# ============================================================
def test_CAVE_TC_013_deterministic():
    """CAVE-SC-012: 同输入 3 次调用输出完全一致"""
    text = "在 Windows 环境下使用 PowerShell 处理用户要求更新到最新版的请求"
    outs = [compress(text, max_chars=200) for _ in range(3)]
    assert outs[0] == outs[1] == outs[2]


# ============================================================
# REQ 5: CLI 子命令
# ============================================================
def test_CAVE_TC_014_cli_stdout(tmp_path):
    """CAVE-SC-013: fstdd caveman <file> → stdout 有内容, exit 0"""
    f = tmp_path / "in.txt"
    f.write_text("summary: 做压缩器\nconstraints: deterministic", encoding="utf-8")
    r = _run([PY, str(FSTDD_BIN), "caveman", str(f)])
    assert r.returncode == 0, r.stderr
    assert len(r.stdout.strip()) > 0


def test_CAVE_TC_015_cli_max_flag(tmp_path):
    """CAVE-SC-014: --max 100 生效"""
    f = tmp_path / "in.txt"
    f.write_text("a" * 500, encoding="utf-8")
    r = _run([PY, str(FSTDD_BIN), "caveman", "--max", "100", str(f)])
    assert r.returncode == 0, r.stderr
    assert len(r.stdout.strip()) <= 100


def test_CAVE_TC_016_cli_missing_file(tmp_path):
    """CAVE-SC-015: 文件不存在 → exit code non-zero"""
    r = _run([PY, str(FSTDD_BIN), "caveman", str(tmp_path / "nope.txt")])
    assert r.returncode != 0


# ============================================================
# REQ 6: Integration points
# ============================================================
def test_CAVE_TC_017_canon_generate_appends_summary(tmp_path):
    """CAVE-SC-016: canon generate → 同目录追加 caveman_summary.txt"""
    from fstdd.cli.commands.canon import _generate_one

    change = "2026-10-03-caveman-demo"
    cdir = tmp_path / ".fstdd" / "changes" / change
    (cdir / "canonical" / "proposals").mkdir(parents=True)
    (cdir / "canonical" / "proposals" / f"{change}.yaml").write_text(
        "meta:\n  title: demo\n"
        "why:\n  problem: 背景故事\n"
        "what_changes:\n  - description: 做压缩器\n",
        encoding="utf-8",
    )
    _generate_one(tmp_path, change, "proposal")

    summary_file = cdir / "caveman_summary.txt"
    assert summary_file.exists()
    assert len(summary_file.read_text(encoding="utf-8")) <= 200


def test_CAVE_TC_018_hub_issue_adds_scope_min():
    """CAVE-SC-017: hub_client.issue → scope 自动附带 scope_min"""
    import hub_client

    hub = hub_client.HubClient(token="x", url="http://127.0.0.1:1", node_id="TEST")
    captured = {}
    hub._post = lambda path, body: captured.update({"path": path, "body": body}) or {}

    hub.issue(summary="s", scope={"task_id": "t1", "runner_cmd": "cmd", "noise": "x" * 300})
    scope = captured["body"]["scope"]
    assert "scope_min" in scope
    assert scope["scope_min"]["task_id"] == "t1"


def test_CAVE_TC_019_hub_complete_result_min_conditional():
    """CAVE-SC-018: result>200 → 附 result_min；短 result 不附"""
    import hub_client

    hub = hub_client.HubClient(token="x", url="http://127.0.0.1:1", node_id="TEST")
    hub._get = lambda *a, **k: {}
    hub.list_tasks = lambda *a, **k: []
    captured = {}
    hub._post = lambda path, body: captured.update({"body": body}) or {}

    hub.complete("task-1", result="x" * 500)
    assert "result_min" in captured["body"]

    captured.clear()
    hub.complete("task-1", result="ok")
    assert "result_min" not in captured["body"]


# ============================================================
# REQ 7: trim_rules 具体 regex
# ============================================================
def test_CAVE_TC_020_zh_modifier_regex():
    """CAVE-SC-019: 中文修饰词 regex 实际把 'XX的YY' 短语砍掉"""
    out = compress("使用最新版的软件", max_chars=200)
    assert "的" not in out


def test_CAVE_TC_021_duplicate_command_merged():
    """CAVE-SC-021: 重复命令合并为一次"""
    out = compress("git pull git pull", max_chars=200)
    assert out.count("git pull") == 1


# ============================================================
# REQ 8: token reduction 实测
# ============================================================
def test_CAVE_TC_022_token_reduction_ge_50pct():
    """CAVE-SC-022: scope_min token ≤ full scope 的 50%"""
    full = {
        "task_id": "task-abc",
        "runner_cmd": "python tests/run_release_validation.py",
        "constraints": "幂等",
        "deadline": "24h",
        "idempotency_key": "k",
        "motivation": "很长的背景说明" * 50,
        "description": "很长的描述文本" * 50,
        "why": "原因分析" * 50,
    }
    mini = compress_dict(full, DEFAULT_KEEP_KEYS)
    full_len = len(json.dumps(full, ensure_ascii=False))
    mini_len = len(json.dumps(mini, ensure_ascii=False))
    assert mini_len <= 0.5 * full_len