# -*- coding: utf-8 -*-
"""经验回传：把本机沉淀的 FSTDD 经验整理为可提交到本仓库的经验包。

设计取舍（为什么不用 `fstdd experience share`）：
  上游 share 有两条路径，目标是硬编码的：
    1. `gh repo clone leonai42/stdd-experiences` 后直接 push —— 需写权限，普通使用者必然失败
    2. fallback：POST 到 `https://hzddyy.com/stdd/api/share-experience` —— 第三方服务器
  两者都不是「回传到本项目自己的仓库」，且后者属第三方数据外发。
  故本脚本自建回传链路，目标为本仓库的 experiences/ 目录。

安全底线：导出前强制脱敏（路径 / IP / 域名 / 凭证 / 邮箱），
  `--no-sanitize` 需显式指定，且会打印警告。

用法：
    python tools/share_experience.py --list              # 列出可回传的经验
    python tools/share_experience.py --export            # 导出到 experiences/
    python tools/share_experience.py --export --dry-run  # 预览，不写文件
    python tools/share_experience.py --export --from-archive   # 含归档 test-report 提取
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# 经验包回传目标仓库（可用环境变量 EXP_REPO 覆盖）
DEFAULT_EXP_REPO = os.environ.get("EXP_REPO", "2749817087qq/Fstdd-experiences")

# Git 远端基址。默认 GitHub；可用 FSTDD_GIT_BASE 覆盖，
# 例如自建 Git 服务、或本地/file:// 远端（离线联调与回归测试）。
GIT_BASE = os.environ.get("FSTDD_GIT_BASE", "https://github.com").rstrip("/")

# GitHub API 基址（fork / PR 用）。可用 FSTDD_API_BASE 覆盖，便于离线联调。
API_BASE = os.environ.get("FSTDD_API_BASE", "https://api.github.com").rstrip("/")


SCP_SYNTAX_RE = re.compile(r"^(?:[\w.-]+@)?[\w.-]+:(?!/)(?!//)\S+$")


def is_local_path(s: str) -> bool:
    """判断给定目标是否是一个「本地/网络文件系统路径」。

    覆盖形态：
      · POSIX 绝对路径        /home/x/repo.git
      · Windows 盘符路径      C:\\repos\\x.git  /  C:/repos/x.git
      · UNC 路径              \\\\server\\share\\x.git
    """
    if s.startswith(("/", "\\\\")):
        return True
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():   # C:\... 或 C:/...
        return True
    return False


def git_remote(repo: str, token: str = "") -> str:
    """按目标仓库构造可 clone/push 的远端地址。

    repo 允许四种形态：
      · 已是 URL(https/ssh/git/file) → 原样使用
      · 本地/网络文件系统路径        → 原样使用（离线联调、自建共享盘）
      · 本地基址 + owner/name        → 拼接（GIT_BASE 被设为本地路径时）
      · owner/name                   → 走 GIT_BASE（默认 GitHub）
    """
    if re.match(r"^(https?|ssh|git|file)://", repo) or is_local_path(repo):
        return repo
    if SCP_SYNTAX_RE.match(repo):                # git@host:owner/name
        return repo

    # GIT_BASE 本身是本地路径：直接把 owner/name 拼成本地远端，
    # 例如 FSTDD_GIT_BASE=C:/tmp/remotes → C:/tmp/remotes/owner/name.git
    if is_local_path(GIT_BASE):
        if GIT_BASE.startswith("\\\\"):          # UNC 基址：手工拼接，避免 Path 规范化出错
            return GIT_BASE.rstrip("\\/").replace("\\", "/") + "/" + repo + ".git"
        return str(Path(GIT_BASE) / (repo + ".git")).replace("\\", "/")

    auth = f"{token}@" if token else ""
    base = GIT_BASE.split("://", 1)
    scheme, host = (base[0], base[1]) if len(base) == 2 else ("https", GIT_BASE)
    return f"{scheme}://{auth}{host}/{repo}.git"

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = REPO_ROOT / ".fstdd" / "experiences"
ARCHIVE_DIR = REPO_ROOT / ".fstdd" / "archive"
OUT_DIR = REPO_ROOT / "experiences"


# ---------------------------------------------------------------------------
# 出站参数校验（2026-10-11 share-hardening）
# ---------------------------------------------------------------------------
# 合法形态：/home/ubuntu/fstdd-inbox、fstdd-hub、FSTDD003、user@host:/srv/x。
# 拒绝：空格 / ; / | / 反引号 / $ / ( ) / 重定向 / 换行 / 上跳段（..）。
_REMOTE_PATH_OK_RE = re.compile(r"[\w.@:/-]+")


def _validate_remote_path(value: str, label: str) -> tuple[bool, str]:
    """scp 目标参数白名单校验（防命令注入 + 路径上跳 + 选项注入）。

    `remote_dir` / `ssh_alias` / `FSTDD_NODE_ID` 三者均来自环境变量，
    原实现直接拼进 scp 目标字符串 ⇒ 命令注入面。用**白名单**而非转义：
    scp 的 `host:path` 语法中引号语义复杂，白名单更可验证。

    ⚠️ 前导 `-` 必须显式拒绝：白名单字符集含 `-`，若不拦，`FSTDD_SSH_ALIAS=-F/tmp/evil`
    会被 ssh/scp 当作**选项**解析（`-F` 可加载攻击者配置 ⇒ `ProxyCommand` 本地命令执行）。
    """
    v = value or ""
    if not v:
        return False, f"{label} 为空，已拒绝"
    if v.startswith("-"):
        return False, f"{label} 不得以 `-` 开头（会被 ssh/scp 当作选项），已拒绝：{v[:40]!r}"
    if not _REMOTE_PATH_OK_RE.fullmatch(v):
        return False, f"{label} 含非法字符，已拒绝（白名单 [\\w.@:/-]）：{v[:40]!r}"
    if v.startswith("..") or ".." in v.split("/"):
        return False, f"{label} 含上跳路径段（..），已拒绝：{v[:40]!r}"
    return True, ""


def _check_token_file_permissions(path: Path, label: str) -> None:
    """读取 token 文件前检查权限，过宽则告警（**仅告警，不阻断**）。

    EXP FSTDD005-EXP-20260918-C6：明文落盘到 0644 位置会导致全量吊销。
    直接拒绝读取会让既有用户突然无法工作 ⇒ 告警 + 文档引导是更安全的迁移路径。
    Windows 的 `st_mode` 不含 POSIX 权限位，直接跳过。
    """
    if os.name == "nt":
        return
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return
    if mode & 0o077:
        print("[WARN] %s 权限过宽（%o）：建议 `chmod 600 %s`"
              % (label, mode & 0o777, path))


# 关闭开关的持久配置（`share.silent.enabled`，缺省 true）
CONFIG_PATH = REPO_ROOT / ".fstdd" / "config.d" / "experience.yaml"


def _detect_test_runner() -> bool:
    """导入期判定一次：当前进程是否在测试运行时。

    pytest 的自身模块在收集阶段就留在 sys.modules 里，据此即可分流；
    生产运行时 sys.modules 无 pytest ⇒ 恒为 False，行为不变。
    `FSTDD_AUDIT_TEST=1` 供手工联调复用同一分流。
    """
    if os.environ.get("FSTDD_AUDIT_TEST", "").strip().lower() in {
            "1", "true", "yes", "on"}:
        return True
    return "pytest" in sys.modules


# 单一事实源（审计 F11）：判定只在 import 期做**一次**并固化。
# 若 `_under_test_runner()` 每次调用都重算，则可能出现「加载期判生产（AUDIT_PATH
# 指向 share-audit.yaml）、调用期判测试（函数返回 True）」的分叉 —— 一旦将来有人
# 改成按函数返回值决定落点，测试记录就会写进生产审计，正是本轮要消除的问题。
_UNDER_TEST = _detect_test_runner()


def _under_test_runner() -> bool:
    """是否在测试运行时 —— 恒等于导入期判定结果（见 `_UNDER_TEST`）。"""
    return _UNDER_TEST


# 回传审计记录：项目内可预期路径、append-only、属本机运行态（.gitignore 已排除）
#
# 测试运行时改写到 `.fstdd/share-audit.test.yaml`（2026-10-17 起）：
# 历史上 `tests/` 里的脱敏夹具（如 BAD-EXP-001.md）产生的记录会 append 进
# **生产**审计，长期把真实信号淹没 —— 实测累计 66 条测试污染记录。
# 导入期分流后，夹具记录落在 .test.yaml，生产审计只反映真实回传。
AUDIT_PATH = (REPO_ROOT / ".fstdd"
              / ("share-audit.test.yaml" if _under_test_runner()
                 else "share-audit.yaml"))

# 允许保留的公共域名（其余一律脱敏）
PUBLIC_DOMAINS = {
    "github.com", "gitee.com", "gitlab.com", "pypi.org", "python.org",
    "npmjs.com", "nodejs.org", "wikipedia.org", "stackoverflow.com",
}

# 文件扩展名：`README.md`、`design.md` 这类「单词.后缀」形式会被域名正则误伤，
# 必须显式排除，否则文档内容会被替换成 <DOMAIN> 而失去意义。
FILE_EXTS = {
    "md", "py", "txt", "json", "yaml", "yml", "sh", "ps1", "bat", "cmd",
    "exe", "log", "cfg", "ini", "toml", "rst", "html", "htm", "css", "js",
    "ts", "go", "rs", "java", "c", "h", "cpp", "hpp", "lock", "bak", "tmp",
    "png", "jpg", "jpeg", "gif", "svg", "pdf", "zip", "tar", "gz", "whl",
    # 运行时/系统文件：实测踩到 /tmp/t.sock 被当成域名替换成 <DOMAIN>
    "sock", "pid", "so", "dll", "dylib", "conf", "service", "socket",
}

# 已知域名后缀白名单 —— 域名脱敏采用「宁漏勿误」策略：TLD 不在本表中的一律保留原文。
#
# 原因：域名正则 `\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b` 会把「标识符.方法名」整类吃掉，
# 实测被误杀的包括 sqlite3.connect / conn.execute / time.monotonic / re.compile /
# rsplit / timezone 等公开技术标识符。这些内容被替换后，经验文档的技术内核会
# 整段失效（曾经把两篇经验的根因代码块和唯一修复方案全吃成 <DOMAIN>）。
#
# 判据（见 EXP-20260915-B3）：**漏脱敏可补救，误脱敏不可逆**。
# 内网域名由专门的规则（local/internal/corp/lan）先行处理，不依赖本表。
KNOWN_TLDS = {
    # 通用顶级域
    "com", "net", "org", "edu", "gov", "mil", "int",
    # 国别/地区
    "cn", "hk", "tw", "mo", "jp", "kr", "sg", "uk", "us", "de", "fr", "ru",
    "au", "ca", "in", "it", "es", "nl", "se", "ch",
    # 常用新通用域
    "io", "dev", "ai", "app", "co", "me", "info", "biz", "tech", "cloud",
    "xyz", "online", "site", "top", "shop", "store", "wiki", "blog", "work",
    # 组合国别域
    "com.cn", "net.cn", "org.cn", "co.uk", "com.hk",
    # 内网域（防御性保留，正常由内网域名规则先行命中）
    "local", "internal", "corp", "lan", "intranet",
}

# 脱敏规则：(正则, 替换, 说明)
SANITIZE_RULES: list[tuple[re.Pattern, str, str]] = [
    # 凭证类优先（避免被后续规则切碎）
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), "<TOKEN>", "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "<TOKEN>", "GitHub PAT"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "<TOKEN>", "API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<TOKEN>", "AWS key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
     "<PRIVATE_KEY>", "私钥"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}"), "Bearer <TOKEN>", "Bearer 令牌"),
    # 凭证类补充（2026-10-11 share-hardening）：三类高价值形态。
    # 注意：大小写不敏感一律走 `re.compile(pat, re.IGNORECASE)`，**绝不内联 `(?i)`** ——
    # 交付件正是把内联 (?i) 写进多段拼接串的中间，导致 Python 3.11+ import 即崩
    # （re.PatternError: global flags not at the start of the expression）。
    (re.compile(r"\baws_secret_access_key\b\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
                re.IGNORECASE),
     r"aws_secret_access_key=<AWS_SECRET>", "AWS Secret Access Key"),
    (re.compile(r"([?&](?:api[_-]?key|token|password|secret|access[_-]?token)=)"
                r"([^&\s\"'<>]+)", re.IGNORECASE),
     r"\1<REDACTED>", "URL 认证参数"),
    # SSH 私钥路径必须先于下方 POSIX 家目录规则（否则绝对路径会先被吞成 <PATH>）
    (re.compile(r"(?:~|/(?:home|Users|root)/[^\s/]+)?/\.ssh/"
                r"(?:id_rsa|id_ecdsa|id_ed25519|id_dsa|authorized_keys|known_hosts)\b"),
     "<SSH_KEY_PATH>", "SSH 私钥路径"),
    # 邮箱
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), "<EMAIL>", "邮箱"),
    # IPv4
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<IP>", "IP 地址"),
    # 内网/私有域名
    (re.compile(r"\b(?:[\w-]+\.)+(?:local|internal|corp|lan)\b"), "<DOMAIN>", "内网域名"),
    # Windows 绝对路径 MUST 排在 URL 之后：否则 `https://github.com/x/y`
    # 会被盘符规则从中间的 `s:/` 起吞成 `http<PATH>`，公共域名判定随之失效。
    (re.compile(r"[A-Za-z]:\\{1,2}(?:[^\s\"'`|<>]+\\{1,2})*[^\s\"'`|<>\\]*"), "<PATH>", "Windows 路径"),
    (re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:/(?:[^\s\"'`|<>/]+/)*[^\s\"'`|<>]*"), "<PATH>", "Windows 路径(POSIX 写法)"),
    # POSIX 家目录路径
    (re.compile(r"/(?:home|Users|root)/[^\s\"'`|<>)]+"), "<PATH>", "POSIX 路径"),
]


# 出站残余自检判据（第二道防线）——逐字复刻服务端拒收判据，并叠加凭证模式。
#
# 服务端（fstdd-inbox-server）判据：re.compile(r"/(?:home|Users)/[^\s/]+")，命中即拒。
# 上层 sanitize() 拦住之后，第二层「开没开」天然不可观测（EXP FSTDD005-EXP-20260918-C4），
# 故把判据抽为本模块常量，供测试**直接断言常量本身**。
#
# 2026-10-11 share-hardening：与 SANITIZE_RULES 的 3 条新规则**同源对齐**（EXP-2026-0013：
# 声明形态与实现必须覆盖同一组形态）。大小写不敏感走 `re.IGNORECASE` 参数，**绝不内联 `(?i)`**。
# 新增形态中凡「脱敏后会被替换成 `<占位符>`」的（目前是 URL 认证参数），一律带 `(?!<)` 负向前视，
# 否则脱敏后的 `?token=<REDACTED>` 会被误判为残余，导致正常条目在 stage 阶段被整条剔除；
# AWS Secret / SSH 路径两条因判据本身要求「40 位 base64」「/\.ssh/<具体文件名>」，
# 占位符天然不命中，无需前视（EXP-2026-0033）。
OUTBOUND_RESIDUAL_RE = re.compile(
    r"/(?:home|Users)/[^\s/]+"
    r"|\bgh[pousr]_[A-Za-z0-9]{16,}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
    r"|\bsk-[A-Za-z0-9]{20,}\b"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\bBearer\s+[A-Za-z0-9._\-]{20,}"
    r"|\baws_secret_access_key\b\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"
    r"|[?&](?:api[_-]?key|token|password|secret|access[_-]?token)=(?![<\s])[^&\s\"'<>]+"
    r"|(?:~|/(?:home|Users|root)/[^\s/]+)?/\.ssh/"
    r"(?:id_rsa|id_ecdsa|id_ed25519|id_dsa|authorized_keys|known_hosts)"
    # ── 2026-10-18 审计补齐（M1）：`SANITIZE_RULES` 能清、本判据此前抓不到的 4 类 ──
    #
    # `pre_staged=True` 时脱敏**动作**被跳过，本判据是唯一的内容防线；
    # 漏一类就等于该形态在静默回传路径上裸奔（实测含 `C:\Users\...` 的文件
    # 经真实 silent_share 出站）。补齐依据 = 「与 SANITIZE_RULES 同源对齐」。
    #
    # ⚠️ **通用外网域名不得加入**：`sanitize()` 故意保留 `PUBLIC_DOMAINS`
    #    （github.com / python.org / pypi.org…），加通用域名分支会把正常经验
    #    文档整条剔除 —— 误杀不可逆，宁可漏。
    #    故只补内网域名（local|internal|corp|lan），它们必被 sanitize 转成 <DOMAIN>。
    r"|[A-Za-z]:\\{1,2}(?:[^\s\"'`|<>]+\\{1,2})*[^\s\"'`|<>\\]*"      # Windows 反斜杠路径
    r"|(?<![A-Za-z0-9])[A-Za-z]:/(?:[^\s\"'`|<>/]+/)*[^\s\"'`|<>]*"     # Windows 正斜杠路径
    r"|\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"                                  # 邮箱
    r"|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"                          # IPv4
    r"|\b(?:[\w-]+\.)+(?:local|internal|corp|lan)\b",                   # 内网域名
    re.IGNORECASE,
)


def sanitize(text: str, enabled: bool = True) -> tuple[str, list[str]]:
    """返回 (脱敏后文本, 命中的规则说明)。"""
    if not enabled:
        return text, []
    hits: list[str] = []
    for pat, repl, label in SANITIZE_RULES:
        if pat.search(text):
            hits.append(label)
            text = pat.sub(repl, text)
    # 非白名单域名（须排除文件名，否则 README.md 之类会被误伤）
    def _dom(m: re.Match) -> str:
        raw = m.group(0)
        d = raw.lower()
        tld = d.rsplit(".", 1)[-1]
        if tld in FILE_EXTS:          # 形如 README.md / design.yaml
            return raw
        if d in PUBLIC_DOMAINS:
            return raw
        # 宁漏勿误：TLD 不在已知后缀表里的（sqlite3.connect / conn.execute /
        # time.monotonic 这类「标识符.方法名」）一律保留 —— 误脱敏不可逆。
        if tld not in KNOWN_TLDS:
            return raw
        hits.append("域名")
        return "<DOMAIN>"

    text = re.sub(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", _dom, text, flags=re.I)
    return text, sorted(set(hits))


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    fm_raw, body = text[3:end], text[end + 4:]
    fm: dict = {}
    for line in fm_raw.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("\"'")
    return fm, body.lstrip("\n")


def collect_local() -> list[dict]:
    """收集 .fstdd/experiences 下已沉淀的经验。

    ⚠️ 枚举口径必须是「任意 ``*.md``」（FSD-004）：V3.1.1 起新经验 ID 带
    installation_id 前缀（``WBCC-0803ADF7-EXP-2026-0001.md``），
    ``glob("EXP-*.md")`` 会把它们**全部漏掉** ⇒ 回传通道静默只推旧经验。
    """
    out = []
    if not EXP_DIR.exists():
        return out
    for f in sorted(p for p in EXP_DIR.glob("*.md") if not p.name.startswith(".")):
        fm, body = parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
        out.append({"id": fm.get("experience_id", f.stem), "fm": fm,
                    "body": body, "source": f.name})
    return out


def extract_from_archives() -> list[dict]:
    """从归档 change 的 test-report.md「过程中的问题与处理」章节提取经验。"""
    out = []
    if not ARCHIVE_DIR.exists():
        return out
    for tr in sorted(ARCHIVE_DIR.glob("*/test-report.md")):
        change = tr.parent.name
        text = tr.read_text(encoding="utf-8", errors="replace")
        # 定位「过程中的问题与处理」章节
        # 章节名存在变体（「过程中的问题与处理」/「过程中发现的问题与处理」），故放宽匹配
        m = re.search(r"\n##\s*[一二三四五六七八九十\d]*[、.]?\s*过程中[^\n]*问题与处理(.*?)(?=\n##\s|\Z)",
                      text, re.S)
        if not m:
            continue
        section = m.group(1)
        for sub in re.split(r"\n###\s+", section):
            sub = sub.strip()
            if not sub:
                continue
            title = sub.splitlines()[0].strip()
            body = "\n".join(sub.splitlines()[1:]).strip()
            if len(body) < 80:  # 过短的多为占位
                continue
            eid = "EXP-" + hashlib.sha1(f"{change}:{title}".encode()).hexdigest()[:8].upper()
            out.append({
                "id": eid,
                "fm": {
                    "experience_id": eid,
                    "category": "process_deviation",
                    "severity": "medium",
                    "occurrences": 1,
                    "source_change": change,
                    "title": title,
                },
                "body": f"### {title}\n\n{body}",
                "source": f"{change}/test-report.md",
            })
    return out


def render(entry: dict, sanitized: bool, hits: list[str]) -> str:
    fm = entry["fm"]
    lines = ["---"]
    for k in ("experience_id", "category", "severity", "occurrences",
              "source_change", "title"):
        if fm.get(k) not in (None, ""):
            lines.append(f"{k}: {fm[k]}")
    lines.append(f"exported_at: {datetime.date.today().isoformat()}")
    lines.append(f"sanitized: {'true' if sanitized else 'false'}")
    if hits:
        lines.append(f"sanitize_hits: [{', '.join(hits)}]")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + entry["body"].rstrip() + "\n"


def find_token() -> str:
    """凭证来源：环境变量 > 工作区约定的 token 文件。"""
    for env in ("GITHUB_TOKEN", "PUSH_TOKEN", "GH_TOKEN"):
        v = os.environ.get(env, "").strip()
        if v:
            return v
    cand = REPO_ROOT.parent / ".workbuddy-ai" / "tmp" / ".gh_token"
    if cand.exists():
        _check_token_file_permissions(cand, "GitHub token 文件")
        return cand.read_text(encoding="utf-8").strip()
    return ""


def inbox_url() -> str:
    """经验接收端点（我们自己的服务器）。

    用途：使用者**没有 GitHub 凭证**时回传经验。
    思路对齐上游 STDD 的 _share_via_api，但服务器是我们自己的，
    数据不外发给第三方；提交进「待审核池」，由维护者审核后同步进仓库。
    可用 FSTDD_INBOX_URL 覆盖（自建实例）。

    端点迁移（2026-09-23）：`http://43.134.236.80:8787` 的公网入口已永久关闭，
    改为经 443 反代的 `https://quanthub.ccreits.cn/inbox/api/share-experience`。
    切勿再直连 8787（公网不可达）。
    """
    return os.environ.get(
        "FSTDD_INBOX_URL", "https://quanthub.ccreits.cn/inbox/api/share-experience"
    ).rstrip("/")


def inbox_token() -> str:
    """回传凭证（2026-09-25 项②）：环境变量 > 约定文件。

    服务端 fstdd-inbox-server 校验 `Authorization: Bearer <token>`（恒定时间比较）；
    token 由服务端 tokens.json 按节点铸发（仅存 sha256），历史 P0 教训：
    明文落盘到 0644 位置会导致全量吊销——本函数只读 env 与 0600 约定文件，
    绝不打印、绝不写入任何日志或审计。
    """
    v = os.environ.get("FSTDD_INBOX_TOKEN", "").strip()
    if v:
        return v
    cand = REPO_ROOT.parent / ".fstdd-inbox-token"
    try:
        if cand.exists():
            _check_token_file_permissions(cand, "inbox token 文件")
            return cand.read_text(encoding="utf-8").strip()
    except OSError:  # noqa: BLE001
        pass
    return ""


# 批量提交参数（可用环境变量覆盖）
INBOX_BATCH_ITEMS = int(os.environ.get("FSTDD_INBOX_BATCH_ITEMS", "20"))
INBOX_BATCH_BYTES = int(os.environ.get("FSTDD_INBOX_BATCH_BYTES", str(1024 * 1024)))
INBOX_RETRY = int(os.environ.get("FSTDD_INBOX_RETRY", "4"))


# ---------------------------------------------------------------------------
# 可关闭：环境变量优先（临时/自动化），配置文件持久（长期选择）
# ---------------------------------------------------------------------------
_TRUTHY = {"1", "true", "yes", "on"}


def config_silent_enabled() -> bool:
    """读取 `.fstdd/config.d/experience.yaml` 的 `share.silent.enabled`，缺省 True。

    配置缺失 / 不可解析时**按开启处理**：默认行为由契约决定，不由文件是否存在决定。
    """
    try:
        import yaml
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        node = data.get("share") or {}
        silent = node.get("silent") or {}
        return bool(silent.get("enabled", True))
    except FileNotFoundError:
        return True
    except Exception:  # noqa: BLE001
        return True


def share_disabled() -> bool:
    """静默回传是否被关闭。`FSTDD_NO_SHARE` 优先，配置文件次之。"""
    if os.environ.get("FSTDD_NO_SHARE", "").strip().lower() in _TRUTHY:
        return True
    return not config_silent_enabled()


# ---------------------------------------------------------------------------
# 回传目标：锁定到本机自有云服务器目录（scp 直传，不依赖任何 token）
# ---------------------------------------------------------------------------
# 配置面 `.fstdd/config.d/experience.yaml` 的 share.silent 块：
#   transport : scp | inbox      首选通道（scp 失败自动降级另一条）
#   ssh_alias : fstdd-hub        ~/.ssh/config 的 Host 别名
#   inbox_dir : 远端落地目录
# 环境变量优先（FSTDD_TRANSPORT / FSTDD_SSH_ALIAS / FSTDD_INBOX_DIR），
# 便于 CI 与联调覆盖。
DEFAULT_SSH_ALIAS = "fstdd-hub"
DEFAULT_INBOX_DIR = "/home/ubuntu/fstdd-inbox"
DEFAULT_TRANSPORT = "scp"
# 合法取值。非法值不再静默按 scp 处理 —— 拼错 `endpoint`/`post` 会让首选通道
# 悄悄变成 scp，排查时无从察觉（2026-10-18 审计 F10）。
VALID_TRANSPORTS = ("scp", "inbox")


def _config_silent_block() -> dict:
    """读取 `share.silent` 子块；配置缺失 / 不可解析时按空块处理。"""
    try:
        import yaml
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        node = data.get("share") or {}
        return node.get("silent") or {}
    except FileNotFoundError:
        return {}
    except Exception:  # noqa: BLE001
        return {}


def ssh_alias() -> str:
    """scp 目标主机的 SSH 别名。环境变量 > 配置 > 缺省 fstdd-hub。"""
    return (os.environ.get("FSTDD_SSH_ALIAS", "").strip()
            or str(_config_silent_block().get("ssh_alias", ""))
            or DEFAULT_SSH_ALIAS)


def inbox_dir() -> str:
    """scp 远端落地目录。环境变量 > 配置 > 缺省 /home/ubuntu/fstdd-inbox。"""
    return (os.environ.get("FSTDD_INBOX_DIR", "").strip()
            or str(_config_silent_block().get("inbox_dir", ""))
            or DEFAULT_INBOX_DIR)


def preferred_transport() -> str:
    """首选通道：`scp`（缺省）或 `inbox`。环境变量 > 配置 > 缺省。

    无论取哪一档，`publish()` 都会在首选失败时自动降级到另一条，
    所以本值只影响**尝试顺序**，不影响最终可达性。

    非法值（如误写 `endpoint` / `post`）会**告警**后回落 `scp`，不再静默处理 ——
    静默回落的后果是「配置看起来生效了，实际没生效」，排查方向会被带偏（审计 F10）。
    """
    raw = (os.environ.get("FSTDD_TRANSPORT", "").strip().lower()
           or str(_config_silent_block().get("transport", "")).strip().lower()
           or DEFAULT_TRANSPORT)
    if raw not in VALID_TRANSPORTS:
        print("[WARN] transport=%r 非法（合法值：%s），已回落 %s"
              % (raw, " / ".join(VALID_TRANSPORTS), DEFAULT_TRANSPORT))
        return DEFAULT_TRANSPORT
    return raw


# ---------------------------------------------------------------------------
# 可审计：项目内 append-only 的 .fstdd/share-audit.yaml
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _scrub(text: str, secrets=()) -> str:
    """脱敏任意文本：先抹掉已知凭证，再走通用脱敏规则。

    审计记录里绝不能出现凭证明文 —— git 的报错信息会把带 token 的远端 URL
    原样回显，必须先按**实际 token 值**替换，再用通用规则兜底。
    """
    out = str(text or "")
    for s in secrets:
        if s:
            out = out.replace(s, "<TOKEN>")
    out, _ = sanitize(out, True)
    return out


def _append_locked(path: Path, lines: list[str]) -> None:
    """带**跨进程锁**的 append（2026-10-18 审计 M3）。

    背景：Windows 的 `O_APPEND` 语义是「seek 到末尾再写」，跨进程**非原子**。
    实测 2 进程各写 100 条丢 40 条（20%）、4/8 进程丢约 9%，且**无半行、无解析
    异常** —— 整条记录静默消失，比半行更难发现。而 `record_audit` 又把异常全吞，
    丢失完全不可见。

    POSIX 下 `O_APPEND` 是原子的，本函数退化为普通 append（不加锁）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(lines)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        locked = False
        if os.name == "nt":
            import msvcrt
            try:
                # 锁首字节：写前 seek(0) 只影响锁的起点，"a" 模式的写入恒在末尾
                f.seek(0, os.SEEK_SET)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                locked = True
            except OSError:
                locked = False      # 拿不到锁就退化，不能让审计写入卡住交付
        try:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        finally:
            if locked:
                try:
                    f.seek(0, os.SEEK_SET)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass


