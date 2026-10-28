import logging
import re
import sys
import io
from pathlib import Path
from typing import Optional, Dict, Any, Iterator

_logger: Optional[logging.Logger] = None
STDD_SOURCE: Optional[Path] = None

# V3.1.1: installation_id 形状 `{PREFIX}-{8HEX}` 的**唯一事实来源**。
# 生成端（init.py）与读取端（experience.py）共用同一常量 —— 两处各写一份正则会漂移：
# 生成端放宽而读取端收紧，症状是「init 明明写了 ID，_next_id 却回落到旧格式」。
INSTALLATION_ID_RE = re.compile(r"^[A-Z0-9]{2,8}-[0-9A-F]{8}$")

# anti-drift-gates C5：evidence 事实标签的**唯一事实源**。
# 形态 `[F]` 或 `[F:来源]`。判据只应有一处 —— 散落到各调用方内联正则必然分叉
# （本仓 EXP-2026-0026：判据锚点必须落在统一实现上）。
FACT_TAG_RE = re.compile(r"\[F(?::[^\]\n]+)?\]")


def has_fact_tag(text) -> bool:
    """判断 evidence 是否含事实标签 ``[F]`` / ``[F:来源]``。

    约定（写入 fstdd-build / fstdd-deliver skill）：
    - ``[F]`` 事实 —— 须附命令输出 / 文件内容 / 测试结果
    - ``[D]`` 推导 —— 从 [F] 推出，须给推导链
    - ``[G]`` 猜测 —— 无证据，禁入任务清单 / change 范围 / commit message
    """
    if not text:
        return False
    return bool(FACT_TAG_RE.search(str(text)))


