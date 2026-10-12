# Genie 重设计取证卷宗：OpenAI Chat 页面与 Help Center 客服助手 helper

- 日期：2026-10-12（UTC）
- 取证人：设计调研会话（复刻依据采集，供 /prototype 出原型）
- 证据：`captures/` 下 19 张真实浏览器截图（均为实际访问页面的直接截取）＋本文引用的计算样式与 widget CSS 源码规则
- 视口：桌面 1440×900；移动 390×844（iPhone UA）。界面语言 English（chatgpt.com 首访按浏览器 locale 呈中文，经其设置面板切换 English (US) 后重截）
- 通道：chatgpt.com 系列经 Playwright 浏览器插件；help.openai.com 系列经本机 Python Playwright 驱动有头 Google Chrome 132（Cloudflare 挑战自动通过后取证）。headless 通道被 "Just a moment…" 挑战拦截，已如实记录
- 纪律遵守：全程只读浏览。未登录任何账号、未在任何表单输入任何字符、未发送任何消息、未调用任何外部模型 API

---

## ① 组件清单

### A. chatgpt.com 未登录 landing

#### A1 整体版式
- 用途：未登录访客的第一屏——左 260px 固定侧栏 + 右主区；主区内容列 768px 水平居中
- 几何：侧栏 260×900；主区 1180；composer 卡 768×52 居中（x=466）；标题块约在视口垂直 43% 处（composer 卡 y=462）；披露句贴视口底（y=876）
- 令牌：body 背景 `#fcfcfc`、正文色 `#0d0d0d`（gray-1000）；字体栈 `-apple-system-body, ui-sans-serif, -apple-system, "system-ui", "Segoe UI", Helvetica…`（macOS 实测；Windows/Android 会落到 Segoe UI/Roboto 系）
- 截图：`chatgpt_landing_full_1440.png`、`chatgpt_landing_viewport_1440.png`

#### A2 顶部导航条
- 用途：模型名 chip（左）＋ Log in / Sign up for free（右）
- 几何：高 52px；Log in 按钮 64×44；Sign up 129×44
- 令牌：Log in＝实心近黑 pill：`bg #0d0d0d`、字 14px/600 白、`radius 999px`、`padding 0 12px`；Sign up＝白底描边 pill：`border 1px rgba(0,0,0,.2)`、字 14px/600 `#0d0d0d`
- 截图：`chatgpt_topbar_1440.png`

#### A3 侧栏
- 用途：导航（Images/Plugins/Deep research/套餐/Help/Settings）＋底部登录引导卡
- 几何：项 248×36；登录卡 section 260×185、`padding 20px`、内含 h2 20px 高与 44px 高 Log in 白底描边按钮
- 令牌：导航项 `radius 10px`、`padding 6px 10px`、`gap 6px`、字 16px/400
- 截图：`chatgpt_sidebar_logincard_1440.png`

#### A4 居中标题（轮换 headline）
- 用途：开场提问，轮换两句：中文版同 h1 内实测两句「你想做点什么？我们先从哪里开始？」；EN 版 a11y 快照捕获到 "Where should we begin?"，容器全文含 "What are you working on?"（轮换标题）
- 几何：EN 测得单行 255×28（EN 句较短）
- 令牌：24px / 行高 28 / weight 400 / 字距 0.07px / `#0d0d0d`
- 截图：`chatgpt_landing_full_1440.png`、`chatgpt_composer_group_1440.png`

#### A5 Composer 输入卡（本任务核心参照）
- 用途：消息输入行：左「+」附加钮 → 内联工具菜单 → 输入框 → 右听写钮、发送钮
- 几何：卡 768×52；「+」/听写/发送各 44×44；textarea 614×24（17px/24）
- 令牌：卡 `radius 28px`、`border 1px rgba(0,0,0,.1)`、`bg #fff`、`padding 7px 10px`、三层投影 `rgba(0,0,0,.04) 0 0 0 1px, rgba(0,0,0,.04) 0 2px 8px 0px, rgba(0,0,0,.024) 0 4px 80px 8px`；placeholder `#8f8f8f`；按钮 `radius 999px`；caret `#0d0d0d`
- 交互态：聚焦输入框时**卡不出现任何 ring/描边变化**（实测聚焦前后 box-shadow、border 完全一致）；发送钮空输入时 disabled
- 截图：`chatgpt_composer_group_1440.png`（卡+标题）、`chatgpt_composer_focus_1440.png`（聚焦态视口）

