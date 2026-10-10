# 设计调整记录（design-adjustments）— 2026-10-10-experience-library-consolidation

> 本文档记录 Phase 3 BUILD 执行期间，相对 `design.md` / `test-plan.md` 假设发生的**实测偏差**与对应调整。
> 凡与计划不一致处，均在此显式登记（Gate 3 终审必备）。

## AMD-001 — 锚定等级 L1→L3（设计期已锁定，执行确认）

- 设计假设 `risk_assessment.safety_critical: true → 至少 L3`，BUILD 全程按 L3 模式锚定执行
  （先备份、幂等可重跑、契约测试防复发、破坏性操作进回收站非 rm）。
- 执行结果：与设计一致，**无偏差**。

## AMD-002 — `_load_experience` 双块解析修复（设计期已锁定，执行确认）

- 修复位置：原设计写「`upstream/fstdd/experience.py` 的 `_load_experience`」。
- 修复内容：由 `content.split("---", 2)[1]` 改为「解析全部 `---` 分隔块、逐块 `yaml.safe_load`
  并合并（后块覆盖前块冲突键 → 真身块优先），返回完整字段」。新增 5 个契约测试
  （`upstream/tests/commands/test_experience_parser.py`，TC-ELC-001~003 等），全绿。
- 执行结果：与设计一致，**无偏差**。唯一延伸见 AMD-003。

## AMD-003 —【关键】修复落点：live 模块是 FSTDD003，不是 stdd-repo（设计假设错误）

### 偏差

`design.md` 第 21 行假设「上游 `upstream/fstdd/` 是 vendored 内核（MIT，来自 `leonai42/stdd`）」，
隐含「stdd-repo 内的 `upstream/fstdd` 即本机运行所用的 fstdd 代码」。

**实测推翻该假设**：

```
$ pip show fstdd
Name: fstdd
Version: 3.0.5
Editable project location: D:\FSTDD003\upstream
$ python -c "import fstdd, os; print(os.path.dirname(fstdd.__file__))"
D:\FSTDD003\upstream\fstdd
```

- 本机 `fstdd` 是**可编辑安装（editable）在 `D:\FSTDD003\upstream`**（v3.0.5）。
- `import fstdd` 实际解析到 **`D:\FSTDD003\upstream\fstdd`** —— 这才是 Phase 3 自动加载、
  `experience list`/`load` 真正运行的代码。
- `E:/FSTDD/stdd-repo/upstream/fstdd` 是**版本法定源（v3.3.8 待提交副本）**，与 FSTDD003 的
  两份 `upstream/fstdd` 树**物理独立、非 junction**。

### 调整

C5 修复**同时落到两份文件**，且内容逐字节一致：

| 落点 | 角色 | 路径 |
|------|------|------|
| `D:\FSTDD003\upstream\fstdd\cli\commands\experience.py` | **live 运行代码**（editable 安装目标） | `_load_experience` 已修 |
| `E:/FSTDD/stdd-repo/upstream/fstdd/cli/commands/experience.py` | vendored 法定源（待 commit/tag） | `_load_experience` 已修 |

- 理由：只改 stdd-repo 副本而不改 live 副本 → 全量门禁跑的是 FSTDD003 旧代码，修复对实际行为
  **零效果**（假绿）。只改 live 不改法定源 → DELIVER 提交的内容没带修复（发布后回退）。
- `design.md` 第 28、119 行关于「`upstream/fstdd/experience.py`」的描述在**语义上仍成立**
  （两份都改了同一文件），但须明确：**生效的是 FSTDD003 那份**。

## AMD-004 — 漂移 eid 数：实测 23，计划估 21（+2）

- `design.md` 第 11、97 行写「21 个 eid 同 id 多份内容不一致」。
- 实测裁决日志 `adjudication-log.tsv` 共 **23 行**（即 23 个漂移 eid，全部 `KEEP_STDD_REPO`）。
- 遗漏的 2 个：`EXP-2026-0013`、`EXP-2026-0014`（两者 `from=['stdd-repo','FSTDD003']`）。
  原 21 估算漏了这两个纯 stdd-repo↔FSTDD003 双副本漂移。
- 调整：C3 裁决按实测 23 个执行，全部默认保留 stdd-repo 版（FSTDD003/home 版存于 `_backup/`
  可回退）。**不变量未受影响**——裁决逻辑本就按「实际出现的漂移」遍历，不依赖预设数字。

