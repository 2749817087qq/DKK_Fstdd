# skill 发布前检查清单

> 适用：仓库从 PRIVATE 转 PUBLIC、或发布新版本 skill 之前
> 原则：每一项都给出**可执行命令**与**明确判据**，不接受"看起来没问题"

---

## 1. 许可声明

**检查内容**：每个 skill 的 `license` 字段是否存在、是否与真实来源一致。

```bash
python tools/check_skill_metadata.py
```

**通过判据**：

- `license 缺 0`（全部 skill 均有声明）
- 值为 `unknown` 的 skill 需人工确认来源后再决定是否发布
- 衍生自上游的 skill，其 `license` 必须写明上游协议与版权方

**注意**：`unknown` 表示"已检查但确知未知"，**不等于**"可以当 MIT 用"。
含 `unknown` 的 skill 公开前必须先人工核实。

---

## 2. 凭证扫描

**检查内容**：确认 skill 与仓库中不含硬编码凭证。

```bash
grep -rlE "ghp_|github_pat_|ghu_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer [A-Za-z0-9._-]{20,}" ~/.workbuddy-ai/skills/ ~/.workbuddy/skills/
```

**通过判据**：

- 无输出（0 命中）
- 有输出时逐条人工确认。已知误报模式：`ghu_statis`（"longhu_statis" 中的子串）
- 命中真实凭证 → 立即 revoke 该凭证，**不要**仅删除文件（Git 历史仍可恢复）

---

## 3. 跨机器路径检查

**检查内容**：确认 skill 中没有写死本机绝对路径。

```bash
grep -rn "C:\\\\Users\\\\\|C:/Users/" ~/.workbuddy-ai/skills/ | grep -v "^Binary"
```

**通过判据**：

- 每个命中都要么（a）属于本机适配文档中的**安装位置说明**，要么（b）已通过
  `STDD_SRC` / `STDD_OUT` 环境变量可覆盖
- 出现在可执行命令中的路径，必须能由 `install_workbuddy_skills.py` 按当前位置重新生成

**验证方式（换机模拟）**：

```bash
STDD_SRC=/tmp/fake-upstream STDD_OUT=/tmp/fake-skills \
  python tools/install_workbuddy_skills.py
```

能正常生成且不残留旧路径，才算通过。

---

## 4. 端到端冒烟

**检查内容**：CLI 实际能跑，而不只是文件在位。

```bash
STDD_PY="C:/Python311/python.exe" \
  python ~/.workbuddy-ai/DKKstdd/tools/verify_workbuddy_skills.py
```

**通过判据**：

- 输出含 `[PASS] CLI 冒烟：init / new / status 均通过`
- 退出码为 0
- 门禁有效性反向验证（确认它真的会拦）：

```bash
STDD_CLI=/nonexistent/stdd STDD_PY="C:/Python311/python.exe" \
  python ~/.workbuddy-ai/DKKstdd/tools/verify_workbuddy_skills.py
echo "退出码应为非 0，实际: $?"
```

---

## 5. 元数据校验

**检查内容**：四项元数据齐全，且修改过程未损伤正文。

```bash
python tools/check_skill_metadata.py          # dry-run
python tools/check_skill_metadata.py --fix    # 备份后修复
python tools/verify_skill_standards.py --repo .
```

**通过判据**：

- `四项齐全: 40/40`
- `--fix` 前自动备份到工作区 `<工作区>/backups/skill-metadata-<时间戳>/`
  （项目约定：开发产物一律存放在工作区文件夹内；可用 `STDD_BACKUP_DIR` 覆盖）
- 备份文件数 == 待改文件数（不等即中止）
- 修复后正文哈希与备份一致（只动了 frontmatter）
- `verify_skill_standards.py` 输出 `7/7 通过`

**回滚**：

```bash
python tools/check_skill_metadata.py --revert
```

---

## 附：发布决策

| 检查项 | 未通过时 |
|---|---|
| 许可声明 | **阻断发布** —— 合规风险不可接受 |
| 凭证扫描 | **阻断发布** —— 立即 revoke 并清理历史 |
| 跨机器路径 | 阻断 —— 他人安装即失效 |
| 端到端冒烟 | 阻断 —— 装了也用不了 |
| 元数据校验 | 视情况 —— `unknown` 需人工核实后决定 |
