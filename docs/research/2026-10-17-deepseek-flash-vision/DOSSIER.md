# Genie · deepseek-flash 官方 API 能否看图读文件（#230）

- 日期：2026-10-17（本机时区）；取证与实测窗口为 UTC 2026-10-16 17:11–17:24（周五，非高峰价时段）
- 票：#230（地图 #220）。下游实现票 #236（拍照识别与附件读取）以本卷结论为准
- 取证通道：外部文档全部经 Apify（5 次运行，actor、run id、输入见 `raw/apify/runs.json`）。实测只打官方 `https://api.deepseek.com`，模型只有 `deepseek-flash`；另有 1 次 `GET /models` 列表调用。Pydantic AI 读本机安装件源码，版本与 `services/genie/uv.lock` 锁定的一致
- 密钥：从 `~/.config/terravolt-builder/deepseek.env` 读进进程内存，没有打印，也没有落盘。`raw/` 全目录用脚本逐字节比对过 DeepSeek 密钥和三个 Apify 令牌，命中 0 次（`raw/scripts/` 运行时才从环境变量或本机凭据文件读取，文件本身不含任何密钥）

## 0. 结论先行

- **看图：成立。** 官方 `deepseek-flash`（DeepSeek-V4.1-Flash）在 `/models` 里自报 `input_modalities: ["text","image"]`，官方有专门的 Vision 指南。实测一张合成铭牌图走 OpenAI 兼容的 `image_url`（base64 data URL），HTTP 200、2.3 s，品牌、型号和 9 项额定值逐字正确。Genie 现用的 Pydantic AI 2.55.0 原样把 `BinaryContent` 图片转成同一形状，经 Genie 自己的 `build_model()` 实测也是 200。
- **读文件：只有图片文件成立。** 官方 API 不收 PDF：Files API 和 `file` 内容块只收 JPEG/PNG/GIF/WebP，Anthropic 兼容端点的 `document` 块写明 "Not Supported"，Responses API 写明 "File inputs are not supported"。实测一份 1 页 PDF，两种请求形状都是 400。
- 所以业主要的两项功能都能用 deepseek-flash 做，不用换模型，也不碰模型路由铁律。铭牌照片直接发；PDF（数据表、图纸）要先转成文字（有文字层的页）或页面图片（扫描页、图纸页），再交给 deepseek-flash 读。转换放在哪里，牵涉 `docs/specs/10-knowledge-index.md` 第 39 行"不在 VPS 上解析或跑模型"，见 §9。

## 1. 来源

外部来源全部经 Apify 取得；时间是 Apify 记录的页面加载时间（UTC）。页面原文（带来源头注释）在 `raw/apify/pages/`，完整数据集在 `raw/apify/*.json`。

| 编号 | 来源 | 取得方式 | 抓取时间（UTC） |
|---|---|---|---|
| S1 | https://api-docs.deepseek.com/guides/vision | `apify/website-content-crawler` run `MIJhRxzpdljaeZqof` | 2026-10-16T17:13:09Z |
| S2 | https://api-docs.deepseek.com/zh-cn/guides/vision | 同上 | 2026-10-16T17:13:21Z |
| S3 | https://api-docs.deepseek.com/guides/files_api | 同上 | 2026-10-16T17:13:04Z |
| S4 | https://api-docs.deepseek.com/quick_start/pricing | 同上 | 2026-10-16T17:12:53Z |
| S5 | https://api-docs.deepseek.com/zh-cn/quick_start/pricing | 同上 | 2026-10-16T17:13:22Z |
| S6 | https://api-docs.deepseek.com/quick_start/token_usage | 同上 | 2026-10-16T17:13:21Z |
| S7 | https://api-docs.deepseek.com/api/list-models | 同上 | 2026-10-16T17:13:01Z |
| S8 | https://api-docs.deepseek.com/api/create-chat-completion | `apify/website-content-crawler`（playwright:firefox，逐个点开 tab）run `agng08l0hBGQphJGf` | 2026-10-16T17:16:25Z |
| S9 | https://api-docs.deepseek.com/guides/anthropic_api | run `MIJhRxzpdljaeZqof` | 2026-10-16T17:13:02Z |
| S10 | https://api-docs.deepseek.com/guides/responses_api | 同上 | 2026-10-16T17:13:08Z |
| S11 | https://api-docs.deepseek.com/news/news260910 | 同上 | 2026-10-16T17:13:16Z |
| S12 | https://api-docs.deepseek.com/news/news260821 | 同上 | 2026-10-16T17:13:17Z |
| S13 | https://api-docs.deepseek.com/updates | 同上 | 2026-10-16T17:12:54Z |
| S14 | https://api-docs.deepseek.com/quick_start/rate_limit | 同上 | 2026-10-16T17:13:20Z |
| S15 | https://api-docs.deepseek.com/quick_start/error_codes | 同上 | 2026-10-16T17:13:19Z |
| S16 | https://api-docs.deepseek.com/guides/thinking_mode | 同上 | 2026-10-16T17:13:07Z |
| S17 | https://pydantic.dev/docs/ai/core-concepts/input/ | `apify/rag-web-browser` run `KRsLr2MzCHaBqpnZK` | 运行开始 2026-10-16T17:23:47Z |

