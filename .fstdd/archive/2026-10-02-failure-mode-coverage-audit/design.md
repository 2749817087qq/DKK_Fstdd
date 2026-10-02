# 设计：14 类失败模式覆盖审计 + 缺口补齐

> **Change**: 2026-10-02-failure-mode-coverage-audit
> **Phase**: 2 SPEC (design)
> **Observed at**: 2026-10-02T16:10:00+08:00
> **Observed SHA**: 6b07721

---

## 0 审计结论

### 覆盖矩阵（14 类 → 6 有实装 + 8 仅文字）

| # | 失败模式 | CLI Guard | Skill 引导 | Hook 拦截 | 结论 |
|---|---|---|---|---|---|
| 1 | 幻觉调用（Hallucination） | ❌ | ✅ build.md | ❌ | ⚠️ 仅 skill 引导，无主动检测 |
| 2 | 过度信任 LLM（Overtrust） | ❌ | ✅ build.md | ❌ | ❌ 仅文字引用 |
| 3 | Prompt 注入 | ❌ | ✅ build.md | ❌ | ⚠️ 仅 skill 引导 |
| 4 | 记忆污染（Memory Pollution） | ❌ | ✅ build.md | ❌ | ❌ 仅文字引用 |
| 5 | 上下文窗溢出（Context Overflow） | ❌ | ✅ build.md | ❌ | ❌ 仅文字引用 |
| 6 | 工具参数漂移（Tool Drift） | ❌ | ✅ build.md | ❌ | ⚠️ 仅 skill 引导 |
| 7 | 凭证泄露（Credential Leak） | ✅ verify_notices.py | ✅ | ✅ Guard hook | ✅ **三層覆盖** |
| 8 | 权限绕过（Privilege Bypass） | ❌ | ✅ build.md | ❌ | ❌ 仅文字引用 |
| 9 | 并发竞态（Race Condition） | ❌ | ✅ build.md | ❌ | ❌ 仅文字引用 |
| 10 | 路径遍历（Path Traversal） | ✅ Guard _is_inside_project | ✅ | ✅ Guard hook | ✅ 二層覆盖 |
| 11 | 跨会话残留（Cross-Session State） | ❌ | ✅ build.md | ❌ | ❌ 仅文字引用 |
| 12 | 输出截断（Output Truncation） | ✅ Guard stdin 解析健壮性 | ✅ | ❌ | ⚠️ 仅 Guard 侧 |
| 13 | 格式错误（Malformed Output） | ❌ | ✅ build.md | ❌ | ⚠️ 仅 skill 引导 |
| 14 | 循环依赖（Circular Dependency） | ❌ | ✅ build.md | ❌ | ⚠️ 仅 skill 引导 |

### 三档评级

| 档 | 数量 | 类别 | 策略 |
|---|---|---|---|
| **A 档 · 有实装** | 6 | 1/3/6/7/10/12 | 审计后确认，无需补 |
| **B 档 · 仅 skill 引导（有价值但弱）** | 5 | 1/3/6/13/14 | 可选：加 hook 关键词检测或 CLI detect 子命令 |
| **C 档 · 仅文字引用（空洞）** | 3 | 2/4/5/8/9/11 | P0 缺口，必须补——至少加 skill 引导或 hook 轻量检测 |

---

## 1 修法

### 策略：**先补 skill 引导（最经济），再按需加 hook**

不追求 CLI detect 子命令（重、侵入式），优先 **skill 正文强化 + hook 轻量检测**。

### C 档 6 类：补 skill 引导段落

每类加一个 5 行块到 `build.md` 的"失败模式检查表"章节：

```markdown
| # | 失败模式 | 检查手段 |
|---|---|---|
| 2 | 过度信任 LLM | skill 引导：每次工具调用结果必须二次验证（AI 可能瞎编输出） |
| 4 | 记忆污染 | skill 引导：跨 Session 时清空 memory 上下文，避免旧污染 |
| 5 | 上下文窗溢出 | skill 引导：单文件 edit 控制 < 300 行；chunk 化大修改 |
| 8 | 权限绕过 | skill 引导：不得手动改 .fstdd.yaml 确认字段（Guard V3.0.5 硬阻断） |
| 9 | 并发竞态 | skill 引导：batch 操作串行化；避免同时推多个 change |
| 11 | 跨会话残留 | skill 引导：Phase 完成后清理 `.tmp` / `.scratch` 目录 |
```

### B 档 5 类：可选 hook 关键词检测

**只加 1 个 guard hook 函数**——轻量关键词匹配，不拦截只告警：

```python
# V3.0.10+: 失败模式轻量关键词检测（warn-only，不阻断）
_FAILURE_PATTERNS = [
    ("幻觉调用", re.compile(r"(?:import|from)\s+(?:nonexistent|fake|undefined)")),
    ("Prompt 注入", re.compile(r"(?:ignore previous|you are now|system prompt)")),
    ("工具参数漂移", re.compile(r"tool_input.*schema.*mismatch")),
    ("循环依赖", re.compile(r"circular import|recursive call")),
]

def _check_failure_patterns(hook_path, hook_content):
    """PreToolUse / PostToolUse hook 时扫描目标文件。
    发现失败模式关键词 → warn-only（不阻断）。"""
    hits = []
    for name, pat in _FAILURE_PATTERNS:
        if pat.search(hook_content or ""):
            hits.append(name)
    return hits
```

### 产出物

1. `coverage-report.md` — 14 类覆盖矩阵（本表 + 证据）
2. `build.md` — 6 类 skill 引导段落补充
3. `guard.py` — `_check_failure_patterns()` 轻量检测函数（可选）

---

## 2 测试计划（概要）

| TC | 内容 | 优先级 |
|---|---|---|
| TC-FMC-001 | coverage-report.md 每类有证据文件行号 | P0 |
| TC-FMC-002 | build.md 新增 6 类 skill 引导段落 | P0 |
| TC-FMC-003 | `fstdd guard` 保持原有功能零回归 | P0 |
| TC-FMC-004 | 可选 hook 检测：发现幻觉调用告警不阻断 | P1 |

---

## 3 不做什么

- **不写 CLI detect 子命令**（重、侵入式；Guard 是门禁不是检测，职责分离）
- **不追求 14/14 全 hook 拦截**（6 类本来就不需要主动拦截，skill 引导足够）
- **不修改 Guard 核心门禁逻辑**（Bug 1/2 修完就好）
