# FSTDD 安装层去 WorkBuddy 硬编码：一套共享正文 + 每平台薄清单 + 参数化 installer

<!-- source_hash: 76a26617e3384428 -->
<!-- generated_at: 2026-09-30T06:47:44+00:00 -->
<!-- canonical: canonical/proposals/2026-09-30-multi-platform-adapters.yaml -->

## Why

本仓库的 FSTDD 安装层**写死了 WorkBuddy**：`tools/install_workbuddy_skills.py`
没有 platform 参数、输出目录由 `tools/_skill_install_env.py` 只按 WorkBuddy
内核判据解析（`WORKBUDDY_CONFIG_DIR || ~/.workbuddy`）、`install.sh` / `install.ps1`
默认 `~/.workbuddy-ai/skills`、校验脚本同样只认 WorkBuddy。而 `upstream/.fstdd/platforms/`
已带 6 平台适配（aider / claude-code / copilot / cursor / trae / workbuddy）——
上游本就是「一套核心 Skill → 多平台生成适配文件」，本仓库的安装层却在分发侧
把这条能力收窄成单一平台，其他平台用户无法安装。

2026-09-30 用户已裁定方向：**产物 = 一套共享 skill 正文 + 每平台薄清单
（安装路径 + front-matter 规则）+ 参数化 installer（加 --platform，读 platforms.yaml）**，
**禁止**产出 N 份手写适配分支——那会随版本漂移，且与上游「一套核心」的
设计初衷相悖。


## What Changes

- 新增平台薄清单 `platforms.yaml`（每平台：显示名、skill 根目录解析规则、
front-matter 规则——是否写 version / trigger_keywords、description 形态、
文件形态），作为多平台适配的**唯一事实源**。

- `tools/install_workbuddy_skills.py` 增 `--platform`（默认 workbuddy，保持现有
行为逐字节不变），按 platforms.yaml 渲染 front-matter 与输出目录。

- `install.sh` / `install.ps1` 增 `--platform` / `-Platform` 透传，README 快速开始
补多平台说明。

- `tools/verify_workbuddy_skills.py` 增平台感知（默认仍 workbuddy），或抽出通用
校验入口，保证「装哪平台就校验哪平台」。

- 按序铺平台：① Claude Code（上游 6 文件已齐、标准路径 `~/.claude/skills`）→
② Trae（与 workbuddy 同构，本机装有 Trae，可端到端自验）→ ③ Cursor →
④ Copilot / Aider 缓。**Qoder 暂不做**（上游零适配、装载约定未知、本机未安装，
盲写等于产出不可验证的伪适配）。


### New Capabilities

- **多平台 skill 安装**：通过 `--platform` 选择目标平台，把同一套 FSTDD 共享正文安装为该平台的
skill 形态；新增平台只需在 platforms.yaml 增一条清单，不新增代码分支。


### Modified Capabilities

- **WorkBuddy skill 安装（既有）**：保持为 platforms.yaml 中的一条清单；`--platform workbuddy`（默认）产出
与本次变更前**逐字节一致**，作为回归保护。


## Success Criteria

- [ ] `--platform workbuddy`（默认）的产出与变更前逐字节一致（回归不破）
- [ ] `--platform claude-code` 产出 `<claude skills 根>/<name>/SKILL.md`，其 front-matter 符合 Claude Code 规则（无 version / trigger_keywords，description 引号形态）
- [ ] 仓库内不存在按平台复制的手写正文分支：任一平台 skill 的正文与共享源同源可验（无第二份正文副本）
- [ ] 新增一个平台只需修改 platforms.yaml，不新增 if/else 平台分支代码（以代码审查 + 用例断言）
- [ ] `install.sh --platform <p>` 与 `install.ps1 -Platform <p>` 端到端可装并通过对应平台校验（至少 claude-code 与 trae 实测）
