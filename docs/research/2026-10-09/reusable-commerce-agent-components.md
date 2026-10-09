# 可复用的商务 Agent 组件：协议、数据接口、Agent 循环与 grounding（2026-10-09）

**问题：** 在 2026 年，哪些开源组件、协议和参考实现可以拿来改造（而不是从零自建），为 WordPress + WooCommerce B2B 站提供平台级 AI 导购？约束：WooCommerce 跑在 LiteSpeed 共享主机（PHP），另有一台 Ubuntu VPS 已运行 FastAPI 引擎；约 100 个商品，带结构化属性和关键数值；有兼容合同；回答中的每条事实都必须来自目录数据；需要按工程约束过滤、做比较、加入购物车、发起 Proforma、查询订单状态；EN+DE；不用付费插件，尽量避免 SaaS 锁定；LLM 供应商为 DeepSeek（OpenAI 兼容 tool calling）和 Anthropic。

**方法：** 所有外部读取都经过 Apify：网页和文档用 `apify/rag-web-browser`（REST `run-sync-get-dataset-items`）；GitHub 仓库元数据（stars、license、language、`pushed_at`、archived）用 Apify Actor `moving_beacon-owner1/github----repository-search-data-scraper` 读取，它在内部调用 GitHub REST API。全部数据取于 **2026-10-09**。表中“最后推送”取自 GitHub `pushed_at`（最近一次推送到任意分支），作为最后一次提交的近似值。本仓库的现状只引用代码路径，没有修改。

**分级：** 【事实】= 有来源原文；【推断】= 从事实和第一性原理推导出的判断，供决策参考，不是供应商的说法。

---

## 0. 结论速览

| 层 | 原样采用 | 改造采用 | 跳过 |
|---|---|---|---|
| 协议 | WordPress **Abilities API**（6.9 起进入 core）作为工具定义层 | **UCP Catalog + Cart path**（结账交给网站完成）的数据形状，作为以后对外开放的方向；Automattic `woocommerce-ai-storefront` 的 discovery 思路（llms.txt、`/.well-known/ucp`、JSON-LD `BuyAction`） | ACP / Stripe ACS / Google 原生结账（都要求在线支付）；Shopify 的 MCP（只服务 Shopify 商家） |
| Woo 数据 | **Store API**（`wc/store/v1`，公开读取，用 `Cart-Token` 或 nonce 写购物车）；现有 B2B Core 权威函数 | Woo 核心 MCP（`mcp_integration` flag，**仅限管理端**），只用于内部运维 | 社区 WooCommerce MCP server（stars ≤104、基本不维护、多为管理端 REST 套壳） |
| Agent 循环 | **Pydantic AI**（MIT；`deepseek:` 与 Anthropic 都原生支持；typed tools 加 `output_validator`/`ModelRetry`） | Anthropic SDK `tool_runner`（beta），只作为 Claude 专用路径；WP 7.0 AI Client 的 `using_function_declarations()`（PHP 端的备选） | Dify（修改版 Apache 许可）、Flowise（2026-08-13 已归档）、Rasa CALM（免费版每月 1,000 次会话）、LangGraph 和 OpenAI Agents SDK（对 6–10 个工具来说太重） |
| Grounding | 原生的 **strict tool schema**（Anthropic `strict: true`；DeepSeek `strict` beta）；**Anthropic `search_result` 引用块** | **Instructor/Pydantic 的 validation context**：做 ID 引用加数值核验，代替正则 | Guardrails `ProvenanceLLM`、NeMo `self check facts`（用 LLM 判 LLM，不确定）；Outlines（需要访问 logits，托管 API 不可用） |
| 参考实现 | — | NVIDIA `Retail-Agentic-Commerce`（ACP+UCP 参考，Apache-2.0）的接口切分；`dukandar` 的“产品卡 + 购物车动作”呈现模式 | NVIDIA `retail-shopping-assistant`（需要 4×H100，许可为 NOASSERTION）；各种 “shopping assistant” 演示仓库 |

---

## 1. Agentic-commerce 协议与 WooCommerce 现状

### 1.1 WooCommerce / Automattic 官方立场

