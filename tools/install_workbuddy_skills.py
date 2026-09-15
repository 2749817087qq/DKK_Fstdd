# -*- coding: utf-8 -*-
"""把 STDD (leonai42/stdd V3.0.5) 的 skill 层安装为 WorkBuddy 全局 skill。"""
from pathlib import Path
import os
import re
import sys

# 上游代码：随本仓库 vendor 在 upstream/ 下，故默认按脚本位置自动定位。
# 也可用环境变量覆盖：STDD_SRC / STDD_OUT / STDD_PY
SRC = Path(os.environ.get("STDD_SRC", Path(__file__).resolve().parent.parent / "upstream"))
OUT = Path(os.environ.get("STDD_OUT", Path.home() / ".workbuddy-ai" / "skills"))
SHARED_ABS = (SRC / ".stdd" / "skills" / "_shared").as_posix()
CLI_ABS = (SRC / "bin" / "stdd").as_posix()
PY = os.environ.get("STDD_PY", sys.executable)
PY_CMD = f'"{PY}" "{CLI_ABS}"'

# 本机工具脚本绝对路径：随仓库位置自动定位，避免重装命令指向已删除的旧目录
TOOLS_DIR = Path(__file__).resolve().parent
INSTALL_ABS = (TOOLS_DIR / "install_workbuddy_skills.py").as_posix()
VERIFY_ABS = (TOOLS_DIR / "verify_workbuddy_skills.py").as_posix()


def _check_runtime_deps() -> None:
    """STDD CLI 需要 PyYAML 与 Jinja2，缺了会在 init 时才炸，提前提醒。"""
    missing = []
    for mod in ("yaml", "jinja2"):
        try:
            __import__(mod)
        except ModuleNotFoundError:
            missing.append(mod)
    if missing:
        print(f"[WARN] 解释器 {PY} 缺少依赖: {', '.join(missing)}")
        print(f"       请执行: \"{PY}\" -m pip install pyyaml jinja2")
        print("       或设置 STDD_PY 指向已装依赖的解释器")

SKILLS = [
    dict(
        key="understand",
        name="stdd-understand",
        desc="STDD Phase 1 需求理解与确认：把模糊需求转化为可验证的变更提案（canonical/proposals/<change>.yaml + proposal.md），"
             "并执行自动提案审查、复杂度评分与模式建议，最后经用户确认 Gate 1 锁定。",
        kw="stdd-understand、需求理解、需求分析、变更提案、写 proposal、proposal 起草、STDD 第一步、STDD Phase 1",
    ),
    dict(
        key="spec",
        name="stdd-spec",
        desc="STDD Phase 2 规格设计与测试方案：把已确认的 proposal 转化为技术设计（design.md）、GIVEN/WHEN/THEN 行为规格（specs）"
             "与带 TC-ID 映射的测试方案（test-plan.md），经用户确认 Gate 2 锁定设计基线。",
        kw="stdd-spec、规格设计、写规格、spec 设计、GIVEN WHEN THEN、行为规格、测试方案、test plan、STDD Phase 2",
    ),
    dict(
        key="build",
        name="stdd-build",
        desc="STDD Phase 3 BUILD（切片规划 + TDD 实现 + 质量验证三合一）：拆分垂直切片，逐切片执行 RED→GREEN→REFACTOR，"
             "记录设计偏离，最后做全量质量验证与失败模式检查，生成 test-report 并经用户确认 Gate 3。",
        kw="stdd-build、stdd-slice、stdd-verify、TDD 实现、切片规划、切片拆分、写测试、RED GREEN REFACTOR、质量验证、覆盖率、STDD Phase 3",
    ),
    dict(
        key="deliver",
        name="stdd-deliver",
        desc="STDD Phase 4 交付：归档 change、合并 specs 与项目索引、更新文档、Git commit/tag，完成变更闭环。",
        kw="stdd-deliver、交付、归档 change、合并 specs、发布变更、STDD Phase 4",
    ),
    dict(
        key="upgrade",
        name="stdd-upgrade",
        desc="STDD 技能层升级：从官方仓库同步 .stdd/ 静态资源快照与全局技能版本，处理版本漂移与锁定状态。",
        kw="stdd-upgrade、STDD 升级、升级 stdd、同步 stdd 版本、stdd 版本漂移",
    ),
]


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4:].lstrip("\n")


