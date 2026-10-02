感谢反馈，两个问题都已确认并纳入改进计划：

## 1. 目录收敛到 .fstdd/ 下

完全同意。下一版本会将 `changes/`、`specs/`、`archive/`、`canonical/`、`agent_tests/` 全部收敛到 `.fstdd/` 下，项目根目录只保留一个 `.fstdd/` 目录。已有项目在 `stdd upgrade` 时会自动迁移旧路径，无需手动处理。

## 2. README 过于偏向 CLI 命令

你说得对——用了一个多月，压根没看过 `python bin/stdd xxx` 命令，全靠自然语言对话完成。这正是 STDD 设计的本意（Skill 层封装底层 CLI），但 README 没有体现出来。下一版本会把快速开始部分改为自然语言对话示例优先：

```
# 全局安装/升级
"安装 https://github.com/leonai42/stdd 到全局skill"

# 项目初始化
"/STDD 初始化 当前项目"

# 开始一个需求
"/stdd 开发 我们需要为 API 增加速率限制功能"
```

CLI 命令保留在参考附录中，供需要脚本化或 CI 集成的用户使用。

---

两项改进会包含在下一个版本中发布。感谢你的持续使用和反馈！