- 【事实】woocommerce.com 的 “WooCommerce protocol status” 表：**MCP = Live**（“Shipped in WordPress 6.9 and WooCommerce 10.3 with 9 built-in abilities”），**Abilities API = Live**（“Built into WordPress core”），**UCP (Google) = Coming soon**，**ACP (Stripe) = Coming soon**。ACP 将通过 “Stripe for WooCommerce” 扩展加 Stripe Agentic Commerce Suite 提供。— https://woocommerce.com/agentic-commerce/（取于 2026-10-09）
- 【事实】WooCommerce 开发者博客 2025-10-03：10.3 引入第一版 WooCommerce MCP，覆盖产品和订单管理；目标是“when paired with our existing REST and Store APIs … potentially powering consumer shopping and checkout”；在试验 OpenAI Product Feed Spec。— https://developer.woocommerce.com/2025/10/03/ai-agentic-commerce-in-woocommerce/
- 【事实】WooCommerce MCP 文档：仍为 **Developer Preview**；由 `mcp_integration` feature flag 开启；能力为产品查询/增/改/删，订单查询/改状态/加备注；新集成使用 `https://yourstore.com/wp-json/mcp/mcp-adapter-default-server`，旧的 `/wp-json/woocommerce/mcp` 已 deprecated；以 WordPress 用户加 Application Password 认证，默认要求 `read` capability，且每个 ability 有自己的 permission callback；文档明确提醒订单操作会暴露 PII。— https://developer.woocommerce.com/docs/features/mcp/
- 【事实】UCP 原生支持的功能请求（2026-01-13 提交，34 票）状态仍为 **Open**。— https://woocommerce.com/feature-request/native-support-for-googles-universal-commerce-protocol-ucp-for-ai-agents/
- 【事实】Automattic `woocommerce-ai-storefront`（GPL-3.0，PHP，3★，最后推送 2026-10-05，About 写明 “PRE-RELEASE EXPERIMENTAL NOT FOR PRODUCTION”）。核心原则是 “AI agents discover and recommend. The merchant owns the transaction.” 它发布 `/llms.txt`、`/.well-known/ucp`（checkout policy 为 **web-redirect only**）、带 `BuyAction` 的增强 Product JSON-LD，并接入 Store API 限流和 Order Attribution（`utm_medium=ai_agent`）；“No delegated payments”。它还说明 **core MCP 面向管理端**，**UCP 面向外部购物 agent**。— https://github.com/Automattic/woocommerce-ai-storefront

【推断】Woo 官方目前没有给店内导购用的 shopper-side 协议实现。可用的官方基础只有 Abilities API 加 MCP adapter（管理端）和 Store API。Automattic 自己的试验方向是“agent 只负责发现，交易回到站点完成”，这和我们“没有在线支付、走 Proforma”的模式一致。

### 1.2 OpenAI ACP

- 【事实】规范仓库 `agentic-commerce-protocol/agentic-commerce-protocol`：Apache-2.0，1,568★，最后推送 2026-07-18，由 OpenAI 和 Stripe 维护，状态为 `beta`。版本：2025-09-29、2025-12-12、2026-01-16、2026-01-30、**2026-04-17（Cart, feed, orders, authentication, and MCP）**。— https://github.com/agentic-commerce-protocol/agentic-commerce-protocol
- 【事实】2026-04-17 changelog 新增 Cart capability（`POST/GET/PUT /carts`）；Feed API 是 **push 模型**，由 agent 托管、商家把目录推送过去；discovery 中的 `transports` 声明 `rest`/`mcp`。— https://github.com/agentic-commerce-protocol/agentic-commerce-protocol/blob/main/changelog/2026-04-17.md
- 【事实】CNBC 2026-03-24 报道：OpenAI “pivoted away from Instant Checkout”，改为强调在 ChatGPT 内发现和比较商品。— https://www.cnbc.com/2026/03/24/openai-revamps-shopping-experience-in-chatgpt-after-instant-checkout.html
- 【事实】OpenAI 开发者文档现在把 ACP 描述为让 “ChatGPT to ingest structured catalog data … and surface relevant products”。— https://developers.openai.com/commerce
- 【事实】第三方插件 “UCP/ACP Agent for WooCommerce” 0.1.0：<10 次安装，“3 weeks ago” 更新，PHP 8.1+；写明 ACP 结账 “currently limited to OpenAI-approved merchants”，支付走 Stripe Shared Payment Token。— https://wordpress.org/plugins/ucp-acp-agent-for-woocommerce/

