# CallPilot

电话还没挂，日程已经排好。CallPilot 在一台已 root 的 Android 手机上实时听懂通话，把约定写进日历、提醒和笔记，并在对方改口时改掉已经记下的时间。

这是 H Company × 42AI Computer Use Agents Hackathon（2026-11-07 至 11-08，巴黎）的团队仓库。四人、大约 36 小时。转写用 Gladia Solaria-1。手机上的点击循环用 Holo Models API（`https://api.hcompany.ai/v1/`），因为 H 的 Agents API 没有 Android 环境。

## 文档

- [产品需求](docs/PRD.md)：场景、P0/P1/P2、演示脚本、隐私与延迟、尚未核实的假设
- [开发计划](docs/DEV_PLAN.md)：四人模块划分、JSON 契约、周六到周日的排期、风险兜底、验收清单

活动页：https://luma.com/hz9db5u9

## 现在仓库里有什么

只有文档。产品代码打算在现场写；赛前是否允许写代码还没核实，所以赛前只做 key、root 音频和 adb 探针。模块目录写在开发计划里，还没有建。
