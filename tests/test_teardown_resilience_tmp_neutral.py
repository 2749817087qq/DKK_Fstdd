"""TC-TTR-006 —— 规避层：测试期 TMP/TEMP/TMPDIR 归一到仓库外的中立临时根且可写。

对应 spec: canonical/specs/code/test-teardown-resilience.yaml → SC-004

纪律出处：EXP-2026-0029（`fix_template` 含「把 TMP/TEMP 指向中立目录」）+
EXP-2026-0030（指向 agent runtime 目录会被 Guard 误判）。

🔴 关键实证（本机 shim sitecustomize.py:805-825 / 1027-1040 / 1096-1099）：
   shim 的 bypass 判据是「路径是否位于 `_os_tmp_dirs` **之下**」，而 `_os_tmp_dirs`
   在 shim import 期由 `tempfile.gettempdir()` **固化**。
   ⇒ **落在系统临时根之下 = 被守卫放行（安全）**；**迁出系统临时根 = 反而会撞守卫**。
   故正确做法是「归一**到**系统临时根」，而非另建子目录 ——
   否则子进程会把 `_os_tmp_dirs` 固化成子目录，使 `--basetemp`（在系统临时根下）脱离 bypass。
"""
import os
from pathlib import Path

import conftest as cf

VARS = ("TMP", "TEMP", "TMPDIR")


def test_ttr_006_all_tmp_vars_set():
    """TC-TTR-006 / SC-004：三个变量都必须被显式设置（TMPDIR 在 Windows 上常缺失）。"""
    unset = [v for v in VARS if not os.environ.get(v)]
    assert not unset, f"以下变量未设置：{unset}"


def test_ttr_006_tmp_vars_point_outside_repo():
    """TC-TTR-006 / SC-004：三者均指向**仓库之外**的目录。"""
    repo = Path(cf.repo_root()).resolve()
    for var in VARS:
        raw = os.environ.get(var)
        assert raw, f"{var} 未设置"
        p = Path(raw).resolve()
        assert p.is_dir(), f"{var}={raw} 不是已存在的目录"
        assert p != repo and repo not in p.parents, f"{var} 落在仓库内：{p}"


def test_ttr_006_tmp_vars_are_consistent():
    """TC-TTR-006 / SC-004（AND）：三者应指向**同一个**中立目录（避免解析口径分裂）。

    ⚠️ 不得 `if os.environ.get(v)` 过滤未设置项 —— 否则 TMPDIR 缺失时会**空转通过**，
    正是本 change 要消除的那种「假绿」。
    """
    missing = [v for v in VARS if not os.environ.get(v)]
    assert not missing, f"有变量未设置，无法判定一致性：{missing}"
    resolved = {v: Path(os.environ[v]).resolve() for v in VARS}
    distinct = set(resolved.values())
    assert len(distinct) == 1, f"TMP/TEMP/TMPDIR 未指向同一目录：{resolved}"


def test_ttr_006_stays_inside_shim_bypass_root():
    """TC-TTR-006 / SC-004（核心不变式）：中立根必须**就是**系统临时根。

    若把它迁到别处（如 `~/.cache`），shim 的 `_os_tmp_dirs` 将不再包含它 ⇒
    测试临时路径**脱离 bypass 集**、反而会被守卫拦截 —— 与规避层的目的相反。
    """
    neutral = Path(os.environ["TMP"]).resolve()
    assert neutral == cf._ORIGINAL_TEMP_ROOT, (
        f"中立根被迁出了系统临时根：{neutral} != {cf._ORIGINAL_TEMP_ROOT}"
        "（迁出会脱离 shim 的 bypass 集，反而撞守卫）"
    )


def test_ttr_006_tmp_dir_is_writable():
    """TC-TTR-006 / SC-004（AND）：中立目录可写（写探针文件成功）。"""
    target = Path(os.environ["TMP"]).resolve()
    assert target == cf._ORIGINAL_TEMP_ROOT, f"TMP 未指向中立根：{target}"
    probe = target / f".ttr-write-probe-{os.getpid()}"
    probe.write_text("ok", encoding="utf-8")
    assert probe.read_text(encoding="utf-8") == "ok"
    probe.unlink()
