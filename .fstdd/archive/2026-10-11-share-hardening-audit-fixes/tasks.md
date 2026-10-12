# 2026-10-11 任务清单

> change: 2026-10-11-share-hardening-audit-fixes
> 6 切片 / 22 TC / 10 REQ。执行顺序 = Slice 1 → 6（串行）。

## 1. 脱敏规则补漏 + 第二层防线同源（C1 / REQ-001，P0）— Slice 1

- [x] 1.1 `SANITIZE_RULES` 增 3 条：AWS Secret Access Key（40 字符 base64，带 `aws_secret_access_key` 上下文）
- [x] 1.2 `SANITIZE_RULES` 增 URL 认证参数（`?api_key=` / `?token=` / `?password=` / `?secret=` / `?access_token=`）
- [x] 1.3 `SANITIZE_RULES` 增 SSH 私钥路径（`~/.ssh/id_rsa|id_ecdsa|id_ed25519|id_dsa|authorized_keys|known_hosts`）
- [x] 1.4 `OUTBOUND_RESIDUAL_RE` 同源对齐三类形态；**用 `re.compile(pat, re.IGNORECASE)`，绝不用内联 `(?i)`**
- [x] 1.5 测试：`sanitize()` 三类形态正断言 + `OUTBOUND_RESIDUAL_RE` 常量直断言（SC-004）+ 既有 `tests/test_share_publish_sanitize.py` 保持绿（TC-SEG-001..005）

## 2. scp 目标注入防护 + token 权限告警（C2/C3 / REQ-002,003，P0/P1）— Slice 2

- [x] 2.1 新增 `_validate_remote_path(path, label) -> (ok, err)`：白名单 `[\w.@:/-]` + 拒绝 `..` 段
- [x] 2.2 `_scp_dir()` 入口对 `remote_dir` / `ssh_alias` / `FSTDD_NODE_ID` 三处校验，不合法降级
- [x] 2.3 新增 `_check_token_file_permissions(path, label)`：`st_mode & 0o077` 过宽则 `[WARN]` + `chmod 600` 建议；**仅告警不阻断**；`os.name == "nt"` 跳过
- [x] 2.4 `find_token()` / `inbox_token()` 读取前调用 2.3
- [x] 2.5 测试：注入形态拒绝（TC-SEG-006）+ 合法值放行（TC-SEG-007）+ 权限告警不抛异常（TC-SEG-008）

## 3. publish pre_staged + 重命名 + 测试桩同步（C4/C5 / REQ-004，P0）— Slice 3

- [x] 3.1 `publish(out_dir, repo, token="", pre_staged=False)`：`pre_staged=True` 跳过内部 `stage_sanitized()` 且不清理传入目录
- [x] 3.2 默认 `pre_staged=False` 保持 3 位置参数调用行为不变（`inbox_pull.py` 调用点零改动）
- [x] 3.3 `SCP_LIKE_RE` → `SCP_SYNTAX_RE`（模块内 2 处引用同步）
- [x] 3.4 **同步更新 `upstream/tests/test_silent_share.py` 测试桩**（3 处：`fake_publish`、403 降级 lambda、010c 凭据回显 lambda）
- [x] 3.5 测试：`pre_staged` 不二次脱敏不删目录（TC-SEG-009）+ 旧调用形态行为不变（TC-SEG-010）+ `test_silent_share.py` 全绿（TC-SEG-011）+ `git_remote` 语义不变（TC-SEG-012）

## 4. strip_frontmatter + 安全策略模板化（C7/C8 / REQ-005,006，P0/P1）— Slice 4

- [x] 4.1 `strip_frontmatter()` 改逐行扫描：只在**行首恰为 `---`** 处收尾；找不到则返回原文
- [x] 4.2 新增 `_render_template(name, ctx)`：Jinja2 渲染 `tools/templates/<name>.md.j2`；缺文件返回 `""`
- [x] 4.3 新增 `tools/templates/{security_note_deliver,security_block_deliver,upgrade_duty}.md.j2`（内容 = 原常量，**逐字节等价**）
- [x] 4.4 三处调用改走 `_render_template`，**保留原常量作为 fallback**
- [x] 4.5 测试：`strip_frontmatter` 内含 `---` 边界（TC-ISR-001）+ 无结束标记原样返回（TC-ISR-002）+ 端到端哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 在位（TC-ISR-003，**隔离输出目录**）+ 缺模板回落 `""`（TC-ISR-004）

## 5. CLI 冒烟超时 + install.sh 参数校验 + 源根深度上限（C9/C10/C6 / REQ-007,008，P1）— Slice 5

- [x] 5.1 `verify_workbuddy_skills.py` 各子命令 `subprocess.run(..., timeout=SMOKE_TIMEOUT)`（默认 30s）；超时返回 `(False, "...超时（30s）...")`
- [x] 5.2 `install.sh`：`--py` / `--platform` 缺参或后接另一选项 → `[FAIL]` + `exit 2`；未知参数 → `[WARN]` 不中断
- [x] 5.3 `upstream/fstdd/cli/utils.py`：新增 `_find_source_root(start, max_depth=50)`，`p.parent == p` 时抛错，超限抛含深度的 `RuntimeError`
- [x] 5.4 测试：超时路径（TC-ISR-005，mock hang）+ `install.sh --py` exit 2（TC-ISR-006）+ 未知参数 WARN（TC-ISR-007）+ 深度上限抛错（TC-ISR-008）

## 6. 金融红线补充 + 不回归（C11 / REQ-009,010，P1/P0）— Slice 6

- [x] 6.1 `skills/fstdd-fin/SKILL.md` 红线 7 增「费率/限额变更必须版本化配置（带生效时间与审批记录），禁止热更新直接覆盖」
- [x] 6.2 交付清单增「灾备演练 RTO ≤15min / RPO ≤5min，结果写入运维 Runbook」
- [x] 6.3 测试维度「幂等」增「并发幂等键冲突测试方法（数据库唯一约束 vs 应用层检测）」
- [x] 6.4 测试：关键措辞检索（TC-ISR-009）；**只增不改既有行**，`tests/test_finance_content.py`(17) 保持绿

## 7. 测试与验证（Part C）

- [x] 7.1 各切片 per-slice 验证（TC 覆盖 + 产出物核对 + 测试通过）→ 已写入 `.fstdd.yaml` `phases.build.slices_completed`
- [x] 7.2 全量 pytest 通过（`upstream/tests` + 根 `tests`；唯一允许 `test_a6` 结构性红）（TC-ISR-010）
- [x] 7.3 C1 多路并行技术评审（代码/测试/文档 3 代理）
- [x] 7.4 C2 全量质量检查（pytest + lint + `ci check-failures`）
- [x] 7.5 C3 Diff 审查（逐文件）
- [x] 7.6 C4 失败模式检查（23 类逐项）
- [x] 7.7 C5 经验库自动记录 / C6 design-adjustments / C7 test-report.md
- [ ] 7.8 Gate 3 用户确认

## 8. 附带修复（非计划内，回归阻塞）

- [x] 8.1 刷新裸 except 审计活表到本 change 目录（`audit/except-points.yaml`，承接 25 点，`utils.py` 2 处行号位移）→ 修 `test_aud_002` / `test_grd_001`
- [x] 8.2 `tests/test_experience_sync_tc_traceability.py` 支持 `archive/` 路径（上一 change 归档后 3 用例 FileNotFoundError）
- [x] 8.3 新增 `tests/test_share_hardening_tc_traceability.py`（22 计划 TC 冻结 + 双树扫描）
