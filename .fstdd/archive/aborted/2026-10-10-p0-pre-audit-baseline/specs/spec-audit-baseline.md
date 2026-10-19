# spec: audit-experience-baseline — 经验库审计基线

**需求**: 只读量化经验库元数据失真，产出修复前基线

## SC-1 切块正确性
GIVEN 三段式真实 inbox 文件（注释+导出块+注释+真身块+正文）
WHEN 提取 frontmatter 块
THEN 识别全部块；真身块 = 含 experience_id 键的最后一个块（C-1 锚定）

## SC-2 当前解析器视角模拟
GIVEN 任一经验条目文件
WHEN 计算 missing_current
THEN 以「第一个 frontmatter 块」的键集合比对 experience_id/category/severity，与 experience.py:428 行为一致

## SC-3 结构分类
GIVEN 各类型文件
THEN 分类为：single_block / dual_block_import / exported_block_only / multi_block_N / no_frontmatter
（exported_block_only = 仅有导出块、真身块缺失）

## SC-4 eid 一致性（C-2 / 决策 D-3）
GIVEN 真身块存在 experience_id
WHEN 与文件名 stem 比对
THEN 不一致时计入 summary.eid_mismatch.files[]，该文件记录 eid_match=false
（真实案例：EXP-1BA44745.md 真身块 eid=EXP-1BE44745）

## SC-5 索引对账
GIVEN .experience-index.yaml 存在
WHEN 以真身块 eid 对账（非文件名）
THEN 输出 indexed_true / indexed_false_files / eid 不在索引中的文件清单

## SC-6 分类分布双视角
THEN summary 同时输出 category_distribution_current_parser 与 category_distribution_true，
作为 Phase 1.1 修复后 stats 命令的对比基准

## SC-7 只读与退出码
THEN 运行全程不写入仓库任何文件；退出码 0=完成 / 2=--repo 无效或 experiences 目录不存在
