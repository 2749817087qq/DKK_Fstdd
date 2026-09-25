# Guard 相位门增加路径作用域 - 技术设计

## Context

STDD Guard 的 `cmd_guard_check`（`upstream/fstdd/cli/commands/guard.py`）判定链为：

1. `:700–706` 两道硬阻断（GATE token / `.fstdd.yaml` 确认字段）——**全局粒度**
2. `:711` agent runtime 目录豁免（`.workbuddy-ai/`）——按路径
3. `:717` `_find_active_change()` 取 ACTIVE_CHANGE 与相位
4. `:735` 只读相位下仅放行 change 内 YAML-first 流程产物
5. `:744–756` 相位 ∈ 可编辑集 ⇒ 放行
6. `:803–814` **否则无条件 `return 2`，全程不看目标文件路径**

第 6 步使相位门成为**全项目粒度**：ACTIVE_CHANGE 停在 understand/spec 时，
整个工作区（含与该 change 无关的文件、agent memory 日志）被冻结 ⇒
「ACTIVE_CHANGE 漂移 = 阶段劫持」（D哥 2026-09-25 实测）。

约束：两道硬阻断与 agent runtime 豁免**必须保持现状**；
YAML-first 流程产物放行（`:735`）行为不得改变。

## Decisions

### 1. 作用域声明来源 = canonical proposal 的新增 `scope:` 块

**方案**：在 `canonical/proposals/<change>.yaml` 增加可选块：

```yaml
scope:
  mode: strict          # strict = 声明了才收窄；缺省整个 change 无 scope
  paths:                # 相对项目根的路径模式（glob），可含目录
    - "upstream/fstdd/cli/commands/guard.py"
    - "upstream/tests/commands/test_guard.py"
    - "upstream/fstdd/cli/commands/*.py"
```

**为什么**：
- proposal 是 YAML-first 的流程产物，**AI 可写、人在 Gate 1 可审** ⇒ 作用域
  与需求变更在同一份文档里被确认，不用新增确认通道；
- 与 `what_changes` 并列但机器可读，`what_changes` 保持叙述性不变；
- 不动 `.fstdd.yaml`（该文件确认字段受硬阻断保护，且由 CLI 独占写入）。

**备选方案及排除原因**：
- 备选 A：从 `what_changes` / `tasks.md` 的叙述文字推断路径 —— 不可机器判定，
  误判即静默放行，风险不可接受；
- 备选 B：按 `git status` 的实际改动文件反向界定作用域 —— 因果倒置（门禁在改动
  之前判定），且会形成「改了即自动合法」的自我豁免；
- 备选 C：写入 `.fstdd.yaml` —— 该文件确认字段被硬阻断，需新增旁路，得不偿失。

### 2. 无 `scope:` 声明 ⇒ 维持现状（全局冻结）

**方案**：`scope` 块缺失或 `paths` 为空 ⇒ 完全走既有逻辑（`:803` 全局拦截）。

**为什么**：**fail-closed 优先于可用性**。历史上静默放开比误拦更危险
（参 skill 场景 D 的 fail-open 教训）。已有 change 与未来未声明 scope 的 change
不受影响，行为零漂移。

### 3. 范围外文件在只读相位 ⇒ warn-only 放行（`return 0`）

**方案**：非可编辑相位下，目标路径**不在**声明作用域内 ⇒ 打印警告并放行：

```
[STDD Guard] ⚠️ Phase 'understand' 不允许编辑，但目标文件不在 change 作用域内 — 放行
  active change: 2026-09-25-guard-phase-path-scope (phase: understand)
  target: docs/foo.md (out of scope)
```

**为什么**：warn-only 比静默放行安全（用户与模型都可见），
比全局拦截更符合「门禁只管它管的范围」的语义。

### 4. 路径匹配规则（与既有豁免判定一致）

- `os.path.normpath` 归一化后，尝试 `relative_to(project_root)`；
- 无法归一到项目根内（绝对路径越界、`..` 穿越出去）⇒ 视为**范围外**（warn-only 放行）；
- 匹配用 `fnmatch.fnmatch(rel, pattern)`，目录模式带 `/` 结尾时
  额外匹配其下所有文件；
- 大小写敏感性沿用 `fnmatch` 默认行为，不在本 change 中改变。

**为什么**：与 `_is_exempt_path` 的「先归一化再匹配」同一范式（skill 坑 1），
避免 `..` 穿越成为绕过口子。

### 5. 旧修订 guard.py 副本排查（W5.3，环境与本 change 解耦）

不改代码，只产出清单：本机存在 40,082 B、无 `_AGENT_RUNTIME_DIRS` 的旧副本
（`patchtest`、`FSTDD004` 内嵌仓等）。处置建议单独报 D哥 定，
不混入本次代码变更的 diff。

## Architecture

```
cmd_guard_check(args)
  ├─ hook_path = _read_hook_input()
  ├─ 硬阻断: GATE token / .fstdd.yaml 确认字段            → return 2   【不变】
  ├─ agent runtime 豁免 (.workbuddy-ai/)                   → return 0   【不变】
  ├─ active_dir, phase = _find_active_change()
  │    ├─ phase ∈ 只读 && YAML-first 流程产物              → return 0   【不变】
  │    ├─ phase ∈ EDITABLE_PHASES                          → return 0   【不变】
  │    └─ 【新增】phase ∈ 只读:
  │         ├─ change 未声明 scope                         → return 2   【= 现状，fail-closed】
  │         ├─ hook_path 归一化后 ∈ scope.paths            → return 2   【范围内仍拦】
  │         └─ hook_path 归一化后 ∉ scope.paths            → warn + return 0  【新】
  └─ 无 active flow → 既有 batch / assessment 逻辑         【不变】
```

新增辅助函数（均为纯函数，便于单测）：

```python
def _load_change_scope(change_dir: Path) -> list[str] | None:
    """读 canonical/proposals/*.yaml 的 scope.paths；无块/空列表 → None。"""

def _is_in_change_scope(project_root: Path, file_path: str, patterns: list[str]) -> bool:
    """归一化后判定目标路径是否落在声明作用域内。"""
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 声明过宽（如 `**/*.py`）≈ 回到全局放行，门禁被架空 | warn 行打印目标路径与命中模式；`stdd guard status` 显示作用域条目数供人复核 |
| 声明过窄导致正常流程内编辑被拦 | warn 只报「范围外放行」，不影响；范围内被拦时输出提示「请扩展 scope.paths」 |
| 未声明 scope 的旧 change 仍全局冻结 | 设计如此（fail-closed）；Gate 1 起新增提示，引导补声明 |
| `fnmatch` 不区分大小写导致误匹配 | 记录为已知局限，不在本 change 内扩大范围 |
| 硬阻断被误降级 | 硬阻断位于新增分支之前，且有独立回归用例锁定 |
