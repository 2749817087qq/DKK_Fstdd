# WBCC-0803ADF7-EXP-2026-0021 — Windows `write_text` 静默把 LF 写成 CRLF，污染生产副本 diff

- pattern: 在 Windows 上用 `pathlib.Path.write_text(src)` 回写从 Linux 生产
  scp 下来的源文件副本（补丁脚本场景）。读入时 `read_text` 走 universal
  newlines（CRLF→LF 归一），写出时 `open(mode="w")` 又把 `\n` 翻译成
  `os.linesep`（CRLF）——**往返一次，行尾全变**。而 baseline 副本保持 LF，
  于是 `diff baseline impl` 退化成 `1,601c1,678` 全文件差异，
  真实的 77 行新增被噪声吞掉；`ruff`/`pytest` 全绿，毫无察觉。
- root_cause: `text=True`/`write_text` 的 newline 翻译是**隐式**的——
  不报错、不警告，只在 diff 与字节级检查时显形。症状高度误导：
  看起来像"整个文件被动过"，排查方向会跑向"补丁脚本误写全文"，
  而不是"行尾被翻译"。
- fix_template:
  1. 回写生产同源副本一律 `write_bytes(data.replace(b"\r\n", b"\n"))`，
     即先 `read_bytes()` 全程二进制处理，或在 `open()` 上传 `newline=""`；
  2. 补丁脚本落地后**必须**跑一次 `diff baseline impl | grep -c '^[<>]'`
     做体量 sanity check：diff 行数 ≈ 预期新增行数，数量级不对立即停；
  3. 判别"行尾污染 vs 真全文件改动"用 `diff --strip-trailing-cr`：
     数字骤降（本例 1279→77）即为 CRLF 污染；
  4. 字节普查一次背书全仓：`CRLF 计数 == 总行数` 即全 CRLF；
     同文件 impl 与 baseline 行尾不一致本身就是 red flag。
- severity: medium（不致命但污染证据链；若带着 CRLF 部署到 Linux，
  功能不受影响但 diff 审查与后续 hotfix 对线全乱）
- status: verified
- tags: [windows, crlf, line-endings, write-text, diff-noise, patch-script]
- related: EXP-2026-0017 (Windows 信号), EXP-2026-0009 (silent contract)
- first_seen: 2026-10-19 (change 2026-10-19-pipeline-defects-trio 切片 C GREEN)
- evidence: >-
  `impl/operation_metrics_loader.py` 补丁后 CRLF=678/678 全 CRLF，
  baseline LF=601；`diff --strip-trailing-cr` 后真实差异 77 行纯新增。
  A/B 切片 impl 与 baseline 均 LF（此前补丁走不同写入路径），
  故仅切片 C 中招。
