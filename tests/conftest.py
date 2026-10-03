"""
conftest.py — pytest 共享配置
提供 --platform CLI option + 四平台 marker + 自动 skip 不匹配平台 + 双 key env 兼容
"""
import os
import sys
import re
from pathlib import Path

import pytest


# -------- 平台常量 — 从 platforms.yaml 读（唯一事实源）--------
def _load_platforms():
    """从 .fstdd/platforms.yaml 读平台定义，支持 Windows %VAR% 展开"""
    import yaml as _yaml
    yaml_path = Path(__file__).resolve().parent.parent / ".fstdd" / "platforms.yaml"
    content = yaml_path.read_text(encoding="utf-8")
    data = _yaml.safe_load(content)
    platform_names = list(data.get("platforms", {}).keys())
    skill_dirs = {}
    for pname, pdef in data.get("platforms", {}).items():
        rules = pdef.get("skill_dir_rules", [])
        # 取第一个匹配当前 OS 的规则
        for rule in rules:
            if isinstance(rule, str):
                # env: VAR 形式
                if rule.startswith("env:"):
                    env_name = rule.split(":", 1)[1].strip()
                    val = os.environ.get(env_name)
                    if val:
                        skill_dirs[pname] = os.path.expanduser(val)
                        break
            elif isinstance(rule, dict):
                os_type = list(rule.keys())[0]
                path_template = rule[os_type]
                if (sys.platform == "win32" and os_type == "windows") or \
                   (sys.platform != "win32" and os_type == "unix"):
                    import re as _re
                    # 展开 %VAR% 和 ~
                    expanded = os.path.expandvars(path_template)
                    expanded = os.path.expanduser(expanded)
                    skill_dirs[pname] = expanded
                    break
        if pname not in skill_dirs:
            skill_dirs[pname] = os.path.expanduser("~/.workbuddy/skills")  # fallback
    return set(platform_names), skill_dirs


VALID_PLATFORMS, PLATFORM_SKILL_DIRS = _load_platforms()
# 支持的 marker（把连字符 claude-code 转成下划线 claude_code 用于 marker 名）
PLATFORM_MARKERS = [f"platform_{p.replace('-', '_')}" for p in VALID_PLATFORMS]
# platform marker → 实际平台名 映射（方便 skip 逻辑比对）
MARKER_TO_PLATFORM = {f"platform_{p.replace('-', '_')}": p for p in VALID_PLATFORMS}


# -------- CLI option --------
def pytest_addoption(parser):
    parser.addoption(
        "--platform",
        action="store",
        default="workbuddy",
        choices=sorted(VALID_PLATFORMS),
        help="当前运行平台: workbuddy | trae | claude_code | linux",
    )


# -------- marker 注册 --------
def pytest_configure(config):
    for marker in PLATFORM_MARKERS:
        config.addinivalue_line(
            "markers", f"{marker}: 仅在 {marker.replace('platform_', '')} 平台运行"
        )


# -------- 收集后过滤：平台不匹配 → skip --------
def pytest_collection_modifyitems(config, items):
    current_platform = config.getoption("--platform")
    skip_msg = f"SKIP: platform mismatch (current={current_platform})"
    skip_marker = pytest.mark.skip(reason=skip_msg)

    for item in items:
        item_platforms = set()
        for marker in item.iter_markers(name="platform_"):
            # marker.name = "platform_claude_code" → 映射回实际平台名 "claude-code"
            actual_platform = MARKER_TO_PLATFORM.get(marker.name, marker.name.replace("platform_", ""))
            item_platforms.add(actual_platform)

        if item_platforms and current_platform not in item_platforms:
            item.add_marker(skip_marker)


# -------- 工具函数 --------
def get_current_platform() -> str:
    """从 pytest config 读当前平台"""
    try:
        return pytest.config.getoption("--platform")
    except (AttributeError, ValueError):
        return "workbuddy"


def get_skill_dir() -> Path:
    """根据 --platform 返回 skill 安装目标目录"""
    platform = get_current_platform()
    return Path(PLATFORM_SKILL_DIRS.get(platform, PLATFORM_SKILL_DIRS["workbuddy"]))


def repo_root() -> Path:
    """返回仓库根目录（假设 tests/ 在根下一层）"""
    return Path(__file__).resolve().parent.parent


def read_file(path: Path) -> str:
    """安全读文件，失败返回空串"""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


# -------- env 双 key 兼容 --------
def read_heartbeat_env() -> dict:
    """
    读 .heartbeat.env，支持 FSTDD_ 前缀和 HUB_ 前缀双 key 兼容
    返回 dict: {token, node_id, multihub_url}
    """
    env_path = repo_root() / "tools" / ".heartbeat.env"
    result = {"token": None, "node_id": None, "multihub_url": None}

    content = read_file(env_path)
    if not content:
        return result

    kv = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            kv[k.strip()] = v.strip().strip('"').strip("'")

    # token: FSTDD_TOKEN > HUB_TOKEN > GH_TOKEN
    result["token"] = (
        kv.get("FSTDD_TOKEN")
        or kv.get("HUB_TOKEN")
        or kv.get("GH_TOKEN")
        or kv.get("MULTIHUB_TOKEN")
    )
    # node_id: FSTDD_NODE_ID > HUB_NODE_ID > NODE_ID
    result["node_id"] = (
        kv.get("FSTDD_NODE_ID")
        or kv.get("HUB_NODE_ID")
        or kv.get("NODE_ID")
    )
    # multihub_url: FSTDD_MULTIHUB_URL > HUB_URL > MULTIHUB_URL
    result["multihub_url"] = (
        kv.get("FSTDD_MULTIHUB_URL")
        or kv.get("HUB_URL")
        or kv.get("MULTIHUB_URL")
    )

    return result
