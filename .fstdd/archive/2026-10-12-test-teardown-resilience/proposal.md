# 测试收尾韧性 —— 让 fixture teardown 不被沙箱删除守卫的 SystemExit 打断

<!-- source_hash: be9febec942f7387 -->
<!-- generated_at: 2026-10-12T13:55:57+00:00 -->
<!-- canonical: canonical/proposals/2026-10-12-test-teardown-resilience.yaml -->

## Why

门禁数**不可判**：同一 HEAD、同一命令，不同执行者拿到不同的失败数。
实测（2026-10-12 闭合度验证）：主理人跑 `pytest tests upstream/tests/test_repo_home.py`
得 **5 failed / 1 error**，质量门神跑同一命令得 **4 failed / 17 errors** —— 差异全因沙箱
的 `safe-delete` 守卫是否触发。

根因链（已逐环坐实）：
  ① 沙箱 shim（**仓外**）在删除失败时 `raise SystemExit(1)`
     —— `D:/Program Files/WorkBuddyAI/resources/app.asar.unpacked/cli/vendor/shim/sitecustomize.py:848`；
  ② 该异常若落在 pytest **fixture teardown** 的 `Path.unlink()` / `shutil.rmtree()` 里；
  ③ pytest 的 `TEST_OUTCOME` 元组**不含 `BaseException`** ⇒ `SystemExit` 不被捕获
     ⇒ **fixture 收尾中断**（后续 teardown 步骤被跳过）；
  ④ 后果：临时目录未被清理 / 测试间状态被污染 ⇒ 后续测试在
     `d.mkdir()`（无 `exist_ok`）上抛 `FileExistsError`
     （实测点：`tests/test_verify_notices_default_safe.py:95` 与 `:263`）。

危害不是「多几个红」，而是**判据失效**：抖动会把**真红**淹在噪声里，也会把**假红**当真问题
消耗排查；且 DELIVER 的放行判据（「全量 0 failed」）在抖动下**无法被客观回答**。


## What Changes

- `tests/conftest.py` 增加 **teardown 韧性层**：在 pytest 的收尾阶段捕获
`BaseException`（含 `SystemExit`），使其**不中断 fixture teardown**，
同时以**可见方式**（warning / 报告项）暴露 —— 不得静默吞掉。
实现形态在 Phase 2 定（候选：`pytest_runtest_makereport` hook 包裹 / 自定义
`pytest_exception_interact` / 对 `shutil.rmtree`+`Path.unlink` 的受控包装）。

- `tests/test_verify_notices_default_safe.py` 的 2 处 `d.mkdir()`（L95 / L263）
改为对「目录已存在」鲁棒（`exist_ok=True`）—— 使测试不因上一测试的残留而失败。

- 新增回归测试：**以 monkeypatch 模拟 shim 抛 `SystemExit`**，断言
「① fixture teardown 不被中断；② 该异常可见（非静默）；③ 后续测试不受污染」。
使本 change 的判据**不依赖环境是否恰好触发守卫**（可在任意环境稳定复现）。

- 在 change 的 `test-report.md` 中记录**确定性判定法**（连跑 N 次全量的 failed/errors
是否一致），作为门禁可判性的证据留痕。


## Capabilities

### New Capabilities

- **test-teardown-resilience**：测试收尾对**外部删除守卫**的韧性：fixture teardown 在遭遇 `SystemExit`（来自仓外 shim）
时仍能完成收尾、不污染后续测试，且异常可见。


### Modified Capabilities


## Success Criteria

- [ ] SC1 模拟 `SystemExit`（monkeypatch）时，受影响测试的 fixture teardown **不被中断**（收尾步骤全部执行）
- [ ] SC2 被捕获的 `SystemExit` **可见**：测试报告中出现明确的 warning/条目（不得静默）
- [ ] SC3 反向守卫：真实的 teardown 异常（非 SystemExit）**仍须导致测试失败**
- [ ] SC4 `tests/test_verify_notices_default_safe.py` 在「目标目录已存在」时**不再** `FileExistsError`
- [ ] SC5 连续 3 次全量 `pytest tests` 的 **failed / errors 数完全一致**（确定性）
- [ ] SC6 本 change **未触碰 `upstream/`**（`git diff --name-only` 白名单核对）
- [ ] SC7 全量根级测试在守卫未触发时为 **0 failed / 0 errors**（与改动前一致）