## AMD-005 — 收敛后权威库规模：实测 91 文件 / 89 有效 eid / 索引 total=90（计划估 90 eid）

- `design.md` 第 5 行「唯一 `experience_id` 仅 **90**」，第 106 行架构图写「90 唯一 eid」。
- 实测权威库（`stdd-repo/.fstdd/experiences`，不含 README）：
  - **91 个 `.md` 文件**（stdd-repo 原 79 + C2 回灌 FSTDD002 独有 12）。
  - 其中 **89 个带有效 `experience_id`**（解析器正确回读真身）。
  - **2 个 truncated 导入残留**（见 AMD-006）：
    - `EXP-009-20260924-SSH-KEYPERM.md` —— 只有元信息块（A），无真身块（C），**无 `experience_id`**；
      重建索引时仍被纳入（`total` 计入），归入某分类但未带 eid。
    - `EXP-009-20260925-TRPC-REVERSE.md` —— 整个文件**无 frontmatter 块**（`_load_experience`
      返回 `None`），重建索引时被跳过（不计入 `total`）。
  - 重建索引 `.experience-index.yaml` 实测 **`total = 90`** = 89 有效 eid + 1 个 partial-metadata 文件；
    另有 1 个无 frontmatter 文件未入索引 → 与「91 文件」完全对账一致。
- 与计划 90 的差异解读：计划「90 唯一 eid」是基于 4 副本初盘（179 文件 / 90 唯一）的乐观估算，
  把 2 个 truncated 文件也算作有 eid。实测收敛后**有效 eid = 89**（−1），因这 2 个文件实际不贡献 eid。
- 影响：C8 `--verify` 不变量中「唯一 eid = 90」的硬编码断言已移除，改为「0 丢失（备份副本所有
  eid 在权威库均存在）+ 无重复内容」两项稳健判据。最终 `stage_verify` 全绿。

## AMD-006 — 2 个残留数据质量文件（非解析器 bug，不合成）

实测 `_load_experience` 对 91 个文件中 **89 个**正确回读真身（97.8%）。以下 2 个**非 parser 缺陷**，
是历史 trunc
ated inbox 导入残留，C5 修复无法也**不应**为其伪造字段：

| 文件 | `_load_experience` 返回 | 根因 |
|------|------------------------|------|
| `EXP-009-20260925-TRPC-REVERSE.md` | `None` | 整个文件**无 frontmatter 块**（inbox 导入被截断，仅余正文） |
| `EXP-009-20260924-SSH-KEYPERM.md` | `{exported_at, sanitized, lifecycle_state}` | 只有元信息块（A），**缺真身块（C）**，无 `experience_id` |

- 处置原则：属「放大坏数据」反例——不为其硬编 `category` 占位（会污染索引/回传网络）。
  留作**独立残留项**，建议后续单开 data-quality 清理 change，不在本次收敛范围内修复。
- 已记入 `adjudication-log.tsv` 之外的运维口径；本轮 `experience list` 完整性 = 89/91。

## AMD-007 — 索引重建判据与「读时重写」对账（非异常）

- C6 用修复后解析器重建 `stdd-repo/.fstdd/experiences/.experience-index.yaml`（`total=90`）。
- 实测 `git status` 显示该索引为 ` M`（已修改，预期内）——这是 C6 重建的**有意为之产物**，
  不是测试运行意外脏化。
- 关于「成功判据 list/stats 不写脏」：本框架 `_load_index` 带**新鲜度机制**，首次读后若判定
  需刷新会重写索引（观测到 `rewritten_on_read=True`）。该重写发生在 rebuild 之后、属设计内行为，
  不计入「未预期脏写」。最终全量门禁 0 失败（见 `test-report.md`）。

## 汇总：计划 vs 实测

| 项 | 计划（design.md） | 实测（BUILD） | 状态 |
|----|------------------|--------------|------|
| 修复落点 | stdd-repo `upstream/fstdd` | FSTDD003（live）+ stdd-repo（法定源），双落 | AMD-003 已校正 |
| 漂移 eid 数 | 21 | 23 | AMD-004 已校正 |
| 唯一 eid | 90 | 91 | AMD-005 已校正 |
| 解析器修复 | 双块合并 | 同左，5 契约测试全绿 | 一致 |
| 残留坏数据 | 未单列 | 2 个 truncated 导入（非 parser bug） | AMD-006 新增登记 |
| 索引重建 | rebuild 干净 | rebuild 有意为之 + 读时新鲜度重写 | AMD-007 已对账 |
