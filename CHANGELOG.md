# 更新日志（CHANGELOG）

本文件记录**每个版本新增了什么、以及它带来什么帮助**。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

> **维护规矩**：见 `.fstdd/standards/release-and-docs.md`《发布与文档规程》——
> **每个版本必须同时更新本文件 + 发 GitHub Release**，否则**不得打 tag**。

---

## [Unreleased]

### 门禁 / 改名一致性
- **发布硬门禁 `verify_rename.py` 由 6/8 恢复到 8/8**（spec SC-007 要求 `verify_eol` 7/7 且
  `verify_rename` 8/8，二者此前均被本项阻塞）：
  - **TC-RENAME-002**：`canonical/` 三份权威 YAML（`specs/code`、`specs/agent`、`proposals` 各一）
    与 `CHANGELOG.md` 中仍以改名前旧名书写 CLI 的 36 处残留（旧名 + `new` / `init` /
    `canon generate` 三类写法）逐处改为 `fstdd`。**仓库/产物名（`stdd-repo` 等带连字符者）
    与 `upstream/` 排除区内的历史表述保持不变** —— 改名只针对 CLI 可执行名，不误伤名物。
    本条目刻意不复现旧名字面量：检测器只认「独立标识」，而在此处写下它反而会被正确判为残留。
  - **TC-RENAME-005**：为归档 change `2026-09-26-finder-archive-fallback` 补齐 DELIVER 阶段漏落的
    `test-report.md`（该 change 归档时 `.fstdd.yaml` 仍停在 `deliver: pending`）。报告内容取自
    实测证据（`pytest upstream/tests/test_finder.py
    upstream/tests/commands/test_finder_archive_fallback.py -q` → 21 passed / 8.57s；基线
    `f3b2713`、被测版本 `db4cc7e`），未臆造数据。
  **帮助**：改名后的发布门禁**真正全绿**，而不是靠排除区掩盖旧名残留 —— 此前 6/8 意味着
  「改名未完成」这一事实被 `--help`、归档资产两处缺口共谋隐藏。
- **顶层文档的旧斜杠命令收口**（收正 2026-09-15 改名 change 的一处**误判**）：
  `AGENTS.md` 与 `FSTDD.md` 的常用命令表仍写 `/stdd-continue` 与 `/stdd-status`，
  改为 `/fstdd-continue` 与 `fstdd status`（口径 = 根 `FSTDD_CONSTITUTION.md` §常用命令，
  亦即 `upstream/fstdd/cli/commands/upgrade.py::_CONSTITUTION_MIGRATIONS` 的明文迁移对）。
  `AGENTS.md` 另把相位区间滞留在「Phase 3-6」，与 V3.0 的 6→4 相位合并
  （`upstream/fstdd/cli/commands/phase_constants.py::PHASE_ORDER`）矛盾，一并改为 Phase 3-4。
  **为何逃过门禁**：`tools/verify_rename.py` 的 TC-RENAME-002 为防止误伤 `stdd-repo`、
  `leonai42/stdd-*` 这类**名物**，其正则刻意放过连字符形态 ——
  于是带斜杠的旧命令名成了结构性盲区：这几处一路全绿通过。
  （本条与 `4be8b35` 同一教训：检测器的判据**不得在本文件里复现**，否则条目自身触红。）
  **依据**：2026-09-15 改名 change 的 `design-adjustments.yaml::not_adopted` 曾以
  「`grep '/stdd-'` 命中项全部位于 `.fstdd/archive/` 下」判该评语不成立；此判据不成立 ——
  顶层两处文档确有残留（该评语命名者是对的）。归档文档本身仍按规约保留原样，不在本次改动内。
  **帮助**：agent 读到的命令表与真实可用的命令集一致，不再引导不存在的 `/stdd-continue`。
  **遗留的收口**：本条所指「活配置 / 活 skill 仍是旧命令名」的规范层决策见下条 —— 已裁定并落地。
