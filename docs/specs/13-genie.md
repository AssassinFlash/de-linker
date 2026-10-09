# #13 Genie - Linker's AI assistant

依据：`docs/research/2026-10-09/old-repo-006-target-architecture.md`（工具契约与走查）、`platform-ai-shopping-assistants.md`（对标骨架）、`reusable-commerce-agent-components.md`、`knowledge-audit.md`、`name-check.md`、AGENTS.md §1–§3。

## 产品定义
客户从产品分类页、产品页、Lösungsentwurf 页、账户页或常驻入口打开 Genie；用自然语言给出条件（行业顺序：项目类型含加装 → 相数 → kWp/kW → HV/48 V 与 kWh → 备用 → 接口），Genie 返回合格产品卡（与正文同一集合、每张带"为什么合格"与配对状态）、对比表、一个决定性追问（可跳过），并能执行动作：加入 Lösungsentwurf、加入保存的方案、打开配置器（预填）、查看询盘状态（登录）、转人工（一句团队邮箱 + 摘要）。公司、服务、物流类问题只返回团队邮箱句。首条消息："Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system." / "Hallo, ich bin Genie, der KI-Assistent von Linker. Sie chatten mit einem KI-System."

## 三层
### A. Abilities（`plugins/linker-commerce`，`wp-abilities/v1`，命名空间 `Linker\Commerce\Abilities\`，一类一文件一 schema 一测试）
| ability | 输入 | 输出 |
|---|---|---|
| `linker/search-products` | `{device_class?, application?, phase?, pv_kwp?, kwh_min?, kwh_max?, brand?, series?, future?:['battery'], text?, with_pairings?:bool, lang, limit≤12}` | `{qualified:[{product_id, title, url, why:[{field,value,match:true|'unknown'}], facts:SelectionFactSet, commerce:{price_visible, price?, in_stock:bool, rfq_only:bool}, pairings?:[{product_id,verdict,conditions[]}]}], excluded:{by_reason:{...}}, unknown_fields:[...]}`。资格：device_class、application、phase、`pv_input_kw ≥ pv_kwp`、kWh 范围、已发布且在售；unknown 保留。排序：全匹配 > 含 unknown；再按 `|ac_power_kw − pv_kwp|`；再价格。 |
| `linker/get-product` | `{product_id, lang}` | 商品记录（图值、参数表、FAQ、文档 URL） |
| `linker/compare-products` | `{product_ids[2..4], lang}` | 维度行 × 商品列（电池能量与逆变器输出不混） |
| `linker/check-compatibility` | `{inverter_id, battery_id}` 或 `{product_ids}` | `{verdict: released|released_with_accessory|not_released|unknown, conditions[], documents[]}`（#8 的 compatibility.json） |
| `linker/size-hint` | `{pv_kwp?, annual_load_kwh?, phase?, backup?, plz?}` | `{summary, configurator_url(预填)}`（调 #14 引擎） |
| `linker/inquiry-status` | `{}`（登录） | 本账户询盘列表与状态 |
| `linker/handoff-team` | `{summary}` | `{sentence_en, sentence_de, mailto}` |
| `linker/search-knowledge` | `{query, lang, product_ids?}` | #10 的检索结果（块 ID、文档、页） |
只读 ability 匿名可调；写动作（加入 Lösungsentwurf、加入方案）不是 ability，由浏览器执行。

### B. 服务（`services/genie`，FastAPI + Pydantic AI）
- `POST /turn`（SSE 流）：`{conversation_id, messages[], locale, page_context:{type: category|product|draft|account|other, product_id?, draft_ids?}, user:{logged_in, partner?}}`。
- Agent：工具 = A 的 ability（HTTP，服务令牌只用于 inquiry-status 的用户上下文透传，不持 WP 写权限）；每轮 ≤4 次工具调用；strict 结构化输出 `{language, blocks:[{type:'text', text, refs:[fact_id]} | {type:'ask', field, options[]} | {type:'cards', product_ids[]} | {type:'compare', product_ids[]} | {type:'action', name, args} | {type:'handoff', summary}]}`；文本不含数字，写 `{fact:ID}` 占位。
- 锚定核验（各一文件一测试）：`refs`（引用 ID ∈ 本轮工具结果）、`numbers`（占位符可渲染）、`actions`（允许列表与参数来源）、`scope`（公司/服务/物流意图只允许 handoff）、`wording`（无 Incoterms、无 "our engineers recommend"、库存只说有货）。失败 → 带错误重答一次 → 回退模板（只列 qualified 卡 + 一个追问）。
- 水合：服务端把占位符替换为工具结果里的值与单位；卡片数据由壳按 product_id 再取。
- 模型：默认 DeepSeek（OpenAI 兼容 strict），`GENIE_PROVIDER=anthropic` 可切；实测核验失败率 ≥5% 则默认切 Anthropic（写入 PR）。
- 提示词 `prompts/{en,de}/system.md`：范围、口径、追问顺序、"每轮最多一个追问"、"不写数字"。
- 日志：每轮工具调用、核验结果、模型元数据、用户点赞/点踩（SQLite）。发布：`ops/release.sh`（版本目录 + current 软链 + 回滚）。

### C. 壳与前端（`plugins/linker-tools`：PHP `Linker\Tools\Genie\{Proxy,Entries}`；React 入口 `genie`）
- Proxy：`linker-ai/v1/genie/turn` → 服务（鉴权、locale、page_context、conversation_id、流式回传）；会话存储用 WP 原生：匿名以 cookie 绑定的自定义文章类型 `linker_conversation`，登录后归属用户（无自建表）。
- Entries：产品分类页搜索框识别问句出现 "Ask Genie" 芯片；产品页芯片组（"What pairs with this model?" / "Was passt zu diesem Modell?"、"Compare with…"、"Documents"）；Lösungsentwurf 页（"Check my draft" / "Meinen Entwurf prüfen"、"What happens next?"）；账户页（"Where is my Proforma?" / "Wo steht meine Proforma?"）；常驻入口按页面类型给 2–3 条提示；首次点击才加载 JS。
- 组件：线程、消息、追问芯片、ProductCard（加入 Lösungsentwurf 并读回数量；加入方案；状态 pending/added/unverified/retry 在卡内、高度稳定）、CompareTable、Handoff。
- 文案：按 AGENTS.md 规则逐处写，EN/DE；对抗评审记录附 PR。

## 验收（回归表见 `docs/acceptance/protocol.md` §5，R1–R14；此处为必过项）
- [ ] R1/R2（EN/DE 住宅三相 10 kWp 原句）：qualified ⊆ #7 的住宅三相集合；无 ETR/ESA；卡片 ⊆ 正文引用；一个追问。
- [ ] R3 冲突（12 kWp vs HS3-5K）、R4 事实不足（追问相数）、R5 产品页配对、R8 范围外只有邮箱句、R10 加装只列有放行的电池、R14 披露句。
- [ ] 核验注入测试五类全部拦截；核验失败率写入 PR。
- [ ] ProductCard：加入 Lösungsentwurf 的 pending/added/unverified/retry 与加入方案的 saving/saved/failed 均在卡内可见，按钮高度不变，内容不越过卡片（旧票 191 的验收行）；工作区与常驻 × 1440/390。
- [ ] 视觉验收：四入口 + 常驻 × 状态 × EN/DE × 1440/390。
