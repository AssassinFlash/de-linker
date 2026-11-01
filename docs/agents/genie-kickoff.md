# Genie 实现票 · 开工提示词（地图 #220）

业主 2026-10-17：Genie 不换，继续改；全部 Genie 票由其他 AI 执行，Claude 评审。
用法：每张票开一个新会话（Opus），把该票下面那段提示词整段粘进去。每段提示词都会让执行会话先读本文件的"通用规则"。

## 分批

同一批里的票可以同时开；后一批要等它依赖的票**合并**之后再开。地图上有三张不是 Genie 的票是 Genie 的前提，放在第 1 批一起做：

- **#252 本地与线上同步**：所有执行会话都在本地开发和验收。最新的本地快照停在 10-15，之后线上的改动都不在里面；本地还缺线上编译好的样式，页面截图会和线上对不上。不先做它，有界面的票验收会失真。
- **#221 内部通知收件人**：#243（让 Linker 联系我）要给团队发信，#258 要往每日摘要里写一行。收件人规则和每日摘要都在 #221 里改，先做它，后面的票直接用。
- **#246 询盘对所有人开放**：#244 和 #250 都建在新的询盘管线上。它不卡第 1、2 批，放在第 2 批开。

| 批 | 票 | 等什么 |
|---|---|---|
| 1 | **#252 本地同步** · **#221 内部通知** · #233 理解层 · #257 文档检索 · #258 Jev 质检 | 现在就开。#233、#257、#258 主要是服务端逻辑和评测，不依赖界面样式，用当前快照就能做 |
| 2 | #235 会话保留 · #249 主动预览卡 · #246 询盘对所有人开放 | #252 合并（这三张有界面，验收截图要和线上一致） |
| 2 | #234 读当前页面 · #242 价格跟账号走 · #236 拍照与附件 | #233 合并（这几张都改 `agent.py` / `schema.py`）；有界面的部分另等 #252 |
| 2 | #243 让 Linker 联系我 | #233 和 #221 都合并 |
| 3 | #232 hero 接线 | #236 合并，且 #229（页头 EN/DE 一致）已上线：hero 的像素门拿整页和线上比，页头要先定下来 |
| 3 | #251 零件清单 | #233 和 #236 合并 |
| 3 | #244 询盘附摘要 · #250 询盘确认卡 | #246 合并 |
| 最后 | #237 线上实走 | 以上全部上线。Claude 先走一遍留证据，再由业主走 |

#233 和 #257 都合并后，Claude 用 20 题对照集重跑（过关线见 `docs/specs/13-genie.md` "目标"一节），过了再开第 2 批里改 `agent.py` 的票。

账号链与 i18n 的其余票（#222、#223、#225、#227、#245、#229、#253、#254、#263、#264、#265）与 Genie 不互相阻塞，可以另开会话并行；它们的开工提示词照本文件的"通用规则"写法，把票号换掉即可。

## 通用规则（每个执行会话都要读）