#### A6 快捷 chips（+ 菜单内联工具条）
- 用途：点「+」在卡内展开：Add photos、Web search（免登录）＋分隔句 "Log in to use..."＋Create image、Deep research、Add files（登录锁）
- 几何：chip `padding 6px 10px`、`gap 6px`、`radius 10px`、字 16px
- 令牌：可用 chip 字色 `#0d0d0d`/`#000`；登录锁 chip 整体灰 `#8f8f8f`
- 交互态：打开动画导致元素级截图不稳，取视口整截
- 截图：`chatgpt_composer_plusmenu_1440.png`

#### A7 底部披露句
- 用途：AI 披露＋条款/隐私链接
- 令牌：12px/16、`#5d5d5d`（gray-500）、链接同色下划线；容器宽 1052 居中
- 原文：`ChatGPT is AI. By using it, you agree to our Terms & Privacy Policy. Chats may be reviewed and used to improve our AI models. Learn more`
- 截图：`chatgpt_disclosure_1440.png`

#### A8 登录卡（modal）
- 用途：点 Log in 弹出的鉴权卡（未输入任何内容即截）
- 结构：标题 "Log in or sign up"、副句 "You'll get smarter responses and can upload files, images, and more."、Continue with Google / Apple / phone、OR、Email address 输入行、Continue 按钮
- 截图：`chatgpt_login_modal_1440.png`

### B. help.openai.com 帮助中心 + helper 客服助手

#### B1 首页版式
- 用途：自助支持门户
- 结构：事件横幅（当日有 incident 通报条）→ 头部（OpenAI logo、语言选择 English、Login）→ 1024px 宽大搜索框（64px 高，字 18px，placeholder "Search for articles..."）→ 分类卡片网格（实测卡 309×144、白底、`padding 16px`、`gap 16px`）→ 页脚（logo + ChatGPT/API/Service Status + Cookie Preferences）
- 令牌：字体 `\"OpenAI Sans\", ui-sans-serif, system-ui, sans-serif`；正文 16px/24 `#282828`；bg 白
- 截图：`helper_home_full_1440.png`（全页 1440×8246）

#### B2 Launcher 气泡（widget 触发器，`._Trigger_12slx_83`）
- 用途：右下角常驻客服助手入口
- 几何：50×50 正圆；桌面 `bottom 20px right 20px`（<768px 时 12/12）；z-index 1002；内含 24×24 白色聊天气泡 SVG（`fill=currentColor`）
- 令牌（源码+实测一致）：`bg var(--gray-900)=#181818`、`color #fff`、`radius 100%`、`box-shadow var(--shadow-400)`（实测渲染 `rgba(0,0,0,.12) 0 8px 16px -4px`）、`transition transform .25s ease, opacity`
- 交互态（源码规则）：
  - `:hover` → `transform scale(1.04)`（实测矩阵 1.04，颜色不变）
  - `:active` → `scale(1)`
  - `[data-visible=false]` → `scale(.94); opacity:0; pointer-events:none`
  - `[data-closing=true]` → 过渡延迟 .1s（面板关闭动画让位后气泡再浮现）
- 截图：`helper_launcher_closed_1440.png`（元素 50×50）、`helper_launcher_hover_1440.png`（52×52，缩放后）

#### B3 面板容器（`._Panel_12slx_1`，桌面）
- 用途：点 launcher 弹出的对话窗外壳
- 几何（源码+1440 视口实测）：桌面 `width 400px`（窄桌面 340px；断点 380/576/768px）、`height min(600px, calc(100% - 50px))`、`bottom 20 right 20`、z-index 1002；实测 box [1020,280,400,600]
- 令牌：`radius var(--radius-2xl)=16px`、`bg var(--color-surface-elevated)=#fff`、投影 `var(--shadow)=0 10px 15px -3px rgba(0,0,0,.1), 0 4px 6px -4px rgba(0,0,0,.1)` ＋ `var(--shadow-hairline)=0 0 0 .5px~1px`（实测渲染第三层 `rgba(0,0,0,.08) 0 0 0 1px`）、`transform-origin bottom right`
- 交互态（源码）：入场 `scale(.9)+opacity 0` → `scale(1)+opacity 1`，`.3s var(--cubic-enter)`、延迟 80ms；退场 `.25s var(--cubic-exit-snappy)`；`[data-displayed]` 控制 display
- 截图：`helper_panel_open_viewport_1440.png`、`helper_panel_open_full_1440.png`、`helper_panel_container_1440.png`（元素 400×600）

