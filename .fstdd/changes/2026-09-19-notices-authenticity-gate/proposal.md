# 协作通知真伪校验闸门：阻断未签名收-*.md 触发的凭证落盘与配置改动

<!-- source_hash: f30f0ba9064b5d82 -->
<!-- generated_at: 2026-09-19T01:15:07.133632+00:00 -->
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
提供两个 Python 入口：`classify_notice(path)` 判定单个文件，
`verify_notices(dir)` 批量扫描并返回结构化结果；
以及一个 CLI 入口 `--json`（机器消费）/ 默认人类可读输出，
附 `--strict` 开关（默认关闭）——strict 时 `unverified` 以非零退出码阻断，
非 strict 时 `unverified` 仅告警、退出码为 0。
退出码契约：0 = 可继续（含非 strict 下的 unverified）；2 = 文件被隔离；
3 = strict 模式下发现 unverified。

- 凭证嗅探与隔离：对 `unverified` 通知做凭证形状识别（token 正则），
命中则**不落盘为活配置**，改移入隔离区 `tools/_quarantine/` 并输出一条结构化告警。
告警与隔离记录不回显凭证任何片段（只记文件名、md5 前 12 位、命中规则名）。
子项：`.gitignore` 追加 `tools/_quarantine/`，确保隔离内容永不进入 git 历史。

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

- [ ] 清单内且 md5 匹配的 `收-*`：`classify_notice()` 返回 `status: verified`， CLI 退出码 0。
- [ ] md5 不匹配的 `收-*`：返回 `status: unverified`，输出含该文件名与本地 md5 前 12 位、 不含任何凭证片段；默认（非 strict）退出码 0，`--strict` 退出码 3。
- [ ] `unverified` 且含凭证形状片段的通知：凭证内容不出现在 stdout、stderr、 隔离记录或任何 git 提交中；原文件被移入 `tools/_quarantine/`， 隔离记录仅含文件名 + md5 前 12 位 + 命中规则名；CLI 退出码 2。
- [ ] `00-SIGNATURES.md` 不存在时：全部标记 `unverified` + 一条告警，退出码 0（不阻断）， 且 `tools/fstdd003_daily_share.py` 的既有回传路径行为不变、零回归。
- [ ] `tools/test_verify_notices.py` 全部用例通过（RED→GREEN 留痕）， 且既有 `tools/` 相关测试零回归。
- [ ] 误隔离上界可测：对 fixtures 中的 5 份已知格式真实通知（含协作通知、撤回令、 回执各至少 1 份）运行校验器，隔离数为 0。
- [ ] `tools/_quarantine/` 已被 `.gitignore` 覆盖： `git check-ignore -v tools/_quarantine/x` 返回非空且退出码 0。
- [ ] 回传计数语义不变：连续两轮运行 `submitted` 计数只增不减、无重复提交 （与 P17 去重日志 `.fstdd/_fstdd003_share_log.json` 一致）。
