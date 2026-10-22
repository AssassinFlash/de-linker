# 统一方案工具对站点入口、内容、路由、语言、SEO及统计的影响

日期：2026-10-22。研究范围：站点入口、内容、路由和语言/SEO/统计；不重复商务记录、Genie对话及保存模型调查。只写研究文件，未操作浏览器、未启动服务、未写产品代码或生产。

## 结论与取证版本

不能把“SC应用改好”作为整项交付。至少要同时完成：入口意图合同、旧屋顶深链迁移、EN/DE切换恢复、站点内容与搜索元数据同步、共享呈现隔离，以及尊重现有同意状态的可观测事件。已有导航已经是一个SC入口，需改变的是屋顶的可发现性和进入同一项目的能力，不应凭想象再合并一遍导航。

产品依据是[本轮产品结构决定](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-system-route-548/docs/research/2026-10-22-roof-system-rebuild/PRODUCT-STRUCTURE.md)：统一工具/项目，全欧洲，屋顶重点入口，Journal工作台。它不等于已有视觉或现有结果获批。

静态现状锁定 origin/main **340a11a9cc3a33f687ca8092fcd6285cb9dcfc42**，本轮用`git show`读该提交；主checkout仍2b2e8267，本研究分支原HEAD为5b37f7fb，未rebase。下文S编号全部指向340a固定源码，避免本地分支行号漂移。线上运行版本本轮未读回。既有r549 HTTP/浏览器证据来自10月22日装入的独立快照、代码起点123aea57，不伪称340a线上实测。

标签：**S=固定源码事实，R=既有HTTP/DOM读回，B=既有浏览器实走，N=本轮建议且待实现验收**。

## 1. 入口和内容消费者

| 消费者与当前行为 | 只换工具会留下的问题 | 必须同步修改的位置与实际要求 |
|---|---|---|
| **主页、桌面导航、移动菜单、页脚（S/R）**：EN/DE页头各有一个SC链接；描述说Roof detail是附加步骤。主页既有R只找到三条SC链接，文字与桌面、手机导航及页脚相同，未见单独屋顶主内容CTA。S1–S3；R1:7–42 | 新工具即使能画屋顶，客户仍可能只看到“储能整套配置”；若只改桌面菜单，手机旧描述仍在 | EN/DE header partial一起改入口说明；首页本体增加真实屋顶预览/明确开始动作，进入同一工具的屋顶工作区。首页普通内容来自站点数据，不在`configurator_page.html`内；施工前须取得最新LC正文/媒体/语言对并记录对应post ID，不能只改React或导航。保持一个SC工具身份。 |
| **安装商页（R）**：`/for-installer/` 的“Open the Roof detail step”明确链接`?step=roof`，其他CTA进根页；DE对应R1:125–151。R1:91–120 | 目前屋顶深链没有兑现；已有目标/资料也不随入口进入项目 | 同步安装商正文中的href和任务说明；屋顶入口可以先补地点，不允许退回住宅表单找隐藏按钮。输入框/项目意图的Genie接线由另一域审；这里要求链接必须消费已有有效上下文。 |
| **住宅/商用方案及应用页（R）**：住宅“Explore Backup Options”进根页；商业削峰/自用/EV缓冲/关键负荷备电四项CTA全部进根页。R1:385–510 | 默认住宅（S9）丢掉商业背景、具体目标；用户重新填写和猜选项。只改按钮文案仍丢意图 | 对每个CTA记录来源页面、任务、项目背景和可验证已有输入。新统一工具按资料进入对应工作区；背景可预选，不限制屋顶能力。EV缓冲等仅在真实支持的方法范围内承诺，不因CTA存在就宣称会计算。 |
| **商品列表/分类（S）**：侧栏工具卡经`configurator_page_url()`/PageUrls进本语言SC根页，文案说按site data配置storage。S10/S11 | 产品筛选/已选型号不是工具预填；换根URL能保持跳转但不会带设备身份 | 保留本语言原生地址解析。若设计“以此设备开始”，新入口合同须显式携带canonical product/model身份并在工具校验；不得从当前筛选区间推断客户已选择某设备。商品页/比较/询盘的选中产品交接由商务域细化。 |
| **Journal/博客（S/R）**：EN/DE index正文末尾直接进SC根页，原生文章页与schema不随这一链接自动改变。S12；R1:160–180 | 文章谈削峰/备电/屋顶，进入工具却不保留任务；把Journal框架复制到工具也不会自动给文章加正确目标 | 同步EN/DE正文导流与真实任务落点。仅有明确约定的内容可携带intent；不把文章内容当已验证项目输入。Journal本身不是本次全面改版对象。 |
| **FAQ/文档库（S）**：FAQ/Documents有`#linker-library-panel-faq`/`#linker-library-panel-documents`、原生数据片段与配置。S13 | 若抽共享“dashboard导航”时覆盖全局hash/history处理，现有文档深链、过滤和返回会回归；未发现该模板有独立屋顶CTA，不应虚构已有入口 | 工具路由限定自己应用根节点与页面；保留库的hash和query控制。FAQ正文/商品FAQ可能含工具说明，需在最新Woo正文和FAQ存储中检索旧称与德国限定，再按事实更新；本轮未把未读到的数据库正文说成已全部核清。 |

