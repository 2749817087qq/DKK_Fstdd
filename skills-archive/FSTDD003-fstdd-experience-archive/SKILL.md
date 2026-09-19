---
name: fstdd-experience-archive
description: "把 FSTDD 使用过程中发现的问题 / 新建或修改的 skill 归档到 D:\\FSTDD003（分布式任务根，task_id=FSTDD003）。当用户说「FSTDD 的问题记得保存」「归档到 FSTDD003」「经验回传」「FSTDD 报错要记录」，或你在用 fstdd 跑 UNDERSTAND/SPEC/BUILD/DELIVER 时踩到坑（CLI 报错、生成物对不上、change 落错目录、Gate 状态异常）时使用。含 FSTDD 本机定位、EXP 条目格式、目录命名、索引与 TASK.md 更新规则，以及 P1–P14 已知缺陷速查。"
agent_created: true
version: 1.0.0
license: unknown
---

# FSTDD 经验归档（→ `D:\FSTDD003`）

## 归档目标

```
D:\FSTDD003\                     ← 分布式任务根（task_id = FSTDD003，目录名即编号）
├─ TASK.md                       分布式任务卡（**幂等：只增不改历史结论**）
├─ MANIFEST.md                   迁移清单
├─ docs\                         问题报告（长文，可含复现步骤与状态码）
├─ experiences\                  经验条目（**已被 .gitignore，靠回传通道留存**）
│  ├─ FSTDD003-EXP-<ID>.md       归档副本（带 FSTDD003- 前缀）
│  └─ FSTDD003-README.md         索引（⚠ 工具导出产物，会被 --export 覆盖）
├─ skills-archive\               skill 归档（带 FSTDD003- 前缀）
├─ artifacts\                    identity / memory / hardening 等
└─ tools\                        share_experience.py 等
```

⚠ **编号规则**：`FSTDD` + **三位序号**，全局唯一，跨节点不重复。新任务开 `D:\FSTDD<NNN>`。
⚠ **一个节点写一份**：禁止两个执行实例同时写同一任务目录。

## 什么时候归档

| 触发 | 落点 |
|---|---|
| FSTDD **CLI 报错 / 输出不符合预期** | `experiences/` 单条 + `docs/` 报告（问题多时） |
| **绕过**了 FSTDD 的某个坑（有可复用结论） | `experiences/` 单条 |
| 新建 / 修改 / 安装了 **skill** | `skills-archive/FSTDD003-<skill-name>/` |
| 本轮有**成体系**的问题群（≥3 条） | 额外写一份 `docs/` 报告 + 在 `experiences/FSTDD003-README.md` 索引追加 |

---

## 一、EXP 条目格式（`experiences/FSTDD003-EXP-<ID>.md`）

Frontmatter 与正文结构照抄既有条目（如 `FSTDD003-EXP-20260917-EXTRACT-1.md`）：

```yaml
---
experience_id: EXP-20260917-EXTRACT-1      # 命名：EXP-<日期>-<主题>-<序号>
category: tooling
severity: high                             # high | medium | low
occurrences: 2                             # 复现次数
title: 一句话说清"现象 + 后果"
exported_at: 2026-09-17
sanitized: true                            # 已脱敏
---
```

正文固定五段：

```markdown
## 现象        ← 贴真实输出（JSON/日志/状态码），别写"好像不对"
## 根因        ← 定位到**源码行**；贴关键代码片段
## 处理（本次规避）  ← 怎么绕过去的
## 建议修法（按性价比排序）  ← 上游该改哪一行
## 复测建议    ← 修复后跑什么断言能确认修好
```

命名：`EXP-<YYYYMMDD>-<主题>-<序号>`，主题用英文短词（`INSTALL` / `RUN` / `DOCS` / `EXTRACT` / `MULTIWS` …）。

## 二、目录命名

| 类型 | 规则 | 例 |
|---|---|---|
| 经验条目 | `FSTDD003-EXP-<ID>.md` | `FSTDD003-EXP-20260917-EXTRACT-1.md` |
| 问题报告 | `docs/<主题>_<日期>.md` | `docs/RUN_ISSUES_2026-09-17_reits-writer.md` |
| skill 归档 | `FSTDD003-<skill-name>/` | `FSTDD003-fbs-bookwriter/` |

## 三、更新索引与 TASK.md

1. `experiences/FSTDD003-README.md` 表格**追加一行** `| EXP-xxx | 标题 | 文件名 |`。
   ⚠ 该文件是 `tools/share_experience.py --export` 的**导出产物**，下次导出会被覆盖 →
   追加时在文件头注明"手工追加 N 条，来源 XXX"。
