# -*- coding: utf-8 -*-
"""经验回传：把本机沉淀的 STDD 经验整理为可提交到本仓库的经验包。

设计取舍（为什么不用 `stdd experience share`）：
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
from pathlib import Path

# 经验包回传目标仓库（可用环境变量覆盖）
DEFAULT_EXP_REPO = "2749817087qq/DKKstdd-experiences"

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = REPO_ROOT / ".stdd" / "experiences"
ARCHIVE_DIR = REPO_ROOT / ".stdd" / "archive"
OUT_DIR = REPO_ROOT / "experiences"

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
    # Windows 绝对路径
    (re.compile(r"[A-Za-z]:\\{1,2}(?:[^\s\"'`|<>]+\\)*[^\s\"'`|<>]*"), "<PATH>", "Windows 路径"),
    (re.compile(r"[A-Za-z]:/(?:[^\s\"'`|<>]+/)*[^\s\"'`|<>]*"), "<PATH>", "Windows 路径(POSIX 写法)"),
    # POSIX 家目录路径
    (re.compile(r"/(?:home|Users|root)/[^\s\"'`|<>)]+"), "<PATH>", "POSIX 路径"),
    # IPv4
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<IP>", "IP 地址"),
    # 内网/私有域名
    (re.compile(r"\b(?:[\w-]+\.)+(?:local|internal|corp|lan)\b"), "<DOMAIN>", "内网域名"),
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
    """收集 .stdd/experiences 下已沉淀的经验。"""
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


def publish(out_dir: Path, repo: str, token: str) -> bool:
    """把导出的经验包推送到目标仓库（clone → 覆盖写入 → commit → push）。"""
    if not token:
        print("[FAIL] 未找到凭证。请设置 GITHUB_TOKEN，或把 token 放入 "
              "<工作区>/.workbuddy-ai/tmp/.gh_token")
        return False
    tmp = Path(tempfile.mkdtemp(prefix="exp_publish_"))
    try:
        url = f"https://{token}@github.com/{repo}.git"
        r = subprocess.run(["git", "clone", "-q", url, str(tmp / "repo")],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[FAIL] clone 失败: {(r.stderr or '')[:200]}")
            return False

        repo_dir = tmp / "repo"
        dst = repo_dir / "experiences"
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in sorted(out_dir.glob("*.md")):
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
            print(f"[FAIL] commit 失败: {combined[:200]}")
            return False
        if "nothing to commit" in combined:
            print(f"[OK] 无变化，远端已是最新（{n} 条经验）")
            return True

        r = subprocess.run(["git", "push", "-q"], cwd=str(repo_dir),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[FAIL] push 失败: {(r.stderr or '')[:200]}")
            return False
        print(f"[OK] 已推送 {n} 条经验 → https://github.com/{repo}")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="列出可回传的经验")
    ap.add_argument("--export", action="store_true", help="导出到 experiences/")
    ap.add_argument("--from-archive", action="store_true", help="同时从归档 test-report 提取")
    ap.add_argument("--dry-run", action="store_true", help="预览，不写文件")
    ap.add_argument("--no-sanitize", action="store_true", help="不脱敏（危险）")
    ap.add_argument("--publish", action="store_true",
                    help="导出后推送到经验库仓库")
    ap.add_argument("--repo", default=os.environ.get("EXP_REPO", DEFAULT_EXP_REPO),
                    help=f"经验库仓库（默认 {DEFAULT_EXP_REPO}）")
    args = ap.parse_args()

    entries = collect_local()
    if args.from_archive:
        entries += extract_from_archives()

    if not entries:
        print("没有可回传的经验。")
        print("  · 本地经验库为空（.stdd/experiences/ 下无 EXP-*.md）")
        print("  · 加 --from-archive 可从已归档 change 的 test-report 提取")
        return 0

    sanitize_on = not args.no_sanitize
    if not sanitize_on:
        print("⚠️  已禁用脱敏：导出的内容可能包含路径 / IP / 域名 / 凭证，请自行检查后再提交。")

    print("=" * 62)
    print(f"经验回传准备 —— 共 {len(entries)} 条")
    print("=" * 62)

    prepared = []
    for e in entries:
        text = render(e, sanitize_on, [])
        clean, hits = sanitize(text, sanitize_on)
        clean = re.sub(r"^sanitized: .*$",
                       f"sanitized: {'true' if sanitize_on else 'false'}", clean, flags=re.M)
        if hits:
            clean = clean.replace("---\n\n", f"sanitize_hits: [{', '.join(hits)}]\n---\n\n", 1)
        prepared.append((e, clean, hits))
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
           f"导出时间 {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
           "| ID | 标题 | 来源 |", "|---|---|---|"]
    for e, _, _ in prepared:
        idx.append(f"| {e['id']} | {e['fm'].get('title', '-')} | {e['source']} |")
    (OUT_DIR / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8", newline="\n")

    print()
    print(f"已导出 {written} 条 → {OUT_DIR.relative_to(REPO_ROOT)}/")

    if args.publish:
        print()
        print(f"=== 推送到经验库 {args.repo} ===")
        ok = publish(OUT_DIR, args.repo, find_token())
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
