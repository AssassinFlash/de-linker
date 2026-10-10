# #13 Genie 面板运行记录（2026-10-10，真模型）

环境：本地实例 `t13`（快照 `~/de-linker-data/20261010-0033`，106 件已发布商品），`just serve t13`，服务 `GENIE_PROVIDER=anthropic`（claude-haiku-4-5 经 aihubmix OpenAI 兼容端点）+ `GENIE_WP_URL=http://127.0.0.1:8918`。响应原文存本目录 `panel-*.json`。

## 环境修正（本次面板发现，均已修）

1. **快照库无 Polylang 语言**（旧库早于 Polylang）：`PLL()->model->add_language` 建 en/de_DE_formal、默认 en，265 件商品 `pll_set_post_language(en)`。否则 `linker-i18n` 的 RestLang 在 REST 中把语言过滤成 `0=1`，`get_posts` 返回 0 件商品。
2. **AbilityClient 用 POST 调只读 ability** → 405（read-only 要求 GET）：改为 GET + `input[k]=v` 嵌套查询参数（列表展开为 `input[k][i]`）。
3. **空输入 ability（inquiry-status）** GET 无参数 → input=null → 400：input_schema 增加 `'default' => array()`。
4. **inquiry-status 未登录 401** 打断整轮：AbilityClient 把 401 映射为 `{"error":"login_required"}` 事实，模型据此要求登录（R7 行为正确：未登录 → 登录请求句）。
5. **aihubmix 的 claude 会包 ```json 栅栏** → strict 解析炸（UnexpectedModelBehavior 502）：agent 调用加 `response_format: json_object`；cycle 对 RuntimeError（AgentRunError 基类）按核验失败处理（重试一次→模板），不再 502。
6. **裸数字检查误伤型号名**（"GW10K" 前字母挡住 '10' 后却匹配出 '0'）：ground 的数字检测改为 token 级——纯数字 token 才算数，字母+数字混合 token 是型号。
7. **compat conditions 没进 facts**：模型只能照抄带数字的条件文本 → 现在按 `compat.condition.N` 收集为可占位事实。
8. **提示词收紧**：占位符形式 `{fact:PRODUCTID.FIELD}`、产品用模型名不用占位符、ask.field 枚举钉死、product_id 给定时先 get-product、每轮 user prompt 末尾带 reminder。

## 核验失败率（PR 要求）

| 提供方 | 样本 | grounded | 失败率 |
|---|---|---|---|
| deepseek-chat（默认） | R1 流 x5 + R2 流 x5 | 2/5、1/5 | **80% / 80%**（≥5% 阈值 → 按 spec §B 切 Anthropic） |
| claude-haiku-4-5（修复后） | 五条核心流各一 | 4/5 | 20% |
| 同上 | 最难流（配对 kWh 数字）x5 | 3/5 | 40% |

修复后失败率仍 >5%，残余主因：claude 在含数字的工具结果旁仍偶发写裸数字（check 5 拒绝 → 模板回退，不越界）。记录在案，PR 引用本表。

## 逐条结果（meta 摘要；原文见 panel-*.json）

| 条目 | 输入 | meta | 判定 |
|---|---|---|---|
| R1 EN | 190 原句 | grounded=true（attempts 2 后一次 pass，早期存档） | qualified ⊆ HOME-3φ；一个追问；无 ETR/ESA ✓（panel-r1.json 为 DeepSeek 存档 + claude 复跑 pr1 grounded=true） |
| R2 DE | 190 德语 | grounded=true，attempts=1 | 德语文案、cards ⊆ HOME-3φ、一个 brand 追问 ✓（panel-r2.json） |
| R3 | 12 kWp vs HS3-5K | grounded=true（修提示词后） | 文本明说 HS 三相五千瓦型号不足、推荐 12 kW 级 ✓（panel-r3.json 最后一次） |
| R4 | 事实不足 | grounded=true，attempts=1 | 列单相+三相、问相数 ✓ |
| R5 | 4107 配对 | grounded=true，attempts=2 | ~~✓~~ **原判定错误**：该轮答"无 documented 配对"，而 4107 实有 7 个 released_with_accessory（1832 2067 2068 2069 2070 2090 2092）；错因是模型逐对 check-compatibility 撞工具预算墙且 with_pairings 用错侧。2026-10-11 复跑已过线，见下方复跑节 |
| R6 | 购物车读 | grounded=true，attempts=2 | 未登录说明 + 请给型号；登录路径经 inquiry-status（cookie 透传属 #16 端到端） |
| R7 | 账户 Proforma | grounded=true，attempts=2 | 未登录 → 登录请求句 ✓ |
| R8 EN/DE | 安装？ | grounded=true ×2 | 只有 handoff 块 ✓ |
| R9 | 库存+价格 | grounded=true | 走 handoff（保守）；无 Incoterms/数量 ✓ |
| R10 | GW10K-ET 加电池 | claude 下 attempts=2 常回退（模板只列卡）| 部分通过：未放行不冒充；数字泄漏率为残余已知问题 |
| R11 | 48 V 单相 | grounded=true | 明说目录中没有 48 V 家用电池、给 HV 选项；HV 不混入 ✓ |
| R12 | 三相备用 | grounded=true | 只列 backup 相关、条件写明 ✓ |
| R13 | 商品页芯片（4107） | grounded=true（产品导向提示词后） | 以 4107 为主题 ✓ |
| R14 EN/DE | Lieferzeit? | grounded=true ×2 | 披露句一次 + 邮箱句（handoff）✓ |

面板全量 30+ 问的持续套件归 #16（端到端化），本票交付面板文档 + 本记录 + 单元/组件层全部结构保证测试。

## 2026-10-11 复跑（评审必改 1–4 修复后；存档 `docs/acceptance/2026-10-11/13/`）

环境同上；默认供应商已落代码（anthropic / claude-haiku-4-5，`agent.py::provider_name`，`GENIE_PROVIDER=deepseek` 仍可切）。修复内容：范围外先调 handoff-team、邮箱句以 `{fact:handoff.sentence_*}` 进 handoff 块并水合（渲染层可见）；pairing 问句指定工具路径（已知型号 → 一次逆变器侧 `with_pairings:true` 搜索，pairings 载荷补 documents[]）；拼写数字与逐字母型号禁令进 EN/DE 提示词与 reminder。

| 行 | 输入 | meta | 判定 |
|---|---|---|---|
| R2 EN | 原句 + "Any brand is fine"（补品牌中性以出 cards） | grounded=true，attempts=2，turn 147 | cards [3556 4107 3555] ⊆ HOME-3φ；正文无数字 ✓（panel-r2en.json） |
| R2 DE | 德语原句 + "Marke ist egal" | grounded=true，attempts=2，turn 151 | cards [3556 2199 4107 3555]；德语文案 ✓（panel-r2de.json） |
| R5 | 4107 配对问句 | grounded=true，attempts=1，turn 157 | cards 恰为 7 个 released_with_accessory 电池（1832 2067 2068 2069 2070 2090 2092），documents 水合进正文 ✓（panel-r5.json） |
| R8 EN | 安装？ | grounded=true，attempts=1，turn 158 | handoff 块 = 工具句 "Our team will answer that at sales@de-linker.com."，渲染层可见 ✓（panel-r8en.json） |
| R14 DE | Lieferzeit? | grounded=true，attempts=1，turn 159 | handoff = "Unser Team beantwortet das unter sales@de-linker.com." ✓（panel-r14de.json） |
| R10 | GW10K-ET 加装电池 | grounded=true，attempts=1，turn 160 | 链路过线：识别 GW10K-ETA-G20 → 配对搜索 → 6 块放行电池（3611 3612 6519–6522）+ 文档 ✓（panel-r10.json） |
| r3 拼写类 | twelve kilowatt peak vs HS3-5K | grounded=true，attempts=2，turn 161 | 无 twelve 等词；用户数字转述为 "the PV size you gave"；HS3-5K 被正确劝退 ✓（panel-r3spell.json；正文数字为占位符水合值） |
| r4 拼写类 | 事实不足 | grounded=true，attempts=1，turn 162 | 一个追问（application），无拼写数字 ✓（panel-r4spell.json） |
| r11 拼写类 | forty-eight volt | grounded=true，attempts=2，turn 165 | 无 forty-eight 等词 ✓（panel-r11spell.json；首轮模型自造 `input[voltage]` 被 400 拒，重试合规） |
| r13 拼写类 | 商品页 4107 描述 | grounded=true，attempts=2，turn 166 | 无拼写数字；正文数字为水合值；cards=[4107] ✓（panel-r13spell.json；模型捏造不存在的 fact 键被核验拒绝后合规） |

**复跑核验失败率（claude-haiku-4-5）**：落档 10 行全部 grounded。期间被核验拦下的失败尝试（计入失败率）：R2 EN 3、R2 DE 3、R5 5、r11 1、r13 1，合计 13 次失败 / 23 次尝试 ≈ 57%（每行的存档是该流最终合规的一轮）。失败模式两类：模型在正文写裸数字（usable_kwh 5.0/10.0 等，check 5 拒）与捏造不存在的 fact 键（check 1 拒），均被核验拦下、无越界输出。残余失败率仍远高于 5% 线，维持 Anthropic 默认的依据（§B）。

**本次复跑发现并修复的环境缺陷**：`linker-local serve` 不注入 `GENIE_WP_URL`，服务重启后按默认打 `http://127.0.0.1`，ability 全部 503（tools/local services.py 已改为总是注入实例地址）。

