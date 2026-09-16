# 如何回传这些经验

两种方式**任选其一**。方式一不需要任何 token。

## 方式一：网页提交（不需要 token，只要 GitHub 账号）

1. 打开 https://github.com/2749817087qq/Fstdd-experiences
2. 点右上角 **Fork**（在你账号下建一份副本）
3. 进入你 fork 后的仓库 -> **Add file -> Upload files**
4. 把本目录下的 EXP-*.md 全部拖入并提交（若仓库已有 experiences/，放进该目录）
5. 回到你的仓库首页 -> **Contribute -> Open pull request** -> 创建 PR

维护者审核后合并。**全程只需浏览器登录，不需要生成 token。**

## 方式二：一条命令自动提交（需要你自己的 GitHub token）

```bash
export GITHUB_TOKEN='你的 token'   # 需 repo 权限
python tools/share_experience.py --export --publish
```

脚本会自动判断身份：维护者直推，否则自动 fork -> 推送 -> 创建 PR。
**token 是你自己的，本工具不上传、不转存。**

---

## 为什么方式二需要 token？

它用 GitHub API 自动建 PR，API 调用必须有凭证。
方式一走网页，浏览器的登录态就是凭证，所以不需要 token。
两者最终都是「提 PR -> 维护者审核」，结果没有区别。
