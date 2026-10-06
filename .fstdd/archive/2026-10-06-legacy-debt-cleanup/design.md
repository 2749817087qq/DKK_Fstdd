# 测试套件环境健壮性与遗留债务清理 — 技术设计

> change: `2026-10-06-legacy-debt-cleanup`｜mode: standard｜complexity_score: 6
> 观测基线：`observed_at=2026-10-06T21:28:59+08:00`、`observed_base_git_sha=4c6402e366eb3e4e75efafc3f50341b77b0f8fd4`

## Context

### 当前系统状态

- 本仓 = FSTDD 的 WorkBuddy 适配层与金融扩展。版本三轴：**E** 外部上游锚（v3.0.5）／**K** vendored 内核（`upstream/`，3.1.0）／**R** 本仓发行版（3.3.5）。
- 发布门禁 = **四自检脚本**（`verify_rename` 8 TC / `verify_eol` 7 TC / `verify_skill_standards` 7 TC / `verify_workbuddy_skills`）＋ **全量 pytest**（`upstream/tests` 851 用例 ＋ 仓库根 `tests/` 9 文件）。
- **权威门禁环境**（实测唯一全绿组合）＝ 控制台 UTF-8（`chcp 65001` + `[Console]::OutputEncoding=UTF8`）＋ `PYTHONUTF8=1` ＋ `PYTHONIOENCODING=utf-8`，结果 `906 passed / 54 skipped / 0 failed`。

### 技术栈与约束

- 运行面：Python 3.13（managed default env），pytest；Windows 主机（中文 locale，控制台默认 GBK/CP936）。
- 改动边界：**只动测试面 + 工具文档面 + 仓库卫生**；不碰生产代码、不碰 `.fstdd` 内核、不碰 CLI 运行时行为。
- 权限约束：`_scratch/` 是历史 change 明文保留的备份源 ⇒ 只能取消跟踪，**禁删磁盘实体**。

### 四个问题的实测根因

| # | 现象 | 根因（实测） |
|---|------|------------|
| 1 | 换环境就红（双向） | 36 处 `subprocess(..., text=True)` 不指定 `encoding=` ⇒ 解码走 `locale.getpreferredencoding()`。子进程输出 UTF-8 而主机 GBK 时炸；子进程输出 GBK（PowerShell）而 `PYTHONUTF8=1` 令其按 UTF-8 解时也炸 |
| 2 | 发布清单失真 + 根 tests 预存失败 | 清单写于根 `tests/` 迁移前；`test_L1_11` 硬编码 `== "3.3.0"`（自 3.3.1 起过期） |
| 3 | `canon verify` 1/2 | 归档 `proposal.md` 的 `source_hash` 未随 YAML 内容更新 |
| 4 | `_scratch/` 20MB 入库 | 从未加入 `.gitignore`；含 2 个 gitlink（内嵌 git 仓库）与 13.4MB 日志 |

## Decisions

### 1. 编码修复：逐点显式 `encoding=` 补齐，而非全局强制 UTF-8

**方案**：为 `upstream/tests/`、`tests/`、`tools/` 下 **16 文件 36 处** text-mode `subprocess` 调用逐点补 `encoding="utf-8", errors="replace"`。

**为什么**：
- 问题有**两个方向**（子进程输出 UTF-8 被 GBK 解 / 子进程输出 GBK 被 UTF-8 解）。全局环境变量只能压住一个方向 —— `PYTHONUTF8=1` 恰恰制造了第二个方向。逐点 `encoding=` 是唯一能同时压住两个方向的写法。
- 解码契约写在**调用点**，可用 AST 静态审计「未指定 encoding 的 text-mode 调用数 = 0」，把「人记得设环境」变成「机器可验证」。
- `errors="replace"`（U+FFFD）而非 `errors="ignore"`：替换字符**可观测**，不静默丢弃内容（EXP-2026-0014「静默降级」教训）。

