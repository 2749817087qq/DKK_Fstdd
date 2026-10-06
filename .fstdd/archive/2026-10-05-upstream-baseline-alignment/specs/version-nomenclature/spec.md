# Spec: version-nomenclature

> Change: 2026-10-05-upstream-baseline-alignment | Auto-generated Human View

## Requirements

### Requirement: 全仓**活体声明面**（NOTICE.md、README.md、skills/fstdd-fin/SKILL.md、
docs/WORKBUDDY_INSTALL_NOTES.md、tools/install_workbuddy_skills.py）SHALL 按对象标注版本轴：
指称本仓 vendored 内核（`upstream/`）时 SHALL 用内核轴 K=3.1.0，
SHALL NOT 再把内核版本写作 3.0.5；指称上游外部项目最新发布时 SHALL 用外部锚 E 并显式标明为
「上游最新发布」。NOTICE §1 内 SHALL NOT 存在互相矛盾的版本声明。


#### Scenario: SC-001

- **GIVEN** NOTICE.md §1 表格写「版本 | V3.0.5（master 分支）」，同节注记写「上游版本号见 upstream/pyproject.toml（3.0.5）」，而该文件实测为 3.1.0
- **WHEN** 阅读 NOTICE.md §1 全文并核对其中每一处版本声明所指对象
- **THEN** SHALL 使 §1 中不再存在把本仓 vendored 内核版本标为 3.0.5 的表述
- **AND** E 轴（上游最新发布 v3.0.5）SHALL 显式标明为「上游最新发布」并附基线快照出处
- **AND** 指称 `upstream/` 内核版本处 SHALL 写 K=3.1.0
- **AND** §1 内任意两处版本声明 SHALL NOT 互相矛盾

#### Scenario: SC-002

- **GIVEN** README.md:5 徽章为 `upstream-leonai42%2Fstdd%20v3.0.5`，未标轴
- **WHEN** 阅读 README 头部徽章与引言区块
- **THEN** SHALL 使 README 头部同时显式呈现两个轴：上游外部发布（E）与本仓 vendored 内核（K）
- **AND** E 轴徽章标签 SHALL 明确为「上游发布/release」语义，不得被读成内核版本
- **AND** K 轴徽章 SHALL 呈现内核轴当前值 3.1.0
- **AND** README 引言 SHALL 保留「上游 leonai42/stdd（MIT）衍生作品」的署名事实

#### Scenario: SC-003

- **GIVEN** skills/fstdd-fin/SKILL.md 的 frontmatter 为 `stdd_version: "3.0.5-fin.2"`（:10），sources 行写「方法论基底: FSTDD V3.0.5 (MIT)」（:17）
- **WHEN** 读取 fstdd-fin 的 frontmatter 与 sources 段
- **THEN** SHALL 使 `stdd_version` 字段表达内核轴 K=3.1.0（纯 `[0-9.]+` 形态）
- **AND** sources 段的方法论基底 SHALL 指向内核轴 K
- **AND** 如保留上游溯源，SHALL 以 E 轴标注（源自上游 leonai42/stdd，MIT）
- **AND** `version` 字段（本 skill 自身版本）SHALL 保持不变

#### Scenario: SC-004

- **GIVEN** docs/WORKBUDDY_INSTALL_NOTES.md:5 写「来源仓库 …（master 分支，V3.0.5，MIT License）」，:89 写「Gate 3，V3.0.5 三阶段合一」
- **WHEN** 读取该文档中所有含版本号的表述
- **THEN** SHALL 使每处版本表述按对象落到正确轴（上游项目 → E；内核/方法学形态 → K）或去除歧义版本词
- **AND** SHALL NOT 出现把内核/方法学形态标为 3.0.5 的表述

#### Scenario: SC-005

