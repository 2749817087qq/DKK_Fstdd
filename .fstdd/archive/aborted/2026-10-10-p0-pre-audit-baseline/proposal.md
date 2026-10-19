# proposal.md — P0-pre 审计基线批次

**change_id**: 2026-10-10-p0-pre-audit-baseline
**task_type**: code（工具链整改）
**mode**: standard
**状态**: 待 Gate 1 确认

---

## Why（为什么做）

战略评审（2026-10-10 收口）确认 FSTDD 的核心短板是"规矩没有被可信地数据化"：
经验库 79 条目中 46 条（58%）因解析器 `experience.py:428` 只取首个 frontmatter 块
而静默丢失 `experience_id/category/severity`，`experience stats` 分类分布系统性失真。
治理可信度是 D1 消费端分层的前提（P0-pre 前置的理由），而**修复必须先有量化的修复前基线**，
否则"修好了"无法证伪。同时，仓库开箱不可用（默认解释器缺 pyyaml/jinja2/requests/pytest），
且对 vendored 内核的修改尚无登记契约，直接动手会制造 fork drift。

**证据**（observed_at 待执行时在真实仓库采集，含时区 ISO8601 + git HEAD，不得用文档生成时刻冒充）：
- 【执行时填入】`audit_experience_baseline.py --repo E:/FSTDD/stdd-repo` 实跑输出的 audit JSON 路径与关键指标
- 【执行时填入】git HEAD：<commit>

## What Changes（改什么）

**范围内（本 change 冻结）**：
1. `pyproject.toml`：声明运行时依赖（pyyaml/jinja2/requests）与 `[test]` extra（pytest），
   打包 `upstream/fstdd` 包，`fstdd` console script 指向 `fstdd.cli:main`
2. `docs/UPSTREAM_PATCHES.md`：vendored 补丁登记表（文件/行号/原因/上游 PR/回退版本）
3. `tools/audit_experience_baseline.py`：只读审计脚本（本目录已交付，经 4 轮夹具自测）
4. 在真实仓库实跑审计，产出 `audit-2026-10-experience-baseline.json` 修复前基线并归档

**范围外（明确排除，各为独立 change）**：
- ✗ experience.py:428 解析器修复本身（Phase 1.1 修复批次，依赖本基线）
- ✗ `experience reindex --fix-frontmatter` 存量归一化
- ✗ list/stats 只读化（脏索引修复）
- ✗ CRLF 收口 / archive 两阶段 / ci 三面三数（P0-pre 其余子项）
- ✗ D1–D5 任何消费端/权限/集成工作

## Capabilities（能力影响）

- capability `toolchain-packaging`：FSTDD 可 `pip install -e .[test]` 开箱运行
- capability `governance-trust`：经验库失真从"听说 58%"变为"可复现的量化基线"

## Impact（影响面）

| 面 | 影响 |
|---|---|
| upstream/fstdd/ | **零修改**（本批次不动 vendored 代码，只建立将来修改的登记契约） |
| .fstdd/experiences/ | 只读审计，零写入 |
| 发布 | pyproject 新增文件，install.sh/ps1 不受影响 |

## Success Criteria（验收判据，强制）

| # | 判据 | 验证方式 |
|---|---|---|
| SC-1 | 干净 venv `pip install -e .[test]` 后 `fstdd --help` 正常、`pytest upstream/tests` 全绿 | 实机执行 |
| SC-2 | UPSTREAM_PATCHES.md 存在且含登记表头；`fstdd validate` 对"upstream/ 未登记修改"报非零（validate 检查项属本批次；若评估后超出工作量，降级为登记表+人工流程，须 Gate 2 记录决策） | 实机执行 |
| SC-3 | 审计脚本在真实仓库实跑成功（退出码 0），产出 audit JSON | `python tools/audit_experience_baseline.py --repo <path>` |
| SC-4 | audit JSON 中 affected_files 清单与团队已收口的 46 文件清单**逐一对账**：完全一致 → 基线可信；存在差异 → 以实跑数据为准更新认知并记录差异原因，不得反向改脚本凑数 | 人工对账 + 留痕 |
| SC-5 | audit JSON 含 category_distribution_current_parser 与 true 两组分布，作为 stats 修复后的对比基准 | 检查文件 |

## 风险与边界

- 脚本已知限制：正文中出现独立 `---` 行会干扰切段（经验库格式受控，可接受，已写入 docstring）
- 本提案所有"实跑数据"字段在 Gate 1 确认后由执行代理在真实仓库采集，**禁止预填**
- 按失败模式 #23（YAGNI-7）：validate 漂移检查若 Gate 2 评估超 1 人日，则切出独立 change

## 时间基线

- 提案创建：2026-10-10T18:10+08:00（沙箱时钟，仅作流程记录）
- 证据采集：待执行时在真实仓库按双轨校验执行（值层 + git HEAD）