【推断】ACP 的结账部分要求代付（delegated payment）。我们没有在线支付，所以用不上。ACP 中唯一可能有价值的是 Product Feed（把目录推给 ChatGPT 用于发现）。这属于外部渠道和营销决策，与店内导购无关。

### 1.3 Google / Shopify UCP

- 【事实】规范仓库 `Universal-Commerce-Protocol/ucp`：Apache-2.0，3,408★，最后推送 2026-10-08。capability 包括 Checkout、Identity Linking、Order、Payment Token Exchange；传输层可选 **REST、MCP 或 A2A**。官方还有 `python-sdk`（89★，Apache-2.0，2026-10-08）和 `samples`（240★，2026-10-05）。— https://github.com/Universal-Commerce-Protocol/ucp
- 【事实】UCP **Catalog capability**：`dev.ucp.shopping.catalog.search`、`dev.ucp.shopping.catalog.lookup`，支持自由文本搜索、过滤浏览、按 ID 批量取变体和价格比较。— http://ucp.dev/draft/specification/shopping/catalog/（draft 路径）。latest overview 写着 “Cart, Checkout, and Catalog adopt this shape”，示例 profile 的版本为 `2026-08-25`。overview 还规定 business 应为 catalog 操作提供 `continue_url`，指向商品页或搜索结果页，以便 “graceful degradation”。— https://ucp.dev/latest/specification/overview/
- 【事实】Google 侧的落地分 **Native checkout**（需要 Google Pay handler 和订单生命周期）和 **Cart path**（“receive shopping carts and hand off to your website”）两条路径；前提是 Merchant Center，并须加入 waitlist 获得 Google 批准。页面更新于 2026-10-05 UTC。— https://developers.google.com/merchant/ucp/guides/overview
- 【事实】Shopify：旧的 Storefront MCP（`https://{shop}/api/mcp`）中 catalog 和 cart 工具已 **Removed**，改为 UCP，路径为 `https://{shop}/api/ucp/mcp`（Storefront Catalog MCP：`search_catalog`、`lookup_catalog`、`get_product`；Cart MCP：`create_cart`、`get_cart`、`update_cart`、`cancel_cart`；Checkout MCP）；`search_shop_policies_and_faqs` 保持不变。— https://shopify.dev/docs/apps/build/storefront-mcp、https://shopify.dev/docs/agents
- 【事实】WordPress.org 上已有 UCP 插件（30+ 安装，“7 months ago” 更新）。— https://wordpress.org/plugins/universal-commerce-protocol-ucp-for-woocommerce/。GitHub 上的 WooCommerce UCP 实现都很小，例如 `Redemptive-Software/woocommerce-ucp`（Apache-2.0，4★，2026-01-24）和 `boxybird/ucp-checkout-for-woocommerce`（2★，2026-01-19）。

【推断】UCP 是唯一把“目录搜索 → 购物车 → 交回网站完成”定义为一等路径的开放协议。它的 Catalog 和 Cart 形状（product/variant/price、`continue_url`）可以直接当作我们内部工具的输出 schema 参考。这样以后对外开放时，同一组 ability 可以由一个 UCP 适配层发布，不必重新设计。今天就实现完整的 UCP 服务端（签名、profile、协商）没有消费者：Google 需要审批，Woo 官方尚未发布。

### 1.4 Stripe Agentic Commerce

- 【事实】Stripe 的 Sellers 集成使用 UCP 或 ACP；Agents 侧为 “Private preview”。— https://docs.stripe.com/agentic-commerce。Agentic Commerce Suite 标为 “Frontier”，“available in the US, Canada, and select European countries”，并用 Shared Payment Tokens。— https://docs.stripe.com/agentic-commerce/sellers/use-cases/retail

