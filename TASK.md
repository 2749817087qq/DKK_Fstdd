---
task_id: FSTDD003
schema: fstdd-distributed-task/v0.1
title: FSTDD 安装/运行工程测试与经验回传
status: archived          # pending | running | blocked | done | archived
created: 2026-09-12
updated: 2026-09-27
node: WORKBUDDY-AI-WIN   # 执行节点标识（本实例）
owner: D哥
mode: fstdd              # 走 FSTDD 四阶段 + 三确认门
upstream: https://github.com/2749817087qq/DKK_Fstdd.git
experience_repo: 2749817087qq/Fstdd-experiences
inbox: http://43.134.236.80:8787
depends_on: []
tags: [install, hardening, experience-upload, distributed]
---

# FSTDD003 — 分布式任务卡

> 任务目录即任务根：`D:\FSTDD003`。
> 编号规则：**FSTDD + 三位序号**，全局唯一，跨节点不重复。
> 每个任务目录都必须是**可独立运行的 FSTDD 工作区**（含 `.fstdd/` 骨架 + `tools/`）。

## 1. 任务定义

| 项 | 内容 |
|---|---|
| 目标 | 卸载旧 STDD，安装自研 FSTDD，做工程测试，把安装/运行问题回传到经验库 |
| 范围 | 仅限 **WorkBuddy AI 实例**（home = `~/.workbuddy-ai`）。另一实例 `~/.workbuddy` 不在范围内 |
| 交付 | 安装成功 + 7 个 skill 落位 + 三轮问题清单 + 27 条经验回传成功 |
| 终止条件 | 经验回传服务端确认接收，本地 commit 完成 |

## 2. 四阶段执行记录

| 阶段 | 产出 | 确认门 | 状态 |
|---|---|---|---|
| P1 UNDERSTAND | 需求澄清：卸载旧 STDD、装 FSTDD、问题回传 | Gate 1 | ✅ |
| P2 SPEC | `docs/INSTALL_RUN_ISSUES_2026-09-16.md`（4 项已修 + 5 项待修） | Gate 2 | ✅ |
| P3 BUILD | `install.sh` 4 项修复；三层外发防护；自建接收端点降级链 | Gate 3 | ✅ |
| P4 DELIVER | 三轮复测清单；27/27 经验回传；本地 6 个 commit | — | ✅ |

## 3. 分布式执行约定（供后续任务沿用）

1. **任务根 = 目录名**：`D:\FSTDD<NNN>`，目录内必须有 `TASK.md` 与 `.fstdd/`。
2. **节点标识**：每个执行实例在 `node` 字段登记自己的标识，禁止两个节点同时写同一任务目录。
3. **幂等**：任务卡只增不改历史结论；状态变更必须同时更新 `updated`。
4. **依赖**：`depends_on` 填上游 task_id，上游未 done 不得启动。
5. **经验回传**：无 GitHub 凭证时自动降级 POST 到 `inbox`；**禁止第三方外发**。
6. **产物不入库**：`experiences/` 是导出产物，已 `.gitignore`；留存靠回传通道。

## 4. 本任务关键结论（可复用）

- **实例 home 隔离**：WorkBuddy 只扫**自己 home + `skills/`**。`~/.workbuddy` 与 `~/.workbuddy-ai` 各扫各的，不是同一实例扫两处。
- **Git Bash → Windows Python 路径**：`/c/Users/...` 会被解析成 `\c\Users\...`，必须过 `cygpath -m`。
- **`for arg in "$@"` + `shift` 失效**：迭代列表展开时已固定，改用下标遍历。
- **升级覆盖防线**：上游升级会静默覆盖 `deliver.md`，每次升级后必须重跑
  `install_workbuddy_skills.py` + `verify_workbuddy_skills.py`，校验哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1`。
- **回传口径坑（P10）**：`publish` 提交的是**导出目录全量**，`README` 索引只反映源目录条数，两者不一致且会重复累加服务端计数。
  伴生问题：**导出目录不清理陈旧条目**，源目录删了、导出目录还在，口径持续漂移。
  本次已手工对齐到 **源 26 = 导出 26 = 索引 26**。

## 5. 遗留项

- [ ] 本地 6 个 commit 未 push（`github.com:443` 不通、代理 502、SSH 公钥未授权）
- [ ] P10 / P11 尚未回传（再跑一次会重复提交全量 27 条，等服务端去重后再传）
- [ ] `install.sh` 4 项修复未合入上游
- [ ] 待修：P5 token 路径、P6 Guard 平台误判、P7 verify 漏校验、P8 change 名不支持中文、P9 子命令缺参提示
- [ ] **P12 待修**：`extract-proposal` 与 Gate 生成物不兼容（`canon.py::_generate_one()` 只渲染 5 个 section，
      模板 14 个，解析器按模板解析）→ `capabilities/constraints/risk_areas/non_goals` 静默丢空，
      **`what_changes` 虚增**（H3 不终止 H2 区间，被 `_parse_section` 吞并）。最小修法：生成器补 `## Capabilities` 父标题。
- [ ] **P13 待修**：嵌套工作区下 change 落到父工作区；`canon.py::_generate_one()` 的
      change 级 → 项目级 canonical 回退**不打印警告**。另：CLI 入口在 Git Bash 下需 `cygpath`（既有 P3 的同类遗漏）。
- [ ] **P14 待修**：`init` 自动拉社区经验必失败（registry 指向的仓库无 release → 404），
      且 `_post_init_experiences()` 用 `except Exception` 把 404 归因成"网络不可用"；
      提示里的命令名仍是旧 `stdd`。
- [ ] **P19 待修（本节点 2026-09-19 发现）**：`archive` 合并 master specs 时，
      冲突检测只比 `### Requirement:` **标题**，**漏检 SC-ID 跨变更撞号** →
      `.fstdd/specs/<cap>/spec.md` 里静默出现两组 `SC-001..N`（实测 SC-001~004 各 2 次），
      归档输出仍显示「Specs 已合并到 specs/」无任何警告。
      危害：SC-ID 失去全局唯一性，而 test-plan / `agent_spec.yaml` 正是靠 SC-ID 做映射。
      最小修法：`archive.py` 冲突检测补 `#### Scenario: (SC-\d+)` 维度 + 打印带变更名前缀的引用建议。
      详见 `experiences/FSTDD003-EXP-20260919-ARCHIVE-1.md`。
- [ ] **P20 待修（本节点 2026-09-19 发现）**：`archive` 的「Specs 已合并到 specs/」**只合并 Human View**
      （`<ws>/.fstdd/specs/<cap>/spec.md`），**项目级 canonical 双轨未同步** ——
      `<ws>/.fstdd/canonical/specs/{code,agent}/`、`canonical/proposals/` 与 `.canon-index.yaml` 都不会更新，
      归档后必须手工补三步（cp proposal + cp 4 个 spec yaml + 往索引字典按 key 插行）。
      最小修法：把输出文案改成「Human View 已合并到 specs/；canonical/ 需手工同步」。
      详见 `experiences/FSTDD003-EXP-20260919-ARCHIVE-2.md`。
- [ ] **P21 待修（流程侧，非 CLI 缺陷）**：变异测试暴露的两类「形同虚设断言」没有现成检查手段 ——
      ① 裸 `in file` 关键词断言会命中**注释/文档**而非代码；② 服务层常量被 worker 覆盖后，
      只测路由层 ⇒ 该字段**不可观测**，注入变异也不变红。
      建议在 Phase 3 清单加一条：「每个切片 GREEN 后，对最关键的那条断言做 1 次变异注入验证」。
      详见 `experiences/FSTDD003-EXP-20260919-MUTATE-1.md`。
- [ ] **P22 待修（流程侧，非 CLI 缺陷）**：两类「假东西掩盖真路径」——
      ① 逐用例手塞假依赖（`session=object()`）⇒ 被测代码自己「不注入时自建依赖」那段
      **覆盖率恒为 0**，真机第一次真跑每篇抛 `'NoneType' object has no attribute 'get'`
      （95 条用例 95 次手塞，等于真实路径一次没走）；
      ② 造的假数据被**被测代码自己的归一化函数**改写（`link_key` 在冒号处截断 +
      丢非 ASCII ⇒ 5 篇去重成 1 篇、两个中文号名撞成一个）。
      建议：凡可注入依赖**必须有至少一条不注入的用例**；Harness 要记录「收到了什么依赖」；
      造数助手一律带条数自检断言。
      详见 `experiences/FSTDD003-EXP-20260919-MOCK-1.md`。
- [ ] **P23 待修（流程侧，非 CLI 缺陷）**：真机 E2E 不可替代，且其盲区与变异测试**互补**——
      变异测不到「从未被执行过的代码」，E2E 才能抓到（本批 3 个 bug：session 未建 /
      状态栏 JS 从不加 `.show` / 已抓过的被静默跳过显示「成功 0 篇」）。
      另：真数据还暴露两类实验室看不见的口径偏差 —— 抽样取前 N 把全量估成 63 GB
      （索引按时间倒序，前排全是带图大篇；改等距抽样 → 2.2 GB）；
      「失败 1,264 篇」不带原因（两份索引根本不写 `dir`，这些篇导出必失败）。
      建议：Phase 3 完成定义里写死「UI 类变更 ≥1 条真浏览器 E2E + ≥1 条真数据跑批」；
      估算类算法禁止 `rows[:N]`；聚合计数必须能拆原因分类。
      详见 `experiences/FSTDD003-EXP-20260919-E2E-1.md`。
- [ ] **P24 待修（流程侧，非 CLI 缺陷）**：「先写实现后补测试」的变更，事后用
      **切片级 revert 重放**补 RED（摘掉该切片引入的实现 → 只跑它的 TC → 必须变红 → 按字节还原）。
      本批实测 36/36 变红，并抓出三类变异/E2E 都抓不到的洞：
      ① **兜底分支让断言恒真**（`X if cond else <整个文件>`，函数不在时退化成全文件 → 恒真）；
      ② `in src` 关键词断言（改名即失效，本次再次踩到 P21）；
      ③ **切片↔TC 映射是事后追认的，3 条归错了**（靠「摘掉 S5 的 build_epub，TC-024 却没红」才发现
      503 其实在 router 的前置探测里）。
      ⚠ 写 revert 补丁的坑：改名目标串**必须不保留原串作为子串**（`renderExportWarn → renderExportWarnOff`
      等于没打补丁，会给出**假的绿**）。
      建议写进 Phase 3 完成定义：「每个切片要么有 RED 记录，要么有 revert 重放记录」。
      详见 `experiences/FSTDD003-EXP-20260920-RED-1.md`。
- [ ] **P32 待修（🔴 高 · 数据丢失）**：Windows 上 `Remove-Item -Recurse` / `shutil.rmtree()`
      删**目录联接**会**递归删掉联接目标里的真实文件**（本轮实测删掉 1015 个）。
      报错是 `SAFE_DELETE_FAIL_CLOSED`，**看起来只是「删不掉」，实际已部分删除**。
      安全删法只有 `os.rmdir()` / `[IO.Directory]::Delete($p,$false)`。
      建议：任何「删链接」代码路径上出现 `rmtree` / `-Recurse` 视为**阻断级**评审问题；
      删除前必须先校验对象类型（reparse tag）。
      详见 `experiences/FSTDD003-EXP-20260921-JUNCTION-1.md` 与
      `docs/JUNCTION_SELF_CONTAIN_2026-09-21_workbench.md`。
- [ ] **P33 待修（中）**：`os.readlink()` 对目录联接返回 **NT 前缀** `\\?\D:\...`，
      与普通路径字符串比较**永远不等** → 一切「幂等/自愈」逻辑退化成「每次都重建」。
      修法：剥 `\\?\` / `\??\` / `\\?\UNC\` + `normcase/normpath`。
- [ ] **P34 待修（中）**：目录联接 / 硬链接**不能进 git** ——
      ① 入库成坏文本，克隆即废；② 不挡则 `git add <dir>/` 递归扫进**2 万多个数据文件**。
      修法：逐条 `.gitignore` + 用 `git add --dry-run` 复验实际入库清单。
- [ ] **P35 待修（中）**：`is_junction()` 不能用 `islink()` / `is_dir()`（对目录联接与
      符号链接**都为真**）。唯一判据 `os.lstat(p).st_reparse_tag == 0xA0000003`。
- [ ] **P36 待修（中）**：用 `mklink` / `New-Item -ItemType Junction` 建联接要过一层 shell，
      **中文路径易被按 GBK 解析成乱码**（与 bat 编码坑同源）。
      修法：ctypes 直调 `CreateFileW` + `DeviceIoControl(FSCTL_SET_REPARSE_POINT)`，
      全 Unicode 原生，**且免管理员**。
- [ ] **P37 待修（🔴 高 · 静默）**：引擎/数据目录未就绪时若返回「那个不存在的路径」，
      所有读数据接口会**静默返回空**（界面显示「没有数据」，像功能没做）。
      修法：三级兜底 `显式覆盖 > 自包含目录（就绪时）> 真实数据根`；
      就绪判据必须**同时**查「代码在」+「数据在」，少查一个都会把「没配好」伪装成「没数据」。
      ⚠ 本项目**第三次**踩同类事故（前两次：`_paths.py` 非同级目录、`Path()` truthy）。
- [ ] **P38 待修（低）**：守卫测试把**工具自动生成**的文件当违规
      （`python -m venv` 生成的 `.venv\Scripts\activate.bat` 偏移 319 有非 ASCII 字节）。
      后果：每台装了 venv 的机器都红一条 → **守卫被无视**（比没有守卫更糟）。
      修法：`SKIP_DIRS` 补 `.venv/venv/.tox/site-packages`，并加断言锁住「跳过生效」。
- [ ] **订正**：`EXP-20260920-LNK-1` 顶部结论已推翻，原文末尾追加
      `## ⚠️ 事后订正（2026-09-21）`（保留原文，另加脚注，符合铁律 6）。
      真实判据：`LinkFlags` bit0 置位 + `IDListSize` 为几百字节真实 PIDL；
      那一轮「双击没反应」的真正根因是 **GBK bat + `chcp 65001`** 这个独立 bug。
      元教训：**症状相同的两个 bug 会互相顶罪**，修复后要把剩余症状当**新问题**独立复现。
- [ ] **P39 待修（🔴 高 · 静默）**：配置兜底只在**进程启动时**生效。
      `ARCHIVER` 是导入时算好的常量；服务跑起来后再拆目录联接，运行中的进程
      **不会自愈**，读数据接口静默返回空（实测 `only_unfetched` 变 `0`，真实 `2`，
      日志干净无报错）。修法：为运行期状态提供**重新探测**的入口
      （`live_status()` + `/api/health` 的 `degraded`），
      并让**告警文案按「谁在什么时刻看到的」分叉**（启动时就坏 = 已退回、功能好；
      启动后才坏 = 本进程仍指着坏目录、会返回空）。
      ⚠ 验证时必须跑「坏掉」的分支，happy path 永远发现不了。
      详见 `experiences/FSTDD003-EXP-20260921-LIFECYCLE-1.md`。
- [ ] **P40 待修（中）**：`experience add` 的 `--category` 是**闭集枚举**，15 个有效值
      **全是过程/协作失败模式**，**没有「测试设计 / 工程实践」类** →
      本次那条「测试绿着但被测分支根本没执行」只能塞进 `coverage_vacuum`
      （语义勉强，不同构）。建议加 `test_design` / `engineering_practice`，
      或允许自定义 category + 自由 tag。详见 `docs/FLOW_ISSUES_2026-09-21_workbench.md`。
- [ ] **P41 待修（🔴 高 · 静默）**：`fstdd init` **不生成** `.fstdd/version.yaml`
      （`grep init.py` 无命中；该文件只被 `upgrade.py` / `utils.py` 引用）→
      Phase 1 Step 0 的版本自检在**全新项目上从来没生效过**。
      更隐蔽的是 `version-check.md` 规定「落后时告警但不阻断」，
      于是「文件根本不存在」与「版本轻微落后」被压成同一个「告警 + 继续跑」。
      修法：`init` 补写 version.yaml，或把两种状态分成两种结论。
- [ ] **P42 待修（🔴 高 · 静默）**：`config.d/quality.yaml` 的 `lint` / `coverage`
      两道门**不可执行** —— `lint: "ruff check app/ tests/"` 指向**不存在的 `app/`**
      （工作台是 `app.py` 单文件），且 `.venv` 未装 `ruff` / `pytest-cov`。
      而 `coverage.enabled: true` 与 `test-report.md` 模板**要求填覆盖率百分比**的表
      共同**诱导编数字**（把未知伪装成已知）。
      修法：Gate 3 前**试跑一次** `quality.yaml` 的命令，不可执行就报错；
      模板补「工具缺失时填 `N/A` + 写出缺失包名与失败命令」。
      详见 `docs/FLOW_ISSUES_2026-09-21_workbench.md`。