文档站整站抓取 110 页（英文与 zh-cn，114 个请求全部成功）。两次 `apify/rag-web-browser` 搜索（run `E2NeWlXpFnZcAI3Xr`、`xRPgsPlfQBWamjAzt`）用来发现页面，命中的正是 S1、S11、S13；第三方博客（openrouter.ai、omniakey.com、zentor.ai）只留在原始数据里，没有用作依据。

本机与实测来源：

| 编号 | 内容 | 位置 |
|---|---|---|
| L1 | `GET https://api.deepseek.com/models`，2026-10-16T17:11:47Z，HTTP 200 | `raw/models.json` |
| L2 | pydantic-ai-slim 2.55.0、openai 3.28.0 安装件源码（`services/genie/uv.lock` 第 2168–2169 行、第 1835–1836 行锁定的版本；安装件 dist-info 版本相同） | `services/genie/.venv/lib/python3.12/site-packages/`（主检出的 venv，git 忽略） |
| P1–P4 | 4 次实测调用的请求（无密钥、base64 以占位符代替）与响应 | `raw/probe-*.json`，见 §6 |

## 2. 模型 ID（问题 1）

L1 原样返回两个模型：

| id | name | context_window | max_output_tokens | input_modalities | output_modalities | effort |
|---|---|---|---|---|---|---|
| `deepseek-flash` | DeepSeek-V4.1-Flash | 1048576 | 393216 | `text`, `image` | `text` | low / high / max，默认 high |
| `deepseek-v4-pro` | DeepSeek-V4-Pro | 1048576 | 393216 | `text` | `text` | low / high / max，默认 high |

S7 对 `input_modalities` 的定义是 "**Possible values:** [`text`, `image`]"，说明为 "The input types the model accepts."，取值里没有文件或文档类。

S4 价格页（英文原文）：

> MODEL VERSION | DeepSeek-V4.1-Flash | DeepSeek-V4-Pro-0813
>
> [Vision] | ✓ | Not supported
>
> (1) Use `deepseek-flash` as the model name. The legacy names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are still accepted, but the corresponding models have been retired, their requests are served by the DeepSeek-V4.1-Flash model and billed at the Flash price.

S11（2026-09-10 发布说明）："Introducing the smallest model in our new architecture family, with native visual understanding." 以及 "V4.1-Flash is now live on the DeepSeek API with native multimodal support. Set your model to `deepseek-flash`."
S13（更新日志 2026-09-10）："DeepSeek V4.1 Flash is now available on the DeepSeek API with native multimodal support. Change the model name to `deepseek-flash` to call the latest V4.1 Flash model."

结论：`deepseek-flash` 背后是 DeepSeek-V4.1-Flash，原生支持图片输入；旧名 `deepseek-v4-flash`、`deepseek-v4-flash-vision-exp` 也落到同一模型、按 Flash 价计费。`deepseek-v4-pro` 不支持图片（与 Genie 无关，Genie 只用 `deepseek-flash`）。实测响应里的 `model` 字段也是 `deepseek-flash`（P1）。

## 3. 图片输入（问题 2）

### 3.1 请求形状

S1 原文："The `deepseek-flash` model accepts images alongside text, so you can ask the model to describe pictures, read text from screenshots, analyze charts, and more." 以及 "There are three ways to provide an image to the model. All of them use the standard OpenAI-compatible Chat Completions format, where `content` is an array of blocks instead of a plain string."

