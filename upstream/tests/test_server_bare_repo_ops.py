"""Static/read-only tests for the FSTDD server bare-repo data-plane assets."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return (ROOT / "tools" / name).read_text(encoding="utf-8")


def test_deploy_bare_repo_is_idempotent():
    """裸库部署必须可反复执行：已存在则保留数据，不重置仓库。"""
    text = read("deploy_server_bare_repo.sh")
    assert "[SKIP] 裸库已存在" in text
    assert "rev-parse --is-bare-repository" in text
    # 复用密钥、不重复注册
    assert "if [ ! -f" in text
    assert "deploy key 已存在" in text


def test_deploy_bare_repo_verifies_end_state():
    """结论必须来自端状态，而不是命令回显（远端命令可能执行两次）。"""
    text = read("deploy_server_bare_repo.sh")
    assert "rev-list --count master" in text
    assert "ls-remote github" in text
    assert "端状态验证" in text


def test_deploy_bare_repo_uses_least_privilege_credential():
    """镜像凭证为仓库级 Deploy Key（写权限），不得内嵌明文 PAT。"""
    text = read("deploy_server_bare_repo.sh")
    assert '\\"read_only\\":false' in text
    assert "fstdd-hub-mirror" in text
    assert "ssh-keygen -t ed25519" in text
    assert "ghp_" not in text
    assert "github_pat_" not in text


def test_mirror_hook_is_non_force_and_non_blocking():
    """钩子非强制推送（不静默覆盖），且超时兜底、失败不拖垮推送。"""
    text = read("deploy_server_bare_repo.sh")
    # 镜像目标自 ADJ-010 起是 `push "$MIRROR_TARGET"` —— 默认 remote 名 github，
    # 可被 FSTDD_MIRROR_URL 覆盖（自动化验证用）。故按 MIRROR_TARGET 断言，
    # 而不是字面 `github`（否则钩子一改就假红）。
    assert r'push "\$MIRROR_TARGET" --all' in text
    assert r'push "\$MIRROR_TARGET" --tags' in text
    assert r'push "\$MIRROR_TARGET" --all --force' not in text
    assert r'push "\$MIRROR_TARGET" --tags --force' not in text
    assert "timeout 180" in text
    assert "timeout 120" in text
    assert "exit 0" in text


def test_deploy_bare_repo_remote_uses_ssh_alias():
    """remote 必须走 SSH 别名。

    裸主机名（`ubuntu@ip:...`）会绕过 `~/.ssh/config` 的 IdentityFile，
    使 git 退回默认密钥并认证失败 —— 这是实际踩到过的缺陷，故立断言守住。
    """
    text = read("deploy_server_bare_repo.sh")
    assert "FSTDD_SSH_ALIAS" in text
    assert "$ALIAS:$BARE_DIR" in text
    assert "$HOST:$BARE_DIR" not in text


def test_deploy_bare_repo_avoids_dangerous_process_kill():
    """按端口找 PID 再 kill，绝不用 pkill（会匹配到 ssh 命令行自身）。

    断言只扫可执行代码行 —— 脚本注释里正当地提到了 "pkill"（说明为什么不用它），
    扫全文会产生误报。
    """
    code = _code_only(read("deploy_server_bare_repo.sh"))
    assert "pkill" not in code
    assert "rm -rf" not in code


def _code_only(text):
    """剔除注释行与空行，只保留可执行代码。"""
    return "\n".join(
        ln for ln in text.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    )
