# FSTDD 安装与运行问题清单（2026-09-17 第二轮复测）

环境：Windows / Git Bash / Python 3.13.14（隔离 venv）
范围：**仅本软件实例（home = `~/.workbuddy-ai`）**；另一 WorkBuddy 实例（`~/.workbuddy`）不在本次管理范围。
操作：拉取上游新版 → 重新安装 → 冒烟 → 校验

---

## 一、上一轮 4 项修复在新版中**均未合入**

复测确认上游 master 的 `install.sh` 仍为旧实现：

| 编号 | 问题 | 新版状态 |
|---|---|---|
| P1 | `--py <path>` 解析（`for arg in "$@"` + `shift` 不生效） | ❌ 未修，仍是 `for arg in "$@"; do ... --py) shift; PY="${1:-}"` |
| P2 | 未 `export FSTDD_OUT` / `FSTDD_SRC` | ❌ 未修 |
| P3 | Git Bash 路径未转 Windows 形式（写到 `C:\c\Users\...`） | ❌ 未修，`_winpath` 定义了但未用于 `FSTDD_OUT` |
| P4 | 结束 echo 的目录与实际写入目录不一致 | ❌ 未修（且本轮出现新的不一致，见下） |

---

## 二、本轮新增：**注释与实现自相矛盾**（P2 的恶化）

| 位置 | 写的默认值 |
|---|---|
| `install.sh` 头部注释（第 14 行） | `FSTDD_OUT   skill 输出目录（默认 ~/.workbuddy-ai/skills）` |
| `tools/install_workbuddy_skills.py`（第 15 行） | `OUT = Path(os.environ.get("FSTDD_OUT", Path.home() / ".workbuddy" / "skills"))` |

**两者不一致。** 又因 P2（未 export），实际生效的是 Python 侧的 `~/.workbuddy/skills`，
与 install.sh 注释所声称的 `~/.workbuddy-ai/skills` 相反。

后果：使用者按注释以为装到了 A，实际在 B；而 B 属于**另一 WorkBuddy 实例**，
本软件会话看不到 → 表现为"装了但不生效"，且极难排查。

**建议（二选一，别再各写各的）**：
1. `install.sh` 里 `export FSTDD_OUT="$(_winpath "${FSTDD_OUT:-$HOME/.workbuddy-ai/skills}")"`
   —— 单一真源，Python 只认环境变量；
2. 或让 Python 默认值与注释一致，并由 install.sh 只做可选覆盖。

本机已按方案 1 处理（保留 export + `_winpath` + 参数解析修复），
安装结果 `skill 目录: C:/Users/Administrator/.workbuddy-ai/skills`，校验 `[PASS]`。

---

## 三、新增组件审计：`tools/inbox_server.py`

- 性质：自建经验接收端点（**服务端**），给无 GitHub 凭证者一条回传路径，
  替代上游 `POST https://hzddyy.com/...` 的第三方外发。
- 接口：`POST /api/share-experience`（单条/批量）、`GET /health`
- 已有防护：按条数限流（带 `Retry-After`）、批量上限、请求体上限、敏感内容规则、422/429 语义
- 判定：**P2（正当）**。服务器是自有的，数据不外发第三方；本机不运行该服务。
- 提示：若正式部署，建议补齐鉴权与落盘加密/访问控制（当前未见鉴权段落）。

---

## 四、本轮测试结果

| 项 | 结果 |
|---|---|
| `install.sh --yes --py <venv python>` | ✅ 通过（本机已含修复） |
| 7 个 skill 落位 | ✅ `fstdd` + `understand/spec/build/deliver/upgrade` + `fstdd-fin` |
| 安装目录 | ✅ `C:\Users\Administrator\.workbuddy-ai\skills` |
| 安全策略 + 路径适配校验 | ✅ `[PASS] 6 个 skill` |
| CLI 冒烟 | ✅ `init` / `new` / `status` 通过 |
| 外发哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` | ✅ 在位（2 处） |
| `experience list` | ✅ 0 条（无数据可外发） |

---

## 五、推送说明

本文件与 `INSTALL_RUN_ISSUES_2026-09-16.md` 一并回传至
`2749817087qq/Fstdd-experiences`。
本机 `github.com:443` 直连不通、代理 502、SSH 公钥未授权。
**网页上传路径已废弃**（AI 无法操作浏览器 fork / 拖拽文件），
改为无凭证降级 POST 到自建接收端点 `http://43.134.236.80:8787`，实测成功。

---

## 六、补充（09-17 回传后新发现）

### P10 — 导出索引与实际回传集合不一致（口径 bug）

- **现象**：`share_experience.py --export --publish` 打印「已导出 15 条」，
  但 `/health` 的 `received` 一次增加 **27**；`experiences/README.md` 索引只列 15 条。
- **根因**：两处数据源不同，且 publish 传的是**目录**而非导出集合：
  - `collect_local()` 只读源目录 `.fstdd/experiences/`（当前 15 条）→ 决定 `written` 与 README 索引；
  - `publish_via_inbox(OUT_DIR, url)` 传的是导出目录 `experiences/` 全量 → 扫 `EXP-*.md` 得 27 个。
- **副作用（可利用）**：手工丢进 `experiences/` 的 `.md`（如本报告转写的 `EXP-*-DOCS-*`）
  不在源目录里，也能被回传——这正是本次两份报告能进通道的原因。属未文档化的隐式行为。
- **风险**：publish 每次提交**全量**，同一 ID 会重复提交，服务端 `received` 重复累加
  （观测到 87 → 181 一次涨 94，远超本地条目数，疑为重复提交所致）。
- **建议修法**（二选一）：
  1. publish 只提交本次 `prepared` 集合，与 README 索引严格对齐；
  2. 保留全量提交，但客户端记录已提交 ID（如 `.fstdd/share-audit.yaml` 已有审计，可复用）做增量；
     同时服务端按 `experience_id` 去重后计数。
- **优先级**：P2（不影响正确性，但污染统计、且让使用者误判回传条数）

### P11 — `experiences/` 已被 `.gitignore` 忽略，导出产物不入库

- 现象：`git status` 不显示新增的 `EXP-*.md`（被 `.gitignore:10 experiences/` 忽略），
  仅历史已 tracked 的 25 个文件仍显示变更。
- 影响：新产出的经验文件不会进仓库历史，只能靠回传通道留存。
- 判定：符合设计（`experiences/` 是导出产物），但 README 索引被 tracked 属历史遗留，
  导致每次 `--export` 都产生一个纯时间戳的 diff。建议把 `experiences/README.md` 也移出跟踪。
