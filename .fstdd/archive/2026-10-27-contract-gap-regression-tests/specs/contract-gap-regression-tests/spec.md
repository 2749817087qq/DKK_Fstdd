# contract-gap-regression-tests — Capability Spec

> Change: 2026-10-27-contract-gap-regression-tests
> Task Type: code
> 观测基线: git 5c5c40dc6ab506c494714d2f8815ba10e151b854

## 一、能力范围

本 capability 提供 **contract_gap 三类攻击向量的回归测试**，锁定已有代码修复不被未来重构回退。
**不修改代码，只加测试**。

### 1.1 覆盖的攻击向量

| EXP-ID | 攻击向量 | 修复位置 | 修复形态 |
|--------|---------|---------|---------|
| EXP-2026-0027 | 词法前缀比较判定路径安全，`..` 逃逸 archive 守卫 | `finder.py:104` | `hit.resolve().relative_to(archive_root.resolve())` |
| EXP-2026-0031 | Python 3.11+ 内联 `(?i)` 在多段拼接 regex 中导致 import 崩溃 | 全仓 0 残留 | 改用 `re.compile(pat, re.IGNORECASE)` |
| EXP-2026-0032 | 字符白名单 `[\w./-]+` 允许 `..` 组合逃逸 | `finder._resolve_in` | `Path(name).parts` 段级判据拒绝 `..` |

## 二、Requirements

### Requirement: `_resolve_in` 输入层拒绝逃逸
> 每个 `_resolve_in(base_dir, name)` 调用 MUST 拒绝含路径分隔符 / `..` / 绝对路径 / 空 name 的输入。

#### Scenario: 拒绝包含路径分隔符的 name
**GIVEN** 一个正常的 `base_dir`（含 `.fstdd.yaml` 的 change 目录）
**WHEN** 调用 `_resolve_in(base_dir, "foo/bar")`
**THEN** SHALL 返回 `None`，不解析任何目录
**AND** SHALL NOT 抛出异常

#### Scenario: 拒绝包含 `..` 的 name
**GIVEN** 一个正常的 `base_dir`
**WHEN** 调用 `_resolve_in(base_dir, "..")` 或 `_resolve_in(base_dir, "foo/..")` 或 `_resolve_in(base_dir, "../bar")`
**THEN** SHALL 返回 `None`
**AND** SHALL NOT 让 `base_dir / name` 逃逸出 `base_dir`

#### Scenario: 拒绝空 name 与 `.`
**GIVEN** 一个正常的 `base_dir`
**WHEN** 调用 `_resolve_in(base_dir, "")` 或 `_resolve_in(base_dir, ".")`
**THEN** SHALL 返回 `None`

#### Scenario: 允许合法 change 名
**GIVEN** `base_dir/foo-bar-2026-10-27/` 存在且含 `.fstdd.yaml`
**WHEN** 调用 `_resolve_in(base_dir, "foo-bar-2026-10-27")`
**THEN** SHALL 返回该目录 Path 对象
**AND** SHALL NOT 返回 `None`

### Requirement: archive 守卫使用 `resolve()` 归一化判定
> 判定"目标是否在 archive 下"的逻辑 MUST 用真实路径比较（`resolve().relative_to()`），禁止字符串部件比较。

#### Scenario: archive 目录下的路径被识别为归档态
**GIVEN** `hit = project_root / ".fstdd" / "archive" / "some-change"`（真归档路径）
**WHEN** 执行 `hit.resolve().relative_to(archive_root.resolve())`
**THEN** SHALL NOT 抛出 `ValueError`
**AND** SHALL 判定为归档态

#### Scenario: changes 目录下的路径被识别为在办
**GIVEN** `hit = project_root / ".fstdd" / "changes" / "some-change"`（在办路径）
**WHEN** 执行 `hit.resolve().relative_to(archive_root.resolve())`
**THEN** SHALL 抛出 `ValueError`
**AND** SHALL 判定为在办态

### Requirement: 全仓无内联 `(?i)` 拼接 regex
> 任何 `re.compile` / `re.search` / `re.match` / `re.findall` 调用 MUST NOT 在多段字符串拼接中夹带内联 `(?i)` 标志。

#### Scenario: 扫描全仓 (?i) 残留
**GIVEN** 遍历 `upstream/fstdd/**/*.py`（剔除 `__pycache__`）
**WHEN** 用正则 `re.search(r'\(\?i\)', source)` 扫描每个文件
**THEN** SHALL 匹配数为 0

#### Scenario: 模块 import 不崩溃
**GIVEN** 遍历 `upstream/fstdd/cli/commands/*.py`
**WHEN** 用 `importlib.util.spec_from_file_location` 尝试 `re.compile` 所有模块级 `re.compile(...)` 常量
**THEN** SHALL NOT 抛出 `re.PatternError`
