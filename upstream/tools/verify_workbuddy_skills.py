# -*- coding: utf-8 -*-
"""校验 WorkBuddy 全局 STDD skill 的本机策略与路径适配是否仍然在位。

用途：升级 / 重装 / 手动覆盖 skill 文件之后必须运行。
退出码：0 = 全部通过；1 = 存在 FAIL 项（此时禁止继续 DELIVER 相关操作）。

用法：
    "C:\\Python311\\python.exe" "C:/Users/Administrator/.workbuddy-ai/stdd/tools/verify_workbuddy_skills.py"
"""
from pathlib import Path
import sys

SRC = Path(r"C:\Users\Administrator\.workbuddy-ai\stdd")
OUT = Path(r"C:\Users\Administrator\.workbuddy-ai\skills")
SHARED_ABS = (SRC / ".fstdd" / "skills" / "_shared").as_posix()
CLI_ABS = SRC / "bin" / "stdd"
SENTINEL = "STDD_LOCAL_POLICY_NO_UPLOAD_V1"

EXPECTED = [
    "stdd",
    "stdd-understand",
    "stdd-spec",
    "stdd-build",
    "stdd-deliver",
    "stdd-upgrade",
]


def main() -> int:
    fails, warns = [], []

    # 前置：本机依赖与 CLI 是否可用
    if not CLI_ABS.exists():
        fails.append(f"STDD CLI 不存在: {CLI_ABS}")
    try:
        import yaml  # noqa: F401
        import jinja2  # noqa: F401
    except ModuleNotFoundError as e:
        fails.append(f"当前解释器缺少依赖 {e.name}，请改用 C:\\Python311\\python.exe")

    for name in EXPECTED:
        f = OUT / name / "SKILL.md"
        if not f.exists():
            fails.append(f"{name}: SKILL.md 不存在")
            continue
        text = f.read_text(encoding="utf-8")

        if f"name: {name}" not in text:
            fails.append(f"{name}: frontmatter name 缺失或不匹配")

        if name == "stdd-deliver":
            if SENTINEL not in text:
                fails.append(f"{name}: 安全策略哨兵缺失（{SENTINEL}）—— 上传防线已被抹掉")
            if "升级 / 重装后必做" not in text:
                fails.append(f"{name}: 缺少「升级后必做」规程")

        if name == "stdd-upgrade" and "升级 / 重装后必做" not in text:
            fails.append(f"{name}: 缺少「升级后必做」规程")

        if "python bin/stdd" in text:
            fails.append(f"{name}: 残留未替换的 `python bin/stdd`")

        if ".fstdd/skills/_shared/" in text and SHARED_ABS not in text:
            fails.append(f"{name}: 残留未替换的相对路径 .fstdd/skills/_shared/")

        if "C:/Users/Administrator/.workbuddy-ai/stdd" not in text and name != "stdd":
            warns.append(f"{name}: 未发现本机绝对资源路径，可能是未经适配的上游原件")

    print("=" * 60)
    print("STDD 全局 skill 校验")
    print("=" * 60)
    for w in warns:
        print(f"  [WARN] {w}")
    if fails:
        print(f"\n[FAIL] {len(fails)} 项未通过：")
        for x in fails:
            print(f"  - {x}")
        print("\n修复方式：重跑安装脚本")
        print('  "C:\\Python311\\python.exe" '
              '"C:/Users/Administrator/.workbuddy-ai/stdd/tools/install_workbuddy_skills.py"')
        return 1
    print(f"[PASS] {len(EXPECTED)} 个 skill 全部通过：安全策略在位、路径适配完好")
    return 0


if __name__ == "__main__":
    sys.exit(main())