【推断】ACS 本质是支付和目录同步渠道，与“无在线支付”的约束直接冲突，因此跳过。

### 1.5 WebMCP

- 【事实】2026-02-10 Chrome 团队发布 WebMCP 早期预览：网页通过 `navigator.modelContext` 向浏览器内的 agent 暴露可调用工具；规范处于 W3C Community Group draft 阶段。— https://w3c-cg.github.io/aikr/webMCP/webmcp-technical-notes.html

【推断】可以留意，但现在不投入：规范和浏览器支持都在早期。

---

## 2. Agent 访问 WooCommerce 数据的方式

| 通道 | 认证 | 适合导购的哪一步 | 证据 |
|---|---|---|---|
| **Store API** `wc/store/v1` | 读取不需认证；写入需要 nonce，或在 headless 场景下用 `Cart-Token` 头代替 cookie 和 nonce | 商品读取、加购物车、读购物车 | “the Store API is unauthenticated and does not provide access to sensitive store data”；写入 “require a nonce-token” — https://developer.woocommerce.com/docs/apis/store-api/。`Cart-Token`：GET `/cart` 的响应头会返回它，带上即可替代 nonce，也可用于 `/checkout` — https://developer.woocommerce.com/docs/apis/store-api/cart-tokens/。限流功能可选且默认关闭，通过 `woocommerce_store_api_rate_limit_options` 开启 — https://developer.woocommerce.com/docs/apis/store-api/rate-limiting/ |
| **REST v3** `wc/v3` | API key 或 Application Password | 服务端读取订单状态（须按客户限定范围） | Store API 文档自己指出，需要更广访问时用已认证的 WC REST API（同上） |
| **Woo core MCP**（Abilities + `mcp-adapter`） | WP 用户 + Application Password | **只用于管理端或内部**（产品维护、订单运维） | 见 §1.1；`WordPress/mcp-adapter`：GPL-2.0，1,813★，PHP，最后推送 2026-10-08，支持 HTTP 和 STDIO transport，abilities 会自动转换为 MCP tools、resources 和 prompts — https://github.com/WordPress/mcp-adapter |
| **Abilities API** | 每个 ability 自带 `permission_callback` | **工具定义的单一来源**（输入/输出 JSON schema 加执行回调） | 独立仓库 `WordPress/abilities-api` 已于 2026-02-05 归档（215★），因为已并入 core 6.9（woocommerce.com 表述为 “Built into WordPress core”） |

**社区 WooCommerce MCP server（GitHub 搜索 “woocommerce mcp” 按 stars 排序）：**

| 仓库 | ★ | 许可 | 语言 | 最后推送 | 性质 |
|---|---|---|---|---|---|
| techspawn/woocommerce-mcp-server | 104 | MIT | JS | 2025-11-10 | REST v3 管理端套壳，近 11 个月无推送 |
| iOSDevSK/mcp-for-woocommerce | 15 | GPL-2.0 | PHP | 2026-10-07 | **只读、公开**的店面数据，基于已弃用的 Automattic `wordpress-mcp`；端点 `/wp-json/wp/v2/wpmcp/streamable` 无需凭据 — https://github.com/iOSDevSK/mcp-for-woocommerce |
| wppoland/woocommerce-mcp | 2 | MIT | TS | 2026-09-29 | 只读 |
| AmitGurbani/mcp-server-woocommerce | 2 | MIT | TS | 2026-05-05 | 管理端 |
| opestro / Vostos007 / osdeibi / anthonhassel | 2–4 | 各异 | — | 2025 | 停滞 |
| woocommerce/wc-mcp-ability | 6 | — | PHP | 2025-09-22 | 官方 demo，已被 core 取代 |
| Automattic/wordpress-mcp | 945 | — | PHP | 2026-09-17 | **已归档**，“will be deprecated as stable releases of mcp-adapter become available” |

**WordPress “AI Building Blocks”：**