- [ ] **P43 待修（🔴 高）**：**lightweight 模式没落地到 CLI** ——
      `validate.py:24` 的 `required_files` 硬编码为
      `["proposal.md", "design.md", "test-plan.md", ".fstdd.yaml"]`，
      而 `lite.yaml` 规定 lightweight 跳过 `design` / `test-plan`；
      `grep -rln "lightweight\|skip_design"` 只命中 `new.py` / `batch.py` /
      `bootcamp.py` / `__init__.py`，**`validate` / `phase` / `status` 都不读**。
      → **该模式的 change 永远过不了 `validate`**，执行者只有两个都不对的选项：
      ① 硬造两份空壳文档（`test-plan.md` 还会触发 `validate.py:96`
      「TC 案例数少于 Spec Scenario 数」→ 又一条假失败）；
      ② 明知会红而跳过校验器（**主动训练人忽略校验器**，代价更大）。
      `status` 另有一处硬编码：显示「普通交互模式（默认）」，与
      `.fstdd.yaml` 里的 `mode: lightweight` 不符。
      修法：`validate` 读 `mode`；或删掉 `lite.yaml` 里的两个 skip 开关 ——
      🔴 **不要让配置与校验器互相打架**。
      **Phase 4 期间补到两条同族证据**：
      (a) `lite.yaml` 的 `gate2: auto_pass` 与 `gates.yaml` 的
      `phase2_spec.required: true` **对同一道门给出相反规定**，且无校验发现矛盾
      → Gate 3 被 `Gate 2 (spec) is not yet confirmed` 拦下，
      只能先手工 `--gate 2 --confirmed-by cli` 放行；
      (b) `archive` 的「Specs 已合并到 specs/」是**无条件打印**的 ——
      本次实测 `find .fstdd/specs -type f` = **0 个文件**（lightweight 是 proposal_only），
      那句「已合并」没有任何对象（P20 同族）。
- [ ] **P44 待修（🔴 高 · 静默）**：`stdd gate approve --dry-run` **不 dry** ——
      `grep -n "dry_run" fstdd/cli/commands/gate.py` → **0 命中**。
      `--dry-run` 是**父解析器**的全局开关，approve 分支从不消费它，
      直接走到 `_auto_generate_human_views()` + `_confirm_gate()`（`gate.py:315-323`）
      **无条件**写 `.fstdd.yaml`（`_confirm_gate` 见 `gate.py:71-116`）。
      实测：dry-run 那一步就把 Gate 1 锁上并建立 baseline，
      第二条真命令只回一句 `Gate 1 already confirmed at 2026-09-22T18:28:42+00:00`
      —— 那是**正常幂等文案**，不写经验没人会怀疑。
      🔴 危害集中在**它是安全机制本身**：V3.0.5 硬防线要求「AI 不得静默自跑 approve；
      必须先把确认框展示给用户、等用户明确确认后再执行」，
      而 `--dry-run` 正是执行者**为了不违规**才会用的预览手段 ——
      用它反而把门打开，且审计链会记下一个**当时并不存在的用户确认**
      （`confirmed_by: dialog` / `confirmed_actor: ai`，而那一刻用户还没确认）。
      修法：approve 消费 `--dry-run`（只打印将写的字段与当前值、不写盘），
      且 dry-run 输出**不得**再出现 `Gate N confirmed`；更稳的做法是在分发层设
      `DRY_RUN` 上下文，凡写盘函数统一先查它、漏判时**抛异常**。
      ⚠ 本节点**未逐个体检**其余子命令是否同样忽略 `--dry-run`。
      详见 `experiences/FSTDD003-EXP-20260923-GATE-1.md`。
- [ ] **P12 复现（第 2 次 · 2026-09-23 · 工作台）**：本次直接喂 **canonical YAML**
      （`what_changes` 4 条 + `capabilities.new/modified` 各 1 条）给
      `extract-proposal --format json`，返回 `capabilities: {new: [], modified: []}`（**丢空**）
      且 `what_changes` **虚增为 6 条**（把 `### New/Modified Capabilities` 的 bullet 吞并进来）。
      ⇒ **P12 未修，且不限于「`proposal.md` 生成物」** —— 直供 canonical 也照丢。
      规避照旧：**Gate 内容一律读 YAML 原文，不信 `extract-proposal` 的摘要**。
- [ ] **P45 待修（🔴 高 · 静默 · 2026-09-23 · 工作台）**：`ci check-failures` 的检查器读的是**另一套约定**，
      三项检查在 V3.0.5 项目上**恒为 SKIP**，而汇总仍显示「0 错误」——
      ① `(b)` 找 `change_dir/proposal.md` 里的 `- capability: <名>` 行（`ci.py:375`），
      而模板产出的是 `### New Capabilities` + `- **按号列表进度记录**：…` 粗体项目符号 ⇒ 正则匹配不到；
      ② `(j)` 找 `change_dir/coverage.json`（`ci.py:415-426`），而项目只配了
      `quality.coverage.tool: pytest-cov`，**没有任何环节产出该文件**；
      ③ `(l)` 找**项目级** `project_root/.fstdd/canonical/proposals/<change>.yaml`（`ci.py:581`），
      而 canon 脚手架把产物放在 **change 级** `.fstdd/changes/<change>/canonical/proposals/`
      ⇒ **建库到交付之间恒 SKIP**（先有鸡还是先有蛋：锚定检查要在 BUILD 做，
      但它查的文件要到 DELIVER 才生成）。
      🔴 **SKIP 在汇总里与 PASS 同权**（都不算失败）⇒ 项目可长期报「0 错误」，
      而「范围蔓延 / 覆盖率 / 锚定缺失」三类失败模式**从来没被检查过**。
      🔴 更坏的是同一次输出里 `(d)` 报 **FAIL**（见 P46），掩盖了「其实有三项根本没跑」。
      修法：`(l)` 加 change 级回退（先 change 级、再项目级）；`(b)` 改读 canonical proposal YAML 的
      `capabilities` 段（Canonical-First 下 YAML 才是真源）；`(j)` 约定产出 `coverage.json`
      或直接内联跑 `pytest --cov`；汇总里把 SKIP 与 PASS **分开统计并列出原因类别**
      （「不需要」/「工具看不见」），让「0 错误」不能掩盖「N 项没跑」。
      详见 `experiences/FSTDD003-EXP-20260923-CI-1.md`。
- [ ] **P46 待修（中 · 假阳性 · 2026-09-23 · 工作台）**：`ci check-failures` 的 `(d)`
      把「TC-ID **唯一性**」实现成「**字符串出现次数 == 1**」（`ci.py:311-325`）：
      ```python
      duplicates = [tc for tc in unique if tc_ids.count(tc) > 1]
      ```
      而 test-plan 里每个 TC-ID 出现在 3 处是**正常且必要**的（案例表定义 / 测试执行矩阵 /
      建议补充顺序）⇒ 实测 **19 个 TC 全被判「重复」**、报成 **FAIL**，
      而「ID 唯一」这条性质**完全成立**。
      修法：只统计 `**ID**` 行里的 TC-ID（`re.findall(r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})", content)`），
      并**额外**报告「同一 ID 出现在多少个不同案例块」。
      规避（本项目已做）：**交叉引用一律用案例号**（`案例 1.7`），不裸写 TC-ID。
      详见 `experiences/FSTDD003-EXP-20260923-CI-1.md`。
- [ ] **P47 待修（中 · 静默 · 2026-09-23 · 工作台）**：`stdd diff` 两条解析口径与项目约定不匹配 ——
      ① TC 引用按**连字符**（`TC-[A-Z]+-\d{3}`，`diff.py:45/70/102`）在源码里找，
      而 **Python 标识符不能含连字符** ⇒ 测试函数名只能 `test_TC_CP_111_…`（下划线）
      ⇒ 覆盖率假 `0/19 (0%)`。**这是语言约束造成的必然错配，不是写法不规范。**
      ② 案例标题正则 `####\s+案例\s+[\d.]+\s*[—\-]\s*(.+)`（`diff.py:36`）的 `[\d.]+`
      **不接受字母** ⇒ `案例 A.1`（按 capability 分组编号，很自然的组织方式）全部解析不到
      ⇒ 直接 `未找到 TC 案例` 退出（`diff.py:56-58`）。
      ③ 附带：`diff.py:104-114` 的「测试函数」列归属算法取「文件里**首次**出现该 TC-ID 的行
      往上找最近的 `def test_`」，会被类 docstring 的分组注释带偏（实测 `TC-CP-111`
      归到 `test_TC_CP_126_…`）⇒ 修好前**只信覆盖率那一行**。
      修法：比对前**规范化分隔符**（`re.sub(r"[^A-Za-z0-9]", "", s)` 两边都做，
      一行改动解决一整类语言差异）；标题正则放宽到 `[\w.]+`；算不出来时输出
      `N/A（未匹配到任何引用）` 而不是 `0%`（`0%` 与「真的没写测试」长得一样）。
      ⚠ **已实测确认 `ci` 与 `diff` 口径一致**（都做字面子串搜索）：一次格式错配会让
      **两条独立的质量信号同时失效**，没有交叉验证兜底。
      详见 `experiences/FSTDD003-EXP-20260923-DIFF-1.md`。
- [ ] **P48 待修（🔴 高 · 工具误用族 · 2026-09-23 · 工作台）**：一次性批量改写脚本
      「说成功但把文件改坏」的通用形态 —— `re.sub` 回调返回 `m.group(0) + 后续上下文`，
      而 `re.sub` **只替换 `m.group(0)` 那一段** ⇒ 上下文被重复插入、文件结构损坏；
      脚本仍打印「已改写 19 处」、退出码 0。症状：pytest **收集阶段**就失败、
      `ruff` 从 **21 → 741** 条、行数 1443 → 1621。
      🔴 判别信号是**数量级**（不是「多了 20 个新问题」而是「文件被毁」）。
      修法（固化为纪律）：① 机械改写**优先「按行 split→改行→join」**，不用 `re.sub` 回调；
      ② 回调里**永不**写 `m.group(0)+…`；③ 捕获组先 `print(repr(...))` 核对再拼接；
      ④ **脚本自带四项量纲校验**（命中处数 / 文件行数 / 静态检查条数 / 与备份 diff 行数），
      任一不符就**停下来**；⑤ 改前 `cp` 到**仓库外**备份（本次靠它 30 秒内无损还原）。
      详见 `experiences/FSTDD003-EXP-20260923-SCRIPT-1.md`。
- [ ] **P49 待修（🔴 高 · 阻断型假阳性 · 2026-09-24 · 工作台）**：`verify_workbuddy_skills.py` 的默认输出目录
      写死在 `Path.home()/".workbuddy"/"skills"`，而 WorkBuddy 运行期实际加载的是
      **`~/.workbuddy-ai/skills`** ⇒ 校验器查的是**另一个 skills 根**（本机那里躺着
      2026-09-17 的旧副本 `fstdd-deliver/SKILL.md`，8460 B）⇒ 报 **4 项 FAIL**。
      🔴 **危害是阻断型的**：`fstdd-deliver` skill 的收尾硬性规程写着「第 2 步输出 FAIL 时，
      **禁止继续任何 DELIVER 相关操作**」—— 照章执行就会**无理由卡死交付**。
      实测：只把 `FSTDD_OUT` 指向真实目录，同一脚本 **6/6 PASS、exit 0**。
      修法：① `OUT` 默认改为 `~/.workbuddy-ai/skills`；② 两个目录都在时**两个都查**
      并把「本次实际校验了哪个目录」打进输出；③ 打印的修复命令改用 `sys.executable`
      （现在硬编码 `C:\Python311\python.exe`，本机不存在）。
      🔴 关键性质：**校验器必须自报它查的是哪里** —— 否则「6 个 skill 全通过」这句话本身不可信。
      详见 `experiences/FSTDD003-EXP-20260924-DELIVER-1.md`。
- [ ] **P50 待修（中 · 恒不可用 + 文档错误归因 · 2026-09-24 · 工作台）**：`stdd structure delta/merge`
      拼 `<root>/changes/<name>`，**漏了 `.fstdd/`**；而同一 CLI 的 `archive` 走
      `find_change_dir()` + `.fstdd/` 前缀 ⇒ **同一 CLI 内两套路径基准** ⇒ FSTDD 布局下**恒 `not found`**。
      🔴 且这**不是顺序问题**：`fstdd-deliver` Step 2.5 把症状归因成「Step 1 把目录移走了，
      按字面顺序执行必然报错」，实测**归档之前跑照样报** —— **错误的根因解释比没有解释更贵**，
      它把排查者锁在一个永远不会成功的动作上（调顺序）。
      更深一层：该命令扫的是 **change 目录里的代码文件**，而 FSTDD 的 change 目录**只有 md/yaml**
      （本 change 非 md/yaml 文件数 = 0，真代码在 `modules/`、`tests/`）⇒ **修对路径也只产出空清单**。
      修法：要么全改走 `find_change_dir()` 并把扫描源改成 `git diff --name-only <base_gate1>..HEAD`；
      要么把 Step 2.5 标为**已知不可用**并移除。🔴 无论选哪条，**先修 skill 里那句错误归因**。
      详见 `experiences/FSTDD003-EXP-20260924-DELIVER-1.md`。
- [ ] **P51 待修（中 · 顺序自相矛盾 · 2026-09-24 · 工作台）**：`canon verify <change>` 归档后**必失败** ——
      `canon.py` 里 `generate` 走 `_get_canonical_dir()`（有 change 级→项目级兜底），
      而 `verify` 直接拼 change 级路径、找不到就 `Error:` + exit 1。
      ⇒ 白皮书给的 DELIVER 顺序 `archive → 合并 specs → 合并 canon YAML → canon verify → structure merge`
      里，**`canon verify` 在自己的顺序里必然失败**（它要的 change 级 canonical 刚被 archive 搬走）。
      本次规避：只在**归档前**跑（2/2 通过），归档后那次失败仅记录。
      修法：`verify` 改用 `_get_canonical_dir()` 并明确打印「回退项目级」；
      或把顺序改为 `合并 canon → canon verify → archive`。
      详见 `experiences/FSTDD003-EXP-20260924-DELIVER-1.md`。
- [ ] **P52 待修（🔴 高 · 静默丢内容 + 与 P44 同族 · 2026-09-24 · 工作台）**：`stdd canon generate` 两处。
      **① `--dry-run` 不 dry** —— 实测真写了 `proposal.md`（5392 B），且打印 `Generated …`
      而非 `[dry-run] 将…`；与 **P44**（`gate approve --dry-run`）同型：`--dry-run` 定义在父 parser，
      `cmd_canon_generate()` 里 `grep dry_run` **0 命中**。
      ⚠ 对照：`stdd new --dry-run` **真的 dry** ⇒ 失效是**逐命令**的，不是全局的。
      **② Human View 静默丢三节** —— `canon.py:317` 注释写 "from template or direct mapping"，
      但整个函数是**硬编码拼字符串**（`no Jinja2 dependency`），只覆盖
      title / Why.problem / what_changes / capabilities / success_criteria
      ⇒ **`why.motivation` / `constraints` / `non_goals` 全丢**（实测丢 13 条），
      而 `.fstdd/templates/human-view/proposal-brief.md`（这两节都写了）是**死代码**。
      🔴 **丢的正是用户唯一的审阅面**（Gate 1 就是看 proposal.md）。
      🔴 **为什么一直没被发现**：`canon verify` 的 `DC-FIELD` 验的是**反方向**
      （「MD 里引用的字段在 YAML 里存在」），而坏的是「YAML 里有的 MD 里没有」
      ⇒ **两个方向都通过，双轨一致性绿灯而内容已少一半**。
      修法：① 所有会写盘的命令补读 `getattr(args,"dry_run",False)`（与 P44 **合并成一个全命令审计**）；
      ② `canon generate` 改成真用模板（Jinja2 已是既有依赖），或至少补全三段映射；
      ③ `canon verify` 增加**反向**检查 `DC-FIELD-REV`（YAML 非空字段须在 MD 有对应节）。
      本次规避：把 constraints / non_goals **人工贴进 Gate 1 确认框**。
      详见 `experiences/FSTDD003-EXP-20260924-CANON-1.md`。
