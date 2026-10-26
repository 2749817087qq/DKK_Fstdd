# 经验库诊断与框架缺陷修复 — 技术设计

## Context

本仓经验库 113 条经验 + 377 图谱节点。`kg sync` 恒 0 匹配、`ci check-failures`
TC 覆盖假红、`yaml.dump` 破坏手写 YAML、`experience list` 重写索引、`collect_local`
无水位线——5 项系统性缺陷，每项有经验直接证据。

技术栈：Python 3.13 + PyYAML + pytest。修改面：`upstream/fstdd/cli/commands/experience.py`、
`upstream/fstdd/cli/commands/ci.py`、`tools/share_experience.py`。

## Decisions

### D1. C1 frontmatter 解析修复

**问题**：`_load_experience`（`experience.py:408`）用 `re.match(r'^---\n(.*?)\n---', text, re.DOTALL)`
只取**第一个** frontmatter 块。双重包裹条目（外层 `---` 包住内层 `---`）的内层字段全丢。

**修复**：改为取**最后一个** `---...---` 块（双重包裹的内层才是真实 frontmatter）。
若只有一个块，行为不变。加 `parse_all_frontmatter()` 辅助函数，返回所有块的列表，
`_load_experience` 取最后一个非空块。

**测试**：对 113 条经验做 before/after 对比——字段提取结果须一致或更全（双重包裹条目
新提取出字段视为「更全」）。

### D2. C2 ci check-failures 扫描路径修正

**问题**：`ci.py` 的 TC 覆盖检查硬编码 `project_root / "tests"`，不扫 `upstream/tests/`。

**修复**：扫描路径改为 `[project_root / "tests", project_root / "upstream" / "tests"]`，
与全量门禁 `pytest tests upstream/tests` 的路径一致。

**测试**：构造一个 TC-ID 只在 `upstream/tests/` 有实现的场景，断言覆盖率 > 0。

### D3. C3 YAML 回写保护

**问题**：`yaml.dump` 整体回写 `version.yaml` 等手写 YAML，丢注释 + 退化 block scalar + 重排键。

**修复**：新增 `_is_handwritten_yaml(path)` 检测函数——文件含 `#` 注释行或 `key: |`
block scalar 则判定为手写。对判定为手写的文件，禁止 `yaml.dump` 整体回写，
改用正则局部替换（或抛错提示手动改）。在 `experience.py` / `canon.py` 等
会回写 YAML 的入口加前置检查。

**测试**：构造带注释 + block scalar 的 YAML 文件，断言 `yaml.dump` 被拦截，
正则替换后注释保留。

### D4. C4 experience list/stats 无写副作用

**问题**：`experience list` / `stats` 会重写 `.experience-index.yaml`。

**修复**：list/stats 改为纯读——不从磁盘重建索引，只读现有 `.experience-index.yaml`。
若索引不存在或过期，打印 warning 提示跑 `experience reindex`（新子命令），
不自动重建。

**测试**：跑 `experience list` 后断言 `.experience-index.yaml` 的 mtime 不变。

### D5. C5 collect_local 水位线过滤

**问题**：每次 `--silent` 重传全库 113 条。

**修复**：`collect_local()` 读审计日志（`share-audit.yaml`）最近一次成功回传的
`experience_id` 列表，跳过已传的。新增 `--full` 标志强制全量重传。

**注意**：属行为变更——水位线缺失时回退到全量重传（不漏传）。须 D哥 确认。

**测试**：构造审计日志含 3 条已传记录，断言 `collect_local()` 只返回未传的。

## 限制

- D1 的 `parse_all_frontmatter` 不得改变单 frontmatter 文件的解析行为
- D2 的扫描路径不得引入新的误判（非 TC 文件不算覆盖）
- D3 的手写 YAML 检测不得误判纯机器生成 YAML（无注释、无 block scalar）
- D5 须保持 `FSTDD_NO_SHARE=1` 关闭能力不变

## 测试策略

| 切片 | TC | 测试什么 |
|------|-----|---------|
| S1 | TC-ELT-001..003 | D1 frontmatter 解析：单块不变 + 双块取内层 + 113 条 before/after |
| S2 | TC-ELT-004..006 | D2 ci 扫描路径：tests/ + upstream/tests/ + 假红消除 |
| S3 | TC-ELT-007..009 | D3 YAML 保护：检测手写 + 拦截 dump + 注释保留 |
| S4 | TC-ELT-010..011 | D4 读无写：list 后 mtime 不变 + reindex 子命令 |
| S5 | TC-ELT-012..014 | D5 水位线：跳过已传 + --full 强制 + 缺失回退全量 |
