# FSTDD 多节点接入指引 / Distributed Access Guide

> 适用：6 个 AI agent / 3 台开发机共同推进同一代码库
> 建立日期：2026-09-17
> 相关 change：`2026-09-17-server-bare-repo-mirror`（数据面）、`2026-09-17-distributed-task-coordination`（控制面）

## 一、架构速览

```
  开发机 A / B / C 上的 6 个 agent
        │
        │  git-over-ssh（唯一数据面入口）
        ▼
  云服务器 43.134.236.80
  /home/ubuntu/fstdd-git/stdd-repo.git   ← L1 数据面：唯一真值源
        │
        │  post-receive 钩子（Deploy Key，非强制）
        ▼
  GitHub 2749817087qq/DKK_Fstdd          ← 镜像 / 对外通道
```

**三条硬规则**：

1. **服务器裸库是唯一真值源**。任何机器的本地仓库都只是副本，不得作为"事实"依据。
2. **禁止跨机文件拷贝式同步**。所有产出必须走 `git push` —— 本项目已因手工 cp 发生过两次漂移。
3. **GitHub 是镜像，不是源**。GitHub 不可达不阻塞任何流转。

## 二、新节点接入（3 步）

### 步骤 1 — 配置 SSH 别名

在 `~/.ssh/config` 中加入（把 `IdentityFile` 换成该机器的私钥路径）：

```sshconfig
Host fstdd-hub
    HostName 43.134.236.80
    User ubuntu
    IdentityFile <该机器的私钥路径>
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30
    ServerAliveCountMax 4
```

接入前需把该机器的**公钥**加入服务器 `/home/ubuntu/.ssh/authorized_keys`（由运维执行）。

验证：

```bash
ssh fstdd-hub 'echo OK; hostname'
# 期望输出 OK 与 VM-0-17-ubuntu，且 stderr 为空（无主机密钥告警）
```

### 步骤 2 — 克隆或挂载 remote

新机器首次：

```bash
git clone fstdd-hub:/home/ubuntu/fstdd-git/stdd-repo.git
```

已有本地仓库（如法定源 `D:/tools/FSTDD/stdd-repo`）：

```bash
git remote add server fstdd-hub:/home/ubuntu/fstdd-git/stdd-repo.git
# 若已存在则改用：
# git remote set-url server fstdd-hub:/home/ubuntu/fstdd-git/stdd-repo.git
```

### 步骤 3 — 验证接入

```bash
git fetch server
git rev-parse server/master        # 应与服务器裸库 HEAD 一致
```

## 三、日常操作

| 动作 | 命令 |
|---|---|
| 拉取最新 | `git fetch server && git rebase server/master` |
| 推送产出 | `git push server <branch>` |
| 推送并自动镜像 | 同上（钩子自动完成，无需额外操作） |
| 查镜像日志 | `ssh fstdd-hub 'tail -20 /home/ubuntu/fstdd-git/mirror.log'` |
| 核对三方一致 | 对比本地 `git rev-parse HEAD`、`server/master`、GitHub HEAD |

**推送后如何确认镜像成功**：推送命令返回后，钩子已同步执行完毕。核对：

```bash
ssh fstdd-hub 'BARE=/home/ubuntu/fstdd-git/stdd-repo.git; \
  echo "bare:   $(git -C $BARE rev-parse master)"; \
  echo "github: $(git -C $BARE ls-remote github refs/heads/master | cut -f1)"'
```

两者相同即为收敛。

## 四、节点标识约定

| node_id | 说明 |
|---|---|
| `FSTDD001` … `FSTDD006` | 6 个 agent 的稳定标识 |
| `FSTDD005` | 法定源所在开发机（D 盘工作区）上的 agent |

- node_id 是**协作层**标识，与控制面（8788）注册表一致
- 节点 id **不得硬编码**在共享代码里，应由本地配置提供
- 控制面地址 `http://127.0.0.1:8788`（仅回环，经 SSH 访问）

## 五、故障处置

| 现象 | 处置 |
|---|---|
| 推送被拒（非快进） | 先 `git fetch server && git rebase server/master`，不要强推 |
| 镜像日志出现 `[WARN]` | GitHub 侧可能分叉。**不要**在服务器上手动 `--force`；先确认 GitHub 上那几个提交的来源 |
| GitHub 不可达 | 无需处置。裸库与各机流转不受影响，镜像会在下次推送时重试 |
| 主机密钥告警 | **不要**用 `StrictHostKeyChecking=no` 绕过。先 `ssh-keyscan <host> \| ssh-keygen -lf -` 取指纹，与告警中服务器声称的指纹核对，一致才更新 `known_hosts` |
| 服务器磁盘水位高 | `df -h /`；裸库本身仅 MB 级，水位主要来自其他服务 |

## 六、重建数据面

服务器裸库可一条命令重建（幂等，已存在则保留数据）：

```bash
./tools/deploy_server_bare_repo.sh
```

覆盖参数见脚本头部注释。`FSTDD_SKIP_MIRROR=1` 可只建裸库不碰 GitHub。