```
你是 de-linker 仓库的实现会话。工作目录 /Users/chesterjohn/Documents/de-linker。

开工前按顺序读完：
1. AGENTS.md（全部规则；与任何别的文字冲突时以它为准）
2. docs/specs/13-genie.md 的"目标"一节（业主 2026-10-17 定的 Genie 目标与验收）
3. 你的票：gh issue view <票号> --comments（正文 + 全部评论；评论里有后加的验收题和业主裁定）
4. 票里点名的研究、原型与规格文件
读完先用三五句话复述：这张票要交付什么、怎样算完成、你不碰什么。复述完再动手。

做法：
- 分支 feat/<票号>-<短名>，从最新 origin/main 开。AGENTS.md §5："本轮发现的问题本轮修，不开 follow-up，不留 TODO"：你改到的代码、你的票范围内、或与它直接相关的问题，在本分支修掉。只有属于另一张已开的票、而且改了会与那张票冲突的，才记到那张票上并在 PR 里写明。
- 测试要能反复跑：集成测试自己保存并还原它动过的选项和数据，连跑多次结果一样，不需要"跑前手动清表"。
- 本地栈：每张票用自己的实例，名字用票号，例如 #233 用 g233：just sync g233（一条命令：建或重启实例、拉当前线上快照、装入并施加本地许可；just status 的 snapshot 列是快照时间），本地 Genie 用 just serve g233，进后台用 just login g233 --user <快照里的员工登录名>。地址看 just status。不要用别的会话的实例，也不要动 m4check（业主看原型用）。不要在没装快照的裸实例上做任何 UI 工作。
- 界面验收截图前先 just sync 自己的实例，让本地是当天的线上。本地的 WindPress 样式是线上编译好的那份：分支新增了 Tailwind 类时，跑 just windpress-compile <实例> 重新编译，否则新类在本地没有样式。
- 代码约定见 AGENTS.md §4：PHP 一类一文件 + PHPStan 8 + WPCS；Python 用 uv / ruff / mypy / pytest；前端用 React + TS，样式走 WindPress 管线，不在站点页面加插件 CSS。每个数字与阈值写来源注释。
- 模型只许用 AGENTS.md §5 的四条通道：Genie 对话与升级判分 = deepseek-flash（仅官方 api.deepseek.com）；Jev = typesafe/jev-1.13（仅 OpenRouter /api/v1/systemone）；向量 = gemini-embedding-2（仅 OpenRouter）。OpenRouter 失败必须重试并显式报错，禁止静默换模型或静默降级。
- 密钥只从环境或已有的配置文件读（本机 ~/.config/terravolt-builder/*.env，VPS /etc/linker-genie.env），永不打印、不写进仓库、提交、日志或 PR。
- 客户可见文案（含邮件主题与正文）：EN 先定稿，DE 独立撰写（Sie 体），走文案对抗评审，记录放 docs/acceptance/<日期>/<票号>/copy-review.md。用词照 AGENTS.md §3（不说 article / catalogue / cart）。
- 测试邮件纪律：任何测试只发一封、只发 tester；多收件人路由用 Outbox 队列数据断言。
- 旧仓库的 Law / ADR 编号 / 旧工单号不得出现在代码、注释、提交、文档里。

交付（AGENTS.md §5 验收三件套，缺一不交）：
- 真实夹具测试：改动所在层的测试 + 票里写的评测集（EN/DE），结果数字写进 PR。
- 视觉验收（有界面改动时）：1440 与 390、EN 与 DE、逐状态截图，放 docs/acceptance/<日期>/<票号>/。
- PR 描述：把票的完成标准逐条列出，每条后面写证据（测试名、评测结果、截图路径）。做不到的条目直接写"未完成"和原因，不要含糊。
- 开 PR 前 git fetch && git rebase origin/main，just check 和 just test 全绿。
- CI 绿后停下，不要自己合并：在票上留言"PR #<号> 待评审"，等 Claude 评审。评审意见在同一分支上改。

上线（评审通过、合并之后，且业主同意上线时）：
- 同一目标主机由一个会话执行发布写入。插件走 just cutover deploy 和 verify，数据写入前先验证完整备份。Genie 按 services/genie/ops/PUBLICATION.md 做配对发布与收据读回。涉及 Engine 的读取器升级时使用 services/engine/ops/PUBLICATION.md 的独立流程。
- 线上实测证据（截图、对话日志）补到票上。生产写入只经 SSH，先备份后读回。
```

## 第 1 批

### #252 本地与线上同步（前提）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #252 本地与线上同步 + 后台杂项提示清理。这张票是所有界面验收的前提，请优先保证"一条命令拉出与线上一致的本地实例"。