**备选方案及排除原因**：
- 备选 A：在 `conftest.py` 设 `os.environ["PYTHONUTF8"]="1"` —— 只影响**之后新建**的子进程，压不住「子进程输出为 GBK」方向；且把门禁正确性重新绑回环境变量。
- 备选 B：`errors="ignore"` —— 静默丢弃解码失败内容，可能掩盖真实失败（正是本次要消除的「绿灯不可信」）。
- 备选 C：改 `text=False` + 手工 `.decode(...)` —— 改动面更大、可读性下降，且每个调用点都要重写后续 `.stdout` 用法，无收益。

### 2. 版本断言：改为动态读取单一事实源，而非跟随升版改字面量

**方案**：`tests/test_finance_content.py::test_L1_11` 由 `assert m.group(1) == "3.3.0"` 改为 —— 读取 `.fstdd/version.yaml` 的 `fstdd_version`，断言其**存在**、形如 `[0-9.]+`，且与 `.fstdd/config.d/project.yaml` 的 `stdd_version` **一致**。

**为什么**：硬编码把「版本一致性」降级为「人记得改」；该断言自 3.3.1 起已过期 5 个版本，实证会再犯。改为跨文件一致性断言后，**永久有效且更有价值**（同时锚定两处版本源不漂移）。

**备选方案及排除原因**：
- 备选 A：每升版手工改一次字面量 —— 注定再犯，且不增加任何保护。
- 备选 B：删除该用例 —— 丢失「`version.yaml` 必须含 `fstdd_version` 字段」的保护。

### 3. canon 哈希欠账：以 YAML 为唯一事实源，同步 MD 指纹

**方案**：把 `.fstdd/archive/2026-09-18-inbox-api-only-write/proposal.md` 的 `source_hash` 由 `16fa0e448d063e2a` 改为 YAML 的 `content_hash` = `29c0012fe4d0b612`。

**为什么**：V2.9.2 Canonical-First 下 **YAML 是唯一源头**，`proposal.md` 是渲染产物；其 `source_hash` 的语义是「渲染自哪个 YAML 版本」，不是独立事实。YAML 已被维护者修正过（命名合规修复），MD 未重渲染 ⇒ 补指纹即可。

**备选方案及排除原因**：
- 备选 A：反向改 YAML 去匹配 MD —— 会让 YAML 内容回退到旧值，且无从判断 MD 是否为正确渲染。
- 备选 B：不处理 —— `canon verify` 长期 1/2，门禁出现**永久噪声**，掩盖未来真实不一致。
- 备选 C：`canon generate` 重渲染 MD —— 归档目录不在 `canon generate` 的作用域（只覆盖 `changes/`），且重渲染会改写归档证据文件的时间戳注释，违背「归档只读」取向。故**只同步指纹，不改正文**。

### 4. `_scratch/` 取消跟踪：`git rm --cached` ＋ gitignore，绝不删磁盘

**方案**：`git rm -r --cached _scratch/`（27 条目，含 2 个 gitlink）＋ `.gitignore` 增加 `_scratch/`。

**为什么**：
- `_scratch/` 是 `2026-10-03-finance-integration` 明文保留的 `fstdd-fin/SKILL.md` **备份源** ⇒ `git rm`（不带 `--cached`）会连工作树一起删，**绝对禁止**。
- gitignore 是**必要第二步**：否则取消跟踪后 27 个文件变成 untracked，会撞 `upstream/tests/test_repo_home.py::test_a6_no_stray_untracked_files`（除 `.fstdd/changes/` 外不得有 untracked）。
- 2 个 gitlink（mode 160000 内嵌 git 仓库）用 `--cached` 仅解除父仓引用，磁盘实体不动。

**备选方案及排除原因**：
- 备选 A：`git rm -r _scratch/` —— 毁备份，禁止。
- 备选 B：只加 `.gitignore` 不 `--cached` —— **无效**：gitignore 不作用于已跟踪文件（仓库 `.gitignore` 内已有注释记录此坑）。
- 备选 C：写 `.git/info/exclude` —— 只对本机生效、不随仓库传播，协作节点仍会入库。