- **「活配置 / 活 skill」旧命令名收口 —— 上条遗留的规范层决策已裁定落地**：
  裁定「纳入改名范围」＝**运行时会真正被读取、并向用户打印文案**的 `.fstdd/config.d/*.yaml`
  与 `.fstdd/skills/**`（`specs/`、`changes/`、`standards/`、`templates/`、`archive/` 属文档 / 历史，本次不动）。
  本条刻意**不复现旧名字面量**（同 `4be8b35` 的教训：检测器只认「独立标识」，在此写下它反被判为残留）。
  据此修正 4 处：
  - `.fstdd/config.d/guard.yaml` 与 `upstream/.fstdd/config.d/guard.yaml` 的中 / 大规模提示语：
    两处**旧斜杠命令** → `/fstdd-understand`；
  - `.fstdd/skills/_shared/version-check.md` 与 `upstream/.fstdd/skills/_shared/version-check.md` 的
    版本漂移提示：一处**旧斜杠命令** → `/fstdd-upgrade`；另一处**裸写的旧 CLI 名 + `upgrade` 子命令**
    → `fstdd upgrade --unlock`（根副本两处皆旧，内核副本仅裸名那处待改）。
  **为何危险**：这两处是 guard / 版本自检**真的会打印给用户**的文案 —— 引导用户执行
  `/stdd-understand` 或**裸写的旧 CLI 名 + `upgrade` 子命令**这类**不存在**的命令，用户照做必然失败；
  且它避开了门禁（`.fstdd/` 是 TC-RENAME-002 的显式排除区），属**结构性命中盲区**。
  **根副本为何滞后**：`fstdd init` 从内核 `upstream/.fstdd/` 拷贝这两个文件，而根副本的拷贝
  发生在内核修正**之前** —— 于是出现「模板已对、项目副本仍错」；同源内核
  `upstream/.fstdd/skills/_shared/version-check.md` 的 `/stdd-upgrade` 与 CLI 代码
  `new.py` / `install.py` 的 `/fstdd-understand` 早已正确，唯 guard 提示两侧皆漏。
  本次把四处副本两两对齐（根 = 内核）。
  **帮助**：guard 与版本自检打印的命令**真实可用**，不再把用户引向死路；也不再把「模板对 / 副本错」
  的分歧一路带到发布。

### 文档
- **更正 README / NOTICE 关于「是否复制上游代码」的失实表述**：README 原文称
  「本仓库只放我们自己的改动层 —— **不复制**上游那 900 多个文件」，与事实相反 ——
  本仓库**确实完整 vendor 了上游代码**（`upstream/`，704 个文件；全仓 1156 个），
  且 README 自身第 46 / 75 / 99 行早已写明「vendor 自上游」。NOTICE.md 亦通篇未提 `upstream/` 目录。
  本次同时补齐 vendor 范围、命名空间适配（上游 STDD → FSTDD）与许可履行说明。
  **帮助**：使用者与合规审查方从 README / NOTICE 读到的**代码来源与范围与事实一致** ——
  不再出现「仓库里躺着 704 个上游文件、文档却声明不复制」的自相矛盾
  （这属**版权声明里的失实陈述**，比措辞不一致严重得多）。
- **README / NOTICE 的 vendor 规模改为不写易变快照数**：两处原写「`upstream/`（704 个已跟踪文件）」，
  而 `upstream/` 是**随版本发布、持续新增测试文件**的内核 —— 09-29 新增
  `upstream/tests/test_install_scripts.py` 后实际已是 **705 个**，声明与事实再度失准
  （与上一条同属「版权声明里的失实陈述」，量级较小但机理相同）。改为「整目录纳入版本控制」，
  不再内嵌会随提交漂移的计数。
  **帮助**：合规声明**不会因后续提交而自我失效** —— 活文档不承载快照数字，就不再需要每次动
  `upstream/` 后回头校数（上一条的 704 / 1156 即因此在一日内失准）。
