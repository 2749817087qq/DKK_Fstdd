# spec: packaging — 开箱可安装

**需求**: 干净 venv 中安装本仓库后 CLI 可用、测试可跑

## SC-1
GIVEN 一个干净的 Python 3.10+ venv
WHEN 执行 `pip install -e ".[test]"`
THEN 安装成功且 `fstdd --help` 正常输出（退出码 0）

## SC-2
GIVEN 已按 SC-1 安装
WHEN 执行 `pytest upstream/tests`
THEN 全部用例通过（与未打包直跑结果一致）

## SC-3
GIVEN 已按 SC-1 安装
WHEN `python -c "import yaml, jinja2, requests; import fstdd"`
THEN 全部导入成功（声明 = 行为）

## 边界
- 不打包 skills/ tools/ docs/（适配层不进 wheel）
- version 字段 = R 轴 3.3.8，不得取 E/K 轴
