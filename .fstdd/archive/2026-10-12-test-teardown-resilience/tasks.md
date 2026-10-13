# change 2026-10-12-test-teardown-resilience 任务清单

## 1. test-teardown-resilience（P0）— Slice 1：韧性层

- [x] 1.1 在 `tests/conftest.py` 的 `pytest_configure` 内新增删除原语包装安装函数（`os.remove` / `os.unlink` / `shutil.rmtree`）
- [x] 1.2 包装体：捕获 `SystemExit` → `warnings.warn(含目标路径)` + 全局计数 → 正常返回（降级为告警）
- [x] 1.3 包装体：**只放行 `SystemExit`**；其余异常原样抛出（反向守卫，不得 `except Exception`）
- [x] 1.4 注册 session 级汇总输出（固定前缀 `[teardown-resilience]` + 捕获次数）
- [x] 1.5 新增 `tests/test_teardown_resilience_capture.py`：TC-TTR-001（捕获不抛）、TC-TTR-002（收尾不中断）
- [x] 1.6 新增 `tests/test_teardown_resilience_visibility.py`：TC-TTR-003（warning 含路径）、TC-TTR-004（汇总计数）
- [x] 1.7 新增 `tests/test_teardown_resilience_real_exception.py`：TC-TTR-005（真实异常照抛 + 断言源码无宽捕获）
- [x] 1.8 运行本切片测试 → 确认 **RED**（4 failed）→ 实现 → 确认 **GREEN**（11 passed）
- [x] 1.9 跑全量 `pytest tests` 确认无回归（**215 passed, 6 skipped**）

## 2. test-teardown-resilience（P0）— Slice 2：规避层 + 症状加固

- [x] 2.1 在 `tests/conftest.py` 的 `pytest_configure` 内把 `TMP` / `TEMP` / `TMPDIR` 指向**仓库之外**的中立目录（可写）
- [x] 2.2 新增 `tests/test_teardown_resilience_tmp_neutral.py`：TC-TTR-006（三变量均指向仓库外且可写）
- [x] 2.3 `tests/test_verify_notices_default_safe.py` L95 / L263：`d.mkdir()` → `d.mkdir(exist_ok=True)`
- [x] 2.4 新增/改造用例覆盖 TC-TTR-007（目标目录已存在时不抛 FileExistsError）
- [x] 2.5 运行本切片测试 → RED（4 failed）→ 实现 → GREEN（12 passed）
- [x] 2.6 跑全量 `pytest tests` 确认无回归（**221 passed, 6 skipped**）

## 3. 验证类 TC（Part C 执行，不占切片）

- [ ] 3.1 TC-TTR-008：连续 3 次全量 `pytest tests -q -p no:cacheprovider --basetemp=<每次全新>`，比对 failed/errors 数一致
- [ ] 3.2 TC-TTR-009：`git diff --name-only` 白名单核对 —— **不含 `upstream/`**

## 4. 质量验证（Part C）

- [ ] 4.1 C1 多路并行技术评审（3 代理：代码 / 测试 / 文档）
- [ ] 4.2 C2 全量质量检查（pytest + `ci check-failures`）
- [ ] 4.3 C3 Diff 审查（逐文件）
- [ ] 4.4 C4 失败模式检查（23 类全量）
- [ ] 4.5 C5 经验库记录/更新
- [ ] 4.6 C6 汇总设计调整（`design-adjustments.yaml`）
- [ ] 4.7 C7 生成 `test-report.md`

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->