- **发布清单与派生测试的运行口径对齐法定源**：`docs/SKILL_RELEASE_CHECKLIST.md` 的
  §1/§3/§4/§5 命令长期写 `C:/Python311/python.exe`（**本机不存在**）与归档副本
  `~/.workbuddy-ai/Fstdd/tools/`（**不是法定源**），照抄必失败。统一改为 managed **default env**
  解释器 + 法定源 `E:/FSTDD/stdd-repo/tools/`，并在清单顶部补「运行约定」（cwd = 法定源根、`$PY` 定义、
  声明 `C:\Python311` 已弃用）。`upstream/tests/test_{constitution_contract,inbox_endpoint,silent_share}.py`
  三处运行说明同步换掉不存在的解释器；`install.ps1` 的 `-Python` 示例由具体不存在路径改为占位符。
  **帮助**：发布前检查清单**逐条可照抄执行**（不再"看起来没问题"却跑不通），且运行说明一律指向法定源。
- **瘦身计划文档的回归锚点由「快照数」改为「命令式」**：`upstream/V3.0_SLIM_PLAN.md`
  的「落地核对」结语原写「回归锚点：全量套件 `803 passed / 54 skipped`」，而该项「落地核对」
  本为 2026-09-29（`81e4d79`）所加 —— **数写下即漂移**：2026-09-30 实测已是
  **`811 passed / 54 skipped / 0 failed`**（`pytest upstream/tests -q`，退出码 0）。
  改为只锚「**0 failed** + 命令」，不再内嵌易变计数，并注明取证日期，与 `38769b5`
  同一教训（活文档不承载快照数字）。**帮助**：后来者按锚点复核时**照抄命令即可**，
  不会因读到过期计数而误判「V3.0 瘦身四项未落地」——该项结论经复核为**真**
  （`PHASE_ORDER` 4 相位、`LEGACY_PHASE_MAP` 归一、`COMMAND_GROUPS`、`_auto_generate_human_views`、
  `batch.py` 批级管线均在位），过期的是**佐证数字**而非结论本身。

### 测试 / 验证
- **`test_canonical_in_workspace.py` 两处环境相关失败收口**（承接上一版「留待专档处理」）：
  - `TestDInstalledSkill` 不再硬编码**内核兜底值** `~/.workbuddy/skills`（本实例实际加载
    `~/.workbuddy-ai/skills`，前者只剩影子副本）—— 改走 `tools/_skill_install_env.resolve_skill_dir()`
    内核同源解析，skill 名单直接取自安装器常量，消除「在影子副本上一起错、一起绿」
    （2026-09-16 事故同源）的复发通道。
  - `TestCArchive::test_c2` 对「源目录在归档后被外部程序改动」的情况加**时刻判据**：源中最新的
    文件 mtime 晚于归档目录名内嵌时刻（`canonical-archived-<YYYYMMDD>-<HHMMSS>`）即跳过
    （SC-008 只保证归档时刻逐文件一致，后续演化不可复验、非代码缺陷）；未演化时仍严格相等。
  - 结果：全量套件从 `796 passed / 2 failed` 收敛到 **`797 passed / 0 failed`**（跳过数不变）。
- **镜像告警测试的 bash 可用性判定由「存在即用」改为「实跑判定」**：`test_mirror_alert_ops.py`
  的模块级守卫原是 `skipif(shutil.which("bash") is None)`。Windows 下 `C:\Windows\system32\bash.exe`
  是 WSL 启动器，未装发行版时它**存在却一执行就失败**（`bash -c true` 实测 rc=1），
  于是守卫不触发、需真实执行 bash 的用例照跑并在本机全线失败（改前全量套件
  **31 failed / 816 passed / 4 skipped**）。改为**真执行一次** `bash -c true` 再判定可用性。
  **帮助**：无 bash 的机器上这些用例**如实跳过**（本文件 **49 skipped / exit 0**），
  不再把环境差异伪装成红灯。
- **一键安装脚本首次获得回归测试**：`install.sh` / `install.ps1` 此前**在整套测试中零引用** ——
  同日连续三处「一键装」缺陷（`install.ps1` 缺 BOM、两个脚本误选 Store 别名桩、`--py` 取值错位）
  全靠人工实跑发现，**修完即无防线**。新增 `upstream/tests/test_install_scripts.py`（3 项）：
  以**可用解释器实跑**脚本，断言 `--yes --py <解释器>`（`--py` 非首参，正是出错的那条路径）、
  `--py=<解释器>`、`install.ps1 -Python` 三种形式**都选中指定解释器并以 0 退出**；
  `FSTDD_OUT` 一律指向临时目录，**不触碰真实用户 skill 目录**。
  bash 可用性沿用「真跑 `bash -c true` 才采纳」判据，并补 Git for Windows 常见安装位 ——
  否则 `shutil.which("bash")` 命中的 WSL 启动器桩会让整组测试**静默跳过**（假绿）。
  **帮助**：「一键装可用」从人工口头结论变成可回归的门禁。RED 验证：把 `install.sh` 还原到
  修复前 `81e4d79`，`test_install_sh_py_after_yes` 如期失败并逐字复现
  `[FAIL] 未找到可用的 Python 3.10+`；恢复后 3/3 通过。
  回归锚点：`upstream/tests/test_install_scripts.py`（3 项）。