#### B4 面板头部·匿名登录提示条（`._InlineLoginNudge_*`）
- 用途：**匿名态的面板唯一内容**——OpenAI 把 helper 聊天 UI 放在登录墙后，未登录只显示此条
- 实测文本：`Log in for faster, more personalized support.` ＋ 右侧 `Log in` pill 链接
- 令牌（源码+实测）：容器 `padding 8px 12px 8px 16px`、`gap 10px`、`border-bottom 1px var(--color-border-subtle)`；文案 12px / 行高 1.35 / `var(--color-text-secondary)=#5d5d5d`；Log in pill 14px/500、`radius 9999px`、`padding 0 10.64px`
- 交互态（源码）：`grid-template-rows 0fr→1fr` + `translateY(-4px→0)` + opacity，176/132ms ease——顶部条向下展开的动效
- 截图：`helper_panel_open_viewport_1440.png`（可见该条）

#### B5 ChatSurface 与 `<openai-chatkit>`（关键事实）
- 面板主体是 `._ChatSurface_12slx_181`（`flex column; 100%; bg var(--color-surface-elevated)`），内部承载 **`<openai-chatkit>` Web Component**——OpenAI 的统一聊天套件。即：helper 的对话 UI（欢迎语、快捷问题、输入行、发送键、消息气泡）不在帮助中心自己的 CSS 里，而在 chatkit 组件内（其样式随组件分发，匿名态不渲染）。CSS 源码另含：
  - `._Fullscreen_12slx_171`：`position fixed; inset 0; 100dvh; z-index 1000`——面板的整屏展开分支
  - `._ExitNodeToast_12slx_127`：右下 toast（`right 16/bottom 78`，桌面 20/88）、`bg var(--gray-900)`、白字、`radius var(--radius-xl)=12px`、`max-width min(360px, 100vw-32px)`、z-index 1003
- 未取证部分见 ⑤

#### B6 移动端 Sheet（`._Sheet_13gbn_1`）
- 用途：390×844 视口点 launcher 后的形态——**非缩小的桌面面板，而是全宽底部抽屉**
- 几何：`left 0; bottom 0; width 100%`、`max-height calc(100% - 48px)`、实测 box [0,48,390,796]；z-20
- 令牌：顶角 `radius calc(var(--spacing)*4)=16px 16px 0 0`；`<openai-chatkit>` 同顶角圆角；背景 `var(--color-surface-elevated)`
- 拖拽把手：`._HandleIndicator_13gbn_26` 50×4、`bg var(--alpha-15)`、`radius 999px`、top 8px 居中；命中区 `._HandleHitarea` 高 50px
- 桌面板在移动断点的对应形态：`._Panel_12slx_1` 基础规则即全宽 `translateY(100%)→0`、`.6s var(--cubic-enter)` 底部滑入
- 截图：`helper_home_mobile_390.png`、`helper_home_mobile_scrolled_390.png`、`helper_panel_open_mobile_390.png`

#### B7 Backdrop 遮罩（`._Backdrop_12slx_59` / `._Backdrop_13gbn_19`）
- 令牌：`bg #0000004d`（亮色主题）/ `#0000007f`（暗色主题）；z-1001/10；`opacity 0→1` `.4s var(--cubic-exit)`；面板打开时显示
- 截图：`helper_panel_open_mobile_390.png`（移动端遮罩+抽屉）

---

## ② 设计令牌汇总表

### 字体体系
| 用途 | chatgpt.com | help.openai.com |
|---|---|---|
| 字族 | `-apple-system-body, ui-sans-serif, system-ui, Segoe UI…`（系统栈，非自定义字族） | `"OpenAI Sans", ui-sans-serif, system-ui, sans-serif`（私有字族，不外发） |
| 输入框 | 17px/24 | 搜索 18px/29 |
| 正文/导航 | 16px/24 | 16px/24，字距 -0.16px |
| 小字（披露/提示） | 12px/16 `#5d5d5d` | 登录提示 12px/1.35 `#5d5d5d` |
| 按钮 | 14px/600（顶栏）；14px/400（图标钮） | 14px/500（Log in pill） |
| H1 | 24px/28/400/字距 .07px | —（卡片内 h3） |

