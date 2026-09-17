# FSTDD 使用问题清单（2026-09-17 · reits-writer 工作区实战）

环境：Windows / Git Bash / Python 3.13.12（隔离 venv）
上游：`~/.workbuddy-ai/FSTDD/upstream`（本机 FSTDD 安装源）
场景：**嵌套工作区实战** —— 在既有项目根（`公众号历史文章/`）下新建子工作区 `reits-writer/`，
`fstdd init` 后立一个真实变更 `2026-09-17-corpus-paragraph-integrity`，走完 Phase 1（Gate 1）→ Phase 2。

> 与前两轮（`INSTALL_RUN_ISSUES_2026-09-16.md` / `_2026-09-17.md`）的区别：
> 前两轮测的是**安装/运行**，本轮测的是**真实业务变更跑流程**。
> 结论：安装链路已稳，**流程链路（Gate 生成物 ↔ CLI 解析器 ↔ 多工作区）有实质缺陷**。

---

## 一、结论速览

| 编号 | 问题 | 严重度 | 影响面 | 状态 |
|---|---|---|---|---|
| P12 | `extract-proposal` 对 Gate 生成物**系统性失效**，且 `what_changes` 被虚增污染 | **高** | 每个走完 Gate 1 的变更 | 已定位根因，未修 |
| P13 | 嵌套工作区下 change 落到**父工作区**；canonical 双轨回退**静默**写错位置 | 中 | 多工作区项目 | 已定位根因，本次靠"显式 cd + 绝对路径核对"规避 |
| P14 | `init` 自动拉社区经验**必然失败**，报错文案把 404 归因成"网络不可用" | 低 | 每次 `init` | 已定位根因，不影响功能 |

---

## 二、P12（高）：`extract-proposal` 与 Gate 生成物不兼容

### 现象

对 Gate 1 **自动生成**的 `proposal.md` 执行 `fstdd extract-proposal <change>`：

| 字段 | 输出 | YAML 真值 | 偏差 |
|---|---|---|---|
| `capabilities.new` | `[]` | 2 | 丢空 |
| `capabilities.modified` | `[]` | 2 | 丢空 |
| `what_changes` | **10 条** | **6 条** | **虚增 +4，且混入 `**` 残留** |
| `constraints` | `[]` | 7 | 丢空 |
| `risk_areas` | `[]` | 4 | 丢空 |
| `non_goals` | `[]` | 5 | 丢空 |
| `impact.*` | 全空 | 有值 | 丢空 |

**先排除了自己的输入**：换一个更早、结构更简单的 change 跑同一命令，症状完全一致
（`capabilities: 0 / constraints: 0 / risk_areas: 0`，且 capability 描述同样混进 `what_changes`）
→ **不是 YAML 形状问题，是 CLI 自身缺陷**。

### 根因：三方约定不一致，无单一真源

| 组件 | 位置 | 对 `proposal.md` 的预期 |
|---|---|---|
| **生成器** | `fstdd/cli/commands/canon.py::_generate_one()`（约 310–357 行） | 只输出 5 个 section：`## Why` / `## What Changes` / `### New Capabilities` / `### Modified Capabilities` / `## Success Criteria` |
| **模板** | `.fstdd/templates/proposal.md` | 定义 **14 个** section，含 `## Capabilities` 父标题、`## Impact`、`## Constraints`、`## Stakeholders`、`## Risk Areas`、`## NonGoals` … |
| **解析器** | `fstdd/cli/commands/extract_proposal.py` | 按**模板**形状解析：`_parse_capabilities()` 要求 `## Capabilities`；`_parse_section()` 要求精确 `^## <heading>$` |

生成器**从不输出 `## Capabilities` 父标题** → 解析器永远找不到。

### 为什么 `what_changes` 会"变多"（本缺陷最危险处）

`### New Capabilities` / `### Modified Capabilities` 是 **H3**，**不终止 H2 区间**。
缺了 `## Capabilities` 父标题，这两个 H3 段落就落进了 `## What Changes` 的区间内，
被 `_parse_section(content, "What Changes")` 的 `findall(r"^[ \t]*(?:-|\*)\s+(.+)")` 一并吞掉：

```
## What Changes
- 新建 flatbody.py …              ← 真·what_changes（6 条）
- 修改 index.py …
### New Capabilities               ← 不终止上面的 H2 区间
- **压平正文检测与段落还原**：…    ← 被吞成第 7 条
- **索引期整页 HTML 剔除**：…
### Modified Capabilities
- **素材包可信度标注**：…
- **素材包本地路径**：…             ← 第 10 条
## Success Criteria                ← 到这里才终止
```