def record_audit(records: list[dict], secrets=()) -> None:
    """append-only 追加审计记录。

    每条记录落 时间 / 经验标识 / 回传目标 / 结果 / 原因（原因先脱敏），
    可选 `sent_count`（本次实际出站文件数，审计 M4）。
    **任何异常都吞掉** —— 审计写不进去也不得影响回传与交付（零阻塞）。
    """
    try:
        lines = []
        for r in records:
            rec = {
                "time": r.get("time") or _now(),
                "experience_id": r.get("experience_id") or "-",
                "target": r.get("target") or "-",
                "result": r.get("result") or "-",
                "reason": _scrub(r.get("reason", ""), secrets),
            }
            if r.get("sent_count") is not None:
                rec["sent_count"] = r.get("sent_count")
            try:
                import yaml
                lines.append("---\n" + yaml.safe_dump(
                    rec, allow_unicode=True, sort_keys=False,
                    default_flow_style=False))
            except ImportError:
                # JSON 是 YAML 的子集：无 PyYAML 时仍写出可被 safe_load_all 读取的记录
                import json
                lines.append("---\n" + json.dumps(rec, ensure_ascii=False) + "\n")
        if not lines:
            return
        _append_locked(AUDIT_PATH, lines)
    except Exception:  # noqa: BLE001
        pass


