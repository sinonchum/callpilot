# CallPilot

电话还没挂，日程已经排好。CallPilot 在一台已 root 的 Android 手机上实时听懂通话，把约定写进日历、提醒和笔记，并在对方改口时改掉已经记下的时间。

这是 H Company × 42AI Computer Use Agents Hackathon（2026-11-07 至 11-08，巴黎）的团队仓库。四人、大约 36 小时。转写用 Gladia Solaria-1。手机上的点击循环用 Holo Models API（`https://api.hcompany.ai/v1/`），因为 H 的 Agents API 没有 Android 环境。

## 文档

- [产品需求](docs/PRD.md)：场景、P0/P1/P2、演示脚本、隐私与延迟、尚未核实的假设
- [开发计划](docs/DEV_PLAN.md)：四人模块划分、JSON 契约、周六到周日的排期、风险兜底、验收清单

活动页：https://luma.com/hz9db5u9

## 现在能跑什么

不插手机、不配 API key：

```bash
cd laptop
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m orchestrator.demo
```

演示会走完「假通话转写 → 抽出 15:00 的 POC → 假点击保存 → 改口成 16:00 → 读回假日历 → 撤销提醒」，成功时打印 `[ok] POC at 16:00, reminder undone`。

面板在 `panel/`（`npm ci && npm run dev`，然后点「回放剧本」）。契约和模块说明在 [laptop/README.md](laptop/README.md)。

## 还要手机或真 key 的部分

- root 通话音频和 PCM 推流：只有 [phone/README.md](phone/README.md) 和 `phone/app/AudioPump.kt` 草稿，没有 Gradle 工程
- `CALLPILOT_EXECUTOR=adb` 才会执行 adb；默认执行器是内存里的假日历
- `GLADIA_API_KEY` 目前只够创建 live 会话，浏览器式 WebSocket 推流还没接上
- `HAI_API_KEY` 才会把截图发给 Holo。默认是录好的「点保存」脚本
- `INTENT_API_KEY` 才会调用文本模型。默认是针对演示台词的规则抽取器

幻灯片和备份视频还没做。mock 跑出来的步数不要写进 pitch。
