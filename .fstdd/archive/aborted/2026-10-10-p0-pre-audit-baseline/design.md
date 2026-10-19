# design.md — P0-pre 审计基线批次（change_id: 2026-10-10-p0-pre-audit-baseline）

**阶段**: P2 SPEC ｜ **前置**: Gate 1 已确认（2026-10-10T18:26+08:00）｜ **待**: Gate 2 确认

## 1. 目标与非目标

**目标（冻结范围，来自 proposal）**
1. `pyproject.toml`：声明运行时依赖与 [test] extra，打包 upstream/fstdd，`fstdd` console script 可用
2. `docs/UPSTREAM_PATCHES.md`：vendored 补丁登记表
3. `tools/audit_experience_baseline.py`：只读审计脚本（本目录已交付并经真实数据抽查）
4. 真实仓库实跑审计，产出 `audit-2026-10-experience-baseline.json` 修复前基线

**非目标（范围外，任何出现即违规）**
- ✗ experience.py:428 解析器修复 / reindex 归一化 / list/stats 只读化
- ✗ CRLF 收口 / archive 两阶段 / ci 三面三数
- ✗ 基于哈希的 upstream 漂移全量检测（见 §5 决策 D-2，明确切出）

## 2. 真实数据实证（设计的输入，非假设）

经 GitHub 镜像 master 分支两次独立抓取 + base64 解码交叉验证（2026-10-10）：

| 实证 | 结论 |
|---|---|
| inbox 导入条目结构 | 三段式多块：注释 + `---`导出块{exported_at,sanitized}`---` + 注释 + `---`真身块{experience_id,category,severity,...}`---` + 正文 |
| 现有解析器视角（首块） | 3 个必填字段全丢；真身块视角全部可恢复 → 58% 失真机制成立 |
| EXP-2026-0017（本地新建抽样） | 单块、字段齐全 → 本地新建不受影响 |
| **EXP-1BA44745.md** | 🟠 真身块内 experience_id=`EXP-1BE44745`，与文件名/注释块（`EXP-1BA44745`）不一致 → eid 级缺陷真实存在 |

**由此得出的两条硬设计约束**：
- C-1 真身块锚定规则 = 「含 `experience_id` 键的最后一个 frontmatter 块」（注释块内也有 eid 行，简单取末块会被正文/注释干扰）
- C-2 审计必须输出 **filename vs 真身块 eid 一致性** 检查结果（新缺陷类别的检测面）

## 3. 组件设计

### 3.1 pyproject.toml（新增，仓库根）
- `[project] dependencies = [pyyaml>=6.0, jinja2>=3.1, requests>=2.31]`；`[project.optional-dependencies] test = [pytest>=8.0]`
- `[tool.setuptools] package-dir = {"" = "upstream"}` + `packages.find where=["upstream"] include=["fstdd*"]`
- `[project.scripts] fstdd = "fstdd.cli:main"`（与 upstream/fstdd/__main__.py 入口一致）
- `version = "3.3.8"`（R 轴，与 .fstdd/version.yaml 同步；E/K 轴不进本项目 version 字段）

### 3.2 docs/UPSTREAM_PATCHES.md（新增）
- 表头列：# / 文件 / 行号 / 修改原因 / 关联上游 issue或PR / 登记日期 / 登记人 / 预期回退版本
- 基线声明：E=3.0.5 / K=3.1.0 / R=3.3.8，指向 docs/UPSTREAM_BASELINE.md
- 「待登记」区：已识别未动手的修改意向（experience.py:428、71 处 CRLF——后者走上游 PR 路线不本地改）

### 3.3 validate 新增检查项 `upstream-patches`（决策见 D-1）
位于 upstream/fstdd/ 的 validate 命令组。行为：
- 检查 docs/UPSTREAM_PATCHES.md 存在且表体 ≥0 行可解析（表头必须完整）
- 每行登记的文件路径必须存在于仓库（repo root 相对路径）
- 失败 = 非零退出 + 指明缺失文件/表头
- **不做事**：哈希比对、与 UPSTREAM_BASELINE.md 交叉验证（D-2 切出）

### 3.4 tools/audit_experience_baseline.py（已交付 v1.0，本 change 将其入库）
- 零第三方依赖（仓库默认解释器缺 yaml， deliberate）
- 切段算法：按 `---` 分隔线切段，首个无 top-level 键的段 = 正文截断点（自测实证 toggle 法/正则法均会吞块或错位）
- 输出 schema 见 §4；退出码 0=完成 / 2=仓库路径或目录无效

### 3.5 审计产物归档
- 运行：`python tools/audit_experience_baseline.py --repo <repo> --out .fstdd/experiences/audit-2026-10-experience-baseline.json`
- 产物不入 git（.fstdd/experiences/ 受 gitignore 管控与否以仓库实际为准；若入库则作为 Phase 1.1 修复批次的对比基准）

## 4. 数据设计（audit JSON schema）

```
audit_meta:   {tool, repo, audited_at(带时区ISO8601), git_head(可空), note}
summary:      {total_entries, dual_block_entries, affected_entries, affected_ratio,
               field_loss_counts{experience_id,category,severity},
               category_distribution_current_parser{}, category_distribution_true{},
               eid_mismatch: {count, files[]},            # C-2 新增
               index_reconciliation: {indexed_true, indexed_false_files[], eid_mismatch_files[]}}
affected_files: [...]
records[]:    {file, structure(single_block|dual_block_import|exported_block_only|multi_block_N|no_frontmatter),
               n_blocks, first_block_keys[], last_block_keys[],
               true_eid, filename_stem, eid_match(bool),     # C-2 新增
               missing_current[], recovered_by_last_block[],
               in_index(true|false|"index_missing")}
```

## 5. 决策记录（Gate 2 须确认）

| # | 决策 | 内容 | 依据 |
|---|---|---|---|
| D-1 | validate 检查项做**结构级** | 只验证登记表存在/可解析/登记路径存在；不做「未登记修改」检测 | 后者需要逐文件基线哈希，依赖 UPSTREAM_BASELINE.md 的格式约定（本 change 未实读该文件）；YAGNI-7 梯子第 5 级「更简单方案」 |
| D-2 | 哈希级漂移检测**切出**为独立 change | 触发条件：下次同步上游 E/K 轴之前必须落地 | proposal SC-2 允许降级但须 Gate 2 记录——此表即记录 |
| D-3 | eid 不一致检测**纳入**本批次验收 | EXP-1BE44745 案例证明该缺陷真实存在且会被索引对账自然暴露 | 评审质疑 #7「验收判据逐字段定义」的落实 |
| D-4 | 镜像抽查数据**不作正式基线** | GitHub 是镜像非真值源（架构 §5.11），正式基线以本地实跑为准 | 时间基线双轨校验纪律 |

## 6. 风险

| 风险 | 缓解 |
|---|---|
| UPSTREAM_BASELINE.md 实际已含哈希，D-1 错过低成本升级 | P3 开工第一步实读该文件，若含 per-file hash 则 D-1 升级为哈希比对（变更须走 gate amend） |
| 本沙箱无仓库访问权，specs 未对真实 validate/ci 代码做行级锚定 | P3 切片时以仓库实读为准，spec 与代码冲突时停刀上报，不得静默改 spec |