R1是既有匿名HTTP锚点清单，**有链接不等于在相应视口可见**；不将表内各页都冒称B。当前首页是否已有独立可见屋顶入口仍须新快照/浏览器确认。

## 2. URL和深链必须作为公开合同迁移

**现有断点（S+B）：** S4:331–333把旧`/design-canvas/`、`/de/design-canvas/`、`/de/entwurfsflache/`重定向到本语言SC的`?step=roof`。但是S6:80–89输出engine/rest/nonce加五个prefill，**没有读取step或输出data-step**；S7:50却依赖`data.step === 'roof'`。即使补了这层，S8还要求`defaults.plz`才打开屋顶。R2和B1已验证EN/DE旧基线的200落点仍是住宅表单。根因不在301状态是否绿色，不能只修重定向。

S6:51当前只接受`pv_kwp/annual_kwh/phase/backup/plz`；S7:77只承认德国式五位邮编。没有项目国家、工作区、项目版本、选中设备或既有系统拓扑的入口合同。S9默认住宅和按segment挂不同面板，不符合一个项目按任务工作的目标。

**需要落实（N）：** 在统一应用边界定义且验证一种导航意图：目标workspace、项目引用（若有）、来源与目标、可验证的输入补充。具体参数名尚未设计，不把新参数加到旧表单当最终架构。一次性输入仅能合并进当前项目时提示和保留依据，不能无声覆盖已有方案；无效/过时引用显示可恢复错误。屋顶无地点时落屋顶工作区的地点采集态，不能假装已有地图。应用内back/forward/refresh和分享后的落点属于同一合同。

迁移至少覆盖S4里的旧planner、request-a-project、旧quote与三个屋顶地址，EN/DE本语言一跳到正确落点。S5的`carrying_query()`在目标自带query时直接返回，**原请求其他query会被丢弃**：不能假定UTM/新项目引用经旧roof URL自动保留。目标workspace语义可以优先，但允许携带的其他参数需显式合并/校验并验收。当前工具源码未见读取location.hash/search或history路由；新路由不能仅靠新URL长得合理。

## 3. 语言、国家、SEO和schema是不同消费者

