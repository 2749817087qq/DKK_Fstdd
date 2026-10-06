"""
test_install_smoke.py — L0 基础设施冒烟（5 TC）
需要真实环境：git remote 正确、install_workbuddy_skills.py 可用、hub_client.py 可用
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import repo_root, get_current_platform, get_skill_dir, read_heartbeat_env


ROOT = repo_root()


def _expected_release_tag() -> str:
    """期望的发布 tag 由单一事实源派生：`.fstdd/version.yaml` 的 fstdd_version。

    TC-RTA-005 / SC-005：不得硬编码 `fstdd-v<版本>` 字面量（旧写法写死 3.1.1，
    自 3.3.x 起已过期；仅在 git fetch 可达时才执行，长期被 skip 掩盖）。
    """
    content = (ROOT / ".fstdd" / "version.yaml").read_text(encoding="utf-8")
    m = re.search(r'^\s*fstdd_version:\s*["\']?([\d.]+)["\']?', content, re.MULTILINE)
    assert m, "fstdd_version not found in .fstdd/version.yaml"
    return f"fstdd-v{m.group(1)}"


def _run(cmd: list, cwd=None, timeout=60):
    """subprocess run wrapper, return (rc, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else str(ROOT),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        return -1, "", f"TIMEOUT: {e}"
    except FileNotFoundError as e:
        return -2, "", f"NOT FOUND: {e}"


# ============================================================
# L0-01: git pull → HEAD tag 与 .fstdd/version.yaml 声明一致
# ============================================================
def test_L0_01_git_pull_to_tag():
    expected = _expected_release_tag()

    # 先 fetch tags
    rc, out, err = _run(["git", "fetch", "origin", "--tags"])
    # fetch 可能因为 network fail 非零，尝试继续
    if rc != 0:
        pytest.skip(f"git fetch failed (network?): {err.strip()[:200]}")

    # 检查 HEAD tag
    rc, out, err = _run(["git", "describe", "--tags", "--exact-match", "HEAD"])
    if rc != 0:
        # 可能 HEAD 没打 tag（tag 在某个 commit 上），检查所有 tag
        rc, out, err = _run(["git", "tag", "-l", expected])
        assert rc == 0 and expected in out, \
            f"{expected} tag not found. tags output: {out}"
        pytest.skip("tag exists but not on HEAD — this is OK for install smoke")

    assert expected in out.strip(), f"HEAD tag = {out.strip()}, expected {expected}"


# ============================================================
# L0-02: install_workbuddy_skills.py --platform <p> → exit 0
# ============================================================
def test_L0_02_install_skills():
    platform = get_current_platform()
    install_script = ROOT / "tools" / "install_workbuddy_skills.py"

    if not install_script.exists():
        pytest.skip(f"install_workbuddy_skills.py not found at {install_script}")

    rc, out, err = _run(
        [sys.executable, str(install_script), "--platform", platform],
        timeout=120,
    )

    # 打印输出方便调试
    print(f"\n--- install stdout ---\n{out}")
    if err:
        print(f"--- install stderr ---\n{err}")

    assert rc == 0, f"install_workbuddy_skills.py exit {rc}, expected 0"

    # 检查 skill dir 存在 + fstdd-fin 在内
    skill_dir = get_skill_dir()
    fin_dir = skill_dir / "fstdd-fin"
    assert fin_dir.exists(), f"{fin_dir} not found after install"


# ============================================================
# L0-03: verify_workbuddy_skills.py → exit 0
# ============================================================
def test_L0_03_verify_skills():
    platform = get_current_platform()
    verify_script = ROOT / "tools" / "verify_workbuddy_skills.py"

    if not verify_script.exists():
        pytest.skip(f"verify_workbuddy_skills.py not found at {verify_script}")

    rc, out, err = _run(
        [sys.executable, str(verify_script), "--platform", platform],
        timeout=60,
    )

    print(f"\n--- verify stdout ---\n{out}")
    if err:
        print(f"--- verify stderr ---\n{err}")

    assert rc == 0, f"verify_workbuddy_skills.py exit {rc}, expected 0"


# ============================================================
# L0-04 + L0-05: multihub ping + online nodes
# ============================================================
@pytest.fixture(scope="module")
def _hub_client():
    """检查 hub_client.py 是否可用"""
    hc = ROOT / "tools" / "hub_client.py"
    if not hc.exists():
        pytest.skip("hub_client.py not found")
    env = read_heartbeat_env()
    if not env["token"] or not env["multihub_url"]:
        pytest.skip(".heartbeat.env missing token or URL")
    return env


def test_L0_04_node_in_online_list(_hub_client):
    env = _hub_client
    hc = ROOT / "tools" / "hub_client.py"

    rc, out, err = _run(
        [sys.executable, str(hc), "list-nodes"],
        timeout=15,
    )
    print(f"\n--- hub list-nodes stdout ---\n{out[:500]}")
    if err:
        print(f"--- stderr ---\n{err[:200]}")

    # 只检查连通性 + 本节点出现
    assert rc == 0, f"hub_client list-nodes exit {rc}"
    node_id = env.get("node_id")
    if node_id:
        assert node_id in out, f"node {node_id} not in online list"


def test_L0_05_multihub_ping(_hub_client):
    hc = ROOT / "tools" / "hub_client.py"
    rc, out, err = _run(
        [sys.executable, str(hc), "ping"],
        timeout=15,
    )
    print(f"\n--- hub ping stdout ---\n{out[:500]}")
    assert rc == 0, f"hub_client ping exit {rc}"