def read_installation_id(project_root, warn: bool = False) -> Optional[str]:
    """读取 ``.fstdd/version.yaml`` 的 ``installation_id``。

    文件不存在 / 无字段 / 字段不是合法形状 → 返回 ``None``（调用方回落旧 ID 格式）。

    为什么要校验形状：该字段可能被手改成列表、空串、或含 ``/`` 的任意串。
    不校验的话 ``_next_id`` 会把它拼进**文件名**（``{iid}-EXP-....md``）
    ⇒ 路径穿越或建文件失败，且失败点在写盘而非读配置处，排查成本高。
    非法值一律当「没配置」处理；``warn=True`` 时向 stderr 出声，
    避免「配了却不生效」被当成正常回落。
    """
    if project_root is None:
        return None
    version_path = Path(project_root) / ".fstdd" / "version.yaml"
    if not version_path.exists():
        return None

    import yaml  # 局部导入：utils 被每个子命令导入，避免启动即加载 yaml

    try:
        data = yaml.safe_load(version_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    iid = data.get("installation_id")
    if iid is None:
        return None
    if isinstance(iid, str) and not iid.strip():
        # 空串 = 「未设置」的等价写法（模板默认值 / 手工清空），不是错值 → 不出声
        return None
    if not isinstance(iid, str):
        if warn:
            print(
                f"  ⚠️  {version_path} 的 installation_id 不是字符串"
                f"（{iid!r}，应形如 WBCC-0803ADF7），本次回落到旧 ID 格式",
                file=sys.stderr,
            )
        return None
    iid = iid.strip().upper()
    if not INSTALLATION_ID_RE.match(iid):
        if warn:
            print(
                f"  ⚠️  {version_path} 的 installation_id 形状非法"
                f"（{iid!r}，应形如 WBCC-0803ADF7），本次回落到旧 ID 格式",
                file=sys.stderr,
            )
        return None
    return iid


def set_top_level_scalar(path, key: str, value: str) -> bool:
    """在 YAML 文件顶部首个顶层键之前定向插入/替换 ``key: value``，保留其余字节。

    设计约束（change 2026-10-22-installation-id-backfill，REQ-IID-004 / SC-IID-010）：
    - **不**用 ``yaml.dump`` 整体回写——那会丢注释、把块标量退化成转义串（实测 −101 行）。
    - bytes 级读写，按原文件主导行尾（CRLF/LF）保持；支持 UTF-8 BOM 剥离。
    - 插入点 = 首个顶层键行之前（避开「文件以块标量结尾被吸进块内」的陷阱）。
    - 写入前 4 条自检（解析 / 键值深比较 / 注释行 / 块标量标记）任一失败则不落盘。
    - 幂等：目标键已等于 value → 不写（连 mtime 都不动）。

    返回 True 表示已落盘（或本就相等无需写）；False 表示自检失败未落盘。
    """
    import yaml

    path = Path(path)
    if not path.exists():
        # 文件不存在 → 直接创建单键文件（init 在全新项目上的落点）
        path.write_bytes(f"{key}: {value}\n".encode("utf-8"))
        return True

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM 剥离
        raw = raw[3:]
    text = raw.decode("utf-8")

    if not text.strip():
        path.write_bytes(f"{key}: {value}\n".encode("utf-8"))
        return True

    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    # 首个顶层键行（插入点）：跳过注释与空行，要求行首为字母/下划线（无缩进）
    topkey_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:")
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if topkey_re.match(line):
            insert_idx = i
            break

    # 解析原文件做幂等与深比较判据
    try:
        original = yaml.safe_load(text)
    except (OSError, yaml.YAMLError, TypeError):
        return False
    if not isinstance(original, dict):
        return False
    if original.get(key) == value:
        return True  # 幂等：值已相等，不写

    # 该 key 若有既有顶层行 → 原位替换；否则在插入点新增
    key_re = re.compile(r"^" + re.escape(key) + r":(\s|$)")
    existing_idx = None
    for i, line in enumerate(lines):
        if key_re.match(line):
            existing_idx = i
            break

    if existing_idx is not None:
        new_lines = list(lines)
        new_lines[existing_idx] = f"{key}: {value}"
    else:
        new_lines = lines[:insert_idx] + [f"{key}: {value}"] + lines[insert_idx:]

    candidate = newline.join(new_lines)

    # ── 写入前 4 条自检 ──
    try:
        reparsed = yaml.safe_load(candidate)
    except (OSError, yaml.YAMLError, TypeError):
        return False
    if not isinstance(reparsed, dict):
        return False
    expected = dict(original)
    expected[key] = value
    if reparsed != expected:
        return False
    # ③ 原文件所有注释行逐行仍在（list 保序 → 顺序不变）
    comment_lines = [l for l in lines if l.lstrip().startswith("#")]
    for cl in comment_lines:
        if cl not in new_lines:
            return False
    # ④ 原文件块标量标记（形如 `changelog: |`）仍在
    block_re = re.compile(r"^[ \t]*[A-Za-z_][A-Za-z0-9_]*:\s*\|")
    block_markers = [l for l in lines if block_re.match(l)]
    for bm in block_markers:
        if bm not in new_lines:
            return False

    path.write_bytes(candidate.encode("utf-8"))
    return True


def setup_logging(verbose: int = 0) -> None:
    global _logger
    _logger = logging.getLogger("stdd")
    if verbose == 0:
        _logger.setLevel(logging.WARNING)
    elif verbose == 1:
        _logger.setLevel(logging.INFO)
    else:
        _logger.setLevel(logging.DEBUG)
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        _logger.addHandler(handler)


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        setup_logging(0)
    return _logger


# V3.0.2: Standard STDD subdirectories (all under .fstdd/)
def get_stdd_dir(project_root: Path, subdir: str) -> Path:
    """Get a STDD subdirectory path (under .fstdd/)."""
    return project_root / ".fstdd" / subdir


# V3.0.2: Resolution with fallback for migrated projects  
def resolve_stdd_path(project_root, subdir):
    """Get STDD path, preferring .fstdd/ but falling back to root level."""
    new_path = project_root / '.fstdd' / subdir
    old_path = project_root / subdir
    if new_path.exists(): return new_path
    if old_path.exists(): return old_path
    return new_path


# 测试文件识别的单一事实源（REQ-CTR-001，change 2026-10-16-ci-checker-tc-recognition）。
# 直接 rglob("test_*.py") 对连字符命名 test-*.py 结构性失明（下游多层次agent 的
# EXP-2026-0001 类假红：ci 覆盖检查恒定 0/N、diff 显示「未覆盖」、trace 找不到测试引用）。
# 新增命名模式必须改此处——ci.py / diff.py / trace.py 三处调用点一律经本函数扫描。
_TEST_FILE_PATTERNS = ("test_*.py", "test-*.py")


def iter_test_files(tests_dir: Path) -> Iterator[Path]:
    """产出 tests_dir 下全部测试文件：test_*.py 与 test-*.py 两种命名，去重无重复。

    新增命名模式必须改本函数（唯一修改点）——ci.py / diff.py / trace.py 三处调用点
    一律经此扫描，禁止各自 rglob。
    只产出**文件**（目录条目即使名为 test_x.py 也被跳过，防止调用方 read_text 抛
    IsADirectoryError——rglob 本身不区分文件/目录）。
    两模式第 5 字符互斥（_ vs -）天然不重叠；仍以 seen 集合防御未来模式扩张。
    tests_dir 不存在时产出为空（与 rglob 对不存在目录行为一致）。
    """
    seen = set()
    for pattern in _TEST_FILE_PATTERNS:
        for test_file in tests_dir.rglob(pattern):
            if not test_file.is_file():
                continue
            resolved = test_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield test_file


# 源根向上查找的最大层数。正常仓库从 cli/utils.py 到根不超过 5 层；
# 50 是极端安全上限，用于防止符号链接循环导致无限遍历（2026-10-11 share-hardening）。
MAX_SOURCE_DEPTH = 50


def _find_source_root(start: Path, max_depth: int = MAX_SOURCE_DEPTH) -> Path:
    """从 start 向上查找 FSTDD 源根（含 FSTDD.md/STDD.md 且含 bin/ 目录）。

    超过 max_depth 层仍找不到 ⇒ 抛含深度信息的 RuntimeError（不无限循环）。
    """
    p = start
    for _ in range(max_depth):
        # 改名兼容：FSTDD.md（新）优先，STDD.md（旧）回退。
        # 此前只认 STDD.md，改名后任何未预设 STDD_SOURCE 的调用路径都会
        # RuntimeError（测试直接 import cmd_init 即触发）。
        if ((p / "FSTDD.md").exists() or (p / "STDD.md").exists()) and (p / "bin").is_dir():
            return p
        if p.parent == p:
            raise RuntimeError(
                "Cannot find FSTDD source root (FSTDD.md or STDD.md not found)"
            )
        p = p.parent
    raise RuntimeError(
        f"Cannot find FSTDD source root within {max_depth} levels "
        f"(depth limit reached from {start}; possible symlink loop)"
    )


def get_stdd_source() -> Path:
    global STDD_SOURCE
    if STDD_SOURCE is not None:
        return STDD_SOURCE
    return _find_source_root(Path(__file__).resolve().parent)


def read_config(project_root: Path) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    config_d = project_root / ".fstdd" / "config.d"
    if config_d.is_dir():
        for cfg_file in sorted(config_d.glob("*.yaml")):
            import yaml
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    config.update(data)
                else:
                    get_logger().warning("config.d/%s 不是 dict 类型，已跳过", cfg_file.name)
        if config:
            get_logger().info("从 config.d/ 加载配置 (%d 个文件)", len(list(config_d.glob("*.yaml"))))
            legacy = project_root / ".fstdd" / "config.yaml"
            if legacy.exists():
                get_logger().warning("检测到旧 config.yaml，建议删除（config.d/ 已生效）")
            return config
    legacy = project_root / ".fstdd" / "config.yaml"
    if legacy.exists():
        import yaml
        with open(legacy, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        get_logger().info("从 config.yaml 加载配置（向后兼容）")
    return config


def fix_windows_encoding() -> None:
    if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ── Version utilities (V2.9) ──

def get_source_version() -> Optional[str]:
    """Read stdd_version from STDD source's config.d/project.yaml."""
    try:
        source = get_stdd_source()
        config = read_config(source)
        return config.get("stdd_version")
    except Exception:
        return None


def get_project_version(project_root: Path) -> Optional[str]:
    """Read version from .fstdd/version.yaml (preferred) or fallback to project.yaml."""
    version_file = project_root / ".fstdd" / "version.yaml"
    if version_file.exists():
        try:
            import yaml
            data = yaml.safe_load(version_file.read_text(encoding="utf-8"))
            if data and "stdd_version" in data:
                return data["stdd_version"]
        except Exception:
            pass
    # Fallback to legacy project.yaml
    config = read_config(project_root)
    return config.get("stdd_version")


def compare_versions(v1: str, v2: str) -> int:
    """Compare semantic version strings. Returns -1, 0, or 1.

    Supports '2.7', '2.8.0', 'v2.9' style formats.
    """
    def _parse(v: str) -> tuple:
        v = v.strip().lstrip("v").lstrip("V").strip("'").strip('"')
        parts = v.split(".")
        return tuple(int(x) for x in parts if x.isdigit())

    a = _parse(v1)
    b = _parse(v2)
    max_len = max(len(a), len(b))
    a = a + (0,) * (max_len - len(a))
    b = b + (0,) * (max_len - len(b))
    if a < b:
        return -1
    elif a > b:
        return 1
    return 0


def try_version_check(project_root: Path) -> None:
    """Check project vs source version, print notice if outdated.
    Never raises — any exception is silently ignored.
    """
    try:
        if not (project_root / ".fstdd").is_dir():
            return

        # Check lock status
        version_file = project_root / ".fstdd" / "version.yaml"
        if version_file.exists():
            import yaml
            data = yaml.safe_load(version_file.read_text(encoding="utf-8"))
            if data and data.get("locked", False):
                return  # Locked project — skip

        source_ver = get_source_version()
        proj_ver = get_project_version(project_root)

        if source_ver and proj_ver and compare_versions(proj_ver, source_ver) < 0:
            print(f"  [STDD] 有新版本可用: {source_ver} (当前: {proj_ver})")
            print("  [STDD] 运行 'fstdd upgrade --check' 查看详情，"
                  "或 'fstdd upgrade --lock' 锁定版本")
    except Exception:
        pass  # Never block execution
