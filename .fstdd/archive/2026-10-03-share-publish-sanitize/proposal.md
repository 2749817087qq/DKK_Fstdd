# 经验出站强制脱敏收口（publish_via_inbox / scp / GitHub 发送前 sanitize）

<!-- source_hash: 00c6a7ed72b1782e -->
<!-- generated_at: 2026-10-03T10:53:45+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-share-publish-sanitize.yaml -->

## Why

`tools/share_experience.py` 的出站路径直接读取 `experiences/` 目录下的**原始文件**
并外发，不再过 `sanitize()`：
  · `publish_via_inbox`（L626-638）逐条 `f.read_text()` 直发；
  · `publish_via_scp`（L575+）把整个 out_dir 原样 scp 到服务器；
  · `publish()` 的 GitHub 分支（L834-836）用 `shutil.copy2` 原样拷贝。
该目录本应只放 `prepare_entries()` 产出的脱敏文件，但一旦混入**未经本流水线**
的文件（如手工放入的 `experiences/FSTDD003-EXP-*.md`），原始路径/凭证片段就会
被直接外发。实测事故：`FSTDD003-EXP-20261002-03` 含 `/home/ubuntu/...` 与一段
token 片段，被 inbox 服务端以 `contains POSIX home path` 拒收。


## What Changes

- 新增 `stage_sanitized(out_dir) -> Path`：把 out_dir 下经验文件逐条读入、经 `sanitize(text, True)` 强制脱敏后写入临时目录并返回；同时内置**出站残余自检**（复刻服务端同款判据 `/(?:home|Users)/` + 已知凭证模式），命中残余则该条不进入 stage 并记录原因
- 三条出站路径统一改为经 `stage_sanitized()` 收口：`publish_via_inbox` 用 stage 内容发送；`publish_via_scp` 改为先 stage 再 scp stage 目录（不再直发原目录）；`publish()` 的 GitHub 分支从 stage 目录 copy（替换 `shutil.copy2(f, ...)` 原文件）
- 新增回归测试 `tests/test_share_publish_sanitize.py`：以含 `/home/ubuntu/...` 与 token 片段的样本文件驱动三条出站路径，断言出站内容不含 POSIX home path 与已知凭证模式；并断言正常文件正文不被误伤（语义保持）
- 重跑 DELIVER 静默回传（--export --publish --silent）验证端到端无残留、无 4xx 拒收，并核对 .fstdd/share-audit.yaml 记录正常

### New Capabilities

- **share-outbound-sanitize**：经验回传的出站收口：任何经 share_experience 发送的内容（inbox POST / scp / GitHub）在离开本机前强制脱敏，且脱敏不可被 --no-sanitize 绕过

## Success Criteria

- [ ] 对含 `/home/ubuntu/...` 与 token 片段的样本，经 `publish_via_inbox` 发送的 body 不再含 `/(?:home|Users)/` 与已知凭证模式，服务端返回 accepted（非 4xx 拒收）
- [ ] `publish_via_scp` 与 GitHub 分支的拷贝源为 stage 目录，且 stage 内容已脱敏（测试可断言）
- [ ] `tests/test_share_publish_sanitize.py` 全绿；`pytest tests/` 无回归
- [ ] `--export --publish --silent` 端到端成功，`.fstdd/share-audit.yaml` 记录正常
- [ ] 三条出站路径的代码中不存在对 `experiences/` 原始文件『读后直发』的调用（grep 可验证）
