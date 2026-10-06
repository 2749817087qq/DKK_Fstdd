# Spec: repo-hygiene

> Change: 2026-10-06-legacy-debt-cleanup | Auto-generated Human View

## Requirements

### Requirement: 非发布物目录 `_scratch/` SHALL NOT 被 git 跟踪。取消跟踪 SHALL 仅作用于**索引**
（`git rm --cached`），磁盘实体 SHALL 完整保留 —— 该目录是历史 change 明文保留的
`fstdd-fin/SKILL.md` 备份源。同时 SHALL 在 `.gitignore` 中忽略 `_scratch/`，
使其不再以 untracked 形态出现。


#### Scenario: SC-001

- **GIVEN** `_scratch/` 修复前有 27 个条目被 git 跟踪（含 2 个 mode 160000 的 gitlink：`_scratch/stdd-dev/stdd-repo`@5e3f9a3、`_scratch/upstream-cli-sync`@c383be7）
- **WHEN** 执行 `git ls-files _scratch/`
- **THEN** SHALL 输出为空
- **AND** 取消跟踪 SHALL 通过 `git rm -r --cached _scratch/` 完成
- **AND** SHALL NOT 使用不带 `--cached` 的 `git rm`（会删除工作树实体）

#### Scenario: SC-002

- **GIVEN** `_scratch/` 修复前有 27 条索引实体（25 x 100644 + 2 x 160000 gitlink），磁盘上均存在；其中 2 个 gitlink 的磁盘目录为**空目录**（从未 init 子模块）
- **WHEN** 在取消跟踪后清点 `_scratch/` 的磁盘实体
- **THEN** SHALL 使 27 条索引实体对应的磁盘实体全部仍在（数量与内容不变）
- **AND** 2 个 gitlink 的磁盘目录 SHALL 仍在（父仓引用解除，实体不动）
- **AND** 25 个普通文件实体 SHALL 全部仍在且非空（内容未丢失）
- **AND** SHALL NOT 出现任何 `_scratch/` 之外的已跟踪文件被删除

#### Scenario: SC-003

- **GIVEN** `_scratch/` 已取消跟踪
- **WHEN** 检查仓库根 `.gitignore` 并执行 `git status --porcelain`
- **THEN** SHALL 使 `.gitignore` 含忽略 `_scratch/` 的规则
- **AND** `git status --porcelain` 输出 SHALL NOT 出现任何 `_scratch/` 条目
- **AND** `upstream/tests/test_repo_home.py::test_a6_no_stray_untracked_files` SHALL 通过

#### Scenario: SC-004

- **GIVEN** 本 capability 的改动（取消跟踪 + gitignore）已完成，且未触碰 `_scratch/` 之外的文件
- **WHEN** 执行 `git status --porcelain` 与 `git ls-files _scratch/`
- **THEN** SHALL 满足三项同时成立：`git ls-files _scratch/` 为空、`_scratch/` 在 `.gitignore` 中、磁盘实体仍在
- **AND** 仓库体积相关：`_scratch/` 的 20MB SHALL NOT 再进入后续提交
- **AND** 本次 SHALL NOT 因取消跟踪而删除任何非 `_scratch/` 的已跟踪文件