- **GIVEN** 上述活体声明面已按 SC-001..SC-004 修正完成
- **WHEN** 对活体声明面执行「内核版本被写作 3.0.5」的定向扫描断言
- **THEN** SHALL 使命中数为 0
- **AND** 扫描范围 SHALL 覆盖 NOTICE.md、README.md、skills/fstdd-fin/SKILL.md、docs/WORKBUDDY_INSTALL_NOTES.md、tools/install_workbuddy_skills.py
- **AND** 扫描 SHALL NOT 覆盖 upstream/ 内上游自有文档与历史/临时区（.fstdd/archive/**、skills-archive/**、_scratch/**、artifacts/**）

### Requirement: `tools/install_workbuddy_skills.py` 生成的 skill SHALL 由机器可读版本源派生版本字段，
SHALL NOT 硬编码 3.0.5：frontmatter `version` SHALL 取发行版轴 R，
`stdd_version` SHALL 取内核轴 K；来源横幅与 module docstring SHALL NOT 写死版本号。


#### Scenario: SC-006

- **GIVEN** `_build_frontmatter()` 现以字面量输出 `version: "3.0.5"` 与 `stdd_version: "3.0.5"`（:304-305）
- **WHEN** 执行 `tools/install_workbuddy_skills.py --platform workbuddy` 生成 skill
- **THEN** SHALL 使生成 frontmatter 的 `version` 等于 `repo_stdd_version(REPO_ROOT)`（R=3.3.4）
- **AND** SHALL 使 `stdd_version` 等于 `upstream/` 内核轴 K=3.1.0，且为纯 `[0-9.]+` 形态
- **AND** SHALL NOT 在生成 frontmatter 中出现字面量 3.0.5

#### Scenario: SC-007

- **GIVEN** 来源横幅（:377）写「本 skill 来自开源项目 FSTDD … V3.0.5」，module docstring（:2）写「FSTDD (leonai42/stdd V3.0.5)」
- **WHEN** 执行安装脚本并读取生成 skill 的头部横幅与脚本源码 docstring
- **THEN** SHALL 使横幅描述 skill 正文来源时使用内核轴 K，SHALL NOT 写死 3.0.5
- **AND** 横幅 SHALL 保留上游项目名与源仓库 URL（https://github.com/leonai42/stdd）
- **AND** 横幅 SHALL 保留资源根目录与 CLI 入口的绝对路径适配（现有行为不变）
- **AND** module docstring SHALL 不含未标轴的硬编码版本号

#### Scenario: SC-008

- **GIVEN** 安装脚本已按 SC-006 / SC-007 去硬编码
- **WHEN** 依次重跑 `tools/install_workbuddy_skills.py` 与 `tools/verify_workbuddy_skills.py`
- **THEN** SHALL 使校验器输出 PASS（退出码 0）
- **AND** 生成戳 SHALL 仍为 `生成自 stdd-repo@3.3.4`（stamp_line(REPO_VERSION) 既有行为不变）
- **AND** `fstdd-deliver` 哨兵与静默回传策略块 SHALL 保持完整
- **AND** 路径适配断言（无 `python bin/stdd` 残留、无未替换 `.fstdd/skills/_shared/`）SHALL 保持通过

### Requirement: 本次口径修正 SHALL NOT 改变既有门禁的判定语义：`verify_rename` 的排除区与
`ALLOWED_OLD_MENTIONS` 保持原样、结果仍 8/8；`verify_eol` 7/7、`verify_skill_standards` 7/7 保持通过。


#### Scenario: SC-009

- **GIVEN** `verify_rename.py` 的排除区（含 upstream/ 等）与 `ALLOWED_OLD_MENTIONS`（含 `"STDD V3.0.5"`）在改动前已定义
- **WHEN** 在改动后执行 `tools/verify_rename.py`
- **THEN** SHALL 保持 8/8 通过
- **AND** `tools/verify_rename.py` 的排除区与白名单内容 SHALL 保持不变
- **AND** `upstream/` 内上游自有文档 SHALL 保持原样（未纳入本次改动）

#### Scenario: SC-010

- **GIVEN** `verify_skill_standards` 严格只认 frontmatter 的 `version` 字段，不认 `stdd_version`
- **WHEN** 在改动 fstdd-fin 的 `stdd_version` 与 sources 之后执行 `tools/verify_skill_standards.py` 与 `tools/verify_eol.py`
- **THEN** SHALL 使 `verify_skill_standards` 7/7 通过、`verify_eol` 7/7 通过
- **AND** `skills/fstdd-fin/SKILL.md` 的 `version` 字段 SHALL 保持 1.0.0 不变
- **AND** 改动后的文件 SHALL 满足行尾符治理（LF）要求
