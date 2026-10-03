# -*- coding: utf-8 -*-
"""凭证形态门禁 —— 明文高置信凭证不得随仓库分发。

背景
----
服务器 GitHub 镜像被 **push protection** 拦截：历史中混入了两枚明文凭证
（GitHub PAT 形态串 + OPENSSH 私钥）。根因不在写权限，而在「凭证形态字面量入库」。
本门禁提供一道**仓库侧、可验证**的防线：任何 tracked 文件出现高置信凭证形态
即判红，随全量 `pytest upstream/tests` 自动执行。

设计原则
--------
· 纯函数 `scan_text_for_credentials()` 可被正/负样本单测 —— 避免写成「恒真」假门禁。
· 全仓扫描 `git grep -nIE` 只读遍历 tracked 文件。
· **零白名单**：合法 fixture 已改为运行时拼接构造，不设豁免清单。
· 泛化前缀（如裸 `Bearer`）不纳入 —— 误报会迫使引入白名单，反而削弱门禁。

运行：
    cd /d/FSTDD/stdd-repo && <python> -m pytest upstream/tests/test_no_plaintext_credentials.py -q
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# 高置信凭证形态：模式名 → ERE（与 git grep -E 同源，供纯函数与全仓扫描共用）。
# 注意：这些模式串本身**不构成**凭证形态（前缀后紧跟 `[`，非连续字母数字），
# 故本文件不会自命中 —— 见 test_scan_ignores_regex_literals。
CREDENTIAL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("github_pat_classic", r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("github_pat_fine", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("openai_style_key", r"sk-[A-Za-z0-9]{20,}"),
    ("aws_access_key_id", r"AKIA[0-9A-Z]{16}"),
    ("pem_private_key_header", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

_COMPILED = tuple((name, re.compile(pat)) for name, pat in CREDENTIAL_PATTERNS)


def scan_text_for_credentials(text: str) -> list[tuple[int, str]]:
    """返回 [(行号, 模式名), ...]；行号从 1 起，便于定位。"""
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pat in _COMPILED:
            if pat.search(line):
                hits.append((lineno, name))
                break
    return hits


def _git_grep(pattern: str) -> list[str]:
    """对 tracked 文件执行只读 git grep。

    git grep 退出码：0 = 命中，1 = 无命中，其它 = 执行错误。
    仅「git 未安装」允许 skip；执行错误必须**硬失败** —— 否则门禁会 fail-open
    （扫描压根没跑成却判通过），正是本门禁要防的静默失效。
    """
    try:
        proc = subprocess.run(
            ["git", "grep", "-nIE", "--", pattern],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:  # git 未安装：门禁无判据，skip 而非假绿
        pytest.skip("git 不可用，无法执行 tracked 文件凭证扫描")
    assert proc.returncode in (0, 1), (
        "git grep 执行失败（退出码 %d）：%s" % (proc.returncode, proc.stderr.strip()))
    return [ln for ln in proc.stdout.splitlines() if ln]


# ===========================================================================
# 门禁自身的可判定性：正/负样本（防「恒真」假门禁）
# ===========================================================================
def test_scan_detects_injected_pat():
    """TC-CRED-004 / SC-004 正样本：运行时拼接出的 PAT 形态须被报出，且带行号。"""
    text = "prefix\ntoken=" + "ghp_" + "A" * 30 + "\n"
    hits = scan_text_for_credentials(text)
    assert hits, "注入的 PAT 形态未被检出 —— 门禁形同虚设"
    assert hits[0][0] == 2, "命中行号应为 2，实际 %r" % (hits[0],)
    assert hits[0][1] == "github_pat_classic"


def test_scan_ignores_regex_literals():
    """TC-CRED-005 / SC-004 负样本：仅含正则字面量（前缀后紧跟 `[`）不得误报。"""
    text = r"pattern: ghp_[A-Za-z0-9]{20,}" + "\n"
    assert scan_text_for_credentials(text) == []


def test_scan_detects_private_key_header():
    """TC-CRED-004 / SC-004 补充：PEM 私钥头须被检出。"""
    text = "x\n" + "-----BEGIN " + "RSA PRIVATE KEY-----" + "\n"
    hits = scan_text_for_credentials(text)
    assert hits and hits[0][1] == "pem_private_key_header"


def test_gate_is_collected_by_release_command():
    """TC-CRED-002 / SC-002：门禁须落在发布门禁的收集目录 `upstream/tests/`。

    `python -m pytest upstream/tests -q` 只收集该目录；门禁若落在别处，
    发布门禁不会执行它 —— 这是「门禁随发布门禁自动执行」的机制本身。
    """
    assert Path(__file__).resolve().parent == REPO_ROOT / "upstream" / "tests"


# ===========================================================================
# REQ-001：轮换脚本自身脱敏
# ===========================================================================
def test_rotate_script_has_no_pat_literal():
    """TC-CRED-001 / SC-001：脚本含 0 处 PAT 形态字面量，且校验正则保留。"""
    src = (REPO_ROOT / "tools" / "rotate_github_token.sh").read_text(encoding="utf-8")
    assert scan_text_for_credentials(src) == [], "轮换脚本仍含凭证形态字面量"
    assert "^ghp_[A-Za-z0-9]{36}$" in src, "参数校验正则被误删/误改"


# ===========================================================================
# 全仓门禁：tracked 文件零命中（零白名单）
# ===========================================================================
@pytest.mark.parametrize("name,pattern", CREDENTIAL_PATTERNS)
def test_no_plaintext_credentials_in_tracked_files(name, pattern):
    """TC-CRED-003 / SC-002 / SC-003：全部 tracked 文件对五类形态命中数均为 0。"""
    hits = _git_grep(pattern)
    assert hits == [], "tracked 文件命中 %s 形态：\n%s" % (name, "\n".join(hits))


# ===========================================================================
# REQ-004：镜像故障处置手册覆盖 push protection 类
# ===========================================================================
def test_mirror_runbook_present():
    """TC-CRED-007 / SC-006：§五 处置表须含 push protection / secret scanning 的可执行解除路径。"""
    doc = (REPO_ROOT / "docs" / "DISTRIBUTED_ACCESS.md").read_text(encoding="utf-8")
    low = doc.lower()
    assert "push protection" in low or "secret scanning" in low, \
        "处置手册未覆盖 push protection / secret scanning 类"
    assert "unblock-secret" in doc, "未给出一性 unblock 链接指引"
    assert "rotate_github_token.sh" in doc, "未给出凭证轮换命令"
    assert "check_mirror.sh" in doc, "未给出恢复验证手段"
    assert "Release" in doc, "未给出 Release 补发指引"


# ===========================================================================
# REQ-005：孤儿私钥撤销跟踪（SC-007）
# ===========================================================================
def test_orphan_private_key_untracked_and_ignored():
    """TC-CRED-008 / SC-007：私钥脱离跟踪、.gitignore 覆盖，且磁盘文件保留。"""
    key_rel = ".fstdd/_fstdd003_key_new.txt"

    tracked = subprocess.run(["git", "ls-files", "--", key_rel], cwd=str(REPO_ROOT),
                             capture_output=True, text=True, encoding="utf-8")
    assert tracked.stdout.strip() == "", "孤儿私钥仍被 tracked：%s" % tracked.stdout.strip()

    ignored = subprocess.run(["git", "check-ignore", "-v", key_rel], cwd=str(REPO_ROOT),
                             capture_output=True, text=True, encoding="utf-8")
    assert ignored.returncode == 0 and key_rel in ignored.stdout, \
        ".gitignore 未覆盖 %s" % key_rel

    assert (REPO_ROOT / key_rel).exists(), "磁盘私钥文件被误删（应保留数据）"