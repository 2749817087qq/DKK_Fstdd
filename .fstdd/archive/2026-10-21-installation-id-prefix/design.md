# init.py 生成 installation_id + _next_id() 使用前缀 - 技术设计

## Context

**项目**：stdd-repo（FSTDD 框架本身，「用 FSTDD 改 FSTDD」）
**当前版本**：fstdd_version 3.4.0 / upstream_version 3.1.0
**基线 git sha**：`a489420`

**待改代码位置**：
- `upstream/fstdd/cli/commands/init.py`（392 行，`cmd_init` + `_post_init_*` 系列）
- `upstream/fstdd/cli/commands/experience.py`（1687 行，`_next_id` + `_iter_experience_files` + `_rebuild_index`）
- `upstream/.fstdd/version.yaml`（模板，init 时复制到项目）

**既有实践（锚定）**：
- 上游 `.fstdd/experiences/` 已有 `FSTDD002-EXP-*` 前缀条目（12 条），是手工使用的先例
- ccreits-site 项目已用 `WBCC-0803ADF7-EXP-*` 前缀手工改编号并回传（commit `a489420`）

**关键约束**：
- 向后兼容：既有项目（无 installation_id）的 `_next_id` 必须回落到旧格式
- 只用标准库（`secrets` / `yaml`），不引入新依赖
- 不改既有条目的 ID
- EXP-2026-0013 教训：ID 正则与实际形态必须一致

## Decisions

### 1. installation_id 格式：`{PREFIX}-{8HEX}`

**方案**：PREFIX 由项目名前 4 字母大写派生（如 `stdd` → `STDD`，`ccreits-site` → `CCRE`），HEX 由 `secrets.token_hex(4).upper()` 生成。完整格式如 `STDD-A1B2C3D4`。

**为什么**：
- PREFIX 提供人类可读的项目归属（一眼看出是哪个项目的经验）
- HEX 提供 2^32 随机空间，同项目内碰撞概率极低（65K 次 init 才 >50%）
- 合在一起 `PREFIX-HEX` 比 UUID 短得多（13 字符 vs 36），适合做文件名前缀
- 与既有 `FSTDD002` / `WBCC-0803ADF7` 实践形态一致

**备选方案及排除原因**：
- 备选 A：纯 UUID4（`550e8400-e29b-41d4-a716-446655440000`）。太长，不适合做文件名前缀；无人类可读性
- 备选 B：纯递增序号（`FSTDD003` / `FSTDD004`）。需要全局注册表分配，引入中心化依赖
- 备选 C：只用项目名（`STDD`）。同名项目会撞（两个 `stdd` fork）
- 备选 D：`token_hex(8)`（16 位 HEX）。过度——2^32 已够用

### 2. PREFIX 派生：项目名前 4 字母，可 `--prefix` 覆盖

**方案**：`cmd_init` 新增 `--prefix` 可选参数。缺省从 `project_root.name` 取前 4 字母大写。若项目名 < 4 字符，用全部字符。非 ASCII 字符取 ASCII transliteration 或直接跳过。

**为什么**：
- 自动派生免去用户记忆负担
- `--prefix` 给需要显式控制的场景（如一个项目有多个 installation）
- 与 `init` 既有参数风格一致（`--isolate` 等都是可选参数）

**备选方案及排除原因**：
- 备选 A：强制要求 `--prefix`。增加摩擦，大多数用户不需要
- 备选 B：从 `project.yaml` 的 `project.name` 读。init 时该文件还没写入（是 init 写它）

### 3. `_next_id` 读 installation_id 的时机与缓存

**方案**：`_next_id(index)` 改为 `_next_id(index, project_root)`。新增参数 `project_root: Path`。函数内部读 `project_root / ".fstdd" / "version.yaml"`，解析 YAML 取 `installation_id`。

**不做模块级缓存**：`experience add` 是低频操作（每次 DELIVER 才调一两次），读一个小 YAML 文件的开销可忽略。缓存会引入「init 后改了 prefix 但 `_next_id` 仍用旧值」的过期问题。

