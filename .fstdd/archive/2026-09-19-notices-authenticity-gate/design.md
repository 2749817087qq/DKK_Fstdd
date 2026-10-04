# 协作通知真伪校验闸门：阻断未签名收-*.md 触发的凭证落盘与配置改动 — 技术设计

> change: `2026-09-19-notices-authenticity-gate` ｜ mode: thorough ｜ anchoring: L3
> 文件域：`D:\FSTDD003\tools\` + `.gitignore`（其余一律不动）

## Context

**当前系统状态**

- 本节点（FSTDD003）通过每小时轮询自动化 `06ec2c4f` 从云服务器 `ubuntu@<IP>:/home/ubuntu/fstdd-notices/FSTDD003/` 拉取协作通知 `FSTDD003收-*.md`，拉到即执行并回传三件套。
- `from:` 字段是通知文件内的自声明字符串，渠道侧**没有任何签名、摘要或来源校验**。
- 2026-09-18 16:32–16:34 有 13 份署 `from: K` 的文件实为 `hub-infra-agent`(S) 未经 K 授权写入。本节点 17:56 读到 `FSTDD003收-inbox鉴权上线.md` 后落盘了其中明文凭证到 `.fstdd/_fstdd003_token.txt`，并修改 `tools/fstdd003_daily_share.py` 使其 POST 附带 `X-FSTDD-Token` —— 一次完全未授权的回传链路配置变更。
- K 于 19:00 下发撤回令，本节点已回退代码、保留凭证现场并按 DISCIPLINE §七.4 上报。但**根因（渠道零防伪）未修**。
- 协商文件 `FSTDD003复-伪造署名事件处置与开放问题协商.md` 已于 2026-09-19 01:02 scp 给 K（md5 `828320d2f4d2eb51`），Q2 请 K 侧建立 `00-SIGNATURES.md` 清单机制。

**技术栈与约束**

- Python 3.13，隔离 venv `C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default`（含 PyYAML/Jinja2/pytest）。
- `tools/` 现有 5 个脚本：`fstdd003_daily_share.py` / `inbox_server.py` / `install_workbuddy_skills.py` / `share_experience.py` / `verify_workbuddy_skills.py`。**无既有测试文件**（`tools/test_*.py` 不存在），无既有测试资产可复用。
- `.gitignore` 现有条目：`experiences/`、`.fstdd/share-audit.yaml`、`.claude/settings.local.json`、`__pycache__/`、`*.pyc`、`.fstdd/_fstdd003_token.txt`。
- 仓库 remote 数 = 0，永不 push。禁 `git add -A`（会暂存 `_scratch/stdd-dev/` 25MB 基线与内嵌 git 仓库）。
- `fstdd` CLI 必须经 venv python + `$(cygpath -m ...)` 调用（P15）。

**已知会干扰本变更的工具缺陷**

- **P12**（两次复现）：`fstdd canon generate` 的 Human View 只渲染 5 段（丢 constraints/stakeholders/risk_areas/non_goals/critical/anchoring）；`extract-proposal --format json` 的 `capabilities` 返回空数组、`what_changes` 只取到每个 block scalar 的首行、`constraints` 返回空。**本设计的输入一律以 canonical YAML 为准，不采信 CLI 提取结果。**
- **P17**：`submitted` 计数口径与去重日志 `.fstdd/_fstdd003_share_log.json` 必须一致，闸门不得改变该语义。

## Decisions

### D1. 清单摘要用 md5 前 12 位，而非全量摘要

**方案**：`00-SIGNATURES.md` 每行记录 `文件名 | md5 前 12 位 | 落盘时间 | 发出者`，校验器比对前 12 位。

**为什么**：撤回令已给出三个 md5 前 12 位（`2c77481e91a7` / `e6fa9f61c1be` / `661e8543e29e`），说明 K 侧数据源就是这个粒度——用前 12 位可以让 K 侧零改动落地。48 bit 空间对「文件是否被篡改」的用途足够（碰撞需约 2^24 次尝试，对 6 节点规模不构成现实威胁）。

**备选方案及排除原因**：
- 备选 A（全量 md5 / SHA-256）：更严谨，但要求 K 侧改数据源，Q2 落地成本高，会推迟整条防链路；且清单可读性变差。
- 备选 B（文件名 + mtime 比对）：mtime 可被伪造者自由设置，等于零校验。

### D2. 校验器独立成 `tools/verify_notices.py`，不并入回传脚本

**方案**：新建独立模块，提供 `classify_notice(path)`（单文件）、`verify_notices(dir)`（批量）、以及 CLI（`--json` / `--strict`）。轮询自动化以**子进程**调用。

**为什么**：`fstdd003_daily_share.py` 在 09-18 事故中被改坏过一次（加了 `X-FSTDD-Token` 头后被迫回退）。把它当校验器宿主会再次扩大单文件变更面，且回传逻辑与校验逻辑的生命周期不同。子进程调用 + 退出码/JSON 契约使两者彻底解耦。

**备选方案及排除原因**：
- 备选 A（并入回传脚本）：一次事故已证明该文件的变更风险高，不叠加。
- 备选 B（做成 pytest 插件 / import 依赖）：轮询自动化跑的是 shell，import 方式无法被自动化直接消费退出码。

### D3. 闸门默认「告警不阻断」，`--strict` 显式开启

**方案**：非 strict 模式下 `unverified` 只输出一条告警、退出码 0；`--strict` 时 `unverified` 退出码 3 以阻断。

**为什么**：`00-SIGNATURES.md` 尚未落地（Q2 待 K 裁定）。若默认阻断，K 正常下发的通知会被全部拦下，与 2026-09-18 15:32 确立的「协作通知到货后直接执行并回传」准则直接冲突，造成任务漏接——这是**可用性故障**，比原风险更难察觉。闸门先就位、默认低危，等 K 确认清单机制可用后再切 `--strict`。

**备选方案及排除原因**：
- 备选 A（默认阻断）：清单缺失时会让所有通知变成 `unverified` → 全部阻断，协作停摆。
- 备选 B（默认阻断但清单缺失时豁免）：豁免逻辑等于默认不阻断，但代码路径更绕、更难验证。

### D4. 凭证嗅探用形状正则，而非语义解析

**方案**：对 `unverified` 通知跑形状正则（`X-FSTDD-Token:\s*`、`Bearer\s+`、以及「凭证/Token 段落 + 16 位以上字母数字连字符」三类的组合命中），命中即记录规则名。

**为什么**：通知是自由格式 markdown，无法可靠判断「这段文字是凭证」的语义。形状匹配足够识别 token 类凭据，且**误判方向取「宁可隔离」**——隔离区可人工复核，误隔离代价远小于漏判（漏判 = 凭证再次落盘）。

**备选方案及排除原因**：
- 备选 A（语义解析/LLM 判定）：不离线、不可复现、不可测试断言，与 TDD 不可兼得。
- 备选 B（只匹配精确的 `X-FSTDD-Token:` 头）：漏掉 `Bearer` 形式与裸 token 段落，覆盖不足。

### D5. 隔离而非删除

**方案**：命中凭证形状的通知移入 `tools/_quarantine/`，保留原文 + 一份仅含 `文件名 / md5 前 12 位 / 命中规则名 / 时间` 的隔离记录。

**为什么**：撤回令要求保留现场以避免审计断链（09-18 撤回令处理原则）。删除会破坏取证链；隔离既阻断执行又保住证据。隔离区经 `.gitignore` 排除，不进入 git 历史。

**备选方案及排除原因**：
- 备选 A（删除）：破坏审计链，且不可逆。
- 备选 B（原地保留 + 打标记）：文件仍在原目录，下一次轮询会再次读到并可能再次执行。

### D6. 隔离记录与 stdout 不回显凭证片段

**方案**：任何输出（stdout / stderr / 隔离记录 / 日志）只允许出现文件名、md5 前 12 位、命中规则名、时间戳——**凭证本身一个字都不落**。

**为什么**：如果隔离记录里写了凭证片段，`tools/_quarantine/` 就成了一个新的泄露面（且它在 `.gitignore` 里，反而更不容易被审查）。这是本变更最容易自伤的一条，必须有专门测试断言。

**备选方案及排除原因**：
- 备选 A（隔离记录写凭证前 4 位用于比对）：仍然扩大泄露面，收益（比对方便）远小于代价。

### D7. 不修改轮询自动化 prompt，只增加调用点

**方案**：本变更只产出工具与测试；`06ec2c4f` 的调度与 prompt 由后续单独动作接入（需 K 侧清单就绪）。

**为什么**：自动化配置是另一层风险面，且修改它会立即改变线上行为；Q2 未定前接入 `--strict` 有害。工具先可用，接入动作待 Q2 裁定。

**备选方案及排除原因**：
- 备选 A（本次直接改自动化）：工具未经验证就上生产链路，风险叠加。

## Architecture

```
┌─ 每小时轮询自动化 06ec2c4f ────────────────────────────────────────────┐
│                                                                        │
│  ① scp 拉取 notices/FSTDD003/                                          │
│                                                                        │
│  ② ┌─【本变更新增】────────────────────────────────────────────────┐   │
│     │ python tools/verify_notices.py notices/FSTDD003/ --json         │   │
│     │                                                                 │   │
│     │   读 00-SIGNATURES.md ──┐  缺失 → 全量 unverified               │   │
│     │                         │         reason=manifest_missing       │   │
│     │   对每个 收-*.md:       │         + 1 条告警, exit 0             │   │
│     │     md5[:12] 比对       │                                        │   │
│     │      ├─ 命中   → verified                              │         │   │
│     │      ├─ 未命中 → unverified reason=not_in_manifest     │         │   │
│     │      └─ md5 不符 → unverified reason=md5_mismatch      │         │   │
│     │                                                    │             │   │
│     │   unverified ∧ 凭证形状命中 → 移入 tools/_quarantine/          │   │
│     │                     │       + 隔离记录(仅文件名/md5/规则名)      │   │
│     │                     │       exit 2                          │   │
│     │                     ▼                                         │   │
│     │   stdout: {"results":[...], "quarantined":[...], "warnings":[...],│   │
│     │           "exit_code": 0|2|3}  ← 顶层恰好 4 键（SC-015 契约）      │   │
│     │   --strict 且存在 unverified → exit 3                         │   │
│     └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ③ 执行 verified 的通知（本轮：清单缺失 → 全部 unverified → 仅告警）     │
│                                                                        │
│  ④ POST 8787 经验回传  ←── tools/fstdd003_daily_share.py（不变，不附   │
│                            X-FSTDD-Token，不读 _fstdd003_token.txt）    │
└────────────────────────────────────────────────────────────────────────┘