要点：
- 拉取流程已有：just pull（快照）、just pull load <实例> latest（装入），规格 docs/specs/6-live-pull.md。核对它现在拉下来的东西是否与线上一致，包括数据库、uploads、插件版本（含线上新装的 User Switching）、uploads/windpress/ 里线上编译好的样式。本地页面缺样式（例如注册页成了纯文字）就是要消灭的现象，找到根因再修。
- 拉取后施加本地密钥：LiveCanvas 与 SEOPress 的许可证已在 ~/.config/terravolt-builder/livecanvas.env 和 seopress.env（只读取，不打印）。拉取后自动施加，让本地后台没有授权横幅。
- SEOPress 的重定向提示：逐条判断，该建 301 的建，过时的清除。线上写入照通用规则的上线步骤，先备份后读回，并且要业主同意。
- 写下拉取时间，让执行会话能看出本地有多新。

完成标准：一条命令拉出当前快照并装进一个新实例；本地与线上同页截图一致（营销页、产品页、账户页各一张，1440）；线上和本地后台顶部都没有授权横幅与重定向提示（截图）；该建的 301 抽查可用。
```

### #221 内部通知收件人（前提）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #221 账号链 · 内部通知改投 sunriver，恢复每日摘要。#243 和 #258 会直接用你做出来的收件人规则和每日摘要，请把它们做成一个清楚的、可复用的入口，写进规格。

要点（票里有全文和取证）：
- 内部通知（新注册、VAT 复核、新询盘、联系表单留言、每日摘要）只发 sales@sunriverinverter.com，不发 sales@de-linker.com。chester@de-linker.com 能真的收到才保留作抄送：用本票的真实注册顺带验证，结论写进票里。
- 客户可见的地址（Proforma 卖方邮箱、页脚、Genie 转人工句、发件人 From / Reply-To）保持 sales@de-linker.com。现在 Options::team_to() 两头都在用，要拆开，不要直接改选项值。
- 线上现在是临时止血：新注册、VAT 复核、每日摘要三封团队邮件已在线上停用：woocommerce_linker_new_customer_settings、woocommerce_linker_vat_review_settings、woocommerce_linker_digest_settings 三个选项被设成 {"enabled":"no"}，此前它们不存在（备份在主机 ~/backups/2026-10-17-team-mail-stopgap/）；恢复就是 wp option delete 这三个选项。本票上线时把它们恢复。
- 查清每日摘要切换上线后为什么一封没发，修好。
- 线上实测只允许真实的通知、已收到、已批准三封邮件，收件人只限 sales@sunriverinverter.com 和业主指定的测试邮箱（AGENTS.md 2026-10-17）。

完成标准：Outbox 队列断言每类内部通知只到 sunriver（加上经验证的抄送）；客户可见地址一个没变（有测试）；每日摘要在线上按时发出一封；chester@ 的结论写在票上。
```


### #233 理解层

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #233 Genie · 理解层：产品词匹配 + Jev 意图识别 + 代码路由。

要点（票里有全文）：
- 每条消息先在代码里对 Woo 产品数据做确定性匹配（品牌 / 型号 / 系列 / SKU / 分类，EN/DE、大小写与连字符变体）。命中就由代码调用 linker/search-products 出卡片，产品词永远不能被当成称呼或闲聊（"saj" 回 "Hello saj" 是这张票要消灭的 bug）。
- Jev 一次请求同时问：意图（10 类）、是否问本页、是否找人或不满、是否要追问。起点直接用 docs/research/2026-10-17-jev-intent/eval.py 的问题与判据（实测 97%，结果在同目录 RESULTS.md）。
- 代码按 Jev 的答案路由：置信度 ≥0.8 由代码直接调工具（找产品 → search-products；文档参数 → search-knowledge；配对 → check-compatibility；询盘 → inquiry-status；找人 → 先留好接口给 #243）；置信度低于 0.8 交给 deepseek-flash 决定。deepseek-flash 只根据工具结果写回答。
- 与 #257 的边界：你负责"什么时候查文档"，并在文档意图时调用 linker/search-knowledge；检索本身的质量、索引选择、报错方式归 #257，不要改 KnowledgeIndex 一层。
- 顺带纠正（票评论）：回答里出现禁用词 article；PDF 地址原样输出成长 URL，应改为文档卡片 / 链接。用词表进系统提示，并在回答校验里检查。
- Jev 或 OpenRouter 失败：显式记日志，然后降级为 deepseek-flash 决定（这是票里写明允许的降级，必须在日志和测试里可见）。

