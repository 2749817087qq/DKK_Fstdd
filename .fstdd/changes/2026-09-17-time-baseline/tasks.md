# 2026-09-17-time-baseline 任务清单

> 对应 `slices.md` 的 8 个切片 / 52 TC
> 执行模式：全自动长程（`full_auto`）+ `thorough`
> 优先级说明：P0 阻塞性；P1 重要；P2 可延后

## 1. 基础设施：时间工具 + `fstdd baseline` 命令载体（P0，Slice 1）

- [ ] 1.1 新建 `upstream/fstdd/cli/timeutil.py`：`utc_now_iso()` / `normalize_eol()`（单一来源）
- [ ] 1.2 新建 `upstream/fstdd/cli/commands/baseline.py`：`establish` / `show` / `check` 三个动作
- [ ] 1.3 `upstream/fstdd/cli/__init__.py` **五处注册**：`COMMAND_GROUPS` / `_CMD_HELP` /
      `add_parser` / 命令分发表（dotted string）/ 模块文件
- [ ] 1.4 新建 `.fstdd/config.d/nodes.yaml`（节点清单）与 `.fstdd/config.d/baseline.yaml`
      （`samples` / `tolerance_s` / `jitter_max_s` / `timeout_s`）
- [ ] 1.5 测试：`fstdd baseline --help` 被识别 + 三个动作各真实调用一次（**禁止 grep 判据**）

## 2. canon DC-HASH 归一（P0，Slice 2，依赖 1.1）

- [ ] 2.1 `canon.py:299` 改用 `normalize_eol()` 后计算 `DC-HASH`
- [ ] 2.2 `canon verify` 用新算法重算并比对
- [ ] 2.3 一次性迁移：活跃 change + 项目级 canonical 重生成（只改 `source_hash` 一行）
- [ ] 2.4 确认归档 change 未被回溯修改
- [ ] 2.5 测试：CRLF↔LF 往返一致、干净克隆 2/2、负向验证、变异测试

## 3. 时间戳规范统一（P0，Slice 3，依赖 1.1，串行于 Slice 2）

- [ ] 3.1 改造「写入持久化产物的时间戳字段」（约 25 处 / 15 文件）为 `utc_now_iso()`
- [ ] 3.2 **不改动** 4 类豁免：单调钟 / 标识符与目录名 / 纯时间差计算 / 渲染参数
- [ ] 3.3 实现检测器 L1（值层，权威）：产物文件中的时间字段值正则校验
- [ ] 3.4 实现检测器 L2（源层，辅助）：AST 扫描 + **数据化**豁免清单
- [ ] 3.5 豁免清单自检：每条豁免仍能在源码中定位
- [ ] 3.6 全仓扫描 naive 时间戳计数为 0

## 4. 时间基线契约（P0，Slice 4，依赖 3）

- [ ] 4.1 `.fstdd.yaml` 新增 `baseline` 块（at / base_git_sha / node_id / clock_source / established_by）
- [ ] 4.2 `gate.py`：Gate 1 确认时**同事务**写入 baseline 块
- [ ] 4.3 `baseline establish`：幂等；`--at` 可指定；`--force` 才刷新
- [ ] 4.4 `baseline show [--format json] [--check]`：结构化输出 + 退出码可区分
- [ ] 4.5 **本 change 自身回填**：`baseline.at` 取 Gate 1 的 `confirmed_at`（不得取回填动作时刻），
      `established_by: backfill`
- [ ] 4.6 `validate.py`：基线完整性检查（**warning 级，不阻断**）

## 5. 证据时效标注（P0，Slice 5，依赖 4）

- [ ] 5.1 canonical proposal 的 `why.evidence` 加 `observed_at` + `observed_base_git_sha`
- [ ] 5.2 spec 的 `evidence` 与 test-report 证据条目同样携带观测时刻
- [ ] 5.3 模板（两处）的 proposal / spec / test-report 加字段与**填写示例**
- [ ] 5.4 时效三态判定：未过期 / 早于基线 / **无法判定**（缺观测时刻时不得当作未过期）

## 6. 时钟对齐巡检（P0，Slice 6，依赖 1）

- [ ] 6.1 采样：每节点 N 次 ssh 往返，记录 `t0` / `t1` / `t_remote`
- [ ] 6.2 计算：`rtt` / `offset` / `err` / `jitter`；**取最小 RTT 样本**（非平均）
- [ ] 6.3 三态判定 → 退出码 0 / 1 / 2；`err > TOLERANCE` 时**不得**报「可接受」
- [ ] 6.4 只读与幂等：远端只执行 `date`；执行前后状态不变
- [ ] 6.5 不可达节点：标记「无法测量」、不中止、不挂起（带超时）
- [ ] 6.6 采样计数按**收到的有效读数条数**（应对本机「经 ssh 命令执行两次」）

## 7. 宪法条款 + 模板同步（P0，Slice 7，依赖 4 与 5）

- [ ] 7.1 `FSTDD_CONSTITUTION.md` 新增 `### 7. 时间基线`（编号与既有 1–6 连续）
- [ ] 7.2 **两份副本同步**：仓根 + `.fstdd/memory/FSTDD_CONSTITUTION.md`
- [ ] 7.3 逐条核对条款中的「必须」都有对应且已实现的检查
- [ ] 7.4 skill 的 Gate 前自检清单与宪法条款一致
- [ ] 7.5 7 个模板 × **2 处**（`upstream/.fstdd/templates/**` 与 `.fstdd/templates/**`）
- [ ] 7.6 新 change 默认携带基线字段与观测时刻字段

## 8. 跨切面与回归（P0，Slice 8，依赖 1–7）

- [ ] 8.1 全量 pytest：无 failed，收集数 ≥ 641
- [ ] 8.2 凭证扫描：命中数 0
- [ ] 8.3 行尾治理：`tools/verify_eol.py` 通过（无 `i/lf w/crlf`）
- [ ] 8.4 新增测试数 > 0 且 ≥ 52
- [ ] 8.5 `tools/verify_skill_standards.py` 不劣于基线（6/7）

## 9. 收尾（Slice 8 之后）

- [ ] 9.1 Phase 3 C1 多路技术评审（**顺序 3 路自审**：代码 / 测试 / 文档 —— 多 agent 已暂停）
- [ ] 9.2 C2–C7 质量验证与 `test-report.md`
- [ ] 9.3 **Gate 3 等待 D哥 确认**（强制门，不自动跳过）