`**` 加粗标记也没被剥离 → JSON 里表现为"多了几条带 `**` 的条目"。
**数量变多，不看内容根本发现不了** —— 这是本次最值得回传的一点。

### 次生风险：静默失败

`_parse_section()` 找不到标题时 `return []`，**无 warning、无非零退出**。
下游 Gate 校验 / `ci` 会把"没解析到"当成"确实没有"，静默通过。

### 复现

```bash
cd <project_root>          # 必须是有 .fstdd/ 的工作区根
PY=C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe
CLI=$(cygpath -m ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd)   # ← 必须过 cygpath，见第三节
"$PY" "$CLI" extract-proposal <change-id>
```

### 建议修法（按性价比）

1. **生成器补 `## Capabilities` 父标题**（约 1 行）—— 一行同时消掉"丢空"与"吞并"两个症状；
2. 生成器补齐 `## Impact` / `## Constraints` / `## Stakeholders` / `## Risk Areas` / `## NonGoals`
   —— **数据在 YAML 里全都有**，只是没被渲染；
3. `_parse_section()` 找不到标题时告警；`cmd_extract_proposal()` 收尾做一次
   "模板 section 完整性"自检，缺失即非零退出；
4. 抽一份**共享 section 清单常量**，生成器 / 模板 / 解析器三处引用同一真源。

### 本次规避

Canonical-First 下 `canonical/proposals/<change>.yaml` 才是唯一真源，
`proposal.md` 只是 Human View → **人工核对 Gate 内容时直接读 YAML，不依赖 CLI 摘要**。

---

## 三、P13（中）：嵌套工作区下 change 归属错位

### 现象

项目根 `A/` 有 `.fstdd/`，本轮又在 `A/reits-writer/` 下 `fstdd init` 出第二个工作区。
一段时间后检查：

- `A/reits-writer/.fstdd/changes/` → **空**
- 变更 `2026-09-17-corpus-paragraph-integrity` 整个落在 `A/.fstdd/changes/`

`fstdd status` 在两个工作区下看到的"当前变更"不一致。

### 根因

1. **路径全部基于 `Path.cwd()`，不向上发现 `.fstdd/`**
   - `finder.py::find_change_dir(name, project_root=None)` → `project_root = Path.cwd()`
   - `extract_proposal.py:110` → `project_root = Path.cwd()`
   - `canon.py::_get_canon_dir()` → `project_root / ".fstdd" / ...`
   - **没有任何一处校验 change 属于哪个工作区**，也没有 `--root` 之类显式锚定参数。

2. **canonical 的"change 级 → 项目级"双轨回退不提示**
   `canon.py::_generate_one()`（约 284–296 行）：change 级 canonical 不存在时
   **静默回退到项目级 `.fstdd/canonical/`** —— 在嵌套工作区里等于"找不到就写到另一个工作区"。

3. **"当前变更"取全局最近修改**
   `canon.py::_find_current_change()` 与 `finder.py`（`name=None` 分支）
   都取 `sorted(..., key=mtime, reverse=True)[0]` → **跨工作区会串**。

### 附带：CLI 入口在 Git Bash 下必须过 `cygpath`

```bash
"$PY" ~/.workbuddy-ai/FSTDD/upstream/bin/fstdd ...
# → can't open file 'D:\c\Users\...\fstdd'
```

Git Bash 把 `~` 展开成 `/c/Users/...`，Windows Python 解析成 `\c\Users\...`。
**必须** `$(cygpath -m ~/...)`。与既有 P3「Git Bash 路径未转 Windows 形式」同源，
但既有记录只覆盖 `install.sh`，**CLI 入口同样会踩**。

### 建议修法

1. cwd **向上查找最近 `.fstdd/`** 作为 `project_root`；
2. 增加 `fstdd --root <dir>` 或读环境变量 `FSTDD_ROOT`；
3. 双轨回退时**打印警告**；
4. `new` / `gate` 打印 change 的**绝对路径**；
5. 可选：`config.d/project.yaml` 登记 `workspace_id`，跨工作区操作直接拒绝。

### 本次规避

- 执行 `fstdd` 命令前**显式 `cd` 到目标工作区根**，不靠 cwd 继承；
- 产出后用**绝对路径核对落点**（`ls -la "<ws>/.fstdd/changes/"`）；
- 发现落到父工作区时**不擅自搬迁** —— 会破坏 Gate 已确认的 traceability，
  改为记录在案 + 向上游反馈。

---

