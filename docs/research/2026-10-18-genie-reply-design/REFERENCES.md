# Genie 回复区：OpenAI 第一方参考与实现边界

日期：2026-10-18。范围：#223 会话中业主新增的 Genie 视觉要求。右下角 dock 参考 OpenAI Help Center 对话；全页 workspace 参考 ChatGPT 对话与流式回复。保留现有模型、后端协议、权限和业务工具。

本文将 **本次核实的第一方事实**、**已有现场观察**、**Genie 的实现建议** 分开。接口提供某个选项不能证明 ChatGPT 或 Help Center 当前把该选项设成什么值；官方示例也不能作为这两个产品的像素测量值。

## 业主最后确认的实施边界

本研究完成后，业主明确要求：后端怎么接收、怎么回答和保存均保持原样；
只由前端模拟动态思考、加载和渐进显示。下文官方能力与建议表是参考资料，
其中真实流式、取消后端请求等能力没有纳入本票。最终实现使用原 JSON 回答，
等待期间做动态视觉，完整回答收到后做最多 1.2 秒的本地渐进显示。
滚动以 Genie 既有目标9为准：长回答保留阅读位置，由用户主动跳到最新。

## 取得了什么

所有新增外部资料均经官方 Apify Actor 获取；令牌只从既有环境文件加载，没有写入证据。Actor 输入、run ID、来源地址、HTTP 状态与费用见同目录 `*-run.json`；第一方响应文本见 `*-capture.json`。响应 Cookie 已从存档删除。没有登录外部账户、发送模型请求或修改 WordPress/生产数据。