三种方式（S1 原文摘录）：

1. **base64 内联**："Encode the image and embed it directly in the request as a `data:` URL. … The encoded data counts toward the **48 MiB** request body limit"
   ```json
   {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<BASE64_DATA>"}}
   ```
2. **外链 URL**："Pass a publicly accessible `http(s)` link and the model downloads the image for you. The URL must be at most **8192 characters**, the image file may be at most **32 MiB**, and the download must complete within **60 seconds**."
   ```json
   {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
   ```
3. **Files API 的 `file_id`**："Upload an image once with the Files API, then reference its `file_id` in your requests. … images referenced via Files API `file_id` may be up to 64 MiB"
   ```json
   {"type": "file", "file_id": "file-api-xxxxxxxxxxxxxxxx"}
   ```
   同一个 `file` 块也可以内联："a `file` block can carry the image inline as base64 via `file_data` instead of `file_id` (the two are mutually exclusive)"：`{"type": "file", "file_data": "data:image/jpeg;base64,<BASE64_DATA>", "filename": "image.jpg"}`。注意 DeepSeek 的 `file` 块是**扁平**的（`file_id`/`file_data` 直接挂在块上），和 OpenAI 官方把它们包在 `"file": {...}` 里不同，§5 的 P4 会撞上这一点。

S8（Chat Completions API 参考，user message）："The contents of the user message. Either a string, or an array of content parts (for image input)." 内容块只有三种：Text content part、Image content part（`image_url.url` + 可选 `detail`）、File content part（`file_id` / `file_data` / `filename`）。S8 里 tool message 的 `content` 也允许同样三种块。

`detail`（S1）：`low` 先缩到 512×512（"Faster and cheaper when fine visual detail is not important"）；`high`、`original`、`auto` 都保留原图（`auto` "Currently equivalent to `original`"）。

另外两条端点也能传图（S1；Genie 不走，未实测）：Anthropic 兼容端点 `https://api.deepseek.com/anthropic` 用 `{"type":"image","source":{"type":"base64"|"url"|"file",…}}`；Responses API 用 `input_image` 块，并且允许把图片放在 `function_call_output` 里（S10）。

### 3.2 限制

S1 "Limits" 表原文：

| Limit | Value |
|---|---|
| Supported formats | JPEG, PNG, GIF, WebP |
| External URL length | 8192 characters |
| Request body size | 48 MiB |
| Max single image size (base64 / external URL) | 32 MiB |
| Max single image size (Files API `file_id`) | 64 MiB |
| Max images per request | 600 |
| Max total image size per request | 64 MiB without `file_id` images; up to 200 MiB including `file_id` images |
| Max image dimension | 8192 px per side; drops to 4096 px per side when a request contains 15 or more images |

其他约束：

- 格式按内容判断（S1）："The format is detected from the actual file content, not from the file name or the declared MIME type." 表里没有 HEIC。
- 角色（S1 "Restrictions"）："Images are supported in `user` messages only. Images in `system` or `assistant` messages return a `400` error."
- Files API（S3）：单文件最大 64 MiB，上传须在 10 分钟内完成，每用户存储 25 GiB、最多 10000 个文件；"Omit both `expires_after` fields to keep the file permanently."——不设过期就永久保存。
- 并发（S14）：`deepseek-flash` 每账户 2500 并发，超出返回 429。
- 推算：base64 会把字节放大约 4/3，所以 48 MiB 请求体实际能装的原始图片字节约 36 MiB（由 S1 的 48 MiB 推算，不是官方数字）。

zh-cn 版（S2）的数字与英文版逐项一致（48 MiB、32 MiB、64 MiB、600 张、8192/4096 px、1024 token）。

### 3.3 Token 与价格

S1 "Token Usage" 原文：

> Images are converted into tokens based on their dimensions, and these tokens are billed together with your text tokens.
>
> - Images with a total pixel count below roughly 544×544 are scaled up while preserving their aspect ratio.
> - Larger images are scaled down while preserving their aspect ratio, so that the total pixel count after resizing is roughly that of a **1300×1300** image.
>
> As a result, there is an upper bound of **1024** tokens per image … When a request contains multiple images, each image is counted independently under the same rule

S6 提供网页上的图片 token 计算器，并说明 "This is an estimate only … refer to the usage returned by the API as the source of truth." S12（2026-08-21，已下线的 V4-Flash-Vision-Exp）写的是 "up to 384 tokens each"，那是旧模型的数字；现行 `deepseek-flash` 以 S1 的 1024 为准。

