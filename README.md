# STDD — WorkBuddy 适配层与金融扩展

> 上游 [leonai42/stdd](https://github.com/leonai42/stdd) V3.0.5（MIT）的衍生作品。
> 本仓库**只包含我们自己的改动层**，不复制上游那 900 多个文件——上游内容请从其原仓库获取。
> 版权与来源的完整说明见 [`NOTICE.md`](./NOTICE.md)。

## 这是什么

STDD = **Spec 先行 + TDD 执行**：先定义行为规格（GIVEN/WHEN/THEN），再写测试，最后实现代码。
四阶段 + 三道强制用户确认门，把模糊需求变成有据可查、有测可验的交付。

本仓库解决的是**上游装到 WorkBuddy 上不好用**的问题，以及金融系统场景的扩展：

| 问题 | 解决 |
|------|------|
| 上游 WorkBuddy 安装器输出到 `~/.workbuddy/skills/*.md`，实际加载目录是 `~/.workbuddy-ai/skills/<name>/SKILL.md` | `tools/install_workbuddy_skills.py` 改为目录格式 |
| skill 正文里的项目相对路径全局安装后解析不了 | 安装时固化为绝对路径 |
| CLI 依赖 PyYAML/Jinja2，默认解释器可能没有 | 绑定到具备依赖的解释器 |
| Deliver 阶段会**自动向外部社区仓库上传项目经验** | 默认禁用 + 哨兵 + 校验脚本 |
| **升级会静默覆盖 skill，把上述策略全部抹掉** | 三层防护 + 升级后强制重跑规程 |
| 金融系统研发缺领域约束 | `skills/stdd-fin/SKILL.md` |

## 目录结构

```
.
├── LICENSE                          # 本仓库原创内容的 MIT 许可
├── UPSTREAM-LICENSE.txt             # 上游 STDD 的 MIT 许可原文（合规保留）
├── NOTICE.md                        # 版权与来源声明（重要）
├── tools/
│   ├── install_workbuddy_skills.py  # 生成适配后的全局 skill + 施加安全策略
│   └── verify_workbuddy_skills.py   # 校验策略哨兵与路径适配是否仍在位
├── docs/
│   └── WORKBUDDY_INSTALL_NOTES.md   # 安装、适配、安全策略、验证记录
└── skills/
    └── stdd-fin/SKILL.md            # 金融系统版 STDD（原创重构）
```

## 安装使用

```bash
# 1. 先获取上游 STDD（本仓库不含上游代码）
git clone https://github.com/leonai42/stdd.git

# 2. 运行安装脚本，生成 WorkBuddy 全局 skill
python tools/install_workbuddy_skills.py

# 3. 校验（升级后必跑）
python tools/verify_workbuddy_skills.py
```

脚本顶部的 `SRC` / `OUT` / `PY` 三个常量需按本机实际路径调整
（当前硬编码为 Windows + `C:\Python311\python.exe`）。

## 升级后必做

任何升级 / 重装 / 手动覆盖 skill 文件之后，**必须**重跑安装 + 校验两步，
否则安全策略与路径适配会被静默抹掉：

```
python tools/install_workbuddy_skills.py
python tools/verify_workbuddy_skills.py   # FAIL 时禁止继续 DELIVER 相关操作
```

## 关于 stdd-fin

金融系统版 STDD（代号 FinSTDD）。把金融科技工程能力翻译成 STDD 流程中的
**强制规格项与验收项**——落在流程之外的知识等于不会被执行的知识。

核心增值：数据契约、口径定义表、合规与审计契约（三份契约 Gate 2 锁定）；
静默降级、重复扣款、账实不符等 8 类金融系统特有失败模式的拦截点。

## 许可

- 本仓库原创内容：**MIT**（见 `LICENSE`）
- 上游 STDD：**MIT**，版权归 杭州大道一以科技有限公司（见 `UPSTREAM-LICENSE.txt`）
- `fintech-engineer`：**无开源许可**，本仓库**不含其原文**，仅参考领域视角并署名（见 `NOTICE.md`）
