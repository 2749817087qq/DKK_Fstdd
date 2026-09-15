# 版权与来源声明

本仓库是 **FSTDD（Spec+Test Driven Development）的 WorkBuddy 适配层与金融领域扩展**，
属于上游项目的衍生作品。所有第三方权利均在此列明，未列明的内容均为本仓库原创。

---

## 1. 上游项目：FSTDD

| 项 | 内容 |
|----|------|
| 项目 | FSTDD — Spec+Test Driven Development |
| 仓库 | https://github.com/leonai42/stdd |
| 版本 | V3.0.5（master 分支） |
| 许可 | **MIT License** |
| 版权 | Copyright (c) 2026 杭州大道一以科技有限公司 (Hangzhou Dadao Yiyi Technology Co., Ltd.) |

**权利依据**：MIT 许可允许自由使用、复制、修改、合并、出版发行、散布、再许可及销售软件副本。
**义务履行**：上游 MIT 许可全文已随本仓库保留于 [`UPSTREAM-LICENSE.txt`](./UPSTREAM-LICENSE.txt)，
原版权声明与许可声明未被移除或改动。

**本仓库对上游的改动**（详见 [`docs/WORKBUDDY_INSTALL_NOTES.md`](./docs/WORKBUDDY_INSTALL_NOTES.md)）：

1. skill 安装格式适配：上游 WorkBuddy 安装器输出 `~/.workbuddy/skills/*.md`（单文件），
   本适配改为 WorkBuddy 实际加载的目录格式 `~/.workbuddy-ai/skills/<name>/SKILL.md`。
2. 路径固化：skill 正文中的项目相对路径（`.fstdd/skills/_shared/*`、`python bin/fstdd`）
   改为绝对路径，使其可在全局安装位置工作。
3. 运行时绑定：CLI 调用绑定到具备 PyYAML / Jinja2 依赖的 Python 解释器。
4. 安全策略：默认禁用「经验自动上传社区」步骤（该步骤会向外部仓库外发项目数据），
   并加入哨兵标记与校验机制，防止升级时被静默抹除。

上述改动文件均位于 [`tools/`](./tools/) 与 [`docs/`](./docs/)，**不在上游仓库中**。

---

## 2. 第三方参考：`fintech-engineer`

| 项 | 内容 |
|----|------|
| 名称 | fintech-engineer（金融科技工程师）v1.0.3 |
| 来源 | ClawHub 市场（https://clawhub.ai），经技能市场安装至本地 |
| 许可 | **未声明任何开源许可**（无 LICENSE、无作者署名、无版权声明） |

**处理方式**：

- 该 skill **无开源许可声明**，依著作权法默认保留全部权利，**不享有转载与再分发授权**。
- 本仓库 **`skills/fstdd-fin/SKILL.md` 不包含该 skill 的任何原文内容**，未复制其段落、清单或表述。
- 仅参考其**领域分类视角**（金融系统应覆盖哪些领域），并以本仓库原创的
  「四条主线自查问题」形式重新组织。
- 涉及的金融领域术语（KYC、AML、事件溯源、Saga、PCI DSS 等）均为**行业公共知识**，
  不受个别作品专有。
- 已在 `skills/fstdd-fin/SKILL.md` 的 frontmatter 与正文中明确署名其参考来源。

> ⚠️ **注意**：本仓库对外分发时，**不得**包含 `fintech-engineer` 的 `SKILL.md` / `SKILLS.md` 原文。
> 如需使用其原始内容，请自行向权利方取得授权。

---

## 3. 第三方参考：`wb-finance-skill`

WorkBuddy 内置的金融场景总入口 skill（腾讯 WorkBuddy 产品自带组件）。
本仓库**不包含其任何内容**，仅在 `fstdd-fin` 中以协作契约方式引用其取数规范
（例如「涉及市场数据时优先使用 agentic_search」）。属于功能协作引用，不构成内容复制。

---

## 4. 本仓库原创内容

以下内容为本仓库原创，采用 MIT License（见 [`LICENSE`](./LICENSE)）：

- `tools/install_workbuddy_skills.py` — WorkBuddy 全局 skill 安装与策略施加脚本
- `tools/verify_workbuddy_skills.py` — 安全策略与路径适配校验脚本
- `docs/WORKBUDDY_INSTALL_NOTES.md` — 安装、适配、安全策略与验证记录
- `skills/fstdd-fin/SKILL.md` — 金融系统版 FSTDD（原创重构）
- 本 `NOTICE.md` 与 `README.md`

---

## 5. 免责声明

本仓库内容按「原样」提供，不含任何明示或暗示的担保。
金融相关流程与检查项仅供工程参考，**不构成合规意见或法律意见**；
实际金融系统的合规要求请以适用法域的监管机构要求与专业法律意见为准。
