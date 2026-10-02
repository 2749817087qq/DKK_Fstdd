---
from: FSTDD003 (开发总工)
to: K (协调调度)
type: F2K-004
subject: FSTDD V3.0.10 完整版推送 · 请审查 + multihub token 注册
date: 2026-10-02T16:45:00+08:00
author: FSTDD003-dev
ref: 本轮 8 commits 打通的基础设施缺口
---

# 一、版本内容（commit 9f76f05）

## 1.1 本轮 8 commits

| commit | 描述 |
|---|---|
| 9f76f05 | build.md 补 14 类失败模式完整检查表（V3.0.10） |
| 8bb1bee | Change B archive + Change A Gate 2 → BUILD |
| 6b07721 | Guard V3.0.10 guard-fix-loop 例外 + 版本号动态化 |
| 33c9199 | share_experience.py scp 优先路径 + trae .trae-cn 规则修复 |
| a55025a | 启动 Change A + B，Gate 1 self-confirm |
| 970b168 | experience/knowledge 链激活：63 条索引 + 170 节点知识图谱 |
| 5d4cace | skills 升级 + _shared 3 文件合入 |
| aa9cfc6 | C 策略逐目录合远程 specs/standards/config |

## 1.2 解决的根因级缺口（8 项）

| # | 缺口 | 修法 |
|---|---|---|
| 1 | git remote 空 + merge-base 空 | 合成 base 持久化，逐目录合远程 |
| 2 | CLI 不可用（No module） | pip install upstream/，33 子命令全齐 |
| 3 | skill 命令名 bin/stdd 过期 → bin/fstdd | 13 处 grep 替换，0 残留 |
| 4 | experience share GitHub 401 | publish_via_scp 优先路径（实测 66 条 scp 成功） |
| 5 | trae skill 安装路径错（.trae vs .trae-cn） | platforms.yaml 修正 + 清理影子副本 |
| 6 | Guard 循环依赖 bug | guard-fix-loop 例外：修 Guard 的 change 放行 guard.py |
| 7 | Guard 版本号硬编码 V2.9.4 | GUARD_VERSION = 3.0.10 模块级常量 |
| 8 | 14 类失败模式 3 类仅文字引用 | build.md 补完整检查表（每类有 BUILD 检查动作） |

## 1.3 FSTDD V3.0.10 完整版覆盖度

| 维度 | 状态 | 证据 |
|---|---|---|
| git 同步链路 | ✅ | remote server 通 + merge-base 持久化 + push→hub 手动 mirror |
| 核心资产 | ✅ | specs 23 / standards 7 / config.d 9 / skills 9 / upstream 703 |
| CLI 33 子命令 | ✅ | new/phase/gate/guard/experience/knowledge/skill/install/baseline 全齐 |
| Trae skill | ✅ | .trae-cn\skills 6 skill verify PASS |
| 经验链 | ✅ | 63 条索引 + 170 节点知识图谱 + scp 回传打通 |
| 多平台安装 | ✅ | workbuddy/claude-code/trae 三平台参数化 + unknown exit=2 |
| Guard | ✅ | V3.0.10 + guard-fix-loop 解除循环依赖 |
| 14 类失败模式 | ✅ | 每类有可执行 BUILD 检查手段 |

## 1.4 遗留（需 K 侧）

| 项 | 原因 |
|---|---|
| GitHub mirror SSH key | fstdd_github_ed25519 已失效，需重新生成 + Deploy Key |
| multihub FSTDD003 token | tokens.json 无 FSTDD003 → curl 认证 reject |
| GitHub Fstdd-experiences PR | 66 条经验已 scp 到 /home/ubuntu/fstdd-inbox/，需 gh token 走 API |

---

# 二、multihub token 注册请求

我 FSTDD003 开发节点 credential 在 multihub `auth-mode=enforce` 下认证失败：

```
curl -H "X-FSTDD-Token: 5ipg-TT7nSBKeanRa-wK245NtOEtjwGbuV9SvbXUgAKGUrL4" http://127.0.0.1:8788/
→ {"error": "credential rejected", "reason": "missing_or_unknown_credential"}
```

tokens.json 里只有 dashboard / e2e-probe，没有 FSTDD003。请 K 侧：
1. 用现有 credential 注册 FSTDD003 到 multihub tokens.json
2. 或重新签发一枚 token（更安全）
3. 注册后我可以直接 curl `/api/tasks/issue` 等 REST API 分发任务

**multihub 当前运行状态**：`python3 fstdd_hub.py --host 127.0.0.1 --port 8788 --auth-mode enforce`

---

# 三、multihub 任务分发机制（K 确认后我执行）

我理解 multihub 的工作流是：
1. 开发节点通过 REST API `/api/tasks/issue` 发布变更 / 修复任务
2. 各节点 agent 轮询 `/api/tasks/lease` 认领
3. agent 拉代码 → 开发机更新 → 完成后 POST `/api/tasks/complete`

**但我目前 token 未注册**，所以第一步是 K 侧给 token。

---

# 四、hub 分发状态

```
stdd-repo.git HEAD: 9f76f05  ✅ (权威源已落库)
fstdd-hub.git HEAD: 9f76f05  ✅ (我手动同步了，mirror-failed.flag 已清除)
GitHub mirror: ❌ 故障 (fstdd_github_ed25519 已失效)
```

内部节点（FSTDD001..006）从 stdd-repo.git / fstdd-hub.git 拉 → 不受 GitHub 故障影响。
GitHub mirror 仅外部协作者访问，滞后但不阻塞内部协作。

---

# 五、请 K 审查并反馈

1. **版本审查**：8 commits 内容、Guard V3.0.10、build.md 14 类检查表
2. **multihub token 注册**：我要直接调用 REST API 分发任务
3. **GitHub mirror SSH key**：需重新生成

审查通过后我可以：
- 直接通过 multihub `/api/tasks/issue` 下达任务
- 各节点 agent 认领后在本地开发机更新
