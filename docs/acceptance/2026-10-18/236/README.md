# #236 Genie · 拍照识别与附件读取 — 验收

实例 g236（快照 20261018-0541，线上 2026-10-17 21:49 UTC），`just serve g236`，模型只有 deepseek-flash（官方 API）；Jev 只在非铭牌轮次上被问。规格：`docs/specs/13-genie.md`"附件与铭牌"；规格 10 的"不在 VPS 上解析"改为只管知识索引。

## 评测（`services/genie/eval/attachments/`，结果 `eval/`）

```
uv run --locked python eval/attachments/nameplates.py --wp http://127.0.0.1:9121 \
    --service http://127.0.0.1:9124 --uploads ~/de-linker-data/20261018-0541/uploads \
    --out ../../docs/acceptance/2026-10-18/236/eval
```

**读取**（`eval/readings.json`）：11 张真实铭牌照片（来源见 `services/genie/eval/attachments/README.md`）+ 1 张研究里的合成铭牌，每张一次 deepseek-flash 调用（关思考，0.9–4.3 s）。

| 照片 | s | kind | 品牌 | 型号 | 额定值 | 分级 | 结果 |
|---|---|---|---|---|---|---|---|
| saj-sununo-plus-4k-m | 3.41 | nameplate | SAJ | Sununo Plus 4K-M | 15 | none | ✓ |
| saj-r5-6k-s2-15 | 3.15 | photo | INVS | R5-6K-S2-15 | 18 | — | ✗ 见下 |
| goodwe-gw10k-et | 3.57 | nameplate | GOODWE | GW10K-ET | 22 | none | ✓ |
| goodwe-gw3648-em（横拍） | 3.05 | nameplate | GOODWE | GW3648-EM | 21 | none | ✓ |
| goodwe-gw5048-em | 3.49 | nameplate | GOODWE | GW5048-EM | 16 | none | ✓ |
| goodwe-gw7600a-es | 3.46 | nameplate | GOODWE | GW7600A-ES | 20 | none | ✓ |
| goodwe-gw5048d-es | 3.46 | nameplate | GOODWE | GW5048D-ES | 16 | none | ✓ |
| goodwe-bat-c-label（五型号未勾选） | 4.28 | nameplate | GOODWE | null | 24 | unreadable | ✓ |
| pylontech-us3000c（型号被笔划过） | 3.12 | nameplate | PYLONTECH | null | 5 | unreadable | ✓ |
| ecoflow-powerocean-bd-5.1-s1 | 2.43 | nameplate | EcoFlow | EF BD-5.1-S1 | 7 | none | ✓ |
| pylontech-us3000c-thumbnail（140 px） | 1.26 | nameplate | PYLONTECH | null | 0 | unreadable | ✓ |
| nameplate-probe（**合成**，SAJ H2-10K-T3） | 1.82 | nameplate | SAJ | H2-10K-T3 | 10 | exact（4107） | ✓ |

11/12 按印刷读对、11/12 分级正确。**失分**：`saj-r5-6k-s2-15` 是一张拼图（左边是装在箱里的机器、SAJ 标志倒着，右边是不印厂家的标签）：关思考的五次读取型号都读对（R5-6K-S2-15），品牌依次是 INVS、SOLIS、HVS、INVS 与 null（`thinking.md`）——除 null 外都是猜测；其中两次把整张图判为 photo 而不是铭牌（这次即是），其余判为 nameplate、分级 none。后果有限：分级不依赖品牌（型号不在我们范围即 none），卡上照实显示读到的品牌，客户可点 "Type the model" 纠正；但这是模型的猜测，记在这里，不靠针对这张图改提示词去掩盖。

真实照片里没有我们经营的型号（客户拍的多是自己已装的设备）；精确命中这一档用合成铭牌评测（README 写明），在实网与浏览器里都跑通（下表 plate-exact、e2e）。找过 SAJ H2/HS2/HS3/CB2、GoodWe ET/ETR/ESA、Pylontech Force H2/US5000 的真实铭牌照片，没有找到。

**轮次**（`eval/turns.json`，真实服务 HTTP，EN/DE 各一遍）：18/18 通过。

