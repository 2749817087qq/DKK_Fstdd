# Code/Prompt Patch — 06ec2c4f（C1 落点）

以下片段即为对守护自动化 prompt（06ec2c4f）的实际补丁（经 `automation_update` 应用）。

## 新增铁律（放在【纪律】段之前或内）

```
【499 修复铁律：scp/ssh 一律后台+await】
本守护所有 `scp`/`ssh` 调用（含第 0 步列服务器 `收-`、第 1 步拉取、第 4 步回写）
**必须**以 `run_in_background=true` 启动，立即取得 `task_id`，随后以
`TaskOutput(task_id, block=true, timeout=600000)` 等待完成。**严禁**以前台方式
阻塞等待长传输。前台 turn 不被 2–3 分钟传输拖垮，即可从根本上消除网关记录的
`499 canceled` 噪声。传输成败**只以文件系统为准**（scp exit=0 + 目标文件落地），
不因 499 噪声误判为服务端故障。可操作 SOP 见 `tools/fstdd003_daemon_499_sop.md`。
```

## 第 0 步示例加注

原：`ssh -i /d/id_ed25519 ubuntu@43.134.236.80 "ls ... | grep '^FSTDD003收-'"`
改为：该 `ssh` **以 `run_in_background=true` 启动 + TaskOutput 等待**（见 499 修复铁律）。

## 第 1 步示例加注

原：`scp -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@...:/home/ubuntu/fstdd-notices/FSTDD003/* D:/FSTDD003/.fstdd/_notices/FSTDD003/`
改为：**以 `run_in_background=true` 启动 + TaskOutput 等待**（见 499 修复铁律）；
完成后以 `ls D:/FSTDD003/.fstdd/_notices/FSTDD003/` 校验落地。

## 第 4 步示例加注

原：`scp ... FSTDD003复-<主题>.md ubuntu@...:/home/ubuntu/fstdd-notices/FSTDD003/`
改为：**以 `run_in_background=true` 启动 + TaskOutput 等待**；回写后按需校验。

## 第 5 步自查加注

原：`curl -s http://<IP>:8787/health` 看 `received` 计数...
改为：在自查末尾追加一行 `pull_mode: background+await`（本轮拉取/回写均走后台+await）。
