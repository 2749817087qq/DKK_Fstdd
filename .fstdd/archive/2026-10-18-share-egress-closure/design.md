# 经验静默回传的出站收口闭合 - 技术设计

> change: `2026-10-18-share-egress-closure` ｜ 基线 `14a941c` ｜ 报告 `deliverables/gstack/pre-launch-check-fstdd-share-6d-2026-10-18.md`

## Context

`tools/share_experience.py` 是 DELIVER 阶段 Step 2.8 的静默回传实现：`silent_share()` 收集
本机经验 → 强制脱敏 → 写 `OUT_DIR` → `publish()` 三档降级（scp → github → endpoint）。
它**零交互、失败不告警**，唯一可信信号是 `.fstdd/share-audit.yaml`。

改造前的三条约束互相矛盾：

1. `pre_staged=True` 声称「调用方已脱敏」，于是直接 `return _scp_dir(out_dir, ...)`；
2. `_scp_dir` 用 `iterdir()` **全量枚举**目录；
3. `OUT_DIR` 就是活体经验库 `experiences/`，`silent_share()` 只写本轮文件、**不清空**目录。

三者叠加 ⇒ 目录里的历史残留连同 README/SUBMIT 一起出站，而审计记 `success`。
审计 F1 用受控探针复现了这一路径。

## Decisions

### 1. 把 `pre_staged` 的语义从「跳过整个收口」改为「只跳过脱敏动作」

**方案**：新增 `_prepare_outbound(out_dir, pre_staged) -> (dir|None, skipped)` 作为**唯一出口**：

| 分支 | 动作 |
|---|---|
| `pre_staged=False` | `stage_sanitized()`：脱敏 + `export_files()` 过滤 + 残余自检 |
| `pre_staged=True` | `_verify_outbound()`：**不脱敏**，但过滤 + 残余自检 + `sanitized:false` 拒绝，通过者 `copy2` 到 `exp_verify_*` |

四个包装器（`publish_via_scp` / `publish_via_inbox` / `_publish_github` / `publish_via_pr`）
全部改走它，且**返回的目录恒由本函数创建**，调用方 `finally` 清理。

**为什么**：`pre_staged` 的正当理由是「避免二次脱敏误伤占位符」（`<TOKEN>` 等），
这只涉及**脱敏动作**，与「是否校验」无关。把两者绑在一起，等于让一个性能优化顺带关掉了安全闸门。

**备选方案及排除原因**：
- 备选 A：`pre_staged=True` 时也跑一遍 `stage_sanitized` —— 会二次脱敏，且会重写整个目录，
  失去「不清理调用方目录」的既有语义。
- 备选 B：只加残余自检、不做过滤 —— README/SUBMIT 仍会出站（实测 16/25 个旧批次含它们）。

### 2. 三档降级改为入口单次校验 + `prepared=True` 直通

**方案**：`publish()` 在入口调一次 `_prepare_outbound()`，三档分别收到该目录并带
`prepared=True`，包装器据此**直通传输**（不再二次校验/二次拷贝）。

**为什么**：审计 M2 实测三档全失败时同一批剔除写 3 遍审计（4 → 12 条），并重复校验 3 次。
把「校验 + 审计」提到入口，语义上也更正确——**一次回传只应有一份校验结论**。

**备选方案及排除原因**：
- 备选 A：给 `_audit_skipped` 加去重 —— 只治审计膨胀，不治重复校验；且去重键会引入新状态。
- 备选 B：`publish()` 直接调 `_scp_dir` 等私有 sink —— 会打破「包装器是唯一入口」的既有不变量，
  测试替身也打不进去。

### 3. 残余判据只补 4 类，**故意不加通用外网域名**

**方案**：`OUTBOUND_RESIDUAL_RE` 新增 Windows 反斜杠路径 / Windows 正斜杠路径 / 邮箱 / IPv4 / 内网域名。

**为什么**：`sanitize()` 的域名规则**故意保留** `PUBLIC_DOMAINS`（github.com / python.org / pypi.org…），
并把已知 TLD 的非公开域名转成 `<DOMAIN>`。若残余判据加通用域名分支，正常经验文档里
每一个 `github.com` 都会被判为「残余」⇒ 整条剔除。**误杀不可逆**（EXP-20260915-B3）。