- 【事实】WordPress 7.0 core 自带 AI Client（`wp_ai_client_prompt()` 流式 builder，`as_json_response($schema)`）。供应商由站点管理员在 **Settings > Connectors** 配置；插件通过 `using_model_preference()` 声明偏好。— https://make.wordpress.org/core/2026/03/24/introducing-the-ai-client-in-wordpress-7-0/（2026-03-24）
- 【事实】底层的 `WordPress/php-ai-client`：GPL-2.0，310★，最后推送 2026-09-30。function calling 由 `FunctionDeclaration`、`FunctionCall`、`FunctionResponse` DTO 和 `using_function_declarations()` 提供，可以把 abilities 直接转换成工具。— https://j.cv/using-abilities-to-build-ai-in-wordpress/。“Allow providers to prepare function declarations before tool-calling requests” 仍是开放 issue（2026-06-22 提出）。— https://github.com/WordPress/php-ai-client/issues/256。`WordPress/wp-ai-client` 已归档（126★，2026-03-01，已合入 core）。`WordPress/ai`（360★，2026-10-08）是实验性质的功能插件。

【推断】对我们最有用的是 **Abilities API 当作工具注册表**。把现有 B2B Core 权威函数（例如 `tv_b2b_product_commerce_state()`、兼容合同读取）包装为 ability 后，ability 的 schema 和 permission 可以同时用于三处：(a) VPS 上 Agent 循环通过一个 REST 端点调用；(b) `mcp-adapter` 给内部运维用；(c) 将来的 UCP 适配层。这样符合 Law 4（一条规则一个实现），不需要新增第二套事实推导。购物车应当属于用户自己的浏览器会话。【推断】让 agent 返回 “add_to_cart” 动作，由前端用用户本人的 Store API 会话执行，比在服务器上持有 `Cart-Token` 更简单，也避免把购物车与身份分离。

---

## 3. 适合 FastAPI 小服务的 Agent 循环

评估标准：6–10 个结构化工具、严格 grounding、EN/DE、同时支持 DeepSeek（OpenAI 兼容）和 Anthropic，而不是通用聊天。

| 框架 | 许可 / ★ / 最后推送 | 两家模型的支持 | Grounding 钩子 | 判断 |
|---|---|---|---|---|
| **Pydantic AI** | MIT / 20,495 / 2026-10-09 | 内置 `deepseek:` 前缀和 Anthropic — https://ai.pydantic.dev/models/overview/ | `@agent.output_validator` 可以抛出 `ModelRetry`，让模型带着错误重试（输出重试预算默认 1，可配置）；支持 `ToolOutput`/`NativeOutput` 结构化输出 — https://ai.pydantic.dev/output/ | **首选**：Python，可直接嵌入现有 FastAPI；typed tools；验证器可以拿到 `RunContext`（含工具结果） |
| Anthropic SDK `tool_runner` | MIT / 3,952 / 2026-10-08 | Anthropic；【事实】DeepSeek 另外提供 Anthropic 格式端点 `https://api.deepseek.com/anthropic` — https://api-docs.deepseek.com/ | `@beta_tool` 自动处理循环、错误包装和类型 — https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner | 还是 beta；适合 Claude 专用路径或作参考。【推断】DeepSeek 的 Anthropic 端点是否支持 `search_result` 引用块尚未验证 |
| OpenAI Agents SDK | MIT / 29,923 / 2026-10-08 | 通过 `set_default_openai_client` 接任意 OpenAI 兼容端点；Anthropic 需 LiteLLM 或 Any-LLM 适配层，文档称这些适配层 “add another compatibility layer” — https://openai.github.io/openai-agents-python/models/ | guardrails、handoffs | 多 agent 编排对我们来说多余；接 Anthropic 要多一层适配 |
| LangGraph | MIT / 42,919 / 2026-10-08 | 通过 LangChain 集成 | “low-level orchestration framework … durable execution, streaming, human-in-the-loop” — https://docs.langchain.com/oss/python/langgraph/overview | 适合长时间、有状态的流程；单轮导购用不上，依赖面大 |
| Vercel AI SDK | GitHub API 许可为 NOASSERTION / 27,190 / 2026-10-09 | 有 DeepSeek provider，支持 `strict` 工具（beta 基址）— https://ai-sdk.dev/providers/ai-sdk-providers/deepseek；tools 支持 `inputSchema`、`strict`、`stopWhen` — https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling | — | 质量好，但是 TypeScript，VPS 上要新增一个 Node 服务；只在前端走 Next.js 时才合适 |
| Dify | 修改版 Apache 2.0 / 157,946 / 2026-10-09 | 多供应商 | 可视化工作流 | 许可禁止未经授权运营 multi-tenant 服务，且不得移除前端 LOGO — https://github.com/langgenius/dify/blob/main/LICENSE；平台很重 → **跳过** |
| Flowise | 55,495 / **2026-08-13 已归档** | — | — | 仓库已只读 — https://github.com/FlowiseAI/Flowise → **跳过** |
| Rasa (CALM) | 仓库 Apache-2.0 / 21,345 / 2026-07-24 | — | CALM 用 LLM 理解语言、用确定性 flow 执行业务逻辑 | 免费的 Developer Edition 限 “1,000 conversation per month” — https://rasa.com/rasa-pro-developer-edition-license-key-request；CALM 在 Pro/Developer Edition 中，不在开源版 → **跳过** |
| WP 7.0 AI Client（PHP） | GPL-2.0（core） | 取决于管理员在 Connectors 中配置的供应商 | `as_json_response`、`using_function_declarations` | 想把循环留在共享主机上时的备选。但工具调用的扩展点仍有开放 issue（#256），共享主机上的长时间流式请求也受限 |

