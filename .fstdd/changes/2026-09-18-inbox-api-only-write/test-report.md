# 测试报告 — 2026-09-18-inbox-api-only-write

> 生成日期：2026-10-04
> mode: standard | task_type: configuration | long_range: full_auto
> 交付分层：**A 仓库侧**（本机 pytest 可验）= 本报告的收口依据；**B 外部挂账**（生产 ssh 运维）= 不阻塞收口，随交付转 K。
> 证据基础：本 change 工作树（HEAD `67b36e0` + 未提交变更）。

## 一、覆盖总览

| 项 | 数值 |
|---|---|
| Spec 需求 | REQ-001..003 + REQ-101..102（5） |
| Spec 场景（SC） | SC-001..009 + SC-101..106（15） |
| 测试用例（TC） | 15（TC-IAOW-001..009 + TC-IBDP-001..006） |
| 本 change 新增 A 层测试 | 19（D 组 15 items + E 组 4） |
| 测试文件 | `upstream/tests/test_inbox_endpoint.py`（D/E 组新增） |
| **A 层 Scenario 覆盖** | **8/8 = 100%**（TC-IAOW-006/007/008/009 + TC-IBDP-002/003/004/006） |
| B 层（外部挂账） | 9 个 TC（见 §五） |

## 二、切片完成度

| 切片 | 覆盖 | TC | 新增测试 | 验证证据 | 状态 |
|---|---|---|---|---|---|
| 1 `inbox_server.py` 鉴权三态 | REQ-003 / SC-006..009 | TC-IAOW-006/007/008/009（4/4） | 15 | `.fstdd.yaml` slices_completed '1'（verified_at 2026-10-04T11:04:56+08:00） | ✅ |
| 2 `deploy_inbox_server.sh` 加固 | REQ-101/102 / SC-102..104 | TC-IBDP-002/003/004（3/3） | 4 | `.fstdd.yaml` slices_completed '2'（verified_at 2026-10-04T11:09:29+08:00） | ✅ |
| Part C 全量回归（非独立切片） | SC-106 | TC-IBDP-006 | — | §三 | ✅ |

## 三、测试执行结果（实测）

| 命令 | 结果 |
|---|---|
| `pytest upstream/tests/test_inbox_endpoint.py -q`（D/E 组单文件） | **64 passed / 0 failed** |
| `pytest upstream/tests -q`（全量回归，本 change 收口） | **906 passed / 54 skipped / 0 failed** |
| `pytest -k d1d`（DA-03 回归用例，RED 记录见下） | RED 时 `RemoteDisconnected`（TypeError 栈）→ GREEN 后 401 通过 |
| 覆盖率 `pytest --cov` | SKIPPED：本机未安装 pytest-cov（`quality.yaml.coverage.fail_under: 0`，非阻塞） |
| lint `ruff` / 类型 `mypy` | SKIPPED：本机未安装；且 `quality.yaml` 指向不存在的 `app/`（见 §五） |

**RED 留痕（DA-03）**：修复前 `test_d1d_non_ascii_token_header_rejected_gracefully` 实测
`http.client.RemoteDisconnected: Remote end closed connection without response`，服务端栈为
`TypeError: comparing strings with non-ASCII characters is not supported`（`tools/inbox_server.py:160`）；
改为 bytes 比较后恢复 GREEN。

## 四、失败模式检查（23 类，全量逐项）