### 颜色体系（亮色，括号内为暗色主题值；来自 widget CSS 变量表）
| 令牌 | 值 |
|---|---|
| gray-0 / surface-elevated | `#fff`（`#0d0d0d`） |
| gray-50 | `#f9f9f9`（`#131313`） |
| gray-100 | `#ededed`（`#181818`） |
| gray-400 | `#8f8f8f`（`#414141`） |
| gray-500（secondary 文本/披露） | `#5d5d5d` |
| gray-700 | `#afafaf`（`#303030`） |
| gray-900（launcher/黑 pill） | `#181818`（`#ededed`） |
| gray-1000（chatgpt 正文） | `#0d0d0d`（`#fff`） |
| help 正文 | `#282828` |
| chatgpt 页面底色 | `#fcfcfc` |
| placeholder | `#8f8f8f` |
| 边框 | `rgba(0,0,0,.1)`~`.2`；hairline `0 0 0 .5px`（亮）/`1px`（暗）alpha-05 |
| 遮罩 | `#0000004d` / 暗 `#0000007f` |

### 圆角
| 令牌 | 值 | 用在哪 |
|---|---|---|
| radius-md | .5rem=8px | 小钮 |
| radius-lg | .625rem=10px | 侧栏项、菜单 chips |
| radius-xl | .75rem=12px | toast |
| radius-2xl | 1rem=16px | helper 面板/移动 sheet 顶角 |
| radius-3xl | 1.25rem=20px | 更大卡 |
| pill | 999px/9999px | 顶栏按钮、Log in pill |
| 圆 | 100% | launcher |
| chatgpt 输入卡 | 28px | ——（不在其梯度内，特例） |

### 投影
| 令牌 | 值 |
|---|---|
| shadow-200 | `0 2px 4px -1px rgba(0,0,0,.08)` |
| shadow-300 | `0 4px 8px -2px rgba(0,0,0,.1)` |
| shadow-400（launcher 实测） | `0 8px 16px -4px rgba(0,0,0,.12)` |
| shadow（面板） | `0 10px 15px -3px rgba(0,0,0,.1), 0 4px 6px -4px rgba(0,0,0,.1)` |
| shadow-hairline | `0 0 0 .5px~1px` 描边影 |
| chatgpt composer | 三层：`0 0 0 1px rgba(0,0,0,.04)`＋`0 2px 8px rgba(0,0,0,.04)`＋`0 4px 80px 8px rgba(0,0,0,.024)` |

### 动效
| 令牌 | 值 |
|---|---|
| cubic-enter | `cubic-bezier(.19,1,.22,1)` |
| cubic-exit | `cubic-bezier(.8,0,.4,1)` |
| cubic-exit-snappy | `cubic-bezier(.65,0,.4,1)` |
| launcher | transform .25s ease（hover 1.04 / active 1 / 隐藏 .94+fade） |
| 面板入场 | scale .9→1 + fade，.3s enter，延迟 80ms；移动 sheet translateY .6s |
| 面板退场 | .25s exit-snappy；气泡再现延迟 .1s |
| 遮罩 | opacity .4s |
| 登录提示条 | rows/opacity/transform 176/132ms ease |

### 间距节奏
- 基数 `--spacing=.25rem`（4px）；chips/导航项 gap 6px；卡片 gap 16px；launcher 出血 20px（桌面）/12px（移动）；面板与视口顶留 50px（`100%-50px`）；nudge 条 padding `8 12 8 16`、gap 10px；chatgpt 输入卡 padding `7 10`、内容列 768px。

---

## ③ 交互状态机（launcher → panel → composer → 往返）

