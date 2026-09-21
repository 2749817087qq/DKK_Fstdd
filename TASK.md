---
task_id: FSTDD003
schema: fstdd-distributed-task/v0.1
title: FSTDD 安装/运行工程测试与经验回传
status: archived          # pending | running | blocked | done | archived
created: 2026-09-12
updated: 2026-09-21
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