def prepare_entries(entries: list[dict], sanitize_on: bool):
    """渲染 + **强制脱敏**，返回 [(entry, 文本, 命中规则)]。

    显式路径与静默路径共用同一实现 —— 两条路径各写一遍脱敏，迟早会漂移，
    而静默路径上的漂移意味着使用者不知情地泄露数据。
    """
    prepared = []
    for e in entries:
        text = render(e, sanitize_on, [])
        clean, hits = sanitize(text, sanitize_on)
        clean = re.sub(r"^sanitized: .*$",
                       f"sanitized: {'true' if sanitize_on else 'false'}", clean, flags=re.M)
        if hits:
            clean = clean.replace("---\n\n", f"sanitize_hits: [{', '.join(hits)}]\n---\n\n", 1)
        prepared.append((e, clean, hits))
    return prepared


def export_files(out_dir: Path) -> list[Path]:
    """导出产物里的**经验文件**。

    注意：out_dir 里还有 README.md（索引）和 SUBMIT.md（回传指引），
    它们不是经验，不能提交给经验库。
    """
    skip = {"README.md", "SUBMIT.md"}
    return sorted(p for p in out_dir.glob("*.md") if p.name not in skip)


def _audit_skipped(skipped: list[str]) -> None:
    """把被出站校验剔除的条目写审计（target: stage / result: skipped）。

    「静默不出站」本身也是信息：使用者需要知道**少传了什么**。此前调用方把
    `stage_sanitized` 的 skipped 直接丢弃（`_skipped =`），只有审计里留一条，
    stdout 之外无从察觉（审计盲区 2）。
    """
    if not skipped:
        return
    for s in skipped:
        # 先脱敏再打印：残余命中片段可能是 token 原文（审计 D5-03）。
        # 落盘侧 record_audit 已有 _scrub，但 stdout 此前是裸的。
        print("      [skip] %s" % _scrub(s))
    record_audit(
        [{"time": _now(), "experience_id": s.split("：", 1)[0],
          "target": "stage", "result": "skipped", "reason": s}
         for s in skipped])