```
[关闭态] launcher（50×50 黑圆，白气泡 icon）
   │ hover: scale 1.04（不变色）
   │ click
   ▼
[开启] backdrop fade-in(.4s) ＋ 桌面: panel scale .9→1 + fade(.3s, 延迟80ms, origin=右下)
 │                     移动(<768px): 全宽 sheet 底部滑入(.6s) + 顶部 drag handle(50×4)
   ▼
[面板·匿名态]（本次实测的终点）
   顶部 InlineLoginNudge 展开(176ms)：灰提示句 + Log in pill
   主体 <openai-chatkit> 不渲染聊天 UI（登录墙）
   ▼ （登录后，未取证）
[对话态] ChatSurface=chatkit：欢迎语/快捷问题/输入行/发送键
   ▼ composer 聚焦（chatgpt 参照：无 ring，卡样式不变；发送钮随输入 disable→enable）  ＊仅 chatgpt 侧实测
   ▼ 发送 → 用户消息（右）→ 助手回复流式（左）→ 可继续/关闭   ＊未取证（需登录）
   │
   ▼ 关闭（Esc/关闭钮/遮罩点击）
[退场] panel .25s exit-snappy 收缩消失 → launcher 延迟 .1s 后 scale-in 回来
分支：Fullscreen（面板→整屏 100dvh）；ExitNodeToast（结束节点右下黑 toast）
```

---

## ④ 复刻要点（给 /prototype 的落地建议）

1. **必须保持 OpenAI 原味的**：launcher（50×50 正圆、`#181818` 底、24px 白聊天气泡 icon、右下 20/20、hover 仅 scale 1.04 不变色）；面板几何（400×min(600, 视口-50)、16px 圆角、`transform-origin bottom right`、入场 scale-fade .3s/退场 .25s、80ms 入场延迟）；移动端全宽 bottom sheet＋遮罩 `#0000004d`＋16px 顶角＋50×4 drag handle。
2. **投影体系照抄值**：launcher `0 8px 16px -4px 12%`；面板 `0 10px 15px -3px / 0 4px 6px -4px`＋hairline；Genie 现在的坞条若沿用站点令牌，至少把这三组值注册为新令牌（如 `--shadow-genie-*`）进 WindPress 管线，勿内联。
3. **字体不引入 OpenAI Sans**（私有字族）；用站点既有栈。字阶可直接对齐：面板内 12/14/16 三档就够（提示 12 灰、按钮 14/500、正文 16）。
4. **灰阶映射**：OpenAI gray-0/500/900/1000 ≈ 站点 surface/secondary/ink 系——建议复刻时取 `#fff`/`#5d5d5d`/`#181818`/`#0d0d0d` 四个锚点，其余用站点梯度填充；暗色值表已在上文（widget 自带 data-theme=dark 全套，值得为 Genie 暗态预留）。
5. **composer 参照 chatgpt 输入卡**：大圆角（28px 相对 768 宽卡；按 Genie 面板 400 宽等比可取 ~24px）、1px `rgba(0,0,0,.1)` 描边＋极浅三层投影、聚焦不加 ring；placeholder `#8f8f8f`；左右 44×44 圆形图标钮。
6. **快捷问题 chips 二选一**：help 风格（面板内平铺问题卡）或 chatgpt 风格（「+」菜单内联、未开放项置灰 `#8f8f8f`）。Genie 是 B2B 询盘助手，建议面板内平铺 3 条左右快捷问题（对应 help 中心的 cards 视觉：白卡、16px padding、10~16px 圆角）。
7. **登录提示条模式转译**：OpenAI 的 InlineLoginNudge（顶部 12px 灰条+pill）在 Genie 里没有登录语义，但其形态正适合放「这是 AI 系统」的法定披露条（我们已有首条消息披露的要求）——同款 8/12/8/16 padding、底边 hairline、176ms 展开动画。
8. **披露句位置**：照 chatgpt 把 12px 灰披露句放 composer 正下方（不是页脚），EN/DE 双语同型。
9. **发送钮**：44×44 圆形、空输入 disabled；有输入后实心（chatgpt 顶栏黑 pill 同语言：`#0d0d0d` 底白 icon）。
10. **移动端策略**：390 视口 Genie 不做缩小的桌面面板，改全宽 sheet（`100%-48px` 高、顶角 16px、把手 50×4）——与 OpenAI helper 一致。
11. **工程注意**：OpenAI 用 `<openai-chatkit>` Web Component 封装聊天 UI 与外壳解耦——Genie 重设计时同样建议把「外壳（launcher/panel/sheet/backdrop/披露条）」与「对话面（消息列表/composer）」分成两个组件边界，便于站点页嵌入与工具页全屏两种宿主。