### 合规 / 来源声明
- **来源口径再校正：`upstream/` 是「持续维护的适配内核」，不是冻结的上游 vendor 快照**。
  上一版把它写成「上游 V3.0.5 代码的 vendor 副本」，并称「改动文件均位于 `tools/` 与 `docs/`」——
  实测不符：上游引入提交 `3aa7d25`（09-15）之后，本仓库按 change 流程**直接改 `upstream/` 内核**
  （命名空间替换 `636db4c`/`0758fd1`；功能提交 `85383bd`/`30e9f70`…；发布 `f3b2713` 把
  `upstream/CHANGELOG.md` 的标题 `V3.0.7` 改成 `V3.1.0` 并插入 9 行本仓库版本文案）。
  同时删去 LICENSE/NOTICE「未列明的内容均为本仓库原创」的越界主张 —— 仓库根 `.fstdd/` 有
  **49 个文件与 `upstream/.fstdd/` 逐字节相同**（如 `standards/python.md`）。
  **帮助**：署名与来源忠于事实（MIT 要求）—— 合规审查方读到的「哪些是上游、哪些是本仓库改动」准确无误。
- **一键装 `install.ps1` 依赖检查修复**：原 `try { & $Python -c ... } catch {...}` 在 PS 5.1 下
  **不捕获原生命令的非零退出**，缺 PyYAML/Jinja2 时会误报「OK（已具备）」。改用 `$LASTEXITCODE` 判定
  （实测 old=True / new=False）。
  **帮助**：缺依赖不再被静默放过，避免 skill 看似装好、真正跑 CLI 时才失败。
- **README §4 初始化示例路径修正**：`python "C:/路径/stdd/bin/fstdd" init` → `python "<本仓库路径>/upstream/bin/fstdd" init`
  （原路径 `C:/路径/stdd/bin/fstdd` 在仓库中不存在，照抄必失败）。

### 修复 / 分发可用性
- **一键装 `install.ps1` 在 Windows PowerShell 5.1 下无法解析（文件缺 UTF-8 BOM）**：
  该文件以 UTF-8 **无 BOM** 入库，而 Windows PowerShell 5.1 对无 BOM 脚本默认按系统
  ANSI 代码页读取 —— 本机代码页为 936（GBK），中文正文被错误解码、引号配对被打乱，
  于是 `& $Python -c "…"` 之后的语句被当作代码解析，直接抛 `Unexpected token 'if'`
  （实测 `powershell -ExecutionPolicy Bypass -File install.ps1` 退出码 1，一行未执行）。
  修复：为 `install.ps1` 补 UTF-8 BOM（`EF BB BF`；行尾仍为 LF）。
  **帮助**：Windows 用户按 README §4 照抄 `.\install.ps1` 不再必然失败 —— 此前该文件
  在本机默认 shell 下**完全不可用**，是一键装路径上被掩盖的阻断点。
