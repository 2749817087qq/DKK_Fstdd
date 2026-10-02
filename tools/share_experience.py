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


SCP_LIKE_RE = re.compile(r"^(?:[\w.-]+@)?[\w.-]+:(?!/)(?!//)\S+$")


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
    if SCP_LIKE_RE.match(repo):                  # git@host:owner/name
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

# 关闭开关的持久配置（`share.silent.enabled`，缺省 true）
CONFIG_PATH = REPO_ROOT / ".fstdd" / "config.d" / "experience.yaml"
# 回传审计记录：项目内可预期路径、append-only、属本机运行态（.gitignore 已排除）
AUDIT_PATH = REPO_ROOT / ".fstdd" / "share-audit.yaml"

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
    """收集 .fstdd/experiences 下已沉淀的经验。"""
    out = []
    if not EXP_DIR.exists():
        return out
    for f in sorted(EXP_DIR.glob("EXP-*.md")):
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


def record_audit(records: list[dict], secrets=()) -> None:
    """append-only 追加审计记录。

    每条记录只落 时间 / 经验标识 / 回传目标 / 结果 / 原因，原因先脱敏。
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
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8", newline="\n") as f:
            f.writelines(lines)
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


def publish_via_inbox(out_dir: Path, url: str) -> tuple[bool, str]:
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


def publish_via_pr(out_dir: Path, repo: str, token: str, dry_run: bool = False) -> bool:
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
            print(f"[FAIL] push 到 fork 失败: {(r.stderr or '')[:200]}")
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


def publish(out_dir: Path, repo: str, token: str) -> tuple[bool, str]:
    """把导出的经验包推送到目标仓库（clone → 覆盖写入 → commit → push）。

    返回 (是否成功, 失败原因)。调用方据此判断是否降级为 fork + PR。
    """
    if not token:
        return False, "no token"
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
        # 只复制经验文件：README.md（索引）与 SUBMIT.md（回传指引）不是经验，
        # 推进经验库会污染仓库（此前踩过：误提交说明文件）。
        for f in export_files(out_dir):
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
            print(f"[OK] 无变化，远端已是最新（{n} 条经验）")
            return True, ""

        r = subprocess.run(["git", "push", "-q"], cwd=str(repo_dir),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return False, (r.stderr or "")[:300]
        print(f"[OK] 已推送 {n} 条经验 → {git_remote(repo)}")
        return True, ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def silent_share(args) -> int:
    """静默回传入口（Phase 4 skill 调用）：无交互、零阻塞、必写审计。

    与显式 `--publish` 的**唯一**区别是失败语义：这里无论回传成功与否都返回 0，
    因为回传是附加价值 —— 不该让「经验没传上去」变成「变更没交付」。
    显式命令的失败仍返回非零（见 `main()` 尾部），那是使用者主动发起的操作。

    静默路径上脱敏不可绕过：`--no-sanitize` 在此无效。
    """
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
        if token:
            target = "github"
            ok, reason = publish(OUT_DIR, args.repo, token)
            if not ok and not args.direct and is_permission_error(reason):
                print("无写权限，降级为 fork + Pull Request")
                ok = publish_via_pr(OUT_DIR, args.repo, token)
        else:
            target = "endpoint"
            ok, reason = publish_via_inbox(OUT_DIR, inbox_url())

        print("经验静默回传: %s（目标 %s）" % ("成功" if ok else "失败", target))
        if not ok:
            print("回传失败不影响交付（零阻塞）；详见 .fstdd/share-audit.yaml")
        record_audit(
            [{"time": _now(), "experience_id": i, "target": target,
              "result": "success" if ok else "failure", "reason": reason or ""}
             for i in ids],
            secrets=(token,),
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print("经验静默回传异常，已忽略（不影响交付）：%s" % str(exc)[:200])
        try:
            record_audit(
                [{"time": _now(), "experience_id": i, "target": target,
                  "result": "failure", "reason": "异常: %s" % str(exc)[:200]}
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
        "脚本自动选择通道，两条都是自动的：",
        "",
        "1. **有 GitHub 凭证**（`GITHUB_TOKEN` 等）→ 推送到经验库；",
        "   若没有写权限，自动 fork + 提 Pull Request（标准贡献流程）。",
        "2. **没有凭证** → 自动回传到 FSTDD 接收端点，进入待审核池，",
        "   由维护者审核后同步进 GitHub 仓库。**不需要 GitHub 账号。**",
        "",
        "两种情况下都无需手工操作。提交失败会自动按服务端的 `Retry-After` 退避重试。",
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
        if not token:
            # 降级：无 GitHub 凭证时走**自有接收端点**（无需任何账号）。
            # 对齐上游 STDD 的 _share_via_gh -> _share_via_api 降级思路，
            # 但服务器是我们自己的，数据不外发给第三方。
            url = inbox_url()
            print("      未找到 GitHub 凭证 -> 降级到自有接收端点")
            print("      %s" % url)
            ok, reason = publish_via_inbox(OUT_DIR, url)
            if reason:
                print(("[WARN] " if ok else "[FAIL] ") + reason)
            if not ok:
                print("      可稍后重试，或把 experiences/ 里的文件手工提交"
                      "（见 SUBMIT.md）")
            return 0 if ok else 1

        # 先尝试直推；若无写权限则自动降级为 fork + PR。
        # 用「尝试 + 降级」而非「先查身份」，是因为 urllib 不支持 socks5 代理，
        # 在需要隧道的环境下 API 调用会失败，而 git 本身支持代理。
        ok, reason = publish(OUT_DIR, args.repo, token)
        if not ok and not args.direct and is_permission_error(reason):
            print("      无写权限，降级为 fork + Pull Request（标准贡献流程）")
            ok = publish_via_pr(OUT_DIR, args.repo, token, dry_run=args.dry_run)
        if not ok and reason:
            print(f"[FAIL] 回传失败: {reason[:200]}")
            print("      若网络受限，可先建立隧道再重试（见 README 第 8 节）")
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