| 来源 | 本次结果 | 能证明的内容 |
|---|---|---|
| [OpenAI ChatKit.js 概览](https://openai.github.io/chatkit-js/) | HTTP 200；`chatkit-docs-capture.json` | 完整聊天组件包含流式回复、消息/线程管理、来源注释、交互组件。自托管后端支持取消回复。 |
| [OpenAI ChatKit TypeScript 类型](https://github.com/openai/chatkit-js/blob/main/packages/chatkit/types/index.d.ts) | HTTP 200；`chatkit-types-source.d.ts` 是经 Apify 获取的原文 | 回复生命周期、错误、线程加载、重试、反馈、跟随滚动、披露文字与可配置主题的公开契约。 |
| [OpenAI 官方示例目录](https://github.com/openai/openai-chatkit-advanced-samples) | HTTP 200；`chatkit-examples-source.md` | 支持、新闻、地图等对话实例；进度消息、流式事件、回复开始/结束回调与来源注释的实际集成方式。 |
| [官方 Customer Support 面板](https://github.com/openai/openai-chatkit-advanced-samples/blob/main/examples/customer-support/frontend/src/components/ChatKitPanel.tsx) | HTTP 200；`chatkit-support-panel-capture.json` | 组件主题、开场问题、附件/语音、错误与回复完成回调的具体组合。它是示例应用，并非 help.openai.com 的实际客户会话。 |
| [ChatKit Studio Playground](https://chatkit.studio/playground) | 文本抓取 HTTP 200，但仅返回应用壳标题；浏览器截图 Actor 未获账户权限，见下文 | 文本抓取不能证明其消息的实际排版。 |
| [Help Center 联系支持说明](https://help.openai.com/en/articles/6614161-how-can-i-contact-support) | 首次 Apify 文本抓取被 403 拦截；浏览器截图重试未获账户权限，见下文 | 这次文本抓取没有得到正文，不能据此描述回复 UI。 |
| 猜测的 ChatKitOptions 文档深链 | HTTP 404；保留 `chatkit-options-capture.json` 作为失败记录 | 已以公开源码替代；不引用这个不存在的页面作为依据。 |

## 已有现场观察的适用范围

[2026-10-12 dossier](../2026-10-12-genie-openai-design/DOSSIER.md) 记录了未登录 ChatGPT landing 与 Help Center 匿名外壳，含截图与计算样式。可继承：Help Center 桌面 400×600 面板、16px 圆角、移动端全宽底部 sheet、44px 输入控件、底部披露的弱化字阶，以及 ChatGPT 768px 输入列等**当日已观察值**。这些值有时间性；没有在本次重测为“当前回复区尺寸”。

该 dossier 明确指出：Help Center 聊天内容在登录墙后，匿名态只出现登录提示；没有取得用户气泡、助手消息、加载、流式往返截图。ChatGPT 当日也没有发送消息。不能把该材料中的推导状态机称为实际回复证据。

## 本次核实的公开回复契约

1. **流式与完成是不同状态。** 官方类型定义独立的 `chatkit.response.start`、`chatkit.response.end`；另有 `chatkit.error`。线程历史也有单独的 load start/end。由此可明确区分等待首段、正在输出、完成、错误与历史加载，不能只靠一段“正在输入”的文本覆盖全部情况。源码见[事件类型](https://github.com/openai/chatkit-js/blob/main/packages/chatkit/types/index.d.ts#L1175-L1220)，本地原文 `chatkit-types-source.d.ts` 1175–1220 行。
2. **滚动尊重正在读旧消息的人。** `ThreadOption.autoScroll` 的文档明确限定：流式时仅在用户已经接近底部时自动跟随；默认关闭。这是 OpenAI 公开组件的行为契约，不能推定当前 ChatGPT 具体阈值。见[线程选项](https://github.com/openai/chatkit-js/blob/main/packages/chatkit/types/index.d.ts#L283-L290)。
3. **重试与反馈是显式能力。** 官方 `ThreadItemActionsOption` 分别提供反馈与重试，二者默认关闭；重试会触发删除相应线程项并开始生成的服务器事件。Genie 只有在现有本地协议支持时才呈现相应真实动作，不显示没有消费者的装饰按钮。见[回复动作类型](https://github.com/openai/chatkit-js/blob/main/packages/chatkit/types/index.d.ts#L266-L280)。
4. **披露是输入区的附属文字。** 官方 `DisclaimerOption` 明确把 markdown 文本放在 composer 下，可提高对比度。可确认位置语义，不能从该类型推导字号、行高或每个平台的具体措辞。见[披露类型](https://github.com/openai/chatkit-js/blob/main/packages/chatkit/types/index.d.ts#L259-L264)。
5. **细节状态可以由真实进度驱动。** 官方新闻示例发出进度事件来表示搜索/加载；地图示例用回复开始和结束回调锁定再恢复交互。它们证明进度与生命周期可以分别呈现，没有要求 Genie 暴露隐藏推理或伪造搜索阶段。见[进度示例](https://github.com/openai/openai-chatkit-advanced-samples#progress-updates)和[回复生命周期示例](https://github.com/openai/openai-chatkit-advanced-samples#response-lifecycle-ui-state)。
6. **主题是可调整的。** 官方类型允许 14–18px 基础字号、普通/紧凑/宽松密度、四种圆角梯度、自定义字体与色彩。它支持两种容器共享一套组件并有不同密度的实现方式；这些是允许值，均不是本次测得的 ChatGPT 固定令牌。见[主题与字体类型](https://github.com/openai/chatkit-js/blob/main/packages/chatkit/types/index.d.ts#L783-L830)。
7. **不需要改模型来学习界面。** ChatKit 概览区分 OpenAI 托管与自托管后端，且对两者均提供聊天 UI。这里仅把官方组件作为设计与状态契约证据；没有引入 SDK、远程 iframe、OpenAI 模型或新会话服务的实施决定。见[后端区分](https://openai.github.io/chatkit-js/#managed-vs-self-hosted-backend)。

## 给 Genie 的实现建议（设计选择，非声称已测得的 OpenAI 产品样式）

| 项目 | dock：Help Center 的紧凑对话 | workspace：ChatGPT 的阅读式对话 |
|---|---|---|
| 布局 | 保留现有 sheet/浮层；消息占主要高度，底部区只保留紧凑元信息 | 居中阅读列；宽屏留白服务于正文；移动端全宽适配 |
| 用户消息 | 右侧浅灰气泡，宽度自然收缩；长文本保留正常换行 | 右侧浅灰气泡；宽度受阅读列约束 |
| 助手消息 | 左侧无厚卡片的连续正文；短段落、可读的列表和轻量来源入口 | 连续文章式正文；明确的段落、标题、列表、表格和代码层级 |
| 回复动作 | 完成后紧凑图标动作，保留可访问名称与清楚的焦点态 | 正文后出现 copy/retry 等真实可执行动作；不让每条回复变成一块工具栏卡 |
| 等待首段 | 助手当前位置的轻量状态；发送键切为停止，状态由请求驱动 | 同左；首段出现后以正文取代等待态 |
| 流式 | 把数据增量追加在同一条助手消息；不逐段新建气泡；可停止 | 同左；表格/代码/列表应在未完成时仍稳定排版；不对每个字施加额外入场动画 |
| 停止与错误 | 停止保留已收内容；错误保留用户消息与已收部分，并有可执行恢复入口 | 同左；已完成回复的正常动作与失败恢复分开 |
| 跟随滚动 | 仅在读到尾部时跟随；用户向上滚动后停跟随并出现回到底部入口 | 同左；新 token 不抢走正在阅读的旧消息 |
| 披露与链接 | 将 AI 说明设为低对比的辅助文字；帮助/联系/隐私整成一条可换行的紧凑链接行；账户入口按同一灰阶和字阶融合 | 输入区下保留同一语义，避免重复大段页脚和独立强分隔账户栏 |

上表提出的气泡、无厚卡片正文、轻量图标和等待指示属于这次实现的设计解释；需要以 c223 的真实等待、部分输出、完成、停止、失败、重试、长回复、手动滚动截图验收。不能以接口声明替代渲染验收。

## 对原反馈的直接处理原则

业主指出的是 composer 下的 AI 说明、FAQ/下载、联系、隐私和账户链接缺少整体设计。调整时应将它们作为一个附属元信息区域统一字阶、灰阶、间距与换行；减少各自争夺注意力的横线、颜色和间距。AI 身份披露必须保留；帮助、联系、隐私与本语言登录/注册都要仍可达。不要通过隐藏必须的信息或制造空白区来获得“干净”的截图。

## 浏览器截图的具体阻塞

为补足实际回复外观，尝试官方 `apify/web-scraper` 的浏览器渲染及快照功能。Apify API 返回 HTTP 403，错误类型为 `full-permission-actor-not-approved`：该 Actor 要求整个 Apify 账户的完整访问授权，当前未获批准。一次收窄为单一 Studio URL 的重试仍是同一权限错误。原文见 `browser-reference-block.json`。这是账户权限边界，**不是网络超时**；没有扩大授权、绕过 Apify 或要求主会话停止实施。

已批准的 `apify/rag-web-browser` 可正常访问第一方文档和源码。它对 Studio 的此次抓取只返回应用壳，无法拿到经过客户端渲染的消息。官方示例的 README 也没有可用的对话截图。因此本轮不再增加 Actor 调用；用可追溯的官方契约约束 Genie 的加载、流式、停止、重试和滚动，再以 c223 真实夹具截图证明 Genie 的实际呈现。

## 未取得的证据

- 当前登录后的 chatgpt.com 实际回复、工具调用、加载动画的逐状态截图。
- 当前登录后的 help.openai.com 客服真实会话逐状态截图。
- 两个正式产品当前的回复精确字号、行高、气泡半径、宽度和自动滚动距离。

因此本次可以交付“依照已取证外壳、官方组件契约与业主方向完成的 Genie 设计”，不能交付“与两个正式产品当前登录态逐像素相同”的结论。后者需要已授权的已登录现场取证。