## Architecture

### 修复面 → 校验面 的闭环

```
                   ┌──────────────────────────────┐
   C1 编码修复 ────▶│ 16 文件 36 处 subprocess      │
   (16 files)       │   + encoding="utf-8",         │
                    │     errors="replace"          │
                    └───────────────┬──────────────┘
                                    │ 静态审计（AST）
                                    ▼
                    未指定 encoding 的 text-mode 调用 == 0
                                    │
                                    │ 动态验证（双环境）
                                    ▼
         ┌───────────────────────────────────────────────┐
         │ 环境 A 权威门禁（控制台UTF8+PYTHONUTF8=1）      │
         │   → 全量 pytest 0 failed                      │
         │ 环境 B 非 UTF-8（不设 PYTHONUTF8，控制台 GBK）  │
         │   → test_multi_platform 2 例不再 UnicodeDecodeError │
         └───────────────────────────────────────────────┘

   C2 清单/断言 ──▶ release-and-docs.md 纠错
                    test_L1_11 → 动态读 version.yaml
                          │
                          ▼
              断言：任意 fstdd_version 下 test_L1_11 通过

   C3 哈希补齐 ────▶ 归档 proposal.md source_hash ← YAML content_hash
                          │
                          ▼
              canon verify 2026-09-18-inbox-api-only-write == 2/2

   C4 仓库卫生 ────▶ git rm -r --cached _scratch/  +  .gitignore "_scratch/"
                          │
                          ▼
              git ls-files _scratch/ == ∅  ∧  磁盘 27 实体仍在  ∧  test_a6 通过
```

### 调用链（C1 的两种失败方向）

```
pytest (父进程)
   │
   ├─ subprocess.run([...], text=True)          ← 缺 encoding=
   │        │
   │        ├─ 子进程输出 UTF-8 ──▶ 父按 locale(GBK) 解 ──▶ UnicodeDecodeError: 'gbk' ... 0xae/0x8e   [方向 1]
   │        └─ 子进程输出 GBK   ──▶ PYTHONUTF8=1 令父按 UTF-8 解 ──▶ UnicodeDecodeError: 'utf-8' ... 0xce   [方向 2]
   │
   └─ subprocess.run([...], text=True, encoding="utf-8", errors="replace")   ← 修复后
            └─ 无论子进程输出何编码 ──▶ 确定性按 UTF-8 解，非法字节 → U+FFFD（可观测）
```

> 注：`errors="replace"` 只消除「**解码**噪声」，不改变子进程**语义**；真实失败仍以非 0 退出码 / 断言失败呈现，不会被吞掉。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 编码修复写成 `errors="ignore"`，静默丢弃内容掩盖真实失败 | 强制 `errors="replace"`；TC 断言扫描 `errors=` 取值，禁止 `ignore`（对应 EXP-2026-0014） |
| 36 处分散改动遗漏或改错调用语义 | 以 AST 清单逐文件核对「text-mode 未指定 encoding 数 == 0」；改动**只增参数**，不动 `args` / 断言 |
| 修复改变了用例数量（误删/误改） | `pytest --collect-only` 修复前后用例清单逐条比对，必须完全一致 |
| `canon verify` 修了 MD 指纹但 YAML 又被改，产生新不一致 | 以 `canon verify` 2/2 为验收断言；**只同步指纹、不改 YAML 正文** |
| `git rm --cached` 误写成 `git rm`，删掉备份实体 | 全程显式路径 + 仅 `--cached`；验收断言「磁盘 27 实体仍在」；操作前先记录实体清单 |
| 取消跟踪后 `_scratch/` 变成 untracked，撞 `test_a6` | 同批次加入 `.gitignore`；验收跑 `test_a6_no_stray_untracked_files` |
| 改发布清单措辞时顺手改动了清单其它条目语义 | 只改第 29 行那一处失真表述；其余逐字不动 |
