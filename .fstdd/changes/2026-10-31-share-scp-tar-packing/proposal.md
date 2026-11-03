# 经验回传 scp 通道改 tar 打包：112 个文件 5m19s → 目标 <30s

<!-- source_hash: 50ee16dff5b93f1a -->
<!-- generated_at: 2026-11-03T11:17:41+00:00 -->
<!-- canonical: canonical/proposals/2026-10-31-share-scp-tar-packing.yaml -->

## Why

`tools/share_experience.py` 的 `_scp_dir()` 把 out_dir 里**每个文件单独列进 scp 命令行**
（`scp -r -- file1 file2 ... file112 host:dir/`）。112 个经验实测耗时 **5 分 19 秒**。

后果不是「慢」，而是**假失败**：任何外层 timeout < 5min 的调用（CI、skill 自动调用、
人工 `timeout 120`）都会在传输中途 SIGTERM 杀掉进程 ⇒ `subprocess.run` 返回非 0
⇒ `_scp_dir` 判失败 ⇒ `publish()` 降级到 inbox 通道（本机无 inbox token ⇒ 401）
⇒ 审计记 `target: endpoint` / `result: failure`。

**但已传的文件留在服务器上** —— 实测 2026-10-31 三次不同 timeout 留下 13 / 25 / 37 个
文件的三个半成品批次，而审计全部记成「失败」。症状极具迷惑性：服务器上明明有文件，
审计说没传上去。

这个假信号直接导致我在 v3.6.0 DELIVER 收尾时误报「经验回传失败、112 条待传」——
而这恰恰是 v3.6.0「反漂移机制」要防的**形态 A（无证据断言：看了审计就下结论，
没核实服务器上的事实）**。


## What Changes

- 新增 `_pack_tar(out_dir) -> tuple[Path | None, str]`：用 Python 标准库 `tarfile`
把 out_dir 下所有文件打成单个 `<node_id>-experiences-<ts>.tar.gz`（写到临时目录），
返回路径与失败原因。用标准库而非系统 `tar` 命令 —— 跨平台（Windows/macOS/Linux）
且不依赖 PATH。

- 改 `_scp_dir()` 第 4 步：从「枚举全部文件逐个 scp」改为
「scp 单个 tar 包 → 远端 `tar -xzf` 解包 → 删 tar」。批次目录名与时间戳语义不变
（仍是 `{node_id}-experiences-{YYYYmmdd-HHMMSS}`），保证既有消费方（服务器侧扫描）
不受影响。

- 远端解包后的**文件数校验**改为：`ls batch_dir/*.md | wc -l` 与打包前的本地文件数
比对，不一致则返回失败（防止解包不完整被当成功）。同时校验 tar 包已被删除
（不留残骸）。

- 保留**逐文件 scp 作为 fallback**：tar 打包失败（如文件被占用 / tarfile 异常）时
自动回退到原有逐文件路径，并在 reason 里标注「已回退逐文件模式」。
理由：tar 是性能优化，不该成为新的单点故障。

- 新增 `tests/test_share_scp_tar.py`：覆盖 ① tar 打包产物可被解开且文件数与源一致
② 打包后单次 scp 的 argv 里只有 1 个源文件 ③ 远端解包文件数不符 ⇒ 失败
④ tar 打包异常 ⇒ 回退逐文件 ⑤ 安全校验（`..` 路径、`-` 开头文件名）在 tar 路径上
仍然生效。


## Capabilities

### New Capabilities


### Modified Capabilities

- **share-transport-performance**：经验回传 scp 通道的传输效率与成败判据：从「逐文件 scp」改为「tar 打包 + 单次传输
+ 远端解包」，并补齐「远端解包后文件数校验」（防解包不完整被当成功）与
「tar 失败自动回退逐文件」（防优化变成新单点故障）。


## Success Criteria

- [ ] SC-01：`_pack_tar()` 存在，能把 N 个文件打成单个 .tar.gz，解包后文件数与内容与源一致
- [ ] SC-02：`_scp_dir()` 走 tar 路径时，scp 命令行**只有 1 个源文件**（tar 包本身）
- [ ] SC-03：112 个文件场景下，tar 路径的实测耗时 < 30 秒（当前逐文件为 5m19s）
- [ ] SC-04：远端解包后文件数与本地不一致时，返回失败（不是假成功）
- [ ] SC-05：tar 打包异常时自动回退逐文件，且 reason 里标注回退
- [ ] SC-06：批次目录命名与远端布局不变（`{node_id}-experiences-{YYYYmmdd-HHMMSS}`）
- [ ] SC-07：既有 `tests/test_share_ssh_transport.py` 全部用例通过（或只改因实现变更必须改的断言，并注明理由）
- [ ] SC-08：新增测试 ≥ 5 个，覆盖打包/单次传输/数量校验/回退/安全校验
- [ ] SC-09：全量门禁 0 failed
