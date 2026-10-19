# 3.3.9+ — 经验静默回传出站收口 · 测试方案与详细案例

> 版本：`3.3.9+unreleased`（change `2026-10-18-share-egress-closure`）
> 创建日期：2026-10-18
> 对应 Phase 2 Spec：`specs/share-egress-closure/spec.md`（REQ-001 … REQ-006，SC-001 … SC-014）

## 一、测试策略

### 1.1 测试金字塔

| 层 | 占比 | 侧重 |
|---|---|---|
| 单元 | ~75% | 判据函数（`_verify_outbound` / `is_production_egress` / `_sanitize_text`）的逐形态真值表 |
| 集成 | ~20% | `publish()` 三档降级的审计条数、`silent_share()` 全链路（桩化 subprocess） |
| E2E | ~5% | **一次真实** `--silent` 打到隔离 inbox 目录，核对远端产物 |

### 1.2 测试原则

- **判据必须直接断言**，不靠副作用变红。审计 F8 指出：锁 Windows glob 的 4 个用例
  全靠 `_fake_run` 读 `dir/*` 抛异常才红，一旦 `_fake_run` 变容错就静默变绿。
- **修法禁区要写进用例**。`PUBLIC_DOMAINS` 放行必须有正向用例（SC-005），
  否则下次有人「顺手补齐域名分支」会把正常经验全剔掉。
- **测试不得写生产**。所有探针显式 `FSTDD_AUDIT_TEST=1`；出站一律桩化，
  真实 E2E 用 `FSTDD_INBOX_DIR` 指到隔离目录。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `tests/test_share_ssh_transport.py` | 51 | 单元 + 集成 | SC-001~011（pre_staged 校验、argv 形态、降级异常、配置面、审计分流、守卫） |
| `tests/test_exp_sync_sanitize_parity.py` | 37 | 单元 | SC-012（17 类形态逐条比对 + 委托断言 + 弱副本已删） |
| `tests/test_share_disabled_switch.py` | 9 | 单元 | SC-013 / SC-014（非法 UTF-8、子目录找根、注册表目录排除） |
| `tests/test_share_publish_sanitize.py` | 12 | 集成 | 四条出站通道的脱敏收口（TC-SOS-009/010/011） |
| `tests/test_share_hardening.py` | 15 | 集成 | SC-011（实跑 upstream 套件）+ 既有加固不变量 |
| `upstream/tests/test_silent_share.py` | 24 | 集成 | 零阻塞、目标锁死、内部异常不穿透 |
| `upstream/tests/test_inbox_endpoint.py` | 40 | 单元 | 端点协议、分批、重试 |

## 二、详细测试案例

### TC-CLOSURE-001（SC-001）索引文件不出站

- **前置**：tmp 目录含 `EXP-OK.md`（`sanitized: true`）、`README.md`、`SUBMIT.md`
- **动作**：`publish_via_scp(dir, pre_staged=True)`，`subprocess.run` 桩化
- **期望**：scp argv 的源文件列表 == `['EXP-OK.md']`
- **落点**：`tests/test_share_ssh_transport.py::test_pre_staged_filters_index_files_and_residual`

### TC-CLOSURE-002（SC-002）未脱敏被剔除并留痕

- **前置**：tmp 目录含 `EXP-LEFTOVER.md`（`sanitized: false` + 明文 token + 内网 IP）
- **动作**：同上
- **期望**：文件不出站；审计出现 `experience_id: EXP-LEFTOVER.md` / `result: skipped`
- **落点**：`::test_pre_staged_audits_rejected_entries`

### TC-CLOSURE-003（SC-002 后半）全被剔除不发空批次

- **期望**：返回 `(False, "...无可用文件...")`，且 `subprocess.run` 零调用
- **落点**：`::test_pre_staged_refuses_when_everything_rejected`

### TC-CLOSURE-004（SC-003）传输源恒为独立临时目录

- **期望**：`seen["src"].name.startswith("exp_verify_")` 且 ≠ 调用方目录
- **落点**：`::test_pre_staged_filters_index_files_and_residual`（断言段）

### TC-CLOSURE-005（SC-004 / SC-005）残余判据真值表

