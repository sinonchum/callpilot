# 手机侧（尚未实现）

这里没有可安装的 App，也没有 Gradle 工程。`app/AudioPump.kt` 只是接口草稿。真机部分要等 root 手机、USB 和周五的音频探针。

笔记本侧已经用假设备和录好的转写把后面的链路跑通。接上手机时，只要把 PCM 帧送进同一个解码器，编排器就不用改。

## 目标

通话进行中，从 `VOICE_CALL` 读 PCM，经 USB 推到笔记本。手机不保存 Gladia 或 Holo 的 key。

## 帧

大端：

```text
uint32 header_json_bytes
header_json utf-8
uint32 pcm_bytes
pcm bytes
```

头示例：

```json
{
  "v": 1,
  "type": "audio.frame",
  "call_id": "call_demo",
  "seq": 1,
  "ts_mono_ms": 0,
  "sample_rate": 48000,
  "channels": 2,
  "encoding": "pcm_s16le",
  "capture": "voice_call"
}
```

`sample_rate` 和 `channels` 填硬件真实值。重采样到 16 kHz 由笔记本的 STT 模块做。`seq` 从 1 连续递增。

笔记本上的参考实现是 `laptop/stt/pcm.py` 的 `encode_frame` / `decode_frame`。

## 接到笔记本

1. 手机进程监听 `127.0.0.1:8770`。
2. 笔记本执行 `adb forward tcp:8770 tcp:8770`，再连接这个端口。
3. 不要走场地 Wi-Fi。scrcpy 也走 USB。
4. 采集期间屏幕上要有可见的「正在记录通话」，并且有本机开关。演示对方必须事先同意。

`CAPTURE_AUDIO_OUTPUT` 是 privileged 权限，普通 `pm grant` 通常无效。需要 priv-app 或 Magisk 模块。BCR 只证明 root 后可以录成文件；这里要的是实时流，不能直接拿它的落盘路径当产品。

## 音源顺序

周五探针选定一种，周六不要再改：

1. `voice_call` 双声道
2. `voice_call` 单声道
3. VoIP 的系统播放
4. 免提 + `MIC`
5. 事先同意录好的剧本音频（面板上必须标明）
6. 切到备份视频

## adb

真实点击不在默认路径里。设置 `CALLPILOT_EXECUTOR=adb` 和 `ANDROID_SERIAL` 之后，`laptop/executor/adb.py` 才会执行命令。没设置时它直接拒绝，避免 CI 碰到设备。

它会拼这些命令，但还不覆盖「打开已有事件再改时间」的界面流程。假设备按标题覆盖同一条；真机上 INSERT 会再开一张表单，更新已有事件仍要现场做。

- `adb shell su -c input tap X Y`
- `adb exec-out screencap -p`
- `adb shell am start -a android.intent.action.INSERT -d content://com.android.calendar/events ...`
- `adb shell content query --uri content://com.android.calendar/events --projection _id:title:dtstart:dtend:eventLocation`
- `adb shell content delete --uri content://com.android.calendar/events --where ...`

`input text` 只适合 ASCII。演示里的地点走 Intent extras，不靠键盘输入。