完成标准（逐条给证据）：
- 票里的裸品牌、型号、系列、分类词评测集 EN/DE 全部出对应产品，零例被当称呼。
- 60 条 Jev 评测在 VPS 上复跑，意图 ≥95%，并加入线上真实问题（VPS turns.sqlite 里的历史问句，去掉个人信息）。
- docs/research/2026-10-17-knocket/raw/trial/questions.json 的第 1、8、10、14 题：分别出 SAJ 产品、答出 EcoFlow 的相数与功率、作为文档问题处理 CB2 间距（不转 sales@）、把容量问题引向配置器（不兜底，不甩 12 张卡）。用 raw/trial/genie.py 对本地实例跑，结果贴进 PR。
```

### #257 文档检索

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #257 Genie · 文档检索真正用上 gemini-embedding-2。

已完成，不要重做：线上 wp-config.php 的 HOME 修复已上线并验证（见票评论，网页检索确实走了 gemini-embedding-2）。

本票剩下的：
- 失败显式：配置了查询编码器却编码失败时，重试后显式报错并记日志，不能静默退回 FULLTEXT。只有主机根本没有查询编码器时，才允许按 AGENTS.md §4 用 BM25 回退，而且要在日志里标明。
- 两份索引择一：线上 WP 的 wp_genie_chunks（MariaDB）与 VPS 的 /opt/linker-genie/index/current（SQLite）。选一份作为 Genie 的唯一检索源，写清理由，更新 docs/specs/10-knowledge-index.md，另一份的去留写进规格。
- 回答引用文档页码；数字由服务端从检索块填入，模型只引用块 ID（AGENTS.md §4）。
- 与 #233 的边界：#233 负责"什么时候查"，你负责"查得准、报错清楚、引用对"。本票的端到端验收用强制调用 search-knowledge 的评测来做；#233 合并后由 Claude 做一次完整重跑。

完成标准（逐条给证据）：
- 网页检索确实调用 gemini-embedding-2（OpenRouter 用量随检索增长，或日志），失败有显式报错。
- 文档评测集 EN/DE，至少包含 docs/research/2026-10-17-knocket/raw/trial/questions.json 的第 2、3、5、6、7、8、9、10、19 题。第 3 题要答出"3 个 MPPT"，第 7 题要答出 2026 年起户用混合机 10 年，第 9 题要给出 SAJ 配置说明 'Export limit settings' 或 H2 手册 6.6 节的步骤，第 10 题要给出快速安装指南里的间距；每题都要引用检索块。第 19 题必须明说文档里没有，不能编。判分依据见 docs/research/2026-10-17-knocket/TRIAL.md §1。
```

### #258 Jev 质检

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #258 Genie · Jev 质检上线。

业主 2026-10-17 已定：**只做事后质检**。回答照常立刻发出，不进回答路径。
要点：
- 按 docs/specs/33-judge-bakeoff.md 的"部署目标"：VPS 上队列驱动的后台进程，逐轮评判线上 Genie 的回答（有据 / 恰当 / 推荐是否更好），并做引用核验。Jev 不确定时升级给 deepseek-flash（官方 API）判。
- 通道：Jev = typesafe/jev-1.13，仅经 OpenRouter /api/v1/systemone；规格 33 里写的 aihubmix 已被模型路由铁律取代，实现时按铁律做，并把规格改正。
- 现有本地评判代码：services/genie/eval/judges/score.py，能复用就复用。
- 结果在 WP 后台可见，能追到具体对话。每日摘要里加一行质检汇总：#221（恢复每日摘要）已合并就直接接上；还没合并就在 #221 票上留言写清接口，由 #221 接。
- 作为 systemd 服务部署到 VPS（与 linker-genie 同一套方式），失败显式报警，不静默。

