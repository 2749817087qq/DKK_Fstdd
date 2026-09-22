---
task_id: FSTDD003
schema: fstdd-distributed-task/v0.1
title: FSTDD 安装/运行工程测试与经验回传
status: archived          # pending | running | blocked | done | archived
created: 2026-09-12
updated: 2026-09-23
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