## 2026-10-11 复跑（业主裁定：Genie = deepseek-flash 直连官方 API；存档 `docs/acceptance/2026-10-11/13/deepseek-flash/`）

【业主裁定 2026-10-11】Genie 的对话模型只有 deepseek-flash 一个，直连 DeepSeek 官方 API（`https://api.deepseek.com`）；上一节"维持 Anthropic 默认"的结论**被本裁定取代**——Anthropic 选项连同 `GENIE_PROVIDER` 开关已从服务/发布/文档整个删除（`agent.py::CHAT_PROVIDER` 常量，测试锁死无开关），aihubmix 密钥只保留给 Jev 评审级联与 gemini-embedding-2 索引（#33/#10）。

本节口径为裁定落地后的正式复跑：**11 行**（原 10 行 + R1 原句），问句与逐条表一致（R2 EN/DE 补品牌中性后缀，拼写类行用拼写数字变体），SSE 原文按原格式存档于同目录。同日早些的 10 行首次直连复跑（turn 167–176，同样全 grounded）留存于 git 历史（commit 6c271ce 的本文件与归档）；两轮的行级结论一致。

**端点行为实测（直连 vs aihubmix 代理路径，2026-10-11）**：
- `deepseek-flash` 为官方在架 SKU（`/v1/models`：DeepSeek-V4.1-Flash，1M 上下文，effort 档 low/high/max、默认 high）；`response_format: json_object` 支持，输出无 ```json 栅栏——aihubmix 时代的栅栏失败模式不复现。
- 它是**思考型模型**：响应带 `reasoning_content`（`usage.completion_tokens_details.reasoning_tokens` 计入配额），`max_tokens` 过小时内容为空（思考先烧完配额）——服务不设 `max_tokens`，不受影响。
- `response_format: json_schema` 返回 HTTP 400（Chat Completions 端点不支持）——服务用 pydantic-ai 工具式输出 + `json_object`，不走该路径。
- **关键差异（已适配）**：思考模式拒绝任何强制 `tool_choice`（HTTP 400 "Thinking mode does not support this tool_choice"）。aihubmix 代理路径不拒。适配：`build_model` 改用 pydantic-ai 的 `DeepSeekProvider`（附带 `reasoning_content` 字段与工具循环中的思考内容回传）+ profile 声明实测事实（思考恒开——effort 档无 "none"；思考中禁强制选择），pydantic-ai 遂把 TurnOutput 输出工具本会发出的 `required` 自行降级为 `auto`。库内的名字表只认旧 SKU `deepseek-v4-*`，不认在架名 `deepseek-flash`，故这两条事实须在 `build_model` 的 profile 里声明。

| 行 | 输入 | meta | 判定 |
|---|---|---|---|
| R1 | 原句 | grounded=true，attempts=2，turn 177 | cards [4107 1182 2199 3555 3556 6514] ⊆ HOME-3φ = refs；数字为水合值；一个追问 ✓（panel-r1.json） |
| R2 EN | 原句 + "Any brand is fine" | grounded=true，attempts=1，turn 178 | cards [3556 1182 2199 4107 3555 6514] ⊆ HOME-3φ；正文无裸数字；一个追问 ✓（panel-r2en.json） |
| R2 DE | 德语原句 + "Marke ist egal" | grounded=true，attempts=1，turn 179 | cards [4107 1182 2199 3555 3556]；德语文案；水合值（AC 10、PV 15–20）✓（panel-r2de.json） |
| R5 | 4107 配对问句 | grounded=true，attempts=2，turn 180 | cards 恰为 4107 + 7 个 released_with_accessory 电池（1832 2067 2068 2069 2070 2090 2092）；条件与配置文档进正文 ✓（panel-r5.json） |
| R8 EN | 安装？ | grounded=true，attempts=1，turn 181 | 只有 handoff 块 "Our team will answer that at sales@de-linker.com." ✓（panel-r8en.json） |
| R14 DE | Lieferzeit? | grounded=true，attempts=1，turn 182 | 只有 handoff 块 "Unser Team beantwortet das unter sales@de-linker.com." ✓（panel-r14de.json） |
| R10 | GW10K-ET 加装电池 | grounded=true，attempts=1，turn 183 | 识别 GW10K-ETA-G20；6 块放行电池（3611 3612 6519–6522）全在卡上（另含逆变器本体 3556 一张卡）+ 数据手册 URL、条件句 ✓（panel-r10.json） |
| r3 拼写类 | twelve kilowatt peak vs HS3-5K | grounded=true，attempts=2，turn 184 | 无 twelve 等词；HS3-5K（5/10）明确劝退，改列 PV 适配机型（2198 1185 4108 3576 3584）✓（panel-r3spell.json） |
| r4 拼写类 | 事实不足 | grounded=true，attempts=1，turn 185 | 单相+三相并列，一个追问（phase）✓（panel-r4spell.json） |
| r11 拼写类 | forty-eight volt | grounded=true，attempts=1，turn 186 | 无 forty-eight 等词；如实说明直流电压档不在可取数据里，追问容量 ✓（panel-r11spell.json） |
| r13 拼写类 | 商品页 4107 描述 | grounded=true，attempts=1，turn 187 | 以 H2-10K-T3 为主题（10 kW AC、20 kW PV、3 相均为水合值）；cards=[4107]=refs ✓（panel-r13spell.json） |

**deepseek-flash 直连核验失败率（裁定门槛的统计）**：
- **行级（§B 口径，流未 grounded 即失败）：0/11 = 0% < 5% → 默认成立**，不触发升级业主。
- 生成级（被五核验拦下的模型生成 / 全部生成）：3/14 ≈ 21%（R1、R5、r3 拼写类各 1 次首轮被拦，同轮重试过线；失败原因按现设计不落盘，turn 日志只记每 POST 的最终 failures）。口径注：§B 的历史测量（80%、20–40%、57%）均为行级；生成级数字与此前的 claude 复跑（13/23）同为成本口径，一并如实记录。

**Jev 试点（同轮回答的事后判分）**：jev-1.13 第一道 + 置信度不足升级 deepseek-flash 直连，对本节 11 轮逐问判分（grounded/appropriate/better_pick），与确定性核验一致率 29/30 ≈ 96.7%；唯一分歧（R5 的 grounded）经查为试点构造把逆变器卡片拍平进 offered 列表所致，判分输入歧义而非回答事实错误。全表与判据见 `docs/acceptance/2026-10-11/13/jev-pilot.md`（运行记录 `services/genie/eval/judges/runs/pilot-20261011/`）。