2. `TASK.md`：
   - 在 **遗留项** checklist 追加 `- [ ] P<NN> 待修：…`
   - 新增/追加一个 `## N. 第N轮（日期 · 场景）` 章节，**只增不改**已有章节的历史结论
   - 同步 `updated` 字段

---

## 🔴 铁律（本 skill 自己踩过的坑）

1. **先复现，再写结论。** 不写没验证过的推断。
   判断"是不是我的输入有问题"的最快办法：**拿另一个已知的输入跑同一命令**，
   症状一致 → 是工具的锅；症状不一致 → 查自己的输入。
2. **把"怎么排除的"写进经验。** 排除过程比结论更有价值 —— 下一个人（和你自己）会照着重做。
3. **脱敏**：`sanitize_paths / sanitize_ips / sanitize_domains` 均为 `true`。
   用 `~` 代替 home，用 `<project_root>` 代替真实项目路径。
4. **区分"丢空"与"虚增"**：静默失败里 **"变多"比"变空"更难察觉**，
   写报告时一定要显式对比"输出 vs 真值"，别只说"结果不对"。
5. **记录"确认正常"的部分**。避免读者把整个工具判死。
6. **🔴 成功标准写错时：保留原文，另加脚注，不改原文**（D哥 2026-09-18 裁定）。
   原文是「当时的预期」这一历史事实 —— 把标准改成实测值 = 事后美化，会让后人
   看不出当初判断错在哪。正确做法：
   ```yaml
   success_criteria:
     - "... > 10,000 篇"          # ← 一字不改
   success_criteria_notes:
     - id: NOTE-1
       applies_to: "success_criteria[5]"
       verdict: "标准有误，不可达；功能正常"
       measured: "7,203 篇"
       root_cause: "..."      # 分母错配
       correct_acceptance: "..."  # 与判据口径一致的比率
       current_enforcement: "..." # 真正生效的断言在哪
   ```
   实际验收改用新口径的断言（做进 smoke test），原标准不再作为失败判据。
7. **写带数量的成功标准前，先答三问**：
   ① 分母是什么（写成 `分子/分母` 完整形式，别只留一个百分数）
   ② 分母与判据会不会互相夹逼（判据若有长度/大小门槛，门槛外的部分天然不可能命中）
   ③ 外推样本有没有偏（索引常按某维度聚集，取前 N 条会失真 ——
      实测前 2,000 条外推 4,700，真实值 7,203，偏低 35%）
   → 优先写**相对值**（「占 X 的比例 ≥ N%」），少写绝对值。
   完整案例见 `D:\FSTDD003\experiences\FSTDD003-EXP-20260918-CRIT-1.md`。

---

## 四、本机 FSTDD 定位（避免每次重找）

| 项 | 位置 |
|---|---|
| 安装源 / upstream | `~/.workbuddy-ai/FSTDD/upstream/` |
| **CLI 入口** | `~/.workbuddy-ai/FSTDD/upstream/bin/fstdd`（Python 脚本，委托到 `fstdd/cli`） |
| skill 落位 | `~/.workbuddy-ai/skills/fstdd*` + `fstdd-fin` |
| 社区经验 registry 配置 | `<ws>/.fstdd/config.d/experience.yaml` |
| 回传工具 | `D:\FSTDD003\tools\share_experience.py` |

### Git Bash 下调用 CLI（必须过 `cygpath`）

```bash
PY="C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe"
CLI=$(cygpath -m ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd)   # ← 不加这步必挂
cd <目标工作区根>                                             # ← 先 cd，见 P13
"$PY" "$CLI" <subcommand>
```

不加 `cygpath` → `~` 展开成 `/c/Users/...` → Windows Python 解析成 `\c\Users\...`
→ `can't open file`。

### 回传

```bash
python tools/share_experience.py --export --publish   # 无 GitHub 凭证自动降级到自建端点
python tools/share_experience.py --export             # 只导出不回传
```

⚠ **P10 口径坑**：`publish` 提交的是**导出目录全量**，而索引只反映**源目录**条数
（源目录 = `.fstdd/experiences/`），两者不一致且会重复累加服务端计数。
且导出目录**不清理陈旧条目**（源目录删了、导出目录还在）→ 口径持续漂移。
已提交过的不要反复跑，或等服务端去重。

---

## 五、已知缺陷速查（P1–P14，别重复踩）