- **一键装 `install.ps1` 在「PATH 上只有 Store 别名桩」的 Windows 上误选解释器**：
  候选选择原为「`Get-Command` 找得到就用第一个」（`python3` → `python` → `py`）。
  而 Windows 上 `python3` / `python` 常指向 Microsoft Store 的**应用执行别名**桩 ——
  它**存在**，一执行却退出 9009、无输出。于是当 PATH 上只有该桩、机器里另有可用解释器
  （如 WorkBuddy 自带的 `~/.workbuddy-ai/binaries/python/envs/*/Scripts/python.exe`）时，
  脚本报 `[FAIL] 需要 Python 3.10 或以上` —— **归因错误**：用户照做去升 Python 也修不好。
  （实测：`powershell -ExecutionPolicy Bypass -File install.ps1` 退出码 1，选中
  `…\WindowsApps\python3.exe`；同机 workbuddy env 的 3.13.14 可正常 `import yaml, jinja2`。）
  修复：候选改为**真跑一次版本探测**（`sys.version_info >= (3,10)`）才采纳，坏桩自动跳过；
  并追加 WorkBuddy 自带环境解释器作为兜底。
  **帮助**：一键装在「PATH 只有 Store 别名」的 Windows 上**真正可用**（修复后实跑 exit 0，
  定位到 3.13.14，7 个 skill 全装、`verify_workbuddy_skills.py` PASS），失败时也不再指错方向。
  说明：POSIX 孪生脚本 `install.sh` 的同类「存在即用」选择，**本次一并修复**（见下条）。
- **一键装 `install.sh`（POSIX 孪生脚本）同类误选解释器修复**：上条曾以「本机无可执行的
  bash」为由暂缓，后经实测**该前提已不成立** —— PATH 上的 `C:\Windows\system32\bash.exe`
  确为失败桩，但 WorkBuddy 自带的 PortableGit bash
  （`~/.workbuddy-ai/binaries/PortableGit/*/bin/bash.exe`，5.3.15）`true` / `false`
  退出码实测 **0 / 1**，可完整执行 `install.sh`。
  症状与 `install.ps1` 同源：`pick_python` 以 `command -v python3 python py`「存在即用」，
  而 Git Bash 下 `python3` / `python` 解析到 Microsoft Store 的应用执行别名桩 ——
  选中后 `"$PY" --version` 退出 9009（实测，脚本报 `[FAIL] 该解释器无法执行`，无输出），
  且**不回落**到机器里可用解释器（`~/.workbuddy-ai/binaries/python/envs/*`）。
  修复：候选改为**真跑一次版本探测**（`sys.version_info >= (3,10)`）才采纳，坏桩自动跳过；
  并追加 WorkBuddy 自带环境解释器兜底，与 `install.ps1` 对齐。
  **帮助**：Windows 用户在 Git Bash 下按 README §4 执行 `./install.sh` 不再必然失败 ——
  修复后实跑 exit 0，定位到 `…/envs/default/Scripts/python.exe`（3.13.14），
  依赖检查 OK、7 个 skill 全生成、`verify_workbuddy_skills.py` PASS。
- **一键装 `install.sh` 的 `--py` 取值解析错位**：参数解析用 `for arg in "$@"` 配 `shift`，
  当 `--py` 不是首个参数时（如常用组合 `./install.sh --yes --py /path/python`）会 shift 掉
  错误元素，`$1` 落到 `--py` 自身，`PY` 被赋成字面量 `--py` —— 随后报
  `[FAIL] 未找到可用的 Python 3.10+`，而所给路径其实可用。
  （实测：修复前 `./install.sh --yes --py <可用解释器>` 退出码 1，仅打印该 FAIL；
  修复后退出码 0，`[1/4] Python:` 正确回显所给路径。）
  修复：改为 `while [[ $# -gt 0 ]]` 按当前位置读取 `--py` 的取值（`${2:-}`）；
  `--py=/path` 与默认无参形式行为不变（三种形式修复后实跑均 exit 0）。
  **帮助**：显式指定解释器（本机 PATH 无可用 `python` 时唯一可靠路径）不再静默失败 ——
  脚本头部与 README §4 均记载该用法。
