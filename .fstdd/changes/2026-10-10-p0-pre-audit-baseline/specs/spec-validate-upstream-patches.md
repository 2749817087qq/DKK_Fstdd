# spec: validate upstream-patches 检查项

**需求**: fstdd validate 新增结构级检查（决策 D-1）

## SC-1
GIVEN docs/UPSTREAM_PATCHES.md 存在且表头完整
WHEN 运行 `fstdd validate`
THEN 该项通过；若表体为空则通过并提示「登记项为 0」

## SC-2
GIVEN 登记表某行指向的文件不存在于仓库
WHEN 运行 `fstdd validate`
THEN 该项失败、非零退出、输出指明缺失路径

## SC-3
GIVEN docs/UPSTREAM_PATCHES.md 缺失或表头不完整
WHEN 运行 `fstdd validate`
THEN 该项失败、非零退出、输出「登记表缺失/表头不完整，修改 upstream/ 前必须先登记」

## 非行为（显式不做）
- 不比对文件哈希（D-2 切出）
- 不扫描 upstream/ 全部文件找「未登记修改」（无基线哈希时该检测必然误报或漏报）