- [ ] **P54 待修（🔴 高 · `canon generate` 第二族，承 P52 · 2026-09-24 · 工作台）**：
      **① `--type {proposal,design,spec}` 被静默忽略** —— `canon.py:243` 把 `args.type` 传进
      `_generate_one()`，而函数体内 `output_file = change_dir / "proposal.md"` **硬编码**，
      `grep -n "gen_type" canon.py` → **只有签名那一处、函数体零引用**。
      实测 `--type spec` 与 `--type proposal` 输出**逐字相同**。与 P52 的 `--dry-run`、
      `EXP-20260923-GATE-1` 的 `gate approve --dry-run` **同族：参数被解析、被传递、然后没人读**。
      **② `--all` 复活已归档 change** —— `cmd_generate` 的 `--all` 分支扫的是**项目级**
      `.fstdd/canonical/`（不是 change 级），且 `_generate_spec` 的输出目录取自 YAML 里的
      `meta.change_id` ⇒ 只要项目级 canon 里留着任何已归档 change 的 YAML，就会被写回
      `.fstdd/changes/<已归档名>/`。实测跑一次 `canon generate <change> --all` 凭空多出
      `.fstdd/changes/2026-09-23-wizard-target-per-account/`（proposal.md + 2 个 spec.md），
      而该 change 早已在 `.fstdd/archive/` 里 ⇒ 死 change 被 `status`/`validate`/
      `_find_current_change` 当成**活跃变更**。另：`--all` 分支里 `<change>` 位置参数**被完全忽略**。
      **③ 双轨漂移 ⇒ 再生成的内容比归档更差，还抹掉手工补注** —— 项目级副本只在**归档那一刻**
      写一次，Phase 2 之后的修正与 BUILD 期手工补注**都不回灌**。实测归档里是修正后的
      `{biz: {list_pulled_at}}（实现时去掉了原稿里的 fetched 字段…）`，再生成出来是**原稿**
      `{biz: {list_pulled_at, fetched}}`；归档 `specs/按号列表进度记录/spec.md` 里那 2 行
      BUILD 期偏离注记（`> ⚠️ BUILD 中第 2 次小偏离新增（范围轴）…`）在新产物里**消失**。
      🔴 **而 `canon generate` 的两个入口读写不同副本**：`<change>` 读 **change 级**、
      `--all` 读 **项目级** ⇒ **同一条命令的两种用法产出不同内容**，排查时最容易走偏。
      **④ 🔴 关键事实纠正（我自己的认知错了）**：`specs/<cap>/spec.md` **不是** `canon generate`
      生成的，而是 `gate approve --gate 2` 时由 `gate.py::_auto_generate_human_views` 从
      **change 级** `canonical/specs/code/*.yaml` 自动生成（读对目录、逐条告警损坏 YAML、
      跳过 `TODO` scaffold）—— **它是唯一正确的路径，Phase 2 结束时根本不需要手跑 `canon generate`**。
      ⚠ 但 `fstdd-spec/SKILL.md:265` 把「`canon generate --all`」写成 Gate 2 **兜底手段**，
      恰好把上面 ①②③ 三个坑**一次踩满** ⇒ **skill 必须改**（第 261 行那句是对的，第 265 行有害）。
      本次规避：不删先隔离（`mv` 到 `.fstdd/_quarantine/`；动手前查 `os.lstat().st_reparse_tag`
      确认**非目录联接**才敢用普通移动）。详见 `experiences/FSTDD003-EXP-20260924-CANON-2.md`。
- [ ] **P53 待修（🔴 高 · 字段无人负责 + 静默降级 · 2026-09-24 · 工作台）**：
      `complexity_score` / `mode` / `score_confidence` **三个字段没有任何 CLI 写入端**。
      `new.py:59-62` 硬编码 `mode: "standard"` + `complexity_score: None` + `score_confidence: None`，
      注释却写着 `# V2.9: set by Phase 1 Step 3.5`（**一个从未实现的承诺**）；
      全 CLI `grep "complexity_score"` 只有 `new.py:61` 与 `batch.py:567` 两处、**都在写 `None`**。
      `mode` 更明确：`schema-verify.md` 声明 `writers: [new, gate]`，而
      `grep -n "mode" gate.py` → **0 命中** ⇒ **声明的写入端不存在**。
      `fstdd-understand/SKILL.md:104` 只说「模式确认后写入 `.fstdd.yaml`」，**不给命令、不给键位置**
      ⇒ 只走 CLI 的执行者在这一步**不可能合规**，只能静默跳过或凭空宣称已写。
      实测：Phase 1 走完 + Gate 1 已锁，`.fstdd.yaml` 仍是 `null / null / standard`
      ⇒ **12 分 → thorough 的判定静默丢失**；而 `fstdd-build/SKILL.md:95/:180` 真的读 `mode`
      决定质量门强度（lightweight 跳过切片规划 / standard-thorough 走 test-plan 的 TC 转换）
      ⇒ **大型变更被按标准档执行，无报错、无告警**，`stdd validate` 也照样「验证通过」
      （schema 里 `required: false` ⇒ 永远拦不到）。
      🔴 **最阴的一层：`stdd status` 里有个同名不同义的键** —— `status.py:29-30` 读的是
      **`long_range.mode`**（`normal`/`full_auto`，**交互模式**），而不是顶层 **`mode`**
      （`lightweight`/`standard`/`thorough`，**复杂度档位**）。两个轴共用一个名字
      ⇒ 没有任何 CLI 界面能把 `mode` 读回来，排查时极易去改**错的那个键**。
      本次规避：**手工补写三个顶层键**（`12` / `thorough` / `preliminary`），
      并先读代码确认 `phase.py` / `gate.py` 都是 `safe_load → 原地改 → dump`
      ⇒ **手改键不会被后续命令抹掉**（这是敢动手的前提，务必单独验）。
      修法：① 给写入端（`gate approve --gate 1 --mode … --complexity-score … --score-confidence …`，
      正好对上 schema 声明的 `mode.writers: [new, gate]`）；② skill 正文**给可复制的命令**
      （无命令时明写「手工编辑这三个顶层键」+ YAML 片段）；③ Gate 1 时 `complexity_score is None`
      **必须警告或阻断**（当前没有任何检查会碰到它）；④ 杀掉同名碰撞
      （`long_range.mode` → `interaction_mode`，或顶层 `mode` → `quality_mode`），
      并让 `stdd status` **两行都打**；⑤ 删掉 `new.py:61` 那句误导注释。
      详见 `experiences/FSTDD003-EXP-20260924-MODE-1.md`。
- [ ] **P55 待修（🔴 高 · 门禁字段被静默降级 · 2026-09-24 · 工作台）**：
      `stdd phase advance` **会把已过门阶段的 `status` 从 `completed` 降回 `in_progress`**
      —— 即「已确认的门被无声撤销」。
      **实测**：`gate approve 2026-09-24-native-wx-ui --gate 2 --confirmed-by dialog --evidence "确认"`
      正确写入 `phases.spec.status: completed`（`confirmed_*` 四字段齐全），
      之后为了修正 `current_phase`（approve **不写**这个字段，仍停在 `understand`）跑了
      `phase advance 2026-09-24-native-wx-ui spec` ⇒ 输出**只有一行正常的推进文案**
      `Phase 1: UNDERSTAND → Phase 2: SPEC`，**无报错、无警告、无「会覆盖已有状态」提示**，
      而 `phases.spec.status` 已变成 `in_progress`。
      **根因①**：`phase.py` advance 分支（约 :173-175）
      `phases.setdefault(nxt, {})["status"] = "in_progress"` —— `setdefault` **只保证键存在、
      不保证值不被覆盖**，对 `nxt`（要进入的阶段）**零前置检查**；
      同一分支对 `current`（要离开的阶段）**反而有** gate 检查（`confirmed_at` 必须存在）
      ⇒ **只防「没确认就想走」，不防「已确认的被退回」**。`set` 分支（:194）是**同一写法**。
      **根因②**：`target_phase` 位置参数**被完全忽略** —— advance 分支只做
      `nxt = _PHASE_ORDER[idx + 1]`，**从不读 `args.target_phase`**。
      实测传 `spec`（恰 == `understand+1`）看不出异常；传 `build` 也照样只推进到 `spec`。
      与 P52（`canon generate --dry-run`）、P54（`canon generate --type`）、
      `EXP-20260923-GATE-1`（`gate approve --dry-run`）**同族：参数被解析、被传递、然后没人读**。
      **🔴 危害面 = 门禁字段，不是展示字段**：`guard.py:415`（「前序阶段全部 `completed`」才算合法到达）、
      `batch.py:539`（`spec.status != "completed"` ⇒ 批级直接 🚫 阻断）、
      `batch.py:351-353`（门状态显示 ✅ → ○，**已确认的门看起来没过**）、
      `archive.py:29`（`build_done` 判定 ⇒ **拒绝归档**）、`status.py`（人看到的唯一界面变了）。
      **🔴 最阴的一层**：`confirmed_at` / `confirmed_by` / `confirmed_evidence` **三字段原样保留**
      ⇒ YAML 里「确认信息」看着完好无损，**只有 `status` 一个词变了**；
      排查时若只 grep `confirmed`，会得出「门还在」的结论。
      **为什么这次会踩到**：`fstdd-spec/SKILL.md` Step 7 第 5 项写「更新 `.fstdd.yaml`
      （phase: spec → completed, confirmed_at 时间戳）」——**不给命令、也不说不要用什么命令**，
      执行者自然会拿官方推进命令 `phase advance` 去「更新 phase」；而
      `gate approve` 与 `phase advance` **各自只负责一半状态**（前者只写 `status`、
      后者只写 `current_phase`），且 `advance` 会破坏 `approve` 的成果
      ⇒ **正确顺序只能是 advance → approve，反过来就丢状态**。
      本次规避：手工把 `phases.spec.status` 改回 `completed`（`confirmed_*` 未动），
      并**同时核对 `current_phase` 与 `phases.<x>.status` 两个字段都对**（只修一个会留下
      「阶段对了但门显示没过」或反之）；**不再跑 `phase advance`**。
      修法：① advance 加「禁止降级」守卫
      （`if nxt_data.get("status") != "completed": nxt_data["status"] = "in_progress"`，
      要重开必须走显式 `set` + 确认）；② advance 读取 `target_phase`，
      或在忽略它时**明确报错**；③ `gate approve` 顺带把 `phase_key` 写进 `current_phase`
      ⇒ **从根上消除「必须再跑 advance」这个多余动作**；④ skill 侧写明正确顺序（已改）；
      ⑤ `phase status` 增加提示：`status == in_progress` 但 `confirmed_at` 存在 ⇒
      打印「可能被 advance 降级，请核对」。详见 `experiences/FSTDD003-EXP-20260924-PHASE-1.md`。
- [x] **（已闭合）引擎副本与源漂移** —— 见「15. 第 15 轮」。
      原条目：「引擎副本与源会随时间漂移（`setup_engine.py` 每次比对 sha256 并告警，
      `TC_SC_034` 也守着）。**不改上游**是 D哥 定的范围，漂移只告警不自动同步。」
      → 2026-09-21 已按 D哥 裁定单开 change 落地（只告警 + 显式 `--sync-engine`）。

## 6. 第四轮（2026-09-17 · 真实业务变更实战）

前两轮测**安装/运行**，本轮测**真实变更跑流程**：在既有项目根下新建子工作区 `reits-writer/`，
`fstdd init` 后立变更 `2026-09-17-corpus-paragraph-integrity`，走完 Phase 1（Gate 1）→ Phase 2。

**结论：安装链路与骨架生成已稳；流程链路（Gate 生成物 ↔ CLI 解析器 ↔ 多工作区锚定）有实质缺陷。**

| 编号 | 问题 | 严重度 | 经验条目 |
|---|---|---|---|
| P12 | `extract-proposal` 对 Gate 生成物系统性失效 + `what_changes` 虚增污染 | **高** | `EXP-20260917-EXTRACT-1` |
| P13 | 嵌套工作区下 change 落到父工作区 + canonical 双轨回退静默写错位置 | 中 | `EXP-20260917-MULTIWS-1` |
| P14 | `init` 自动拉社区经验必失败 + 报错归因错误 | 低 | `EXP-20260917-REGISTRY-1` |

报告全文：`docs/RUN_ISSUES_2026-09-17_reits-writer.md`

### 本轮新增可复用结论

- **P12 最危险处不是"丢空"而是"虚增"**：`what_changes` 6 → 10 条，**数量变多，不看内容发现不了**。
  根因是 `### New Capabilities`（H3）**不终止** `## What Changes`（H2）区间 —— 缺 `## Capabilities`
  父标题时，capability 的 bullet 被 `_parse_section` 吞并。**静默失败里，"变多"比"变空"更难察觉。**
- **Canonical-First 的正确用法**：`canonical/proposals/<change>.yaml` 是唯一真源，
  `proposal.md` 只是 Human View。**人工核对 Gate 内容时直接读 YAML，不要依赖 `extract-proposal` 摘要。**
- **嵌套工作区铁律**：执行 `fstdd` 命令前**显式 `cd` 到目标工作区根**；产出后用
  **绝对路径核对落点**；发现落错位置**不擅自搬迁**（会破坏 Gate 已确认的 traceability），
  记录在案 + 向上游反馈。
- **Git Bash 调 Windows Python 必过 `cygpath -m`**：既有 P3 只覆盖 `install.sh`，
  本轮确认 **CLI 入口 `bin/fstdd` 同样踩**（`~` → `/c/Users/...` → `\c\Users\...` → `can't open file`）。
- **"社区经验拉不到 ≠ 初始化失败"**：`_post_init_experiences()` 异常被吞，`init` 仍 rc=0，可继续。

## 7. 第五轮（2026-09-18 · 完整跑通一个真实变更）

首次**从 UNDERSTAND 到 DELIVER 完整跑通**一个业务变更
（`2026-09-17-corpus-paragraph-integrity`，complexity 9 / thorough / 长程模式）。
Gate 1/2/3 全过，已归档（`.fstdd/archive/`），specs 已合并进 `.fstdd/specs/`。

| 项 | 结果 |
|---|---|
| TC 覆盖 | 19/19 |
| 切片 | 5/5，每切片均有新增测试 > 0 |
| 单测 | 27 → 55 个，全绿 |
| 设计偏离 | 6 项（2 large / 4 small） |

### P15 — 成功标准的**分母错配**（本轮最有价值的流程教训）

Spec 里写「`flat_body_restored` 标记数 > **10,000** 篇」，实测 **7,203** 篇才在 Gate 3
前发现标准不可达。**功能完全正常，是标准写错了。**

根因：写标准时引用实测结论「压平率 50.8%」，但这个比例的分母是**长文子集**
（`content_len >= 1500`，实际只占全库 34.9%），不是全库。
而判据 `is_flat()` 本身要求 `len >= 1500` —— **低于门槛的文章天然不可能命中**，
标准的上限被判据自己压死了。

→ 完整条目：`experiences/FSTDD003-EXP-20260918-CRIT-1.md`
（含「写成功标准前的自检三问」与「绝对值 vs 相对值」对照表）

### 本轮新增可复用结论

- **写带数量的成功标准前必答三问**：① 分母是什么（写成 `分子/分母` 完整形式，别只留百分数）
  ② 分母与判据会不会互相夹逼 ③ 外推样本有没有偏（索引常按某维度聚集，取前 N 条会失真）。
- **实测值低于标准时，先怀疑标准再怀疑实现**：拿实测值反推分母，对不上就是标准错了。
- **标准写错时的处置（D哥 裁定）**：**保留原文 + 加脚注**，不改原文。
  原文是「当时的预期」这一历史事实，改成实测值等于事后美化。
  加 `success_criteria_notes` 写清实测值/根因/正确口径，验收改用新口径断言。
- **实现期偏离要分级**：small（顺序/内部实现）直接改 + 记；
  large（会出数据事故 / 与已确认规范冲突）必须显式标出并交用户决定，AI 不擅自改。

---

## 9. 第八轮（2026-09-18 · archiver-design 设计工作区 · 外部规范冲突）

新建 `archiver-design/`（GUI 设计资产，含 `fstdd init`）。本轮**未走变更流程**，产出的是设计资产
（PRD / IA / 布局 / 设计令牌 / 四屏高保真 HTML 原型）+ 一份外部规范裁剪表。

**结论：本轮无 CLI 缺陷；唯一新增风险是"规范权威性判定"——外部资料自称一票否决，
差点静默覆盖用户既有红线（不碰数据库 / 无登录 / 只采 37 个号）。**

| 编号 | 问题 | 严重度 | 经验条目 |
|---|---|---|---|
| P15 | 外部规范自称"最高优先级/一票否决"，与用户红线冲突时无成文裁定规则 | **高** | `EXP-20260918-DESIGN-1` |

### 本轮新增可复用结论

- **优先级铁律（跨项目）**：① 用户本人指令/亲口红线 ② 项目既有约定 ③ **外部资料一律第 3 级**。
  外部资料**自称一票否决不等于真的一票否决**——它的"一票否决"只在自己的技术前提内成立。
- **静默失败的另一种形态**：不是 CLI 输出错，而是**模型倾向服从"成文权威文本"，
  从而遗忘用户此前亲口的约束**。红线不是被违反，是被遗忘 → 必须写进记忆，不能只在会话里说一次。
- **裁剪要留痕**：任何进入项目的外部规范，产出物里必须有一份**显式三分类表**
  （采纳 / 改造 / 拒绝），且每条"拒绝"注明**与哪条红线冲突**（本次 20 条，落在 archiver-design 的规范适配表）。
- **P14 再次复现**：`init` 拉社区经验必 404，异常被吞、rc=0。确认"拉不到 ≠ 初始化失败"，可继续。
- **高保真原型用 HTML 而非图片**：无 Figma 且离线的前提下，HTML 可点击、能进 git（diff 有意义），
  且**能与实现共用同一份 design-tokens.css** → 从机制上消灭"设计稿和线上不一样"。
  配套冒烟脚本（JS 语法 / 令牌差集 / 死链 / 导航 / 每屏必备）固化在该工作区 tools 下。

### 遗留项

- [ ] P15 待反馈：建议 FSTDD 在 config.d 支持 `external_docs: {name, scope, authority}`，
      让"参考了哪份外部资料、适用到什么程度"进入变更记录，避免口头裁定随会话蒸发。

---

## 10. 第九轮（2026-09-18 · archiver-gui · Phase 1→3 全跑通）

`archiver-gui` 工作区走完 **UNDERSTAND → SPEC → BUILD**（thorough + 长程全自动模式），
change `2026-09-18-gui-skeleton-credential`：25 条 TC 全通过、5/5 切片验证通过。

**结论：流程本身无缺陷；本轮新增的都是"可复用的工作方式"，不是 CLI bug。**

| 编号 | 问题 | 严重度 | 经验条目 |
|---|---|---|---|
| P16 | 复用上游 venv 时假设依赖齐全 → 表现为"双击没反应" | 中 | `EXP-20260918-GUI-1` |