## 四、P14（低）：`init` 自动拉社区经验必然失败，报错归因错误

### 现象

`fstdd init` 结束固定输出：

```
  [STDD] 社区经验拉取失败（网络不可用），可稍后手动执行 stdd experience pull
```

**网络完全正常的机器上同样出现**（GitHub 可直连）。

### 根因（实测状态码）

```
github.com/leonai42/stdd-experiences                              200   ← 仓库存在
github.com/leonai42/stdd-experiences/releases/latest/download     404   ← 无任何 release
.../experience-python-latest.tar.gz                               404
gitee.com/leonai42/stdd-experiences/releases/download/v1.0.0/...  404
```

`experience.py::_download_with_fallback()`（552–572 行）拼接规则：

| type | 拼接 |
|---|---|
| `github` | `{url}/experience-{pack}-latest.tar.gz` |
| `gitee` | `{url}/{version}/experience-{pack}-{version}.tar.gz` |

仓库存在但**没发布 release** → `releases/latest/download` 必然 404。

### 三个附带缺陷

1. **报错归因错误**：`init.py::_post_init_experiences()`（203–214 行）用 `except Exception` 一把抓，
   **HTTP 404（配置错）与 `ConnectionError`（真网络问题）压成同一句话**，
   把人引去查网络/代理，而真正要改的是 registry 配置。
2. **提示命令名仍是旧 `stdd`**（`stdd experience pull`），照抄执行会 `command not found`
   —— 重命名改造的遗漏点。
3. **默认仓库 ≠ 实际使用的经验库**：默认指 `leonai42/stdd-experiences`（上游 STDD 仓库），
   本项目实际回传目标是 `2749817087qq/Fstdd-experiences`（见 `TASK.md` 的 `experience_repo`）。

### 影响与判定

- **社区包拉不到 ≠ 初始化失败**：`_post_init_experiences` 异常被吞，`init` 仍 rc=0；
  `_self_check` 只提示 `经验库: ⚠️ 空（手动拉取: stdd experience pull）`。可继续。
- 但每次 `init` 都留一条误导信息，新人会白花时间。

### 建议修法

1. `_download_with_fallback()` **区分状态码**：404 → "registry 配置错误（release 不存在）"；
   `ConnectionError/Timeout` → "网络不可用"；
2. `_post_init_experiences()` 不要静默 `except Exception`，至少带出状态码或落日志；
3. 修掉提示里的旧命令名（全仓再扫一遍同类遗漏）；
4. 默认 registry 指向**真实发布 release** 的仓库；或**默认留空**由使用者显式配置
   —— 宁可不拉，也别给一条必然失败的默认值。

---

## 五、本轮**确认正常**的部分（避免误判）

| 项 | 结果 |
|---|---|
| `fstdd init`（在子工作区） | ✅ 骨架完整：`config.d` 9 个 yaml + `templates` 24 个 + `platforms` 3 平台 × 6 skill + `standards` + `skills` + `.claude/settings.local.json` |
| 三道门 `required: true` | ✅ `config.d/gates.yaml` 生效 |
| Canonical-First（AI 只写 `canonical/**/*.yaml`） | ✅ Gate 1 通过后自动生成 `proposal.md`，带 `source_hash` |
| `fstdd gate approve --gate 1` | ✅ 写入 `phases.understand.confirmed_*`，含 `confirmed_by` / `confirmed_evidence` |
| 复杂度评分 | ✅ 文件数 + 行数 + Capability + 风险 + 数据/API + 安全 → `complexity_score: 9` → `mode: thorough` |
| `fstdd canon verify`（DC-HASH） | ✅ `source_hash` 校验与"缺 hash 自动重生成"回填逻辑存在 |
| `fstdd validate` / `status` / `new` | ✅ 通过 |

**结论**：FSTDD 的**安装链路与骨架生成已稳**，问题集中在
**Gate 生成物 ↔ CLI 解析器的一致性**（P12）与**多工作区锚定**（P13）。

---

## 六、回传说明

本文件与三条经验条目一并回传至经验库：

| 条目 | 严重度 |
|---|---|
| `EXP-20260917-EXTRACT-1`（P12） | high |
| `EXP-20260917-MULTIWS-1`（P13） | medium |
| `EXP-20260917-REGISTRY-1`（P14） | low |

回传通道：无 GitHub 凭证时降级 POST 到自建端点（见 `tools/share_experience.py`）。
注意既有 P10 口径坑：`publish` 提交的是**导出目录全量**，索引只反映源目录条数，两者会不一致且重复累加服务端计数。