`deepseek-flash` 价格（S4，每 1M token，美元）：

| | 非高峰 | 高峰 |
|---|---|---|
| 输入（缓存命中） | $0.003 | $0.006 |
| 输入（缓存未命中） | $0.15 | $0.30 |
| 输出 | $0.60 | $1.20 |

S5 的人民币价：命中 0.02/0.04 元，未命中 1/2 元，输出 4/8 元。高峰时段（S4 注 2）："Peak hours are 01:00 - 04:00 and 06:00 - 10:00 UTC, Monday through Friday, excluding Chinese public holidays." 图片 token 和文字 token 同价，没有单独的图片价。Files API 本身免费（S12："Free to use"）。

推算（由上表与 1024 上限算出）：

- 一张图最多 1024 token → 未命中时每张最多 $0.000154（非高峰）/ $0.000307（高峰）。
- P1 实测一次铭牌识别：输入 611 + 输出 414 token → $0.00034（P1 发生在非高峰）；同样用量放在高峰为 $0.00068。
- 德国工作日上午落在高峰价段：06:00–10:00 UTC 即夏令时 08:00–12:00、冬令时 07:00–11:00。

### 3.4 延迟

文档没有给延迟数字：在整站 110 页里检索 latency / time to first / TTFT / tokens per second，只命中 V3 时代的两篇旧新闻（news0802、news1226）和 Codex 接入页（英文与 zh-cn）里一段内嵌提示词的 "round-trip latency"，都不是 V4.1-Flash 的延迟数字；S11 只有定性的 "faster inference"。

实测（非流式、思考模式按默认开启、非高峰时段，各 1 个样本）：

| 调用 | 用时 | 输出 token（其中推理） |
|---|---|---|
| P1 原始 HTTP，铭牌图 | 2.30 s | 414（190） |
| P3 经 Pydantic AI，同一张图 | 2.16 s | 420（196） |
| P2、P4 PDF 被拒 | 0.18 s、0.25 s | — |

两个成功样本只能说明"非高峰、单张约 0.7 MP 的图、约 400 输出 token 时约 2 秒"，不构成延迟分布。

## 4. 文件与 PDF（问题 3）

官方 API 不收 PDF，证据五条，彼此独立：

1. Files API（S3）："The Files API lets you upload images and reference them later by `file_id`." "Supported formats: **JPEG, PNG, GIF, and WebP**. The format is detected from the actual file content."
2. Chat Completions 的 File content part（S8）：`file_data` 是 "A base64-encoded data URL of the image (`data:image/jpeg;base64,...`). Mutually exclusive with `file_id`."——字段说明里只有图片。
3. `/models` 的 `input_modalities` 取值只有 `text`、`image`（S7、L1）。
4. Anthropic 兼容端点（S9 "Message Fields" 表）：`array, type = "document"` → **Not Supported**。
5. Responses API（S10 "Input Items" 表，`message` 行）："`input_image` parts are processed as real images … File inputs are not supported"。

实测（§6 的 P2）：按 S8 文档形状发 `{"type":"file","file_data":"data:application/pdf;base64,…","filename":"datasheet-probe.pdf"}`，官方回：

```
HTTP 400
.messages[0]: You have uploaded an unsupported file. Please make sure your file is valid and has one of the following formats: webp, png, jpeg, and gif. (request_id: 60e00258-ed04-44d3-b2ae-b92223970f40)
```

报错是显式的 400，API 不会静默丢掉附件再让模型凭空作答。

所以 PDF 必须先在我们这边转换。项目里现成的 Docling 只用于知识索引的离线构建：`services/genie/pyproject.toml` 的 `index` 依赖组注释写着 "the VPS never installs it (docs/specs/10-knowledge-index.md: no parsing or models on the VPS)"，`docs/specs/10-knowledge-index.md` 第 39 行原文"不在 VPS 上解析或跑模型"，第 23 行写明 VPS 为 1 vCPU、3.9 GB、无 GPU。Docling 的 OCR 在构建机上靠 Apple Vision（`ocrmac`，仅 macOS）。所以运行时的附件转换不能照搬 Docling 那条管线，选项见 §9。

## 5. Pydantic AI 能否传图（问题 4）

