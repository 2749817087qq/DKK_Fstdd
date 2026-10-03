# 2026-10-03-share-publish-sanitize 测试方案与详细案例

> 版本：v3.2.0（change 级）
> 创建日期：2026-10-03
> 对应 Phase 2 Spec：canonical/specs/code/2026-10-03-share-publish-sanitize.yaml（REQ-001..004 / SC-001..012）

## 一、测试策略

### 1.1 测试金字塔

- **单元（主）**：`stage_sanitized()` 的脱敏/保留/不改原目录/自检剔除/判据常量，
  以及 4 个拷贝点「源为 stage」的断言——全部用 tmp_path + 可观测桩，零外部依赖。
- **集成（次）**：`publish_via_inbox()` 指向本地 stub 端点（http.server），
  校验真正发出的 POST body 无残留。
- **E2E（轻）**：`--export --publish --silent` 端到端一次，校验零阻塞退出码 + 审计留痕
  （走真实链路或本地 FILE 远端降级）。

### 1.2 测试原则

- 断言**内容**而非「调用成功」：直接断言 staged 文本不含/含指定模式（EXP C3 教训）。
- 第二道防线**直接断言其自身判据**，不只看行为结果（EXP C4 教训）。
- 声明与实现同源：`OUTBOUND_RESIDUAL_RE` 判据用「声明样例」参数化输入校验（EXP-2026-0013 教训）。
- 不触达真实服务器 / GitHub：外部通道一律桩化，保证离线可跑、可重复。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| tests/test_finance_content.py | ~15 | 静态/集成 | L1 静态内容断言（与本次无交集，仅作回归基线） |
| tests/test_install_smoke.py | ~5 | 集成 | install 链路冒烟 |
| tests/conftest.py | - | 夹具 | 公共 fixture |
| tests/run_release_validation.py | - | runner | L0-L7 分类执行入口 |

## 二、详细测试案例

### 功能 1：出站强制脱敏（REQ-001）

#### 案例 1.1 — POSIX 家目录路径被清除

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-001 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-001 |
| **优先级** | P0 |
| **预置条件** | tmp out_dir 含 1 个正文含 `/home/ubuntu/fstdd-skills/inbox/` 的 .md |
| **输入** | 调用 `stage_sanitized(out_dir)`，读 staged 对应文件 |
| **预期结果** | 内容不匹配 `/(?:home|Users)/`；原文件保持原样 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 凭证片段被替换

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-002 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-002 |
| **优先级** | P0 |
| **预置条件** | out_dir 含正文含 `ghp_...`/`github_pat_...`/`sk-...`/`Bearer ...` 的文件 |
| **输入** | `stage_sanitized(out_dir)` |
| **预期结果** | 出现 `<TOKEN>`；原文凭证串不再出现 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.3 — 正常标识符不被误伤（语义保持）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-003 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-003 |
| **优先级** | P1 |
| **预置条件** | out_dir 含正文含 `README.md`、`sqlite3.connect`、`https://github.com/x/y` |
| **输入** | `stage_sanitized(out_dir)` |
| **预期结果** | 三者原样保留 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.4 — 原目录不可变

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-004 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-004 |
| **优先级** | P1 |
| **预置条件** | out_dir 含 N 个文件（含 1 未脱敏样本），记录快照哈希 |
| **输入** | `stage_sanitized(out_dir)` |
| **预期结果** | 文件数不变、逐字节不变；staged 目录不在 out_dir 内 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.5 — frontmatter sanitized 声明修正

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-005 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-005 |
| **优先级** | P2 |
| **预置条件** | out_dir 含 `sanitized: false` 的文件 |
| **输入** | `stage_sanitized(out_dir)` |
| **预期结果** | staged frontmatter 为 `sanitized: true`；正文除脱敏外不变 |
| **当前状态** | ❌ 测试缺 |

### 功能 2：出站残余自检（REQ-002）

#### 案例 2.1 — 残余命中条目被剔除且报告

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-006 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-006 |
| **优先级** | P1 |
| **预置条件** | 构造 sanitize 后仍含 `/home/` 残留的文本（monkeypatch 使 sanitize 不对其生效） |
| **输入** | `stage_sanitized(out_dir)` |
| **预期结果** | 该文件不在 staged；`skipped` 含文件名与原因 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — 自检判据常量可直接断言

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-007 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-007 |
| **优先级** | P1 |
| **预置条件** | `OUTBOUND_RESIDUAL_RE` 已定义 |
| **输入** | 对常量本身 search `x /home/u y` 与 `/homework/x` |
| **预期结果** | 前者命中、后者不命中（与服务端判据一致） |
| **当前状态** | ❌ 测试缺 |