### 本轮新增可复用结论

- **`stdd new <name>` 会自动补日期前缀**：传 `2026-09-18-xxx` 会得到
  `2026-09-18-2026-09-18-xxx`（日期重复）。**只传短名**（如 `gui-export`）。
- **Gate 1/2 的批准前提是 change 目录下已有 `.fstdd.yaml`** → 必须先用 `stdd new` 建骨架，
  否则 `gate approve` 报 `.fstdd.yaml not found`。
- **Canonical 双轨**：`stdd new` 生成的是 `changes/<change>/canonical/`，
  而手工写可能落到项目级 `.fstdd/canonical/`（P13 同类坑）→ **两份都写同一内容最稳**。
- **P12 未复现**：手写 canonical YAML（带 `## New Capabilities` 父标题）时
  Gate 生成的 proposal.md 完整无丢空/虚增 → P12 只针对 Gate 自动生成物。
- **长程模式值得一开**：`AskUserQuestion` 一次预授权后，5 个切片 RED→GREEN 连续跑完无中断，
  比逐切片确认省掉大量往返；Gate 3 仍是强制确认门（未自动跳过）。
- **`.bat` 里的逻辑测不了**：把依赖探测抽成 `check_deps.py` 后 TC 才有确定断言；
  中文 `.bat` 需按 **GBK** 写入（cmd 默认代码页）。

### P17 — Phase 4 的 CLI 路径基准三套并存（`EXP-20260918-GUI-2`）

`canon.py` 用 `.fstdd/changes/<change>`；`structure.py` 用裸 `Path.cwd()/changes/<change>`；
`archive` 又只在**工作区根**能找到 change。同一个 CWD 下必然有的命令能跑、有的 not found。

三个连带后果：
1. **`canon verify` 只能在归档前跑**，而 `fstdd-deliver` 文档把 verify 排在归档之后 → 必然失败。
2. **`structure delta` 必须 CWD=`.fstdd`**，于是结构索引写到 `.fstdd/.fstdd/code-structure/`（凭空多一层）。
3. **`structure delta` 产物恒为空**：它只枚举 change 目录里的非 `.md/.yaml` 文件，而那里只有 md/yaml。

根因：V2.9 把 change 目录搬到 `.fstdd/changes/`，`canon.py` 跟了、`structure.py` 没跟。
**升级改了一半路径约定。**

规避（本次实测有效）：
`canon verify`（工作区根）→ `structure delta`（CWD=`.fstdd`）→ 清 `.fstdd/.fstdd`
→ `archive`（工作区根）→ 手工合并 canonical 到 `.fstdd/canonical/`。

### P18 — 长程模式下 RED 阶段会被静默跳过（`EXP-20260918-GUI-3`）

7 个切片里只有前 3 个真跑了 RED；后 4 个是先写实现再补测试，**一次就绿**。
`fstdd-build` 要求 RED→GREEN，但没有强制检查点，长程 `full_auto` 下这条约束被绕过。

**补偿手段**：优先用**运行时变异**（在解释器里改常量/函数输入，如 `MIN_INTERVAL=0.0`、
`FREQ_HINTS=()`），**不要改源文件** —— 本次一次文件级变异让分页循环跑飞到
`max_pages=10000`，pytest 挂住 4 分钟只能 kill，还要从备份还原。

**建议**：把「本切片 RED 失败数」写进 `slices.md` 记录，事后可核对；
测试报告里如实标注哪些切片没跑 RED。

### 遗留项

- [ ] P16 已记录，无需改工具（属使用方式问题）。
- [ ] **P18 待反馈**：建议长程模式在每个切片 GREEN 前强制校验 RED 失败数 > 0。
- [ ] **P17 待反馈**：建议 CLI 统一用「向上找 `.fstdd/` 标记」确定 project_root；
      `canon verify` 支持读 `archive/<change>`；`structure delta` 改为扫真实变更源码文件。
      另建议 `fstdd-deliver` 文档的 Step 顺序改为
      `canon verify` → `structure delta` → `archive` → `structure merge` → canon 合并。

---

## 11. 第十轮（2026-09-19 · reits-writer 写作层 ②→⑥ 四个变更连跑）

**场景**：`reits-writer` 工作区，把 REITs 写作链路从「② 定角度」一路做到「⑥ 排版导出」，
四个 FSTDD 变更连续走完四阶段（含 2 个长程模式、1 个普通模式）。

| # | change | complexity | 模式 | 切片 | 结果 |
|---|---|---|---|---|---|
| 1 | `2026-09-18-writing-pack` | 9 / thorough | 长程 | 6 | ② 定角度 + ③ 大纲 交付 |
| 2 | `2026-09-18-writepack-polish` | 7 / standard | 普通 | 3 | 大纲 15 段 → 4 段 |
| 3 | `2026-09-18-draft-skeleton` | 9 / thorough | 长程 | 4 | ⑤ 成稿 交付 |
| 4 | `2026-09-18-typeset` | 8 / thorough | 长程 | 3 | ⑥ 排版导出 交付 |

**四道门全部由用户显式确认**（`confirmed_by: dialog`，evidence 逐条落进 `.fstdd.yaml`）。
测试从 0 → 90 个（写作层），采集层 55 个无回归。

### 有效做法（值得固化）

- **小变更把 Phase 1+2 一次做完、两道门一起过**：`writepack-polish` 用这招省了一轮往返，
  用户接受（回复「Please continue.」即视为两门齐过，evidence 里写明）。
- **`gate approve --gate 2` 会自动生成 spec.md Human View**，`--gate 1` 生成 proposal.md Human View。
  不必手工维护这两份。
- **长程模式下的 Gate 3 仍需用户确认**：本次四次都是「我先给 Gate 3 确认框 + 结论摘要，
  用户回「确认」/「Please continue.」后再 `gate approve`」。长程 ≠ 免 Gate。

### 本节点发现的新缺陷

- **P19**：`archive` 合并 master specs 时 SC 编号跨变更静默重复
  （冲突检测只比 Requirement 标题）。详见 `experiences/FSTDD003-EXP-20260919-ARCHIVE-1.md`。

### 遗留项

- [ ] **P19 待修**：见顶层遗留项与 `FSTDD003-EXP-20260919-ARCHIVE-1.md`。
- [ ] 建议 `fstdd-deliver` 的 Phase 4 清单加一条：「归档后检查 master spec 是否含多组同号 SC；
      若有，跨变更引用一律带变更名前缀」。
- [ ] 本次四个变更**均未跑 `canon verify`**（P17 的 CWD 基准问题仍在）——
      归档前的验证只用了 `git status` + 单测，属已知降级。

## 12. 第十一轮（2026-09-19 · archiver-gui · 第 3 批 `2026-09-18-gui-articles-fetch`）

| 项 | 内容 |
|---|---|
| 变更 | `2026-09-18-gui-articles-fetch`（文章管理 F4 + 抓取正文 F5） |
| 复杂度 / 模式 | 12 / `thorough` |
| 四道门 | Gate 1 ✅ · Gate 2 ✅ · Gate 3 ✅（均 `confirmed_by: dialog`） |
| 测试 | 本批 39 条，全量 **95 passed / 0 failed** |
| 交付 | commit `27e3711` + tag `gui-articles-fetch-v1` |

### 有效做法（值得固化）

- **8 个切片全部真跑 RED**（17 errors → 16 errors → 5 failed），
  修正了第 2 批「S4~S7 先写实现后补测试」的问题 —— 代价是多花一轮往返，但换来了可信度。
- **变异测试真的要做**：17 次注入里抓出 **2 条假绿**（P21），
  其中一条是「关键词断言命中注释」，另一条是「服务层常量被上层覆盖」。
  没跑变异的话这两条会一路绿到交付。
- **归档前先跑 `canon verify`**（P17 的 CWD 基准要求）：本次 2/2 通过（DC-HASH / DC-FIELD）。
- **归档后必查四项**（P19 + P20 合并成一条清单）：项目级 canonical 有文件、
  proposal 在、索引里三条路径都能对上真实文件、master spec 无跨变更撞号。

### 本轮发现的新缺陷

- **P20**：`archive` 只合并 Human View，项目级 canonical 双轨与 `.canon-index.yaml` 未同步
  （详见 `experiences/FSTDD003-EXP-20260919-ARCHIVE-2.md`）。
- **P21**（流程侧）：两类形同虚设的断言，靠变异测试才暴露
  （详见 `experiences/FSTDD003-EXP-20260919-MUTATE-1.md`）。

### 遗留项（本轮新增）

- [ ] P20 待修 / P21 待修 —— 见顶层「5. 遗留项」。
- [ ] 本轮归档后 `.pager` 组件类仍缺：`archiver-gui/web/static/app.css` 有单测要求
      **逐字节等于** `archiver-design/mockups/assets/app.css`（TC-SVC-003），设计侧已冻结，
      分页器只能复用 `.toolbar`。等设计侧解冻后补。

## 13. 第十二轮（2026-09-20 · archiver-gui · 第 4 批 `2026-09-18-gui-export` + 第 3 批 E2E 补跑）

| 项 | 内容 |
|---|---|
| 变更 | `2026-09-18-gui-export`（导出屏：配置/估算 + 执行/历史，md / html / epub） |
| 复杂度 / 模式 | 12 / `thorough` |
| 四道门 | Gate 1 ✅（`D1=A 如实做` / `D2=A 自己写`）· Gate 2 ✅ · Gate 3 ✅（均 `confirmed_by: dialog`） |
| 测试 | 本批 34 条，全量 **137 passed / 0 failed**；变异 12 次注入 **12/12 被抓** |
| 交付 | commit `4a91401` + tag `gui-export-v1`（四批 tag 齐：`gui-skeleton-credential-v1` / `gui-accounts-sync-v1` / `gui-articles-fetch-v1` / `gui-export-v1`） |

### 本轮最大收获：真机 E2E 抓出 3 个单测全绿也漏掉的 bug（P22 + P23）

先按 D哥 要求把第 3 批欠的 3 条 E2E 跑掉，结果第一次真抓取就崩：

1. **`run_fetch` 从未建 session**（`_make_session()` 写了没调用）→ 真抓每篇
   `'NoneType' object has no attribute 'get'`。原因：**每个用例都手塞 `session=object()`**，
   真实构造路径覆盖率 0。→ 补 `session = session or _make_session()` + TC-FET-022/023。
2. **状态栏 JS 从不加 `.show`**（CSS 是 `display:none` + `.show{display:flex}`）
   → 长任务界面零反馈，暂停/取消按钮跟着藏起来 = 无法中断。→ 补 `classList.toggle` + TC-FET-020。
3. **已抓过的静默跳过** → 真库 28,665 篇**全部**已抓，默认路径下界面显示「成功 0 篇」无解释。
   → 加 force 开关 + 弹框提示 + TC-FET-019/021。

**结论：变异测试与 E2E 是互补不是替代** —— 变异只能改「被执行到的代码」，
「根本没被执行」和「只在真数据下才触发」这两类洞只有 E2E 能发现。

### 真数据暴露的两类口径偏差

- **体积估算 63.5 GB → 2.2 GB**：抽样取「前 30 篇」，而索引按发布时间倒序、
  前排全是刚抓的带图大篇。改**等距抽样** `rows[::step][:limit]` 后回到 2.2 GB。
- **「失败 1,264 篇」没有解释**：三份索引里 `articles.jsonl`(435) 与 `net_archive`(829)
  **根本不写 `dir`** → 这些篇导出必失败。加 `no_body_count()` + 界面前置提示 +
  中文失败原因（「索引里没有正文落盘路径（dir 为空）—— 这篇得先抓取正文才能导出」）。
- 顺带核实的事实：全库 28,669 篇里**只有 1.4%（386 篇）有本地图片**，
  28,279 篇无图。导出屏如实报「无本地图片 28,279 篇」，不假装嵌入成功。

### 有效做法（值得固化）

- **E2E 脚本自己要先挑对样本**：按 `estimate()` 逐号筛 `no_body == 0`。
  37 个号里只有 3 个合格 —— 不筛就会随机挑到必失败的号，然后误判成产品 bug（本轮踩了两次）。
- **产物级断言**：E2E-005 导完 EPUB 后**解压 zip 数章节**，断言「章节数 == 成功篇数」
  （21 vs 21），比「接口返回 200」强得多。⚠ ebooklib 会额外产出 `nav.xhtml`，计数要排除。
- **真写 EPUB 走 ebooklib**（D2=A 自己写）：一篇一章 + 本地图 `EpubImage` +
  按号分书 + `tmp.replace()` 原子落地。实测 21 篇 → 1 本 / 102 KB / 2.0 s。
- **四个 `.num` 一律留空**、估算值标「估算」，不放假数据 —— 真数据下 28,669 / 2.2 GB 全部对得上。

### 本轮发现的新缺陷

- **P22**（流程侧）：假依赖 / 假数据掩盖真路径（详见 `experiences/FSTDD003-EXP-20260919-MOCK-1.md`）。
- **P23**（流程侧）：真机 E2E 不可替代 + 真数据口径偏差（详见 `experiences/FSTDD003-EXP-20260919-E2E-1.md`）。

### 补做（2026-09-20）：切片级 RED 重放，36/36 变红

第 4 批 8 个切片原本**未严格先 RED**，`slices.md` 只做了如实标注 —— 标注不是验证，
事后用 **revert 重放**真跑了一遍：摘掉每个切片引入的实现（service / router / index.html /
app.js 打补丁），只跑该切片名下 TC，断言必须变红，跑完按字节还原。
脚本 `archiver-gui/.tmp_e2e/red_replay_export.py`（可重复执行）。

- 结果 **36/36 全部变红**；还原后全量 **137 passed**。
- 首轮只红 33/38 → 剩下 5 条里：1 条真·假绿（TC-019 兜底分支恒真，已修）、
  3 条切片↔TC 映射错（已按重放结果改表）、1 条是我补丁打错了（改名保留子串）。
- → 记为 **P24**，见顶层「5. 遗留项」。

### 遗留项（本轮新增）

- [ ] P22 / P23 / P24 待修 —— 见顶层「5. 遗留项」。
- [ ] `archiver-gui` 四批已全部交付（骨架+凭证 / 公众号+同步 / 文章+抓取 / 导出），
      功能面封闭；`.pager` 组件类仍缺（同 §12 遗留），等设计侧解冻。

---

## N. 第 N 轮（2026-09-20 · 工作台接入 / 本机 PG 连线）

场景：把 `archiver-gui`（公众号归档器）迁到 `工作台/` 根目录并跑通；
同时对「工作台连本机 PostgreSQL」走 FSTDD Phase 1（UNDERSTAND）写 proposal。
完整报告见 `docs/VERIFY_SPEC_ISSUES_2026-09-20_workbench.md`。

### 本轮新缺陷（P25–P31）

- **P27（高，流程侧）**：迁移后端口被旧实例占用，新实例 bind 失败（`WinError 10048`）
  但后台启动不回显；curl 打到旧进程，`health` 与所有数据端点**字节级相同** → 误判「运行成功」。
  → `experiences/FSTDD003-EXP-20260920-VERIFY-1.md`
- **P28（高，流程侧）**：成功标准写了「3 张表不存在」这类**环境否定型陈述**；
  库正被并发写入，20 分钟后 `business` 表数 93 → **182**，那 3 张表**存在但 0 行**。
  → `experiences/FSTDD003-EXP-20260920-SNAPSHOT-1.md`
- **P25（中）**：`gate approve` 需 change 级 `.fstdd.yaml` 先存在，缺失时报通用异常。
- **P26（中）**：Human View 只渲染 `## Why` / `## What Changes` / `## Success Criteria`，
  自定义 section（如 `success_criteria_notes`）**静默不渲染且无 warning**；
  `canon verify` 仍报 2/2 通过 → **写错的成功标准若只在自定义字段纠正，Gate 审查者看不到**。
- **P29（中）**：Git Bash 会话 locale 为 GBK，SQL 中文被编成 GBK 发给 UTF-8 的 PG
  → `invalid byte sequence for encoding "UTF8"`，一度误判成「库脏了」。
  **GBK 根因链第三次咬人**（print emoji 崩进程 / Python 中文 `\b` 词边界 / 本次 SQL）。
- **P30（中）**：非同级目录相对路径陷阱**第 3 次**出现（本次在 `tests/test_skeleton.py:18`）。
- **P31（低）**：PowerShell `Add-Type` 被安全策略拦，回收站 API 不可用。

### 有效做法（值得固化）

- **迁移后验证铁律**：只验证**新目录独有的文件**（新增静态资源 / 改过的 title / 新增路由），
  禁止用两端共有的数据端点作判据。
- **纠正成功标准的正确姿势**（D哥 09-18 裁定）：**原文一字不改，另加
  `success_criteria_notes` 脚注**（含 `measured_at` / `finding` / `root_cause` / `correction`）。
- **环境判据不入成功标准**：改成相对/可复算判据；环境状态只在 `risk_areas` 里带快照时间戳记录。
- **单一路径解析器**：`modules/_paths.py` + 环境变量覆盖，改完 grep 确认 0 残留；
  **测试文件也要一起改**。

### 顺带核实的事实（非问题）

- `__MACOSX/`：18 个真实文件 + 22 个 `._*` 元数据，**无任何代码**。
- 迁移包只过来 `migration/`，`路口理财工作台/`（server.py + index.html 1.25 MB）**没过来**
  → 完整工作台组装**阻塞在代码复制**。
