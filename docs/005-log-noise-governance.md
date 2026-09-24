<!-- ARCHIVED-BY-K provenance
source_node: FSTDD005
original_path: notices/FSTDD005/FSTDD005复-日志采集与噪音治理.md
archived_at: 2026-09-25
note: 由 K-main 按《节点交付物入库规程》收进主仓（此前仅存于 notices/，不进版本、不可检索）
-->

---
title: "FSTDD005复-日志采集与噪音治理"
from: FSTDD005（经验回传轮询自动化）
to: K（FSTDD 经验库归口节点）
date: 2026-09-21
re: FSTDD005收-日志采集与噪音治理.md（5 项任务）
status: 已诊断 + 方案就绪；**T-A/B/C 含改脚本动作，按 K 2026-09-18 边界「先回执确认再动手」，未自动改源码**
---

# 005 复-日志采集与噪音治理

> 处理依据：本自动化为**只读**经验回传轮询（不修改任何 FSTDD 项目源码/配置）。
> 收到的 5 项任务中，T-A/B/C 涉及改 `skill-improvement/scripts/*.py`（写/改动作），
> T-D/E 文本已明示「不要擅自删配置或改系统文件」。
> 故本轮**只做诊断 + 给出可比对判据的方案**，不执行任何写入；待 K/D哥 确认后再动手。

---

## T-A 崩溃采集按 `launchedAt` 过滤

**做了什么（只读核查）**：通读 `collect_skill_feedback.py` 的 `scan_crashes()`（L394-412）。
确认根因：该函数用 `in_window(int(st.st_mtime*1000), ...)` —— 即**按文件 mtime（文件存在/写入性）**判新增，
而非事件时间 `launchedAt`/entries 时间。09-19 22:5x 的 3 个崩溃文件（daemon-3160 / main-10392 / sidecar-236）
其文件写入/采集落在 09-20 窗口内，故被误标为「09-20 新增」。

**判据证据**：与 `daily/2026-09-20.md` §6 崩溃辨析表一致（3 个窗口外条目 launchedAt=09-19 22:5x）。

**提议改动（需确认）**：`scan_crashes()` 改为读取崩溃文件内 `launchedAt` 字段（崩溃文件为 JSON，含 `launchedAt`/`entries` 时间），用事件时间做窗口判定：
```python
def _launched_at_ms(p: Path) -> int | None:
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if "launchedAt" in line:
                m = re.search(r'"launchedAt"\s*:\s*"([^"]+)"', line)
                if m:
                    return parse_iso_ms(m.group(1))
    except OSError:
        return None
    return None
# 在 scan_crashes 中：
la = _launched_at_ms(p) if p.suffix == ".json" else None
if la is not None:
    if not in_window(la, start_ms, end_ms):
        continue            # 窗口外 → 不标新增
else:
    if not in_window(int(st.st_mtime*1000), start_ms, end_ms):
        continue
```
**回归验证**：09-19 22:5x 三个应判为「窗口外」；窗口内真新增应只剩 daemon-9704/8288 两项。

**卡点**：需 K 确认是否直接改 `collect_skill_feedback.py`（写动作）。确认后我方执行并复跑校验。

---

## T-B 良性噪音显式归类

**做了什么（只读核查）**：`scan_logs()`（L291-378）按 error/warn/perf 分桶，但**无「良性噪音」显式标注**；
`build_brief()`（L452-516）直接把三类（feature-flag 404 / netdrive access_denied / AutomationPromptSettler）计入问题表/告警。
现状虽未「误报为故障」，但缺明确归类行。

**判据证据**：`daily/2026-09-20.md` §3 P3 两条 + AutomationPromptSettler（§3 末，「良性聚合」）已人工注明良性，
但**采集脚本层无自动归类**。

**提议改动（需确认）**：在 `scan_logs()` 增加良性噪音集合，命中者在 brief 里输出「判定=良性噪音 + 理由」且**不进问题表**：
```python
BENIGN = [
    (re.compile(r"/v2/feature-flag/api/feature-flags/check"), "feature-flag 端点已下线/版本不匹配，404 属预期噪音"),
    (re.compile(r"custom-mcp:netdrive"), "netdrive 连接器未授权，待人工授权，非内核缺陷"),
    (re.compile(r"AutomationPromptSettler"), "单条自动化多轮状态切换聚合计数，非卡死"),
]
```
并在 `build_brief` §三「断言」段对每类输出一行 `判定=良性噪音 + 理由`；问题表不含它们。

**卡点**：同 T-A，需确认改 `collect_skill_feedback.py`。

---

## T-C 扫描窗口参数化（scan_log_keywords.py）

**做了什么（只读核查）**：`scan_log_keywords.py` 当前**无 argparse**，`w0`/`w1` 为硬编码常量（L6-7）：
`w0 = 2026-09-20 00:00Z, w1 = 2026-09-21 00:00Z`。每次换日需手改并备份（日报 §已知局限已确认）。

**判据证据**：`daily/2026-09-20.md` 第 5 行与「已知局限」均记载「窗口硬编码，已就地联动并备份」。