| 用例 | EN s | DE s | 内容 |
|---|---|---|---|
| plate-exact | 8.9 | 4.2 | 合成 SAJ H2-10K-T3：分级 exact，出 4107 产品卡，请客户确认 |
| plate-none-saj / -goodwe | 9.8 / 8.5 | 10.0 / 13.5 | 说出读到的型号、我们不经营；同品牌产品作为另外的设备出卡 |
| plate-none-pylontech | 13.4 | 9.8 | 型号读不出（unreadable），只说读到的品牌，请清晰照片或手输 |
| plate-unreadable | 2.8 | 4.8 | 缩略图：unreadable，不出卡 |
| datasheet-en（EN 数据表） | 10.6 | 10.8 | H2-10K-T3 最大 PV 功率 20000 Wp，引用附件或数据表 |
| datasheet-de（DE 数据表） | 13.1 | 13.9 | 最大 DC 电压 1000 V，引用 att1 |
| drawings（4 页无文字层的安装指南） | 30.8 | 35.7 | 4 页渲染读出，概述内容并引用 att1 |
| follow-up（不带文件，读取由代理带回） | 10.5 | 10.0 | 铭牌上的最大 PV 输入电压 1000 Vdc，引用 att1 |

最长的一轮是图纸 PDF（31–36 s，四页并行读图 + 回答），在壳的 60 s 内。

**思考开关**：`thinking.md`（开思考 2.9–31.4 s、一张两次超时；关掉 0.9–4.0 s，型号读得一样或留空）。

**确认消息实测**：`copy-review.md` 末节与 `eval/confirmations.json`：六句确认消息 EN/DE 各自走到 documents / pairing / products 路由。

## 视觉验收（`shots/`，`tests/e2e/specs/genie-attachments.spec.ts`，EN/DE × 1440/390）

每组 8 个状态：`1-photo-prompt`（预览卡"拍铭牌"打开的面板）、`2-refused`（xlsx 当场拒绝）、`3-picked`（选好的照片）、`4-nameplate-exact` 与 `4-nameplate-card`（铭牌卡与产品卡）、`5-confirmed`（点"Yes, what works with it?"后的回答）、`6-nameplate-unreadable`、`7-type-the-model`（手动输入出口，输入框已聚焦）、`8-datasheet`（PDF + 问题）。

顺带修掉：390 px 的 dock 底板（`.linker-genie-app` 的白底）被固定定位的 30% 遮罩盖住，整张面板发灰（任何入口打开的 dock 都如此，产品页 Ask 实测同样）；现在列本身带白底（`genie.css`）。

**hero**：hero 接线是 #232。本票把附件做成可复用的两件：`src/genie/attachments/prepare.ts`（照片重编码、类型与大小检查）与 `useAttachments`（选中、准备、拒绝、上限），加上 dock 加载器的 `linker-genie-ask {attach:true}`（打开 Genie 并给出选择照片的按钮）。hero 的拍照与附件控件直接用它们；hero 本身没有在本票接线，所以没有 hero 截图。

## 上传安全（测试）

- 代理 `Attachments`：`tests/php/Unit/AttachmentsTest.php`（四种类型按首字节通过、伪装的 exe/svg/PDF/WAV/HEIC 原样 415、超过 3 个与坏 base64 400、单文件与整轮超限 413、超过每小时额度 429、访客按连接、登录按账号）；`ProxyTest`（文件走 `attachments`、不进存档消息、会话的 readings 随轮次带上、`reading` 事件不回给浏览器、被拒的文件不到服务也不开会话）；`ThreadTest`（readings 存进 meta、最新 10 条、从存档流里拿掉）。
- 服务：`tests/test_attachments.py`（照片摆正、≤1.69 MP、EXIF/GPS 去掉；类型伪装、超限、非 base64、解压炸弹在解码前拒绝；PDF 文字层、扫描页渲染上限与未读页点名、坏 PDF；deepseek 400 立即报错并记日志、5xx 重试一次、非 JSON 报错；没有密钥记日志；读取的数字是事实、质检能重建；长文件按问题选段；代理与服务的上限数值一致）；`tests/test_nameplate.py`（真实产品词上的分级；铭牌轮次不问 Jev；exact/none/unreadable 的路由与卡；引用照片数字的回答通过核验并水合；追问不带文件；SSE 带卡与读取、轮次日志里没有文件字节）。
- 壳：`src/genie/attachments/prepare.test.ts`（类型、缩放、命名、HEIC 打不开、经 canvas 重画、上限与 PHP 一致）、`App.test.tsx`（文件随轮次发送、拒绝在发送前、代理拒绝说明原因且不留在对话里、确认按钮发出的消息、读不出时换照片与手输、预览卡打开的选择按钮）、`src/preview/controller.test.ts`（"拍铭牌"建议发 `{attach:true}`）。