锁定版本：`pydantic-ai-slim` 2.55.0、`openai` 3.28.0（L2）。Genie 的 `build_model()`（`services/genie/src/linker_genie/agent.py` 第 120–157 行）用 `OpenAIChatModel` + `DeepSeekProvider`，走 Chat Completions。

源码（`pydantic_ai/models/openai.py`，2.55.0 安装件）：

- `BinaryContent` 图片（第 2138–2142 行）：`image_url = ImageURL(url=item.data_uri)`，有 `vendor_metadata` 时带 `detail`，产出 `{"type":"image_url","image_url":{"url":"data:<mime>;base64,…"}}`，与 S1 的方式 1 一致。
- `ImageUrl`（第 2118–2126 行）：默认原样发 URL（S1 的方式 2）；`force_download=True` 时先下载再发 data URI。
- 文档类 `BinaryContent`（第 2150–2159 行）与 `DocumentUrl`（第 2177–2207 行）：产出 OpenAI 的**嵌套**形状 `{"type":"file","file":{"file_data":…,"filename":"filename.<ext>"}}`。profile 开关 `openai_chat_supports_document_input`（`profiles/openai.py` 第 364 行）默认 `True`，DeepSeek 的 profile 没有关掉它。
- `UploadedFile` 图片（第 2239–2247 行）：`OpenAIChatModel` 直接抛 `UserError`（"Referencing an uploaded image by `file_id` is not supported by OpenAIChatModel. Use `ImageUrl` or `BinaryContent` for images, or use `OpenAIResponsesModel`."）。也就是说，Genie 现在这条路用不了 Files API 的 `file_id`。
- 工具返回的文件（第 2091–2098、2115–2116 行）：文字进 tool message，文件另起一条 user message。这和 S1 "Images are supported in `user` messages only" 相容。
- 图片没有任何能力门：`providers/deepseek.py` 的 profile（第 45–87 行）只声明思考、JSON、tool_choice 相关能力。名字表 `DeepSeekModelName`（第 26 行）不认识 `deepseek-flash`，`is_v4` 判断（第 47 行）按 `deepseek-v4-` 前缀；这些只影响思考相关的默认值，Genie 已在 `build_model` 的 profile 里自行声明，与传图无关。

文档（S17，Pydantic AI "Multimodal Input"）："Note: Some models do not support image input. Please check the model’s documentation to confirm whether it supports image input." 表中 `OpenAIChatModel` 一行：直接发 URL 的是 `ImageUrl`，下载后发字节的是 `AudioUrl`、`DocumentUrl`。对不收文档的模型，文档给的办法是："you can still provide document content as text input by extracting the text yourself and passing it as a string or `TextContent`."

实测（§6）：

- P3：经 Genie 自己的 `build_model()`（worktree 源码，未改一行）发 `BinaryContent(png)`。抓到的线上请求体就是 S1 的形状，`POST https://api.deepseek.com/v1/chat/completions` 返回 200。
- P4：同一路径发 `BinaryContent(application/pdf)`。Pydantic AI 发出嵌套的 `file` 块，官方回 400 ".messages[1]: file must have a file_id or file_data (request_id: 71e905f3-39f7-419d-91d3-a0f8167b8b9f)"——DeepSeek 只认扁平的 `file` 块，嵌套形状在格式校验这一步就被拒；就算改成扁平形状，PDF 也会像 P2 那样被拒。

结论：2.55.0 原样支持图片（`BinaryContent` 与 `ImageUrl` 都行），不用升级、不用改库、不用自己拼请求。文档类输入在这条路上走不通，原因有两层：DeepSeek 不收 PDF；Pydantic AI 的 `file` 形状也和 DeepSeek 的不一致。

## 6. 实测（问题 5）

### 6.1 测试件

- `raw/nameplate-probe.png`：本机用 Pillow 生成的**合成**铭牌（生成脚本 `raw/scripts/make_fixtures.py`）。1040×680，152 927 字节，sha256 `b67ceb771aa34672…`，64 色调色板，倾斜 2.5°，0.8 px 高斯模糊加噪点，模拟手机翻拍。标签上的数值是测试串，**不是产品事实**，没有拿 SAJ 数据手册核对过。逐行真值在 `raw/nameplate-probe.truth.json`。
- `raw/datasheet-probe.pdf`：手写的 1 页 PDF，带 Helvetica 文字层（pdftotext 可读出三行），694 字节，sha256 `0624d8f422ce77ae…`。