【推断】选型理由：工具只有 6–10 个，任务路径大致固定，真正难的是 grounding，而不是编排。所以需要的是“一个 typed 工具循环 + 一个确定性的输出验证器”，不是多 agent 图或可视化平台。Pydantic AI 能同时接 DeepSeek 和 Anthropic，验证器又能拿到工具结果，覆盖最多需求，引入的东西也最少。

---

## 4. 值得借鉴模式的开源导购实现

| 仓库 | 许可 / ★ / 最后推送 | 可借鉴 | 应避免 |
|---|---|---|---|
| NVIDIA-AI-Blueprints/**Retail-Agentic-Commerce** | Apache-2.0 / 79 / 2026-09-29 | ACP 与 UCP 参考实现（`/.well-known/ucp`、`/checkout_sessions/*`、A2A）；Merchant API 与 search/recommendation agents 分开；Apps SDK MCP server 加 widget — https://github.com/NVIDIA-AI-Blueprints/Retail-Agentic-Commerce | 依赖 NIM/Milvus；包含代付 PSP，我们用不上 |
| NVIDIA-AI-Blueprints/retail-shopping-assistant | NOASSERTION / 100 / 2026-10-09 | LangGraph 编排，catalog retriever、memory/cart、guardrails 分为不同服务 | 本地运行需要 “4x H100 GPUs (preferred) or 4x A100”，“no built-in end-user authentication” — https://github.com/NVIDIA-AI-Blueprints/retail-shopping-assistant |
| fahdi/dukandar-shopping-assistant-for-woocommerce | 无许可声明 / 6 / 2026-10-05 | WooCommerce 内：产品卡（图、价、库存、View/Add to cart 按钮）；通过对话完成加购、查看、删除；不存在的折扣会拒绝编造 — https://github.com/fahdi/dukandar-shopping-assistant-for-woocommerce | 没有许可证，**不能复制代码**，只能借鉴模式 |
| AmirIqbalKhan/wc-ai-shopping-assistant | GPL-2.0 / 3 / 2026-07-26 | “grounded catalog recommendations”，多供应商 | 体量很小，未经验证 |
| vulpy-io/vulpy-commerce-core（Medusa v2） | Apache-2.0 / 114 / 2026-09-16 | 在 Medusa 上内置运营 assistant | 技术栈不同，偏管理端 |
| financedistrict-platform/medusa-plugin-agentic-commerce | MIT / 7 / 2026-10-06 | 一个插件同时提供 UCP 和 ACP 端点 | 加密货币支付，与我们无关 |
| Shopify/ucp-cli | MIT / 79 / 2026-09-29 | UCP 客户端技能：catalog → cart → checkout handoff → order | 只适用于 Shopify 生态 |
| lucasboscatti/sales-ai-agent-langgraph | MIT / 102 / 2024-12-27 | LangGraph 销售 agent 示例 | 已停更近两年 |
| Meow Apps **AI Engine**（wordpress.org） | 90,000+ 安装 / 3.8.4 / “22 hours ago” 更新 | 自带 function calling 框架、MCP、Abilities 接入 — https://wordpress.org/plugins/ai-engine/ | changelog 说明部分 functions “stay Pro”（付费）；接入后对外部插件形成锁定。GitHub `jordymeow/ai-engine` 仓库无许可声明（48★） |
| alibaba/EasyRec | Apache-2.0 / 2,361 / 2026-04-15 | 大规模推荐算法框架 | 约 100 个 SKU 用不上召回或排序模型 → **跳过** |
| QwenLM/Qwen-Agent | Apache-2.0 / 17,151 / 2026-03-04 | function calling、MCP、RAG | 围绕 Qwen 设计；与 Pydantic AI 功能重叠 |

GitHub 搜索 “shopping assistant llm” 和 “ecommerce agent tool calling” 的前 30 条结果，除上表外 stars 均低于 15，基本是课程或黑客松演示，不适合复用。

【推断】可以复用的是**模式**，不是代码：(1) 搜索、推荐与交易分开（NVIDIA RAC）；(2) agent 返回结构化的商品卡和购物车动作，由前端渲染和执行（dukandar）；(3) “agent 负责发现，交易回到站点完成”（Automattic AI Storefront 和 UCP Cart path）。这三点与我们现有 `linker-ai-assistant` 的 evidence → compose → validate 链路兼容。

---

## 5. 可替代手写正则验证器的 grounding / 验证模式

现状（本仓库）：`plugins/linker-ai-assistant/includes/class-linker-ai-answer-validator.php` 共 11,446 行，含 310 处 `preg_match`；它检查任务覆盖、来源 ID、型号和数字，以及特定 claim 主题，并在若干场景用服务端 `composition()` 重写正文（参见 `docs/research/2026-09-22-advisor-answer-pipeline.md` 的“实际生产调用链”）。

| 模式 | 具体库 / API | 确定性 | 用途 |
|---|---|---|---|
| **Strict tool schema** | Anthropic `strict: true`（“Guarantee schema validation on tool names and inputs”）和 `output_config.format` JSON outputs — https://platform.claude.com/docs/en/build-with-claude/structured-outputs；DeepSeek `strict` 模式（Beta，基址 `https://api.deepseek.com/beta`，所有 function 都要设 `strict: true`，服务端校验 schema）— https://api-docs.deepseek.com/guides/tool_calls/ | 是（解码约束） | 保证工具参数（过滤条件，如 Application、Phase、数值范围）和最终答案 JSON 合法，替代格式类正则 |
| **Citation-by-ID** | Anthropic `search_result` 内容块：工具结果可以直接返回 `{type:"search_result", source, title, content, citations:{enabled:true}}`，Claude 会自动生成引用；`source` 可以是任意稳定标识（如 `kb://…`），除 Claude Haiku 3 外所有 active 模型都支持，无需 beta header — https://platform.claude.com/docs/en/build-with-claude/search-results | 引用由 API 生成，指向具体块 | Claude 路径上，让每句话都带来源块 |
| **答案中的数值必须出现在工具结果中** | Pydantic `field_validator` 加 **validation context**：Instructor 的 `context` 参数会把源数据传给验证器，失败时用 `max_retries` 让模型重答 — https://python.useinstructor.com/concepts/reask_validation/；或使用 Pydantic AI 的 `output_validator` 加 `ModelRetry` | 是（代码比对） | 答案 schema 写成 `claims[{text, fact_ids[], numbers[{value, unit, fact_id}]}]`；验证器检查每个 `fact_id` 都在本轮工具结果中，且 `value`/`unit` 与该 fact 相等；未通过就重试，仍失败则回退到权威模板 |
| **数字不让模型写** | 不需要库：模型只输出 `{{fact:ID}}` 占位符，由服务端从目录数据填入数值和单位 | 是 | 【推断】这一步消除了数字幻觉。它是现有 `composition()` 覆盖逻辑的通用版本 |
| LLM 判定 provenance | Guardrails Hub `ProvenanceLLM`（MIT，用 LLM 判断输出块是否得到 k 个最近源块支持）— https://guardrailsai.com/hub/validator/guardrails/provenance_llm；仓库 `guardrails-ai/guardrails`：Apache-2.0，7,498★，2026-10-09 | 否 | 只能作为语义层的补充审读，不能代替数值核验 |
| LLM 自查事实 | NeMo Guardrails `self check facts` 输出 rail（基于 `$relevant_chunks`；文档称其效果 “strongly dependent on the capability of the LLM”）— https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/fact-checking；`NVIDIA/NeMo-Guardrails`：Apache-2.0 | 否 | 同上，而且引入 Colang 配置体系 → 跳过 |
| 受约束解码 | `dottxt-ai/outlines`（Apache-2.0，15,910★，2026-09-21） | 是 | 【推断】需要本地模型或 logits 访问；托管的 DeepSeek 和 Anthropic API 已有原生 strict 模式，因此跳过 |
| Instructor | `567-labs/instructor`：MIT，13,988★，2026-10-08 | — | 如果不用 Pydantic AI，它是最轻的“schema + context 验证 + reask”方案 |

【推断】替代正则的组合：(1) strict 工具参数加 strict 答案 schema，解决格式问题；(2) claim 必须带 `fact_ids`，验证器做 **集合包含** 和 **数值相等** 比对，解决出处和数值问题；(3) 数值由服务端按 ID 填入，模型写不出错数；(4) 只有未通过的部分走 `ModelRetry` 重试一次，再失败就回退到权威模板。这样大部分正则（数字、型号、来源）都变成一个由 schema 驱动的通用比对函数。剩下真正需要语言判断的部分，如“比较是否回答了问题”和“DE 措辞”，可以选用 LLM 审读，但不作为硬门禁。

---

## 6. 对本站的组合建议（【推断】）

1. **工具层（PHP，共享主机）：** 把现有权威读取函数包装为 WordPress abilities，例如 `linker/catalog-search`（过滤 Application/Phase/数值范围）、`linker/product-facts`（返回 keyed figures，每条带 `fact_id`）、`linker/compatibility-check`（读取兼容合同）、`linker/compare`、`linker/proforma-start`、`linker/order-status`（限定当前客户）。输出形状参考 UCP Catalog（product/variant/price/`continue_url`）。权限沿用 B2B Core 的上下文。
2. **购物车：** 前端用用户自己的 Store API 会话执行 agent 返回的 `add_to_cart` 动作，不在服务端代持购物车。
3. **循环（VPS，FastAPI）：** 使用 Pydantic AI，配置 `deepseek:` 主模型和 Anthropic 备用；工具即上述 abilities 的 REST 端点；答案 schema 加 `output_validator` 实现 §5 的确定性核验；Claude 路径额外使用 `search_result` 引用块。
4. **对外协议：** 暂不实现。如果以后决定让 Gemini 或 ChatGPT 发现目录，先借鉴 Automattic AI Storefront 的 llms.txt、`/.well-known/ucp`（web-redirect）和 JSON-LD 做法，并复用同一组 abilities。ACP、Stripe 和 Google 原生结账都需要在线支付，与当前范围冲突。
5. **内部运维：** 开启 Woo core `mcp_integration` 和 `mcp-adapter`（Application Password 加最小权限用户），只给内部 AI 工具用，不对购物者开放。

## 7. 未验证 / 局限

- Vercel AI SDK、Medusa、Meilisearch 的 GitHub API 许可字段为 NOASSERTION，本次未读取它们的 LICENSE 文件。
- 未验证 DeepSeek 的 Anthropic 兼容端点是否支持 `search_result` 引用块和 `strict` 工具。
- 未在本站环境实测 WooCommerce MCP、Store API `Cart-Token` 与 LiteSpeed 缓存、`mcp-adapter` 在共享主机上的表现。
- WordPress.org 插件的“更新于 N weeks ago”是相对时间，以取数日 2026-10-09 为基准。
