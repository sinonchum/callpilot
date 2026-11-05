# CallPilot 产品需求（黑客松 MVP）

电话还没挂，日程已经排好。CallPilot 在通话进行中听懂内容，在一台已 root 的 Android 手机上像人一样操作 App，把约定写进日历、提醒和笔记。每一步可确认、可撤销。

本文是 H Company × 42AI Computer Use Agents Hackathon（2026-11-07 至 11-08，巴黎，[活动页](https://luma.com/hz9db5u9)）的产品需求。团队 4 人：Simon 与 3 名队友，现场大约 36 小时。依据已约定的方案写；和方案不一致的地方写在 [范围决定](#scope-decisions)，未核实的事实写在 [待核实与假设](#assumptions)。模块接口、排期和测试以 [DEV_PLAN.md](DEV_PLAN.md) 为唯一契约来源。

## 问题

打电话时会约定时间和要办的事。挂断后要自己打开日历、便签、提醒，把内容手工抄进去。一忙就忘。

现有产品停在「转写 + 摘要」。最后一步「去做」仍要人来。便签、WhatsApp、Doctolib 这类 App 往往没有可用的开放 API，所以「接一个日历 API」覆盖不了真实手机上的操作。

CallPilot 的做法：不把日历 API 当主路径。Agent 看屏幕、点按钮，在真机上把事做完，并且在通话还没结束时就开始。H 的 Agents API 目前只有 web 和 desktop，没有 Android 环境，因此手机上的截图—坐标—点击循环由我们自己写。模型走 Holo 的 OpenAI 兼容 Models API（`https://api.hcompany.ai/v1/`），坐标是相对截图的 0–1000 整数。

## 目标用户与场景

黑客松 MVP 只服务这一场演示，不面向公开注册用户。

| 角色 | 是谁 | 要看到什么 |
| --- | --- | --- |
| 机主 | 现场拿着 root 手机的队员（Simon 的演示机） | 通话中日历被填上、改口后时间被改掉、挂断后能确认或撤销 |
| 对方 | 另一台手机拨入的队友，知情并同意被记录 | 按固定台词说话，包含一次改时间 |
| 评委 | 看投屏和面板的人 | 左侧 scrcpy 真机画面一直有动作，右侧面板能看见转写、槽位和 agent 步骤，结尾日历里真有一条事件 |

主场景（演示脚本，也是 P0 验收场景）：

1. 机主手机处于通话中，系统通话音频被实时转写。
2. 对方用法英混说约定：下周二 15:00、地点 Station F、事项 POC，并要求周四前把 deck 发过去。
3. 话还没说完，面板上已经出现日历草稿。
4. 对方改口：「Ah non, plutôt 16h.」槽位 `time` 从 15:00 变成 16:00，手机上的日历事件被改到 16:00。
5. 挂断后出现确认卡：日历（周二 16:00，Station F）、提醒（周四前发 deck）、便签（通话摘要）。确认后保留；再撤销提醒，条目被删掉。
6. 用 root 读取系统日历库，证明事件真实存在，而不是只存在于模型的回答里。

演示台词固定为：

> On se voit mardi prochain à 15h à Station F pour le POC… and can you send me the deck before Thursday?

> Ah non, plutôt 16h.

日期锚点：黑客松周六是 2026-11-07，周日是 2026-11-08。两天说出「mardi prochain」都解析为 2026-11-10（周二）。「before Thursday」对应 2026-11-12。时区 `Europe/Paris`（当日 CET，UTC+1）。16:00 的 `beginTime` 为 `1794322800000`，默认时长 60 分钟则 `endTime` 为 `1794326400000`。15:00 的 `beginTime` 为 `1794319200000`。

## 黑客松目标

P0 演示必须做到：

- 真机通话（或已写明的音频兜底）实时出字。
- 增量槽位听懂「会议 + 提醒 + 摘要」，并吃得下「15:00 改成 16:00」。
- 日历事件写进系统日历，并用 `content query` 读回核对。
- 投屏 + 笔记本面板让评委同时看见手机和内部状态。
- 挂断后可以确认，并撤销提醒。
- 现场翻车时，10 秒内切到同一脚本的备份视频。
- 幻灯片上的延迟、步数、成功率来自排练实测。禁止预填未测到的数字。

奖项目标（与方案一致）：

| 奖项 | MVP 里怎么体现 | 优先级 |
| --- | --- | --- |
| 主奖 €5k / €3k / €2k | 真机、中途改口、读回校验、实测数字 | 主攻 |
| Best Use of Gladia €1,000 | Gladia Solaria-1 是整条链路入口：partial 只做预览，final 驱动槽位；法英混说；双声道能分则分 | 主攻 |
| Best Use of Devin €1,000 | 用 Devin 生成 Kotlin 推流样板或测试脚本时，pitch 里说明哪些文件是 Devin 写的 | 可选，不占关键路径 |
| Best LinkedIn / X post 各 €500 | 周日上午剪 30 秒视频，按活动页当时的标签发帖 | 顺手 |
| Linkup | 把「Station F」解析成完整地址写入地点栏 | 可选（P2） |
| Stripe | 和本产品没有自然结合点 | 不做 |

## 非目标

本次黑客松明确不做：

- iOS、无 root 的通用 Android 发行版、多用户账号体系。
- 用 H Agents API 驱动手机。该 API 没有 Android 环境。
- 把 Google Calendar 云端 API 当作主路径。主路径是真机 UI + 本机日历 content provider。
- WhatsApp、Doctolib 的完整自动化。它们只作为「没有 API 也要能点」的动机。演示 App 是日历。
- 说话人分离模型。双方区分靠通话双声道；做不到就标成 `unknown`。
- 本地跑 Holo4-35B-A3B 开源权重。笔记本能否跑动未验证，只作时间富余时的隐私模式彩蛋。
- Stripe 支付、账号系统、应用商店上架。
- 把 root 音频、真实 adb 和付费模型调用提前当成已经跑通。这些仍要现场验证。仓库里已有的是可离线测试的笔记本 mock：规则槽位、假点击、假日历。活动如果禁止赛前代码，以周六工作人员的说法为准。

<a id="scope-decisions"></a>

## 范围决定

下面几条是为了在 36 小时内对准 3 分钟脚本，对方案原文做的收窄。实现时按这里，不要按两套说法各写一半。

1. **通话中可以写入日历草稿。** 方案的风险表写「动作先进入确认卡」。3 分钟脚本的高潮是评委看见日历里的 15:00 被改成 16:00，这要求通话中已经有一条可修改的事件。P0 采用：槽位稳定后走日历 INSERT 预填并保存；挂断后的确认卡表示「保留这些结果」；拒绝或撤销走反向计划删除。更严的「未确认绝不落库」留作 P1。若周六确认规则不允许未确认写入，切到 P1：屏幕上只留预填表单，保存发生在点确认之后，改口改的是表单里的时间。
2. **评委主视觉是笔记本面板。** 方案架构写了手机悬浮窗和笔记本面板两套确认卡。P0 只做面板上的确认卡（脚本布局就是 scrcpy 在左、面板在右）。手机悬浮窗是 P1。
3. **P0 的「提醒」是同一日历库里的第二条事件**，标题 `Send the deck`，开始时间 2026-11-12 09:00（`1794470400000`）。这样校验和撤销都走已经要做的 content provider。系统闹钟 App 是 P1。
4. **P0 的「便签」是确认卡上的通话摘要。** 打开便签 App 并写入是 P1。日历里多出一条真实事件、改口、撤销，这三件是主奖演示的底线。
5. **P0 撤销用反向计划里的 `content delete`，然后把日历重新亮到投屏上。** 方案希望 agent 亲手删。Holo 点删除是同一条反向计划的可选策略；排练不稳定就不要上现场。
6. **意图抽取不占用 Holo 配额。** 方案只写「云端 LLM」。Holo 免费层 `holo3-1-35b-a3b` 只有 10 次/分钟，GUI 循环本身就很吃请求。槽位更新用单独的文本模型 key。厂商周六早上选定。

## 用户故事

1. 作为机主，我在通话里听到对方约定时间和事项，希望挂断前手机上已经出现对应的日历草稿，这样我不用事后回忆。
2. 作为机主，对方改口把 15:00 改成 16:00 时，我希望系统改的是同一条事件，而不是再新建一条 16:00。
3. 作为机主，我希望挂断后看到一张卡，上面同时有日历、提醒和摘要，我可以保留，也可以撤销提醒。
4. 作为机主，我希望录音开始前有明确开关和持续可见的记录指示，对方是事先同意的人。
5. 作为评委，我希望大屏左侧是真机、右侧是转写和步骤，并且有人用日历数据库把结果读回来。
6. 作为队员，我希望每个模块都有 JSON 契约和 mock，这样音频、GUI、意图、面板可以周六上午并行开工。

## 功能需求

优先级：P0 必须出现在演示里；P1 主路径稳定后再做；P2 有余力才做。

### 音频捕获（P0）

- 在 root 手机上采集通话音频。优先 `AudioRecord` 源 `VOICE_CALL`，做成特权应用持续推流。BCR 只证明「root 后可以录到文件」，我们要的是实时 PCM 流，需要自写推流，不直接拿 BCR 的落盘路径当产品。
- 帧格式见 DEV_PLAN 的 PCM 帧。手机报原始采样率；笔记本重采样到 Gladia 会话要求的格式。
- 传输优先 USB：`adb forward`。场地 Wi-Fi 不作为主路径。
- 通话开始、结束要有事件，面板能显示「正在听」。

### 实时转写（P0）

- Gladia Live API，模型 `solaria-1`。流程是 `POST /v2/live` 拿 WebSocket URL，再推音频。
- 会话配置：`encoding=wav/pcm`，`bit_depth=16`，`sample_rate=16000`，`language_config.languages=["fr","en"]`，`code_switching=true`，`messages_config.receive_partial_transcripts=true`。`channels` 与实际推流一致（1 或 2）。`endpointing` 从官方默认 0.05 秒起，周六按台词手感调。
- `is_final=false` 的 partial 只更新面板预览。只有 `is_final=true` 可以改槽位。同一 `data.id` 是同一句的更新，面板替换显示，不追加重复行。
- 官方材料称 partial 低于 103 ms、整句大约 300 ms 量级。这是厂商数字。我们自己的数字周日排练再写上幻灯片。官方同时提醒：打开多语言或 code-switching 后，partial 准确率会下降。演示台词必须混说，所以 partial 只供观赏，行动以 final 为准。

### 增量意图（P0）

- 每条 final 产出一份 JSON patch。确定性 reducer 把 patch 叠成槽位快照（事件、提醒、笔记）。
- 槽位至少包含：标题、日期、时间、时区、地点、提醒标题、提醒时间、摘要。
- 相对日期按通话开始时的 `Europe/Paris` 本地日历解析。
- 更正只改被更正的字段，保留同一实体 id，并留下 `from` / `to`。
- partial 可以刷新 `preview` 文本，不得把字段标成 `stable`，不得触发执行。

### 计划与执行策略（P0）

- 日历创建/更新：设备探针确认 INSERT Intent 可用时走 `intent_prefill`（预填后由少量 GUI 步骤核对并保存）。不可用时走纯 GUI。
- 每条动作带反向计划，写入动作账本。
- 演示只承诺 3 个可见结果：POC 日历事件、Send the deck 提醒、确认卡上的摘要。

### GUI 循环（P0）

- 主力模型 `holo4-35b-a3b`（公开标价 input $0.30 / cached $0.03 / output $2.00，每百万 token）。难步骤备用 `holo4-27b`（公开标价 $0.40 / $0.04 / $3.00）。免费层 `holo3-1-35b-a3b` 仅 10 次/分钟，只用于赛前连通性探针，不用于现场演示。
- 使用 function calling，`tool_choice="required"`。注册 `click`、`swipe`、`type`、`answer`。官方示例明确写了 `click` 和 `answer`；`swipe` 和 `type` 的参数形状以 DEV_PLAN 为准，周六用一次真实调用核对模型是否按这个 schema 出参。
- 坐标是整数 `[0, 1000]`，原点在截图左上角。用**送进模型的那张图**的像素宽高换算，再交给 `input tap`。禁止送模前缩放像素。JPEG 压缩可以，宽高必须不变。
- Agent 循环打开 thinking，`temperature=0.8`。上下文里最多保留 3 张截图。循环在 `answer` 时停止。空 tool call 不是停止。
- INSERT 路径步数上限 8。演示硬上限 12。AndroidWorld 上大约 19 步、每题大约 3 分钟的量级说明纯 GUI 长任务不适合这场 3 分钟演示。

### Root 执行器（P0）

- `adb shell su -c` 执行 `input tap` / `input swipe` / `input text` / `input keyevent`、`am start`、`content query`、`content delete`。
- 截图优先 `adb exec-out screencap -p`。若必须 root，改成 shell 落盘再拉文件。周五两种都量一次。
- `uiautomator dump` 作为文本辅助，P1。
- 执行器是哑的：收到 JSON 就执行并返回截图与耗时。重试策略放在 GUI 循环里。

### 校验（P0）

- 动作结束后读取 `content://com.android.calendar/events`（URI 以周五在演示机上的探针为准）。
- 比对标题、`dtstart`、地点。读回不一致则算失败，进入重试或反向回滚。
- 这是演示里「事件真的在」的证据。

### 确认、撤销、面板（P0）

- 面板用 TypeScript + React，本地网页。展示：双路或单路转写、槽位 diff、agent 步骤、确认卡。
- 确认卡在挂断后列出 3 条结果。确认 = 保留。撤销提醒 = 执行该条的反向计划。
- 面板到编排器的唯一写操作是 `confirm.decision`。其余事件只读。

### P1

- 未确认不落库的严格模式。
- 手机悬浮窗确认卡。
- 便签 App 的 GUI 写入。
- 系统时钟/闹钟里的真提醒。
- 每步截图比对，失败重试 2 次后切回 Intent 路径。
- `holo4-27b` 处理失败步骤。
- 双声道标成「我 / 对方」。声道哪边是本机，以周五探针为准。
- `uiautomator dump` 辅助定位。

### P2

- Linkup 把 Station F 解析成通讯地址。
- 本地 GGUF 单步定位，当作隐私模式演示。
- Devin 样板代码及 pitch 里的署名说明。
- 30 秒社交视频和发帖。标签以活动页当天的要求为准。

## 非功能需求

### 延迟

厂商数字和我们的现场目标分开。幻灯片只写测到的数。

| 环节 | 现场目标（排练不达标就改演示节奏，不改写数字） | 说明 |
| --- | --- | --- |
| Gladia partial | 记录实测，不设硬门槛 | 厂商称 &lt; 103 ms；code-switching 下仅作预览 |
| final 到达面板 | 记录实测 | 厂商称 final 大约 300 ms 量级 |
| 约定句的 final 结束 → 面板草稿可见 | ≤ 5 s | 不含把事件保存进日历 |
| 槽位稳定 → 日历库能查到事件 | ≤ 45 s | INSERT 预填路径 |
| 改口 final → 日历库时间为 16:00 | ≤ 60 s | 同一条事件 |
| 撤销 → 提醒条目消失 | ≤ 20 s | `content delete` 路径 |

### 隐私与同意

- 开始采集前，手机上有本机开关。开关打开期间，屏幕上一直有「正在记录通话」指示。
- 演示对方是事先同意的队友。不录无关人员，不把观众电话接进这条链路。
- 原始 PCM 默认不落盘。只有在队员口头同意、并且显式打开 fixture 录制时才写测试文件。
- 音频只发给当次 Gladia 实时会话。挂断后发送 `stop_recording`。
- 送给 Holo 的内容是截图和当前任务文本，不附带整段录音。H 的 Models API 文档写明默认不存储 prompt 和 response。这是厂商声明。演示仍只用剧本通话。
- 转写留在笔记本进程内存里，提交作品前删掉演示日志里的多余通话。
- API key 只放环境变量：`HAI_API_KEY`、`GLADIA_API_KEY`。禁止进 git。
- 法国对私人谈话录音的同意要求，赛前由队员再核对一次。本文不把未核对的法条写成已确认结论。演示的底线是：双方知情、开关可见、录音范围限于这场剧本。

### 可靠性

- 日历动作在写入前按「标题 + 当天 `dtstart`」查询。已有则更新，避免改口时变成两条。
- GUI 单步失败后重试最多 2 次，然后回到 Intent 路径或已标定的保存按钮坐标。
- 点击坐标与截图像素绑定。截图宽高、状态栏、导航栏区域周五记进设备档案。
- 演示机提前关掉通知、自动更新和弹窗。屏幕常亮。USB 连接 scrcpy。笔记本上网走手机热点或自带网络，不依赖场地 Wi-Fi。
- 编排器崩溃时，日历库是事实来源。重启后先 `content query`，再决定补保存还是反向删除。
- 整段演示失败时，播放周日上午录好的同脚本视频。切换动作要在彩排里练到 10 秒内完成。

## 成功指标

周日 10:00 前用同一台词连续成功 3 次，才算可以上主路径。每次记录：

- final → 草稿、稳定 → 查到事件、改口 → 16:00、撤销 → 条目消失，四段耗时。
- INSERT 路径的 GUI 步数（目标 ≤ 4）。纯 GUI 对照如果跑了，只记步数和耗时，不拿来当现场路径。
- 日历库读回：标题 `POC`，本地时间 16:00，地点含 `Station F`。
- 提醒条目撤销后查询结果为空。
- 3 次里失败的那次要记下失败步骤，用来决定现场是否改走备份视频。

这些格子在测到之前保持空白。

## 演示场景

时长 3 分钟。左侧 scrcpy，右侧面板。队友用第二台手机拨入。

| 时间 | 画面 | 完成标准 |
| --- | --- | --- |
| 0:00–0:25 | 一张「通话后要打开 3 个 App」的图 | 一句话讲清：转写很常见，没人帮你把事做完 |
| 0:25–0:40 | 投屏亮出手机，面板已连接 | 评委看见真机和转写区 |
| 0:40–1:50 | 法英台词 | 面板草稿出现：周二 15:00、Station F、POC，以及 deck 提醒 |
| 1:50–2:10 | 「Ah non, plutôt 16h.」 | 槽位改为 16:00，日历里同一条事件改为 16:00 |
| 2:10–2:35 | 挂断，确认卡 | 三点都在卡上；点确认；撤销提醒后条目消失 |
| 2:35–3:00 | 架构图 + 实测数字 | 数字来自当天上午的排练表 |

备用：同脚本完整视频放在笔记本本地，全屏播放的快捷方式彩排过。

<a id="assumptions"></a>

## 待核实与假设

赛前或周六 10:30 前要有结论。结论未出之前，按「当前假定」开发 mock，不要把假定写成已验证。

| 项 | 当前假定 | 怎么核实 |
| --- | --- | --- |
| 赛前能否写产品代码 | 仍未核实。仓库里已有离线 mock；真机和付费调用留到现场 | 周六签到时问工作人员，并再读活动页 |
| 提交物格式、评审表、社交标签 | 未知 | 同上。Linkup / Devin / 发帖以当天页面为准 |
| Morning 赞助 | 任务简报提到了 Morning，方案正文的赞助表没有这一项 | 周六核对 Luma 赞助清单。对不上就不做相关功能 |
| 演示机型号、Android 版本、root 方式 | 未知。BCR 文档认为双声道通话录音主要在较新 Pixel 上确认过 | 周五探针。结果写入设备档案 |
| `CAPTURE_AUDIO_OUTPUT` | 这是 privileged 权限，普通 `pm grant` 不够，需要 priv-app / Magisk 模块一类安装方式 | 周五真机。失败则按 DEV_PLAN 的音频兜底 |
| 双声道哪一侧是本机 | 未知 | 周五分别捂住上下行试听 |
| 日历 content URI、INSERT 是否弹出可保存表单 | URI 先用 `content://com.android.calendar/events` | 周五在演示机上 query 和 `am start` |
| 意图文本模型 | 单独的 key，强制 JSON，不走 Holo 限流 | 周六 10:30 前选定并打一次 patch |
| Gladia 账号额度与部分计费 | 未知 | 周四开通并跑官方 WebSocket 示例 |
| H 付费额度到账 | 官方写额度最多约 15 分钟到账 | 周四充值，演示前再看余额 |
| `swipe` / `type` 的 tool schema | 采用 DEV_PLAN 里的形状 | 周六第一次 Holo 调用核对 |
| 15:00 的默认时长 | 60 分钟 | 台词没说结束时间，演示按此固定 |
| 提醒时刻 | 周四 09:00 | 台词只说 Thursday 之前 |
| 笔记正文 | 确认卡上的一段摘要：时间、地点、deck | P0 不写便签 App |
| 「你」这个角色 | 方案里的 Android / 音频 / root 执行器负责人是 Simon（仓库许可证版权人 Simon QIN） | 若现场换人，只改负责人，不改模块边界 |
| 伊泽尔黑客松线上说明会 | 方案写 11/5 当天还有这场会，具体钟点不在方案里 | 周四自行对一下日历，避免和 key 开通打架 |
| scrcpy 与 `screencap` 能否同时用 | 假定可以 | 周五同屏试一次 |

## 参考

- 活动页：https://luma.com/hz9db5u9
- H Models API：https://hub.hcompany.ai/models-api/overview
- Holo 坐标、截图预算、`answer`：https://hub.hcompany.ai/models-api/build-an-agent/core-concepts
- Holo function calling：https://hub.hcompany.ai/models-api/build-an-agent/function-calling
- H Agents API 环境（无 Android）：https://hub.hcompany.ai/agents-api/environments/overview
- Gladia Live 快速开始：https://docs.gladia.io/chapters/live-stt/quickstart
- Gladia endpointing：https://docs.gladia.io/chapters/live-stt/features/endpointing
- Gladia code-switching：https://docs.gladia.io/chapters/language/code-switching
- BCR：https://github.com/chenxiaolong/BCR