**备选方案及排除原因**：
- 备选 A：把 `SANITIZE_RULES` 整个搬进残余判据 —— 同上，公开域名会误杀。
- 备选 B：`pre_staged=True` 时跑 `sanitize()` 再比对差异 —— 语义正确但要重写目录，与决策 1 冲突。

### 4. 审计写锁用 `msvcrt.locking`，POSIX 不动

**方案**：`_append_locked()` 在 Windows 上锁首字节；POSIX 退化为普通 append。

**为什么**：审计 M3 实测 Windows `O_APPEND` 是「seek 到末尾再写」，跨进程非原子，
2 进程各写 100 条丢 40 条，**且无半行、无解析异常**（整条静默消失）。
POSIX 的 `O_APPEND` 本身原子，加锁只会增加复杂度。

**备选方案及排除原因**：
- 备选 A：独立锁文件 + `O_EXCL` 自旋 —— 多一个文件、多一套清理逻辑。
- 备选 B：改 SQLite —— 违反「审计是 append-only 文本、可 grep」的既有运维习惯。

### 5. 守卫打点选 `run` + `call`，**放弃 `Popen`**

**方案**：`install()` 包装 `subprocess.run` 与 `subprocess.call`（`check_output`→`run`、
`check_call`→`call` 自动覆盖），并用 `_normalize_args()` 处理 `shell=True` 字符串 argv、
`_prog_name()` 剥 `.exe`。

**为什么**：第一版把打点下移到 `Popen`（想一处覆盖全部），实测**全量门禁收集期即崩**：
`asyncio/windows_utils.py:125` 在 import 期 `class Popen(subprocess.Popen)` 继承它，
函数不可被继承 ⇒ `TypeError: function() argument 'code' must be code, not str`。

**代价**：直接 `subprocess.Popen(...)` 不被拦截。这是**已知缺口**，已写进 `install()` docstring。
当前仓库无此形态（已 grep 核实）。

## Architecture

```
silent_share(args)
  ├─ share_disabled()?  → 写 target:none/skipped → return 0
  ├─ collect_local() + prepare_entries(True)   # 强制脱敏
  ├─ 写 OUT_DIR（只写本轮，不清空）
  └─ publish(OUT_DIR, pre_staged=True)
       ├─ _prepare_outbound(OUT_DIR, True)      ← 单次校验 + 单次审计
       │    ├─ export_files()                   过滤 README/SUBMIT/非 .md
       │    ├─ OUTBOUND_RESIDUAL_RE             4 类新形态 + 原 6 类
       │    ├─ _declares_unsanitized()          parse_frontmatter 判定
       │    └─ copy2 → exp_verify_*             独立临时目录
       ├─ PUBLISH_SENT_COUNT = 文件数
       ├─ 三档降级（prepared=True 直通）
       │    ├─ publish_via_scp   → _scp_dir     argv: scp -r -- <files> host:dir/
       │    ├─ _publish_github   → _github_dir
       │    └─ publish_via_inbox → _post_inbox_dir
       │    （每档 try/except 收敛异常，不穿透）
       └─ finally: rmtree(exp_verify_*)

审计：record_audit(records, secrets) → _scrub → _append_locked(AUDIT_PATH)
      AUDIT_PATH 在 import 期由 _UNDER_TEST 常量决定（test / prod 分流）
```

## Risks

| 风险 | 缓解 |
|---|---|
| 补残余判据误杀正常经验 | 只补 4 类；`PUBLIC_DOMAINS` 显式放行；10 形态判定用例锁死 |
| `prepared=True` 被外部误用传任意目录 | 私有语义，仅 `publish()` 使用；docstring 明示「须来自 `_prepare_outbound()`」 |
| 文件锁影响零阻塞 | 拿不到锁就退化（不阻塞），整段仍在 `try/except` 内 |
| 守卫漏 `Popen` | docstring 显式声明；仓库内 grep 确认无该形态 |
