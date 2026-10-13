"""
conftest.py — pytest 共享配置
提供 --platform CLI option + 四平台 marker + 自动 skip 不匹配平台 + 双 key env 兼容
"""
import functools
import os
import pathlib
import re
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

import pytest


# -------- 韧性层：删除原语守卫（design.md D2 / D3）--------
#
# 背景（test-plan.md 六、证据记录）：
#   沙箱 safe-delete 守卫（shim sitecustomize.py）在拦截删除时 raise SystemExit；
#   该异常落在 pytest fixture teardown 内时，会中断收尾链并留下残留 ⇒ 门禁数不可判。
#   根因有两处：① 测试侧 Path.unlink()；② upstream/fstdd/cli/commands/experience.py 的
#   `os.remove(lock_path)`（`except OSError` 抓不到 SystemExit）。
#
# 策略：在 pytest 进程内包装删除原语，使 ①② 都经由本层 ⇒ 不修改 upstream/ 亦可兜住。
# 纪律：**只放行 SystemExit**（守卫签名），真实异常原样抛出；捕获必须可见、可计数（不得静默）。

DELETE_GUARD_PREFIX = "[teardown-resilience]"
# 会话级捕获统计（**就地变更**，便于测试直接读取快照做差）
DELETE_GUARD_STATS = {"captured": 0, "targets": []}
# 已保存的原实现（键 = "<holder>.<attr>"）
_DELETE_GUARD_ORIGINALS = {}
_DELETE_GUARD_INSTALLED = False

# 需要包装的删除入口：(宿主对象, 属性名)
#
# 🔴 必须含 `pathlib.Path.unlink` / `Path.rmdir` —— 实测（本机 shim sitecustomize.py:1281）
#    shim 会**直接替换** `pathlib.Path.unlink` 为 `_safe_path_unlink`，而该函数在
#    **非 bypass 分支**直接调用 `_try_trash()`（:1237），**完全不经过 `os.unlink`**
#    ⇒ 只包装 `os.*` 会漏掉根因①（仓库内路径走的正是这一支）。
_DELETE_GUARD_SURFACES = (
    (os, "remove", "os.remove"),
    (os, "unlink", "os.unlink"),
    (os, "rmdir", "os.rmdir"),
    (shutil, "rmtree", "shutil.rmtree"),
    (pathlib.Path, "unlink", "pathlib.Path.unlink"),
    (pathlib.Path, "rmdir", "pathlib.Path.rmdir"),
)


def _guarded_delete(inner, target, *args, **kwargs):
    """把一次删除调用包进韧性层。

    - 只放行 ``SystemExit``（沙箱守卫签名），降级为**可见告警 + 计数**后正常返回；
    - 其余异常（``PermissionError`` / ``OSError`` 及其它 ``BaseException`` 子类）**原样抛出**。

    这是本 change 的**可判性前提**：判据针对该纯函数，可用 monkeypatch 稳定复现，
    不依赖「环境恰好触发守卫」。
    """
    try:
        return inner(target, *args, **kwargs)
    except SystemExit as exc:
        DELETE_GUARD_STATS["captured"] += 1
        DELETE_GUARD_STATS["targets"].append(str(target))
        warnings.warn(
            f"{DELETE_GUARD_PREFIX} 删除被沙箱守卫中断"
            f"（SystemExit code={exc.code}），已降级放行：{target}",
            UserWarning,
            stacklevel=2,
        )
        return None


def _install_delete_guard():
    """包装 ``_DELETE_GUARD_SURFACES`` 列出的全部删除入口（幂等）。

    包装后，**框架代码（如 experience.py 的 ``os.remove``）也会经由本层**，
    从而在不触碰 ``upstream/`` 的前提下同时兜住两处根因。

    包装体在**调用时**查表取原实现（而非闭包捕获），使端到端判据可被 monkeypatch 稳定驱动。
    """
    global _DELETE_GUARD_INSTALLED
    if _DELETE_GUARD_INSTALLED:
        return  # 已安装（幂等）

    def _wrap(key, original):
        def _wrapper(target, *args, **kwargs):
            return _guarded_delete(_DELETE_GUARD_ORIGINALS[key], target, *args, **kwargs)
        _wrapper.__wrapped_key__ = key
        # 保留元信息（__name__/__doc__ 等）：手工逐个复制而非 `functools.wraps`
        # （后者会 update 原实现的 `__dict__`，而内建函数没有 `__dict__`）。
        # 这里不写 try/except —— 对 Python 函数 setattr 这三个 str 属性不会失败；
        # 且本 change 的纪律是「不得静默」，宁可让它抛也不要吞（D3 / EXP-2026-0014）。
        for attr in ("__name__", "__qualname__", "__doc__"):
            value = getattr(original, attr, None)
            if isinstance(value, str):
                setattr(_wrapper, attr, value)
        return _wrapper

    for holder, name, key in _DELETE_GUARD_SURFACES:
        original = getattr(holder, name)
        _DELETE_GUARD_ORIGINALS[key] = original
        setattr(holder, name, _wrap(key, original))
    _DELETE_GUARD_INSTALLED = True


def _delete_guard_summary() -> str:
    """返回会话级汇总行（固定前缀 + 捕获次数）。"""
    n = DELETE_GUARD_STATS["captured"]
    return f"{DELETE_GUARD_PREFIX} 会话共捕获 {n} 次删除守卫中断"


