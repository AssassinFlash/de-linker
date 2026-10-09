# 006 决议：新中心的架构（2026-10-09）

依据：005 盘点、190 链路追踪、线上事实盘点、002 对标、003 组件研究、007 事实契约。环境事实（2026-10-09 实测）：线上 PHP 8.3.33 / LiteSpeed，REST 已有 `wp-abilities/v1` 与 `wc/store/v1`；VPS Ubuntu 24.04、Python 3.12、1 vCPU、3.9 GB，已有 design-engine 的版本化发布与回滚（`/opt/linker-design-engine/releases/`）。

## 一句话

**事实与动作留在 WordPress（b2b-core 把现有权威函数包成 Abilities）；代理循环跑在 VPS 的 Python 服务（Pydantic AI）；WP 插件缩成壳（入口、会话、代理转发、浏览器端动作执行）。模型只调度与叙述：它只能引用本轮工具返回的商品 ID 与事实 ID，数字由服务端按 ID 填入。**

## 三层

### 1. 事实与动作层：`terravolt-b2b-core` 的 Abilities
每个工具是一个 ability（`wp-abilities/v1`），一个文件、一个 schema、一个测试，直接调用现有权威函数，不复制规则。

| ability | 输入 | 输出 | 复用的权威 | 权限 |
|---|---|---|---|---|
| `linker/search-products` | `{device_class?, application?, phase?, pv_kwp?, kwh_min?, kwh_max?, brand?, future?:['battery'], text?, limit}` | `{qualified:[{product_id, fact_id, title, why:[{field, value, match:true|unknown}], figures:{…规范单位}, commerce:{state, price_visible, in_stock}}], excluded:{by_reason:{application:n, phase:n, pv_input:n, not_in_range:n}}, unknown_fields:[…]}` | 007 的 `tv_woo_b2b_product_traits()` 契约 + `tv_b2b_product_commerce_state()` + 货架 | 匿名可读；价格按现有 B2B 门控 |
| `linker/get-product` | `{product_id}` | 商品记录（ADR-0033 图值、参数表、FAQ、文档 URL 全部自有） | `tv_woo_b2b_facts()`、`tv_b2b_material_with_overrides()` | 匿名 |
| `linker/compare-products` | `{product_ids[2..4], dimensions?}` | 对比表（行 = 维度；电池能量与逆变器交流输出不混） | 现比较页同一数据 | 匿名 |
| `linker/check-compatibility` | `{product_ids}` 或 `{inverter_id, battery_id}` | `{documented: true|false|unknown, scope, source_doc_id}`；无文件即 unknown，不得推断 | `tv_b2b_material_compatibility_*` + `contracts/compatibility-lists.json` | 匿名 |
| `linker/size-hint` | `{plz?, annual_load_kwh?, kwp?, phase?, target_usable_kwh?, segment}` | 引擎 `/design/quick` 的结果摘要 + 到 Planner 的 continue_url（带预填） | `Linker_AI_Engine` + `tv_b2b_project_calculation_inputs` | 匿名 |
| `linker/cart-add`（**浏览器执行**） | `{product_id, qty}` | 服务只返回动作描述；插件在浏览器里用 Store API（`wc/store/v1/cart/add-item`，nonce/Cart-Token）执行并读回数量 | Store API | 已批准合作伙伴（现 `tv_b2b_can_purchase`） |
| `linker/project-add`（浏览器执行） | `{product_id, qty}` | 同上，走现有 `tvb2b/v1/project-products` | ADR-0018/0019 | 匿名（claim cookie）/登录 |
| `linker/proforma-start` | `{}` | `{continue_url: /proforma-request/ 或 /de/proforma-anfrage/}`；服务端不建单 | 187/195 的 Proforma 页 | 登录 |
| `linker/order-status` | `{reference?}` | 该账户最近 Proforma/订单的状态与阶段条 | 现账户门户数据 | 登录（未登录 → 要求登录） |
| `linker/handoff-team` | `{summary}` | 团队邮箱句（EN/DE）+ 会话摘要（供 mailto 或复制） | `Linker_AI_Contracts::team_email_sentence()` 迁至 b2b-core | 匿名 |

**选品核心就在 `search-products` 里，确定性**：先资格（device_class、application、phase、`pv_input_kw ≥ pv_kwp`、kWh 范围、在售），缺字段记 unknown 保留；再排序（已知全匹配 > 含 unknown；其后按交流功率与陈述 kWp 的接近度排序，这是排序不是门槛；再按价格）；返回每件的 `why`。正文与卡片都只能来自 `qualified`。"future battery" 是逆变器上的条件（不把电池放进 device_class），由模型按 schema 填入 `future`，ability 据此只在 `why` 里标注"可接电池/有文件配对"。

