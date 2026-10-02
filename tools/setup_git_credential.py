# -*- coding: utf-8 -*-
"""配置 git 凭证 —— 把 .gh_token 绑定到正确的 GitHub 账号。

背景（实测踩到）：
本机 Windows Credential Manager 里存的是 **Sidneywu1986** 的凭证，
而项目仓库属于 **2749817087qq**。于是 `git push origin` 一直报
`Permission ... denied to Sidneywu1986`（403），只能靠显式带 token 绕过。

本脚本把 .gh_token 对应的凭证写入 Credential Manager，
并绑定到 2749817087qq，使 `git push origin` 可直接使用。

用法：
    python tools/setup_git_credential.py --check     # 只检查，不写入
    python tools/setup_git_credential.py --apply     # 写入凭证
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOKEN_FILE = REPO.parent / ".workbuddy-ai" / "tmp" / ".gh_token"
ACCOUNT = "2749817087qq"
HOST = "github.com"


def read_token() -> str | None:
    if not TOKEN_FILE.exists():
        print(f"[FAIL] 找不到 {TOKEN_FILE}")
        return None
    raw = TOKEN_FILE.read_bytes()
    tok = raw.strip().decode("ascii", "replace")
    if len(raw) != len(tok.encode()):
        print(f"[WARN] token 文件含多余空白（{len(raw)} → {len(tok)} 字节），已按去空白处理")
    if not tok.startswith(("ghp_", "github_pat_")):
        print(f"[WARN] token 前缀异常：{tok[:8]}...（期望 ghp_ 或 github_pat_）")
    return tok


def verify_token(token: str) -> bool:
    """用 API 验证 token 并打印其账号与权限。"""
    import urllib.error
    import urllib.request

    req = urllib.request.Request("https://api.github.com/user")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            scopes = r.headers.get("X-OAuth-Scopes", "")
            import json
            login = json.loads(r.read().decode())["login"]
        print(f"      账号: {login}")
        print(f"      权限: {scopes or '(fine-grained，无 scope 头)'}")
        if login != ACCOUNT:
            print(f"[WARN] token 属于 {login}，与预期账号 {ACCOUNT} 不一致")
            return False
        if "delete_repo" in scopes:
            print("[WARN] 该 token 含 delete_repo —— 权限过大，建议重建")
        if "admin:enterprise" in scopes or "admin:org" in scopes:
            print("[WARN] 该 token 含组织/企业级管理权限 —— 权限过大，建议重建")
        return True
    except urllib.error.HTTPError as e:
        print(f"[FAIL] 验证失败 HTTP {e.code}（token 可能无效或已撤销）")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 无法验证（可能网络受限，需走隧道）：{str(e)[:80]}")
        return True   # 网络问题不阻断写入


def apply_credential(token: str) -> bool:
    """通过 git credential approve 写入 Credential Manager。"""
    payload = f"protocol=https\nhost={HOST}\nusername={ACCOUNT}\npassword={token}\n\n"
    r = subprocess.run(["git", "credential", "approve"], input=payload,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(f"[FAIL] 写入凭证失败：{(r.stderr or '')[:150]}")
        return False
    print(f"      已写入 Credential Manager：{HOST} / {ACCOUNT}")
    return True


def check_push() -> None:
    """验证 git push origin 是否可用（不发实际数据）。"""
    r = subprocess.run(["git", "push", "--dry-run", "origin", "master"],
                       cwd=str(REPO), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode == 0:
        print("      [OK] git push origin 可用（dry-run 通过）")
    elif "denied" in out or "403" in out:
        print(f"      [FAIL] 仍被拒绝：{out.strip().splitlines()[-1][:120]}")
    else:
        print(f"      [WARN] 结果不确定：{out.strip().splitlines()[-1][:120] if out.strip() else '无输出'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写入凭证（默认只检查）")
    args = ap.parse_args()

    print("=" * 62)
    print(" 配置 git 凭证")
    print("=" * 62)

    token = read_token()
    if not token:
        return 1
    print(f"  token 前缀: {token[:12]}...  长度: {len(token)}")

    print("\n[1/3] 验证 token")
    verify_token(token)

    if not args.apply:
        print("\n[检查模式] 未写入任何凭证。加 --apply 执行。")
        return 0

    print("\n[2/3] 写入 Credential Manager")
    if not apply_credential(token):
        return 1

    print("\n[3/3] 验证 git push origin")
    check_push()

    print("\n完成。若 push 仍失败，检查 remote URL 是否含正确的用户名：")
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(REPO),
                       capture_output=True, text=True)
    print(f"  origin = {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