**为什么传 `project_root` 而非全局读 `Path.cwd()`**：
- `experience add` 可能在 worktree 模式下运行，`cwd` 不一定是项目根
- 显式传参比隐式依赖 `cwd` 更可测试

**备选方案及排除原因**：
- 备选 A：在 `_load_index` 时一并读 installation_id 写进 index dict。耦合两层职责（索引管理 + 版本管理）
- 备选 B：模块级常量 `INSTALLATION_ID = _read_install_id()`。启动时求值，worktree 切换后不更新
- 备选 C：环境变量 `FSTDD_INSTALLATION_ID`。泄漏到子进程，worktree 模式会串

### 4. 回落逻辑：`version.yaml` 不存在或无字段 → 旧格式

**方案**：
```python
def _next_id(index: dict, project_root: Path = None) -> str:
    last = index.get("last_id", 0)
    year = datetime.now().year
    next_num = last + 1
    base = f"EXP-{year}-{next_num:04d}"
    if project_root is None:
        return base
    install_id = _read_installation_id(project_root)
    if install_id:
        return f"{install_id}-{base}"
    return base
```

**为什么**：
- `project_root=None` 时（如单元测试直接调 `_next_id`）直接返回旧格式
- `version.yaml` 存在但无 `installation_id` 字段（既有项目）→ 返回旧格式
- `version.yaml` 不存在 → 返回旧格式
- 只有 `installation_id` 非空时才加前缀

**备选方案及排除原因**：
- 备选 A：既有项目也自动补 installation_id。改 `version.yaml` 是写操作，`_next_id` 应该是纯读
- 备选 B：抛异常要求必须先 init。太激进，破坏既有项目

### 5. `_iter_experience_files` ID 提取：确认带前缀形态可识别

**方案**：不修改 `_iter_experience_files` 的逻辑（2026-09-17 修复已支持任意 `.md` + frontmatter `experience_id`），但在测试中验证带前缀的文件名 stem（`WBCC-0803ADF7-EXP-2026-0019-syspath-presence-vs-position`）能被正确提取。

**关键点**：`_iter_experience_files` 优先取 frontmatter `experience_id`，没有时用文件名 stem。带前缀的经验文件如果有 frontmatter，ID 从 frontmatter 取（完整 `{PREFIX}-EXP-{year}-{NNNN}`）；没有 frontmatter 时从文件名 stem 取。

**EXP-2026-0013 教训应对**：ID_RE 正则（如果存在）必须匹配 `{PREFIX}-EXP-{year}-{NNNN}` 形态，不能只匹配 `EXP-{year}-{NNNN}`。需在测试中验证。

**备选方案及排除原因**：
- 备选 A：重写 `_iter_experience_files` 加带前缀的 glob。破坏 2026-09-17 修复的「扫所有 .md」设计
- 备选 B：在 `_rebuild_index` 里加前缀解析。职责错配——rebuild 只负责从文件提取 ID，不负责定义 ID 格式

## Architecture