## 评审第 1 轮修复（PR #309，2026-10-18 接手续做）

评审意见见 PR #309 评论 "Review, round 1 (#236): two axes, Standards and Spec"（14 项已裁定）。修复在被 API 限流中断后由接手会话续完，逐项状态：

| 项 | 状态 | 落点 |
|---|---|---|
| 1 第三方照片 | **业主裁定推翻**：照片用于本评测已获授权，**保留在仓库** `eval/attachments/photos/`（2026-10-18）。README 的"图片在哪"一节按此改写，双 sha256 溯源保留 | `eval/attachments/README.md` |
| 2 PDFium 线程安全 | 完成：PDF 工作进独立进程（`pdfwork.py`），带墙钟超时与内存隔离；并发与恶意/慢 PDF 测试 | `pdfwork.py`、`test_attachments.py` |
| 3 无来源数字 | 完成：schema 的长度上限与 id 正则在代码处注明来源 | `schema.py` |
| 4 PHP `Attachments::check` | 完成：先按 base64 长度判定再解码；拒绝也计入额度；先检查整轮文件再取额度 | `Attachments.php`、`AttachmentsTest.php` |
| 5 服务请求体与鉴权 | 完成：ASGI 层按整轮上限截断；turn 端点要求壳的令牌（`gate.py`）；PDF 解析有墙钟上限 | `gate.py`、`test_nameplate.py` |
| 6 轮次日志 PII | 完成：reading 只记一次全文，后续轮次记 `earlier`；删除会话时 `forget` 清 reading 文字、由该文字派生的调用（`from_reading`）的参数/结果，以及 `understanding` 路由日志里的同一段文字。规格 13 "保存与清理"已写明 | `log.py`、`route.py`、`understand.py`、`docs/specs/13-genie.md` |
| 7 视觉通道守卫 | 完成：图像读取仅在 base URL 主机为 `api.deepseek.com` 时运行，否则显式失败 | `gate.py`、`vision.py` |
| 8 附件里的价格/交货 | 完成：提示词加同一条规则；核验拒绝把 `att*` 数字说成价格/运费；评测新增价格表与交货条款 PDF（EN/DE）与"不得出现金额/时效、交货走 handoff"断言 | `prompts/{en,de}/system.md`、`ground.py`、`eval/attachments/papers.py`、`cases.json` |
| 9 单位与地区格式 | 完成：附件数字带单位水合、按本轮语言格式化；评测通过条件检查单位与小数格式 | `hydrate.py`、`figures.py`、评测 |
| 10 "der Dienst" 泄漏 | 完成：路由提示不再出现内部用语，只对客户说照片与设备 | `route.py` |
| 11 品牌猜测 | 完成：读到的品牌只在本站产品词表内才保留，否则按未读出处理；`thinking.md` 的表述已更正 | `nameplate.py`、`thinking.md` |
| 12 真实铭牌精配 | 部分完成：从我们自托管文档抽出铭牌图（GoodWe GW112.6-BAT-AC-G10 两张 exact、GW5KN-ET 一张 none）；SAJ 与 Pylontech 的托管文档无铭牌，README 记录排查结论。评测用例已接入（`--labels`），**尚未重跑**（需本地栈与官方通道密钥） | `eval/attachments/{README.md,cases.json,nameplates.py}`、`~/de-linker-data/eval/attachments/labels/` |
| 13 首页预览卡 | 完成：e2e 改为桌面点卡片上的"拍铭牌"建议（手机按现有设计无卡片，走标记入口）；截屏新增 `${lang}-${width}-0-card`。**截屏需在本地栈重拍** | `tests/e2e/specs/genie-attachments.spec.ts` |
| 14 hero 交接 | 已记录在 #232 | #232 评论 |

本轮验证：服务端 `pytest` **909 passed**、`ruff`、`mypy` 全过；壳 `vitest` **178 passed**、`tsc`、`eslint` 全过；PHP 单元 **230 passed**。端到端评测与截屏重跑待本地栈（与合并前一致的门）。
