# test-report：2026-09-23-poll-daemon-499-fix

**change**：`2026-09-23-poll-daemon-499-fix`
**日期**：2026-09-23（收口补录 2026-10-03）
**结论**：🟢 通过（TC-1~TC-6 全绿）

> 本变更为**调用模式 / 自动化配置变更**，无可编译单元代码；GREEN 证据 = **演示轮 + 配置审计**，
> RED = 历史前台模式曾触发 499（2026-09-17 轮次 scp 2m18s）。TC-ID 与
> `specs/agent/499-prevention.md` 场景一一对应。

---

## 一、TC 执行矩阵

| TC-ID | 场景 | 期望结果 | 状态 | 证据 |
|-------|------|----------|------|------|
| TC-1 | 拉取走后台+await | 前台 turn 不被长传输阻塞，本轮无 499 | ✅ GREEN | 演示轮以 `run_in_background=true` 启动 scp + `TaskOutput` 等待 |
| TC-2 | scp 实际成功 | `scp` exit=0，文件落地 | ✅ GREEN | 演示轮 `ls` 目标目录 + 关键文件落地校验 |
| TC-3 | 负向对照 | 历史前台模式曾触发 499；新模式同耗时不再产生 | ✅ 对照成立 | 历史 2m18s → 网关 499；新模式同量级耗时无 499 |
| TC-4 | 对账/回执零回归 | 缺口自愈、最长延迟 ≤60min，无重复/漏发 | ✅ GREEN | 演示轮跑完第 0~4 步比对收/复计数 |
| TC-5 | pull_mode 审计 | 每轮记录 `pull_mode: background+await` | ✅ GREEN | 第 5 步自查字段落地 |
| TC-6 | SOP 存在且被引用 | 文件存在、prompt 含后台+await 铁律 | ✅ GREEN | `tools/fstdd003_daemon_499_sop.md` 存在（实测 `Test-Path` = True） |

## 二、修复落点（提交 `2be0960`）

| 项 | 落点 | 产物 |
|---|---|---|
| C1 | 守护自动化 prompt（06ec2c4f）新增「所有 scp/ssh 必须后台启动 + await」铁律，第 0/1/4 步示例加注 | `specs/code/daemon-prompt-patch.md` |
| C2 | 第 5 步自查追加 `pull_mode: background+await` 记录行 | 同上 prompt |
| C3 | 新增可操作 SOP | `tools/fstdd003_daemon_499_sop.md`（已存在） |

## 三、失败判定约定（防 499 噪声误判）

- 传输成败**只以文件系统为准**：`scp` exit=0 + 目标文件存在/md5 一致。
- 网关若仍出现 499 噪声，**不代表服务端失败**，不触发重试/告警风暴；
  仅当文件系统校验失败（exit≠0 或文件缺失）才判失败并上报。

## 四、范围外（不改动）

- 调度周期（HOURLY）、对账/自愈/紧急快通道逻辑均正常，不在本次范围。
- 共享池 :8787 可达性属基础设施（本轮实测 :22 通 / :8787 不通），与 499 根因无关。

## 五、偏离记录

无。严格按提案实施（见 `design-adjustments.md`）。