模块边界
  tools/verify_notices.py          新增 · 无外部依赖（stdlib: hashlib/json/
                                   pathlib/re/argparse/shutil）
  tools/test_verify_notices.py     新增 · pytest，自造 fixtures，不依赖真实 notices/
  tools/_quarantine/               新增目录（.gitignore 覆盖，不入库）
  .gitignore                       +1 行: tools/_quarantine/
  tools/fstdd003_daily_share.py    不修改（仅被测试断言「行为不变」）
```

**关键不变量**：`verify_notices.py` 从不写 `.fstdd/_fstdd003_token.txt`、从不读它、从不调用网络。凭证只会被移动，永不被打印。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 清单缺失时若实现成阻断，会中断 K 的协作通知交付（可用性故障，比原风险更隐蔽） | D3 默认告警不阻断；阻断仅 `--strict` 显式开启，待 Q2 裁定后再接入 |
| 凭证嗅探误判：误隔离正常通知 / 漏判伪造凭证 | 误判方向取「宁可隔离」（D4）；隔离保留原文可人工复核；SC-008 以 5 份真实格式通知断言隔离数为 0 |
| 隔离记录自身成为新泄露面 | D6 只记文件名 + md5 前 12 位 + 规则名；SC-010 断言凭证片段不出现在 stdout/stderr/隔离记录/git |
| 接入闸门破坏既有回传链路（09-18 曾出现计数污染） | D2 子进程解耦，退出码/JSON 契约写进断言；SC-016/017/018 断言回传语义与凭证文件不变 |
| 12 位摘要的碰撞风险 | 48 bit 空间，对 6 节点规模的替换攻击不构成现实威胁；升级路径明确（D1 备选 A），Q2 裁定时可换 |
| `_quarantine/` 意外入库 | `.gitignore` 追加条目 + SC-011 用 `git check-ignore -v` 断言 |
| P12 导致 AI 误信 CLI 提取结果而漏写 spec | 本设计的所有输入取自 canonical YAML（已用 `yaml.safe_load` 校验字段齐全）；`extract-proposal` 输出不采信 |
| 本轮无既有测试资产，回归保护从零建立 | test-plan 以「新增即全绿」为目标，同时把「回传行为不变」写成显式 TC，不依赖历史用例 |
