# installation_id 回填：给已初始化项目补齐身份，且不破坏 version.yaml 的可读文本形态

<!-- source_hash: 9b404e276b399981 -->
<!-- generated_at: 2026-10-22T17:19:10+00:00 -->
<!-- canonical: canonical/proposals/2026-10-22-installation-id-backfill.yaml -->

## Why

上一个 change（2026-10-21-installation-id-prefix）只让**新**项目在 `fstdd init` 时 获得 `installation_id`。所有在 v3.1.1 之前初始化的项目 —— 包括本框架仓 stdd-repo 自己 —— 都没有该字段，`_next_id()` 继续产旧格式 `EXP-{year}-{NNNN}`，撞号风险 并未真正消除：ccreits-site 目前靠手工打的 `WBCC-0803ADF7-` 前缀撑着（commit a489420，6 条经验逐个改名），而框架仓新沉淀的 EXP-2026-0038/0039/0040 仍是旧格式。 现存的唯一回填路径是「在项目根重跑 `fstdd init`」，实测会带来两类破坏（见 evidence）。

## What Changes

- 新增顶层子命令 `fstdd installation-id [--prefix X] [--dry-run]`：**只**确保 `installation_id` 存在，不执行 guard 安装 / 经验拉取 / 配置补块 / 全局注册表写入。 已存在合法值 → 打印现值并以 0 退出（不改文件）；不存在 → 生成并写入； `--dry-run` 只打印将生成的值。`.fstdd/` 不存在时报错并以非 0 退出。 复用 `init._get_prefix()` / `_generate_installation_id()` / `utils.INSTALLATION_ID_RE`， 不复制正则与派生逻辑。
- `init._ensure_installation_id()` 的写入从 `yaml.dump` 整体回写改为**注释保留的定向插入**： 在**首个顶层键行之前**插入一行 `installation_id: <值>`（注释头仍留在文件最上方）， 而非在文件末尾追加（文件若以块标量结尾，追加行会被吸进块内）。 写入前 4 条自检（解析 / 键值深比较 / 注释行 / 块标量标记）：`yaml.safe_load` 可解析且为映射、去掉目标键后键值深比较相等、原注释头逐行仍在、 `changelog: |` 等块标量字面标记仍在；任一不满足则不落盘并报错。 `version.yaml` 不可解析时**不写**（沿用上一 change 的 SC-IID-007）。
- `upgrade._write_version_yaml()` 同缺陷同修：它也是 `yaml.dump` 整体回写， 下一次 `fstdd upgrade` 会把 C2 保住的注释头再毁一次。改为同样的注释保留写入 （合并语义不变：未在该次写入参数里出现的既有字段一并存活）。
- 在 stdd-repo 根执行一次 `fstdd installation-id`（PREFIX = `STDD`，由目录名 `stdd-repo` 自动派生），把结果留档为本 change 的验收证据（`git diff` 应为 +1 行）。 并在本仓真跑一次 `fstdd experience add` 验证产出 ID 以 `STDD-` 开头。

## Capabilities

<!-- 机读声明：`fstdd ci check-failures` 的 (b) 范围检查只认 `- capability: <name>` 行，
     而 `fstdd canon generate` 不产出该行（见 FU-005）。每次重新生成 Human View 后需手工补回。 -->
- capability: installation-identity

### New Capabilities


### Modified Capabilities

- **installation-identity**：补上「已初始化项目如何获得 installation_id」这条路径：新增零副作用回填命令， 且写入 SHALL 保留 version.yaml 的注释与字面块等可读文本形态（不再用 yaml.dump 整体回写）。

## Impact

**代码层面**：
- upstream/fstdd/cli/commands/init.py：`_ensure_installation_id` 写入改为注释保留插入；并新增 `cmd_installation_id` 入口（不另建模块，复用同文件的 prefix 派生）
- upstream/fstdd/cli/commands/upgrade.py：`_write_version_yaml` 同修
- upstream/fstdd/cli/utils.py：新增 `set_top_level_scalar()`（注释保留的唯一写入口）
- upstream/fstdd/cli/__init__.py：注册 `installation-id` 子命令
- upstream/tests/commands/：新增/扩展测试（注释保留、幂等、错误路径、prefix 一致性）

**配置层面**：
- .fstdd/version.yaml：新增 `installation_id` 一行（本仓回填，C4）
- .fstdd/experiences/.experience-index.yaml：**不改**（last_id 保持 40，作为回归断言）

**基础设施**：
- 无新增依赖、无服务变更、无部署动作
- 全局 `~/.fstdd/projects.yaml`：本 change 的 `installation-id` 命令**不写**该表（与 init 的差异点）

## Success Criteria

- [ ] stdd-repo 的 `.fstdd/version.yaml` 含 `installation_id`，值匹配 `^[A-Z0-9]{2,8}-[0-9A-F]{8}$`
- [ ] 回填后该文件 4 行注释头仍在、`changelog: |` 字面块标记仍在，且 `git diff` 仅新增 1 行
- [ ] 回填后 `yaml.safe_load` 的既有键值与本 change 前逐键相等（changelog / notes / feedback_protocol 内容不变）
- [ ] 重复执行 `fstdd installation-id`，version.yaml 字节级不变
- [ ] 在无 `.fstdd/` 的目录执行 `fstdd installation-id` 时给出明确错误并以非 0 退出
- [ ] `fstdd installation-id --prefix 'BAD!'` 向 stderr 告警并回落项目名派生，不中止
- [ ] stdd-repo 内 `fstdd experience add` 产出的 ID 以 `STDD-` 开头
- [ ] 带注释的 version.yaml 经 `upgrade._write_version_yaml` 后注释头与字面块仍在
- [ ] `_rebuild_index` 在真实 109 条经验库上回填前后 `last_id` 恒为 40
- [ ] 全量回归（框架侧 + 仓库侧）不退化；`fstdd ci check-failures` 0 error
