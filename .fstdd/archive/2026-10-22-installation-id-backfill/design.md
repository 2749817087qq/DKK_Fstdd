# installation_id 回填：给已初始化项目补齐身份，且不破坏 version.yaml 的可读文本形态 - 技术设计

## Context

**当前系统状态**

- `installation_id` 的产生路径只有一条：`fstdd init` → `cmd_init` → `_ensure_installation_id()`
  （`upstream/fstdd/cli/commands/init.py`）。它用 `yaml.dump(data, ...)` **整体回写** `.fstdd/version.yaml`。
- 读取侧是 `utils.read_installation_id()`，形状校验用 `utils.INSTALLATION_ID_RE`
  （`^[A-Z0-9]{2,8}-[0-9A-F]{8}$`）。`experience._next_id()` 有值则产
  `{IID}-EXP-{year}-{NNNN}`，无值回落 `EXP-{year}-{NNNN}`。
- **v3.1.1 之前初始化的项目全都没有该字段** —— 包括本框架仓 stdd-repo 自己。

**实测约束（本 change 的前提事实，详见 proposal.evidence）**

| 事实 | 数值 |
|---|---|
| 本仓 `version.yaml` | 336 行 / 27280 字节 / **LF 行尾** / 无 BOM |
| 注释头 | 4 行（版本三轴 E/K/R 口径说明） |
| 块标量 | `changelog: \|`（~300 行发行说明）、`notes: \|` |
| `yaml.dump` 回写后 | 235 行（−101），注释头全丢，`changelog` 退化为双引号转义串 |
| 语义是否等价 | **等价**（`safe_load` 后键值逐键相同）—— 破坏的是文本形态 |
| `cmd_init` 在已初始化项目上的额外副作用 | `guard init` / `experience pull --pack python` / `project.yaml` 补 `isolation` / 写全局 registry |
| 经验库 | 109 个 `.md`，4 种命名族，`last_id = 40` |
| 下游枚举口径 | 已统一为 `glob("*.md")`，`INDEX_ITEM_RE` 允许多段前缀，无遗留 `EXP-\d` 假设 |

**技术栈**：Python 3.10+、PyYAML。**不引入新依赖**（排除 `ruamel.yaml`）。

## Decisions

### 1. 回填入口 = 新增独立子命令 `fstdd installation-id`

**方案**：新增顶层子命令 `fstdd installation-id [--prefix X] [--dry-run]`，
实现为 `init.py` 内的 `cmd_installation_id(args)`（复用同文件的
`_get_prefix()` / `_generate_installation_id()` 与 `utils.INSTALLATION_ID_RE`），
在 `cli/__init__.py` 注册。**只**确保 `installation_id`，不跑任何 `_post_init_*`、不写全局 registry。

**为什么**：
- 回填是「一次性、可重复、零副作用」的动作，而 `init` 是「装骨架 + 装 guard + 拉经验」的多效动作。
  把两者混在一条命令里，等于让用户为了一个字段承担四类副作用。
- 所有 v3.1.1 之前的项目都需要回填。做成 CLI 子命令后，每个项目一条命令即可，
  且随发行版分发；写成 `tools/` 脚本只有本仓能用。
- 语义正交：`init` = 初始化，`upgrade` = 升级静态资源，`installation-id` = 确保身份。

**备选方案及排除原因**：
- **给 `init` 加 `--installation-id-only` 开关**：不新增模块，但「init 只做一部分」语义含糊，
  且与既有 `--force` / `--dry-run` / `--prefix` 组合出歧义（`--force --installation-id-only` 该覆盖什么？）。
- **`tools/backfill_installation_id.py` 一次性脚本**：只救本仓，其他历史项目仍无路径，
  与 proposal.motivation 冲突。
- **让 `upgrade` 顺带补**：`upgrade` 的语义是「拉取并覆盖 `.fstdd/` 静态资源」，
  顺手改身份会让用户意外；且 `init` 已 import `upgrade._register_project`，反向 import 易成环。

### 2. 写入用「定向文本插入」，不用 `yaml.dump` 整体回写

**方案**：在 `cli/utils.py` 新增 `set_top_level_scalar(path, key, value) -> bool`：
按文本处理，定位插入/替换位置后只改动目标行，**其余字节原样保留**。
`init._ensure_installation_id()` 与 `upgrade._write_version_yaml()` 都改为调用它。

**为什么**：`yaml.dump` 会丢注释、把块标量退化成转义串（实测 −101 行）。
version.yaml 在本仓承载的是**人读的发行说明**，不是纯机器配置；
`git blame` 连续性和 diff 可审性都是实际价值。

**备选方案及排除原因**：
- **`ruamel.yaml` round-trip 模式**：能保注释，但引入新依赖，违反 proposal 约束；
  且 round-trip 对块标量的重排仍可能产生噪声。
- **继续 `yaml.dump`，接受注释丢失**：对「只有 3~4 个键、无注释」的普通项目无害，
  但对本仓是实质性破坏，且回填会产出 100+ 行噪声 diff 掩盖真实改动。
- **只在文件末尾追加一行**：实现最简单，但**不安全** —— 若文件以块标量（如 `notes: |`）结尾，
  追加的行会被吸进该块，变成 notes 的内容，且 `yaml.safe_load` 依然「解析成功」，静默错。

### 3. 插入点 = 首个顶层键行之前

