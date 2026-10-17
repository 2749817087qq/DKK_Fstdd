import logging
import sys
import io
from pathlib import Path
from typing import Optional, Dict, Any, Iterator

_logger: Optional[logging.Logger] = None
STDD_SOURCE: Optional[Path] = None


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
# EXP-2026-0001 类假红：ci 覆盖检查恒定 0/N、diff 显示「未覆盖」、trace 找不到测试引用；
# 本仓同名编号为 Guard 阶段门，非此语义）。
# 新增命名模式必须改此处——ci.py / diff.py / trace.py 三处调用点一律经本函数扫描。
_TEST_FILE_PATTERNS = ("test_*.py", "test-*.py")

# TC-ID 案例定义行正则（REQ-CTR-002，change 2026-10-16-ci-checker-tc-recognition）：
# ci.py check_tcid_unique 使用本常量，杜绝 TC 计数口径再次分裂（EXP-20260917-A1：
# 全文口径致 10/10 归档 change 误报；EXP-2026-0017：下游被迫把每个 TC-ID 字面压到全文恰一次）。
# validate.py 的查重保留同表达式内联字面量——源码级守卫测试
# test_c3_validate_source_uses_scoped_regex 要求其内含定义行正则；修改本常量必须
# 同步 validate.py 内联正则（两处注释互相引用）。
# 语义：只数 `| **ID** | TC-… |` 定义行——「两个案例不得共用同一 ID」；
# 测试执行矩阵/补充顺序中对 TC-ID 的引用是模板正常写法，不计重复。
TC_ID_DEFINITION_ROW_PATTERN = r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})"


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


def get_stdd_source() -> Path:
    global STDD_SOURCE
    if STDD_SOURCE is not None:
        return STDD_SOURCE
    p = Path(__file__).resolve().parent
    while True:
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
            print("  [STDD] 运行 'stdd upgrade --check' 查看详情，"
                  "或 'stdd upgrade --lock' 锁定版本")
    except Exception:
        pass  # Never block execution