- **内核元数据 `upstream/pyproject.toml` 修正三处改名残留 + 一处依赖漏列**：
  `8693d82 feat(S2): CLI 与 Python 包改名为 fstdd` 把包目录 / CLI 入口 / 数据目录都改成了
  `fstdd`，**唯独漏改 `pyproject.toml`**（`git log` 可证：该文件最后一次改动仍是引入提交
  `3aa7d25`，从未被改名提交触及）。于是它同时声明了四处指向不存在物的**改名前旧名**：
  分发包名是旧名、`readme` 指向的 Markdown 文件名不存在（现役名为 `FSTDD.md`）、CLI 入口
  指向不存在的模块（现役为 `fstdd.cli`）、`packages.find include` 模式与 `package-data` 的
  包名键都匹配不到任何真实包。实测：`upstream/` 下只有 `fstdd/` 包、
  只有 `bin/fstdd`；全仓测试一律 `from fstdd.cli… import`。**对外分发时 `pip install ./upstream`
  会因「readme 缺失 / 找不到包 / 入口指向不存在的模块」而断裂。**
  **另**补声明 `requests>=2.28` —— `fstdd/cli/commands/{experience,curate,knowledge}.py`
  均 `import requests`，且 `init` 会拉入 `experience`；macOS 干净 venv 全新安装时 123 个用例
  因此连带失败（占首跑失败的 92.5%，取证见 [docs/006-macos-compat-report.md](./docs/006-macos-compat-report.md) §4.1）。
  `authors` 保留上游署名不动（依 MIT 要求，署名须忠于事实）。
  **帮助**：分发出的内核**自洽可装** —— 包名 / 入口 / readme / 依赖声明与真实结构一致，
  不再是「改名只改了一半」的半成品。回归锚点：
  `upstream/tests/test_install_source.py::TestEPackagingMetadata`（5 项）。
- **一键装依赖检查漏 `requests`（补 `pyproject.toml` 的半修）**：上一版给 `upstream/pyproject.toml`
  补了 `requests>=2.28`（见上条），但**依赖声明的其余四个点没跟上** —— README 前置要求、
  `install.sh` / `install.ps1` 的 `[2/4]` 检查、`tools/install_workbuddy_skills.py::_check_runtime_deps`
  仍只列 PyYAML / Jinja2。后果（EXP-20260916-C1 实录）：干净 venv 下四步闭环在 `[4/4]` 断裂 ——
  `fstdd init` 因顶层 `import requests` 崩溃，而 `[2/4]` 却报「OK（已具备）」、`[4/4]` 只报
  「CLI 端到端冒烟失败」，**归因指向错误方向**（教用户去查 yaml/jinja2）。修复：四处声明点
  一并补 `requests`，并让 `tools/verify_workbuddy_skills.py` 的依赖前置检查也覆盖 `requests`，
  使缺依赖时直接点名包名、不再伪装成冒烟失败。
  **帮助**：一键装的「依赖检查 → 生成 → 校验」闭环不再在最后一步因漏声明而断；
  对外分发时按 README 前置要求装齐三个依赖即可一次性装成。
  实跑：`install.sh --yes`（`FSTDD_OUT` 指向临时目录）退出码 0，
  `[2/4] 依赖检查: PyYAML / Jinja2 / requests` OK、`[4/4]` 冒烟通过。
  回归锚点：`upstream/tests/test_install_source.py::TestFInstallDepDeclarations`（5 项，
  防「只修 pyproject、其余声明点不动」的半修）。

### 规范 / 路径口径
- **退役被取代的 canonical spec `d-drive-home`**：该 spec 来自变更 `2026-09-17-migrate-to-d-drive`，
  其 SC-008 / SC-009 仍要求「法定源 SHALL 写为 `D:/tools/FSTDD/stdd-repo`」—— 而该迁移
  **从未在本机落地**（实测 `D:\tools` 不存在，仓库实际位于 `E:\FSTDD\stdd-repo`），继任 spec
  `canonical-in-workspace` 已把「法定源 = 工作区内的 `stdd-repo`」定为权威。留着它有两个害处：
  ① `fstdd index` 按 spec 目录建索引（`index.py`），会把它当**活能力**；② 它守着一个从未发生的
  事实，后来者据以排查必被误导（与 `test_migrate_to_d_drive.py` 13 项恒红同源）。
  处理：从现行 `.fstdd/specs/` 移除；历史原文留档于
  `.fstdd/archive/2026-09-17-migrate-to-d-drive/specs/d-drive-home/spec.md`（不丢证据）。
  **帮助**：现行规范集与实际工作区布局一致，索引里不再有指向不存在路径的能力。
  回归锚点：`upstream/tests/test_repo_home.py::TestDDocsAndMemory::test_d4_superseded_d_drive_spec_retired`。