### 6.2 调用清单

全部打官方端点，模型都是 `deepseek-flash`，共 5 次 chat completion，外加 1 次 `GET /models`：

| # | 时间（UTC） | 通道 | 内容块 | 结果 |
|---|---|---|---|---|
| L1 | 17:11:47 | `GET https://api.deepseek.com/models` | — | 200，见 §2 |
| P1 | 17:19:56 | 原始 HTTP `POST https://api.deepseek.com/chat/completions` | text + `image_url`（data:image/png） | 200，2.30 s |
| P2 | 17:20:18 | 同上 | text + 扁平 `file`（`file_data`: data:application/pdf） | 400，0.18 s |
| P3′ | 17:20:18 与 17:21:26 之间 | Pydantic AI（`build_model()`） | text + `BinaryContent(image/png)` | 请求已发出；我的脚本按旧 API 调了 `result.usage()`（2.55 里 `usage` 是属性），在写记录之前崩溃，结果未存档 |
| P3 | 17:21:26 | 同上，修正脚本后重发 | 同 P3′ | 200，2.16 s |
| P4 | 17:21:44 | 同上 | text + `BinaryContent(application/pdf)` | 400，0.25 s |

P3 的 `prompt_cache_hit_tokens` 是 384：P3′ 与 P3 的前缀相同（system 指令 + 同一段文字 + 同一张图），最可能是 P3′ 留下的缓存；P1 没有 system 指令，前缀不同。可见图片内容也能吃到上下文缓存。

### 6.3 请求形状（P1；无密钥，base64 以占位符代替）

```json
POST https://api.deepseek.com/chat/completions
Authorization: Bearer <DEEPSEEK_API_KEY>
Content-Type: application/json

{
  "model": "deepseek-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "This photo shows the nameplate (rating label) of a device. Transcribe it exactly as printed: the brand, the model, the product type, every rating with its label and value, the serial number and any marks. Do not correct, complete or guess anything; write null for anything you cannot read. Answer in JSON: {\"brand\": str|null, \"model\": str|null, \"product_type\": str|null, \"ratings\": [{\"label\": str, \"value\": str}], \"serial\": str|null, \"marks\": [str]}"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,<raw/nameplate-probe.png 的 base64：152927 字节>"}}
      ]
    }
  ],
  "response_format": {"type": "json_object"}
}
```

请求体 204 586 字节。没有设置 `thinking`，按 S16 默认开启、effort 为 high。P3 的线上请求体（`raw/probe-3-image-pydantic-ai.json` 的 `wire`）与此相同，只多了 Pydantic AI 的 `instructions` 生成的一条 `system` 消息和 `"stream": false`，地址是 Genie 用的 `https://api.deepseek.com/v1/chat/completions`。

### 6.4 响应摘要与识别质量

P1：`id` `5c9303f0-744c-4f9e-9be9-7ba3325d5e33`，`model` `deepseek-flash`，`finish_reason` `stop`；usage：`prompt_tokens` 611（全部未命中缓存），`completion_tokens` 414（`reasoning_tokens` 190）。`response_format: json_object` 与图片输入同时可用，返回的是不带代码栅栏的纯 JSON。

| 字段 | 标签真值 | P1 | P3 |
|---|---|---|---|
| brand | SAJ | SAJ | SAJ |
| product_type | HYBRID INVERTER | 一致 | 一致 |
| model | H2-10K-T3 | H2-10K-T3 | H2-10K-T3 |
| ratings（9 项，标签与数值） | Max. PV input voltage 1000 V … Ingress protection IP65 | 9/9 逐字一致 | 9/9 逐字一致 |
| serial | S/N: H2T3K10A2609000123 | H2T3K10A2609000123（按提问只给值） | 同 P1 |
| marks | CE、IEC 62109 | CE、IEC 62109 | CE、IEC 62109 |

两次输出逐字相同。思维链（`reasoning_content`）里模型自己复核了一遍序列号。

图片 token 估算：611 减去文字部分（提示 449 字符，按 S6 "1 English character ≈ 0.3 token" 约 135）≈ 476，含消息模板开销；按 S1 的面积规则推算 1024 × (1040×680)/(1300×1300) ≈ 429。两者同一量级。API 的 usage 不单列图片 token（S8 的 usage 结构），所以只能估算。

