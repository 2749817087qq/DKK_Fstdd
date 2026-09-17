#!/usr/bin/env python3
"""STDD 数据外发加固 — 幂等施加 / 检查 / 网络层兜底。

背景：stdd-deliver 的 Step 2.8 会把项目经验发到外部，且有两条外发路径：
  A. gh CLI 路径（优先）：gh repo clone leonai42/stdd-experiences -> git push
     用本机 GitHub 账号向作者仓库推送，会暴露 GitHub 身份。
  B. server API 路径（fallback）：POST https://hzddyy.com/stdd/api/share-experience
     payload = {experience_id, content, author(git config user.name)}

三层防线：
  层1 skill 层（默认）   —— 禁用声明，防 AI 自动执行
  层2 网络层（block）    —— hosts 屏蔽 hzddyy.com + git pushInsteadOf 重定向，防误调用 CLI
  层3 项目层（--project）—— 打项目内 .stdd/skills/deliver.md 副本

用法：
  python apply.py                      检查并施加 skill 层（幂等）
  python apply.py --check              只检查，缺失退出码 1
  python apply.py --project <path>     额外加固项目级副本
  python apply.py block                施加网络层兜底（需管理员改 hosts）
  python apply.py unblock              撤销网络层兜底
  python apply.py status               查看三层防线状态
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
MARKER = "STDD-HARDENING:NO-UPLOAD"
GUARD_FILE = Path(__file__).parent / "guard-block.md"

SKILL_TARGETS = [
    HOME / ".workbuddy-ai" / "skills" / "stdd-deliver" / "SKILL.md",
    HOME / ".workbuddy-ai" / "stdd" / ".stdd" / "skills" / "deliver.md",
]

# ---- 网络层兜底配置 ----
HOSTS = Path(r"C:\Windows\System32\drivers\etc\hosts")
HOST_MARK = "STDD-HARDENING-BLOCK"
BLOCK_HOSTS = ["hzddyy.com", "www.hzddyy.com"]
SINK = "https://127.0.0.1:1/leonai42/stdd-experiences"  # 不可达，push 必失败
PUSHINSTEADOF = [
    "https://github.com/leonai42/stdd-experiences",
    "https://github.com/leonai42/stdd-experiences.git",
    "git@github.com:leonai42/stdd-experiences.git",
]

RE_28 = re.compile(r"^### Step 2\.8: 经验自动上传.*$", re.M)
TITLE_28 = (
    "### Step 2.8: 经验上传（V2.9.6）— ⛔ 默认禁用\n\n"
    "> **默认跳过。** 该步骤会将项目沉淀的经验发到外部站点，属数据外发。\n"
    "> 两条外发路径：\n"
    "> 1. `gh` CLI → `git push` 到 `leonai42/stdd-experiences`（暴露 GitHub 身份）\n"
    "> 2. `POST https://hzddyy.com/stdd/api/share-experience`（含经验正文 + `git config user.name`）\n\n"
    "> 依据文件顶部「数据外发管控」策略：**未获用户显式要求时不执行，不反问，静默跳过**。\n\n"
    "**跳过时**（默认路径）：\n"
    "- 输出 `ℹ️ 经验上传已跳过（默认禁用，需显式授权）`\n"
    "- 如需上传请明确告知，例如：\"把本次经验上传到社区\"\n\n"
    "**仅在用户显式要求时执行**：\n\n"
    "0. **上传前二次确认**：先列出待上传条目（EXP-ID + 标题 + 内容摘要），\n"
    "   提示\"以上 N 条将发往外部站点\"，等待用户确认后再执行。\n"
    "   **未确认不调用任何 `share` 命令。**"
)
RE_29 = re.compile(r"^经验上传完成后，自动同步到跨项目知识图谱。$", re.M)
TEXT_29 = (
    "同步到跨项目知识图谱（**仅本地 + 只读拉取**，非外发，不受 Step 2.8 禁用影响，照常执行）。\n\n"
    "执行 `python bin/stdd knowledge merge`，将本地经验合并到 `knowledge-graph.yaml`。\n"
    "（`knowledge merge` 仅从 GitHub raw 只读 GET 社区图谱，不会上传任何本地数据。）"
)


# ---------------- 层1：skill 层 ----------------
def insert_after_frontmatter(text: str, block: str) -> str:
    if not text.startswith("---"):
        return block + "\n\n" + text
    end = text.find("\n---", 3)
    if end == -1:
        return block + "\n\n" + text
    end += len("\n---")
    return text[:end] + "\n" + block + "\n" + text[end:]


def harden(path: Path, block: str, check_only: bool) -> tuple:
    if not path.exists():
        return "SKIP", f"  SKIP   {path} （不存在）"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return "OK", f"  OK     {path} （防线已存在）"
    if check_only:
        return "MISS", f"  MISS   {path} （防线缺失）"
    new = insert_after_frontmatter(text, block)
    new = RE_28.sub(lambda _: TITLE_28, new)
    new = RE_29.sub(lambda _: TEXT_29, new)
    path.write_text(new, encoding="utf-8")
    return "FIXED", f"  FIXED  {path} （已施加）"


def run_skill_layer(check_only: bool, extra_targets=None) -> int:
    block = GUARD_FILE.read_text(encoding="utf-8").rstrip() + "\n"
    targets = list(SKILL_TARGETS) + list(extra_targets or [])
    missing = 0
    for t in targets:
        state, line = harden(t, block, check_only)
        print(line)
        if state == "MISS":
            missing += 1
    return missing


# ---------------- 层2：网络层 ----------------
def _git(args, check=True):
    return subprocess.run(["git"] + args, capture_output=True, text=True)


def block_network() -> None:
    print("[层2] 网络层兜底")

    # 2a. hosts 屏蔽（需管理员）
    try:
        content = HOSTS.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  FAIL   hosts 读取失败: {e}")
        content = None

    if content is not None and HOST_MARK not in content:
        lines = [f"# {HOST_MARK} — block STDD experience upload endpoint"]
        lines += [f"127.0.0.1 {h}" for h in BLOCK_HOSTS]
        lines.append(f"::1 {BLOCK_HOSTS[0]}")
        lines.append(f"# end {HOST_MARK}")
        try:
            with HOSTS.open("a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(lines) + "\n")
            # 关键：写入后必须回读校验。曾出现脚本报 FIXED 但内容被安全软件回滚的情况。
            verify = HOSTS.read_text(encoding="utf-8", errors="replace")
            if HOST_MARK not in verify:
                print("  FAIL   hosts 写入后被回滚（安全软件拦截？）"
                      " — 请以管理员身份重试，或改用防火墙/Python 层兜底")
            else:
                print(f"  FIXED  hosts 已屏蔽 {', '.join(BLOCK_HOSTS)}（已回读校验）")
        except PermissionError:
            print("  NEED-ADMIN  hosts 需要管理员权限。请以管理员身份运行：")
            print(f'    powershell -Command "Start-Process python -ArgumentList '
                  f'\'{Path(__file__)},block\' -Verb RunAs"')
        except Exception as e:
            print(f"  FAIL   hosts 写入失败: {e}")
    else:
        print(f"  OK     hosts 已含屏蔽规则" if content is not None else "  SKIP   hosts")

    # 2b. 防火墙出站规则（比 hosts 持久；hosts 常被安全软件回滚）
    _fw("delete")  # 先清旧的，避免重复
    ok = _fw("add")
    print(f"  {'FIXED' if ok else 'FAIL'}   防火墙出站阻止 {', '.join(_fw_ips())}"
          + ("" if ok else "（可能需要管理员权限）"))

    # 2c. git pushInsteadOf（不需要管理员）
    for url in PUSHINSTEADOF:
        key = f"url.{SINK}.pushInsteadOf"
        existing = _git(["config", "--global", "--get-all", key])
        vals = existing.stdout.split()
        if url in vals:
            print(f"  OK     pushInsteadOf 已含 {url}")
        else:
            r = _git(["config", "--global", "--add", key, url])
            print(f"  {'FIXED' if r.returncode == 0 else 'FAIL'}   pushInsteadOf 添加 {url}")


def unblock_network() -> None:
    print("[层2] 撤销网络层兜底")
    try:
        content = HOSTS.read_text(encoding="utf-8", errors="replace")
        if HOST_MARK in content:
            keep = []
            skip = False
            for line in content.splitlines():
                if HOST_MARK in line:
                    skip = "end" not in line
                    continue
                if skip:
                    continue
                keep.append(line)
            HOSTS.write_text("\n".join(keep) + "\n", encoding="utf-8")
            print("  FIXED  hosts 屏蔽已移除")
        else:
            print("  OK     hosts 无屏蔽规则")
    except PermissionError:
        print("  NEED-ADMIN  hosts 需要管理员权限才能撤销")
    except Exception as e:
        print(f"  FAIL   {e}")

    print(f"  {'FIXED' if _fw('delete') else 'OK'}   防火墙规则移除")

    for url in PUSHINSTEADOF:
        r = _git(["config", "--global", "--unset",
                  f"url.{SINK}.pushInsteadOf", url])
        if r.returncode == 0:
            print(f"  FIXED  pushInsteadOf 移除 {url}")
    _git(["config", "--global", "--remove-section",
          f"url.{SINK}"])  # 空节清理，失败无妨


FW_RULE = "STDD-Block-Experience-Upload"
FALLBACK_IP = "124.222.113.129"


def _fw_ips():
    ips = {FALLBACK_IP}
    try:
        import socket
        for ip in socket.gethostbyname_ex("hzddyy.com")[2]:
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    return sorted(ips)


def _fw(action: str) -> bool:
    cmd = ["netsh", "advfirewall", "firewall", action, "rule"]
    if action == "add":
        cmd += [f"name={FW_RULE}", "dir=out", "action=block",
                f"remoteip={','.join(_fw_ips())}", "protocol=TCP"]
    else:
        cmd += [f"name={FW_RULE}"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def _fw_present() -> bool:
    try:
        r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule",
                            f"name={FW_RULE}"], capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def _dns_blocked() -> bool:
    """实测 DNS 是否真的把 hzddyy.com 指回本机（文件里写了但被回滚时不算数）。"""
    try:
        import socket
        return socket.gethostbyname("hzddyy.com").startswith("127.")
    except Exception:
        return False


def status() -> None:
    print("=== 三层防线状态 ===")
    print("\n[层1] skill 层（禁用声明）")
    miss = run_skill_layer(check_only=True)

    print("\n[层2] 网络层（hosts + git push 重定向）")
    in_file = False
    try:
        in_file = HOST_MARK in HOSTS.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    eff = _dns_blocked()
    if eff:
        print("  hosts 屏蔽: 已生效（hzddyy.com -> 127.0.0.1）")
    elif in_file:
        print("  hosts 屏蔽: ⚠️ 文件里已写但解析未生效（被安全软件回滚或需刷新 DNS）"
              " — 重跑 apply.py block")
    else:
        print("  hosts 屏蔽: 未启用（可选项，常被安全软件回滚）")
    print(f"  防火墙出站: {'已启用' if _fw_present() else '未启用'}（主手段，阻断路径 B）")
    r = _git(["config", "--global", "--get-all", f"url.{SINK}.pushInsteadOf"])
    n = len(r.stdout.split())
    print(f"  git push 重定向: {'已启用（%d 条）' % n if n else '未启用'}")
    print(f"  gh CLI: {'已安装（路径 A 可用，风险高）' if _has_gh() else '未安装（路径 A 不可用）'}")

    print("\n[层3] 项目层")
    print("  逐个项目检查 .stdd/skills/deliver.md 是否含 "
          f"{MARKER}；用 --project <path> 施加")

    print("\n" + ("⚠️ 层1 有缺失，执行 apply.py 修复" if miss else "✅ 层1 完好"))


def _has_gh() -> bool:
    try:
        return subprocess.run(["gh", "--version"], capture_output=True,
                              timeout=10).returncode == 0
    except Exception:
        return False


# ---------------- main ----------------
def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("action", nargs="?", default="apply",
                    choices=["apply", "block", "unblock", "status"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--project", action="append", default=[])
    args = ap.parse_args()

    if not GUARD_FILE.exists():
        print(f"guard-block.md 缺失: {GUARD_FILE}")
        return 2

    if args.action == "status":
        status()
        return 0
    if args.action == "block":
        block_network()
        return 0
    if args.action == "unblock":
        unblock_network()
        return 0

    # apply / --check
    print("[CHECK]" if args.check else "[APPLY]")
    extra = []
    for p in args.project:
        proj = Path(p)
        # 3a. 项目内 skill 副本
        extra.append(proj / ".stdd" / "skills" / "deliver.md")
        # 3b. 安装源模板：`stdd install <platform>` 会把 platforms/<p>/skills/stdd-deliver.md
        #     写回平台技能目录 → 不加固等于给防线留后门（claude-code / trae / workbuddy）
        for tpl in sorted((proj / ".stdd" / "platforms").glob("*/skills/stdd-deliver.md")):
            extra.append(tpl)
    missing = run_skill_layer(args.check, extra)

    if missing:
        print(f"\n⚠️ {missing} 处防线缺失。执行：python {Path(__file__)}")
        return 1
    print("\n✅ skill 层防线完好（Step 2.8 默认禁用）。")
    print("   如需网络层兜底（防误调用 CLI）：python %s block" % Path(__file__).name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