| 形态 | 期望 |
|---|---|
| `C:\Users\alice\secret.txt` | 拦 |
| `D:/work/private/x.md` | 拦 |
| `alice@example.com` | 拦 |
| `10.20.30.40` | 拦 |
| `db.internal` | 拦 |
| `/home/ubuntu/x` | 拦 |
| `ghp_` + 36×A | 拦 |
| `https://github.com/owner/repo` | **放** |
| `见 pypi.org/project/x` | **放** |
| `python.org` | **放** |

- **落点**：`tests/test_share_ssh_transport.py`（10 形态参数化）

### TC-CLOSURE-006（SC-006）三档降级只审计一遍

- **前置**：目录含 2 个会被剔除的文件；三档全部桩成失败
- **期望**：`_prepare_outbound` 调用 **1** 次；skipped 审计 **2** 条（改前 6 条）
- **落点**：`::test_publish_prepares_once_and_reuses_verified_dir`

### TC-CLOSURE-007（SC-007）`sent_count` 等于实际出站数

- **期望**：审计记录含 `sent_count`，值 == 通过校验的文件数
- **落点**：真实 E2E 核对（见本文件「二、详细测试案例」末节「真实端到端」）

### TC-CLOSURE-008（SC-008）并发写不丢记录

- **前置**：2 进程各写 100 条到同一 tmp 审计文件
- **期望**：保留 200 条
- **状态**：⚠️ **未自动化**。审计员用一次性探针测得改前丢 20%；改后未复测（见 test-report 已知缺口）

### TC-CLOSURE-009（SC-009）守卫六形态

| 形态 | 期望 |
|---|---|
| `run(["ssh","fstdd-hub",...])` | 拦 |
| `run("ssh fstdd-hub ...", shell=True)` | 拦 |
| `check_output(["ssh","fstdd-hub",...])` | 拦 |
| `call(["scp",...,"fstdd-hub:/tmp/"])` | 拦 |
| `check_call(["rsync","a","fstdd-hub:/x"])` | 拦 |
| `run([r"C:\...\ssh.exe","fstdd-hub","ls"])` | 拦 |

- **落点**：探针实测 6/6；`tests/test_share_ssh_transport.py::test_egress_guard_*`

### TC-CLOSURE-010（SC-010）不误伤

- **期望**：`is_production_egress(["ssh","ubuntu@fstdd-nonexistent-host.invalid",...])` == False
- **落点**：`::test_egress_guard_matches_only_production`（13 组参数化）

### TC-CLOSURE-011（SC-011）两种单跑都装守卫

- **期望**：`pytest tools/tests/` 与 `pytest upstream/tests/` 各自会话内 `is_installed() == True`
- **落点**：`::test_egress_guard_is_installed_in_this_session` + 手动探针

### TC-CLOSURE-012（SC-012）脱敏规则唯一事实源

- **期望**：17 类形态两套实现逐字节一致；`_SANITIZE_RULES is None`
- **落点**：`tests/test_exp_sync_sanitize_parity.py`（37 例）

### TC-CLOSURE-013（SC-001 / SC-007 / SC-006）真实端到端

- **命令**：
  ```
  FSTDD_INBOX_DIR=/home/ubuntu/_fstdd-e2e-verify FSTDD_AUDIT_TEST=1 \
    python tools/share_experience.py --silent
  ```
- **期望**：远端目录 90 文件、**无 README/SUBMIT**、残余命中 0、`sanitized:false` 0；
  审计 89 条 `target:scp / result:success / sent_count:90`；生产审计 0 条当日记录
- **清理**：`rm -rf /home/ubuntu/_fstdd-e2e-verify`

### TC-CLOSURE-014（SC-013 / SC-014）静默开关

- **落点**：`tests/test_share_disabled_switch.py`（9 例）

## 三、回归门禁

```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -m pytest tests upstream/tests -q
```

> ⚠️ 必须显式给路径。裸跑 `pytest` 会在 `upstream/examples/hello-stdd/tests/`
> 收集失败（`ModuleNotFoundError: src`），那是示例工程，不在门禁范围。