```
fstdd init                                fstdd experience add
     │                                         │
     ▼                                         ▼
cmd_init                               cmd_experience_add
     │                                         │
     ├── 1. 创建 .fstdd/ 骨架                   ├── _index_lock
     ├── 2. ★ 生成 installation_id              ├── _load_index
     │     secrets.token_hex(4).upper()         ├── ★ _next_id(index, project_root)
     │     PREFIX = --prefix or               │     ├── _read_installation_id(project_root)
     │       strip([^A-Z0-9]) → [:4] → FSTDD    │     │   └── utils.read_installation_id
     │     结果恒匹配 ^[A-Z0-9]{2,8}$           │     │       （形状校验，非法 → None + 告警）
     ├── 3. 写入 .fstdd/version.yaml            │     ├── 有 → f"{id}-EXP-{year}-{NNNN}"
     │     installation_id: "STDD-A1B2C3D4"     │     └── 无 → f"EXP-{year}-{NNNN}"（回落）
     │     （合并写：既有字段不丢；            ├── 写经验文件
     │      解析失败则不写并告警）              └── _save_index
     ├── 4. _register_project
     ├── 5. _post_init_*
     └── 6. _post_init_self_check
           ★ 打印实际生效值（✅ <id> / ⚠️ 未写入）

fstdd experience list                     fstdd experience sync --push
     │                                         │
     ▼                                         ▼
_iter_experience_files                   _exp_sync.push_bundle
     │                                         │
     ├── 扫所有 *.md + *.yaml                    ├── load_entries（用 _iter_experience_files）
     ├── 优先取 frontmatter experience_id       ├── sanitize（脱敏）
     ├── 没有则用文件名 stem                     └── scp/inbox POST
     └── ★ 带前缀的 stem 与 frontmatter
        均为完整 ID，无需特殊处理
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 既有项目（无 installation_id）的 `_next_id` 回落到旧格式，与新项目带前缀的 ID 在同一索引中共存 | 两者字符串不同（`EXP-2026-0019` vs `STDD-A1B2C3D4-EXP-2026-0019`），不会覆盖；`_rebuild_index` 用完整字符串做唯一键 |
| PREFIX 从项目名派生时，非 ASCII / 含连字符的项目名可能产出畸形前缀 | 派生前 `strip().upper()` + 剥掉所有非 `[A-Z0-9]` 字符，再取前 4 位；清洗后不足 2 位回落 `FSTDD`。**必须清洗而非「保留连字符」**：`my-project → MY-P` 会让 ID 变三段，打穿 `split('-')[-1]` 取序号的既有假设（实测 `_rebuild_index` 会把 HEX 段当序号，last_id 直接跳到 803 万级） |
| `--prefix` 用户指定了含特殊字符的值（如 `MY PROJECT`） | 校验 `[A-Z0-9]{2,8}`，不合法则**告警 + 回落项目名派生**（原设计为 exit 1，评审后改降级：一个可选参数不该让 init 全盘失败） |
| `_next_id` 新增 `project_root` 参数，既有调用点需更新 | 全仓 grep 确认唯一调用点是 `_cmd_add`；签名带默认值 `None`，漏传只会静默回落旧格式（不是崩溃），故用测试 `test_next_id_project_root_none` 固化该行为 |
| EXP-2026-0013：ID 正则与实际形态不一致 | 正则收归 `fstdd.cli.utils.INSTALLATION_ID_RE` 单一常量，生成端与读取端共用；测试断言 `INSTALLATION_ID_RE.match(iid)` 而非硬编码格式 |
| **`fstdd upgrade` 会抹掉 installation_id**（设计时的假设「upgrade 不改项目级 version.yaml」是**错的**） | 实测：`upgrade._write_version_yaml` 以固定 5 字段**整体覆盖**项目级 version.yaml。已改为「读既有 → 合并 → 写」，并加 `test_upgrade_write_preserves_installation_id` 用自定义字段 `future_field` 反向验证合并语义（防下一个新增字段重蹈覆辙） |
| **ID 带前缀后打穿下游 `EXP-*.md` 通配** | 实测 4 处消费方依赖 `EXP-` 前缀，其中 `tools/share_experience.py` 是**回传通道**（漏掉 = 云端静默收不到新经验，比 CLI 侧更隐蔽）。全部改为「任意 `*.md`（FSD-004 语义）」；并把 FSD-004 门禁的扫描范围从 `fstdd/cli` 扩到 `tools/` + `.fstdd/hooks/`，让这类回归在下次立刻变红 |
| version.yaml 损坏时被覆写成只剩 installation_id | `_ensure_installation_id` 解析失败即**不写**并告警（返回 None，自检报 ⚠️）；`_write_version_yaml` 解析失败也出声而非静默当空 |