- 工作台：`server.py` 纯标准库 / 8518 / `WB_*` 可覆盖；`index.html` 单文件零 CDN；
  行情走 `BrowserBackend` 浏览器直连东财（不经 server），分析/净值/持仓/通知依赖 server
  → **server 一挂就是「外壳在、数据全空」**。

### 遗留项（本轮新增）

- [ ] P25–P31 待修 —— 详见 `docs/VERIFY_SPEC_ISSUES_2026-09-20_workbench.md` 末尾清单。
- [ ] 阻塞项：等 `路口理财工作台/` 从 Mac 复制到本机后，才能按
      `工作台/docs/公众号页面接入方案.md` 完成「公众号视图接入 + 双端 8518/8733 打通」。

---

## 14. 第 14 轮（2026-09-21 · 工作台自包含 · 目录联接）

**场景**：`D:\项目\工作台` 要做成自包含（D哥：`工作台要做成自包含模式，不要代码散了`）。
约束（D哥 选项）：**只搬引擎代码、数据留原地**；**只搬工作台、别动别的项目**。

**注意**：本轮**未走 FSTDD 四阶段**（是运行期工程改造，非规格变更）。
记录的价值在于问题群本身，不在流程。

### 方案

```
工作台\engine\{archiver,netutil,profile_ext_fetch,target_gap_v2}.py  ← 逐字节复制，一行未改
工作台\engine\{data,archive,net_archive,exports}  ← NTFS 目录联接 → wechat-archiver\*
工作台\公众号 (1).json                            ← 硬链接（target_gap_v2.ROOT 要读）
工作台\.venv                                      ← 自带解释器
```

**为什么用联接而不是改代码**：四个模块的数据常量**全是**
`Path(__file__).resolve().parent` 派生（`archiver.py:49` /
`profile_ext_fetch.py:48` / `target_gap_v2.py:48-56`）。
改代码 = 副本与上游**永久分叉**；挂联接 = **零修改**生效。

### 本轮新缺陷（P32–P38）

- **P32（🔴 高 · 真实数据丢失）**：`Remove-Item -Recurse` 删目录联接
  **递归删掉了目标里 1015 个真实文件**；报错却是 `SAFE_DELETE_FAIL_CLOSED`
  （看起来只是「删不掉」）。
- **P33（中）**：`os.readlink()` 对联接返回 NT 前缀 `\\?\D:\...` →
  与普通路径比较永远不等 → 幂等性归零（每次都「将重建」）。
- **P34（中）**：联接/硬链接不能进 git（否则 `git add` 递归扫进 2 万多个数据文件）。
- **P35（中）**：`is_junction` 判据必须用 reparse tag，`islink`/`is_dir` 都不可靠。
- **P36（中）**：`mklink` / `New-Item -ItemType Junction` 过 shell → 中文路径 GBK 乱码；
  改 ctypes 直调，**顺带免管理员**。
- **P37（🔴 高 · 静默）**：引擎未就绪若返回空路径 → 读数据接口**静默返回空**。
  本项目**第三次**踩同类事故。
- **P38（低）**：守卫测试把 `venv` 自动生成的 `activate.bat` 当违规 →
  守卫常红 → 被无视（比没有守卫更糟）。

### 有效做法（值得固化）

1. **「代码搬走 + 数据留原地」优先选联接而非改代码** —— 当数据路径由
   `Path(__file__)` 派生时，改代码会让副本与上游永久分叉。
2. **删除类操作先校验对象类型，再删**；把「拒绝删除」做成显式异常而非静默跳过。
3. **凡「按路径判断是否已就绪」的逻辑，必须能区分「没配好」与「没数据」** ——
   就绪判据要同时查「代码在」+「数据在」。
4. **验证脚本要能自己发现配置缺失**，不能等报错才暴露。
5. **建 NTFS 重解析点用 ctypes 直调**，不走 shell —— 中文路径 + 免管理员一次解决。
6. **自愈判据不能是「存在即跳过」**（`.lnk` 的 `lnk_is_valid()` 同理：
   判据是 `LinkFlags` bit0 + `IDListSize` 长度，不是文件存在）。

### 顺带订正

`FSTDD003-EXP-20260920-LNK-1.md` 顶部结论（「唯一逃路是手写 .lnk 二进制」、
「去掉 IDList 就对了」）**已推翻**，原文末尾追加
`## ⚠️ 事后订正（2026-09-21）`（保留原文，另加脚注）。
真实判据是 `LinkFlags` bit0 置位 + `IDListSize` 为几百字节真实 PIDL。

**元教训（值得单独记）**：**症状相同的两个 bug 会互相顶罪。**
那一轮「双击没反应」= ①坏的 .lnk（图标就不对）+ ②GBK bat + `chcp 65001`（图标对了也不动）。
先修好 ①，症状只变了形式（从「白纸图标」变成「图标对但不动」），
被误判成「①没修好」，又回头折腾 .lnk 一整轮。
→ **修复后要把剩余症状当成新问题独立复现一次。**

### 验证证据

```
tools/setup_engine.py --check      → 4 联接 + 1 硬链接全 [ok]，连跑两次无 [new]
tools/check_engine.py              → 所有数据常量 resolve() 落在真实数据根，全 OK
ctypes 探针建/删联接               → 中文路径无损；删除后目标 4 文件完好
8733/8518 用自带 .venv 重启         → /api/health 200
POST /api/fetch/start force 重抓    → 成功 1 篇 · 失败 0 篇（17s）
                                      失败那篇原因是内容级（视频类无图文正文），
                                      证明引擎经联接加载成功、URL 解析成功
产物落点                            → archive/中金点睛/2026-09-21_...；
                                      索引 articles_local.jsonl 两路均 28568 行（同一份）
测试                                → 183 → 207 passed（0 skipped）
```

### 遗留项（本轮新增）

- [ ] P32–P38 待修 —— 见顶层「5. 遗留项」，详见
      `docs/JUNCTION_SELF_CONTAIN_2026-09-21_workbench.md`。
- [ ] **P39 待修**（本轮补验时新发现）—— 配置兜底只在**进程启动时**生效。
      详见顶层「5. 遗留项」与 `experiences/FSTDD003-EXP-20260921-LIFECYCLE-1.md`。
- [ ] 引擎副本与源会随时间漂移（`setup_engine.py` 每次比对 sha256 并告警，
      `TC_SC_034` 也守着）。**不改上游**是 D哥 定的范围，漂移只告警不自动同步。
- [ ] 工作台本地 git 已提交 `e7340d0`（自包含）/ `5d3a249`（概览）/ `a8f9b4f`（运行期可见性），无 remote。

### 补验：模拟「刚克隆」暴露 P39（2026-09-21）

自包含落地后补做了一项验证：**拆掉全部目录联接模拟刚克隆**。

- 好的一半：新进程导入时兜底生效（退回真实数据根），功能不坏；
  `setup_engine.py` 一键复原，`--check` 全 `[ok]`。
- **坏的一半（新缺陷 P39）**：**服务已经在跑时**再拆联接，运行中的进程
  **不自愈** —— `only_unfetched` 返回 `0`（真实 `2`），**不报错、日志干净**。
  根因：`ARCHIVER` / `SELF_CONTAINED` 是**模块导入时**算好的常量，
  兜底的作用域实际只有「启动那一刻」，不是整个生命周期。

**处理**：没做运行期自愈（要把 5 个模块的路径常量全改成函数，
改动面大、回归风险高，而触发条件只是维护动作），改为**让它可见** ——
`_paths.live_status()` 每次重新探测 + `/api/health` 增加 `engine.degraded`，
`degraded` 时 `status` 也变成 `degraded`。

**关键细节**：告警文案必须按「谁在什么时刻看到的」分叉 ——
启动时就未就绪 = 已退回真实数据根（**功能是好的**）；
启动后才丢 = 本进程仍指着坏目录（**会返回空**）。
判据 `ARCHIVER == resolve_engine()`。混成一句会把排查方向带偏。

实测：`ok/false/2` → 运行中拆 `engine/data` → `degraded/true/0` →
重建联接（**不重启**）→ `ok/false/2`。
测试 23 → 27 条（`TC_SC_040–043`），全量 207 → **211 passed**。

**元教训**：**验证一定要跑「坏掉」的分支。**
本次是「模拟刚克隆」这个动作顺带拆掉了联接，才撞见运行期缺口；
只跑 happy path 永远不会发现。凡是「配置兜底」，都要问一句
**「它从什么时候开始生效、到什么时候失效」**。

### 补验的另一半：把「建/修」放进启动链（2026-09-21）

§P39 只解决了「坏掉之后看得见」。**「还没配好」这一半同样静默**，只是方向相反：
克隆后没跑 `setup_engine.py` → 启动时就未就绪 → 兜底退回真实数据根 →
功能/界面/health 全正常 → **用户完全不知道已经不自包含了**。

⇒ `tools/launch.py` 新增 `ensure_engine()`，启动链变 5 步
（`[1/5]` 快捷方式 → `[2/5]` 引擎自包含 → `[3/5]` 依赖 → `[4/5]` 代理 → `[5/5]` 起服务），
**双击即用**。

**前提**：修复脚本必须**幂等且绝不破坏现有状态** ——
已是正确联接就跳过、目标是真实目录就**拒绝覆盖并报错**、删除只用 `os.rmdir()`。
**不幂等的修复脚本放进启动链 = 每次启动做一次危险操作。**

测试：`TC_SC_050`（启动链含该步 + 编号连贯）、
`TC_SC_051`（**真的拆一个联接再调它**，验证修得回来；只断言「源码里有这行」是假绿）。
全量 211 → **213 passed**。

**复用要点**：**凡引入兜底，就要同时把幂等的配置修复动作放进启动链 ——
否则兜底越完善，配置缺失越没有信号。**

---

## 15. 第 15 轮（2026-09-21 · 工作台 · 引擎副本漂移「只告警不自动同步上游」）

**change**：`2026-09-20-engine-drift-warn-only`（工作区 `<project_root>/工作台`）
**模式**：FSTDD V3.0.5 · **lightweight**（复杂度评分 2）—— 本轮是**首次**在
lightweight 模式下完整走完 Phase 1 → Phase 3。

### 变更内容（业务侧）

`engine/*.py` 是 `wechat-archiver/*.py` 的**逐字节拷贝**（必须实拷贝：引擎代码要能
独立分发，不能靠目录联接挂到另一个仓库）。拷贝必然随时间漂移，
而旧实现在**默认运行**（`fix=True`，即双击 `start-all.bat` 走的启动链）下
**静默覆盖**漂移副本。

D哥 2026-09-20 裁定：「按你『只搬工作台、不动别的』的范围，**只告警不自动同步上游**。
单开 change 处理。」

落地为三态 + 四入口：

| 状态 | 默认行为 |
|---|---|
| 缺失 | 仍从源拷（首次引导 / 克隆自举，无本地内容可丢） |
| **漂移** | 🔴 **只告警，绝不覆盖** |
| 一致 | 打一行 `[ok]`（旧实现一致时一行不打 →「空白」既可能是「全对」也可能是「没跑到」） |

```bash
setup_engine.py                # 建/修联接 + 补缺失；漂移只告警（rc=0）
setup_engine.py --check        # 零写入；漂移 → rc=1（可接 CI 的哨兵）
setup_engine.py --sync-engine  # 🔴 唯一会覆盖副本的路径（显式开关）
setup_engine.py --remove       # 拆联接
```

⚠ **默认运行必须 rc=0** —— 否则 `launch.py::ensure_engine()` 会把「代码漂移」
误报成「联接未就绪（会退回真实数据根）」，打出一句**语义错误**的提示。

测试：自包含契约 29 → **37 条**（新增 `TC_SC_060~067`）；全量 286 → **294 passed**。
`TC_SC_034` 保留为漂移哨兵，**只修文案**（旧文案「跑 setup_engine.py 同步」
在新行为下会把人引向**无效操作**）。

### 🔴 本轮最有价值的发现（已固化为 P40–P42）

**测试绿着，但被测分支根本没执行。**

`TC_SC_064` 断言「`--check` 漂移 → rc=1」。它**第一次就绿了**。
真因：`rc=1` 是 `links_ok and files_ok and not drifted` 的**合取**，
而 tmp 测试环境里没有 `engine/data` 联接 → `links_ok` 恒假 →
函数在**第一个 `return 1`** 就返回，**漂移分支一行没跑到**。

修法：隔离里把**与被测分支无关的判定维度**显式置空
（`monkeypatch.setattr(se, "LINK_DIRS", ())` → `all(()) == True`），
让合取只剩被测项。详见 `experiences/FSTDD003-EXP-20260921-DRIFT-1.md`。

**变异自检（本轮做的）**：把漂移分支 `if sync:` → `if True:`（退回无条件覆盖）：

```
TC_SC_060/063/064/066/067  ❌ 红   ← 该红的红了
TC_SC_061/062/TC_SC_034    ✅ 绿   ← 该绿的绿了（同等重要）
```

**「该绿的保持绿」与「该红的红了」同等重要** —— 只报「5 条变红」
不足以证明咬对了位置。

⚠ 变异自检自身也会**假绿**，本轮两个坑（都属「假阳性」族）：
① 锚点里的 `\n` 经 shell heredoc 退化成**字面字符** → 变异体 `SyntaxError` →
**全红** → 被误读成「守卫咬住了」；
② `Path.read_text()/write_text()` 做 LF↔CRLF **换行翻译** → 变异变成
「文件被重写」而非「一行被改」。
对策：锚点不含 `\n`、不带尾部冒号 + `o.find()` 切片 + `compile()` 自检；
变异走 `read_bytes()` / `write_bytes()`。

### 本轮新缺陷（P40–P42，均为「门在但没关」族）

| 编号 | 严重度 | 一句话 |
|---|---|---|
| **P40** | 中 | `experience add` 分类枚举**无「测试设计」类** → 只能塞进语义不匹配的 `coverage_vacuum` |
| **P41** | 🔴 高 · 静默 | `fstdd init` **不生成** `.fstdd/version.yaml` → 版本自检在全新项目上**从来没生效过**，且被「告警不阻断」掩盖 |
| **P42** | 🔴 高 · 静默 | `quality.yaml` 的 `lint`/`coverage` **不可执行**（指向不存在的 `app/`、工具未装），而 `enabled: true` + 模板要覆盖率数字 → **诱导编数字** |
| **P43** | 🔴 高 | **lightweight 模式没落地到 CLI** —— `validate.py:24` 的 `required_files` 硬编码要 `design.md` + `test-plan.md`，而 `lite.yaml` 规定 lightweight 跳过这两份；`grep lightweight` 只命中 `new/batch/bootcamp/__init__`，`validate`/`phase`/`status` 都不读 → **该模式的 change 永远过不了 `validate`**；`status` 还硬编码显示「普通交互模式（默认）」 |

共同形状：**声明 ≠ 事实**。配置写着 `enabled: true` / `lint: <命令>` /
「检查 version.yaml」/ `skip_design: true`，但**没有任何机制验证它真的跑起来了** ——
与「静默失效」同族，只不过坏的是**流程门**本身。
P43 更进一层：**不只是门没关，是「门的说明书」和「门的实物」各说各话** ——
配置说「跳过」、校验器说「必须有」，两个真源打架而无人发现
（只有走到 lightweight 的 change 才会撞上）。
详见 `docs/FLOW_ISSUES_2026-09-21_workbench.md`。

### 确认正常的部分（避免把工具判死）

`gate approve --gate 1` 正常且 YAML→`proposal.md` 自动生成（`source_hash` 落盘）；
**中文证据经 Git Bash 传入 CLI 未乱码**（`confirmed_evidence` 原样落盘）；
`experience add` 的**报错信息质量高**（直接列出全部有效值）；
`.fstdd.yaml` 的 baseline 机制自动记录 `base_git_sha` / `node_id` / `clock_source`；
Git Bash 调 CLI 经 `cygpath -m` **一次通过，未复现 P15**。

### 遗留项（本轮新增）

- [ ] **P40 / P41 / P42 / P43 待修** —— 见顶层「5. 遗留项」，详见
      `docs/FLOW_ISSUES_2026-09-21_workbench.md`。
- [x] **引擎副本漂移**（上一轮遗留）—— 本轮已闭合（只告警 + 显式 `--sync-engine`）。
- [ ] 建议：DELIVER 后**不再手动 `--sync-engine`**，等上游下次真实改动时
      走一次完整路径（告警 → 判断方向 → 显式同步 → 提交），把这条路径**跑通一次**。
- [ ] `engine/` 目前**无漂移**（4 对 sha256 全同，独立 `sha256sum` 复核），
      故本轮**未重新同步** `engine/*.py` —— 本次是**预防性**变更。

---

## 16. 第 16 轮（2026-09-23 · 工作台 · 补抓向导 `2026-09-23-wizard-target-per-account` Phase 1→2）

**场景**：把「补抓向导取到第一个合格凭证后**永久停在 ④ 拉列表**」这个卡点做成 FSTDD change。
Phase 1（UNDERSTAND）在上一轮完成；本轮在用户确认后锁 Gate 1、做 Phase 2（SPEC）。

**Phase 2 产出**（5 份文档 + 1 份索引）：