def adapt(body: str) -> str:
    body = body.replace(".stdd/skills/_shared/", SHARED_ABS + "/")
    body = body.replace("python bin/stdd", PY_CMD)
    body = body.replace("`stdd ", "`" + PY_CMD + " ")
    body = body.replace("`python \"{CLI_ABS}\"`".format(CLI_ABS=CLI_ABS), "`" + PY_CMD + "`")
    return body


# 可被 grep 的哨兵：verify 脚本依赖它判断"本机安全策略是否仍然在位"
SENTINEL = "STDD_LOCAL_POLICY_NO_UPLOAD_V1"

# 锚点：上游 deliver.md 的经验上传小节。上游改版后该文本可能消失，
# 因此插入失败绝不允许静默 —— 走兜底 + 写后校验。
DELIVER_ANCHOR = "### Step 2.8: 经验自动上传（V2.9.6）\n"

SECURITY_NOTE_DELIVER = (
    f"> ⛔ **[本机安装策略：默认禁用]**<!-- {SENTINEL} --> 本步骤会把项目沉淀的经验上传到 STDD 外部社区 Git 仓库，"
    "属于数据外发行为。除非用户在本轮对话中显式要求上传，否则一律跳过并输出 "
    "`经验上传: 已按本机策略跳过（默认禁用，需用户显式授权）`。"
    f"用户确需时再手动执行 `{PY_CMD} experience share <EXP-ID>`。\n\n"
)

# 兜底策略块：当锚点不存在时，整段前置到正文最前面（不依赖任何上游文本）
SECURITY_BLOCK_DELIVER = (
    f"## ⛔ 本机安全策略（{SENTINEL}）\n\n"
    "> 本 skill 中任何「上传 / share / 外发经验到社区仓库」的步骤（如 Deliver 阶段的经验上传），"
    "**默认一律跳过**，除非用户在本轮对话中显式要求。\n"
    "> 跳过时输出：`经验上传: 已按本机策略跳过（默认禁用，需用户显式授权）`。\n"
    f"> 用户确需时再手动执行 `{PY_CMD} experience share <EXP-ID>`。\n\n"
    "> ⚠️ 本策略由本地安装脚本施加。**任何升级 / 重装 / 版本同步之后都会失效**，"
    "必须重跑安装与校验脚本，详见文末「升级后必做」。\n\n"
)

# 升级后必做：硬编码进 upgrade skill 与总入口，防止防线被静默抹掉
UPGRADE_DUTY = f"""
## ⛔ 升级 / 重装后必做（本机硬性规程）

上游升级（`/stdd-upgrade`、重新拉取仓库、手动覆盖 skill 文件）会**直接覆盖本文件**，
本机施加的安全策略与路径适配会随之消失，且**不会有任何提示**。因此：

**每次升级后，必须立即执行以下两步，缺一不可：**

```
"{PY}" "{INSTALL_ABS}"
"{PY}" "{VERIFY_ABS}"
```

- 第 1 步重新生成本机适配后的 skill（含安全策略、绝对路径、Python 解释器绑定）
- 第 2 步校验策略哨兵 `STDD_LOCAL_POLICY_NO_UPLOAD_V1` 是否仍在位
- **第 2 步输出 FAIL 时，禁止继续任何 DELIVER 相关操作**，先修复再继续

升级后如未执行上述步骤即进入 Deliver 阶段，视为**流程违规**。
"""


