"""时间基线：基础设施切片（Slice 1）— `fstdd baseline` 命令与 timeutil。

对应 TC
-------
- TC-TMPL-003  CLI 命令五处注册齐全
- TC-TMPL-004  命令可被真实执行（**禁止以「源码里出现某字符串」为判据**）
- TC-TMPL-005  另一节点（无额外安装步骤）可直接执行
- TC-TMPL-006  节点与阈值可配置

设计要点
--------
1. **真实执行 CLI 子进程**，而不是 grep 源码。五处注册中有三处是字符串，
   grep 必然「全绿」而命令仍可能不可执行（`EXP-20260915-B1` + `EXP-20260917-A2`）。
2. 分发表的 dotted string 必须**真的能 import**（`importlib.import_module`），
   否则表现为「命令被识别但无法执行」。
3. 「另一节点」用**临时目录 + 干净 cwd** 模拟：不复制仓库、不安装、不加 PYTHONPATH 之外的路径。
4. 全部测试只读或只写临时目录，**不污染本仓库**。
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
CLI_INIT = UPSTREAM / "fstdd" / "cli" / "__init__.py"


def run_cli(*args: str, cwd: Path | None = None, env_extra: dict | None = None):
    """以子进程执行 CLI。返回 (returncode, stdout, stderr)。"""
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd) if cwd else str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


# --------------------------------------------------------------------------- #
# TC-TMPL-003 — 五处注册齐全
# --------------------------------------------------------------------------- #

def test_tmpl_003_five_registration_points():
    """TC-TMPL-003：`baseline` 命令必须在五处同时到位。

    缺失后果（实测根因 `EXP-20260915-B1`）：分发表是**动态导入字符串**，
    少任何一处都不报错，只表现为「命令不存在」或「命令无法执行」。
    """
    src = CLI_INIT.read_text(encoding="utf-8")

    # ① COMMAND_GROUPS
    m = re.search(r"COMMAND_GROUPS\s*=\s*\[(.*?)\n\]", src, re.DOTALL)
    assert m is not None, "找不到 COMMAND_GROUPS"
    assert '"baseline"' in m.group(1), "① COMMAND_GROUPS 未含 baseline"

    # ② _CMD_HELP
    assert re.search(r'^\s*"baseline"\s*:', src, re.MULTILINE), "② _CMD_HELP 未含 baseline"

    # ③ add_parser
    assert re.search(r'add_parser\(\s*"baseline"', src), "③ 未 add_parser(baseline)"

    # ④ 分发表（dotted string）— 必须真实可导入。
    #    注意：`_CMD_HELP` 里也有 `"baseline": "..."`，其值是中文描述，
    #    会抢先匹配宽松正则。用字符类 [a-z_.] 锚定「模块路径」形态来区分两处。
    disp = re.search(r'^\s*"baseline"\s*:\s*"([a-z_\.]+)"', src, re.MULTILINE)
    assert disp is not None, "④ 分发表未含 baseline"
    dotted = disp.group(1)
    module_path, _, func_name = dotted.rpartition(".")
    assert module_path, f"④ 分发表路径不是 dotted string: {dotted!r}"
    mod = importlib.import_module(module_path)  # 不可导入 → 此处失败
    assert hasattr(mod, func_name), f"④ {dotted} 中找不到 {func_name}"

    # ⑤ 命令模块文件存在
    mod_file = UPSTREAM / "fstdd" / "cli" / "commands" / "baseline.py"
    assert mod_file.is_file(), f"⑤ 命令模块文件不存在: {mod_file}"


# --------------------------------------------------------------------------- #
# TC-TMPL-004 — 真实执行（禁止 grep 判据）
# --------------------------------------------------------------------------- #

def test_tmpl_004_help_and_three_actions():
    """TC-TMPL-004：`--help` 被识别 + 三个动作各真实调用一次。

    ⚠️ 判据必须是「真实执行的结果」，不是「源码里出现某字符串」——
    后者会被检测规则自己满足（`EXP-20260917-A2`）。
    """
    rc, out, err = run_cli("baseline", "--help")
    assert rc == 0, f"`fstdd baseline --help` 失败 rc={rc}\n{err}"
    for action in ("establish", "show", "check"):
        assert action in out, f"--help 未列出动作 {action}"

    # 三个动作各真实调用一次（不要求成功，要求「被识别并进入执行」）
    for action in ("establish", "show", "check"):
        rc, out, err = run_cli("baseline", action)
        assert "invalid choice" not in (err + out).lower(), (
            f"`baseline {action}` 未被 CLI 识别（可能是漏注册）"
        )
        assert "No module named" not in (err + out), (
            f"`baseline {action}` 触发 ModuleNotFoundError（分发表路径错）"
        )


def test_tmpl_004_establish_show_roundtrip(tmp_path):
    """TC-TMPL-004 增强：show 能结构化读出 establish 写入的内容。

    用临时目录做最小 FSTDD 项目，避免污染本仓库。
    """
    proj = tmp_path / "proj"
    proj.mkdir()
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"`fstdd init` 在临时项目失败: {err}"

    change = "tmp-baseline-demo"
    rc, _, err = run_cli("new", change, cwd=proj)
    assert rc == 0, f"`fstdd new` 失败: {err}"

    rc, out, err = run_cli("baseline", "establish", change, cwd=proj)
    assert rc == 0, f"`baseline establish` 失败 rc={rc}\n{err}"

    rc, out, err = run_cli("baseline", "show", change, "--format", "json", cwd=proj)
    assert rc == 0, f"`baseline show --format json` 失败 rc={rc}\n{err}"
    payload = json.loads(out)
    for key in ("at", "base_git_sha", "node_id", "clock_source"):
        assert payload.get(key), f"show 输出的 {key} 为空: {payload}"


# --------------------------------------------------------------------------- #
# TC-TMPL-005 — 另一节点可直接执行
# --------------------------------------------------------------------------- #

def test_tmpl_005_executable_from_clean_cwd(tmp_path):
    """TC-TMPL-005：在「另一个 cwd」直接执行，无需任何安装步骤。

    不复制仓库、不改 sys.path —— 只换 cwd，模拟另一节点 git pull 后直接跑。
    """
    clean = tmp_path / "clean-node"
    clean.mkdir()
    rc, out, err = run_cli("baseline", "--help", cwd=clean)
    assert rc == 0, f"在干净 cwd 执行 baseline --help 失败 rc={rc}\n{err}"
    assert "No module named" not in (out + err), "另一节点执行触发 ModuleNotFoundError"


def test_tmpl_005_missing_config_gives_clear_message(tmp_path):
    """TC-TMPL-005：配置缺失时给出明确提示，而非静默失败。"""
    proj = tmp_path / "proj-noconf"
    proj.mkdir()
    run_cli("init", cwd=proj)
    rc, out, err = run_cli("baseline", "check", "--format", "json", cwd=proj)
    text = (out + err).lower()
    # ⚠️ 空断言防护：下面这些「不该出现」的模式，才是本用例真正守卫的东西。
    #    若只断言「有输出或 rc==0」，那么命令根本不存在时也会通过（实测到过）。
    assert "no module named" not in text, "不应抛出模块错误（分发表路径错）"
    assert "invalid choice" not in text, "命令未被 CLI 识别（漏注册）"
    assert "traceback" not in text, "不应抛出未捕获异常"
    # 配置缺失时：要么给出明确提示（非 0 退出码），要么使用文档化的默认值（0）
    if rc != 0:
        assert (out + err).strip(), "非零退出但没有任何输出 —— 属于静默失败"


# --------------------------------------------------------------------------- #
# TC-TMPL-006 — 节点与阈值可配置
# --------------------------------------------------------------------------- #

def test_tmpl_006_config_drives_behaviour(tmp_path):
    """TC-TMPL-006：修改配置即改变行为，无需改代码。

    用 `tolerance_s` 的不同取值驱动 `baseline check` 的输出。
    """
    proj = tmp_path / "proj-cfg"
    proj.mkdir()
    run_cli("init", cwd=proj)
    cfg_dir = proj / ".fstdd" / "config.d"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "baseline.yaml").write_text(
        "samples: 3\ntolerance_s: 2.0\njitter_max_s: 1.0\ntimeout_s: 5\n",
        encoding="utf-8",
    )
    rc_a, out_a, err_a = run_cli("baseline", "check", "--format", "json", cwd=proj)

    (cfg_dir / "baseline.yaml").write_text(
        "samples: 3\ntolerance_s: 99.0\njitter_max_s: 1.0\ntimeout_s: 5\n",
        encoding="utf-8",
    )
    rc_b, out_b, err_b = run_cli("baseline", "check", "--format", "json", cwd=proj)

    # 配置改变 → JSON 中报告的 tolerance 必须跟着变
    def tol_of(out: str):
        try:
            payload = json.loads(out)
        except Exception:
            return None
        cfg = payload.get("config", payload)
        return cfg.get("tolerance_s")

    assert tol_of(out_a) == 2.0, f"tolerance_s=2.0 未生效: {out_a or err_a}"
    assert tol_of(out_b) == 99.0, f"tolerance_s=99.0 未生效（配置未被读取）: {out_b or err_b}"


# --------------------------------------------------------------------------- #
# timeutil（Slice 1 的另一半产出）
# --------------------------------------------------------------------------- #

def test_timeutil_utc_now_iso_is_timezone_aware():
    """`utc_now_iso()` 必须产出带时区的 ISO 8601。

    SC-010：CLI 新产出的时间字段 SHALL 匹配 `([+-]\\d{2}:\\d{2}|Z)$`。
    """
    spec = importlib.util.spec_from_file_location(
        "_fstdd_timeutil", UPSTREAM / "fstdd" / "cli" / "timeutil.py"
    )
    assert spec and spec.loader, "timeutil.py 不存在"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    value = mod.utc_now_iso()
    assert re.search(r"([+-]\d{2}:\d{2}|Z)$", value), f"naive 时间戳（无时区）: {value!r}"


def test_timeutil_normalize_eol_crlf_lf_and_lone_cr():
    """`normalize_eol()` 与 `tools/verify_eol.py` 同口径：三种形态都归一为 LF。"""
    spec = importlib.util.spec_from_file_location(
        "_fstdd_timeutil", UPSTREAM / "fstdd" / "cli" / "timeutil.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.normalize_eol(b"a\r\nb\r\n") == b"a\nb\n"
    assert mod.normalize_eol(b"a\rb") == b"a\nb"        # 孤立 CR
    assert mod.normalize_eol(b"a\nb\n") == b"a\nb\n"    # 幂等
    assert mod.normalize_eol(b"") == b""
