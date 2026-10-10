# spec: patches-registry — vendored 补丁登记表

**需求**: 对 upstream/ 的任何修改先登记，登记有单一事实源

## SC-1
GIVEN 仓库根存在 docs/UPSTREAM_PATCHES.md
WHEN 读取文件头
THEN 包含基线声明（E=3.0.5 / K=3.1.0 / R=3.3.8）与指向 UPSTREAM_BASELINE.md 的引用

## SC-2
GIVEN 表体任一行
WHEN 解析该行
THEN 8 列齐全：# / 文件 / 行号 / 修改原因 / 关联上游issue或PR / 登记日期 / 登记人 / 预期回退版本

## SC-3
GIVEN 「待登记」区
WHEN 检查其内容
THEN 至少列出 experience.py:428（解析器缺陷）一项；CRLF 项标注「走上游 PR，不本地改」
