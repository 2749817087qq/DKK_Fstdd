# 切片规划 — 2026-09-15-crlf-eol-governance

> 模式：standard｜任务类型：code｜Capability：eol-governance（新增）
> 切片依据：test-plan.md 的 TC-EOL-001 ~ TC-EOL-007，按「可独立验证」切分

## 切片清单

### Slice 1 — EOL 规则声明

| 项 | 内容 |
|---|---|
| **目标** | 在仓库根声明 EOL 规则，使批量 add 不再产生 CRLF 告警 |
| **实现** | 新增 `.gitattributes`，内容 `* text=auto eol=lf` |
| **对应 TC** | TC-EOL-001、TC-EOL-002 |
| **新增测试** | `tools/verify_eol.py::tc_001`、`tools/verify_eol.py::tc_002` |
| **依赖** | 无（首个切片） |
| **风险** | 规则选错会导致索引行尾翻转，由 TC-EOL-004 兜底拦截 |

### Slice 2 — 行尾状态归一

| 项 | 内容 |
|---|---|
| **目标** | 消除索引与工作区行尾不一致的混合态文件 |
| **实现** | 全库 `git ls-files --eol` 扫描（实测 4 个）→ `rm` + `git checkout --` 重建 |
| **对应 TC** | TC-EOL-003、TC-EOL-004、TC-EOL-005 |
| **新增测试** | `tools/verify_eol.py::tc_003`、`tc_004`、`tc_005` |
| **依赖** | Slice 1（须先有规则，checkout 才按 LF 重建） |
| **风险** | `rm + checkout` 会丢弃未暂存改动，执行前已用 `git status --porcelain` 确认 |

### Slice 3 — 可执行性与文档

| 项 | 内容 |
|---|---|
| **目标** | 确保脚本 shebang 不被破坏，且 EOL 策略在文档中可查 |
| **实现** | CLI 冒烟验证；README §8 补充「行尾符（EOL）治理」小节；新增 `.gitignore` 排除 CLI 生成的本地配置 `.claude/` |
| **对应 TC** | TC-EOL-006、TC-EOL-007 |
| **新增测试** | `tools/verify_eol.py::tc_006`、`tc_007` |
| **依赖** | Slice 1、Slice 2 |
| **风险** | 无 |

## 执行顺序与理由

```
Slice 1（规则） → Slice 2（归一） → Slice 3（验证+文档）
```

规则必须先于归一：只有 `.gitattributes` 生效后，`git checkout --` 才会按 LF 重建文件；
顺序颠倒会导致归一后再次被 `core.autocrlf` 转成 CRLF。

三个切片**串行执行**，不可并行——它们操作同一个 Git 索引，并会产生状态耦合。

## 偏离记录（Design Adjustments）

| # | 偏离 | 原因 | 影响 |
|---|---|---|---|
| DA-1 | 规则由 `* -text` 改为 `* text=auto eol=lf` | 实测 `* -text` 使索引翻转为 `i/crlf` 并产生 494 行 diff | 在 Gate 1 前已修正提案并重确认 |
| DA-2 | 新增 `.gitignore` 排除 `.claude/` | CLI 生成的本地配置含本机路径，且会被持续重建 | 原提案未包含，属实现期发现 |
| DA-3 | TC-EOL-005 断言改为「排除有意修改 + 仅统计 diff-filter=M」 | 原断言无法区分行尾变更与内容变更，且在提交前因新增文件必然假失败 | 测试设计缺陷修正，非实现缺陷 |