| # | 失败模式 | 结论 |
|---|---|---|
| 1 | 幻觉调用 | ✅ 变更代码仅用 stdlib（`ipaddress`/`secrets`/`os`/`sys`）；评审代理确认无未 import / 未定义标识符 |
| 2 | 过度信任 LLM | ✅ 每步工具结果二次核验：RED 由真实 pytest 输出确认、GREEN 复跑、全量回归复跑 |
| 3 | Prompt 注入 | ✅ N/A：未改 system prompt / skill 定义；无 `ignore previous` 类痕迹 |
| 4 | 记忆污染 | ✅ 仅沿用本 change 事实（Phase 2 已确认状态），无旧 session 污染传播 |
| 5 | 上下文窗溢出 | ✅ 单文件 edit 均 < 300 行；大改 chunk 化 |
| 6 | 工具参数漂移 | ✅ 工具调用均按文档 schema，无自造参数 |
| 7 | 安全凭证泄露 | ✅ 全量回归含 `test_no_plaintext_credentials.py`（通过）；变更文件无 token/key 明文（仅 env 名与头名常量） |
| 8 | 权限绕过 | ✅ 未手改 Gate 字段；Gate 2 evidence 为真实 dialog 原文；Gate 3 未自跑 |
| 9 | 并发竞态 | ✅ 本档持 change 租约（`.lease.yaml`，F-A 主责）；单一 change 串行推进 |
| 10 | 路径遍历 | ✅ 文件操作均在 repo 内；部署脚本远端路径为固定常量 |
| 11 | 跨会话残留 | ✅ `_scratch/` 已 gitignored；未新增 `.tmp`；工作树无遗留垃圾（`test_a6` 通过） |
| 12 | 输出截断 | ✅ N/A：无 hook payload 截断场景；pytest/CLI 输出完整读取 |
| 13 | 格式错误 | ✅ `.fstdd.yaml` / canonical YAML / spec 全部 `yaml.safe_load` 通过 |
| 14 | 循环依赖 | ✅ 变更仅 stdlib import，无环 |
| 15 | 重复扣款 | ✅ N/A（非扣款接口）；同 `experience_id` 按 ID 覆盖写，重放幂等 |
| 16 | 账实不符 | ✅ `/health` received 口径 == 收目录根下 `*.md` 数（TC-IAOW-009 断言） |
| 17 | 静默降级 | ✅ 启动横幅显式 `auth: ON/OFF`；非法白名单项 stderr 显式告警（EXP-2026-0014） |
| 18 | 精度丢失 | ✅ N/A（无金额字段） |
| 19 | 审计缺口 | ✅ 401 / legacy-ip / 落盘均记 IP 与条数；部署后置校验逐条 PASS/FAIL |
| 20 | 状态机漏洞 | ✅ N/A（无状态机） |
| 21 | 额度穿透 | ✅ 限流在服务端按条数计（429 + Retry-After）；MAX_BATCH 服务端强制（已知问题见 §五） |
| 22 | 合规遗漏 | ✅ 服务端二次跑 `SENSITIVE_PATTERNS`（不信任客户端脱敏） |
| 23 | 过度工程 | ✅ 仅实现 spec 要求的最小三态；评审后 bytes 修复为最小改动；无新依赖/新抽象 |

## 五、经验库记录（C5）

本次失败模式检查沉淀 2 条**新**经验（`experience extract` 无自动命中，改为显式 `experience add` 并 `verify`）：

| 经验 ID | 类别 | 模式 | 状态 |
|---|---|---|---|
| EXP-2026-0018 | runtime_deviation | 服务端未消费请求体即响应错误码 → 客户端 TCP RST（WinError 10053） | verified |
| EXP-2026-0019 | runtime_deviation | `secrets.compare_digest` 比较含非 ASCII 的 HTTP 头 str → TypeError | verified |

另：切片实现时已复用时既有经验 EXP-2026-0014（静默吞异常→显式告警）与 EXP-2026-0013（声明形态 vs 实现 → parametrized）。

## 六、已知问题 + 未完成项