def _verify_outbound(out_dir: Path) -> tuple[list[Path], list[str]]:
    """出站**校验腿**：不脱敏，但必须过三道关。

    `pre_staged=True` 的调用方声称已自行脱敏，本函数负责**验证这个声称**：
      ① `export_files()` 口径 —— 排除 README.md / SUBMIT.md 与一切非 `*.md`；
      ② `OUTBOUND_RESIDUAL_RE` 残余自检 —— 命中即剔除（EXP FSTDD005-EXP-20260918-C1）；
      ③ frontmatter `sanitized: false` 拒绝 —— 文件自己声明未脱敏，就不许离机。

    为什么不能省（2026-10-18 审计 F1）：旧实现在 `pre_staged=True` 时直接把调用方
    目录交给 `_scp_dir`，而 `_scp_dir` 用 `iterdir()` 全量枚举 ⇒ ①②③ 全跳过。
    `silent_share()` 只写本轮文件、**不清空** `OUT_DIR`（= 活体经验库 `experiences/`），
    目录里的历史残留随之出站；审计还记成 `target: scp / result: success`，
    成功记录反而掩盖了泄露。
    """
    allowed: list[Path] = []
    skipped: list[str] = []
    for f in export_files(out_dir):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped.append("%s：读取失败 %s" % (f.name, exc))
            continue
        m = OUTBOUND_RESIDUAL_RE.search(text)
        if m:
            skipped.append("%s：残余敏感内容 %s" % (f.name, m.group(0)[:40]))
            continue
        if _declares_unsanitized(text):
            skipped.append("%s：自称未脱敏（sanitized: false），拒绝出站" % f.name)
            continue
        allowed.append(f)
    return allowed, skipped


def _declares_unsanitized(text: str) -> bool:
    """frontmatter 是否自称未脱敏。

    2026-10-18 审计 L1：原判据是裸正则 `^sanitized:\\s*false\\s*$`，只认
    「精确小写、无引号、行尾即结束」一种写法 —— 实测 9 种变体里 7 种绕过：
    `"false"` / `'false'` / `False` / `FALSE` / `no`（YAML 布尔）/ 带行内注释 /
    带缩进。内部写入方（`render()` / `--no-sanitize`）产出的都是精确形式，
    所以自产文件不受影响；但手工放入或外部工具生成的文件会漏判。
    改用 `parse_frontmatter()` 解析后取值，与文件读取路径口径一致。
    """
    fm, _body = parse_frontmatter(text)
    if not fm:
        return False
    val = fm.get("sanitized")
    if isinstance(val, bool):
        return val is False
    if isinstance(val, str):
        return val.strip().strip("\"'").lower() in {"false", "no", "off", "0"}
    return False


def _prepare_outbound(out_dir: Path, pre_staged: bool) -> tuple[Path | None, list[str]]:
    """产出**可出站目录** —— 四个出站包装器（scp / inbox / github / pr）共用的唯一入口。

    返回 `(目录, skipped)`；目录为 `None` 表示校验后无可出站文件。
    **无论哪条分支，返回的目录都由本函数创建、调用方负责 `finally` 清理**，
    绝不返回调用方目录本身。注意过滤口径是「**未脱敏 / 命中残余**」，不是
    「非本轮」—— `OUT_DIR` 里合法的历史经验仍会一并出站，这是既有语义
    （审计 L2 指出旧注释把两者混为一谈）。

    · `pre_staged=False` → `stage_sanitized()`：脱敏 + 过滤 + 残余自检
    · `pre_staged=True`  → 跳过脱敏**动作**（调用方已脱敏），但过滤 / 残余自检 /
      `sanitized: false` 拒绝照跑，通过者拷贝到独立临时目录
    """
    if not pre_staged:
        return stage_sanitized(out_dir)

    allowed, skipped = _verify_outbound(out_dir)
    _audit_skipped(skipped)
    if not allowed:
        return None, skipped
    verified_dir = Path(tempfile.mkdtemp(prefix="exp_verify_"))
    for f in allowed:
        shutil.copy2(f, verified_dir / f.name)
    return verified_dir, skipped


def stage_sanitized(out_dir: Path) -> tuple[Path, list[str]]:
    """把 out_dir 下的经验文件强制脱敏后写入**独立临时目录**（出站唯一拷贝源）。

    这是「出站不变量」：无论 out_dir 里是流水线产物还是手工放入的文件，
    离开本机前都必须经此收口。`--no-sanitize` 对出站无效（恒 True）——
    它是离开本机的动作，而导出脱敏只作用于本地可读产物。

    第二道防线：stage 后以 OUTBOUND_RESIDUAL_RE 自检，命中残余的条目**不进入 stage**，
    文件名与原因计入 skipped 并留审计痕迹（EXP FSTDD005-EXP-20260918-C1）。

    返回 (staged_dir, skipped)；调用方负责 `finally` 清理 staged_dir。
    """
    staged_dir = Path(tempfile.mkdtemp(prefix="exp_stage_"))
    skipped: list[str] = []
    for f in export_files(out_dir):
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped.append("%s：读取失败 %s" % (f.name, exc))
            continue
        clean, _hits = sanitize(raw, True)
        # 声明与实现一致（EXP-2026-0013）：出站内容确已脱敏，frontmatter 不得再自称 false
        clean = re.sub(r"^sanitized: .*$", "sanitized: true", clean, flags=re.M)
        m = OUTBOUND_RESIDUAL_RE.search(clean)
        if m:
            skipped.append("%s：残余敏感内容 %s" % (f.name, m.group(0)[:40]))
            continue
        (staged_dir / f.name).write_text(clean, encoding="utf-8", newline="\n")

    _audit_skipped(skipped)
    return staged_dir, skipped


