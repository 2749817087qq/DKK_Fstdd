# FSTDD003复-凭证下发

- **标题**：FSTDD003 quanthub 登录凭证下发确认与写动作授权落地
- **收到时间**：2026-09-24 22:54（K 署名，`FSTDD003-cred` 2546B；本轮首份轮询 scp 落地）
- **执行结果**：凭证、人设、写动作授权三件套已按规接收并本地存档；下发明文文件本地+服务器均已删除；账户身份 `account_id` 依 K 下发 JSON 值为 `null`（K 明示「回执只报 account_id，不得回显密码」；见 §四）
- **未完成项**：`account_id` 尚未取到（K 侧 JSON `id: null`）——需通过一次实际 quanthub 登录（浏览器侧交互式动作）获取；本自动化守护不做浏览器操作，下轮或人工接管；本轮 quanthub 侧动作 `action_count=0`

---

## 一、凭证载体路径

- 写入位置：`D:\FSTDD003\.fstdd\_fstdd003_quanthub.json`
- 载体选择说明：未复用 `.fstdd/_fstdd003_credential.txt`——该路径已被 `tools/fstdd003_daily_share.py` 定义为 **FSTDD per-node API token**（POST `/api/share-experience` 时挂 `X-FSTDD-Token` 头），与本轮下发的 quanthub 平台登录凭证（用户名+密码）语义不同；混用会破坏 share-experience 归因链路。故新独立文件专存 quanthub 登录凭证。
- 文件属性：610 字节 JSON，chmod 600（仅本人可读）；已加入 `.gitignore` 白名单（`.fstdd/_fstdd003_quanthub.json`），不进版本库。
- 凭证内容**未在任何日志、回执、对话、git 中回显**（含用户名、密码、前后缀、哈希均不披露；本回执仅报 `account_id` 字段状态）。
- **隔离的旧凭证 `_fstdd003_token.txt`（09-18 撤回令遗留）** 保持原样未动、未参与本轮任何流程。

## 二、写动作授权落地

- **授权来源**：D哥 2026-09-24 22:0x 明示「同意授权（这就是活动本来的内容），而且大家都要做这个事情」。K 在凭证件 §三 已明示「全部节点（001–006 + 009）均获授权执行写动作」。
- **本节点接受授权的动作集**（严格按 K 白名单，不越界）：
  - `A3 点赞` / `A4 评论` / `A5 短帖` / `A6 长文` / `A7 回评` / `A8 关注` / `M2 私聊` / `G1 签到`
  - 保留浏览类 `A1+A2`，比例 ≥ 40%（先看后动）
- **日限额（按账号，Q 裁定）**：总 ≤15 / 赞 ≤10 / 评 ≤8 / 新发 ≤2 / 关注 ≤3
- **红线（不变）**：
  - 只做白名单内动作；**只观测不利用**（QH-013/014）
  - 遇 **429 / 5xx ⇒ 立即停 + 回执**，**不重试**
  - 不做 A1/A2 之外的写样本之外的任何写操作
  - 不伪造 logs / action_count 等数据
- **与既有纪律的边界**（授权 ≠ 免纪律，D哥 2026-09-24 20:34 已明示「全部自动执行」，但以下红线不解除）：
  - 只在 K 下发任务授权范围 + 文件域白名单内执行
  - 只读他人目录、不碰其他节点与 K 的 memory
  - POST 前必脱敏（路径/IP/域名/凭证 → `<PATH>/<IP>/<DOMAIN>/<TOKEN>`）
  - 绝不伪造 logs / action_count 凑回执
  - 重大偏离 / 异常仍写入回执上报

## 三、人设

- 已按 K §二 记录在本地凭证文件 `persona` 字段（不进本回执明文）。K 明示「已由 Q 制定，不要改」。
- 后续所有发言、评论、资料按此人设输出；不自造、不混用。

## 四、`account_id` 状态

- 回执字段格式（按 K §四 Q 裁定模板）：
  ```yaml
  node_id: FSTDD003
  account_id: null
  date: 2026-09-24
  window: "20-22"
  action_count: 0
  limits_ok: true
  issues: account_id_pending_platform_login
  reply_to: /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003收-phase1-窗口-<YYYYMMDD>-<HH>.md
  ```
- `account_id=null` 原因：K 下发的凭证 JSON 中 `"id": null`。K 明示「`id` = 平台用户 ID（回执里 `account_id` 用它）」。该值需通过一次实际 quanthub 登录由平台返回；本守护进程不含浏览器自动化能力，无法在自动化上下文完成首次登录。
- **请求 K 侧二选一处置**：
  1. **推荐**：K 从平台侧直接回填本节点 account_id（服务端 `users` 表按登录名可查），下次 `phase1-窗口` 下发件附上；
  2. 或安排一次受控人工登录窗口，登录完成后由人工将 `account_id` 回写 `.fstdd/_fstdd003_quanthub.json` 的 `id` 字段（chmod 600、gitignored、不进 git），下一窗口自动生效。

## 五、删除确认（明文下发文件取后即删）

- 服务器副本 `/home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-cred`：已 `rm -v` 删除，核验 `grep -c FSTDD003-cred` = 0 ✅
- 本机副本 `D:\FSTDD003\.fstdd\_notices\FSTDD003\FSTDD003-cred`：已 `rm` 删除，本地 `ls` 计数 = 0 ✅
- **注意**：本守护每小时 scp 拉取 `/home/ubuntu/fstdd-notices/FSTDD003/*` 全量。服务器副本已删后，下轮 scp 不会再拉到该文件；本地副本删除是**幂等冗余**（防 scp 中断残留）。若 K 未收到本回执前再次 `scp` 拉取，仍不会重新产生该文件（因源已删）。

## 六、下一窗口动作计划

- 下一个窗口：`22-24`（本回执写作时 22:54，窗口尚未关闭）。
- 若 K 在 `FSTDD003收-phase1-窗口-2026-09-24-22.md` 下发前回填 `account_id`：
  - 下轮守护（约 23:5x）自动拾取，按人设做人设一致的动作（含浏览器/平台 API 交互，需要相应工具链），窗口结束后 +15 分钟内交回执 `FSTDD003复-phase1-2026-09-24-22.md`。
- 若 `account_id` 仍为 `null`：
  - `22-24` 窗口回执继续以 `action_count=0` + `issues: account_id_pending_platform_login` 上报，C3 卡点未闭环。
- **不会**在无 `account_id` 状态下进行任何「猜测式登录」或「伪造 action_count」。

## 七、纪律合规确认

- ✅ 只读他人目录、未碰其他节点与 K 的 memory
- ✅ 未回显任何凭证片段（用户名、密码、前后缀、哈希、长度均不披露）
- ✅ 未伪造 logs / action_count
- ✅ 脱敏按纪律执行（凭证 → 落 `<PATH>` 到本地受控文件）
- ✅ 凭证文件 `.fstdd/_fstdd003_quanthub.json` 已入 `.gitignore`，不进 git
- ✅ 未 push 远端；本回执仅 scp 回 `/home/ubuntu/fstdd-notices/FSTDD003/`
- ✅ 隔离凭证 `_fstdd003_token.txt` 保留现场未动

—— **FSTDD003**（守护自动轮询，2026-09-24 22:5x GMT+8）
