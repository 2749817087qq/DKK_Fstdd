# -*- coding: utf-8 -*-
"""校验 WorkBuddy 全局 FSTDD skill 的本机策略与路径适配是否仍然在位。

用途：升级 / 重装 / 手动覆盖 skill 文件之后必须运行。
退出码：0 = 全部通过；1 = 存在 FAIL 项（此时禁止继续 DELIVER 相关操作）。

用法：
    "C:\\Python311\\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/tools/verify_workbuddy_skills.py"
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

# 与安装脚本一致：默认自动定位，可用 FSTDD_SRC / FSTDD_OUT 覆盖
SRC = Path(os.environ.get("FSTDD_SRC", Path(__file__).resolve().parent.parent / "upstream"))
# 与 install_workbuddy_skills.py 保持一致：WorkBuddy 实际加载的是 ~/.workbuddy/skills
OUT = Path(os.environ.get("FSTDD_OUT", Path.home() / ".workbuddy" / "skills"))
SHARED_ABS = (SRC / ".fstdd" / "skills" / "_shared").as_posix()
# FSTDD_CLI 用于故障注入测试：指向不可用时校验必须 FAIL，不得静默通过
CLI_ABS = Path(os.environ.get("FSTDD_CLI", str(SRC / "bin" / "fstdd")))
PY = os.environ.get("FSTDD_PY", sys.executable)
SENTINEL = "FSTDD_LOCAL_POLICY_NO_UPLOAD_V1"

# 静默回传策略块的必备标记。
# 只查哨兵是不够的：哨兵可能被留在文件里而策略正文被换回旧口径（如「默认禁用，
# 需用户显式授权」）或被整段删掉 —— 那时防线实际上已经失效，必须一并 FAIL。
DELIVER_SHARE_MARKERS = ("share_experience.py", "--silent", "FSTDD_NO_SHARE")

EXPECTED = [
    "fstdd",
    "fstdd-understand",
    "fstdd-spec",
    "fstdd-build",
    "fstdd-deliver",
    "fstdd-upgrade",
]


def smoke_test() -> tuple[bool, str]:
    """CLI 端到端冒烟：在临时目录实际执行 init / new / status。

    只检查「文件在位」是不够的 —— 文件存在但跑不起来时静态检查照样通过。
    """
    if not CLI_ABS.exists():
        return False, f"CLI 不存在: {CLI_ABS}"

    tmp = Path(tempfile.mkdtemp(prefix="stdd_smoke_"))
    try:
        for args in (["init"], ["new", "smoke"], ["status"]):
            r = subprocess.run(
                [PY, str(CLI_ABS), *args],
                cwd=str(tmp), capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip().splitlines()
                hint = tail[-1] if tail else "无输出"
                return False, f"`fstdd {' '.join(args)}` 退出码 {r.returncode}：{hint}"
        return True, "init / new / status 均通过"
    except OSError as e:
        return False, f"CLI 执行异常（环境问题而非 skill 问题）：{e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    fails, warns = [], []

    # 前置：本机依赖与 CLI 是否可用
    if not CLI_ABS.exists():
        fails.append(f"FSTDD CLI 不存在: {CLI_ABS}")
    try:
        import yaml  # noqa: F401
        import jinja2  # noqa: F401
    except ModuleNotFoundError as e:
        fails.append(
            f"当前解释器缺少依赖 {e.name}。请 pip install pyyaml jinja2，"
            f"或用 FSTDD_PY 指定已装依赖的解释器"
        )

    for name in EXPECTED:
        f = OUT / name / "SKILL.md"
        if not f.exists():
            fails.append(f"{name}: SKILL.md 不存在")
            continue
        text = f.read_text(encoding="utf-8")

        if f"name: {name}" not in text:
            fails.append(f"{name}: frontmatter name 缺失或不匹配")

        if name == "fstdd-deliver":
            if SENTINEL not in text:
                fails.append(f"{name}: 安全策略哨兵缺失（{SENTINEL}）—— 上传防线已被抹掉")
            for marker in DELIVER_SHARE_MARKERS:
                if marker not in text:
                    fails.append(
                        f"{name}: 静默回传策略块不完整（缺 `{marker}`）"
                        f"—— 策略可能被上游覆盖或降级为旧口径")
            if "升级 / 重装后必做" not in text:
                fails.append(f"{name}: 缺少「升级后必做」规程")

        if name == "fstdd-upgrade" and "升级 / 重装后必做" not in text:
            fails.append(f"{name}: 缺少「升级后必做」规程")

        if "python bin/fstdd" in text:
            fails.append(f"{name}: 残留未替换的 `python bin/fstdd`")

        if ".fstdd/skills/_shared/" in text and SHARED_ABS not in text:
            fails.append(f"{name}: 残留未替换的相对路径 .fstdd/skills/_shared/")

        if SRC.as_posix() not in text and name != "fstdd":
            warns.append(f"{name}: 未发现资源绝对路径（期望含 {SRC.as_posix()}），可能是未经适配的上游原件")

    # 运行时冒烟：确认 CLI 真的能跑，而不只是文件存在
    smoke_ok, smoke_msg = smoke_test()
    if not smoke_ok:
        fails.append(f"CLI 端到端冒烟失败：{smoke_msg}")

    print("=" * 60)
    print("FSTDD 全局 skill 校验")
    print("=" * 60)
    print(f"  [{'PASS' if smoke_ok else 'FAIL'}] CLI 冒烟：{smoke_msg}")
    for w in warns:
        print(f"  [WARN] {w}")
    if fails:
        print(f"\n[FAIL] {len(fails)} 项未通过：")
        for x in fails:
            print(f"  - {x}")
        print("\n修复方式：重跑安装脚本")
        print('  "C:\\Python311\\python.exe" '
              '"C:/Users/Administrator/.workbuddy-ai/Fstdd/tools/install_workbuddy_skills.py"')
        return 1
    print(f"[PASS] {len(EXPECTED)} 个 skill 全部通过：安全策略在位、路径适配完好")
    return 0


if __name__ == "__main__":
    sys.exit(main())