---

## [3.1.0] — 2026-09-26

**主题**：**让 change 可以活在隔离环境里** —— 一个 change 不再必然劫持整个工作区。
**规模**：含自 `fstdd-v3.0.6` 起的全部提交（原「迭代 02」+ change 隔离形态 + 归档回退修复）。

### 修复
- **回传端点迁移**：默认端点由 `http://43.134.236.80:8787` 改为 `https://quanthub.ccreits.cn/inbox/api/share-experience`
  （8787 公网入口已永久关闭，改经 443 反代）。
  **帮助**：新节点按默认配置即可投递，不必手工改地址；旧地址已不可达，此修复消除了"配置对但连不上"的困惑。
- **测试与实现漂移修复**：两处测试断言仍写旧端点、`share_experience.py` 改动未提交
  ⇒ 全量套件由 **3 failed / 732 passed** 恢复为 **735 passed / 0 failed**。
  **帮助**：CI/回归不再有假红灯，改动可被信任。
- **README §6 经验回传口径更正**：原文写「默认禁用、除非本轮显式要求一律跳过」，
  与**权威设计**矛盾 —— `docs/WORKBUDDY_INSTALL_NOTES.md`（§经验策略，且被
  `test_c3_doc_skill_count_and_policy` 守卫）明确：Step 2.8 为**静默回传到「我方指定位置」**，
  **不向第三方外发**，可用 `FSTDD_NO_SHARE=1` 或 `share.silent.enabled: false` 关闭。
  **帮助**：用户从 README 读到的行为描述与**真实行为一致** —— 不再误以为"经验不会被回传"
  （这是**安全章节里的失实陈述**，比措辞不一致严重得多）。
- **change 目录解析增归档回退**：`fstdd archive` 之后，`validate` / `status` / `canon verify` /
  `structure merge` 四条命令**必然 exit 1** —— 它们只查 `.fstdd/changes/`，**没有 `.fstdd/archive/` 回退**，
  而 DELIVER 把归档排在这些步骤之前 ⇒ **DELIVER 自身不可用**，只能靠「还原 → 执行 → 再归档」人肉往返绕开。
  根因是**四个各自独立、都硬编码 `changes/`** 的解析器（`finder.py` / `canon.py`（**纯路径拼接、
  根本不走 finder**）/ `gate.py` / `state.py`），故只修一处**不足以**修好 `canon verify`；
  现统一为 `find_change_dir(..., include_archive=True)` 回退，**默认关闭**以保证
  `archive` / `abort` 逐字零漂移（否则 `archive` 会把自己再移动一次）。
  **帮助**：**归档后的 change 仍可正常查询** —— 归档完直接重跑四条命令全部 rc=0
  （`canon verify` 输出 **2/2 通过**），不必再人肉还原；「归档后查询」本就是合法语义，
  此前却要靠「顺序正确」才能成立。
  验证：新增 TC-FAF-001~013（与 SC-001~013 一一对应）；全量套件 **850 passed / 0 failed**。

### 新增
- **`fstdd new --isolate <none|worktree|branch>`（change 隔离形态）**：`worktree` 让 change 活在
  独立 git worktree（默认建在仓外 `<项目>.worktrees/`）；`branch` 切独立分支、共享工作区；
  `none` 为默认，行为与旧版**逐字一致**。配套：worktree 形态会把主仓的门禁 hook 注册文件
  复制进去（保持 Guard 有效）；`fstdd new` 增加提示行；`fstdd init` 往
  `.fstdd/config.d/project.yaml` 补 `isolation` 配置块。
  **帮助**：**一个 change 停只读相位不再冻结整个工作区** —— 只冻结它自己 `scope.paths`
  声明的路径，范围外的文件仅告警放行；两处 change 可以真正并行而不互相干扰
  （此前只能靠人肉错峰协调）。
- **四份规程入标准库**（`.fstdd/standards/`）：升级同步 / 节点接入 / 编号取号 / 交付物入库。
  **帮助**：新节点与后续升级**有据可依**，不再"各自猜"。
