# 笔记本侧

不插手机、不配 key 就能跑通：假转写 → 槽位 → 计划 → 假点击 → 假日历读回 → 撤销提醒。

```bash
cd laptop
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m orchestrator.demo
```

最后一行应以 `[ok] POC at 16:00, reminder undone` 结束，退出码 0。CI 跑的是同一条命令。

面板：

```bash
cd panel
npm ci
npm test
npm run dev
```

打开页面后点「回放剧本」。若要让面板跟着 WebSocket 走，另开一个终端：

```bash
cd laptop
python3 -m orchestrator.serve
```

默认地址 `ws://127.0.0.1:8765/events`。可用 `VITE_WS_URL` 改。

## 环境变量

没设置时全部走 mock。

| 变量 | 作用 |
| --- | --- |
| `CALLPILOT_FORCE_MOCK=1` | 即使下面的 key 存在也走 mock |
| `GLADIA_API_KEY` | 才构造 Gladia 客户端。直播 WebSocket 推流还没接，`create_session` 只会 `POST /v2/live` |
| `GLADIA_BASE_URL` | 默认 `https://api.gladia.io` |
| `HAI_API_KEY` | 才向 `https://api.hcompany.ai/v1` 发 Holo 请求 |
| `CALLPILOT_HOLO_BASE_URL` | 默认 `https://api.hcompany.ai/v1` |
| `CALLPILOT_MODEL` | 默认 `holo4-35b-a3b` |
| `INTENT_API_KEY` / `INTENT_BASE_URL` / `INTENT_MODEL` | 槽位改走文本模型。默认是规则抽取器 |
| `CALLPILOT_EXECUTOR=adb` | 才真正调用 adb。默认 `FakeExecutor` |
| `ANDROID_SERIAL` | `adb -s` |

## 目录

和 `docs/DEV_PLAN.md` 一致。`contracts/models.py` 是消息契约，`contracts/schema/v1.json` 由这些模型导出。`fixtures/demo_script.jsonl` 是剧本，`fixtures/panel_replay.jsonl` 是 mock 演示的事件记录，测试会核对它没有漂。

真机接线见 [phone/README.md](../phone/README.md)。