- **语言与国家（S/N）：** S7以HTML lang选择EN/DE；国家应是项目数据，不能把德语当德国。S14在340a已扩展商品过滤白名单，包含`step`与`phase`，并对Contact载荷做专门重校验；仍不保留`pv_kwp/annual_kwh/backup/plz`，也没有新项目国家/项目引用的语义。切EN↔DE不能重建空项目或重置国家。不要让规划载荷借用Contact专属JSON或随意扩大所有页面query白名单。
- **路由权威（S/N）：** S11以canonical page和Polylang twin解析动态入口；S16:156–157注册两个工具页面，同一S17 mount模板。新工具不应因内部workspace新增一批虚假WP页面或破坏现有页面配对；若选独立应用路由，需有明确的两语言入口/回跳适配和项目恢复。具体路由由新架构决定。
- **SEO（S/N）：** S15给Polylang EN加x-default；S23仅作用商品归档，不能误当统一工具SEO已处理。施工应分别核工具公共入口的title/description/canonical/hreflang/sitemap、旧别名301、私有项目/带敏感资料结果的索引与分享策略。公开根页可介绍能力，个人项目/计算版本不应因SPA路由默认落入公共索引。这里是需定义的产品交付，未声称当前SEO配置已满足。
- **schema与存储边界（S/未知）：** 本轮tracked工具LC模板S17只有mount，没有SoftwareApplication JSON-LD。tracked ProductSchema/ArchiveSchema未发现配置器URL消费者；这不证明数据库SEOPress schema模板、营销LC正文、文章/FAQ里没有旧工具名或德国承诺。施工前须只读导出当前站点相应对象与已渲染head，形成“对象ID/语言/来源→旧引用→改动→读回”的内容迁移清单，并同步真实能力说明和JSON-LD；不能只全仓搜索后宣布SEO清零。产品结构改变不授权改写无关产品事实。

## 4. 共享呈现和统计的具体影响

**共享呈现（S/N）。** S16的present拥有工具模板、页头页脚、DE twins和WindPress卷；临时在WP后台改它们会与代码发布冲突。Journal工作台参考可用，但新工具样式必须有自己的应用作用域，避免把`aside/nav/input`或全局tokens改到博客、商品过滤、账户、FAQ。S18只扫描commerce的LC/PHP；S19目前tools provider仅扫Entries.php，**并没有扫描React工作台源码**；S20/现有App仍加载自带CSS。这是实现新工作台时须明确纠正/替换的实际样式产出边界，不能以“WindPress已安装”证明新工具类生效。S24有共享sticky header高度和锚点offset，画布、属性面板、手机底部操作与CMP需真实同屏验证。

**统计（S）。** 定向搜索`plugins/linker-tools/src`、tools/includes、commerce/assets与includes未见工具自定义`gtag/dataLayer/page_view`调用（注释提及GA4不算事件）。S21/S22已有SiteKit+CookieYes的解析器阻断、全球denied默认、撤回时禁用/清cookie并可能reload。既有C1是同意链/原生页面浏览证据，不证明屋顶使用、计算成功或项目恢复已经被测量。

**所需可观测合同（N）。** 同一次工具visit至少能区分入口来源与任务、打开屋顶、获得/缺失自动数据、人工输入完成、计算开始/完成/失败、结果因输入变化过时、继续设备/报告等状态；事件在实际状态成立时发出，失败不能记作成功。精确事件名与payload尚待实现规格。统计不得携带地址、坐标、邮编、用户文件、原始负荷、型号自由文本、私有项目链接或报告内容；按已给分析同意发送，拒绝时工具功能照常。SPA工作区导航和真实page_view不要重复上报；旧URL、EN/DE转换与referrer/UTM要能归到同一能力入口。S22的撤回可能触发reload，故**撤回同意后项目恢复**也是必验路径，不能把恢复问题归咎CMP而留下。

## 5. 本域验收路径与放行证据

以下全部为**N，尚未执行**；现有B只证明旧问题，不构成新工作台验收。以EN/DE×1440/390执行对应状态，记录源SHA、快照、身份、URL、输入、前后项目版本、截图与DOM/网络结果。