def apply_deliver_policy(body: str, errors: list) -> str:
    """施加经验上传禁用策略。锚点命中 → 就地插入；锚点失效 → 整段兜底前置。绝不静默。"""
    if DELIVER_ANCHOR in body:
        body = body.replace(
            DELIVER_ANCHOR,
            DELIVER_ANCHOR + "\n" + SECURITY_NOTE_DELIVER,
            1,
        )
    else:
        print("  [WARN] deliver 锚点未命中（上游可能已改版），改用兜底策略块前置")
        body = SECURITY_BLOCK_DELIVER + body

    # 兜底之上再加一层：无论哪条路径，都必须有 header 级声明
    if SENTINEL not in body:
        body = SECURITY_BLOCK_DELIVER + body
    return body


def main() -> int:
    _check_runtime_deps()
    if not SRC.exists():
        print(f"[FAIL] 未找到上游代码: {SRC}")
        print("       请确认 upstream/ 存在，或用 STDD_SRC 指定路径")
        return 1

    src_skills = SRC / ".stdd" / "skills"
    installed = []
    errors = []

    for s in SKILLS:
        src_file = src_skills / f"{s['key']}.md"
        if not src_file.exists():
            print(f"[SKIP] 源文件不存在: {src_file}")
            continue
        body = adapt(strip_frontmatter(src_file.read_text(encoding="utf-8")))

        if s["key"] == "deliver":
            body = apply_deliver_policy(body, errors)
            body += "\n---\n" + UPGRADE_DUTY
        if s["key"] == "upgrade":
            body += "\n---\n" + UPGRADE_DUTY

        header = (
            "> 本 skill 来自开源项目 STDD (Spec+Test Driven Development) V3.0.5，"
            "源仓库 https://github.com/leonai42/stdd ，已适配 WorkBuddy 全局 skill 目录。\n"
            f"> 静态资源与共享片段根目录：`{SRC.as_posix()}`\n"
            f"> CLI 入口：`{PY_CMD}`（该解释器已具备 PyYAML / Jinja2 依赖）\n"
            "> 首次在某项目使用 STDD 前，需先在该项目根目录执行初始化："
            f'`{PY_CMD} init` —— 生成 `.stdd/` 骨架、模板与项目状态文件。\n\n'
        )

        fm = (
            "---\n"
            f"name: {s['name']}\n"
            "description: |\n"
            f"  {s['desc']}\n"
            f"  触发词：{s['kw']}\n"
            'version: "3.0.5"\n'
            'stdd_version: "3.0.5"\n'
            "license: MIT（上游 STDD leonai42/stdd，版权归杭州大道一以科技有限公司；\n"
            "  本文件为其在 WorkBuddy 平台的适配版本，含本地安全策略与路径适配）\n"
            "source: https://github.com/leonai42/stdd\n"
            "---\n\n"
        )

        content = fm + header + body
        dest_dir = OUT / s["name"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "SKILL.md").write_text(content, encoding="utf-8")

        # 写后校验：策略在位 + 路径适配无残留（防止静默失效）
        name = s["name"]
        if s["key"] == "deliver" and SENTINEL not in content:
            errors.append(f"{name}: 安全策略哨兵缺失（{SENTINEL}）")
        if "python bin/stdd" in content:
            errors.append(f"{name}: 残留未替换的 `python bin/stdd`")
        if ".stdd/skills/_shared/" in content and SHARED_ABS not in content:
            errors.append(f"{name}: 残留未替换的相对路径 .stdd/skills/_shared/")
        if f"name: {name}" not in content:
            errors.append(f"{name}: frontmatter name 缺失或不匹配")

        installed.append(name)
        print(f"[OK] {name} -> {dest_dir / 'SKILL.md'}")

    # 总入口 skill
    entry_dir = OUT / "stdd"
    entry_dir.mkdir(parents=True, exist_ok=True)
    entry = f"""---
name: stdd
description: |
  STDD（Spec+Test Driven Development）总入口：Spec 先行 + TDD 执行的 AI 辅助研发流程，
  四阶段（UNDERSTAND → SPEC → BUILD → DELIVER）+ 三道用户确认门 + 失败模式检查。
  负责判断项目是否已初始化 STDD、路由到正确的阶段 skill，并说明 CLI 与静态资源位置。
  触发词：STDD、stdd、spec 驱动开发、测试驱动开发、TDD 流程、规约驱动、四阶段流程、用 STDD 开发。
stdd_version: "3.0.5"
source: https://github.com/leonai42/stdd
---

# STDD 总入口（WorkBuddy 全局安装）

## 这是什么

STDD = **Spec 先行 + TDD 执行**。先定义行为（GIVEN/WHEN/THEN 规格），再写测试，最后实现代码。
四阶段 + 三道强制用户确认门（Gate 1/2/3），把模糊需求变成有据可查、有测可验的交付。

| 阶段 | 触发 skill | 主要产出 | 确认门 |
|------|-----------|---------|--------|
| P1 UNDERSTAND | `stdd-understand` | canonical/proposals/<change>.yaml、proposal.md | Gate 1 |
| P2 SPEC | `stdd-spec` | design.md、specs/*.md、test-plan.md | Gate 2（最关键） |
| P3 BUILD | `stdd-build` | slices、TDD 实现、test-report.md | Gate 3 |
| P4 DELIVER | `stdd-deliver` | archive、合并 specs、git tag | 无 |

## 本机安装位置

- 静态资源与模板：`{SRC.as_posix()}`
- CLI 入口：`{PY_CMD}`
  - 依赖 PyYAML / Jinja2，本机使用 `C:\\Python311\\python.exe`（已具备）；换成其他解释器请先确认依赖
- 已安装的阶段 skill：`{OUT.as_posix()}` 下的 `stdd-understand/` `stdd-spec/` `stdd-build/` `stdd-deliver/` `stdd-upgrade/`

## 首次使用（必须先初始化项目）

在**项目根目录**执行：

```
{PY_CMD} init
```

生成 `.stdd/` 骨架（模板、config.d、rules、knowledge 等）与项目状态文件。
未初始化的项目，阶段 skill 中引用的 `.stdd/templates/*`、`.stdd/config.d/*` 将不存在，流程无法完整执行。

## 路由规则

1. 用户提出一个模糊需求，要做功能/改造 → `stdd-understand`
2. proposal 已确认，要设计规格与测试方案 → `stdd-spec`
3. 规格已确认，要实现（切片 + TDD + 验证） → `stdd-build`
4. 验证通过，要归档交付 → `stdd-deliver`
5. 提示版本漂移或要升级 → `stdd-upgrade`
6. **当前项目没有 `.stdd/` 目录时，一律先执行初始化再进入任何阶段。**

## 安全提示（本机策略）

- `stdd-deliver` 的 Step 2.8「经验自动上传社区」默认**禁用**（会向外部仓库外发项目经验），
  仅当用户显式要求时才执行。该策略带哨兵标记 `{SENTINEL}`，可被校验脚本检测。
- `stdd-upgrade` 会从 `raw.githubusercontent.com` 拉取文件覆盖本地 `.stdd/` 静态资源，属用户主动触发的联网行为。

{UPGRADE_DUTY}
"""
    (entry_dir / "SKILL.md").write_text(entry, encoding="utf-8")
    if SENTINEL not in entry or "Python311" not in entry:
        errors.append("stdd: 总入口缺少安全策略或升级规程说明")
    installed.append("stdd")
    print(f"[OK] stdd -> {entry_dir / 'SKILL.md'}")

    print("\n已安装 skill:", ", ".join(installed))
    if errors:
        print("\n[FAIL] 校验未通过，以下问题必须修复后才能使用：")
        for e in errors:
            print("  - " + e)
        return 1
    print("[PASS] 全部 skill 已通过安全策略与路径适配校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
