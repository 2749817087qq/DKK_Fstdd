# -*- coding: utf-8 -*-
"""tests/conftest.py — pytest 共享配置

提供 --platform CLI 参数，所有 test_*.py 共用。
节点只需要 --platform 一个参数就能跑对平台的测试。
"""
from __future__ import annotations
import pytest


def pytest_addoption(parser):
    parser.addoption("--platform", action="store", default=None,
                     help="目标平台: workbuddy / claude-code / trae / linux. Auto-detect if omitted.")


def pytest_configure(config):
    """根据 --platform 自动标记不匹配的平台为 skip"""
    target = config.getoption("--platform")
    if not target:
        return

    # 注册平台 markers（避免 warning）
    for p in ("workbuddy", "trae", "claude-code", "linux"):
        config.addinivalue_line("markers", f"{p}: 限定此平台运行")


@pytest.fixture(scope="session")
def platform(request):
    p = request.config.getoption("--platform")
    if p:
        return p
    # 自动检测
    import platform as pf
    s = pf.system().lower()
    if s == "windows": return "workbuddy"
    if s == "linux": return "linux"
    if s == "darwin": return "workbuddy"
    return "workbuddy"


def pytest_collection_modifyitems(config, items):
    """收集阶段自动 skip 不匹配平台的 item"""
    target = config.getoption("--platform")
    if not target:
        return

    skip_me = pytest.mark.skip(reason=f"平台不匹配: 需要其他平台, 当前 --platform {target}")
    for item in items:
        item_platforms = [m.name for m in item.iter_markers()
                          if m.name in ("workbuddy", "trae", "claude-code", "linux")]
        if item_platforms and target not in item_platforms:
            item.add_marker(skip_me)