1. **新访客首页→屋顶重点入口**：桌面/手机可找到；进入同一工具屋顶工作区，无地点时明确采集；选国家/地点后布局；再到负荷/设备仍是同一项目。共享导航、页脚、CookieYes在小屏不遮挡主动作。
2. **旧书签/搜索结果→正确工作区**：枚举S4各地址及DE别名；带step、允许的query/UTM和无效参数；一跳/无循环，正确语言与workspace，不退回默认住宅。刷新、back/forward同样正确。
3. **商用内容四目标→项目**：商业自用、削峰、备电等逐个CTA保留其意图；商业仍可画屋顶；已存在项目时不会无声覆盖。EV缓冲若方法未成立，明确下一步所需输入与团队交接，而不是展示伪计算结果。
4. **商品分类/列表、PDP、Journal/正文、FAQ/文档→规划/返回**：既有过滤和文档hash保留；打开正确语言工具；有约定的设备/目标上下文逐项验收；浏览器返回仍是原筛选/文章/文档位置。PDP、比较、商务交接由相应域补证。
5. **项目国家FR/CH/UK等与EN↔DE独立**：同一项目/版本和位置不变、输入不丢、国家不变；页面元数据是对应语言；不沿用德国5位邮编判断其他国家。逐国计算精度由引擎域核，不在本域以路由成功代替。
6. **SEO/内容发布读回**：root工具EN/DE title、canonical、alternate/x-default及sitemap；旧址301；新私有项目/报告不会落公开索引；静态LC、动态正文、商品FAQ和schema中的旧入口/适用范围逐项闭环。
7. **拒绝/同意/撤回统计**：初次拒绝不产生测量流量，接受后仅发送允许的状态事件，错误与成功分开；切工作区不重复page_view；撤回触发reload时项目/任务能恢复。生产验证不把测试项目或PII写分析属性。
8. **共享面回归**：工具之外首页/产品/分类/Journal/FAQ/账户两语言导航、搜索、focus、sticky offset和风格无未经授权变化；WindPress编译后的真实CSS与LC发布读回，不能仅看源码类名。

## 6. 固定证据索引

本表提供精确路径、行号与340a不可变源码链接。实施前以将要发布的固定SHA重跑这些消费者，不将本报告分支的旧业务文件当最新实现。