| 产物 | 规模 | 要点 |
|---|---|---|
| `design.md` | 212 行 | 6 条技术决策，每条带备选方案与排除理由；含数据流图与状态机 |
| `canonical/specs/code/wizard-list-progress.yaml` | 2 req / 6 scenario | 占 `SC-001~SC-006`（capability 按号列表进度记录） |
| `canonical/specs/code/wizard-step-position.yaml` | 2 req / 10 scenario | 占 `SC-007~SC-016`（capability 补抓向导步骤定位） |
| `canonical/specs/agent/<change>.yaml` | 4 个 CP | 含一条**源码级只读守卫**（`wizard_state()` 函数体内不得出现写入调用） |
| `test-plan.md` | 310 行 | `TC-CP-111~126`（16 条）与 16 个 Scenario 一一映射 + 回归风险矩阵 |
| `canonical/.canon-index.yaml` | 更新 | 本 change 有 2 个 capability ⇒ 2 个 spec 文件 |

**本轮新增的规范约束（可复用）**：

- **Scenario id 必须在本 change 内全局唯一**（模板注释原话「全局唯一，对应 TC-ID」）。
  两个 capability 各自从 `SC-001` 起头 = 撞号，必须**全局连续编号**。
- Gate 2 的 Human View 生成器按 `canonical/specs/code/*.yaml` **逐个 glob**，
  以 `meta.capability` 决定落点 `specs/<capability>/spec.md` ——
  **文件名不影响落点**；但 `capability` 含 `TODO` 的文件会被**静默跳过**（`gate.py:146-153`）。
- `status` 的「Spec 文件: N 个」数的是 `changes/<change>/specs/**/*.md`（Human View），
  **不是** canonical YAML ⇒ Gate 2 之前显示 `0 个` **是正常的，不是缺陷**。

**🔴 本轮最有价值的发现（已固化为 P44）**：

`stdd gate approve --dry-run` **不 dry**。本轮按常规姿势先跑 dry-run 预览、再跑真命令，
结果 dry-run 那一步就把 Gate 1 锁上并建立了 baseline，真命令只回一句
`Gate 1 already confirmed at 2026-09-22T18:28:42+00:00`。
根因：`--dry-run` 是**父解析器**的全局开关，`gate.py` 里 `grep dry_run` **零命中**，
approve 分支无条件走 `_auto_generate_human_views()` + `_confirm_gate()`。
详见 `experiences/FSTDD003-EXP-20260923-GATE-1.md`。

**方法侧收获（非 CLI 缺陷，但很贵）**：

- 🔴 **同一条消息里的多个 `Edit` 会互相覆盖**（各自基于同一基线重算 → 最后写入者胜）。
  本轮用 4 条 Edit 改 `test-plan.md` 的 SC 映射，实测**只有第 4 条生效**；
  又因「某条的目标值撞上另一条尚未修改的旧值」产生**级联覆盖**，把 8 行改错。
  ⇒ **同一文件的多处修改必须一次覆盖整块，或分多条消息逐条做**；改完必须
  用**机器校验**（正则比对映射二元组）复验 —— 肉眼扫表格靠不住。
- 审查脚本要写成**能咬人**的形式：第一版只查「SC 数 == TC 数」→ 全绿；
  加严成「`(capability, SC)` 二元组 与 test-plan 的『对应 Spec』行**一一对应**」后，
  立刻抓出 5 处错映射。⇒ **凡是「数量相等」的检查都不算检查。**

### 遗留项（本轮新增）

- [ ] **P44 待修** —— 见顶层「5. 遗留项」。
- [ ] **P12 复现（第 2 次）** —— 直供 canonical YAML 也丢 `capabilities` 且 `what_changes` 虚增 4→6。
- [ ] **（本 change 自身）** Gate 2 待 D哥 确认 → 之后 Phase 3 BUILD（16 条 TC）+ Phase 4 DELIVER。
- [ ] **（本 change 自身的语义变更，Gate 2 需告知）** 修好之后向导语义变成
      「**拉完所有号的列表才进第 ⑤ 步**」，既有 `TC_CP_061` 与 `TC_CP_062` 末例要按新模型改写。
- [ ] **（同轮并行事项，非本 change）** 工作台「三刀前端挂载」已完成并提交（`c629b50`，
      10 文件 +1807/−3，全量测试 305 passed）；下一步「逐页重写 `/accounts` + `/articles`」
      按 D哥 裁定**等本 change 修完再开**。





## 17. 第 17 轮（2026-09-23 · 工作台 · 同一 change 的 Phase 3 BUILD 收尾 + Phase 4 前的质量验证）

**场景**：承接第 16 轮。D哥 确认 Gate 2（「确认，进 BUILD」）并选 **全自动长程模式**；
本轮把 `2026-09-23-wizard-target-per-account` 的 **Phase 3 BUILD 跑完**（切片规划 + TDD + 质量验证 C1~C7），
停在 **Gate 3 等确认**（长程模式下 Gate 3 仍为强制门，不自动跳过）。

**Phase 3 产出**：3 片（原计划 4 片，实测重切 —— SC-002 的 `and` 断言天然跨 C1+C2）、
**19 条 TC**（`TC-CP-111~129`，含 BUILD 中追加的 127~129）、
`tests/test_capture.py` 由 81 → **116 用例**；逐文件全量 **340 passed / 0 failed**。

**本轮新增的规范约束（可复用）**：

- 🔴 **测试口径**：**不要用 `pytest tests/ -q` 单进程全量** —— 本机实测 **832.25s**，
  且出现过 9 分钟停在 21% 被超时杀掉。**逐文件跑**（每个 `timeout 200`）稳定且 ≈58s。
- 🔴 **`stdd diff` / `stdd trace` 需要源码里有「连字符」TC-ID** —— Python 函数名只能带下划线，
  必须在 docstring 里另写一份 `TC-CP-1NN / SC-0NN`，否则覆盖率假 `0%`（→ P47）。
- 🔴 **案例标题必须用 `[\d.]+` 能匹配的编号**（`案例 1.1`，不能用 `案例 A.1`），否则 `diff` 直接退出（→ P47）。
- 🔴 **test-plan 里每个 TC-ID 只能出现一次**（交叉引用改用**案例号**），否则 `ci` 的 `(d)` 报 FAIL（→ P46）。
- **SKIP ≠ PASS**：`ci check-failures` 的 3 条 SKIP 全部**手工补做**并写进 `test-report.md`（→ P45）。

**🔴 本轮最有价值的发现（已固化为 P45~P48）**：

一次 `ci check-failures` 的输出里同时藏着两种「假信号」：
`(d)` 报 **FAIL**（假阳性 —— 把「字符串出现次数」当「ID 唯一性」）掩盖了
**3 项根本没跑**（假阴性 —— 检查器找的路径/格式与 V3.0.5 实际布局不一致，恒 SKIP），
而汇总仍显示「0 错误」。这与 `EXP-20260921-DRIFT-1`（测试绿着、被测分支没执行）是**同一家族**：
**把「没报错」当成「没问题」。**

**方法侧收获**：

- **变异自检要防「假咬人」**：第一版变异体（`try:`→`if True:`）产生悬空 `except` → `SyntaxError`
  → **全红** → 会被误读成「守卫咬住了」。harness 必须给变异体加 `compile()` 语法自检。
  最终 **6/6 按预期**，源码还原 byte-identical。
- **负结论必须带「归因锚点」**：`TC_CP_126`（只读契约）断言「写入点未被调用」是**负结论**，
  单独看永远可能因为别的原因成立 ⇒ 补「读盘计数器非空 + `steps` 五步齐全 + `current=='list'`」，
  证明这次执行**确实走到了**那个分支。
- **读盘边界打桩，不给判据打桩**：打 `load_progress`（读盘边界），**不打** `list_pulled`（判据本身）——
  给判据打桩等于把被测对象换掉了。
- **共享入口被改后必须跑整个测试文件**：`TC_CP_097` 只在跑整文件时才暴露回归（测试方案原本只列了 4 条受影响用例，实测 **5 条**）。
- **覆盖率要逐行核对新增段**：改动文件 77%（`service.py` 80% / `router.py` 63%）看似不高，
  但 `coverage json` 逐行核对后 **新增代码段 100% 覆盖**（未覆盖行全在本变更未触碰的抓包/正文段）。

### 遗留项（本轮新增）

- [ ] **P45 / P46 / P47 / P48 待修** —— 见顶层「5. 遗留项」。
- [ ] **（本 change 自身）Gate 3 待 D哥 确认** → 之后 Phase 4 DELIVER；
      交付说明**必须写明**语义变更「**拉完所有号的列表才进第 ⑤ 步**」。
- [ ] **（本 change 自身的遗留，已记入 test-report 已知限制）**：
      ① 前端「待补（个号）」仍按**凭证轴**算（`#wzRemain` 用 `progress.remaining`），
      新模型下应是「凭证 + 列表」两轴 —— 前端在本 change 范围外，建议单独开 change；
      ② ⑤ 抓正文按钮是**死按钮**（既有问题）；
      ③ `mypy` 未安装且 `quality.typecheck` 指向的 `app/` 目录本项目不存在（配置从模板继承）；
      ④ agent **CP-3**（起服务 + 真实 HTTP 只读冒烟）未跑，需 D哥 侧环境。
- [ ] **（skill 归档）** `electron-renderer-web-mount` 已归档到
      `skills-archive/FSTDD003-electron-renderer-web-mount/`。

## 18. 第 18 轮（2026-09-24 · 工作台 · 同一 change 的 Phase 4 DELIVER 收口）

承接第 17 轮。D哥 确认 Gate 3（`--confirmed-by dialog --evidence "确认"`，**不带** `--dry-run`）后进 DELIVER。
本轮**交付本身顺利完成**，但 DELIVER 这条链上又挖出 **3 条新缺陷（P49~P51）**。

### 交付结果（全部实测）

| 步骤 | 命令 | 结果 |
|---|---|---|
| 版本自检 | 读 `.fstdd/version.yaml` | ⚠ 文件不存在（P-FLOW-1 已知：`init` 不生成）→ 只告警不阻断 |
| 双轨验证 | `canon verify <change>`（**归档前**） | ✅ 2/2 通过（DC-HASH + DC-FIELD） |
| 归档 + 合并 human view | `archive <change> --yes` | ✅ 合并出 2 个 capability spec 到 `.fstdd/specs/`，`status: archived`，目录移入 `.fstdd/archive/` |
| 合并 canonical（项目级） | `cp` 5 个文件到 `.fstdd/canonical/` | ✅ proposals 1 + specs/agent 1 + specs/code 2 + `.canon-index.yaml` |
| 项目索引 | `index update` | ✅ `project-index.yaml updated: 1 changes, 2 capabilities` |
| 知识图谱 | `knowledge merge` | ⚠ 社区图谱不可达 → **本地降级、exit 0**（设计正确，不阻断） |
| 代码结构摘要 | `structure delta` / `structure merge` | ⏭ **跳过**（工具在 FSTDD 布局下不可用 → P50） |
| 加固复验 | `verify_workbuddy_skills.py`（带 `FSTDD_OUT`） | ✅ 6/6 PASS / exit 0（不带则**假 FAIL** → P49） |

### 🔴 本轮最有价值的发现

**三条都是「门在、但走不通」，而且各自有一种不同的坏法：**

| 编号 | 坏法 | 一句话 |
|---|---|---|
| **P49** | **阻断型假阳性** | 校验器查错目录 → 假 FAIL → 而 skill 明写「FAIL 时禁止继续 DELIVER」⇒ **照章执行就卡死交付** |
| **P50** | **恒不可用 + 文档错误归因** | 路径基准漏 `.fstdd/`（与同 CLI 的 `archive` 两套基准）；且 **skill 把症状归因成「归档顺序」** ⇒ 调顺序永远修不好 |
| **P51** | **顺序自相矛盾** | `canon verify` 归档后必失败，而白皮书给的顺序里它就在归档**之后** |

**固化出的三条判据：**

1. **校验器必须自报「它查的是哪里」** —— 否则「N 项全通过」这句话本身不可信。
   本机有两个 skills 根（`~/.workbuddy/skills` 与 `~/.workbuddy-ai/skills`），
   **都长得像真的**（前者还有 `_stdd_source.json` 和上百个别的 skill），光看文件系统分不出哪个是活的 ——
   唯一可靠依据是**运行期加载回执**（`Skill` 工具返回的路径）。
2. 🔴 **错误的根因解释比没有解释更贵。** skill 把 `structure delta` 的 `not found` 解释成
   「归档把目录移走了」，而实测**归档前跑同样报**。照错误解释行动（调顺序）永远不会成功；
   按真因行动（修路径）又会发现**修好也没用**（它的扫描源本身已过时）。
   ⇒ **文档里写根因时，必须带上「怎么证伪它」的实验**。
3. **「工具说 X」不等于「X 成立」**：同一轮里，
   `structure delta` 说 not found（真的坏了）、`verify` 说 FAIL（假的）、
   `knowledge merge` 说社区不可用（真，但已正确降级）。
   **三者输出形态相似、可信度完全不同** ⇒ 每条都要独立验证一次。

### 顺带暴露：一个遗留僵尸 change

`stdd status` 在归档后自动切到 **`2026-09-20-workbench-local-pg`**（09-20 Gate 1 之后停摆，
只剩 `proposal.md` + canonical proposal，`current_phase: understand` 但 `understand.status: completed`），
`stdd validate` 因此报 2 个错误（缺 `design.md` / `test-plan.md`）—— **与本次交付无关**。
⇒ 说明 `stdd validate`（不带 change 名）验的是「当前 active change」，
**归档一个 change 之后必须重新确认它验的是谁**，否则会把别人的错误当成自己的。

### 遗留项（本轮新增）

- [ ] **P49 / P50 / P51 待修** —— 见顶层「5. 遗留项」。
- [ ] **（工作台）僵尸 change `2026-09-20-workbench-local-pg` 待处置**：
      要么恢复推进，要么 `stdd abort` 归档到 `aborted/`，要么明确留着。**未擅自处理**。
- [ ] **（工作台）`.fstdd/config.d/experience.yaml` 的静默回传开关未动**：
      本轮 **Step 2.8 经验回传已跳过**（未执行任何外发）。若确定永久关闭，
      应设 `share.silent.enabled: false` 或环境变量 `FSTDD_NO_SHARE=1`。
- [ ] **（工作台）本 change 的 git 提交 + 首个 tag 待 D哥 确认**（本仓库此前 0 个 tag）。

## 19. 第 19 轮（2026-09-24 · 工作台 · 新 change `2026-09-24-native-wx-ui` Phase 1）

接 D哥 指令「走 FSTDD Phase 1」。新 change = **公众号界面原生重写**（照三刀真实布局，
拆掉挂载探针）。本轮只走到 Phase 1 起草 + 审查，**Gate 1 尚未确认**。

### 本轮唯一的新缺陷：P52

`stdd canon generate` 两处，且**丢的正是用户唯一的审阅面**（Gate 1 就是看 `proposal.md`）：

| 处 | 事实 | 危害 |
|---|---|---|
| ① `--dry-run` 不 dry | 真写了 `proposal.md`（5392 B），打印 `Generated …` 而非 `[dry-run] 将…` | 想「先预览不落盘」的人会误以为没写 |
| ② Human View 丢三节 | 硬编码直接映射只覆盖 5 个字段 ⇒ `why.motivation` / `constraints` / `non_goals` **全丢**（实测丢 13 条）；`templates/human-view/proposal-brief.md` 是**死代码** | 用户在 Gate 1 审不到 7 条约束 + 6 条非目标 |

🔴 **最值钱的一条**：`canon verify` 的 `DC-FIELD` 验的是**反方向**
（「MD 引用的字段在 YAML 里存在」），而坏的是「YAML 里有的 MD 里没有」
⇒ **两个方向都绿灯，双轨一致性通过而内容已少一半**。
与 `EXP-20260921-DRIFT-1` 同族：**「没报错」≠「没问题」**。

### 本轮的方法侧收获（Phase 1 探索阶段）

- **🔴 先查名字，再动代码。** D哥 说的「两屏手搓列表页」，在仓库里有**两份**实现：
  `web/index.html` 的 `view-accounts`/`view-articles`（8733），和
  `路口理财工作台/index.html` 的 `view-wxaccount`/`view-wxarticle`（8518）。
  `git log -S "view-wxaccount" -- web/index.html` → **0 条**，证明这个名字**只在 8518 那份**，
  而 `docs/三刀前端挂载.md:325` 在讲 8733 的上下文里用了它 ⇒ **文档串名了**。
  ⇒ 若照着文档猜，会把「删 8518 的两屏」当成「删 8733 的两屏」，**方向完全反了**。
  这类「名字对不上」只能靠 `git log -S` + 逐份 grep 证实，不能靠上下文推断。
- **参照物当代码读，不要当界面看。** 三刀渲染层是压缩后的 Vue，
  但 `grep -o '"[^"]*[一-龥][^"]*"'` 抽中文文案能**快速画出它的功能边界**
  （实测抽出「云端清单 / 一键导入 / 新建分组 / 广场 / 已达单次同步上限 / 互动数据 /
  抓取评论 / 付费文章 · 当前仅为免费试读 / 导入 JSON / Excel 文件」）
  ⇒ 一眼看出「哪些功能我们**根本没有对应通道**」，直接写成 non_goals，避免做出死按钮。
