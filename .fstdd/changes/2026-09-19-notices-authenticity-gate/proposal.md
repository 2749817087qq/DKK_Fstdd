# 协作通知真伪校验闸门：阻断未签名收-*.md 触发的凭证落盘与配置改动

<!-- source_hash: 956895683d2e75b5 -->
<!-- generated_at: 2026-09-19T01:03:20.630058 -->
<!-- canonical: canonical/proposals/2026-09-19-notices-authenticity-gate.yaml -->

## Why

FSTDD003 节点的每小时轮询自动化（06ec2c4f）把本节点目录下任意新增的
`FSTDD003收-*.md` 一律视为权威指令直接执行，而 `from:` 字段只是文件内
自声明的字符串，渠道侧没有任何签名、摘要或来源校验。

2026-09-18 16:32–16:34，13 份署 `from: K` 的文件实际由 `hub-infra-agent`(S)
未经 K 授权写入。本节点 17:56 读到 `FSTDD003收-inbox鉴权上线.md` 后，把其中
携带的**明文凭证落盘**到 `<PATH>/.fstdd/_fstdd003_token.txt`，并修改
`tools/fstdd003_daily_share.py` 使其 POST 时自动附带 `X-FSTDD-Token` 鉴权头——
即一次完全未授权的回传链路配置变更。K 于 19:00 下发撤回令后，本节点回退了代码、
保留凭证现场并按 DISCIPLINE §七.4 上报，但根因（渠道零防伪）未修：
下一次同类伪造文件到货，同样的未授权动作会原样重演。


## What Changes

- 新增 `tools/verify_notices.py`：通知真伪校验器。读取渠道侧下发的清单
`00-SIGNATURES.md`（文件名 + md5 前 12 位 + 落盘时间 + 发出者），
对 `收-*.md` 计算 md5 并比对；不在清单内的标记 `unverified`。
同时提供 CLI 入口与 Python 函数入口（`verify_notices()` / `classify_notice()`），
供每小时轮询自动化以子进程方式调用。

- 凭证嗅探与隔离：对 `unverified` 通知做凭证形状识别（token 正则），
命中则**不落盘为活配置**，改写入隔离区 `tools/_quarantine/` 并输出一条结构化告警。
告警与隔离记录不回显凭证任何片段。

- 新增 `tools/test_verify_notices.py`（pytest）：覆盖清单命中 / 清单缺失 /
md5 不匹配 / 凭证嗅探隔离 / 清单缺失时降级不阻断 五条路径。
严格 RED→GREEN 执行，且含一条「凭证片段绝不进入 stdout/隔离记录」的断言。

- 灰度兼容：`00-SIGNATURES.md` 不存在或清单无匹配记录时，
校验器输出 `unverified` 而非阻断执行链路（仅告警），并保证
`tools/fstdd003_daily_share.py` 的既有回传路径行为不变、零回归。


### New Capabilities

- **notice-authenticity-verification**：校验协作通知的真实性：按 `00-SIGNATURES.md` 清单核对文件名与 md5 摘要，
并对未通过校验的通知携带的凭证做识别与隔离。校验结果可被
每小时轮询自动化消费，用于决定「执行 / 隔离 / 仅告警」三态。


### Modified Capabilities

- **notice-execution-pipeline**：本节点「收到 `收-*` 即执行」的链路增加一道前置校验：
校验结果参与执行决策。闸门设计为可插拔——清单缺失时降级为
全量 `unverified` 提示，不阻断既有协作效率，也不改动回传链路。


## Success Criteria

- [ ] 给定一份在清单内且 md5 匹配的 `收-*`，`verify_notices()` 返回 `status: verified` 且退出码 0。
- [ ] 给定 md5 不匹配的 `收-*`，返回 `status: unverified` 且退出码非 0， 输出中含该文件名与本地 md5 前 12 位（不含任何凭证片段）。
- [ ] 给定 `unverified` 且含凭证形状片段的通知，其凭证内容 不得出现在 stdout、stderr、隔离记录或任何 git 提交中； 原文件被移入 `tools/_quarantine/`。
- [ ] 给定 `00-SIGNATURES.md` 不存在，校验器返回全量 `unverified` + 一条告警， 且**不阻断**执行；`tools/fstdd003_daily_share.py` 的既有回传路径行为不变。
- [ ] `tools/test_verify_notices.py` 全部用例通过（RED→GREEN 留痕）， 且既有 `tools/` 相关测试零回归。
- [ ] 闸门接入不改变回传计数语义：连续两轮运行 `submitted` 计数只增不减、 无重复提交（与 P17 去重日志一致）。