### 6.5 PDF 两条路的报错原文

- P2（扁平 `file` + `file_data`，即 S8 文档形状）："`.messages[0]: You have uploaded an unsupported file. Please make sure your file is valid and has one of the following formats: webp, png, jpeg, and gif. (request_id: 60e00258-ed04-44d3-b2ae-b92223970f40)`"，`type`/`code` 都是 `invalid_request_error`。
- P4（Pydantic AI 的嵌套 `file`）："`.messages[1]: file must have a file_id or file_data (request_id: 71e905f3-39f7-419d-91d3-a0f8167b8b9f)`"，Pydantic AI 抛 `ModelHTTPError`（status 400）。

## 7. 旁注：与实现直接相关的代码现状

- 前端 `plugins/linker-tools/src/genie/App.tsx` 第 198–208 行的 `ask()`：问题文本后面拼 "Attached: <文件名>"；第 892–896 行注释写明 "The turn route carries text only (docs/specs/13-genie.md)… nothing claims the file's bytes went anywhere."
- WP 代理 `plugins/linker-tools/includes/Genie/Proxy.php` 的 `turn()`（第 246–300 行）：把浏览器送来的整段 `messages` 原样转给服务的 `/assistant/turn`，**再把同一段 `messages` 写进会话记录**（`$this->thread->record(...)`）。图片如果以 base64 混在 `messages` 里，每一轮都会被写进 WordPress 库，也会跟着每轮重发。
- 服务 `services/genie/src/linker_genie/schema.py` 第 116–117 行：消息 `content: str`，现在没有放附件的字段。
- `agent.py` 第 130–139 行的注释说 deepseek-flash "always thinks — its effort levels are low/high/max with no "none""。现行官方文档的说法不同：S16 的开关是 `{"thinking": {"type": "enabled/disabled"}}`，S8 的 `reasoning_effort` 可取 `none`（"`none` disables thinking mode"）；`/models` 的 `supported_levels` 按 S7 定义本来就不列 `none`（"`none`, which turns thinking mode off, is not included"）。本票没有实测关闭思考，只记下这处文档与注释不一致，留给本线判断。它影响铭牌识别这类单独调用能不能关思考来降延迟。
- 建议在 `build_model` 的 profile 里加 `"openai_chat_supports_document_input": False`：误把 PDF 当 `BinaryContent` 传进来时，Pydantic AI 会在本地直接抛 `UserError`（`models/openai.py` 第 2150–2152、2286–2294 行），不必花一次请求换一个 400。

## 8. 未能核实

- **真实照片的质量**：本卷只有 1 张合成图，测了 2 次。真实铭牌的反光、透视、压印或蚀刻字、污渍、弱光、德文标签、HEIC 原图都没测。#236 的完成标准本来就要求用真实铭牌照片和数据表 PDF 做评测，那一步不能省。
- **延迟分布**：只有 2 个非流式、非高峰的成功样本，高峰与并发下的表现未知。
- **图片 token 精确数**：usage 不单列图片 token，只有 §6.4 的估算。
- **`detail: low` 对小字的影响**、**`ImageUrl` 外链直传**（只有源码与文档，未实测）、**Anthropic 兼容端点与 Responses API 的图片输入**（Genie 不走这两条，未实测）。
- **服务端留存**：Files API 不设过期即永久保存，这是 S3 原文；内联图片在 DeepSeek 侧怎么留存，文档里没看到，本票也没有查隐私条款。
- **Files API 上传 PDF**：没有实测，S3 写明只收四种图片格式。

## 9. 裁定与建议实现路径

**裁定：(a)。** 业主说 deepseek-flash 能看图，官方 API 上属实（S1、S4、S7、L1、P1、P3）。"读文件"只对图片文件成立：PDF 等文档官方 API 不收（§4 的五条文档证据加 P2、P4 两次 400）。附件读取照样可以全部交给 deepseek-flash，前提是我们先把 PDF 转成文字或页面图片。无需换模型，也无需业主另行裁定模型；要本线定的是 PDF 转换放在哪一层（下文第 5 条）。

建议路径（供 #236 起规格）：