| # | 名称 | 原因 | 影响 | 处置 / 补完计划 |
|---|---|---|---|---|
| 1 | `ci check-failures` (d) 重复 TC-ID | 工具口径：按**全文出现次数**判定，test-plan.md 每 TC 在「分层映射表」与「详细案例」各出现一次 | 全部 15 个 TC 被误报重复 | **已知工具口径问题**：已核实既往 `2026-09-19-notices-authenticity-gate`（已交付）test-plan.md 同样触发（TC-NAV-001 出现 6 次等），非本 change 缺陷；不改工具、如实记录 |
| 2 | `ci check-failures` TC 实现覆盖 0/15 | 工具口径：CLI 硬编码扫描 `<root>/tests`，本仓测试在 `upstream/tests` | 覆盖显示 0% | **已知工具口径问题**：A 层 8 个 TC 均有对应测试函数（§一/§三实测），建议另立 change 扩展扫描路径 |
| 3 | `ci check-failures` (g) AND 超限 warn | 工具口径：按**整文件**统计 `**AND**` 行数而非按 Scenario | 2 个 spec.md 报警 | 已知口径问题，非本 change 引入 |
| 4 | B 层 9 项外部挂账 | 本机与生产 `43.134.236.80` 不互通，无法代跑 | A 层收口不受阻 | 随交付说明转 K 人工执行并回执：TC-IAOW-001..005、TC-IBDP-001/002(端上)/004(端上)/005 |
| 5 | `--rate-limit` CLI 覆写后未复检 `MAX_BATCH<=RATE_LIMIT` | **预存在**（非本 change 引入）：模块级 assert 仅在 import 时以默认值 120 校验 | `--rate-limit <50` 时批量恒 429 | 记录为已知问题，建议另立 change 在 `main()` 覆写后复检 |
| 6 | deploy verify 段以 `curl -H` 传 token 短暂暴露于远端进程表 | B 层脚本设计（需读 env 取 token） | 低危（仅端上本地可见） | 记录，K 端上可评估改用 `curl --config` 或临时 0600 文件 |
| 7 | `quality.yaml` 路径项与本仓布局不符 | **预存在**：`lint: ruff check app/ tests/`、`typecheck: mypy app/` 指向不存在的 `app/`；`unit_dir: tests/` 与实际的 `upstream/tests` 不一致 | lint/typecheck 无法按配置执行 | 记录为已知问题，建议另立 change 校正配置路径 |

## 七、设计偏离

Phase 3 记录 DA-02/DA-03/DA-04（均为连接层/健壮性/测试口径，不改变对外接口与行为语义）；
Phase 2 已登记 DA-01（实现口径：契约冻结 + 仓库自主实现 + 部署收敛）。
完整清单见 [design-adjustments.md](design-adjustments.md)。

## 八、C1 多路评审发现处置

| 来源 | 发现 | 处置 |
|---|---|---|
| 代码代理 | 非 ASCII 凭证头致 `compare_digest` TypeError | **已修**（DA-03）+ 回归用例 |
| 代码代理 | `--rate-limit` 覆写未复检 | 已知问题 #5（预存在，另立 change） |
| 代码代理 | deploy 未校验 env 可被服务用户读取 | 复核后**驳回**：systemd 以 root 读取 `EnvironmentFile`，无需服务用户可读 |
| 代码代理 | deploy 用 `curl -H` 传 token | 已知问题 #6（B 层） |
| 测试代理 | 静态守护断言为全局子串匹配 | 记录为**已知局限**（DA-04）；静态文本守护天然为粗网 |
| 测试代理 | TC-IBDP-006 无独立函数 | 该 TC 定义为「全量回归」，由 §三 承载，非函数级 |
| 文档代理 | change 内 `.canon-index.yaml` 失真 | **已修**：索引改为指向 4 个真实 capability 文件 |
| 文档代理 | `specs/agent/2026-09-18-*.yaml` 为未填模板 | **已删**（孤儿脚手架，真实 agent 规格为 2 个 capability 文件） |
| 文档代理 | `code-structure-delta.md` 正文空白 | **已补**变更文件清单 |
| 文档代理 | `.fstdd.yaml` traceability 全 0 / tasks 未勾 | **已修**（traceability 5/15/15/19；tasks 全勾） |
| 文档代理 | test-plan §五 与 §零/§三 矛盾 | **已修**（改为「已随切片 1 实现并通过」） |

## 九、结论

- A 层 8/8 TC 覆盖 100%；本 change 单文件 **64 passed**；全量回归 **0 failed**。
- 23 类失败模式全量检查完成，无未处置的 critical/high。
- 已知问题 6 项均已逐条给出原因/影响/处置，其中 #1/#3 为**系统性工具口径问题**（已验证既往已交付 change 同样触发）。
- B 层 9 项外部挂账不阻塞收口，随交付转 K。
- **A 仓库侧就绪 Gate 3**，风险等级：低。