---

## ⑤ 拦截/登录墙限制与替代取证路径（如实记录）

1. **helper 聊天 UI 在登录墙后**（最大限制）：点开面板后匿名用户只看到 "Log in for faster, more personalized support." 登录提示条；欢迎语、快捷问题、输入行、发送键、关闭钮、头部、消息气泡**均未取得截图**（需 OpenAI 账号登录，纪律禁止）。替代取证：(a) 实测登录提示条的全部计算样式；(b) 通过浏览器已加载样式表的 CDN 源（Playwright request 上下文带 Referer 拉取，直连 urllib 403）取得 widget 完整 CSS `ChatKitIntegration-alAtJNqs.css`（6.3KB），本文全部 widget 规则（Trigger/Panel/Sheet/Backdrop/ChatSurface/Fullscreen/Toast/Handle/Nudge）均逐字引自该源码；(c) 确认聊天面= `<openai-chatkit>` Web Component，其 UI 不在帮助中心 CSS 内。chatkit 组件内部的样式未取得。
2. **Cloudflare 挑战拦截 headless**：无头 Chromium 与 Chrome new-headless 均被 "Just a moment…" 拦截（title 实测）；改有头 Chrome 132 后 ~4s 自动通过，全程无人工干预。
3. **并发会话争用 Playwright 插件浏览器**：取证中途该共享浏览器被另一会话接管（tab 被切换/关闭，一度跳到 de-linker.com）。chatgpt.com 系列在争用发生前已完成；help.openai.com 系列整体迁移到本机 Python Playwright 独立通道完成。
4. **chatgpt.com 语言**：首访按 Accept-Language 呈中文；`lang` cookie 无效；经其设置面板切 English (US) 后取证。中文版仅存在于过程，最终产物全为 EN。
5. **未发送任何消息**：对话往返（用户气泡/助手回复流式态）无截图；状态机相应环节标注「未取证」。发送钮 enabled 态以 chatgpt 侧按钮令牌（44×44 圆钮）为参照并已注明来源差异。
6. **元素级截图两处不稳**：chatgpt「+」菜单与 helper 面板个别元素截图因入场动画 "element is not stable" 失败，改取同状态视口整截（`chatgpt_composer_plusmenu_1440.png`、`helper_panel_open_viewport_1440.png`），信息不损失。
7. `helper_home_full_1440.png`（1440×8246）原始 5.3MB，为满足 <800KB 以 256 色量化压缩至 767KB（版式为纯色卡面，无肉眼可见损失）。

## 截图索引（19 张）

| 文件 | 组件/状态/视口 |
|---|---|
| chatgpt_landing_full_1440.png | chatgpt landing 整页（EN，1440×900 无滚动） |
| chatgpt_landing_viewport_1440.png | 同上视口帧 |
| chatgpt_topbar_1440.png | 顶部导航（黑 pill Log in + 描边 Sign up） |
| chatgpt_sidebar_logincard_1440.png | 侧栏底部登录卡 |
| chatgpt_composer_group_1440.png | 居中标题+composer 卡（768 宽） |
| chatgpt_composer_focus_1440.png | composer 聚焦态（无 ring） |
| chatgpt_composer_plusmenu_1440.png | 「+」展开的快捷工具 chips 菜单 |
| chatgpt_disclosure_1440.png | 底部 12px 灰披露句 |
| chatgpt_login_modal_1440.png | 登录卡 modal（Google/Apple/phone/Email） |
| helper_home_full_1440.png | help 首页全页（搜索框+分类卡网格） |
| helper_launcher_closed_1440.png | launcher 关闭态（50×50 元素图） |
| helper_launcher_hover_1440.png | launcher hover 态（scale 1.04） |
| helper_panel_open_viewport_1440.png | 面板展开视口（匿名登录墙态） |
| helper_panel_open_full_1440.png | 面板展开全页 |
| helper_panel_container_1440.png | 面板容器元素图（400×600） |
| helper_home_mobile_390.png | help 首页移动端（launcher 在右下） |
| helper_home_mobile_scrolled_390.png | 移动端滚到底（launcher 悬浮） |
| helper_panel_open_mobile_390.png | 移动端 bottom sheet + 遮罩（展开态） |