def _chunk_experiences(files: list[Path], max_items: int,
                       max_bytes: int) -> list[list[Path]]:
    """按**条数**与**字节**双重上限分批。

    只按条数分批会在经验偏大时撞上服务端的单请求字节上限（413），
    所以两个维度都要卡。
    """
    chunks: list[list[Path]] = []
    cur: list[Path] = []
    cur_bytes = 0
    for f in files:
        try:
            size = f.stat().st_size
        except OSError:
            size = 0
        if cur and (len(cur) >= max_items or cur_bytes + size > max_bytes):
            chunks.append(cur)
            cur, cur_bytes = [], 0
        cur.append(f)
        cur_bytes += size
    if cur:
        chunks.append(cur)
    return chunks


def _post_experiences(endpoint: str, body: bytes,
                      max_retry: int) -> tuple[bool, object, int]:
    """POST 一批经验，暂时性失败按 Retry-After / 指数退避重试。

    返回 (是否成功, 响应 dict 或错误文案, 实际重试次数)。

    重试策略：
      · 429（限流）与 5xx —— 重试，优先采用服务端给的 Retry-After
      · 其余 4xx —— 确定性错误（格式不对、内容被拒），重试无意义，立即返回
    """
    import json
    import urllib.error
    import urllib.request

    delay = 2.0
    retried = 0
    last = "未知错误"

    for attempt in range(max_retry + 1):
        req = urllib.request.Request(endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "fstdd-share-experience")
        # 2026-09-25 项②：服务端（fstdd-inbox-server）已启用节点级鉴权——
        # 401=未知/未携带，403=已吊销。token 由服务端 tokens.json 按节点铸发
        # （sha256 存档，明文只交付节点），本工具只负责携带、不铸造。
        tok = inbox_token()
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return True, json.loads(r.read().decode("utf-8") or "{}"), retried
        except urllib.error.HTTPError as e:  # noqa: PERF203
            detail = ""
            try:
                detail = (json.loads(e.read().decode("utf-8", "replace") or "{}")
                          .get("error", ""))
            except Exception:  # noqa: BLE001
                pass
            last = "HTTP %d%s" % (e.code, (": " + detail) if detail else "")
            if e.code != 429 and e.code < 500:
                return False, last, retried
            wait = delay
            try:
                ra = e.headers.get("Retry-After") if e.headers else None
                if ra:
                    wait = max(1.0, float(ra))
            except (TypeError, ValueError):
                pass
            if attempt >= max_retry:
                return False, last, retried
            retried += 1
            print("      [retry] %s，%.0fs 后重试（第 %d/%d 次）"
                  % (last[:80], wait, retried, max_retry))
            time.sleep(wait)
            delay = min(delay * 2, 30)
        except Exception as exc:  # noqa: BLE001
            last = "端点不可达: %s" % str(exc)[:120]
            if attempt >= max_retry:
                return False, last, retried
            retried += 1
            print("      [retry] %s，%.0fs 后重试（第 %d/%d 次）"
                  % (last[:80], delay, retried, max_retry))
            time.sleep(delay)
            delay = min(delay * 2, 30)

    return False, last, retried


def publish_via_scp(out_dir: Path,
                    ssh_alias: str = DEFAULT_SSH_ALIAS,
                    remote_dir: str = DEFAULT_INBOX_DIR,
                    pre_staged: bool = False,
                    prepared: bool = False) -> tuple[bool, str]:
    """出站收口：先产出**校验通过的独立目录**，再走 scp。

    ``pre_staged=True``：调用方已自行脱敏（如 `silent_share()` 先经
    `prepare_entries()`）⇒ 跳过脱敏**动作**，但 `export_files()` 过滤、
    `OUTBOUND_RESIDUAL_RE` 残余自检、`sanitized: false` 拒绝**照跑**
    （见 `_prepare_outbound`，2026-10-18 审计 F1）。

    ``prepared=True``：`out_dir` **已经是** `_prepare_outbound()` 的产物
    （由 `publish()` 在入口做一次校验后传入）⇒ 直通传输，不再二次校验 / 二次拷贝。
    这是审计 M2 的修法：三档通道消费同一个已校验目录，剔除只审计一遍。
    调用方须保证该目录来自 `_prepare_outbound()`，不得传任意目录。
    """
    if prepared:
        return _scp_dir(out_dir, ssh_alias, remote_dir)
    send_dir, _skipped = _prepare_outbound(out_dir, pre_staged)
    if send_dir is None:
        return False, "出站校验后无可用文件（全部被过滤 / 命中残余 / 自称未脱敏）"
    try:
        return _scp_dir(send_dir, ssh_alias, remote_dir)
    finally:
        shutil.rmtree(send_dir, ignore_errors=True)


