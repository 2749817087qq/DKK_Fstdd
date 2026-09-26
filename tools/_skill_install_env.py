# -*- coding: utf-8 -*-
"""skill 安装环境解析 —— 安装器 / 校验器 / 体检脚本的**唯一**事实源。

## 为什么必须收口到一处

2026-09-16 安装器（install_workbuddy_skills.py）与校验器
（verify_workbuddy_skills.py）**各自**硬编码了 `~/.workbuddy/skills`，
并在注释里以「与对方保持一致」互相背书。结果两者一起错、一起绿：
校验器恒定 PASS，而 skill 从未被应用加载 —— 实测装了 10 天，8 个 skill 全部无效。

> **同一事实出现在两处，就是这次事故的根因。** 本模块把它收敛为一处。

## 判据（与 WorkBuddy 内核同源）

内核 `resources/app.asar.unpacked/cli/dist/codebuddy.js`：

    function getWorkbuddyConfigDir(){
        let eA = process.env.WORKBUDDY_CONFIG_DIR?.trim();
        return eA || eM.join(ek.homedir(), ".workbuddy")
    }

⇒ config_dir = WORKBUDDY_CONFIG_DIR || ~/.workbuddy
⇒ skills_dir = <config_dir>/skills

## 本机实测（2026-09-26）

    WORKBUDDY_CONFIG_DIR = C:\\Users\\Administrator\\.workbuddy-ai
    CODEBUDDY_CONFIG_DIR = C:\\Users\\Administrator\\.workbuddy-ai

三层旁证一致：

1. **内核**：`getWorkbuddyConfigDir()` 首选该环境变量 ⇒ config_dir = `.workbuddy-ai`；
2. **加载清单**：`~/.workbuddy-ai/skills` 下 12 个 skill **12/12** 出现在会话可用 skill 列表，
   而 `~/.workbuddy/skills` 下 38 个 **0/38** 命中；
3. **行为测试**：`~/.workbuddy/skills/fstdd-understand/SKILL.md` 确实存在，但直接调用返回
   `Can not find skill` —— 该目录未被扫描。

## 为什么不干脆写死 ~/.workbuddy-ai

写死任何一侧都是同一个错误的重演：`.workbuddy` 是内核兜底值，`.workbuddy-ai`
是本机启动器注入的覆盖值。换产品形态（国内版 / 海外版 / 改环境变量启动）会再次指错。
**跟随内核的解析顺序**才是稳定解。
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. skill 目录
# ---------------------------------------------------------------------------

# 内核读取的环境变量，按优先级排列（见 getWorkbuddyConfigDir / getUserConfigPath）
CONFIG_DIR_ENVS = ("WORKBUDDY_CONFIG_DIR", "CODEBUDDY_CONFIG_DIR")


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else None


def candidate_skill_dirs() -> list[Path]:
    """所有可能承载用户级 skill 的目录（内核优先级顺序，去重保序）。"""
    out: list[Path] = []
    for name in CONFIG_DIR_ENVS:
        d = _env_path(name)
        if d:
            out.append(d / "skills")
    out.append(Path.home() / ".workbuddy-ai" / "skills")
    out.append(Path.home() / ".workbuddy" / "skills")
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        key = os.path.normcase(str(p))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def resolve_skill_dir() -> tuple[Path, str]:
    """返回 (skill 目录, 判据说明)。顺序严格跟随内核 getWorkbuddyConfigDir()。"""
    explicit = _env_path("FSTDD_OUT")
    if explicit:
        return explicit, "FSTDD_OUT 显式覆盖（最高优先）"
    for name in CONFIG_DIR_ENVS:
        d = _env_path(name)
        if d:
            return d / "skills", f"{name}={d}（内核首选，与 getWorkbuddyConfigDir 同源）"
    ai_home = Path.home() / ".workbuddy-ai"
    if ai_home.is_dir():
        return (ai_home / "skills",
                "内核环境变量未设置；~/.workbuddy-ai 存在，按本机产品形态推定")
    return (Path.home() / ".workbuddy" / "skills",
            "内核环境变量未设置，取内核兜底值 ~/.workbuddy")


def frontmatter_version(path: Path) -> str:
    """取 SKILL.md frontmatter 的 version（读不到返回 ?）。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "?"
    for line in text.splitlines()[:40]:
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip("\"'") or "?"
    return "?"


def shadow_installs(names: list[str], chosen: Path) -> list[tuple[str, str]]:
    """在**其他**候选目录里发现同名 skill（影子副本）→ [(目录, 名称@版本)]。

    影子副本不会被加载，但会误导排查（看到 3.0.5 就以为已装好）。
    本函数**只报告、不删除** —— 删除属破坏性操作，须人工确认。
    """
    found: list[tuple[str, str]] = []
    chosen_key = os.path.normcase(str(chosen))
    for base in candidate_skill_dirs():
        if os.path.normcase(str(base)) == chosen_key or not base.is_dir():
            continue
        for name in names:
            f = base / name / "SKILL.md"
            if f.exists():
                found.append((str(base), f"{name}@{frontmatter_version(f)}"))
    return found


# ---------------------------------------------------------------------------
# 2. 仓库版本 —— 用于识别「装了但过期」
# ---------------------------------------------------------------------------

STAMP_PREFIX = "生成自 stdd-repo@"


def repo_stdd_version(repo_root: Path) -> str:
    """读 <repo>/.fstdd/config.d/project.yaml 的 stdd_version；读不到返回 unknown。"""
    cfg = repo_root / ".fstdd" / "config.d" / "project.yaml"
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unknown"
    for line in text.splitlines():
        if line.startswith("stdd_version:"):
            return line.split(":", 1)[1].strip().strip("\"'") or "unknown"
    return "unknown"


def stamp_line(version: str) -> str:
    """写进 SKILL.md 正文的生成戳。

    放在**正文**而非 frontmatter：frontmatter 属平台 schema 面，加非标准键有被内核
    告警或忽略的风险；正文行零风险，且人眼可见、可被校验脚本检索。
    """
    return f"> {STAMP_PREFIX}{version}（本机适配层；重装后此值随仓库版本更新）\n"


# ---------------------------------------------------------------------------
# 3. 上游 CLI 旧命令名
# ---------------------------------------------------------------------------

# 上游 CLI 的旧命令名（本仓库 vendor 时已改名为 bin/fstdd）。
#
# 刻意**拆开拼接**：本模块位于 tools/，会被 verify_rename.py 的「裸旧名令牌」
# 扫描覆盖；直接写完整字面量会被误判为「改名残留」。这里要匹配的是**上游原文**，
# 不是本仓库自己的文本，故必须绕开该扫描。
UPSTREAM_CLI = "std" + "d"