| 编号 | 问题 | 严重度 |
|---|---|---|
| P1–P4 | `install.sh` 4 项：参数解析失效 / 未 export `FSTDD_OUT` / Git Bash 路径未转 Windows / echo 目录不一致 | 中 |
| P5 | token 路径 | 待修 |
| P6 | Guard 平台误判 | 待修 |
| P7 | verify 漏校验 | 待修 |
| P8 | change 名不支持中文 | 待修 |
| P9 | 子命令缺参提示 | 待修 |
| P10 | 回传口径不一致（提交全量 vs 索引源目录），重复累加计数 | 中 |
| P11 | `experiences/` 被 gitignore，导出产物不入库 | 低 |
| **P12** | **`extract-proposal` 对 Gate 生成物系统性失效 + `what_changes` 虚增** | **高** |
| **P13** | **嵌套工作区下 change 落到父工作区 + canonical 双轨回退静默写错位置** | 中 |
| **P14** | **`init` 自动拉社区经验必失败 + 报错把 404 归因成"网络不可用"** | 低 |
| **P15** | **`fstdd` CLI 经裸 `python3` 运行报 `ModuleNotFoundError: No module named 'yaml'`**；须用隔离 venv python + Git Bash 下 `$(cygpath -m ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd)` 转换路径，否则 `~` 展开成 `/c/Users` 被 Windows Python 解析失败 | 中 |
| **P16** | **SSH 私钥位置**：节点服务器私钥恒在 **D 盘根 `/d/id_ed25519`**（ed25519），**不是** `$USERPROFILE/.ssh/id_ed25519`；scp/ssh 用 `-i /d/id_ed25519 -o StrictHostKeyChecking=no`，Host `ubuntu@43.134.236.80`。误用 `.ssh/` 那把会 `Permission denied (publickey)`（假阻塞） | 高 |
| **P17** | **服务端不去重**：同 `experience_id` 重复 POST 会累加 `received` 计数。本地须用 `.fstdd/_fstdd003_share_log.json` 记录已提交 ID（`tools/fstdd003_daily_share.py` 据此增量发），否则每日重发污染计数 | 中 |
| **P18** | **回执闭环**：K 下发的 `FSTDD00X收-<主题>.md` 任务，完成后写 `FSTDD00X复-<主题>.md` 经 scp 回 `ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD00X/`（仅本节点目录，禁碰他人文件夹）。回执四要素：标题/收到时间/执行结果/未完成项（见 00-NOTICE.md 第四节） | 中 |
| **P19** | **`archive` 合并 master specs 时 SC 编号跨变更静默重复**：冲突检测只比 `### Requirement:` 标题，**漏检 SC-ID 撞号** → `specs/<cap>/spec.md` 里出现两组 `SC-001..N`，归档输出仍显示「Specs 已合并到 specs/」无警告。危害：SC-ID 失去全局唯一性，而 test-plan / `agent_spec.yaml` 正是靠它做映射 | 中 |

### P19 速记（归档后必查）

- **触发条件**：本次归档的 capability **之前已存在于** `.fstdd/specs/` 下
  （首次归档走 `shutil.copy2`，不会撞）。**同一 capability 被 ≥2 个变更改过 = 必然撞号**。
- **源码**：`fstdd/cli/commands/archive.py:57-78` —— 合并是**追加**（内容不丢，这点对），
  但 `existing_reqs & new_reqs` 只比 Requirement 标题。
- **归档后必跑三查**：
  ```bash
  grep -o "^#### Scenario: SC-[0-9]*" .fstdd/specs/*/spec.md | sort | uniq -c | awk '$1>1'   # 撞号
  grep -c "^> Change:" .fstdd/specs/*/spec.md                                                 # 多组 header
  grep -c "^#### Scenario:" .fstdd/specs/<cap>/spec.md                                        # 应等于各变更之和
  ```
- **处理原则**：**不擅自重编 master spec 的 SC-ID**（会破坏 Gate 已确认的 traceability）。
  内容确认没丢即可，**跨变更引用一律带变更名前缀**（`<change>/SC-002`），不裸用 `SC-002`。
- **真源永远是归档原件**：`archive/<change>/canonical/specs/code/*.yaml` 逐变更独立编号。
- 详见 `experiences/FSTDD003-EXP-20260919-ARCHIVE-1.md`。

### P15 速记（Windows 本机跑 fstdd CLI 必踩）
- 隔离 Python 二进制 `C:/Users/Administrator/.workbuddy-ai/binaries/python/versions/3.13.12/python.exe` 缺 `yaml`；`pyyaml` 装在 venv `C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`。
- 正确姿势：
  ```bash
  VENV_PY="C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe"
  CLI=$(cygpath -m ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd)
  "$VENV_PY" "$CLI" status
  ```
- **绝不**裸调 `python3 bin/fstdd` 或把 `~` 直接拼进 Windows 路径。