**提议改动（需确认）**：增加 `--date YYYY-MM-DD` / 环境变量 `SCAN_DATE`，**不改默认行为**（无参时维持原逻辑）：
```python
import argparse, os
ap = argparse.ArgumentParser()
ap.add_argument("--date", default=os.environ.get("SCAN_DATE", ""),
               help="扫描日 YYYY-MM-DD；省略则用脚本内置默认窗口")
a = ap.parse_args()
if a.date:
    d = datetime.datetime.strptime(a.date, "%Y-%m-%d")
    w0, w1 = d, d + datetime.timedelta(days=1)   # 00:00Z ~ 次日 00:00Z
# 否则沿用下方硬编码默认（保持原行为）
```
**判据**：`--date 2026-09-21` 跑通且结果区间 = 09-21 00:00Z~09-22 00:00Z；无参时与现行为一致。

**卡点**：需确认改 `scan_log_keywords.py`（写动作）。

---

## T-D Git Bash 完整性核查（`/etc/msystem.d/MSYS` 缺失复发）

**做了什么（只读核查）**：
- Git 安装目录**权威副本存在**：`C:\Program Files\Git\etc\msystem.d\MSYS`（152B，Feb 2 2026）。
- Git Bash 运行时 VFS 层 **`/etc/msystem.d/MSYS` 不存在**（ConPTY 内 `ls /etc/msystem.d/MSYS` → No such file or directory）。
- ShellSnapshotService 跑快照脚本时 source `/etc/msystem`，引用 `/etc/msystem.d/MSYS` → 169 次 warn/error。

**结论**：
1. **该文件「应存在」**（标准 Git Bash 组件，安装副本完好）。
2. **「复发」根因**：09-18 闭环依据 = 安装路径存在 + 当时窗口内 0 次；但本次报错来自**运行时 VFS 路径**
   （WorkBuddy 托管的 ConPTY Git Bash 的 `/etc`，并非直接映射安装目录），环境漂移/重启后该 VFS 视图未含 msystem.d，
   与安装副本完好并不矛盾。属**良性环境噪音**，非真实缺陷。
3. **恢复步骤（如需，需 K 复核后再执行，不自行改系统文件）**：
   - 轻量：重启 Git Bash/ConPTY 会话，使其 `/etc` 重新派生自安装目录（多数情况自动恢复）；
   - 兜底：以管理员复制 `C:\Program Files\Git\etc\msystem.d\MSYS` → 运行时 `/etc/msystem.d/MSYS`
     （此步改系统环境，超出节点自治范围，须 K 裁定）。
4. **为何「复发」**：VFS 视图不持久、随 shell 会话重建；安装副本虽在，但快照服务每次起新会话重新 source 才暴露缺失。

**建议**：日志层对该 stderr 降噪（判为良性环境噪音）；无需改本机系统文件。本节点**不擅自改系统文件**。

---

## T-E netdrive MCP 连接器（access_denied ×224）

**做了什么（只读核查）**：
- 日志证据：`daemon-app-server [McpApps] discovery failed for custom-mcp:netdrive: {"error":"access_denied","error_description":"not_authorized"}`（224 次 warn，09-20 11:05 起）。
- 配置定位：标准用户级 `mcp.json` 在 `~/.workbuddy-ai/mcp.json` **不存在**（仅 `mcp-approvals.json` 为空 `{}`）；
  netdrive 是**「自定义 MCP 连接器」**，经 WorkBuddy 连接器商店/Connector 管理注册，不落地于本地可编辑 mcp.json。
- 日志 grep 在 `~/.workbuddy-ai/cache/acc-product-config-v3.json` 中命中 `netdrive`（产品目录条目，非用户安装配置）。

**处置（二选一，均需人工在 UI 操作，本节点不自行删/改）**：
- **① 重新授权**：WorkBuddy UI → 连接器管理 → netdrive → 重新授权；成功判据 = 日志不再出现 `custom-mcp:netdrive ... access_denied`。
- **② 若已不用，移除配置**（**只列项、不删除**）：在连接器管理中删除名为 `netdrive` 的 custom-mcp 条目；
  删除前请确认无其他会话依赖该连接器（如文件网盘挂载）。

**卡点**：本节点**不擅自删配置或改系统文件**（依任务明示）。待 D哥/K 在 UI 操作后，下轮采集观察 `access_denied` 归零。

---

## 汇总

| ID | 动作性质 | 本轮处理 | 待确认/卡点 |
|----|---------|---------|------------|
| T-A | 改 `collect_skill_feedback.py` | 诊断 + 给出 launchedAt 过滤补丁 | K 确认后改脚本并复跑 |
| T-B | 改 `collect_skill_feedback.py` | 诊断 + 给出良性噪音归类补丁 | K 确认后改脚本 |
| T-C | 改 `scan_log_keywords.py` | 诊断 + 给出参数化补丁 | K 确认后改脚本 |
| T-D | 只读诊断 | 结论：安装副本完好、运行时 VFS 缺失，良性噪音 | 不自行改系统文件；建议日志降噪 |
| T-E | 只读诊断 | 结论：custom-mcp 未授权，配置在连接器商店 | 不自行删；待 UI 重授权或移除 |

**本次日报第 1 项（Hook Traceback）已由 K 修掉（`53633d9`）—— 本节点无需动作，下轮采集观察其归零。**

> ⚠️ 按 K 2026-09-18 边界「含写/删/改动作的任务先回执确认再动手」+ 本自动化硬约束「不修改任何 FSTDD 项目源码」，
> T-A/B/C 三处脚本改动**均未执行**，仅提供方案。请 K/D哥 确认是否改 `D:\FSTDD005\skill-improvement\scripts\*.py` 后我再落地。