完成标准：线上新对话在几分钟内出现评判结果；后台能看到并追到对话；Jev 不确定时的升级有日志；OpenRouter 失败有显式报错。
```

## 第 2 批

### #235 会话全部保留（等 #252 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #235 Genie · 会话全部保留。

要点：
- 业主 2026-10-17：访客的全部会话保存在本浏览器（不止一个），可切换、可清除、可发到自己邮箱；登录后全部并入账户并跨设备（docs/specs/13-genie.md 目标第 7 条，验收 A9、A12）。
- 现状：plugins/linker-tools/includes/Genie/Conversations.php 写死访客只有一个会话；plugins/linker-tools/src/genie/App.tsx 切换 / 新建会话时无条件收起侧栏（第 317 行附近）。
- 保留策略照现有 Retention（访客 90 天）；浏览器端存储与服务端记录的关系写进 13-genie.md。
- "发到自己邮箱"是事务邮件：文案走对抗评审，测试守测试邮件纪律。

完成标准：访客连开三个会话都在列表里、可切回；新建不收起面板；登录后三个都在账户下；换设备登录也在；EN/DE × 1440/390 截图。
```

### #249 主动预览卡（等 #252 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #249 Genie · 主动预览卡。

业主已选样式 A · 提示卡（票评论）。可运行的原型和截图在 docs/prototypes/2026-10-17-preview-card/，原型代码只作参考，不进生产，按仓库约定重写。
规则照原型和票：首页（滚过 hero 后）、产品、分类、解决方案页；滚过主内容并停留约 8 秒出现；每次访问最多一次；对话进行中不出现；关掉后 30 天不再出现；表单、询盘、登录页不出现；手机端只在圆钮上出标记；不抢焦点。点建议走 Genie dock 加载器的 linker-genie-ask 事件。阈值写来源注释（docs/research/2026-10-17-ai-assistants/）。
卡片里点名当前页面：#234 未合并前，用页面上已有的产品 / 分类名；#234 合并后改用它的页面上下文。不要在本票里扩展 PageContext。
文案（各页 2–4 条建议、AI 提示）走对抗评审。

完成标准：验收 A3——1440 / 390 截图逐条证明每条规则；EN/DE。
```

### #246 询盘对所有人开放（等 #252 合并；#244、#250 的前提）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #246 账号链 · 询盘对所有人开放（访客也能发）。#244 和 #250 会建在你做出来的询盘管线上，请把"发一份询盘"做成一个入口，Proforma 请求页和以后的 Genie 确认卡都调它。

要点：业主 2026-10-17 已定，见 AGENTS.md §2"询盘对所有人开放"和原型 docs/prototypes/2026-10-17-inquiry/（README 与 DECISION）：访客只填邮箱、姓名、公司（选填）和一个开放留言框，不问国家；Lösungsentwurf 里的产品一并带上；Proforma 请求页左表单、右草稿；已登录客户资料折叠成一行。联系表单保持现状；联系留言与询盘"两扇门、一份记录"。外观照线上现有商务页设计（AGENTS.md 2026-10-10）。文案走对抗评审，测试守测试邮件纪律。

完成标准：访客不登录能发出带产品的询盘；已登录客户一键发送；团队通知只到 #221 定下的内部收件人（Outbox 断言）；EN/DE × 1440/390 截图。
```


### #234 读当前页面（等 #233 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #234 Genie · 读当前页面。#233（理解层）已合并，在它的基础上做。

要点：
- 每轮带 URL、页面类型、产品 / 分类 / 文章 / 草稿 ID、标题；在服务端解析成该页的真实内容。八类页面：首页、产品、分类、解决方案 / 营销页、博客、FAQ、Lösungsentwurf、账户。现在的 PageContext 只有 5 个 type（services/genie/src/linker_genie/schema.py）。
- 站内页面内容现在不在知识库里（docs/specs/10-knowledge-index.md），需要一份页面内容来源（WP 原生 REST 或生成的内容包），写进规格。
- Jev 的"是否问本页"（#233）决定什么时候用页面内容回答。
- dock 打开时的开场建议随页面变化，每类页面至少两条，文案走对抗评审。
- #249 的预览卡改用本票的页面上下文。