- **删除面要先证「没人引用」。** `grep -rn "sandao" app.py modules/*.py modules/*/*.py`
  （排除 `modules/sandao/` 自身）→ **0 命中**，`modules/sandao/` 只靠 `manifest.json` 自动挂载
  ⇒ 删除是干净的，可以在 proposal 里写成可验证的成功标准（`/sandao/` 与 `/api/_ipc*` 返回 404）。

## 20. 第 20 轮（2026-09-24 · 工作台 · Gate 1 落地后复核，挖出 P53）

**触发**：D哥 确认 Gate 1 后，按惯例**复核落盘状态**（`ls` change 目录 + `cat .fstdd.yaml` + `stdd status`），
而不是直接宣布 Phase 1 完成。**这一轮的价值全部来自「多看一眼状态文件」这个动作。**

### 本轮新缺陷：P53 —— 三个字段没有任何 CLI 写入端

| 字段 | schema 声明的写入端 | 实际写入端 | Gate 1 后的实测值 |
|---|---|---|---|
| `mode` | `[new, gate]` | 只有 `new`（硬编码 `standard`） | `standard`（应为 `thorough`） |
| `complexity_score` | `[understand]` | **无** | `null`（应为 `12`） |
| `score_confidence` | — | **无** | `null`（应为 `preliminary`） |

三条证据链：

1. `new.py:59-62` 硬编码 `mode: "standard"` / `complexity_score: None` / `score_confidence: None`，
   注释写着 `# V2.9: set by Phase 1 Step 3.5` —— **一个从未被实现的承诺**。
2. 全 CLI `grep -rn "complexity_score"` → 只有 `new.py:61` 与 `batch.py:567`，**都在写 `None`**；
   `grep -n "mode" gate.py` → **0 命中** ⇒ schema 声明的 `mode.writers: [new, gate]` 里那个 `gate` **不存在**。
3. `fstdd-understand/SKILL.md:104`：「模式确认后写入 `.fstdd.yaml`（`mode`, `task_type`,
   `complexity_score`, `score_confidence: preliminary`）」—— **没有命令、没有键位置、没有示例**。

### 为什么这条比前几条更值得记

- **它是「静默降级」而不是「静默丢内容」。** P52 丢的是审阅面（人一眼能看出少了节），
  而 P53 丢的是**质量门档位** —— `fstdd-build/SKILL.md:95/:180` 真的读 `mode`：
  `lightweight` 跳过切片规划、`standard/thorough` 才走 test-plan 的 TC 转换。
  ⇒ 12 分的变更被按 `standard` 执行，**全程无报错、无告警**，而且
  `stdd validate` 照样「验证通过」（schema 里 `required: false`，永远拦不到）。
- **「要求做某件事但不给手段」的指令，实际产出是沉默的违规。**
  只调 CLI 的执行者在这一步**不可能合规** —— 只能静默跳过，或凭空宣称已写。
  这与 P24 系列同源：**没走 RED 的变更事后无法补**，因为没有任何东西记录过「本该走 RED」。
- 🔴 **同名不同义的键是排查陷阱。** `status.py:29-30` 读的是 **`long_range.mode`**
  （`normal`/`full_auto`，**交互模式**），不是顶层 **`mode`**（复杂度档位）。
  `stdd status` 因此**永远看不到**复杂度档位；排查者看到「执行模式：普通交互模式（默认）」
  会以为是模式没设，然后去改**错的那个键**，问题照旧。

### 本次处理

1. 手工补写三个顶层键：`complexity_score: 12` / `mode: thorough` / `score_confidence: preliminary`。
2. 🔴 **动手前先读代码确认手改是安全的**：`phase.py:70/:98/:178/:196` 与 `gate.py:38/:86/:113`
   都是 `yaml.safe_load` → 原地改 → `yaml.dump`，**不是从模板重建 dict**
   ⇒ 手加/手改的键会被保留。**这一步是敢动手的前提，不能省。**
3. 复核：`stdd validate 2026-09-24-native-wx-ui` → **验证通过**。

### 本轮方法侧收获（可复用）

- **「Gate 过了」不等于「Phase 1 的产物落盘了」。** 门只管它自己那几个字段
  （`baseline` / `phases.*.status` / `confirmed_*`），**门旁边那条线可能没人接**。
  ⇒ **每次过门后，把该阶段该写的字段逐个对照 schema 查一遍**，而不是只看门的状态。
- **schema 里 `writers: [...]` 是「应该有人写」，不是「已经有人写」。**
  验写入端要 `grep` 到**实际赋值语句**为止；`required: false` 的字段
  **不会有任何校验器替你发现问题**。
- **手改状态文件前，先确认写盘语义是 `load→改→dump` 还是 `重建 dict`。**
  前者手改安全，后者手改会被下一次 CLI 调用静默抹掉。
- **同名键要当成红旗。** 发现两个不同语义的字段共用一个名字时，
  先假设「读它的地方读错了」，再去找第二个键。

### 本轮结论

- P53 已记录并归档，本次 change 已按正确档位（`thorough`）落盘。
- ⚠ **留给后续 change 的硬约束**：新 change 在 Phase 1 结束时
  **必须手工补写这三个键**，直到 P53 修掉为止（否则每开一个 change 就静默降级一次）。



## 21. 第 21 轮（2026-09-24 · 工作台 · Phase 2 SPEC 的 Step 5.5 自检，挖出 P54）

**触发**：Phase 2 的 `test-plan.md` 刚写完，按 skill 的「Gate 2 前五项自检」逐项核对，
其中一项写的是「`specs/`（`canon generate --all` 后生成）」⇒ 去跑 `canon generate`。
**这一轮的价值来自「按清单核对」这个动作本身 —— 清单里那一项本身就是错的。**

### 本轮新缺陷：P54 —— `canon generate` 的第二族（承 P52）

三条症状，一次踩满：

| # | 症状 | 实测证据 |
|---|---|---|
| ① | `--type {proposal,design,spec}` **被静默忽略** | `canon generate <change> --type spec` → 输出的仍是 `proposal.md`，与 `--type proposal` **逐字相同**。`grep -n "gen_type" canon.py` → **只有签名那一处**，函数体内 `output_file = change_dir / "proposal.md"` 硬编码 |
| ② | `--all` **复活已归档 change** | 跑一次后 `.fstdd/changes/` 凭空多出 `2026-09-23-wizard-target-per-account/`（proposal.md + 2 个 spec.md），而该 change 早在 `.fstdd/archive/` 里 |
| ③ | 再生成的内容**比归档差**，且抹掉手工补注 | 归档 `proposal.md` 是修正后的 `{biz: {list_pulled_at}}（实现时去掉了原稿里的 fetched 字段…）`，新产物是**原稿** `{biz: {list_pulled_at, fetched}}`；归档 spec.md 里 2 行 BUILD 期偏离注记在新产物里**消失** |

三条根因链：

1. **参数被解析、被传递、然后没人读** —— 与 P52 的 `--dry-run`、`EXP-20260923-GATE-1` 的
   `gate approve --dry-run` **完全同族**。这已经是**第三例**了 ⇒ 应当升级成一条**通用审计**：
   全命令 `grep` 每个参数名，凡在签名/解析器里出现、handler 不读的，一律补上或删掉参数。
2. **`--all` 的扫描范围与输出目录分属两套基准** —— 扫的是**项目级** `.fstdd/canonical/`，
   输出目录却取自 YAML 里的 `meta.change_id`。归档动作既不清理项目级 canon，
   `--all` 也不排除 `archive/` 里的名字 ⇒ 死 change 必然被复活。
3. **双轨（项目级 vs change 级 `canonical/`）真的漂移了** —— 项目级副本只在**归档那一刻**写一次，
   Phase 2 之后的修正、BUILD 期的手工补注**都不回灌**。🔴 **最阴的一层**：
   `canon generate` 的**两个入口读写不同副本**（`<change>` 读 change 级、`--all` 读项目级）
   ⇒ **同一条命令的两种用法产出不同内容**，排查时极易走偏。

### 🔴 本轮最重要的一条：一个被写错的「自检清单」

我此前记的「Gate 2 前五项自检包含 `canon generate --all`」是**错的**。
`gate.py::_auto_generate_human_views` 的 docstring 与实现写明：

```python
# - Gate 1 → proposal.md from changes/<change>/canonical/proposals/<change>.yaml
# - Gate 2 → specs/<cap>/spec.md from changes/<change>/canonical/specs/code/*.yaml
```

⇒ **`specs/<cap>/spec.md` 是 `gate approve --gate 2` 时自动生成的**，
读的正是我们写的 **change 级** YAML，还会逐条告警损坏的 YAML 而不静默（DFX-011）、
跳过 `TODO` scaffold。**它是本项目里唯一正确的 Human View 生成路径。**
**Phase 2 结束时根本不需要手跑 `canon generate`** —— 跑了只有害。

⚠ 而 `fstdd-spec/SKILL.md:265` 写着「若 Gate 2 自动生成未生效，手动执行
`stdd canon generate --all` 补齐」⇒ **这条兜底恰好把 ①②③ 三个坑一次踩满**。
同文件第 261 行那句（「无需重复执行 `canon generate --all`」）是**对的**。
⇒ **同一个 skill 里两行自相矛盾，而错的那一行是「出问题时才会看」的那一行。**

### 为什么这条比前几条更值得记

- **P52 与 P54 是同一个函数的两族缺陷，且都没被任何校验器覆盖。**
  P52 是「丢了内容」（人一眼能看出少了节），P54 是「给了更旧/更错的内容」
  —— 后者更危险，因为**看起来是完整的**。
- **它是「工具会主动破坏证据」**：`canon generate` 会用旧快照覆盖掉
  「带 BUILD 期手工补注」的 Human View。而 Human View 是**用户唯一的审阅面**。
  一次误操作就能把审计链上最有信息量的那两行注记抹掉，且**无备份、无告警**。
- **「清单里的错误」比「代码里的错误」更贵**：代码错了会报错，清单错了会让人
  **按清单执行一个有害动作**。这正是本轮的收获 —— 我差点就照着自己写的清单跑了。

### 本次处理

1. **不删、先隔离**：`mv .fstdd/changes/2026-09-23-wizard-target-per-account
   .fstdd/_quarantine/2026-09-23-resurrected-by-canon-generate-all-20260924/`。
   - 🔴 动手前按跨项目铁律查 `os.lstat().st_reparse_tag`：`0x0` ⇒ **不是目录联接**，
     才能安全用普通移动（若是 junction 就只能 `os.rmdir`，否则会递归删掉联接目标里的真文件）。
   - **隔离而不是删**：它与归档**内容不同**（见症状 ③），先留证据给决策人看。
2. **不再跑 `canon generate --all`**，改由 `gate approve --gate 2` 自动生成 spec Human View。
3. 修正 `fstdd-spec/SKILL.md:265` 那条有害兜底（改为「Gate 2 自动生成；若未生效，
   先看 `.fstdd.yaml` 的 gate 状态，**不要**用 `canon generate --all`」）。
4. `changes/` 恢复为 `2026-09-20-workbench-local-pg` + `2026-09-24-native-wx-ui` 两个。

### 本轮方法侧收获（可复用）

- **「按清单核对」之前，先核对清单本身。** 清单是上次的自己写的，
  而上次的自己可能记错了 —— 本轮全部价值都来自「跑之前先读了 `gate.py` 的实现」。
- **凡是「兜底手段」，先确认它在当前状态下是不是**有害**的。**
  兜底通常写于「正常路径不可用」的假设下，但**正常路径可用时跑它，它可能比不做更糟**。
- **一个工具如果同时有「扫 A 写 B」的入口和「扫 B 写 B」的入口，它们迟早会分叉。**
  看到 `--all` 与 `<name>` 两种用法时，先问「它们读写的是同一份东西吗」。
- **第三例同族缺陷 ⇒ 停止逐例记录，改记一条通用审计规则。**
  （`--dry-run` 不 dry / `gate approve --dry-run` 不 dry / `--type` 被忽略 —— 三例同族。）
- **删除前先看 `st_reparse_tag`** 已经是一条跨项目铁律，本轮再次救了场：
  如果那个目录是联接，`rmtree` 会删掉归档里的真文件。

### 本轮结论

- P54 已记录并归档，工作区已恢复干净状态。
- ⚠ **留给后续 change 的硬约束**：**Phase 2 结束时不要跑 `stdd canon generate`**
  （任何形态：`--all` / `--type spec`）。spec Human View 由 `gate approve --gate 2` 自动生成。
  若确实需要预览，**只用** `canon generate <change>`（不带 `--all`、不带 `--type`），
  且它只会重新生成 `proposal.md` —— 它**不生成 spec**，别指望它。





## 22. 第 22 轮（2026-09-24 · 工作台 · Phase 2 SPEC 过 Gate 2，挖出 P55）

### 触发

change `2026-09-24-native-wx-ui` 的 Phase 2 SPEC 走完 Step 5（`test-plan.md`）与
Step 5.5（四路独立审查），D哥 回复「确认」⇒ 跑 `gate approve --gate 2` 过门。
过门后做 Step 7 的收尾两项（更新 `.fstdd.yaml`、生成 `phase-context.md`），
**在「更新 `.fstdd.yaml`」这一步踩到 P55**。

### 症状

| # | 症状 | 实测 |
|---|---|---|
| 1 | `gate approve --gate 2` 正确写 `phases.spec.status: completed` + `confirmed_*` 四字段 | ✅ 正常 |
| 2 | 但 `current_phase` 仍停在 `understand` | approve **不写**这个字段 |
| 3 | 为修它跑 `phase advance … spec`，输出只有一行正常推进文案 | `Phase 1: UNDERSTAND → Phase 2: SPEC` |
| 4 | 而 `phases.spec.status` 被改回 `in_progress` | 🔴 **无报错、无警告** |
| 5 | `confirmed_at` / `confirmed_by` / `confirmed_evidence` **原样保留** | 🔴 只 grep `confirmed` 查不出来 |

### 根因链

1. **`nxt` 无条件写成 `in_progress`** —— `phase.py` advance 分支
   `phases.setdefault(nxt, {})["status"] = "in_progress"`。`setdefault` 只保证键存在、
   不保证值不被覆盖。**对 `nxt` 零检查，对 `current` 反而有 gate 检查**
   ⇒ 只防「没确认就想走」，不防「已确认的被退回」。
2. **`target_phase` 被完全忽略** —— advance 分支只做 `nxt = _PHASE_ORDER[idx + 1]`，
   从不读 `args.target_phase`。传 `spec` 恰好等于 `current+1` 所以看不出；
   传 `build` 也照样只推进一格。**与 P52 / P54 / GATE-1 同族**（参数被解析、被传递、然后没人读）。
3. **门禁字段被降级的危害面** —— `guard.py:415`（前序阶段全 `completed` 才算合法到达）、
   `batch.py:539`（批级 🚫 阻断）、`batch.py:351-353`（门显示 ✅→○）、
   `archive.py:29`（`build_done` ⇒ 拒绝归档）、`status.py`（人看到的唯一界面）。
4. **skill 措辞把人引向这个动作** —— `fstdd-spec/SKILL.md` Step 7 第 5 项
   「更新 `.fstdd.yaml`（phase: spec → completed, confirmed_at 时间戳）」
   **不给命令、也不说不要用什么命令**；执行者自然会拿官方推进命令 `phase advance` 去「更新 phase」。

### 本轮最重要的一条：两个命令各自只负责一半状态

- `gate approve` 写 `phases.<x>.status = completed` + `confirmed_*`，**不写 `current_phase`**；
- `phase advance` 写 `current_phase` + 目标阶段 `status = in_progress`，**不写 `confirmed_*`**；
- ⇒ **两者只能按 advance → approve 的顺序跑**，反过来 `advance` 就把 `approve` 的成果冲掉。

**这是「一个状态被两个命令各写一半、且其中一个会破坏另一个」的典型。**
正确修法不是让执行者记住顺序，而是**让 `gate approve` 顺带写 `current_phase`**
⇒ 把「必须再跑一次 advance」这个多余动作从流程里删掉。

### 为什么这条比前几条更值得记

前几条（P52 / P54）坏的是**产物内容**（Human View 丢字段、被旧快照覆盖），
删掉重跑就能修。**P55 坏的是「门本身」**：

- 它让**已通过的门在状态上变成未通过**，而 `confirmed_*` 还在 ⇒
  **审计链看上去完整，实际状态已不一致**；
- 它**没有报错**，输出是一句正常的推进文案 ⇒
  执行者会以为「我刚刚只是修了个阶段字段」；
- 它的受害者是 `guard` / `batch` / `archive` 三处**流程闸门** ⇒
  一次误跑可能导致**归档被拒**或**后续阶段被判定为非法到达**，
  而排查方向会被引到「为什么 archive 说 BUILD 没完成」这种完全错误的地方。

**一句话：这是「安全机制的状态字段被静默改写」，与 `EXP-20260923-GATE-1`
（`gate approve --dry-run` 不 dry，把防 AI 自批的门一起放行）是同一类问题的两个面。**

### 本次处理

1. 手工把 `phases.spec.status` 改回 `completed`（`confirmed_*` 未动）。
2. **同时核对两个字段**：`current_phase: spec` ✅ + `phases.spec.status: completed` ✅
   （只修一个会留下「阶段对了但门显示没过」或反之）。
