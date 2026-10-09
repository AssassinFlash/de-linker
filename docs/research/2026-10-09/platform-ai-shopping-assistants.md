# 平台级 AI 购物助手 2026：实际做什么，de-linker 该复刻哪些

日期：2026-10-09。研究票：`.scratch/advisor-rebuild/issues/002-research-platform-assistants.md`（父图 001）。

方法：外部检索与页面读取全部经 Apify（`apify/rag-web-browser`，REST `run-sync-get-dataset-items`，Google 检索 + 浏览器抓取）。优先一手来源（aboutamazon.com、amazon.science、AWS 博客、shopify.dev / help.shopify.com、about.fb.com、corporate.zalando.com、meituan.com、PR Newswire / Alizila 官方稿）；国内产品一手稿缺失处用新华网、人民网、科技日报等官媒，以及钛媒体、智东西、人人都是产品经理的上手实测，并标为二手。百度百科只用于时间线索，关键节点另有原文佐证。每条事实带 URL 和日期；"推断"一律标明。

## 结论先行

1. **"Rufus 于 2026-05 更名为 Alexa for Shopping"属实。** Amazon 自己的 Rufus 页面写明 "On May 13, 2026, Rufus was renamed Alexa for Shopping"（[aboutamazon, Rufus 页面](https://www.aboutamazon.com/news/retail/amazon-rufus-ai-assistant-personalized-shopping-features)）；CNBC 同日报道独立的 Rufus 聊天机器人停用（[CNBC 2026-05-13](https://www.cnbc.com/2026/05/13/amazon-ditches-rufus-ai-chatbot-in-favor-of-alexa-shopping-agent.html)）。发布稿只说面向美国客户；其他站点（含 amazon.de）是否同步改名，本次未核实。
2. **淘宝现在的名字是"千问AI购物助手"**（2026-05-11 千问 × 淘宝全面打通）。入口在淘宝 App 底部"消息"栏；千问 App 内也能直接逛淘宝、下单。"淘宝问问"（2023）是前身，"AI万能搜"（2025-08 灰度）是搜索框里的形态（[新华网 2026-05-11](http://www.xinhuanet.com/tech/20260511/b94c26581d9c41ea8c3fd3b383ab2939/c.html)）。
3. **美团小团 2026-02 确有升级**：2026-02-12 春节前升级"问小团"AI 管家（[科技日报 2026-02-12](https://www.stdaily.com/web/gdxw/2026-02/12/content_473734.html)）。2026-07-27 又发布小团 2.0，从"能答"变为"能办"（[美团新闻 2026-07-27](https://www.meituan.com/news/NN260727198008607)）。
4. **各家共有的骨架只有三条**：(a) 答案锚定平台自己的结构化目录和实时状态，不靠模型记忆；(b) 嵌入旅程中已有的入口（搜索框、商品页、消息/聊天、订单），而不是另开一个孤立页面；(c) 模型通过工具调用平台既有动作（检索、比较、加购、查单），涉及钱或不可逆的动作必须由用户确认。其余功能（画像、降价提醒、领券、试穿、定时任务）都建立在海量 SKU、海量用户、在线支付之上，de-linker 不具备这些前提。
5. **离 de-linker 最近的 B2B 同类是 Accio**。它的流程终点不是付款，而是向供应商发出询盘/RFQ：任务 → 合格供应商清单 → 用户追加约束收窄 → 对比 → 用户填数量 → 代拟询盘。这和 de-linker 的"工程条件 → 合格候选 → 对比 → 加入篮子 → Proforma 请求"几乎同构。
6. **在聊天里直接结账，行业正在后撤。** OpenAI 在 2026 年初结束了 ChatGPT 的 Instant Checkout，改为与零售商合作做应用内购物（[CNBC 2026-05-13 转述](https://www.cnbc.com/2026/05/13/amazon-ditches-rufus-ai-chatbot-in-favor-of-alexa-shopping-agent.html)）。de-linker 没有在线支付，终点停在 Proforma 请求，与这个方向一致，不算缺陷。

## 1. 逐个助手

### 1.1 淘宝：千问AI购物助手 ／ AI万能搜 ／ 淘宝问问

**名称与形态（时间线）**
- 2023-09 起内测"淘宝问问"，号称电商行业首个生成式 AI 应用。2023-10 增加"用我挑商品"：从足迹、购物车、收藏中选多件商品做对比，生成异同、优势和选购建议；还能总结商品详情与用户反馈（[电商派 2023-10-12](https://www.pai.com.cn/229728.html)）。
- 2025-08 灰度上线"AI万能搜"，入口在搜索栏顶部，标注"一问即答"。一句自然语言生成图文"答案页"：按场景或风格分组，每组附推荐商品、理由、同类预览和价格，结尾给综合建议；可开"深度思考"模式；有"购物偏好"开关；末尾"你还可以问"引导追问（[智东西 2025-08-18](https://zhidx.com/p/497878.html)；[人人都是产品经理 2026-04-07 上手拆解](https://www.woshipm.com/ai/6371687.html)）。
- 2026-05-11 千问与淘宝全面打通。淘宝 App 底部"消息"栏出现"千问AI购物助手"；千问 App 内可完成挑选、对比、下单、履约查询和售后（[新华网 2026-05-11](http://www.xinhuanet.com/tech/20260511/b94c26581d9c41ea8c3fd3b383ab2939/c.html)；[人民网 2026-05-11](http://finance.people.com.cn/n1/2026/0511/c1004-40717594.html)）。

**动作**：AI 问答推荐、参数对比、亮点总结；一句话下单、一句话帮抢、一句话退换货；AI 试穿；发图片、视频或种草链接找同款；AI 省钱（一键生成领券和凑单方案）（新华网同上）。千问内还能查订单物流（[钛媒体 2026-05-12 上手](https://www.tmtpost.com/7984130.html)）。

**锚定**：淘宝 40 亿商品库加上 20 多年真实购物场景数据（新华网）。

**追问与纠偏（官方示例）**
- 多条件一次满足：例如"越野跑鞋＋大 V 底＋GTX 防水＋颜色鲜艳＋BOA 鞋带"，6 个条件同时筛选。
- 参数与真实需求冲突时主动纠偏：例如"小户型想要大匹数空调"，它会指出"性能过剩"并建议降低规格。
- 模糊意图推理："封面是阿德里亚诺的足球游戏"被推出是《实况足球6》。
- 场景组合：例如"孕晚期"直接给出一组商品（新华网）。
- 多轮问清预算和偏好之后再推荐，实测者形容为"AI 导购逻辑"（钛媒体）。

**架构**：官方没有公开。woshipm 作者推测其流程为"自然语言 → 结构化需求标签 → 映射到商品知识库属性 → 结合偏好重排 → 按分组＋解释＋延伸问题组织页面"，这是**推断**，不是官方说明。

### 1.2 美团：小团（问小团 → 小团 2.0）

- 2026-01：美团主 App 上线"问小团"AI 搜索入口（[百度百科·小团](https://baike.baidu.com/item/%E5%B0%8F%E5%9B%A2/67939476) 时间线，下一条有原文印证）。
- **2026-02-12 升级**：用户提出本地吃喝玩乐问题后，问小团会深度思考，搜集平台商户与服务信息并做**二次校验**，再结合真实用户评价给出选择；春节专区可领券，并获得智能推荐的最优惠下单方案。底层是自研 LongCat，同时按任务综合调用多个主流大模型（[科技日报 2026-02-12](https://www.stdaily.com/web/gdxw/2026-02/12/content_473734.html)）。
- 2026-04：入口迁到 App 首页核心位置，即底部导航（百科时间线）。
- **2026-07-27 小团 2.0**："帮我找找"变成"帮我办了"，在用户授权和确认下完成下单、打车、订位。筛选时综合距离、营业状态、用户评价和实时余位，用户确认后再协助预订。对没有接入线上预订的小店，用"AI 外呼"模拟人工电话确认。美团内部把管家能力分为五层：结果准确性、决策辅助、行动代理、情境判断、附加信息提示。数据规模：信息服务覆盖 2800 多个城市，累计校验商家信息 7 亿多次，收录评价 13 亿多条（[美团新闻 2026-07-27](https://www.meituan.com/news/NN260727198008607)）。

**对 de-linker 的启示**："二次校验"（先查实时状态，再说话）和"确认后才执行"是两条可以直接搬的纪律。外呼、领券、按地理位置推荐都不适用。

### 1.3 Amazon：Alexa for Shopping（原 Rufus）

**名称与位置**：2026-05-13 起，Rufus 更名为 Alexa for Shopping，整合 Rufus 与 Alexa+，面向美国用户，无需 Prime（[aboutamazon 发布稿](https://www.aboutamazon.com/news/retail/alexa-for-shopping-ai-assistant)）。入口有三处：App 底部导航的 Alexa 图标、桌面端顶部、**主搜索栏**（搜索栏能识别输入是问题还是关键词，问题直接由助手回答）（发布稿）。CNBC 补充两点：搜索结果中会弹出带少量推荐商品的聊天窗；该助手会在"相关时"展示广告（[CNBC 2026-05-13](https://www.cnbc.com/2026/05/13/amazon-ditches-rufus-ai-chatbot-in-favor-of-alexa-shopping-agent.html)）。改名前 Rufus 已遍布首页、商品详情页和 Lens Live，商品页上有它生成的"相关问题"可直接点击（[aboutamazon Rufus 页面](https://www.aboutamazon.com/news/retail/amazon-rufus-ai-assistant-personalized-shopping-features)；[aboutamazon 2024 Rufus 全美上线](https://www.aboutamazon.com/news/retail/how-to-use-amazon-rufus)）。

**动作**（发布稿）：
- 在搜索结果里勾选多件商品，生成并排对比；
- 搜索结果顶部和商品页给出 AI 概览；
- 一年价格历史；
- 定时任务（例如"降到 10 美元且 2 个月内没买过就加购"）；
- 按对话构建购物车，或从历史订单加购；
- 跨站 Buy for Me；
- 查看和编辑"它对你的了解"；
- 生成购物指南；
- 拍照搜索、降价提醒、自动购买、包裹追踪。

Rufus 页面还提到：按场景搜索时，需求宽泛就建议可浏览的品类，需求具体就直接给可加购的单品；"Help Me Decide"按钮；客服类问题（退换、改单等）。

**锚定与架构（一手技术说明）**
- 自研购物专用 LLM。训练数据以整个商品目录、客户评论、社区问答为主，再加公开网页。回答前先做 RAG，证据源包括评论、目录、社区问答，以及调用 Stores API。点赞/点踩反馈通过强化学习回流。端到端逐 token 流式输出；模型同时生成**界面标记**，由服务端查询内部系统把数据填回答案元素，Amazon 称之为 **hydration**（[Amazon Science 2024-10-04](https://www.amazon.science/blog/the-technology-behind-amazons-genai-powered-shopping-assistant-rufus)）。
- 后来迁到 Bedrock，多模型并用：Nova、Claude Sonnet 和自研模型。按问题复杂度路由：简单参数问答（"这把电钻多少瓦"）走小而快的模型；规划和送礼类问题走推理模型，并可调用网页搜索工具。订单历史这类已知上下文直接放进首轮推理。用工具调用实时查询目录、库存、价格和订单。延迟靠 prompt caching 和并行工具调用压下来。评估指标包括 LLM-as-judge 的准确率、延迟、复访和对话轮数。降价提醒和自动购买需要专门为代理建服务（[AWS ML Blog，约 2025-11](https://aws.amazon.com/blogs/machine-learning/how-rufus-scales-conversational-shopping-experiences-to-millions-of-amazon-customers-with-amazon-bedrock/)；页面作者照片路径日期为 2025/11/20，正文发布日期未抓到）。
- 规模（Amazon 自述）：一年内超过 2.5 亿人使用；使用者完成购买的可能性高 60%（AWS 博客同上）。

### 1.4 Meta AI（购物模式、Business AI）

- **购物模式**（2026-04 Muse Spark 发布，之后随更新扩展）：从各 App 中的穿搭、陈设、送礼内容出发推荐。后续加入：在购物模式里同时搜索附近的 Facebook Marketplace 二手和全网新品，配地图显示位置，可按价格、风格、距离细化；可 @ 某品牌或创作者，以网格浏览其商品；拍照比较同类商品（[about.fb.com Muse Spark 2026-04（含后续更新段落）](https://about.fb.com/news/2026/04/introducing-muse-spark-meta-superintelligence-labs/)）。
- **Business AI**：商家在 WhatsApp 上的 AI，回答"有没有货"等问题，墨西哥和菲律宾每周超过 100 万次对话，2026 年计划扩展到"直接办事"（[about.fb.com 2026-01](https://about.fb.com/news/2026/01/2026-ai-drives-performance/)）。
- Marketplace 卖家侧：Meta AI 根据商品描述、库存、取货地点、价格代拟自动回复（[about.fb.com 2026-03](https://about.fb.com/news/2026/03/facebook-marketplace-new-meta-ai-tools-make-selling-faster-and-easier/)）。
- 架构未公开。techbuzz 等二手稿只是推测，本文不采用。

**对 de-linker**：Meta 在做种草和发现层，不是店内导购，可借鉴的只有"按距离/价格/风格细化"的对话式筛选这一交互。

### 1.5 Alibaba.com Accio（最近的 B2B 同类，重点）

**演进**
- 2024-11-12：作为面向欧美中小企业的 AI B2B 搜索引擎发布，支持英、德、法、葡、西五种语言。用户用文字或图片提问，Accio 给出商品流行度、预估利润分析，最后**列出若干采购选项，由用户与各供应商直接沟通**。数据来自 Alibaba International 平台 5000 万商家、10 亿商品条目及文档，加上公开行业信息；模型为通义千问。测试中采购意向比传统搜索高 40%（[CNBC 2024-11-12](https://www.cnbc.com/2024/11/12/alibaba-launches-ai-search-for-small-biz-says-purchase-intent-jumps.html)）。
- **Accio Agent**（2025）的流程（[WWD/Sourcing Journal，2025；页面最早日期标记 2025-06-16](https://wwd.com/sourcing-journal/industry-news/alibaba-artificial-intelligence-agentic-sourcing-international-commerce-1238855697/)）：
  1. 用户交给它一个任务。可以是单品，也可以是多子任务，例如"活动需要 150 件员工 T 恤 + 帐篷 + 咖啡杯 + 帆布袋，10 月 1 日前到货"；
  2. 它按子任务分别给出合格供应商清单，依据经营年限、国际经验、产能、所在市场、履约记录、认证来评估；
  3. 用户追加约束（例如只要有 Oeko-Tex 认证的），它输出比较各家优劣的定稿清单；
  4. 用户填写各品数量，**Accio 自动起草询盘发给选中的供应商**，之后在平台内与供应商直接对话。

  官方称这一流程自动化了约 70% 的手工采购步骤。
- **Accio Work**（2026-03-23 发布，3 月底上线）：从采购扩展为企业级代理团队，能自动执行 RFQ 并与供应商多轮议价，也覆盖合规（VAT、报关）、营销和物流。用户可以把流程封装成可复用的 "skills"。官方强调答案取自阿里体系的真实交易记录以减少幻觉；涉及资金或文件的高风险动作必须由用户明确批准，并在沙箱内执行。月活超过 1000 万（[PR Newswire 2026-03-23](https://www.prnewswire.com/apac/news-releases/alibaba-international-launches-accio-work-an-enterprise-ai-agent-for-global-businesses-302721781.html)；[Alizila 同题稿](https://www.alizila.com/alibaba-international-unveils-enterprise-ai-agent-platform-for-global-smes/)）。
- 应用商店描述：接入 Alibaba.com、1688、淘宝、AliExpress，对供应商和商品数据做"AI 交叉核验"。有用户评论抱怨按 credits 计费、单次提问耗费上百 credits（[Google Play，2026-10 抓取](https://play.google.com/store/apps/details?id=com.accio.android.app&hl=en)）。

**对 de-linker 的含义**：Accio 证明了 B2B 助手的终点可以是"询盘/RFQ"而不是付款，核心价值在"约束 → 合格清单 → 追加约束收窄 → 对比 → 数量 → 起草请求"这条链上。de-linker 的对应关系是：工程约束（相位、功率、用途、电池兼容）→ 合格 SKU → 对比 → 数量进篮 → Proforma 请求。de-linker 的"供应商评估"维度要换成"商品事实与兼容证据"。

### 1.6 Shopify：Inbox agent（店内 AI 导购）＋ UCP 目录工具

这是**单店、小目录**场景最直接的参照。

- **Inbox agent**（店铺聊天挂件）（[Shopify Help Center，2026-10 抓取](https://help.shopify.com/en/manual/inbox/assigning-your-ai-staff-member)）：
  - 锚定：店铺商品目录、政策、页面、知识库。网页搜索结果只作为"商品相关内容"的次要来源，且**不能冒充店铺知识**。
  - 能做的事：商品问答（详情、库存、价格）、推荐（有偏好或历史时个性化）、查订单（**先要求登录**）、加购；用客户的语言回复，但商品标题可能保留店铺语言。
  - 人工交接：复杂或敏感问题交给员工，并**带上 AI 已有的上下文**；员工不在线时给出店铺邮箱。
  - 披露：强制显示"由 Shopify 提供、你在和 AI 对话"的提示，商家不能删除或修改。
  - 店主责任：Shopify 明确写明店主对 AI 回答的准确性负责。
- **UCP 目录工具**（Universal Commerce Protocol）：旧 Storefront MCP 的目录与购物车工具已移除，改由 UCP 承接（[shopify.dev 迁移说明](https://shopify.dev/docs/apps/build/storefront-mcp)）。单店工具集只有三个（[Storefront Catalog MCP](https://shopify.dev/docs/agents/catalog/storefront-catalog)，实现 ucp.dev 2026-08-25 规范）：
  - `search_catalog`：自由文本 `query`，加 `context`（国家、语言、币种、**intent**），加游标分页；
  - `lookup_catalog`：按 ID 批量查；
  - `get_product`：取完整详情，并做变体选择。

  另有 Cart MCP、Checkout MCP、Order MCP 和 policies/FAQ 工具。
- Shopify Sidekick 是**商家后台**助手，不面向买家，不在本题范围内。

**对 de-linker 的含义**：单店导购所需的工具面很小，"检索 / 按 ID 取 / 取详情 / 篮子 / 订单 / 政策"就够了。答案正确性的责任在店主，所以事实必须来自店铺数据。

### 1.7 Zalando Assistant

- 2024-10-01 推广到全部 25 个市场的已登录用户，使用当地语言；由 Zalando 自有模型加 OpenAI LLM 驱动；能理解地点、天气、场合等上下文（[Zalando 2024-10-01](https://corporate.zalando.com/en/technology/zalando-brings-its-ai-powered-assistant-all-markets-and-adds-four-new-cities-its-trend)）。
- 后续升级（官方稿未抓到日期，晚于 2024-10）（[Zalando 升级稿](https://corporate.zalando.com/en/technology/more-personal-and-smarter-zalando-assistant-enhanced-capabilities-inspire-customers)）：
  - 接入客户账户的偏好和购买历史，试点中"高价值互动"（点赞、加购）增加 40%；
  - **上下文感知**：助手知道用户当前在哪个分区，并给出对应的开场提示。例如在女式牛仔裤分区打开助手，它会说"看到你在看女式牛仔裤"，并建议"Show me flared jeans"。

**对 de-linker**：按页面上下文给开场提示，几乎零成本，可以直接复刻。

### 1.8 京东：京言 ／ 京东AI购

- 2026 年一季度，在京东 App 内用"京言"辅助购物的用户接近 8000 万，同比增长超过 200%（[新浪财经/北京商报 2026-05-19](https://finance.sina.com.cn/jjxw/2026-05-19/doc-inhyivuc2730965.shtml)）；AI 导购年活跃用户超过 1.5 亿（[百度百科·京东AI购](https://baike.baidu.com/item/%E4%BA%AC%E4%B8%9CAI%E8%B4%AD/67966173)）。
- 2025-12 底，独立 App"京东AI购"开始内测。首页分"对话"和"爱购"两个入口；对话入口主动抛出预设话题；用户点进推荐后**跳回京东原生页面**，自行确认规格并支付，属于"辅助决策"模式。百科记录的批评有：推荐品类重复、部分商品信息不准确（百度百科，二手汇编）。

**对 de-linker**："推荐后跳回原生商品页 / 购物车完成确认"是低风险、低成本的做法，适合 de-linker。

### 1.9 Perplexity（跨商户购物）

2025-11 推出免费购物功能：更准确地识别购物意图，并利用以往搜索的记忆做个性化。通过 PayPal "Instant Buy"在答案内结账，零售商作为记录商户（merchant of record），自己处理客服和退货（[CNBC 2025-11-19](https://www.cnbc.com/2025/11/19/perplexity-ai-online-shopping-paypal.html)；[PayPal 新闻稿 2025-11](https://newsroom.paypal-corp.com/2025-11-PayPal-and-Perplexity-Launch-Instant-Buy)）。

这是外部聚合渠道，不是店内助手。对 de-linker 唯一的含义是：目录是否能被外部代理读取（见矩阵"外部代理可读"一行）。

### 1.10 ChatGPT shopping research（反例参考）

- 2025-11 推出，OpenAI 自述"会问聪明的澄清问题，并做深度研究"（[OpenAI LinkedIn 帖](https://www.linkedin.com/posts/openai_introducing-shopping-research-a-new-experience-activity-7398786434486198272-ATMc)；openai.com 原文本次抓取 500，未读到）。
- 实测批评：澄清做成了**限时**的问卷式界面，停顿一会儿就自动跳过；结果是商品卡网格，只有"More like this / Not interested"两个按钮，缺少参数对比与综合判断（[The Next Web](https://thenextweb.com/news/is-chatgpts-new-shopping-research-solving-a-problem-or-creating-one)）。
- 2026 年初结束 Instant Checkout（CNBC 2026-05-13 转述）。

**教训**：澄清问题要可跳过、不限时、只问影响结果的那一项；商品卡必须附带"为什么合格"。

## 2. 横向模式（可直接用于 008 能力 spec）

| 维度 | 观察到的做法 | 出处 |
|---|---|---|
| 入口位置 | 主搜索框识别问句（Amazon、淘宝 AI万能搜、美团问小团）；底部导航或常驻图标（Amazon、美团）；商品页的相关问题（Rufus）；消息栏（淘宝）；店铺聊天挂件（Shopify） | 1.1、1.2、1.3、1.6 |
| 开场 | 预设问题（Rufus、京东）；按当前页面或分区生成的开场提示（Zalando）；结尾的"你还可以问"（淘宝） | 1.3、1.7、1.8、1.1 |
| 收窄 | 一句话多条件并列筛选；参数不合理时主动纠偏；用户追加约束后重算（Accio） | 1.1、1.5 |
| 呈现 | 分组 + 理由 + 商品卡 + 价格，最后给综合建议（淘宝）；勾选后并排对比（Amazon、淘宝问问）；表格汇总（淘宝深度思考）；模型输出界面标记、服务端填充数据（Rufus hydration） | 1.1、1.3 |
| 锚定 | 平台目录 + 实时状态（库存、价格、余位）+ 评论/问答 + 订单；网页只作次要来源，并标明来源 | 1.2、1.3、1.6 |
| 动作 | 加购、按对话建篮、复购、查单、起草询盘/RFQ；高风险动作要求用户确认（美团、Accio Work）；查单前先登录（Shopify） | 1.2、1.3、1.5、1.6 |
| 兜底 | 带上下文交给人工，人工不在时给邮箱（Shopify）；AI 外呼（美团） | 1.6、1.2 |
| 工程 | 工具调用 + RAG；按复杂度路由模型；流式输出；prompt caching；并行工具；LLM-as-judge 评估 | 1.3 |

## 3. 能力矩阵与 de-linker 判定

图例：●＝有一手或可靠证据；○＝二手或部分证据；空＝未见证据（不等于没有）。列：淘＝淘宝/千问，美＝美团小团，亚＝Amazon AfS/Rufus，M＝Meta AI，A＝Accio，S＝Shopify Inbox/UCP，Z＝Zalando，京＝京东，P＝Perplexity，C＝ChatGPT。

判定：**复刻**＝照做；**改造**＝保留机制、换成 B2B 工程语义；**不做**＝前提不成立或与业主裁定冲突。

| # | 能力 | 淘 | 美 | 亚 | M | A | S | Z | 京 | P | C | de-linker 判定与理由 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 搜索框识别问句并交给助手 | ● | ○ | ● |  |  |  |  |  |  |  | **改造**：目录搜索框遇到问句（"10 kWp three-phase hybrid…"）时打开 Advisor 并带上原句；关键词仍走 Woo 搜索。约 100 个 SKU，不需要 AI 概览层 |
| 2 | 按页面上下文给开场提示 |  |  | ● |  |  |  | ● | ○ |  |  | **复刻**：商品页给"与此型号兼容的电池？""单相/三相选哪款？"；目录页按分类给提示；购物车页给"检查这套组合是否匹配" |
| 3 | 多条件一次筛选（意图 → 结构化条件） | ● | ● | ○ |  | ● | ○ |  |  |  |  | **复刻（核心）**：相位、功率、用途、电池类型/兼容、光伏输入，作为资格条件在归一化事实层（007）上**确定性**过滤；模型只负责把话解析成条件 |
| 4 | 参数不合理时主动纠偏 | ● |  |  |  |  |  |  |  |  |  | **改造**：用工程规则说明，例如"10 kWp 不等于必须买 10 kW 逆变器"、单相站点不推荐三相机。规则来自事实和引擎，不新增词表 |
| 5 | 只问影响选择的澄清问题 | ● | ○ | ○ |  | ● |  |  |  |  | ● | **改造**：一次只问一个缺失的决定性条件，用可点选的 chips，可跳过、不限时（ChatGPT 反例）。190 验收已经写了"只问必要问题" |
| 6 | 商品卡 + "为什么合格"理由 | ● |  | ● | ● | ● | ● | ● | ● | ● | ● | **复刻**：卡片和正文出自同一个合格集合；理由引用具体事实（相位、功率、兼容证据） |
| 7 | 模型输出标记，服务端填充事实（hydration） |  |  | ● |  |  |  |  |  |  |  | **复刻（架构）**：模型只输出 SKU ID 和结构；价格、规格、库存、文档链接由服务端从事实层填充，杜绝编造参数 |
| 8 | 并排对比 | ● |  | ● |  | ● |  |  |  |  |  | **复刻**：从候选卡或目录勾选 2–4 款，按工程字段对比（AC 功率、MPPT/光伏输入、相位、兼容电池、保修文档），复用现有比较组件 |
| 9 | 搜索/商品页 AI 概览 |  |  | ● |  |  |  |  |  |  |  | **不做**：商品描述与营销文案冻结（Law 6）；100 个商品不需要生成式品类概览 |
| 10 | 评论/社区问答作为证据 | ○ | ● | ● |  |  |  |  |  |  |  | **改造**：没有评论数据，换成自有托管的 datasheet、手册、兼容清单（ADR-0023）作为证据源，并在答案里引用 |
| 11 | 实时状态二次校验 |  | ● | ● |  | ○ | ● |  |  |  |  | **复刻**：推荐前读取在售/可订状态（显示为"in stock"，不给数量和天数，按业主裁定） |
| 12 | 加购 / 按对话建篮 | ● |  | ● |  |  | ● |  |  | ● |  | **复刻**：加入 Proforma 篮子，用户点击确认；数量由用户给 |
| 13 | 在对话中下单/支付 | ● | ● | ● |  |  |  |  |  | ● | ○ | **改造**：终点是"提交 Proforma 请求"，必须用户明确确认；没有支付语义（行业也在从聊天内结账后撤） |
| 14 | 起草询盘/RFQ |  |  |  |  | ● |  |  |  |  |  | **复刻**：这正是 Proforma 请求；把会话中已确认的条件和 SKU 预填进请求备注 |
| 15 | 查单/状态（需登录） | ● |  | ● |  |  | ● |  |  |  |  | **改造**：登录后读取本人 Proforma/订单记录的状态；匿名用户不给 |
| 16 | 复购 | ○ |  | ● |  |  |  |  |  |  |  | **改造**：安装商和经销商会重复下同类单。"按上次 Proforma 再来一份"是低成本的高价值动作，可放在后一期 |
| 17 | 账户记忆/行为画像个性化 | ● |  | ● |  |  | ● | ● |  | ● |  | **不做画像**：靠行为推荐需要数据量。只保留显式的项目上下文（现有 Project：站点相位、规模），在会话和 Project 范围内记忆 |
| 18 | 拍照/图片找同款 | ● |  | ● | ● | ● |  |  |  |  |  | **改造（可选，后置）**：铭牌或 datasheet 照片 → 识别客户现有设备型号 → 用于兼容判断，不做"找同款" |
| 19 | 价格历史/降价提醒/自动购买 |  |  | ● |  |  |  |  |  |  |  | **不做**：B2B 报价，无在线支付 |
| 20 | 领券/凑单/省钱方案 | ● | ● |  |  |  |  |  |  |  |  | **不做** |
| 21 | 定时任务/主动代理/多代理编排 |  |  | ● |  | ● |  |  |  |  |  | **不做**：超出"AI 导购"的定位 |
| 22 | 带上下文转人工 + 邮箱兜底 |  | ○ |  |  |  | ● |  |  |  |  | **复刻**：公司、服务、物流类问题按业主裁定只给一句团队邮箱；能附上会话摘要更好（mailto 预填或请求备注） |
| 23 | AI 身份披露 |  |  |  |  |  | ● |  |  |  |  | **复刻**：入口处固定一行 EN/DE 说明 |
| 24 | 网页搜索作补充 |  |  | ● | ● |  | ● |  |  | ● |  | **不做**：事实只来自自有目录和托管文档；不引用第三方站点（ADR-0023 的方向） |
| 25 | 点赞/点踩反馈 |  |  | ● |  |  |  |  |  |  | ○ | **改造**：收集反馈供人工复盘（191 卡片反馈），不做强化学习 |
| 26 | 工具调用（检索/按 ID/详情/篮子/订单/政策） | ○ | ○ | ● |  | ○ | ● |  |  |  |  | **复刻（架构）**：工具面照 Shopify UCP 的最小集合：`search_catalog(query, constraints)` / `get_product(id)` / `compare(ids)` / `cart_add` / `proforma_draft` / `my_orders`。约束字段用工程语义 |
| 27 | 按复杂度路由模型 + 流式 + 评估集 |  |  | ● |  |  |  |  |  |  |  | **改造**：简单参数问答走确定性路径或小模型，选型对话走推理模型；先建小型回归评估集（190 原句 EN/DE 起步），用 LLM-as-judge 加人工抽查 |
| 28 | 外部代理可读目录（UCP/MCP） |  |  |  |  |  | ● |  |  | ● |  | **改造（后置）**：同一套目录工具对外只读暴露，相当于 GEO 的延伸；不接外部结账 |

## 4. 对 001 地图未决项的回答

- **客户档案与会话记忆要不要做？** 行为画像不做：所有收益证据（Zalando +40%、Amazon、淘宝"购物偏好"）都建立在海量用户和 SKU 之上。做的是**显式 Project 上下文**（站点相位、规模、已选设备），加上会话内记忆。这和 Shopify 的"会话内偏好用于本次对话"同一量级。
- **入口形态？** 照抄行业已经收敛的四处：目录搜索框（识别问句）、商品页（上下文开场提示）、购物车（组合检查）、账户（Proforma/订单状态）。另外保留一个常驻的聊天入口。不另做一个孤立的"AI 页面"作为主要入口。
- **架构要点**：确定性的资格过滤（事实层）+ 模型负责解析和表达 + 服务端 hydration，加上一个小工具面。这与 Rufus 公开的"RAG/工具 + 界面标记 + 服务端填充"、Shopify 单店工具集一致。

## 5. 未核实与缺口

- Alexa for Shopping 在美国以外（amazon.de）是否同步改名：未核实。
- 淘宝、千问的检索和排序架构：官方未公开，文中引用的拆解是第三方推断。
- Accio Agent 原始发布日期：WWD 页面只抓到日期标记，并非确定的原文日期；Accio 的澄清提问 UI 没有一手截图或文字（只有"追加参数收窄"的流程描述）。
- Zalando 升级稿的发布日期没抓到。
- ChatGPT shopping research 的 openai.com 原文抓取失败（HTTP 500），只能用 OpenAI 官方 LinkedIn 帖和 TNW 实测。
- Klarna、Instacart、拼多多本次未覆盖：题目要求的"3–6 个同类"已用 Shopify、Zalando、京东、Perplexity、ChatGPT 加 Accio 满足。
- 钛媒体援引的"沃尔玛：ChatGPT 内直接成交转化约为跳转的三分之一"是二手转述，未找到沃尔玛原始披露，正文没有把它当作依据。