# -------- 规避层：测试期临时目录中立化（design.md D1a）--------
#
# 依据 EXP-2026-0029（`fix_template` 含「把 TMP/TEMP 指向中立目录」）与
# EXP-2026-0030（指向 agent runtime 目录会被 Guard 误判）。
#
# 🔴 关键实证（本机 shim sitecustomize.py:805-825 / 1027-1040 / 1096-1099）：
#    shim 的 bypass 判据是「路径是否位于 `_os_tmp_dirs` **之下**」，而 `_os_tmp_dirs`
#    在 shim import 期由 `tempfile.gettempdir()` **固化**。
#    ⇒ **落在系统临时根之下 = 被守卫放行（安全）**；**迁出系统临时根 = 反而会撞守卫**。
#    故 D1a 的正确做法是把 TMP/TEMP/TMPDIR **归一到系统临时根本身**（而非另建子目录）——
#    这样连子进程的 `_os_tmp_dirs` 也与基线完全一致，不引入新的非 bypass 面。

# 在**本模块导入时**（早于 pytest_configure、且 shim 已固化 _os_tmp_dirs）抓取系统临时根
_ORIGINAL_TEMP_ROOT = Path(tempfile.gettempdir()).resolve()
_NEUTRAL_TMP_DIR = None


def _pick_neutral_root() -> Path:
    """返回「仓库之外」的中立临时根（仓库内不可作中立目录）。"""
    repo = Path(__file__).resolve().parent.parent
    if _ORIGINAL_TEMP_ROOT != repo and repo not in _ORIGINAL_TEMP_ROOT.parents:
        return _ORIGINAL_TEMP_ROOT
    fallback = (Path.home() / ".cache").resolve()
    warnings.warn(
        f"{DELETE_GUARD_PREFIX} 系统临时根落在仓库内（{_ORIGINAL_TEMP_ROOT}），"
        f"回退到 {fallback} —— 该落点不在守卫的 bypass 集内，删除可能被拦截",
        UserWarning,
        stacklevel=2,
    )
    return fallback


def _neutralize_temp_env():
    """把 TMP/TEMP/TMPDIR 归一到仓库外的中立临时根（幂等）。

    同时清除 ``tempfile`` 的目录缓存（``tempfile.tempdir``）：``gettempdir()`` 会缓存首次
    结果，若会话早期已求值，仅改环境变量**不会生效**（实测踩过）。
    """
    global _NEUTRAL_TMP_DIR
    if _NEUTRAL_TMP_DIR is not None:
        return _NEUTRAL_TMP_DIR

    neutral = _pick_neutral_root()
    neutral.mkdir(parents=True, exist_ok=True)
    _NEUTRAL_TMP_DIR = neutral
    for var in ("TMP", "TEMP", "TMPDIR"):
        os.environ[var] = str(neutral)
    tempfile.tempdir = None  # 清除缓存，使新落点立即生效
    return neutral


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


# -------- marker 注册 + 韧性层安装 --------
def pytest_configure(config):
    for marker in PLATFORM_MARKERS:
        config.addinivalue_line(
            "markers", f"{marker}: 仅在 {marker.replace('platform_', '')} 平台运行"
        )
    # D1a 规避层：测试期临时目录中立化（仓库外专用目录）
    _neutralize_temp_env()
    # D1b 韧性层：安装删除原语包装 —— 会话开始时生效，覆盖测试侧与框架侧的删除调用
    _install_delete_guard()


# -------- 会话级汇总：捕获必须可见（不得静默）--------
def pytest_sessionfinish(session, exitstatus):
    """会话级汇总 —— 捕获必须可见（design.md D3）。

    ⚠️ **不修改 `exitstatus`**：本 change 的目标是「门禁数可判」（SC-006），
    若让捕获次数影响退出码，就会把「守卫是否恰好触发」重新引入失败数 ⇒ 正是要消除的抖动。
    故这里的契约是「**可见**」而非「**判红**」：以告警 + 黄色汇总行呈现。
    """
    if not DELETE_GUARD_STATS["captured"]:
        return
    line = _delete_guard_summary()
    targets = DELETE_GUARD_STATS["targets"]
    shown, omitted = targets[:20], max(0, len(targets) - 20)
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line("")
        reporter.write_line(line, yellow=True)
        for target in shown:
            reporter.write_line(f"  - {target}")
        if omitted:
            reporter.write_line(f"  … 其余 {omitted} 条省略")
    else:
        suffix = f"（其余 {omitted} 条省略）" if omitted else ""
        warnings.warn(line + suffix, UserWarning)


# -------- 自测隔离：本 change 的用例刻意触发捕获，不得污染会话汇总 --------
_SELFTEST_PREFIX = "test_teardown_resilience_"


@pytest.fixture(autouse=True)
def _isolate_delete_guard_selftest(request):
    """把**自测用例刻意触发**的捕获在用后还原，避免污染会话汇总。

    🔴 为什么必须有：`test_teardown_resilience_*` 里的 SystemExit 是**测试自己注入的桩**
    （monkeypatch 原实现），并非沙箱守卫真的拦了删除。若不还原，`pytest_sessionfinish`
    会把它们当成「守卫触发 N 次」报出来 —— 汇总行**失真**，真信号被噪声淹没。
    本夹具只对 `_SELFTEST_PREFIX` 前缀的用例生效，其余用例零影响。
    """
    node_path = getattr(request.node, "path", None)
    if not (getattr(node_path, "name", "") or "").startswith(_SELFTEST_PREFIX):
        yield
        return

    captured_before = DELETE_GUARD_STATS["captured"]
    targets_before = list(DELETE_GUARD_STATS["targets"])
    try:
        yield
    finally:
        DELETE_GUARD_STATS["captured"] = captured_before
        DELETE_GUARD_STATS["targets"][:] = targets_before


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