完成标准：每类页面至少两问的评测通过（含"这页说的……是什么意思"、产品页上的"这款"不用重打型号）；开场建议随页面变化；EN/DE。
```

### #242 价格跟账号走（等 #233 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #242 Genie · 价格跟账号走。#233 已合并，在它的基础上做。

要点：
- 站内唯一的价格规则是 plugins/linker-commerce/includes/Gating/CommerceState.php（已批准才显示价格；待审、限制与访客一样）。Genie 必须用同一条规则，不另写一套。
- 现在 Genie 的产品能力全部匿名调用（services/genie/src/linker_genie/abilities.py），代理刻意不传身份（plugins/linker-tools/includes/Genie/Proxy.php 第 262 行附近）。仿照 inquiry-status 已有的短时令牌（UserContext），让产品能力按客户自己的账号读价格。令牌的有效期与范围写进规格。
- 模型正文不写价格数字，价格只出现在卡片里，由服务端填入。

完成标准：同一产品，已批准账号在 Genie 卡片里看到的价格与产品页一致；访客、待审、限制账号都看不到价格；有夹具测试覆盖四种账号状态。
```

### #243 让 Linker 联系我（等 #233 和 #221 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #243 Genie · 让 Linker 联系我（对话转团队）。#233 已合并，用它的"是否找人或不满"信号。

要点（docs/specs/13-genie.md 目标第 6 条，验收 A5、A6）：
- 触发：客户要求找人时立即提供；同一问题重复三轮时提议一次，不连续提议两次。两个信号叠加：Jev 的"是否找人或不满"，加一张确定性的找人短语表（EN/DE，命中就直接提供，不经模型；思路来自 docs/research/2026-10-17-knocket/DOSSIER.md 和 TRIAL.md）。不要学 Knocket 那样转人工后让 AI 静音。
- 已登录客户不再问联系方式；访客请留邮箱。
- 团队收到：对话全文链接、摘要、当时的页面、Lösungsentwurf。收件人用 #221 做好的内部通知入口（内部通知只发 sales@sunriverinverter.com），不要自己另写收件人。
- 对客户承诺一个工作日内回复（AGENTS.md 2026-10-09）。
- 文案与邮件走对抗评审；测试守测试邮件纪律。

完成标准：EN/DE 下 "Can I talk to a person?"、"Ich möchte mit einem Mitarbeiter sprechen" 和一句不满的话都触发；Outbox 队列断言团队邮件内容齐全；访客与已登录两种流程截图。
```

### #236 拍照识别与附件读取（等 #233 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #236 Genie · 拍照识别与附件读取。#233 已合并，在它的基础上做。

照票里"研究结论"一节做（证据 docs/research/2026-10-17-deepseek-flash-vision/）。要点：
- 浏览器先把照片重编码成 JPEG/WebP（约 1.69 MP，顺带转掉 HEIC）。图片经 deepseek-flash 官方 API 的 image_url 发送。
- 官方 API 不收 PDF：有文字层的页抽文字，扫描页和图纸页渲染成图片。转换放在 VPS（pypdfium2，已在 services/genie/uv.lock）还是浏览器（pdf.js）由本票决定；放 VPS 就同步改 docs/specs/10-knowledge-index.md 关于"不在 VPS 上解析"的那一行。
- 附件走请求里的单独字段，不混进 messages；抽取结果进会话历史，原图不逐轮重发。上传内容的保存与清理随会话保留策略，写进规格。
- 铭牌：单独调用一次 deepseek-flash 抽取（json_object，看不清返回 null）→ 品牌型号交给 linker/search-products → 客户确认 → 走产品或兼容性。置信度由产品数据的确定性命中决定，不用模型自评。看不清时给手动输入的出口。
- build_model 的 profile 加 openai_chat_supports_document_input: False；上游 400 显式进日志。

完成标准：用真实铭牌照片（至少 SAJ、GoodWe、Pylontech 各一张）和数据手册 PDF 的评测通过；hero 与 dock 都能用；EN/DE。
```