### 功能 3：四条路径收口（REQ-003）

#### 案例 3.1 — inbox POST body 无残留

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-008 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-008 |
| **优先级** | P0 |
| **预置条件** | 本地 stub HTTP 端点；out_dir 含未脱敏样本 |
| **输入** | `publish_via_inbox(out_dir, stub_url)`，捕获收到的 body |
| **预期结果** | body 不含 `/(?:home|Users)/` 与凭证；stub 返回成功 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — scp 源为 stage

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-009 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-009 |
| **优先级** | P1 |
| **预置条件** | monkeypatch `subprocess.run` 捕获 scp 参数与源目录内容 |
| **输入** | `publish_via_scp(out_dir, ...)` |
| **预期结果** | 被传输源为 stage 目录（内容已脱敏），非原始 out_dir |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.3 — GitHub 直推拷贝源为 stage

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-010 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-010 |
| **优先级** | P1 |
| **预置条件** | 桩化 git clone/push；scp 桩返回失败以进入 GitHub 分支 |
| **输入** | `publish(out_dir, repo, token)` |
| **预期结果** | 拷入目标 repo 的经验文件无残留 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.4 — fork+PR 拷贝源为 stage

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-011 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-011 |
| **优先级** | P1 |
| **预置条件** | 桩化 `_gh_api` 与 git；out_dir 含未脱敏样本 |
| **输入** | `publish_via_pr(out_dir, repo, token)` |
| **预期结果** | 复制进 PR 分支的文件无残留 |
| **当前状态** | ❌ 测试缺 |

### 功能 4：零阻塞与留痕（REQ-004）

#### 案例 4.1 — 静默入口零阻塞 + 审计留痕

| 字段 | 内容 |
|------|------|
| **ID** | TC-SOS-012 |
| **对应 Spec** | share-outbound-sanitize → Scenario SC-012 |
| **优先级** | P2 |
| **预置条件** | 隔离的临时 repo 根；远端用本地/file:// 降级 |
| **输入** | `python tools/share_experience.py --export --publish --silent` |
| **预期结果** | 退出码 0；`.fstdd/share-audit.yaml` 存在且记录 result/reason |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| stage_sanitized 脱敏/保留/不变/自检 | TC-SOS-001..007 | - | - | 🔴 待补 |
| publish_via_inbox 收口 | - | TC-SOS-008 | - | 🔴 待补 |
| publish_via_scp / publish / publish_via_pr 收口 | TC-SOS-009..011 | - | - | 🔴 待补 |
| 零阻塞 + 审计 | - | - | TC-SOS-012 | 🔴 待补 |

## 四、回归风险矩阵

| 风险区域 | change 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| share_experience 出站函数签名 | 内部调用改为 stage 目录；对外签名不变 | TC-SOS-008..011 + silent_share 端到端 | 🟡 |
| inbox_pull.py（复用 publish/export_files） | publish 内部收口，STAGING_DIR 再脱敏一次 | 幂等（sanitize 幂等），无重复副作用 | 🟡 |
| sanitize 误伤正文 | 规则未改（复用同源） | TC-SOS-003 固定样本断言 | 🟢 |
| 临时目录泄漏 | 新增 stage 临时目录 | try/finally 清理 + 测试断言无残留 | 🟡 |

## 五、建议补充顺序

1. **第一优先**（部署前必补）：TC-SOS-001、TC-SOS-002、TC-SOS-008（核心脱敏不变量 + 真实外发通道）
2. **第二优先**（部署后尽快补）：TC-SOS-003、004、006、007、009、010、011
3. **第三优先**（后续补）：TC-SOS-005、TC-SOS-012

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 未脱敏样本被服务端拒收（contains POSIX home path） | 2026-10-03T18:50:00+08:00 | 066b9f629d21547670a38a375e28e815794e17bd | 服务器 inbox 服务端日志 / share-audit.yaml |
| sanitize() 对该样本可清除全部 /home/ 匹配 | 2026-10-03T18:50:00+08:00 | 066b9f629d21547670a38a375e28e815794e17bd | 本机只读实测 sanitize(text, True) |
| 服务端判据 `/(?:home|Users)/[^\s/]+` | 2026-10-03T18:50:00+08:00 | 066b9f629d21547670a38a375e28e815794e17bd | inbox_server.py L288 |

- `observed_at` 是信息采集时刻，非文档生成时刻。
- 缺 `observed_at` 的证据时效判为「无法判定」。