- **节点交付物入库**：5 份实质交付（自检脚本 / 接入 SOP / 协议差距评估 / macOS 兼容报告 / 日志治理）
  收进主仓（`tools/`、`docs/`、`standards/`），均附来源头。
  **帮助**：此前只躺在协作目录、不进版本、新节点看不到的交付物，**现在可检索、可复用**。

### 移除
- **`fstdd new --parallel` 死代码**：该开关**从未在 argparse 注册**（基线 `git grep -- "--parallel"` 零命中），
  仅靠 `getattr(args, "parallel", False)` 读一个永不存在的属性 ⇒ 恒不执行；
  其 `_setup_parallel_worktrees()`（V2.8 Two-Instance Kickoff）随之移除。
  **帮助**：清掉「看起来有、实际永不生效」的死开关；隔离需求由新的 `--isolate` 承担。

---

## [3.0.6] — 2026-09-21

**主题**：**让"失败不再静默"** —— 检测能力从"能跑"提升到"可信"。
**规模**：79 个文件变更 / **+4,934 行**。

### 新增
- **检测静默修复（11 项 DFX）**：`guard status` 的 Phase Lag、`fstdd status` 的活跃停滞标注、
  `validate` 的基线损坏告警、`fix` 的不可读文件跳过计数、Gate 2 的损坏 spec 逐条告警等。
  **帮助**：**过去"悄悄失败"的 11 处现在会明确出声** —— 出问题时你能看到，而不是以为一切正常。
- **审计哨兵（`audit_silent_except.py`）**：自动扫描"被吞掉的异常"，0 未覆盖即 PASS。
  **帮助**：把"静默失败"变成**可自动检测**的问题，而不是靠人肉 review。
- **变异测试锚定检测存活**：僵尸 / 滞后 / 失配 / L2 守卫 / 基线 各带阴性对照。
  **帮助**：**保证检测本身没坏**（防止"检测器坏了但看起来在跑"）。
- **宪法第 7 节 + skill Gate 自检 + 模板双源守卫**。
  **帮助**：规则进了宪法层，**不会被后续升级无意抹掉**。

### 修复
- **guard 钩子 stdin 解析健壮性**：修掉尾逗号导致的 1 元组崩溃（**fail-open 静默失效**）。
  **帮助**：钩子崩溃时**不再静默放行**（这是最危险的一类失败）。
- **agent 运行时目录免于流程门禁**（`.workbuddy-ai` 等）。
  **帮助**：**消除误阻断**，且零安全损失。
- **sanitizer 过度脱敏**：`identifier.method` 被误判为域名。
  **帮助**：脱敏不再破坏正文可读性。

---

## [1.1.0] — 2026-09-18

**主题**：**时间基线**（time-baseline，8 个 Slice）。
**规模**：全量回归 **692 passed**。

### 新增
- **时间戳统一 UTC + L1/L2 检测器**：**帮助**：跨机协作不再因时区/本地时钟产生误判。
- **DC-HASH 改为 EOL 归一内容哈希**：**帮助**：同一文件在 Windows/Linux 下哈希一致，**跨平台比对不再假阳性**。
- **证据时效标注**（结构化 `why.evidence`）：**帮助**：结论可追溯"依据何时取得"。
- **基线契约**（Gate 1 自动基线 / 回填 / 幂等 / validate 警告）：**帮助**：基线不会因重复执行而漂移。
- **时钟巡检三态契约**（err=rtt/2、epoch 基准、min_samples）：**帮助**：时钟异常**可判定**，而不是靠猜。
- **inbox 按 EXP-ID 覆盖落盘去重 + batch close 时区修复**：**帮助**：重复投递不再产生重复件。

---

## [1.0.0] — 2026-09-15

**首个版本**。

### 新增
- **`rename-to-fstdd`**：项目更名为 FSTDD（WorkBuddy 适配层与金融扩展）。
- **合并 specs**：规范文件归并。
  **帮助**：建立**统一的规范入口**。

---

[3.1.0]: 对比 v3.0.6 —— change 隔离形态 + 迭代 02 全部条目
[3.0.6]: 对比 v1.1.0 —— 79 files / +4934 行
[1.1.0]: 对比 v1.0.0 —— time-baseline 8 Slice
[1.0.0]: 首个版本