def _scp_dir(out_dir: Path,
             ssh_alias: str = "fstdd-hub",
             remote_dir: str = "/home/ubuntu/fstdd-inbox") -> tuple[bool, str]:
    """把经验包 scp 到云服务器 fstdd-inbox（最直接、最可靠的回传路径）。

    前提：本机已配置好 `ssh fstdd-hub`（.ssh/config Host 块 + 密钥已加载），
    远端 /home/ubuntu/fstdd-inbox/ 对 ubuntu 用户可写。

    与 GitHub/POST 两条路径的区别：
      - 不需要 token / API 凭证
      - 不依赖任何外部服务器或第三方服务
      - 纯 SSH + scp，跟 FSTDD 核心推送用的是同一条链路
      - 幂等：每次写到带时间戳的子目录，不覆盖之前的批次

    失败语义：SSH 不通 / 远端目录不可写 → 返回 (False, reason)，
      调用方应该降级到 publish_via_inbox 或 publish_via_pr。
    """
    # 0. 出站参数校验（必须在任何 subprocess 之前）——防命令注入
    node_id = os.environ.get("FSTDD_NODE_ID", "local")
    for _value, _label in ((ssh_alias, "ssh_alias"),
                           (remote_dir, "remote_dir"),
                           (node_id, "FSTDD_NODE_ID")):
        _ok, _err = _validate_remote_path(_value, _label)
        if not _ok:
            return False, _err

    # 1. 快速可达性检查（ssh -o ConnectTimeout=5 alias echo OK）
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", ssh_alias, "echo", "OK"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"SSH 不可达: {ssh_alias} — {(r.stderr or r.stdout).strip()[:120]}"

    # 2. 远端目录可写检查
    r = subprocess.run(
        ["ssh", ssh_alias,
         f"mkdir -p {remote_dir} && touch {remote_dir}/._write_probe_$$ && rm {remote_dir}/._write_probe_$$"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"远端目录不可写: {remote_dir} — {(r.stderr or r.stdout).strip()[:120]}"

    # 3. 构造批次子目录（FSTDD003-experiences-YYYYMMDD-HHMMSS）
    batch = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_dir = f"{remote_dir}/{node_id}-experiences-{batch}"

    # 4. scp 整个 out_dir（含 EXP-*.md）
    #
    # 显式枚举文件，不用 shell glob `dir/*`：Windows 的 scp 不展开通配符，
    # 会把 `dir/*` 当字面路径 stat ⇒ 失败；而批次目录已在远端建好，
    # 于是每次失败都在远端留下一个空目录（2026-10-17 实测今日远端 20+ 个）。
    # 同时用 as_posix() 换正斜杠 —— Windows 反斜杠会被 scp 当成转义符。
    files = sorted(p.as_posix() for p in out_dir.iterdir() if p.is_file())
    if not files:
        return False, f"out_dir 为空，无可回传文件: {out_dir}"

    # 选项注入防护（2026-10-18 审计 F6）：本函数已对 ssh_alias / remote_dir /
    # FSTDD_NODE_ID 做白名单校验，但**源文件名**此前没有任何校验。虽然 as_posix()
    # 产出的是绝对路径（不以 `-` 开头），一旦有人改成相对路径或传入手工构造的
    # 目录，`-oProxyCommand=...` 这类名字就会被 scp 当选项解析。
    # 双保险：① 显式拒绝 `-` 开头；② argv 用 `--` 终止选项解析（OpenSSH scp
    # 走 getopt，`--` 有效 —— 2026-10-18 实测 EXIT=0）。
    bad_names = [os.path.basename(f) for f in files if os.path.basename(f).startswith("-")]
    if bad_names:
        return False, ("源文件名以 `-` 开头，会被 scp 当作选项，已拒绝：%s"
                       % ", ".join(bad_names[:5]))

    r = subprocess.run(
        ["ssh", ssh_alias, f"mkdir -p {batch_dir}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"mkdir 失败: {batch_dir} — {(r.stderr or r.stdout).strip()[:120]}"

    r = subprocess.run(
        ["scp", "-r", "--", *files, f"{ssh_alias}:{batch_dir}/"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"scp 失败 — {(r.stderr or r.stdout).strip()[:120]}"

    # 5. 验证远端文件数
    r = subprocess.run(
        ["ssh", ssh_alias, f"ls {batch_dir}/*.md 2>/dev/null | wc -l"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    n = r.stdout.strip() or "?"
    print(f"[OK] 已 scp {n} 条经验 → {ssh_alias}:{batch_dir}")
    return True, ""


def publish_via_inbox(out_dir: Path, url: str,
                      pre_staged: bool = False,
                      prepared: bool = False) -> tuple[bool, str]:
    """出站收口：先产出**校验通过的独立目录**，再 POST。

    ``pre_staged=True``：调用方已自行脱敏，跳过脱敏**动作**但过滤 / 残余自检 /
    `sanitized: false` 拒绝照跑。与 `publish_via_scp` 完全对称（审计 F1）。

    ``prepared=True``：`out_dir` 已是 `_prepare_outbound()` 的产物 ⇒ 直通，
    不再二次校验 / 二次拷贝（审计 M2：三档消费同一目录，剔除只审计一遍）。
    """
    if prepared:
        return _post_inbox_dir(out_dir, url)
    send_dir, _skipped = _prepare_outbound(out_dir, pre_staged)
    if send_dir is None:
        return False, "出站校验后无可用文件（全部被过滤 / 命中残余 / 自称未脱敏）"
    try:
        return _post_inbox_dir(send_dir, url)
    finally:
        shutil.rmtree(send_dir, ignore_errors=True)


def _post_inbox_dir(out_dir: Path, url: str) -> tuple[bool, str]:
    """把经验**分批** POST 到接收端点（无需任何账号/凭证）。

    此前是逐条提交：提交 N 条 = N 次请求，服务端一旦按请求数限流，
    必然随经验条数线性撞墙；且首个异常就 return False，剩余全部放弃。
    现在改为：
      · 按条数 + 字节双重上限分批（默认 20 条 / 1 MB）
      · 429 / 5xx 按 Retry-After 与指数退避重试
      · 单批失败只影响该批，其余批次照常提交
    """
    import json

    files = export_files(out_dir)
    if not files:
        return False, "没有可提交的经验文件"

    # 幂等拼接（2026-09-25 审计修复）：inbox_url() 的约定是返回**完整 endpoint**
    # （含 /api/share-experience，见 upstream test_inbox_endpoint.py:748 的断言），
    # 但历史实现按旧 8787 base 语义又拼了一次路径，导致 quanthub 端点双重拼接 → 404。
    # 现兼容两种形态：base（如 https://host/inbox）或完整 endpoint 均可。
    base = url.rstrip("/")
    endpoint = (base if base.endswith("/api/share-experience")
                else base + "/api/share-experience")
    chunks = _chunk_experiences(files, INBOX_BATCH_ITEMS, INBOX_BATCH_BYTES)
    print("      分批提交：%d 条 -> %d 批（每批 <= %d 条 / <= %d KB）"
          % (len(files), len(chunks), INBOX_BATCH_ITEMS, INBOX_BATCH_BYTES // 1024))

    ok_n = 0
    bad: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        items = []
        for f in chunk:
            try:
                items.append({"experience_id": f.stem,
                              "content": f.read_text(encoding="utf-8"),
                              "author": ""})
            except OSError as exc:
                bad.append("%s：读取失败 %s" % (f.stem, exc))
        if not items:
            continue

        body = json.dumps({"experiences": items}, ensure_ascii=False).encode("utf-8")
        ok, res, _ = _post_experiences(endpoint, body, INBOX_RETRY)
        if not ok:
            bad.append("第 %d/%d 批（%d 条）：%s" % (i, len(chunks), len(items), res))
            continue
        if not isinstance(res, dict) or not res.get("success"):
            bad.append("第 %d/%d 批：服务端未确认" % (i, len(chunks)))
            continue

        ok_n += int(res.get("accepted", len(items)) or 0)
        for err in (res.get("errors") or []):
            bad.append("%s：%s" % (err.get("experience_id", "?"),
                                   err.get("error", "被服务端拒绝")))
        if len(chunks) > 1:
            print("      [%d/%d] 累计已接收 %d 条" % (i, len(chunks), ok_n))

    if ok_n:
        print("[OK] 已提交 %d/%d 条经验到接收端点（待维护者审核）"
              % (ok_n, len(files)))
    if bad:
        print("      以下 %d 项未成功：" % len(bad))
        for b in bad[:10]:
            print("        - %s" % b)
        if len(bad) > 10:
            print("        ...（其余 %d 项省略）" % (len(bad) - 10))

    if ok_n == 0:
        return False, "全部提交失败：" + (bad[0] if bad else "未知原因")
    if bad:
        return True, "部分失败：成功 %d/%d 条，详见上方清单" % (ok_n, len(files))
    return True, ""


def _gh_api(method: str, path: str, token: str, payload=None) -> dict:
    """极简 GitHub API 调用（用标准库，避免新增 requests 依赖）。"""
    import json
    import urllib.error
    import urllib.request

    url = API_BASE + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "stdd-experience-share")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:  # noqa: BLE001
        return {"__error__": -1, "__body__": str(e)[:300]}


def publish_via_pr(out_dir: Path, repo: str, token: str, dry_run: bool = False,
                   pre_staged: bool = False) -> bool:
    """出站收口：先产出**校验通过的独立目录**，再走 fork+PR。

    与另外三个包装器统一（2026-10-18 审计 F1 同类暴露面）：`pre_staged=True` 时
    跳过脱敏动作，但过滤 / 残余自检 / `sanitized: false` 拒绝照跑。
    """
    staged_dir, _skipped = _prepare_outbound(out_dir, pre_staged)
    if staged_dir is None:
        print("[FAIL] 出站校验后无可用文件，跳过 PR")
        return False
    try:
        return _pr_dir(staged_dir, repo, token, dry_run)
    finally:
        shutil.rmtree(staged_dir, ignore_errors=True)


def _pr_dir(out_dir: Path, repo: str, token: str, dry_run: bool = False) -> bool:
    """自动 fork → 推送到 fork → 创建 Pull Request。

    适用对象：没有目标仓库写权限的贡献者（即绝大多数使用者）。
    用的是**使用者自己的 token**，我们不持有也不需要他们的凭证；
    提交以 PR 形式进入，由维护者审核后合并 —— 这是 GitHub 的标准贡献流程。
    """
    owner, name = repo.split("/", 1)

    me = _gh_api("GET", "/user", token)
    login = me.get("login")
    if not login:
        print(f"[FAIL] 无法获取 GitHub 身份：{me.get('__body__', me)}")
        return False
    print(f"      身份: {login}")

    if dry_run:
        print(f"[dry-run] 将 fork {repo} → {login}/{name}，推送后创建 PR")
        return True

    # 1) fork（已存在时 API 返回 202/403，都继续尝试 clone）
    fr = _gh_api("POST", f"/repos/{repo}/forks", token, {})
    if "__error__" in fr and fr["__error__"] not in (202, 403, 422):
        print(f"[FAIL] fork 失败: {fr.get('__body__')}")
        return False

    # fork 是异步的，轮询等待其可克隆
    fork_url = git_remote(f"{login}/{name}", token)
    deadline = time.time() + 45
    cloned = False
    tmp = Path(tempfile.mkdtemp(prefix="exp_pr_"))
    try:
        while time.time() < deadline:
            r = subprocess.run(["git", "clone", "-q", fork_url, str(tmp / "repo")],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                cloned = True
                break
            time.sleep(5)
        if not cloned:
            print("[FAIL] fork 后仍无法克隆（可能 fork 尚未就绪，稍后重试即可）")
            return False

        repo_dir = tmp / "repo"
        branch = f"experience-{datetime.date.today().isoformat()}"
        subprocess.run(["git", "checkout", "-q", "-b", branch],
                       cwd=str(repo_dir), capture_output=True)

        dst = repo_dir / "experiences"
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        # 只复制经验文件：README.md（索引）与 SUBMIT.md（回传指引）不是经验，
        # 推进经验库会污染仓库（此前踩过：误提交说明文件）。
        for f in export_files(out_dir):
            shutil.copy2(f, dst / f.name)
            n += 1

        subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), capture_output=True)
        r = subprocess.run(
            ["git", "-c", "user.name=stdd-bot",
             "-c", "user.email=stdd-bot@users.noreply.github.com",
             "commit", "-m", f"experience: add {n} entries ({datetime.date.today()})"],
            cwd=str(repo_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        combined = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 and "nothing to commit" not in combined:
            print(f"[FAIL] commit 失败: {combined[:200]}")
            return False

        r = subprocess.run(["git", "push", "-q", "-u", "origin", branch],
                           cwd=str(repo_dir), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[FAIL] push 到 fork 失败: {_scrub((r.stderr or '')[:200], (token,))}")
            return False
        print(f"      已推送到 {login}/{name} 分支 {branch}")

        # 默认分支必须查询而非硬编码：实测目标仓库默认分支为 main，
        # 而脚本原本写死 master，PR 会因 base 不存在而创建失败。
        info = _gh_api("GET", f"/repos/{repo}", token)
        base_branch = info.get("default_branch") or "main"

        pr = _gh_api("POST", f"/repos/{repo}/pulls", token, {
            "title": f"experience: {n} 条经验（{datetime.date.today()}）",
            "head": f"{login}:{branch}",
            "base": base_branch,
            "body": (f"由 `tools/share_experience.py` 自动提交，共 {n} 条脱敏经验。\n\n"
                     f"来源：{login} 的本机经验库。提交前已强制脱敏"
                     f"（路径 / IP / 域名 / 凭证 / 邮箱）。"),
        })
        if "__error__" in pr:
            print(f"[FAIL] 创建 PR 失败: {pr.get('__body__')}")
            return False
        print(f"[OK] 已创建 Pull Request #{pr.get('number')}: {pr.get('html_url')}")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


PERMISSION_HINTS = ("403", "permission", "denied", "forbidden", "not permitted",
                    "write access", "could not read username")


def is_permission_error(msg: str) -> bool:
    return any(h in (msg or "").lower() for h in PERMISSION_HINTS)


def _publish_github(out_dir: Path, repo: str, token: str,
                    pre_staged: bool = False,
                    prepared: bool = False) -> tuple[bool, str]:
    """GitHub 通道：clone → 拷贝校验通过的产物 → commit → push（需 token）。

    fork+PR 降级不在这里做（`publish_via_pr`），由调用方按失败原因决定。

    2026-10-18 审计 F1：旧实现在 `pre_staged=True` 时直接拷贝**调用方目录**，
    绕开了残余自检（只靠 `export_files()` 过滤 README/SUBMIT）。现统一走
    `_prepare_outbound()`，三条出站通道共享同一收口。

    ``prepared=True``：`out_dir` 已是 `_prepare_outbound()` 的产物 ⇒ 直通，
    且**不清理**该目录（所有权在 `publish()`）。
    """
    if prepared:
        staged_dir, own_dir = Path(out_dir), False
    else:
        staged_dir, _skipped = _prepare_outbound(out_dir, pre_staged)
        if staged_dir is None:
            return False, "出站校验后无可用文件（全部被过滤 / 命中残余 / 自称未脱敏）"
        own_dir = True
    tmp = Path(tempfile.mkdtemp(prefix="exp_publish_"))
    try:
        url = git_remote(repo, token)
        r = subprocess.run(["git", "clone", "-q", url, str(tmp / "repo")],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return False, (r.stderr or "")[:300]

        repo_dir = tmp / "repo"
        dst = repo_dir / "experiences"
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in export_files(staged_dir):
            shutil.copy2(f, dst / f.name)
            n += 1

        subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), capture_output=True)
        r = subprocess.run(
            ["git", "-c", "user.name=stdd-bot",
             "-c", "user.email=stdd-bot@users.noreply.github.com",
             "commit", "-m", f"experience: sync {n} entries ({datetime.date.today()})"],
            cwd=str(repo_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        combined = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 and "nothing to commit" not in combined:
            return False, combined[:300]
        if "nothing to commit" in combined:
            print(f"[OK] GitHub 无变化，远端已是最新（{n} 条经验）")
            return True, ""

        r = subprocess.run(["git", "push", "-q"], cwd=str(repo_dir),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return False, (r.stderr or "")[:300]
        print(f"[OK] 已推送到 GitHub {n} 条经验 → {git_remote(repo)}")
        return True, ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # 只在**本函数自己**产出 staged_dir 时清理；prepared=True 时目录归
        # `publish()` 所有，删了会让后续通道与调用方拿到空目录。
        if own_dir:
            shutil.rmtree(staged_dir, ignore_errors=True)


# publish() 最近一次**实际**使用的通道名（`scp` / `github` / `endpoint`）。
# silent_share() 据此如实写审计 —— 否则审计只能记调用方**预设**的通道名，
# 旧实现正是这样把「scp 已成功」记成「endpoint 401 失败」。
# 故意做成模块级变量而非返回值：保持 `publish()` 签名不变，既有调用方与
# 测试替身（fake_publish）无需改动即可继续工作；被整体替换 publish() 时该值
# 不会被写入，调用方自动回落到预设通道名。
PUBLISH_LAST_CHANNEL = ""

# publish() 最近一次**实际出站的文件数**（审计 M4）。
# 此前审计只按本轮 `collect_local()` 的 id 记账 ⇒ 30 条历史 + 1 条新增实际送出
# 31 个文件，审计只留 1 条 success，回答不了「这次到底送出了什么」。
# 与 PUBLISH_LAST_CHANNEL 同样做成模块级：不破坏 `publish()` 签名与测试替身。
PUBLISH_SENT_COUNT = 0


def publish(out_dir: Path, repo: str, token: str = "",
            pre_staged: bool = False) -> tuple[bool, str]:
    """把导出的经验包推送到目标（scp / GitHub / inbox endpoint 三档降级）。

    默认优先级：
      1. scp 到自有云服务器目录 — 不需 token、最可靠、跟核心推送同链路
      2. GitHub 直推 — 需 token（fork+PR 降级由调用方处理）
      3. inbox POST（自建 endpoint） — 需服务端节点级 token

    `share.silent.transport: inbox` 可把第 3 档提到第 1 档。无论取哪一档，
    首选失败都自动降级到其余通道，故该配置只影响**尝试顺序**。

    旧调用（传 token 且希望直推 GitHub）不受影响。

    ``pre_staged=True``：调用方**已自行脱敏**（如 `silent_share()` 先经
    `prepare_entries()`），故跳过脱敏**动作**；但过滤 / 残余自检 / `sanitized: false`
    拒绝仍由包装器内的 `_prepare_outbound()` 执行（2026-10-18 审计 F1）。默认 False。

    成功后（或全失败时记最后尝试的那一档）写入模块级 `PUBLISH_LAST_CHANNEL`；
    `PUBLISH_SENT_COUNT` 记本次**实际出站文件数**（审计 M4：此前 30 条历史 + 1 条新增
    送出 31 个文件，审计只记 1 条 success，回答不了「送出了什么」）。
    """
    global PUBLISH_LAST_CHANNEL, PUBLISH_SENT_COUNT
    PUBLISH_LAST_CHANNEL = ""
    PUBLISH_SENT_COUNT = 0
    alias = ssh_alias()
    remote_dir = inbox_dir()

    # ── 单次校验 + 单次审计（审计 M2）──────────────────────────────────
    # 此前每一档各调一次 `_prepare_outbound()`，三档全试 ⇒ 同一批被剔除文件
    # 写 3 遍审计（实测 4 条变 12 条），并重复校验 3 次。
    # 现改为在入口做**一次**，三档消费同一个已校验目录：
    #   · 审计只写一遍（内层对已清洁目录再校验时 skipped 恒空，不产生记录）
    #   · 文件数在这里一次算准，供 success 记录使用
    send_dir, _skipped = _prepare_outbound(out_dir, pre_staged)
    if send_dir is None:
        return False, "出站校验后无可用文件（全部被过滤 / 命中残余 / 自称未脱敏）"
    PUBLISH_SENT_COUNT = sum(1 for p in send_dir.iterdir() if p.is_file())
    try:
        # prepared=True：send_dir 已由入口的 _prepare_outbound() 校验过，
        # 三档直通传输，不二次校验 / 不二次拷贝 / 不重复审计（审计 M2）。
        def _scp() -> tuple[bool, str]:
            return publish_via_scp(send_dir, alias, remote_dir, prepared=True)

        def _inbox() -> tuple[bool, str]:
            return publish_via_inbox(send_dir, inbox_url(), prepared=True)

        _gh = lambda: _publish_github(send_dir, repo, token, prepared=True)  # noqa: E731
        steps = ([("endpoint", _inbox), ("github", _gh), ("scp", _scp)]
                 if preferred_transport() == "inbox"
                 else [("scp", _scp), ("github", _gh), ("endpoint", _inbox)])

        last = "无可用的回传通道"
        last_step = ""
        for name, fn in steps:
            if name == "github" and not token:
                continue
            last_step = name
            # 通道函数必须**不得抛异常**才能保证降级语义（审计 F3）：
            # 此前 `ok, reason = fn()` 裸调用，scp 缺失（FileNotFoundError）或网络
            # OSError 会直接穿透 publish()，把 github / endpoint 两档一起跳过 ——
            # 三档降级的可用性收益归零。这里把异常收敛成「该档失败」的 reason。
            try:
                ok, reason = fn()
            except Exception as exc:  # noqa: BLE001 —— 通道异常一律降级，不得逃逸
                ok, reason = False, "通道异常 %s: %s" % (type(exc).__name__, str(exc)[:160])
            if ok:
                PUBLISH_LAST_CHANNEL = name
                return True, reason
            last = reason or "未知错误"
            # reason 可能带 token：git 失败时会把 https://x-access-token:<TOKEN>@host
            # 原样写进 stderr，而 `[:40]` 对 40 字符的 ghp_ token 等于没截（审计 D5-03）。
            print(f"[降级] {name} 不可用（{_scrub(last, (token,))}），尝试其他通道...")
        # 全失败时记**最后尝试**的通道 —— 审计据此可判「死在哪一档」，
        # 而不是笼统记成调用方预设的首选通道。
        PUBLISH_LAST_CHANNEL = last_step
        return False, last
    finally:
        shutil.rmtree(send_dir, ignore_errors=True)


def silent_share(args) -> int:
    """静默回传入口（Phase 4 skill 调用）：无交互、零阻塞、必写审计。

    与显式 `--publish` 的**唯一**区别是失败语义：这里无论回传成功与否都返回 0，
    因为回传是附加价值 —— 不该让「经验没传上去」变成「变更没交付」。
    显式命令的失败仍返回非零（见 `main()` 尾部），那是使用者主动发起的操作。

    静默路径上脱敏不可绕过：`--no-sanitize` 在此无效。
    """
    global PUBLISH_LAST_CHANNEL
    target = "none"
    ids: list[str] = []
    try:
        if share_disabled():
            print("经验回传已跳过：静默回传开关已关闭"
                  "（FSTDD_NO_SHARE / share.silent.enabled=false）")
            record_audit([{"time": _now(), "experience_id": "-", "target": "none",
                           "result": "skipped", "reason": "回传开关已关闭"}])
            return 0

        entries = collect_local()
        if args.from_archive:
            entries += extract_from_archives()
        if not entries:
            print("本次无新增经验，跳过回传")
            return 0

        if args.no_sanitize:
            print("静默回传强制脱敏：忽略 --no-sanitize")
        prepared = prepare_entries(entries, True)
        ids = [e["id"] for e, _, _ in prepared]

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for e, content, _ in prepared:
            (OUT_DIR / f"{e['id']}.md").write_text(
                content, encoding="utf-8", newline="\n")

        token = find_token()
        # 本轮写入的文件已过 prepare_entries(True) 脱敏 ⇒ pre_staged=True：
        # 跳过二次脱敏（避免误伤占位符），但**不跳过出站校验**。
        #
        # ⚠️ 2026-10-18 审计 F1 修正：原注释写「publish() 内部各出站入口仍各自
        # stage_sanitized —— 脱敏不可绕过」，那句话在 pre_staged=True 路径上是假的
        # （包装器当时直接 `return _scp_dir(out_dir, ...)`）。更关键的是 OUT_DIR
        # 就是**活体经验库** `experiences/`，本函数只写本轮文件、不清空目录，
        # 所以目录里可能有历史残留（`--no-sanitize` 产物、手工放入、旧 EXP-*.md），
        # 旧实现会把它们连同 README.md / SUBMIT.md 一起 scp 出站。
        # 现由 `_prepare_outbound()` 统一收口：过滤 + 残余自检 + `sanitized: false`
        # 拒绝照跑，通过者拷到独立临时目录再出站。
        PUBLISH_LAST_CHANNEL = ""
        if token:
            target = "github"
            ok, reason = publish(OUT_DIR, args.repo, token, pre_staged=True)
            if not ok and not args.direct and is_permission_error(reason):
                print("无写权限，降级为 fork + Pull Request")
                # 这里**故意不传** pre_staged：PR 是最后一档兜底，宁可多一次
                # 完整脱敏（sanitize 对 <TOKEN>/<PATH> 等占位符幂等，不会误伤）。
                ok = publish_via_pr(OUT_DIR, args.repo, token)
                if ok:
                    reason = ""      # 降级成功：清掉上游失败原因，避免审计写成「success + 403」
                    PUBLISH_LAST_CHANNEL = "github"
        else:
            # 无 GitHub 凭证：仍走 publish() 的三档降级 —— scp 直传自有云服务器目录
            # （不需任何 token）优先，inbox POST 兜底。
            # 2026-10-17 修正：旧实现此处直调 publish_via_inbox()，绕过了 publish() 的
            # scp 优先档，导致审计连续 14 天记 2164 次 endpoint 401，而 scp 批次
            # 其实一直在正常落盘（远端 fstdd-inbox 可见 local-experiences-* 批次）。
            target = "scp"
            ok, reason = publish(OUT_DIR, args.repo, "", pre_staged=True)
        if PUBLISH_LAST_CHANNEL:
            target = PUBLISH_LAST_CHANNEL   # 审计如实记录**实际**通道，不再猜

        print("经验静默回传: %s（目标 %s）" % ("成功" if ok else "失败", target))
        if not ok:
            print("回传失败不影响交付（零阻塞）；详见 %s" % AUDIT_PATH)
        # 每条记录带上本次**实际出站文件数**（审计 M4）：`ids` 只是本轮新增，
        # 而 `publish()` 送出的是「OUT_DIR 里所有通过出站校验的文件」——
        # 两者不等时，审计读者会以为只传了 `len(ids)` 条。
        record_audit(
            [{"time": _now(), "experience_id": i, "target": target,
              "result": "success" if ok else "failure", "reason": reason or "",
              "sent_count": PUBLISH_SENT_COUNT}
             for i in ids],
            secrets=(token,),
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print("经验静默回传异常，已忽略（不影响交付）：%s" % str(exc)[:200])
        try:
            record_audit(
                [{"time": _now(), "experience_id": i, "target": target,
                  "result": "failure", "reason": "异常: %s" % str(exc)[:200],
                  "sent_count": PUBLISH_SENT_COUNT}
                 for i in (ids or ["-"])],
            )
        except Exception:  # noqa: BLE001
            pass
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="列出可回传的经验")
    ap.add_argument("--export", action="store_true", help="导出到 experiences/")
    ap.add_argument("--from-archive", action="store_true", help="同时从归档 test-report 提取")
    ap.add_argument("--dry-run", action="store_true", help="预览，不写文件")
    ap.add_argument("--no-sanitize", action="store_true", help="不脱敏（危险）")
    ap.add_argument("--publish", action="store_true",
                    help="导出后自动回传到经验库仓库"
                         "（维护者直推；其他贡献者自动 fork + 提 PR）")
    ap.add_argument("--direct", action="store_true",
                    help="强制直接推送（默认按 GitHub 身份自动选择）")
    ap.add_argument("--silent", action="store_true",
                    help="静默回传：无交互、失败不阻断交付（退出码恒为 0）、必写审计；"
                         "供 Phase 4 skill 自动调用。脱敏在此路径上不可绕过")
    ap.add_argument("--repo", default=os.environ.get("EXP_REPO", DEFAULT_EXP_REPO),
                    help=f"经验库仓库（默认 {DEFAULT_EXP_REPO}）")
    args = ap.parse_args()

    if args.silent:
        return silent_share(args)

    entries = collect_local()
    if args.from_archive:
        entries += extract_from_archives()

    if not entries:
        print("没有可回传的经验。")
        print("  · 本地经验库为空（.fstdd/experiences/ 下无 EXP-*.md）")
        print("  · 加 --from-archive 可从已归档 change 的 test-report 提取")
        return 0

    sanitize_on = not args.no_sanitize
    if not sanitize_on:
        print("⚠️  已禁用脱敏：导出的内容可能包含路径 / IP / 域名 / 凭证，请自行检查后再提交。")

    print("=" * 62)
    print(f"经验回传准备 —— 共 {len(entries)} 条")
    print("=" * 62)

    prepared = prepare_entries(entries, sanitize_on)
    for e, _, hits in prepared:
        flag = f"脱敏命中: {', '.join(hits)}" if hits else "无敏感内容命中"
        print(f"  [{e['id']}] {e['fm'].get('title', e['source'])}")
        print(f"      {flag}")

    if args.list or not args.export:
        print()
        print(f"导出目标: {OUT_DIR.relative_to(REPO_ROOT)}/")
        print("加 --export 执行导出")
        return 0

    if args.dry_run:
        print()
        print("[dry-run] 未写入任何文件")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for e, content, _ in prepared:
        dest = OUT_DIR / f"{e['id']}.md"
        dest.write_text(content, encoding="utf-8", newline="\n")
        written += 1

    # 索引
    idx = ["# 经验库（对外回传）", "",
           f"> 由 `tools/share_experience.py` 导出，共 {written} 条，"
           f"导出时间 {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC", "",
           "| ID | 标题 | 文件 |", "|---|---|---|"]
    for e, _, _ in prepared:
        # 链接必须指向**导出后的文件名**（{id}.md，可能带归属前缀），
        # 不能用 e['source']（源文件名）—— 两者不一致会让索引链接全断。
        idx.append(f"| {e['id']} | {e['fm'].get('title', '-')} | [{e['id']}.md](./{e['id']}.md) |")
    (OUT_DIR / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8", newline="\n")

    # 回传指引（面向 AI Agent）。
    # 演进过程：最早只提示「请设置 GITHUB_TOKEN」，没有 token 的使用者以为无法回传；
    # 中途曾给 AI 网页操作步骤（D哥 指出这是错的——AI 点不了 Fork、拖不了文件）；
    # 现在改为**无凭证也能自动回传**：降级到我们自己的接收端点，AI 一条命令即可完成。
    # 只有「手工 fork + PR」这一条路需要人类操作浏览器。
    _submit = chr(10).join([
        "# 如何回传这些经验",
        "",
        "> **给 AI Agent 的说明**：「方式一」你**可以直接执行，不需要任何凭证**。",
        "> 「方式三」需要人类操作浏览器，**你做不到，不要尝试、也不要向用户承诺**。",
        "",
        "## 方式一：一条命令自动回传（无需任何账号，推荐）",
        "",
        "```bash",
        "python tools/share_experience.py --export --publish",
        "```",
        "",
        "脚本自动选择通道，三档都是自动的（首选失败自动降级下一档）：",
        "",
        "1. **scp 直传自有云服务器目录**（缺省首选，**不需要任何 token**）；",
        "2. **有 GitHub 凭证**（`GITHUB_TOKEN` 等）→ 推送到经验库；",
        "   若没有写权限，自动 fork + 提 Pull Request（标准贡献流程）。",
        "3. **兜底** → 回传到 FSTDD 接收端点，进入待审核池，",
        "   由维护者审核后同步进 GitHub 仓库。",
        "",
        "三档都无需手工操作。提交失败会自动按服务端的 `Retry-After` 退避重试。",
        "",
        "## 方式二：只导出到本地（不发任何网络请求）",
        "",
        "```bash",
        "python tools/share_experience.py --export",
        "```",
        "",
        "导出到 `experiences/`，文件留在本地，不做回传。",
        "",
        "## 方式三：手工 fork + PR（需要人类操作浏览器）",
        "",
        "```bash",
        "python tools/share_experience.py --export",
        "```",
        "",
        "然后由**人类**在浏览器里：fork 经验库 → 把导出的经验文件放进 `experiences/`",
        "→ 发起 Pull Request。**这一步 AI 做不到**，不要向用户承诺可以代做。",
        "",
        "---",
        "",
        "## 想改用 GitHub 通道（可选）",
        "",
        "如果你希望提交以**你自己的 GitHub 身份**进入（而不是走接收端点），",
        "配置一个 Fine-grained token 即可，只需 Contents 与 Pull requests 的读写权限：",
        "",
        "```bash",
        "export GITHUB_TOKEN='<你的 token>'",
        "python tools/share_experience.py --export --publish",
        "```",
        "",
        "**token 属于使用者，本工具不上传、不转存、不写入仓库。**",
        "",
    ])
    (OUT_DIR / "SUBMIT.md").write_text(_submit, encoding="utf-8", newline="\n")

    print()
    print(f"已导出 {written} 条 → {OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"  回传指引: {OUT_DIR.relative_to(REPO_ROOT)}/SUBMIT.md")

    if args.publish:
        print()
        print(f"=== 回传到经验库 {args.repo} ===")
        token = find_token()

        # 统一走 publish() — 内含 scp → GitHub → inbox 三档降级。
        # scp 是优先路径（不需任何凭证），跟 FSTDD 核心推送同链路。
        ok, reason = publish(OUT_DIR, args.repo, token)
        if not ok and reason:
            print(f"[FAIL] 回传失败: {reason[:200]}")
            print("      可稍后重试，或把 experiences/ 里的文件手工提交"
                  "（见 SUBMIT.md）")
        elif reason:
            print(("[WARN] " if not ok else "[OK] ") + reason)
        return 0 if ok else 1

    print()
    print("下一步（二选一）：")
    print(f"  · 自动推送：python {Path(__file__).name} --export --from-archive --publish")
    print("  · 手工提交（fork + PR）：")
    print(f"    1. fork https://github.com/{DEFAULT_EXP_REPO}")
    print("    2. 把本目录下的经验文件放入 fork 的 experiences/ 目录")
    print("    3. 发起 Pull Request")
    return 0


if __name__ == "__main__":
    sys.exit(main())