## 第 3 批

### #232 hero 接线（等 #236 合并，且 #229 已上线）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #232 Genie · hero 接线实现。#236 已合并。

业主选定变体 B · 就地展开，规则全在票正文里。原型（可运行代码与截图）在 docs/prototypes/2026-10-17-hero/，原型代码只作参考，不进生产。
硬要求：未交互时首页 hero 与线上像素一致（AGENTS.md §5 像素门，掩膜外差异数 = 0，用同一浏览器同机同视口拍 live 与 local）。打字、点胶囊、语音、拍照、附件之后原地展开成对话，回答是真实 Genie，不用脚本。hero 与 dock 是同一个会话。首页 hero 要补进 docs/specs/13-genie.md 的入口一节。

完成标准：EN/DE × 1440/390，每个控件都能原地开聊、不跳页；像素门报告；滚出 hero 后的"继续"入口和关闭后的复原都有截图。
```

### #251 零件清单变成产品（等 #233 和 #236 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #251 Genie · 零件清单变成产品。#233 和 #236 已合并。

要点（目标第 2 条）：客户粘贴清单、上传 CSV / Excel、或者拍手写清单，Genie 逐行用 #233 的确定性匹配找到我们的产品；有疑问的行逐条问；确认后一次加入 Lösungsentwurf（Woo 原生购物车，不建套装 SKU）。读图读文件用 #236 的通道。同行先例见 docs/research/2026-10-17-ai-assistants/。

完成标准：一份 20 行左右的真实混合清单（品牌写法不一、带数量、有一两行我们没有的货）EN/DE 都能逐行匹配、标出不确定和没有的行、一次加入草稿；截图。
```

### #244 询盘附上对话摘要（等 #246 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #244 Genie · 询盘附上对话摘要。#246 已合并，摘要挂在它做好的询盘入口上。

要点：客户和 Genie 聊过之后发询盘时，把对话摘要附在询盘上（后台询盘和团队通知邮件里都能看到），客户在对话里说过的数量、条件、留言预填进询盘表单，不用重复输入（验收 A7）。摘要由 deepseek-flash 生成或按规则拼接，在规格里写清楚。与 #250 确认卡上"附对话摘要"开关用同一个实现。隐私政策补一段说明（文案对抗评审，EN/DE）。会话存储在 linker_conversation（plugins/linker-tools/includes/Genie/Conversations.php）。

完成标准：聊过再发的询盘在后台和 Outbox 队列里都带摘要；预填有截图；隐私政策段落有评审记录。
```

### #250 对话内询盘确认卡（等 #246 合并）

```
先完整读 docs/agents/genie-kickoff.md 的"通用规则"，照做。你的票是 #250 Genie · 对话内询盘确认卡。#246（询盘对所有人开放）已合并。

要点（目标第 5 条，验收 A8）：Genie 在对话里起草询盘，确认卡逐行显示将发送的内容（产品与数量、留言、是否附对话摘要、一个工作日回复承诺），只有客户点"发送"才发出。访客在卡上填邮箱与姓名（与 #246 的访客询盘表单一致）。发送走与 Proforma 请求页同一条 Woo 管线，发出后在同一对话里显示询盘号与状态。缺必填项时转到询盘页并预填。

完成标准：模型输出伪造的"已发送"不会产生询盘（有测试）；确认卡与最终询盘逐行一致；访客与已登录两种流程截图；邮件守测试纪律。
```

## 最后

### #237 线上实走验收

由 Claude 执行：以上全部上线后，Claude 按票里的走法在线上先走一遍并留证据（测试客户邮箱用票评论里业主指定的那个），然后交业主自己走。不需要开执行会话。
