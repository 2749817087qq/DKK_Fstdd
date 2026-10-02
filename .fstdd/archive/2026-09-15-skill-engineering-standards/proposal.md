# skill 工程规范：元数据强制项 + 端到端冒烟 + 发布前清单

<!-- source_hash: ef7bfb45c217febf -->
<!-- generated_at: 2026-09-15T10:19:33.012488 -->
<!-- canonical: canonical/proposals/2026-09-15-skill-engineering-standards.yaml -->

## Why

我们在 STDD 首次完整跑通过程中（change 2026-09-15-crlf-eol-governance）暴露出
skill 工程体系的三处缺口，全部有实测数据支撑：

1) **校验只查「文件在位」，不查「能跑」**
   现有 `tools/verify_workbuddy_skills.py` 对 CLI 的检查只有一行 `CLI_ABS.exists()`，
   全脚本 `subprocess` / `run(` 出现次数为 **0**，即从不实际执行 CLI。
   后果：`.gitattributes` 缺失导致 commit 被 SIGTERM 这类问题，verify 报 PASS
   却完全发现不了——它只回答"文件写对了吗"，不回答"跑起来行吗"。

2) **许可与版本元数据大面积缺失**
   实测扫描本机两个 skill 目录共 40 个 skill：
     - name        40/40 有
     - description 40/40 有
     - version     17/40（缺 23）
     - license      3/40（缺 37）
     - 四项齐全      3/40
   私有使用无碍，但仓库一旦公开，37 个 skill 的许可状态无从判断。

3) **没有发布前检查清单**
   此前公开发布是靠临时判断（"感觉可以了"），没有可复现的检查项。
   凭证扫描、跨机器路径、端到端冒烟都依赖临场想起。


## What Changes

- 扩写 `tools/verify_workbuddy_skills.py`：在现有静态检查之外，增加
「CLI 端到端冒烟」——在临时目录实际执行 `stdd init` / `new` / `status`，
任一失败即 FAIL。使校验从"文件在位"升级为"确实能跑"。

- 新增 `tools/check_skill_metadata.py`：扫描指定 skill 目录，
校验每个 SKILL.md 的 frontmatter 四项（name / description / version / license），
输出缺失清单。默认**只报告不修改**（dry-run）；带 `--fix` 时为全部 skill
补齐缺失字段，取值遵循「宁可 unknown，不可猜测」原则：
  - license 缺失 → 写入 `unknown`（禁止推测第三方协议）
  - version 缺失 → 写入 `unknown`（禁止编造版本号）
理由：显式 `unknown` 优于字段缺失——后者无法区分「未检查」与「确知无」。
`--fix` 执行前**自动备份**到 `~/.workbuddy-ai/backups/skill-metadata-<时间戳>/`。

- 改造 `tools/install_workbuddy_skills.py` 生成的 frontmatter：
固定写入 `license`（声明来源与协议）与 `version` 字段，
使新安装的 skill 天生满足元数据规范。

- 新增 `docs/SKILL_RELEASE_CHECKLIST.md`：发布前清单，含
许可声明、凭证扫描、跨机器路径检查、端到端冒烟、元数据校验五项，
每项给出具体命令与通过判据。


### New Capabilities

- **skill-metadata-governance**：skill 元数据治理：扫描并报告 skill 的 name/description/version/license
完整度，缺失项可定位到具体 skill；安装器生成的 skill 天生合规。

- **skill-release-checklist**：发布前检查清单：把许可、凭证、路径、冒烟、元数据五项固化为
可执行的命令与判据，取代临场判断。


### Modified Capabilities

- **skill-runtime-verification**：校验能力升级：从静态文本检查扩展到实际执行 CLI 的端到端冒烟，
使"能跑"成为可断言的门禁项。


## Success Criteria

- [ ] `tools/verify_workbuddy_skills.py` 输出包含 CLI 冒烟结果，且脚本实际执行了 CLI（subprocess 调用数 > 0）
- [ ] 冒烟失败时脚本退出码非 0（可用临时破坏 CLI 路径的方式反向验证）
- [ ] `tools/check_skill_metadata.py` 能复现实测结论：40 个 skill 中 license 缺 37、version 缺 23
- [ ] 默认（无 --fix）运行时不修改任何 SKILL.md（运行前后文件哈希一致）
- [ ] `--fix` 前自动创建备份目录，且备份文件数 = 待修改文件数
- [ ] `--fix` 后全部 40 个 skill 四项元数据齐全，正文部分哈希与备份一致（证明只动了 frontmatter）
- [ ] `--fix` 后每个 SKILL.md 的 frontmatter 仍可被 YAML 解析（无语法损坏）
- [ ] `docs/SKILL_RELEASE_CHECKLIST.md` 存在，且五项检查各含可执行命令与通过判据
- [ ] 改造后 verify 在真实环境仍输出 PASS（即强化检查未引入假失败）