1. **请求形状**：沿用 Genie 现有的 Chat Completions 路径（`https://api.deepseek.com/v1`、`OpenAIChatModel` + `DeepSeekProvider`）。当轮 user prompt 改成 `[文字, BinaryContent(data, media_type)]`，Pydantic AI 2.55.0 自动产出 S1 的 `image_url` data URL 形状（§5、P3）。不用升级库，也不用 Files API：Files API 的文件默认永久保存（S3），而 `OpenAIChatModel` 本来就不支持图片 `file_id`（§5）。
2. **前端**：把文件字节发出去，不再只发文件名。图片先在浏览器里用 canvas 重编码成 JPEG 或 WebP，总像素压到约 1.69 MP（4:3 时约 1500×1125），这正是 API 自己的缩放目标（S1 "roughly that of a 1300×1300 image"）。这样能把 HEIC 等不支持的格式转掉，也让上传体积远小于 32 MiB 和 48 MiB 的上限。
3. **传输**：附件走请求里单独的字段，不混进 `messages`。`Proxy.php` 会把 `messages` 原样写进会话记录（§7），附件的保存与清理按 #236 的会话保留策略单独写进规格。
4. **铭牌识别**：
   - 先单独调用一次 deepseek-flash 做抽取，`response_format: json_object`，看不清的字段返回 null。P1 的提示词可以直接当起点。
   - 抽出的品牌、型号交给现有能力 `linker/search-products`（`brand`/`series`/`text` 字段，见 `agent.py` 的 `INPUT_DOCS`）映射到产品，再走 #236 记的"客户确认 → 产品卡或兼容性"。"置信度"建议用确定性匹配来定：型号在我们的产品数据里逐字命中就算高，部分命中就请客户确认，没命中就给手动输入的出口。模型的自评不作置信度。
   - 照片上的数字不能直接写进 Genie 的回答：`agent.py` 的 `_user_prompt` 要求 "No number in text in any form"，数字只能经 `{fact:…}` 由工具结果填入。要显示"照片上读到的额定值"，得由服务端把抽取结果登记成事实（比如新开一个命名空间），这一点在 #236 规格里定。
   - 抽取结果（JSON 或文字）进会话历史；后续轮次不要每轮重发原图（API 无状态，整段历史受 48 MiB 请求体上限约束，S1）。
5. **PDF 附件**（数据表、图纸）：
   - 有文字层的页：抽文字，按页标注后作为文字发送。数字直接取自文字层，不经过识别；数据表里的小字号表格也不受 1300×1300 缩放影响；成本按 S6 约 0.3 token/英文字符。
   - 没有可用文字层的页（扫描件、接线图、屋顶图）：把页面渲染成图片再发。A4 页按约 130 dpi 渲染约 1093×1546（约 1.69 MP，与 API 缩放目标相当，属推算），每页最多 1024 token，一次请求最多 600 张图（S1）。一套 20 页的图纸最多约 2 万 token，非高峰未命中约 $0.003（推算）。
   - 带文字的图纸（如单线图）可以文字层和页面图一起发。
   - 转换放在哪一层：
     - (i) **VPS 上用 PDFium**（`pypdfium2` 5.14.0 已在 `services/genie/uv.lock` 里，经 `docling` → `docling-slim` 进入 `index` 组）抽文字、渲染页面。不跑任何模型，单页开销小，和发起模型调用的代码在同一个服务里，可以用真实 PDF 夹具做 pytest。代价是要改 `docs/specs/10-knowledge-index.md` 第 39 行：那条"不在 VPS 上解析"是为知识索引（Docling、OCR、向量模型）写的，用于运行时附件需要写明适用范围和依据。
     - (ii) **浏览器里用 pdf.js** 抽文字层、渲染页面。服务端完全不解析，代价是 Genie 前端包多一个大依赖，手机上处理大 PDF 的性能未知。
     - 本卷倾向 (i)：附件预处理、模型调用和测试夹具都在一处。最终由本线定。
6. **防呆**：`build_model` 的 profile 加 `"openai_chat_supports_document_input": False`（§7），误传 PDF 时在本地报错。上游的 400 也要显式暴露给日志，不静默吞掉。
7. **预算参考**：单张铭牌约 2.2 s、约 $0.0003（非高峰）至 $0.0007（高峰），图片部分每张最多 1024 token（§3.3、§3.4）。真实照片与 EN/DE 数据表的评测集按 #236 的完成标准另建；本卷的合成图只证明链路通、形状对。