**方案**：用 `^[A-Za-z_][\w]*:` 找**首个**顶层键行（跳过注释与空行），在其**之前**插入
`installation_id: <值>`。若文件已有该键则**原位替换**该行（不新增行）。

**为什么**：
- 注释头仍在文件最上方（符合人读习惯，也不破坏「注释属于紧随其后的键」的直觉）。
- 避开了「末尾是块标量」的陷阱（见决策 2 的排除项）。
- 顶层键在 YAML 中无序，插在最前不影响语义。

**备选方案及排除原因**：按字母序插入（`fstdd_version` 之前/之后精确比对）—— 需要理解
既有键序，且一旦文件里有 `<<` 合并键或文档分隔符 `---` 就会错位；「首个顶层键之前」无需理解语义。

### 4. 行尾与 BOM 按原文件保持（bytes 级读写）

**方案**：用 `path.read_bytes()` 解码（先判 `utf-8-sig` BOM），检测文件的主导行尾
（`\r\n` 出现则用 CRLF，否则 LF），插入行使用同一行尾；写回用 `write_bytes()`。

**为什么**：`Path.read_text()` 默认走 universal newlines，会把 `\r\n` 归一成 `\n`；
写回即**全文行尾变更**——对 CRLF 的项目会产生「336 行全改」的 diff，
把一个 +1 行的改动变成不可审的噪声。本仓当前是 LF，但工具是分发给所有项目的。

### 5. 写入前 4 条自检，任一失败则不落盘

**方案**：写入前对新文本做静态校验，全部通过才 `write_bytes`：
1. `yaml.safe_load(new_text)` 可解析且为 `dict`；
2. 除目标键外，所有键值与本 change 前逐键相等（`==` 深比较）；
3. 原文件所有以 `#` 开头的注释行**仍全部存在**（顺序不变）；
4. 原文件中形如 `^[A-Za-z_]\w*: \|$` 的块标量标记**仍全部存在**。

**为什么**：这是「文本编辑」而不是「结构化写」的代价 —— 必须用断言把「我以为的等价」
变成「可验证的等价」。EXP-2026-0038（配置写入口丢字段）与 EXP-2026-0040（写读口径不一致）
都是「写入口自以为正确」导致的静默故障。

### 6. 回填命令不写全局 registry，且幂等

**方案**：`cmd_installation_id` **不**调用 `_register_project`；已有合法值时不改文件
（连 mtime 都不动），以 0 退出并打印现值。

**为什么**：`~/.fstdd/projects.yaml` 已被测试污染到 7237 条（FU-008），
一个「确保一个字段」的命令没有任何理由再去写它。

## Architecture

```
调用链（回填）
  fstdd installation-id [--prefix X] [--dry-run]
    └─ cli/__init__.py  →  cmd_installation_id(args)
         ├─ 无 .fstdd/version.yaml → stderr 报错 + exit 2
         ├─ utils.read_installation_id(root, warn=True)
         │    ├─ 有合法值 → 打印现值，return（不改文件）
         │    └─ 无/坏值 → init._generate_installation_id(init._get_prefix(args, root))
         └─ utils.set_top_level_scalar(version.yaml, "installation_id", iid)
              ├─ 4 条自检（解析 / 键值等价 / 注释行 / 块标量标记）
              ├─ 失败 → stderr 报错，不落盘，exit 3
              └─ 成功 → write_bytes，打印写入值

写入路径（共用）
  init._ensure_installation_id()  ─┐
                                   ├→ utils.set_top_level_scalar()  ← 唯一写入口
  upgrade._write_version_yaml()   ─┘

文本插入示意（本仓实际文件）
  # FSTDD 本地版本声明（F 仓 / stdd-repo）          ← 注释头保留
  # 发行版口径：fstdd_version（…）
  # vendored 上游内核口径：upstream_version（…）
  installation_id: STDD-A1B2C3D4                    ← 新增（首个顶层键之前）
  fstdd_version: "3.4.0"
  upstream_version: "3.1.0"
  …
  changelog: |                                      ← 字面块标记保留
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 文本插入位置判断错误，把键插进上一个块标量内部 | 插入点是「首个顶层键之前」，天然在所有块标量之前；写后 `safe_load` + 键值深比较兜底 |
| 正则 `^[A-Za-z_][\w]*:` 误命中注释行里的 `xxx:` | 正则要求行首无 `#`；测试用「注释内含冒号」的夹具反向验证 |
| CRLF 项目被写成 LF，产生全文 diff | bytes 级读写 + 按原文件主导行尾插入；新增 CRLF 夹具断言写后 `\r\n` 数量只 +1 |
| `--prefix` 派生逻辑在两处实现后漂移（EXP-2026-0040） | 新命令直接调用 `init._get_prefix()`；契约测试断言「目录名派生」与「`--prefix` 显式」两条路径 PREFIX 一致 |
| 回填后 8 位 hex 段被 `_rebuild_index` 当序号，`last_id` 跳到百万级 | 以真实 109 条经验库为夹具断言回填前后 `last_id` 恒为 40；沿用 SC-EID-006 契约 |
| 新命令与 `init` 对「坏值」的处理不一致（一个重写、一个报错） | 两者都走 `read_installation_id(warn=True)` 判定；坏值场景断言两者都产出合法新值 |
| 回填动作本身不可回滚 | 只加 1 行；`git checkout -- .fstdd/version.yaml` 即可回滚；且写入前自检失败不落盘 |
