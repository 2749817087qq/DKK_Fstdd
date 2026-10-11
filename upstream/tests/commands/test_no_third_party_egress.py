"""Slice 6 契约测试：不引入第三方外发（REQ-006，TC-ESAF-001..002）。

对应 spec：
- SC-023 `_cmd_share_single` 仍含 leonai42/hzddyy 的禁用分支，且禁用逻辑未被改动
- SC-024 本变更新增/修改的全部源码无「指向 leonai42/hzddyy 之外的第三方外发目标」，
        仅第一方 fstdd-hub 出现在 share_experience 既有路径

判据用 AST 区分「注释/docstring（说明性，允许）」与「活跃字符串字面量（可能外发，禁止）」。
"""
import ast
import inspect
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
UPSTREAM = REPO / "upstream"

THIRD_PARTY_HOSTS = (
    "hzddyy.com",
    "leonai42/stdd-experiences",
    "leonai42/stdd",
)

# 本变更触及/新增的源码（SC-024 审计范围）
AUDIT_FILES = (
    UPSTREAM / "fstdd" / "cli" / "commands" / "experience.py",
    UPSTREAM / "fstdd" / "cli" / "commands" / "_exp_crypto.py",
    UPSTREAM / "fstdd" / "cli" / "__init__.py",
    REPO / "tools" / "share_experience.py",
)


def _active_literal_hits(path: Path):
    """返回「活跃外发语境」字符串字面量中命中第三方主机的 (行号, 片段)。

    允许语境（说明性，不算外发）：docstring、`print(...)`、日志调用、`add_argument/add_parser`
    等 CLI 描述文本。其余字符串字面量视为「可能承载外发目标」。
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    allowed_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                allowed_ids.add(id(body[0].value))
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            if name in ("print", "debug", "info", "warning", "error", "exception",
                        "critical", "add_argument", "add_parser"):
                for arg in node.args:
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Constant):
                            allowed_ids.add(id(sub))

    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in allowed_ids:
                continue
            for host in THIRD_PARTY_HOSTS:
                if host in node.value:
                    hits.append((node.lineno, node.value[:80]))
    return hits


def test_esaf001_share_single_still_disabled():
    """TC-ESAF-001 / SC-023：_cmd_share_single 的禁用分支与注释保持不变。"""
    from fstdd.cli.commands import experience as exp

    src = inspect.getsource(exp._cmd_share_single)
    assert "leonai42" in src
    assert "hzddyy" in src
    assert "永久禁用" in src
    # 行为：任何调用都返回 False（不外发）
    assert exp._cmd_share_single("EXP-2026-0001", Path(".")) is False

    # 两条历史外发通道仍为「永久移除」态（raise，不发网络请求）
    for fn in (exp._share_via_gh, exp._share_via_api):
        with pytest.raises(RuntimeError):
            fn("EXP-2026-0001", "content")


def test_esaf002_no_new_third_party_egress():
    """TC-ESAF-002 / SC-024：审计范围内无活跃的第三方外发字符串/目标。"""
    assert AUDIT_FILES, "审计文件清单不能为空"
    offenders = []
    for path in AUDIT_FILES:
        assert path.is_file(), f"审计文件缺失: {path}"
        offenders.extend((path.name, ln, frag) for ln, frag in _active_literal_hits(path))
    assert not offenders, f"发现活跃的第三方外发目标: {offenders}"


def test_esaf002b_first_party_target_is_hub():
    """SC-024 补充：第一方传输目标确为自有 hub（fstdd-hub / inbox），非第三方。"""
    share = (REPO / "tools" / "share_experience.py").read_text(encoding="utf-8")
    assert "fstdd-hub" in share
