# skill 工程规范 - 技术设计

## Context

**当前系统状态**

- 两个 skill 目录：`.workbuddy-ai/skills/`（9 个，STDD 自家为主）与
  `.workbuddy/skills/`（31 个，D哥 自建与第三方混合）。
- `tools/verify_workbuddy_skills.py`：纯静态文本检查，对 CLI 只有 `CLI_ABS.exists()`，
  全脚本 `subprocess` 出现次数 **0**。
- `tools/install_workbuddy_skills.py`：生成 6 个 STDD skill 的 frontmatter，
  当前写入 `name` / `description` / `stdd_version`，**无 `license` 与 `version`**。
- 元数据实测（40 个 skill）：`name` 40/40、`description` 40/40、
  `version` 17/40、`license` 3/40、四项齐全 3/40。

**约束条件**

- `--fix` 会写入用户既有的 31 个 skill 文件，必须先备份。
- 只增删 frontmatter 字段，正文字节级不可变。
- 未知许可/版本一律 `unknown`，严禁推测。
- CLI 冒烟不得污染真实项目。

**问题证据**

| 证据 | 来源 |
|---|---|
| verify 从不执行 CLI | 源码 `grep -c "subprocess\|run("` = 0；对 CLI 仅 `Path.exists()` |
| 该盲区造成过实际漏检 | change `2026-09-15-crlf-eol-governance`：CRLF 缺陷导致 commit 被 SIGTERM，而 verify 报 PASS |
| 元数据缺失 | 实测扫描：license 缺 37/40，version 缺 23/40 |

## Decisions

### 1. 冒烟采用「真实子进程执行」，而非 import 调用

**方案**：在 `verify_workbuddy_skills.py` 中用 `subprocess.run([PY, CLI, ...])`
于临时目录实际执行 `init` / `new` / `status`。

**为什么**：

- 只有真实子进程才能覆盖 shebang 解析、解释器路径绑定、工作目录依赖——
  这三类恰是上一个 change 暴露出的真实故障面（CLI 行尾、路径硬编码）。
- `import` 方式会绕过 shebang 与进程环境，等于没验证。

**备选方案及排除原因**：

- **备选 A 仅 `Path.exists()`（现状）**：已被证伪——文件在但跑不起来时照样报 PASS，排除。
- **备选 B `--help` 或 `--version`**：STDD CLI 不支持 `--version`（实测报
  `unrecognized arguments`），且 `--help` 不覆盖 `init` 所需的模板资源读取，排除。
- **备选 C 直接用 `sys.executable`**：与 skill 中固化的解释器可能不一致，
  导致"能跑但用的是错解释器"，排除。统一用脚本内的 `PY` 常量。

### 2. frontmatter 修改采用「文本插入」，而非 YAML 重写

**方案**：定位 frontmatter 的 `---` 区间，在末尾按行插入缺失字段，
正文部分原样拼接，不做 YAML round-trip。

**为什么**：

- YAML round-trip（解析→改→dump）会重排键序、改写缩进、转义多行字符串，
  造成大规模无意义 diff，且可能损坏 D哥 skill 中的手工排版。
- 文本插入可保证正文字节级不变，可用哈希断言证明。

**备选方案及排除原因**：

- **备选 A `yaml.safe_dump` 重写**：会产生全量 diff 且丢失注释与格式，排除。
- **备选 B 正则替换**：多行 description（`|` / `>`）场景下易误匹配，排除。
  实现上改用「按行定位第一个非缩进的顶层键」来确定插入点，不用正则猜。

### 3. 备份策略：全量快照 + 时间戳目录 + 可回滚

**方案**：`--fix` 执行前，把**所有待修改**的 SKILL.md 复制到
`~/.workbuddy-ai/backups/skill-metadata-<YYYYmmdd-HHMMSS>/`，保持相对路径结构。
备份文件数与待改文件数必须相等，不等即中止。提供 `--revert` 从最新备份恢复。

**为什么**：写入目标是用户既有的 31 个 skill，损坏后果是"skill 整体不可用"，
远重于"少一个字段"。备份是唯一可靠的兜底。

**备选方案及排除原因**：

- **备选 A `git` 管理**：这些 skill 目录不是 git 仓库，排除。
- **备选 B 就地 `.bak` 文件**：污染 skill 目录，且 WorkBuddy 可能把 `.bak`
  也识别为 skill，排除。

### 4. 未知值统一写 `unknown`

**方案**：`license` 缺失 → `unknown`；`version` 缺失 → `unknown`。

**为什么**：显式 `unknown` 与字段缺失在语义上不同——前者表示「已检查但确知未知」，
后者无法区分「未检查」与「确知无」。第三方 skill 的许可协议无可靠来源，
任何推测值都比 `unknown` 更危险（错误声明具备误导性）。

**备选方案及排除原因**：

- **备选 A 统一写 `MIT`**：会给无许可的第三方 skill 打上错误声明，属实质性误导，排除。
- **备选 B 写 `0.0.0`**：暗示"已版本化且是初始版"，与事实不符，排除。

## Architecture

### 校验链路（改造后）

```
verify_workbuddy_skills.py
  │
  ├─ 静态检查（原有，保留）
  │    ├─ CLI 文件存在 / yaml·jinja2 可导入
  │    ├─ 6 个 SKILL.md 存在 + name 匹配
  │    ├─ stdd-deliver 哨兵 + 升级规程
  │    └─ 无残留相对路径
  │
  └─ 运行时冒烟（新增）
       └─ tempfile.mkdtemp()
            ├─ stdd init     → 退出码 0？
            ├─ stdd new smoke→ 退出码 0？
            └─ stdd status   → 退出码 0？
            └─ finally: shutil.rmtree(tmp)   ← 必须清理
       任一非 0 → fails.append(...) → 退出码 1
```

### 元数据治理链路

```
check_skill_metadata.py [--fix] [--revert]
  │
  ├─ 扫描：遍历目录 → 解析 frontmatter → 统计四项
  │
  ├─ 默认（无 --fix）：只输出报告，不写任何文件
  │
  └─ --fix：
       1. backup()        → 复制待改文件到 backups/<时间戳>/
       2. 断言 备份数 == 待改数，否则中止
       3. 逐文件 insert_fields()   ← 仅 frontmatter，正文原样
       4. 校验 YAML 可解析，失败则回滚该文件
       5. 输出改动清单
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| `--fix` 损坏用户既有 skill 的 frontmatter | 执行前全量备份 + 备份数断言；写回前 YAML 可解析校验；失败即回滚该文件；提供 `--revert` |
| 正文被意外改写 | 用哈希断言：修改前后正文部分（frontmatter 之后的全部字节）必须一致 |
| 冒烟拖慢校验（每次多 3-8 秒） | 可接受；冒烟是最有价值的门禁项。临时目录用 `finally` 确保清理 |
| 冒烟因环境（非 CLI 缺陷）失败造成误报 | 失败信息区分「CLI 缺失/无权限」与「命令返回非 0」两类，分别给出定位提示 |
| 改造后 verify 由 PASS 变 FAIL | 这正是目的（暴露被掩盖的问题）。test-report 记录该预期；首次运行输出「新增强化检查项」提示 |
| 批量写入 31 个 skill 引发用户疑虑 | 已有明确授权；`--fix` 前打印待改文件清单，默认 dry-run |
