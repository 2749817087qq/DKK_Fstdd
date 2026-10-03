# 清零 6 项预存基线 pytest 失败 - 技术设计

## Context

- 仓库：`e:\FSTDD\stdd-repo`（F 侧），观测基线 HEAD `e7bfb45`，工作树除本变更外干净。
- 解释器：`C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`（3.13.14，含 PyYAML 6.0.3）。
- 基线实测：`python -m pytest upstream/tests -q` → `6 failed, 867 passed, 54 skipped`。
- 发布规程 `.fstdd/standards/release-and-docs.md` §三 要求「全量测试 0 failed」+「四自检脚本全绿」方可 tag；当前 6 项常红使该硬门禁无法成立。
- 6 项失败的根因归为 4 类，均为**存量偏离**，非本变更引入。

## Decisions

### 1. 模板双源：以项目副本为准，补齐镜像，而非反向

**方案**：将 `.fstdd/templates/` 的 `canonical/proposal.yaml`、`canonical/spec.yaml`、`test-plan.md` 三文件覆盖到 `upstream/.fstdd/templates/` 同相对路径。

**为什么**：`git diff` 证实差异方向是单向的——项目副本已含 finance 段（proposal 的 7 红线 / spec 的 10 维测试 / test-plan 的第七章），镜像侧完全没有。`upstream/` 是**对外分发的模板镜像**，缺段落意味着分发出去的模板是残次品。故应向镜像补齐，不能反向删掉项目副本的 finance 段。

**备选方案及排除原因**：
- 备选 A：把镜像侧当权威、删项目副本 finance 段 → 排除。会让 `fstdd-fin` 金融流程失去模板支撑（项目副本是 `fstdd new` 实际取材处，见 new.py 裁定 ISO-4「模板源始终取主仓」）。
- 备选 B：改测试为「仅比较字段集合」→ 排除。测试意图是逐字节一致，放宽等于抹掉门禁。

### 2. 审计表：新建活表（changes 优先）而非改归档表

**方案**：新建 `.fstdd/changes/2026-10-04-baseline-failures-zero/audit/except-points.yaml`，承接归档表 19 点 + 入册 6 新点 = 25 点。

**为什么**：`_default_table()` / `_audit_table_path()` 的解析顺序是 `changes` 优先于 `archive`；活表置于 active change 下、归档表保持不动，是 detection-silence-fixes 既定的 D6 决策。归档表承载历史判据，回改它等于篡改历史。

**备选方案及排除原因**：
- 备选 A：直接改归档表行号 + 加 6 点 → 排除。违反 D6；且下次再有位移会继续污染归档。
- 备选 B：为过测试而删除 6 个「多余」吞异常点（改源码去掉 except）→ 排除。为过测试而改被扫描源码，是治理课题的反面；且其中多为 fail-closed 合理容错。

### 3. 显式 publish 用例：修测试隔离性，不动生产降级逻辑

**方案**：在 `test_tc_cas_008b` 内 `monkeypatch.setattr(SHARE, "publish_via_scp", lambda *a, **k: (False, "isolated-for-test"))`。

**为什么**：`publish()` 的优先级 1 是 scp（`ssh fstdd-hub`），本机 F 侧具备该别名 → scp 真跑成功 → `main()` 返回 0，断言 `== 1` 失败。这是**测试非 hermetic**（依赖运行环境），不是产品缺陷：`main()` 尾部 `return 0 if ok else 1` 的属性本身正确。隔离 scp 后强制降级到 inbox 死端口，才真正验证「显式命令失败→非零」。

**备选方案及排除原因**：
- 备选 A：改 `main()` 让它恒返回 1 → 排除。会破坏静默路径零阻塞与显式路径成功返回 0 的既有语义。
- 备选 B：把 scp 通道删掉 → 排除。scp 是生产优先通道，不能为测试牺牲。

### 4. naive 时间戳：值层补 UTC 后缀、源层 aware、标识符入豁免

**方案**：
- L1 值层：notices-authenticity-gate 的 8 处值补 `+00:00`（`.fstdd.yaml` 3 + canonical proposal/spec ×4 + proposal.md 头部 1）。
- L2 源层真时间戳：`tools/heartbeat.py:60`、`tools/fstdd003_daily_share.py:194` 改为 `.astimezone()`（aware，保留本地墙钟）。
- L2 源层标识符：`hub_client.py` / `share_experience.py` / `verify_notices.py` 3 处日期片段补 `EXEMPTIONS`（category=identifier）。

**为什么**：检测器 L1 判「产出的值」、L2 判「无参 naive 调用且未豁免」。值层按仓库既有 UTC 约定（`timeutil.utc_now_iso`）补 `+00:00`，口径统一；源层对真时间戳用 `.astimezone()` 产出带偏移的本地时间（保留日志可读性，检测器的 aware 标记判据 `("timezone","tz=")` 命中 `.astimezone()`）；对文件名/ID 的日期片段一律入豁免清单并附理由（TC-TSN-006 保证可定位）。

**备选方案及排除原因**：
- 备选 A：把 3 处标识符也改成 aware → 排除。会改变文件名/ID 形态（如批次目录名、隔离后缀），属过度修复。
- 备选 B：直接把 8 个值改成当前时间重写 → 排除。篡改历史时间语义；只补后缀最小。

## Architecture

```
修复面                              载体                                          验证
─────────────────────────────────────────────────────────────────────────────────────
① 模板双源        .fstdd/templates → upstream/.fstdd/templates (3 文件)      test_tmpl_001 / test_epr_003
② 审计活表        .fstdd/changes/<id>/audit/except-points.yaml (25 点)       test_aud_002 / test_grd_001
③ publish 隔离    upstream/tests/test_silent_share.py（1 处 monkeypatch）     test_tc_cas_008b
④ naive 清零      .fstdd/changes/.../notices-.../(值层 8) + tools/(源层 2+3)  test_tsn_007 / test_tsn_005/006
                        ↓
              全量 pytest + 四自检脚本（verify_rename / verify_eol / verify_skill_standards / verify_workbuddy_skills）
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 审计表刷新时把「行号位移」误判为「新增点」，导致指纹集合不等 | 逐点核对 (file, stmt, handler) 指纹；新点仅限实况扫描确无表项的 6 处；以 `audit --check` 哨兵复核 |
| 补时区后缀被质疑「是否原本就是本地时间」 | 统一按仓库既有 UTC 约定（`timeutil.utc_now_iso`）补 `+00:00`，不引入本地偏移造成口径分裂；变更范围最小 |
| 源层 `.astimezone()` 仅被检测器「标记命中」是否属规避 | 该改造确实产出 aware 值（带偏移），非仅加标记；heartbeat 保留 `%z` 偏移、daily_share 用 isoformat 自带偏移 |
| 用例加入 monkeypatch 后被指「为过测试而改测试」 | 属性（显式失败→非零）本身正确且已覆盖；改动仅消除**环境依赖**，属测试质量修复，记入 design-adjustments.md 偏离 |
| 跑全量测试回写 `.fstdd/changes/*/.fstdd.yaml` 的 baseline 块（已知副作用） | 跑完 `git checkout` 还原非预期改动；提交前 `git status` 复核 |