### 2. 助手服务：`services/advisor/`（FastAPI + Pydantic AI，Python 3.12，VPS）
- 循环：Pydantic AI Agent，工具 = 对 `wp-abilities/v1` 的 HTTP 调用（服务令牌，只读 ability 匿名调用；登录态由插件把用户上下文透传，服务不持有 WP 会话）。
- 结构化输出（strict）：`{blocks:[{type:'text'|'ask'|'cards'|'compare'|'action', text?, refs:[fact_id], ask?:{field, options}, product_ids?, action?:{name,args}}], language:'en'|'de'}`。**文本里不允许出现数字**，数字写成 `{fact:ID}` 占位，服务端按本轮工具结果填入（Rufus 的 hydration）。
- 锚定核验（替代 11,446 行正则，各只几行且有测试）：① 每个 `product_id`/`fact_id` 必须出现在本轮工具结果里；② 占位符 ID 必须存在且单位可渲染；③ `action` 必须是允许列表之一且参数来自工具结果；④ 范围外意图（公司/服务/物流）由模型分类后只允许 `handoff-team` 块；⑤ 禁词（Incoterms、"our engineers recommend"、库存数量/日期）。不通过 → 带错误重答一次 → 仍不通过回退到确定性模板（只列 qualified 卡片 + 一句追问）。
- 追问策略：最多一个决定性问题（Accio 模式），可跳过；只问 `unknown_fields` 里影响当前选择的字段。
- 模型：默认 DeepSeek（OpenAI 兼容 strict），Anthropic 作可切换供应商（strict + `search_result` 引用块）；每轮工具调用上限 4、token 上限与超时固定；按复杂度分配模型留作开关（Rufus 做法），首版不做。
- 可观测：每轮记录工具调用、核验结果、模型元数据；点赞/点踩写入会话（Rufus 做法，供人工复盘）。
- 发布：沿用 `deploy_design_engine.sh` 的版本化发布/回滚模式，独立服务目录 `/opt/linker-advisor/`，端口不与业主的 :443 代理冲突，TLS 与证书固定沿用引擎做法。
- 为什么不在 PHP 里跑循环：共享主机的执行时限、无流式与重试基础设施、结构化输出与核验库在 Python 生态成熟；1 vCPU 对 I/O 型循环足够（无本地模型）。

### 3. 壳：重建后的 `linker-ai-assistant`
- 保留：会话存储（ADR-0016/0017）、Tool Frame、设置、provider-watch、weekly-report。
- 新写（小）：`linker-ai/v1/assistant/*` 代理路由（鉴权、locale、page_context、conversation_id → 转发服务，流式回传）；浏览器端动作执行器（Store API 加购并读回、Project 加入、continue_url 跳转）；四个入口 + 常驻聊天（目录搜索框识别问句、商品页"问这款"、购物车/Proforma 页"问我的单"、账户页"订单状态"）；按页面上下文的开场提示；AI 身份披露一句。
- 删除：task-planner、answer-validator、authority-resolver、products、compatibility、knowledge（知识检索改为 ability `linker/search-knowledge` 读现有 knowledge-index 与商品 FAQ，若 008 判定仍需要）、vision（铭牌识别后置，不进首版）。
- JS：恢复源码 `src/` + esbuild 构建脚本进仓库，bundle 为构建产物；组件按入口拆文件；卡片组件重建时吸收 191 的反馈容器修复。

## 190 原句走查（EN；DE 同路径，locale 切换提示与文案）
1. 用户："I need a three-phase hybrid inverter for a home with 10 kWp PV and a future battery. Help me narrow the choice."
2. 模型调用 `search-products({device_class:'inverters', application:'home', phase:3, pv_kwp:10, future:['battery'], limit:8})`。
3. ability：货架 inverters（59）→ application=home（50 → 排除 6 台 ETR 等 commercial）→ phase=3（住宅三相 28；EcoFlow 补属性后 31）→ `pv_input_kw ≥ 10`（排除 HS2-5K 7.5、HS2-6K 9；HS3-5K 10 保留）→ 按交流功率接近 10 kW 排序：H2-10K-T3、GW10K-ETA、HD-P3-10K0、GW9.999K-ETA、HS2-10K、HS3-10K、GW12K-ETA、H2-12K…；每件 `why`：application=home ✓、phase=3 ✓、pv_input 20 kW ≥ 10 ✓、battery pairing documented ✓/unknown。
4. 模型输出：一段说明（只含 refs 与占位符）+ 8 张卡 + 一个追问（"需要停电备用吗？"或"电池品牌有偏好吗？"）。
5. 核验通过；服务端填数；插件渲染。ESA 电池与 ETR 从构造上不可能出现。
6. 回归断言：qualified 全部 application=home ∧ phase=3 ∧ pv_input ≥ 10；卡片 ID ⊆ 正文 refs 的商品集合；无数字来自模型文本。

## 交给执行票实测的事项（属于首张执行票的验收，不是债）
- DeepSeek strict 工具调用与结构化输出在 EN/DE 下的失败率（阈值：核验失败需重答的比例 < 5%，否则切 Anthropic）。
- Store API Cart-Token/nonce 在 LiteSpeed 缓存下的行为（REST 不缓存，但页面 nonce 可能被缓存）。
- Abilities 的服务端调用鉴权（只读 ability 匿名；写动作全部在浏览器执行，服务不需要 WP 写权限）。

## 对 010 的硬约束
`plugins/terravolt-b2b-core/includes/abilities/<one-file-per-ability>.php`；`services/advisor/{app,tools,grounding,prompts,tests}`；`plugins/linker-ai-assistant/{includes/{proxy,conversation,entries},src/,build/}`；任何文件 ≤ 800 行（010 可调），每个 ability 与每个核验规则各有测试。
