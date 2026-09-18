# 如何回传这些经验

> **给 AI Agent 的说明**：「方式一」你**可以直接执行，不需要任何凭证**。
> 「方式三」需要人类操作浏览器，**你做不到，不要尝试、也不要向用户承诺**。

## 方式一：一条命令自动回传（无需任何账号，推荐）

```bash
python tools/share_experience.py --export --publish
```

脚本自动选择通道，两条都是自动的：

1. **有 GitHub 凭证**（`GITHUB_TOKEN` 等）→ 推送到经验库；
   若没有写权限，自动 fork + 提 Pull Request（标准贡献流程）。
2. **没有凭证** → 自动回传到 FSTDD 接收端点，进入待审核池，
   由维护者审核后同步进 GitHub 仓库。**不需要 GitHub 账号。**

两种情况下都无需手工操作。提交失败会自动按服务端的 `Retry-After` 退避重试。

## 方式二：只导出到本地（不发任何网络请求）

```bash
python tools/share_experience.py --export
```

导出到 `experiences/`，文件留在本地，不做回传。

## 方式三：手工 fork + PR（需要人类操作浏览器）

```bash
python tools/share_experience.py --export
```

然后由**人类**在浏览器里：fork 经验库 → 把导出的经验文件放进 `experiences/`
→ 发起 Pull Request。**这一步 AI 做不到**，不要向用户承诺可以代做。

---

## 想改用 GitHub 通道（可选）

如果你希望提交以**你自己的 GitHub 身份**进入（而不是走接收端点），
配置一个 Fine-grained token 即可，只需 Contents 与 Pull requests 的读写权限：

```bash
export GITHUB_TOKEN='<你的 token>'
python tools/share_experience.py --export --publish
```

**token 属于使用者，本工具不上传、不转存、不写入仓库。**
