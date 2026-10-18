# -*- coding: utf-8 -*-
"""出站脱敏规则的**唯一事实源**一致性（2026-10-18 审计 F4）。

背景
----
仓库里有两条出站路径，各自脱敏：

  · `tools/share_experience.py::stage_sanitized()` —— 15 条正则 + 域名白名单
  · `upstream/fstdd/cli/commands/_exp_sync.py::_sanitize_text()` —— 曾自带 4 条正则

后者注释写着「与 share_experience 的 stage_sanitized 一致」，**那句话是假的**。
15 类敏感形态对照实测 12 类漏脱敏：Windows 绝对路径、POSIX 家目录、内网域名、
`ghu_`/`ghr_` token、`sk-` API key、AWS AKIA、私钥块、Bearer 全部漏。
影响面是 `push_bundle(hub_dir=...)` 本地目录适配器 —— 经验会以明文落到 hub 目录。

修复方向不是「把 4 条补齐到 14 条」（两份规则必然再次漂移），而是**复用同一实现**：
`_exp_sync._load_canonical_sanitizer()` 按路径加载 `tools/share_experience.py`，
找不到就**抛错**而不是降级到弱规则 —— 弱规则出站等于静默泄露。

运行：
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \\
        python -m pytest tests/test_exp_sync_sanitize_parity.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


share = _load("fstdd_share_for_parity", "tools/share_experience.py")
sync = _load("fstdd_exp_sync_for_parity", "upstream/fstdd/cli/commands/_exp_sync.py")


# 审计实测漏脱敏的 12 类 + 原本就能命中的 3 类，共 15 类
SENSITIVE_SAMPLES = {
    "Windows 绝对路径": r"C:\Users\bob\secret.txt",
    "Windows 正斜杠路径": "D:/work/private/notes.md",
    "POSIX 家目录": "/home/ubuntu/keys/id_rsa.txt",
    "POSIX Users 路径": "/Users/alice/.ssh/known_hosts",
    "root 路径": "/root/.ssh/id_ed25519",
    "内网域名": "api.corp.internal:8080",
    "ghp token": "ghp_" + "A" * 36,
    "ghu token": "ghu_" + "B" * 36,
    "ghr token": "ghr_" + "C" * 36,
    "github_pat": "github_pat_" + "D" * 30,
    "sk- API key": "sk-" + "e" * 32,
    "AWS AKIA": "AKIA" + "F" * 16,
    # PEM 头必须**运行时拼接**：`upstream/tests/test_no_plaintext_credentials.py`
    # 对 tracked 文件做 `git grep -nIE "-----BEGIN [A-Z ]*PRIVATE KEY-----"`，
    # 且明确「零白名单，合法 fixture 一律运行时构造」。写成连续字面量会让本文件
    # 自己变成违规项（2026-10-18 全量门禁实测踩到）。
    "私钥块": ("-----BEGIN RSA " + "PRIVATE KEY-----\nMIIEow\n"
               "-----END RSA " + "PRIVATE KEY-----"),
    "Bearer 令牌": "Bearer " + "g" * 32,
    "AWS secret": "aws_secret_access_key = " + "h" * 40,
    "邮箱": "bob@example.com",
    "IPv4": "10.1.2.3",
}


@pytest.mark.parametrize("label,sample", list(SENSITIVE_SAMPLES.items()))
def test_exp_sync_matches_canonical_sanitizer(label, sample):
    """TC-CLOSURE-012（SC-012）`_sanitize_text` 必须与 `share.sanitize` 逐字节一致。"""
    got = sync._sanitize_text(sample)
    want = share.sanitize(sample, True)[0]
    assert got == want, "%s：两套规则分叉\n  实际 %r\n  期望 %r" % (label, got, want)


@pytest.mark.parametrize("label,sample", list(SENSITIVE_SAMPLES.items()))
def test_exp_sync_never_leaks_sensitive_form(label, sample):
    """脱敏后不得原样保留敏感内容（防止「一致地都不脱敏」这种假绿）。"""
    got = sync._sanitize_text(sample)
    assert got.strip() != sample.strip(), "%s：脱敏后原样未变" % label


def test_sanitize_text_delegates_to_canonical(monkeypatch):
    """`_sanitize_text` 必须委托给唯一事实源，而不是本地再算一遍。"""
    calls: list = []

    def _spy(text, enabled=True):
        calls.append((text, enabled))
        return "CLEANED", ["stub"]

    monkeypatch.setattr(sync, "_CANONICAL_SANITIZE", _spy)
    assert sync._sanitize_text("dirty") == "CLEANED"
    assert calls == [("dirty", True)], calls


def test_no_weak_rule_table_remains():
    """弱化规则副本必须已删除，否则将来可能被误用回出站路径。"""
    assert sync._SANITIZE_RULES is None, (
        "`_SANITIZE_RULES` 仍是规则表 —— 说明弱化副本没删干净，"
        "存在被重新接入出站路径的风险（审计 F4）"
    )


def test_canonical_sanitizer_resolves_in_repo_layout():
    """仓库布局下必须能解析到唯一事实源。"""
    sync._CANONICAL_SANITIZE = None      # 清缓存，强制重新解析
    try:
        fn = sync._load_canonical_sanitizer()
        assert callable(fn)
        assert fn is share.sanitize or fn.__code__.co_code == share.sanitize.__code__.co_code
    finally:
        sync._CANONICAL_SANITIZE = None