3. 复查 `stdd phase status`（`Status: completed`）与 `stdd status`
   （`Phase 2: SPEC: completed (确认于 …)`、`Spec 文件: 3 个`）。
4. **不再跑 `phase advance`**。
5. 归档 `D:\FSTDD003`：`experiences/FSTDD003-EXP-20260924-PHASE-1.md` + 本文件顶层 P55 + 本轮 + README 行。
6. 改 `fstdd-spec/SKILL.md` Step 7 第 5 项：写明「`gate approve` 已写入 `status` 与 `confirmed_*`，
   **不要**再跑 `phase advance`；若需 `current_phase` 正确，**正确顺序是先 advance 再过门**」。

### 方法侧收获

- **过门之后立刻核对「门字段」与「阶段字段」两处，而不是只看一处。**
  凡是「一个逻辑状态被拆成多个字段」的设计，都要问：**这几个字段是否同时被更新？谁负责哪一个？**
- **官方命令不一定适用于你当前所处的状态。**
  `phase advance` 是「推进」命令，在**已经推进到位**的状态下跑它，它不是幂等的 ——
  而是**破坏性的**。⇒ 用任何「推进 / 初始化 / 同步」类命令前，先问它**在当前状态下是否幂等**。
- **看到「输出只有一句正常文案」时要更警惕，而不是更放心。**
  本轮两次踩坑（P54 的 `canon generate`、P55 的 `phase advance`）都是
  「打印了正常的成功文案，同时静默做了一件坏事」。
- **skill 里的「更新 X」这类措辞必须给命令，或明确写「不要用某命令」。**
  只写意图不写手段，执行者就会挑一个看起来最对的手段 —— 而它可能恰好是最坏的那个。
- **本次 gate approve 本身是健康的**：3 个 `spec.md` Human View 自动生成，
  43 个 Scenario 全覆盖（28 + 10 + 5）、SC-042 / SC-043 都在、无 `TODO` scaffold、
  无告警、**未触发 P54 的 `--all` 复活**。⇒ 缺陷是**局部的**，不是流程整体不可用。

### 本轮结论

- P55 已记录并归档。
- ⚠ **留给后续 change 的硬约束（两条）**：
  1. 🔴 **过门与推进的正确顺序是：先 `stdd phase advance <change> <phase>`，再 `stdd gate approve --gate N`。**
     反过来跑会**把刚确认的门降级**。若已经搞反，**手工把 `status` 改回 `completed`**，
     并**同时**核对 `current_phase`。
  2. 🔴 **不要用 `stdd phase advance` 去「修 `current_phase`」** ——
     它同时会写目标阶段的 `status`。要只改阶段而不动状态，用 `stdd phase set`（但注意
     `set` 分支有**同一写法**的降级问题，见 P55 根因①）。
- ⚠ 本轮还留了一个**未处理的旧账**：僵尸 change `2026-09-20-workbench-local-pg`
  （09-20 过 Gate 1 后无进展，`validate` 报缺 `design.md` / `test-plan.md`），
  以及 `.fstdd/_quarantine/` 下的 P54 隔离产物 —— 待 D哥 裁定后处置。

## 23. 第 23 轮（2026-09-25 · 工作台 · change `2026-09-24-native-wx-ui` Phase 3 Part C 的 `ci check-failures`）

**场景**：同一 change 的 Phase 3 BUILD 收尾（Part C 质量验证）跑到 10.4
`fstdd ci check-failures`，**四项口径漂移全量复发**（与第 17 轮 P45/P46/P47 同一批）。

### 本轮结论

- ✅ 结果：`通过 4 / 警告 2 / 跳过 3 / 错误 1`，**10 项全部逐项处置**并写进 `test-report.md`。
- 🔴 **不是新缺陷，是既有 P45 / P46 / P47 的第二次复现** —— 已归档
  `experiences/FSTDD003-EXP-20260925-CI-1.md`（**只记新细节，不重复首次发现**）。
- **三条既有条目没覆盖的新细节**：
  1. **(d) 的规避手段「交叉引用一律用案例号」治不了「同一 TC-ID 被两条测试函数共用」**
     （`tests/test_skeleton.py:78` 与 `:93` 都是 `TC-SVC-003`，分别验设计令牌与组件样式）
     —— 这是**测试侧**组织方式，不是文档侧交叉引用 ⇒ **用户侧不可规避**，
     必须改 `check_tcid_unique` 的实现。
  2. **`TC 实现覆盖` 对「刻意不带 TC-ID 的测试文件」结构性失明**：
     `tests/test_embed_and_identity.py` docstring 第 5 行明写「不属于任何既有 capability」⇒
     该文件永远不计入统计，而本 change 的 `CP-10` 正依赖它覆盖 SC-002/004/007/008/009
     ⇒ 「68%」是**分母错配**，不是覆盖缺口。
  3. **`(j)` 是「文件位置」陷阱**，不只是「没人产出」：`--cov-report=json` 默认写 cwd，
     而检查器读 `<root>/coverage.json`；且 **Git Bash 把 POSIX 路径传给 Windows Python
     会静默失败**（终端说 "Coverage JSON written to file"，文件却不存在）。
- 🔴 **本轮最有价值的元结论**：**规避手段写在经验库/文档里，换一个工作区就全量复发。**
  两条 CI 经验之间隔两天、换 change、换工作区，**同一台机器同一个 CLI**，四项一项不少地复现。
  ⇒ 凡「用户侧规避」的修法，必须同时落成 **(a) 上游源码修复** 或 **(b) 项目模板/脚手架的默认值**；
  只写文档 = 只对读过它的人、且只对读过的那一次有效。

### 遗留项（本轮新增）

- [ ] **P45 / P46 / P47 仍未修** —— 本轮证明其影响是**跨工作区普遍性**的，优先级应上调。
  尤其 **P46（`check_tcid_unique`）**：既有规避手段被证明**用户侧不可达**。
- [ ] 建议把三条规避**做进 `new` 的模板**（见 EXP 条目的「元结论」一节）：
  test-plan 模板默认「交叉引用走案例号」/ proposal.md 在 `### New Capabilities` 下同时产出
  `- capability: <名>` 行 / quality.yaml 模板给一条可复制的覆盖率命令（含 cwd 说明）。
- [ ] `TC 实现覆盖` 建议增加**「文件级归属」**：允许测试文件头部声明
  `# TC-ID: 本文件不适用（原因）`，被声明的文件从分母剔除并在报告里单列。

### 第 23 轮追加（2026-09-26 · 同一 change 的 Gate 3 收口）

**Gate 3 已过，BUILD → DELIVER 推进成功**（`build.status: completed` + `confirmed_by: dialog`；
`current_phase: deliver`；**build 未被降级**，P55 的坑未触发）。

- 🔴 **新增缺陷：`--dry-run` 逐命令失效的**两个新实例****
  （机制早已记过：P44「父 parser 全局开关、handler 不读」/ P52 / GATE-1）：
  - `phase advance --dry-run` —— **真写盘**：实测把 `current_phase: spec` 改成 `build`、
    并把目标阶段 `status` 改成 `in_progress`。输出**只有正常成功文案**，没有 `[dry-run] 将…`。
  - `phase record-slice --dry-run` —— **真写盘**：打印 `Slice S1 evidence recorded`，且 `grep` 确认
    切片证据真的进了 `.fstdd.yaml`。
  - 已归档 `experiences/FSTDD003-EXP-20260926-DRYRUN-1.md`（含「已知不 dry 的命令」对照表 +
    `new --dry-run` **真的 dry** 这个对照组 ⇒ **失效是逐命令的，不能推广，必须当场验**）。
  - 本轮**良性的巧合**：`phase advance --dry-run` 顺手把过期的 `current_phase` 修正了，
    反而避开了 P55（若 `current_phase` 落后，approve 后再 advance 会把刚完成的阶段降级）。
    ⚠ **是运气不是设计，别依赖**。
- 🔴 **新发现：BUILD → DELIVER 有一个隐藏前置** —— `phase advance` 会拒：
  「BUILD → DELIVER 需要 per-slice 验证证据链。请确保每个 Slice 的 `.fstdd.yaml` 中包含
  `tc_coverage` / `new_tests` / `verified_at`」。⇒ 必须在收口时逐片跑
  `fstdd phase record-slice <change> <SID> --tc-coverage "…" --new-tests N --verified-at YYYY-MM-DD`
  （本次 10 片全部补登记）。**这条不在 skill 的显式清单里**，是「强制约束 #5 切片验证不可跳过」
  的机械化落地 —— 建议写进 `fstdd-build` 的 Phase 3 收口清单，否则每次都会卡在推进那一步。

### 遗留项（第 23 轮追加）

- [ ] **P56 待修（新，2026-09-26）**：`fstdd new <name>` **自动补日期前缀** ⇒ 按仓库惯例传
      `new 2026-09-26-<slug>` 会建出 **`2026-09-26-2026-09-26-<slug>`**（双前缀），且 **exit=0 无警告**；
      `validate` / `canon verify` 照样通过（只看结构不看名字）⇒ **静默**。
      正确用法 `new <纯 slug>`。已归档 `experiences/FSTDD003-EXP-20260926-NEWNAME-1.md`。
      修法建议：检测「已含日期前缀」直接当完整名用（或明确报错）+ `--help` 示例补一句
      「**不要**自己带日期」+ `validate` 加一条「目录名不得双日期前缀」的廉价检查。
- [ ] **P57 待修（新，2026-09-26）· 变异自检里的「假红」**：变异夹具用 `env={"PYTHONPATH": ""}`
      **替换**了整个操作系统环境（`subprocess` 的 `env=` 是替换不是叠加）⇒ Windows 上缺 `PATH`/`SystemRoot` 等
      ⇒ pytest **启动即崩**（`OSError: [WinError 10106]` winsock 初始化失败）⇒ `rc=1`
      **看起来与「守卫咬到了」一模一样**，实际与被测代码无关。
      🔴 **假红比假绿更隐蔽**：它**符合预期**，几乎没人会去查「为什么红了」。
      ⇒ 纪律：**「红了」不是证据，「红的理由」才是** —— 变异自检必须打印并看一眼失败的那条断言/异常。
      已归档 `experiences/FSTDD003-EXP-20260926-FAKERED-1.md`（含 harness 自检与三自证清单）。
- [ ] **P44 / P52 家族应升级为一条独立 P 编号**：「`fstdd` 的 `--dry-run` 逐命令失效」，
      并在 `fstdd-*` 各 skill 里对**每个带 `--dry-run` 的命令**标注「已验 dry / 未验 / 不 dry」。
      现状是散在三条经验里，读者容易以为「修过一次就都好了」。
- [ ] 建议 `_write_state()` 统一入口加 `if args.dry_run: print("[dry-run] 将…"); return`，
      并在 `--dry-run` 时**禁止**打印正常成功文案。
- [ ] 建议把「per-slice 验证证据链」写进 `fstdd-build` 的 Phase 3 收口清单。
- [ ] **P58 待修（新，2026-09-27）· `validate` 的 AND 上限是硬编码绝对值且不归属 Scenario**：
      `validate.py:67-70` 用 `len(re.findall(r"\*\*AND\*\*", content)) > 5` 判定，两个独立问题 ——
      ① 上限 `5` 是写死的绝对值（同函数的 GIVEN/WHEN/THEN 都是「少于 Scenario 数量」的归一化判据），
      没有出处、无配置、无 CLI 参数；② 🔴 计数是**全文**次数、**不归属到具体 Scenario** ⇒
      「1 个 Scenario 带 6 条 AND」与「3 个 Scenario 各 2 条 AND」**同样告警**，后者完全正常。
      设计意图（单 Scenario 上限 vs 全文上限）从实现上无法判断。
      🔴 **最刺眼的一层**：同一文件 `validate.py:75-78` 的 TC-ID 检查**正是为修「全文计数误判」加过修正**
      （改为只统计案例定义行），AND 检查**没有做等价处理**。
      影响面：只 append 到 `warnings`、不影响退出码、Gate 2 照常通过 ⇒ 危害在**诱导性** ——
      为了消警去删实质判据，等于「为了守卫改内容」（与 09-26 D-7「改 source_hash 指针」同型）。
      已归档 `experiences/FSTDD003-EXP-20260927-ANDLIMIT-1.md`。
      修法：按 `#### Scenario:` 切段后逐段计数（与 GIVEN/WHEN/THEN 语义对齐）+ 上限提为配置项 +
      告警文案带归属信息 + 补「3×2 不告警 / 1×6 告警」的对照自测。
- [ ] **（流程教训，本轮新增）**：新增 P 编号前**必须**在 `TASK.md` 里 grep 关键词比对，
      本轮 5 条候选里有 **4 条命中既有编号或属误报**（详见「24. 第 24 轮」对照表）。
      正确动作顺序应是「先 grep 查号 → 再决定新增/引用/撤回」，而非「边踩边编号」。

## 24. 第 24 轮（2026-09-27 · 工作台 · Phase 4 DELIVER 收口 + 缺陷编号回查）

change `2026-09-27-idx-dedupe-guard-ast`（**追溯建档 · test-only**，CP-4 去重守卫由静态文本判据
换成 AST 结构审计）。D哥 22:12 在 Gate 3 确认框选择「全部按建议值放行」后进 DELIVER。

### 交付结果（全部实测）

| 步骤 | 结果 |
|---|---|
| Gate 3 | ✅ `gate approve … --gate 3 --confirmed-by dialog`（evidence 逐条写明 7 项待确认的处置） |
| structure delta / merge | ✅ delta 归档前生成、merge 归档后执行（顺序正确） |
| archive | ✅ `archive/2026-09-27-idx-dedupe-guard-ast` + Human View `specs/文章索引去重守卫/spec.md` |
| canon 三件套 | ⚠ `stdd archive` **未合并**（**P20 既有**）⇒ 手工 `cp -n` 三份 YAML + 补 `.canon-index.yaml` 三处 |
| canon verify | ✅ **2/2**（DC-HASH + DC-FIELD）；根副本与归档副本 sha256 一致 |
| index 结构 | ✅ `yaml.safe_load` 通过：proposals 4→5、agent 4→5、code 7→8 |
| 经验回传 | ❌ **HTTP 401**，68 条分 4 批全部 unauthorized（`Fstdd-experiences` 侧凭证问题） |
| 知识图谱 | ⚠ 社区图谱不可用 → 本地降级，本地无待合并经验 |

### 🔴 本轮最有价值的发现：新增编号前必须回查

本轮原本按「接续本地编号」的思路，准备把 5 条缺陷编为 P59~P63。
**实际回查 `TASK.md` 后，5 条里只有 1 条成立：**

| 本地候选 | 现象 | 回查结论 |
|---|---|---|
| 本地 P56 | `extract-proposal --format json` 把 `Capabilities` 并入 `what_changes`、四个字段全丢空 | ⚠ **= P12**（既有）。且第 13 轮已追加实测「**直供 canonical 也照丢**」，规避方式早已写明：「Gate 内容一律读 YAML 原文，不信 `extract-proposal` 摘要」 |
| 本地 P57 | `status` 显示「Spec 文件: 0 个」 | ⚠ **非缺陷**。第 13 轮已载明：该数字统计的是 `changes/<change>/specs/**/*.md`（Human View），**不是** canonical YAML ⇒ Gate 2 之前显示 0 是**正常** |
| 本地 P58 | `spec.md` AND 数量 (15) 超上限 (5) | ✅ **真新缺陷 → P58** |
| 本地 P59 | `canon generate --dry-run` 非真 dry-run | ⚠ **= P52**（既有），且在 `EXP-20260926-DRYRUN-1` 的「已知不 dry 命令」表**第一行** |
| 本地 P60 | `stdd archive` 不合并 canonical 三件套 | ⚠ **= P20**（既有，`EXP-20260919-ARCHIVE-2`） |

**结论：5 条候选 → 1 条新编号 + 2 条既有编号重复 + 1 条误报 + 1 条已记载的正常行为。**

🔴 **讽刺点**：本地记忆当时写「应重编号为 P59/P60/P61」，那是**没查 `TASK.md` 直接接本地号**的结果，
差一步就把 P59~P63 全编错了。**「先查后编」不是形式主义，它直接决定编号是否正确。**

同时：`TASK.md` 的 `updated` 字段停在 `2026-09-25`（内容已含 09-26 的第 24 轮）⇒ **本次已同步为 2026-09-27**。

### 固化的三条判据

1. **新增 P 编号前的三步**：① `grep -o "P[0-9]\+" TASK.md | sort -u -V | tail` 取真实最大号
   （不靠记忆估算）；② 按现象**关键词** grep（不是按自己的猜测编号）；③ 命中既有编号则
   **引用而非新建**，并在本轮记录里写明对照关系。
2. **「告警」不等于「缺陷」**：`validate` 的 `warnings` 与 `errors` 是两个桶，
   `warnings` 不影响退出码。判定时**先确认它进的是哪个桶**，再谈危害面。
3. 🔴 **同一文件内的一致性是最好的缺陷探测器**：P58 之所以成立，正是因为 `validate.py`
   里 TC-ID 检查已经为「全文计数误判」加过修正、AND 检查没做 —— **同类问题一处修了、另一处没修**，
   就是缺陷的最强证据，比任何抽象论证都硬。

### 经验条目

| 编号 | 条目 |
|---|---|
| P58 | `experiences/FSTDD003-EXP-20260927-ANDLIMIT-1.md` |