### P16 速记（SSH 密钥，别再问第二遍）
- 密钥文件：`D:/id_ed25519`（Git Bash 写作 `/d/id_ed25519`）。**不是** `C:/Users/Administrator/.ssh/`。
- 连通验证：`ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 "echo OK"`。
- 取 notices：`scp -i /d/id_ed25519 -o StrictHostKeyChecking=no "ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD00X/*" D:/FSTDD003/.fstdd/_notices/FSTDD00X/`。
- 回执回写：`scp -i /d/id_ed25519 -o StrictHostKeyChecking=no D:/FSTDD003/.fstdd/_notices/FSTDD00X/FSTDD00X复-*.md ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD00X/`。

### P17 速记（增量去重）
- 端点 `http://<IP>:8787/api/share-experience` 无凭证；`GET /health` 返回 `received` 计数。
- 试运行时曾把 34 条全量重发 → 计数虚高。固化：helper `tools/fstdd003_daily_share.py` 读 `experiences/FSTDD003-EXP-*.md`，与 `.fstdd/_fstdd003_share_log.json` 的 `submitted` 比对，只发新增；每次成功 POST 后把 ID 写入该 log。

### P18 速记（回执闭环）
- 服务器目录纪律（00-DISCIPLINE）：只读写自己 `FSTDD00X/` 文件夹，根文件只读，K 的 memory 文件夹禁入。
- 命名：经验 `FSTDD00X-EXP-<日期>-<编号>.md` 仅 ASCII；中文标题进 frontmatter `title`，否则被编码层吃成 `____-______.md` 无法索引。
- 试运行数据（EXP-20260915/16/17 系列）不再发；原始工具 `share_experience.py` 的 `collect_local()` 读 `.fstdd/experiences/EXP-*.md` 是重发源头，已把 26 个旧 `EXP-*.md` 迁至 `.fstdd/_legacy_trial/` 归档。

### P12 速记（最值得记住的一条）

- 生成器 `canon.py::_generate_one()` **只渲染 5 个 section**，模板定义了 **14 个**，
  解析器 `extract_proposal.py` 按**模板**解析 → `capabilities / constraints / risk_areas / non_goals / impact` **全部静默丢空**。
- **更危险**：生成器不写 `## Capabilities` 父标题 → `### New/Modified Capabilities`（H3）
  **不终止** `## What Changes`（H2）区间 → capability bullet 被 `_parse_section` 吞并
  → **`what_changes` 虚增**（实测 6 → 10），且残留 `**`。
- `_parse_section()` 找不到标题时 `return []`，**无 warning、无非零退出**。
- **规避**：Canonical-First 下 `canonical/proposals/<change>.yaml` 才是唯一真源，
  **人工核对 Gate 内容直接读 YAML，别信 `extract-proposal` 的摘要**。
- **最小修法**：生成器补一行 `## Capabilities` 父标题。

### P13 速记

- 路径全基于 `Path.cwd()`，**不向上发现 `.fstdd/`**，也不校验 change 归属。
- `canon.py::_generate_one()` 的 change 级 → 项目级 canonical 回退**不打印警告**。
- **规避**：执行前**显式 `cd` 到目标工作区根**；产出后**用绝对路径核对落点**；
  发现落错位置**不擅自搬迁**（会破坏 Gate 已确认的 traceability），记录在案 + 反馈。

### P14 速记

- registry 指向的仓库**存在但没有 release** → `releases/latest/download` 必然 404。
- `init.py::_post_init_experiences()` 用 `except Exception` 一把抓 →
  **404（配置错）与 `ConnectionError`（真网络问题）压成同一句"网络不可用"**。
- 提示里命令名仍是旧 `stdd`（重命名遗漏）。
- **"社区经验拉不到 ≠ 初始化失败"**：异常被吞，`init` 仍 rc=0，可继续。

---

## 六、执行清单（照着做）

1. **复现**：拿真实 change 跑命令，贴输出；换另一个已知输入交叉验证。
2. **定位**：grep 上游源码，找到具体文件 + 行号。
3. **写 `experiences/FSTDD003-EXP-<ID>.md`**（五段式）。
4. 问题 ≥3 条 → 追加写 `docs/<主题>_<日期>.md`。
5. **归档 skill**：`cp -r ~/.workbuddy-ai/skills/<s> /d/FSTDD003/skills-archive/FSTDD003-<s>`
   （已存在就 skip，别覆盖）。
6. **更新 `experiences/FSTDD003-README.md` 索引** + **`TASK.md`**（只增不改）。
7. **回传**（可选）：`python tools/share_experience.py --export --publish`，注意 P10 口径坑。
8. **git commit**（显式路径，别 `git add -A`）：`docs/`、`skills-archive/`、新增文件。
   ⚠ `experiences/` 被 gitignore，不会进历史 —— 留存靠回传通道。