- S1：[plugins/linker-commerce/content/livecanvas/partials/header.html:145](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/livecanvas/partials/header.html#L145) — EN桌面工具入口与描述；手机同文件250行。
- S2：[plugins/linker-commerce/content/livecanvas/partials/de/header.html:145](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/livecanvas/partials/de/header.html#L145) — DE桌面入口；手机250行。
- S3：[plugins/linker-commerce/content/livecanvas/partials/footer.html:132](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/livecanvas/partials/footer.html#L132) — 页脚Plan with Linker入口；德语对应partials/de/footer.html:132。
- S4：[plugins/linker-tools/data/legacy-redirects.json:317](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/data/legacy-redirects.json#L317) — 旧planner地址；331–335行旧工具入口。
- S5：[plugins/linker-tools/includes/Redirects.php:114](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/includes/Redirects.php#L114) — carrying_query：目标已有query时整串返回；否则携带请求query；137行起调度。
- S6：[plugins/linker-tools/includes/Configurator/Mount.php:51](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/includes/Configurator/Mount.php#L51) — prefill白名单；80–89行挂载、102–160行过滤。
- S7：[plugins/linker-tools/src/configurator/config.ts:43](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/config.ts#L43) — dataset/语言读取；61–79行预填、德国5位邮编。
- S8：[plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx:190](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx#L190) — openRoof必须与defaults.plz同时存在。
- S9：[plugins/linker-tools/src/configurator/App.tsx:41](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/App.tsx#L41) — 默认住宅；48–54行项目类型切换重置步骤。
- S10：[plugins/linker-commerce/includes/Presentation/ProductShortcodes.php:331](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/ProductShortcodes.php#L331) — 商品列表侧栏工具卡；2011–2012行地址通过PageUrls解析。
- S11：[plugins/linker-commerce/includes/Presentation/PageUrls.php:71](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/PageUrls.php#L71) — 按Polylang解析当前语言页面，缺页返回空串。
- S12：[plugins/linker-commerce/content/livecanvas/blog_index.html:33](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/livecanvas/blog_index.html#L33) — Journal正文尾部进入SC根地址；DE对应de/blog_index.html:33。
- S13：[plugins/linker-commerce/content/livecanvas/faq_page.html:23](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/livecanvas/faq_page.html#L23) — FAQ/Documents原生hash标签；29–36行数据片段与配置。
- S14：[plugins/linker-commerce/includes/Presentation/LanguageLinks.php:28](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/LanguageLinks.php#L28) — 当前语言切换query白名单；118–157行保留/重校验。
- S15：[plugins/linker-i18n/includes/Seo.php:30](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-i18n/includes/Seo.php#L30) — Polylang hreflang与EN x-default；搜索无alternate。
- S16：[plugins/linker-commerce/includes/Presentation/Templates.php:141](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/Templates.php#L141) — 工具EN/DE页面与LC模板归属；194行drift；652行footer同步。
- S17：[plugins/linker-commerce/content/livecanvas/configurator_page.html:10](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/livecanvas/configurator_page.html#L10) — 同一LC挂载模板供两语言使用。
- S18：[plugins/linker-commerce/includes/Presentation/WindPress.php:77](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/WindPress.php#L77) — LC/Presentation PHP进入共享WindPress扫描。
- S19：[plugins/linker-tools/includes/Genie/WindPress.php:64](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/includes/Genie/WindPress.php#L64) — 当前tools provider仅扫描Entries.php；不扫描React源码。
- S20：[plugins/linker-tools/includes/Assets.php:47](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/includes/Assets.php#L47) — 脚本、gettext与独立构建CSS的实际注册。
- S21：[plugins/linker-commerce/includes/Consent/BasicMode.php:31](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Consent/BasicMode.php#L31) — CookieYes/SiteKit consent接线；80–97行阻断；120行全球denied默认。
- S22：[plugins/linker-commerce/assets/consent.js:72](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/assets/consent.js#L72) — 撤回统计同意时禁用GA、清cookie，必要时98行reload。
- S23：[plugins/linker-commerce/includes/Presentation/FamilyNavigation.php:97](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/FamilyNavigation.php#L97) — 商品分组页canonical；111行hreflang；126行scope仅商品归档。
- S24：[plugins/linker-commerce/content/windpress/chrome.css:21](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/content/windpress/chrome.css#L21) — 共享页头高度和anchor scroll offset。

既有证据（不冒充本轮重新实走）：

- R1：[匿名HTTP入口清单](../../2026-10-22-roof-experience/raw/entry-links.json)，2026-10-22T09:27Z、r549 `http://127.0.0.1:9323`；记录HTML锚点和状态，不证明视口可见。关键行7/91/108/143/160/385/463。
- R2：[屋顶深链挂载读回](../../2026-10-22-roof-experience/raw/roof-landing-readback.json)，EN/DE HTTP200但mount无data-step。
- B1：[EN390屋顶入口](../../2026-10-22-roof-experience/browser/local-en-roof-deeplink-390.png)、[EN1440](../../2026-10-22-roof-experience/browser/local-en-roof-deeplink-1440.png)、[DE390](../../2026-10-22-roof-experience/browser/local-de-roof-deeplink-390.png)；当时真实访客落住宅表单。完整覆盖/限制见[体验研究](../../2026-10-22-roof-experience/README.md)，不扩称所有交互全矩阵测试。
- C1：[既有Consent验收](../../../acceptance/2026-10-19/201-consent/README.md)，本地9项真实浏览器测试与后附生产说明来源。该文第28行仅记录当时page_view/session_start/first_visit/scroll，不是规划事件通过证据。

本轮无外部采集，无新增浏览器/服务/账户操作，无业务更改。所有新行为仍待实现与对应验收，研究完成不等于站点影响已修复。
