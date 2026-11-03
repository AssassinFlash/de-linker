# 全站发现与修复记录

目标进行中；下表保留首轮发现及其当时边界。已有后续发布的项目，以“已接受发布与剩余边界”和后续具名批次的当前结论为准，不因历史“待发布”文字重复验证。未覆盖的视觉、交互和业务状态继续保留。

| 问题 | 根因与当前处理 | 当前验收边界 |
|---|---|---|
| 隐私页打印/章节图标变成 u003c 文本 | 页面脚本转义损坏；恢复正确脚本并在唯一已知内容迁移写入前保留斜杠 | 已上线，EN/DE正文hash不变，脚本各29个反斜杠，原生重复写入和部署读回一致 |
| 草稿和询盘按钮对比度、间距、移除入口、链接提示与原生更新状态 | 共享WindPress样式和原生Woo片段未完整承载 | PR512已上线；后续PR517的英德1440/390真实PDP入口→数量1/2→移除/撤销→刷新→0四条线上旅程均已通过，未发送询盘 |
| PDP加入后刷新、更新或撤销多出一件 | add-to-cart命令保留在询盘地址；测试曾手动转到canonical地址掩盖问题 | PR517已上线；四条线上旅程地址不再保留add命令，撤销/刷新后仍为数量2，未发送留言在原生AJAX操作中保留 |
| Genie温度引用丢掉负号 | 数值标记把一元符号留在事实之外 | PR514服务已上线；真实英德新答复均保留-40至+60和-45至+90，295文件逐项读回 |
| Genie恢复历史时价格/附件语言混合、历史价格可能沿用旧权限 | 存储事件中的展示快照未按当前页面与账号重读 | PR517已上线；workspace/hero/dock英德桌面手机12个实际访客状态读回当前语言价格门与文件类型/页码，PDF语言/URL不变；普通approved/restricted/失败权限仍以本地真实夹具为边界 |
| Genie首页单卡过窄/侧栏长德语中间断词 | 以实际容器宽度复用既有手机卡几何；桌面hero单卡占整行，多个卡动作对齐 | PR517线上实际hero单卡900px，dock卡360px；英德两视口动作完整、无页面横溢出。多卡仍以本地真实产品夹具为边界 |
| 首页展开回答缺少段距/标题列表层次，说明文字紧贴reader；手机顶部控件太小 | hero不是原.app排版选择器消费者，首页reset使intro margin为0；hero顶部32px，dock icon32×36，workspace rail-toggle36px | Batch A本地正文排版、44px目标及12入口/6手机增量结果保留。后续654普通恢复、655独立页44px附件与657正常等待已具名上线，但不能替代本行首页展开回答/顶部动作的线上视觉；尚无精确线上映射，该独立门继续待验。证据Q/production-genie-recovery.json、production-workspace-faq.json、production-genie-loading.json及原Batch A本地记录。 |
| 从首页继续到手机侧栏，焦点留在背景，Esc不能关闭 | 线上AX始终为背景附件触发器；原生Esc无变化，当前App缺少对应焦点与关闭边界 | Batch A的32个本地消费者、focus/inert/滚动边界、Esc与原opener返回证据保留。654/655恢复已上线；707另已接受workspace指针关闭/重开，明确不作Escape承诺，不能替代首页→手机helper键盘链。该链线上焦点/Esc/返回仍独立未验；见Q/public-file-coverage.json的workspace_rail_clearance_candidate及原Batch A记录。；2026-10-28线上EN产品页390的独立Ask Genie入口，在React加载中与已加载两状态均原生Escape关闭并把焦点还给入口，见production-genie-recovery.json/product_helper_mobile_escape_current；这不替代首页Continue与premount fallback的独立未验。 |
| Genie文件加载失败时Retry仍是裸文字，helper没有关闭/键盘退出 | 早期fallback在React bundle未载前未继承按钮样式；本轮真实故障另确认首个空root占满一屏，把追加的fallback及Close/Retry推到视口外。717仅用WindPress三行在直接load-error存在时隐藏直接空root；ready非空root不命中，clearFailure移除故障后自动恢复 | PR717已上线并原生归档：source699e2a55、merge9a916f38、native20261027T231924Z-genie-recovery-699e2a55。线上员工态DE390 helper标题/44px Close与Retry可见→解除精确脚本阻断后原生Retry使root非空/displayblock→恢复后App Close隐藏面板并返回Genie fragen；EN1440 workspace故障Retry可见、无Close符合既有语义，Retry后root非空。既有本地Chrome guest EN390保留account siblings并实际点击fallback Close返回入口，DE1440 workspace Retry通过；普通loading/ready及原PHP bootstrap/focus证据复用。公开CSS886534B/SHA3b967370，仅新增规则1处，移除此规则后与旧3c97ad24精确相同；源/卷1f978815、Tools319/Publicatione3保持。首次archive末尾SSH断线发生在manifest已archived后，一次compact只读核4fileshash/8siblingsabsent并退役prior715完成，无重发/重编。只关闭此空占位缺陷和具名消费者；HomeContinue、ordinary failure cache、完整迟到ready/所有入口/线上guest与整页Genie仍独立开放。见Q/production-genie-recovery.json.premount_load_error_viewport。 |
| 营销/首页展开状态中若干细节仍缺设计 | 逐看58张原图发现source错误在照片上无底、附件移除按钮约18px、住宅输入图标约36px、首页深色发送底上的深色箭头、德语铭牌按钮越过内边距及原生两行输入略裁切 | 原32用例/74原图的限定呈现结果保留；643线上EN390/DE1440 Home两行输入均client=scroll54px、高54.39px，已关闭该具名裁切范围。Dictate重复段落已由Batch A最终8用例本地修复，不能再写正在增量；未定位其线上直接证明。646只接受Home图像/Logo等具名范围，不能扩成全部展开态通过；其余source/移除/箭头/欢迎区状态沿原局部证据及独立线上缺口。见Q/production643-home-en-390.json、production643-home-de-1440.json、production646-online.json及Batch A/README.md。 |
| 透明照片页头的语言文字低对比 | 住宅/商业页冷态原图中的EN/DE深字落在暗照片上，属于既有全站页头状态 | PR544已修复；当前线上EN住宅1440首屏确认语言白字/实底#15352f、两链接44×44，实际WindPress cover规则覆盖普通深字默认值。既有住宅/商业ENDE四个本地首屏证据复用，不重测，不冒称本轮线上四页矩阵；原低对比保留为修复前观察。见footer-readable-controls.json/header_current_runtime_followup.transparent_photo_language_diagnosis |
| 安装商手机截图眉题被sticky页头遮住的疑点 | 诊断截图已滚到源输入区；实际Computer Use回到scrollY=0后，德语390页头0–81px、眉题199–213px，首屏完整 | 作为捕获状态诊断关闭，未改页面。原图/DOM见marketing-layout/installer-de-390-scroll-zero；不扩展为其余首屏视觉全部通过 |
| 普通产品加入询盘时带入无关的旧Genie问题 | 原Form隐式取历史summary_note；668已移除普通表单/提交的自动摘要，显式Genie确认摘要保留 | 原线上四次PDP入口均带入旧温度问题；668已上线归档，线上native旧摘要回调0次，真实本地failed-POST含空值保留。当前记录inquiry-message-context.json；完整询盘/收件箱不由此关闭 |
| 4个营销页视口初次等待媒体就绪超时 | 初次静态捕获没有留下失败时媒体状态；无法仅凭超时判站点bug | 补上失败诊断后逐项重试均正常（住宅双视口、英文大型储能手机、德文大型储能手机），首批100视口仅记初步诊断通过；原始失败记录保留，未据此改站点。全部visual_review和interaction仍pending |

| 账户询盘手册链接的手机触摸区偏小（670已修复） | 原account.css仅22.5px高，缺少完整触摸区与hover/focus反馈；当前沿同一WindPress组件补齐 | account-datasheet-touch-target：普通pending客户英德1440/390均44px；线上EN1440/DE390、真实hover/Tab焦点和4px留白点击原PDF通过。原22.5px截图保留；唯一记录account-datasheet-controls.json；其他账户状态与整页pending不变 |

## 已实测的新入口缺陷

住宅储能页 #system-search 的 textarea 接受 `Which battery works with the SAJ H2 inverter?`，但点击 .lk-send-btn 只按 /genie/ 链接导航；进入后恢复原会话，该问题既未在输入框保留，也未成为新消息。建议胶囊经实际消费者复核可预填输入框；缺口在发送步骤。住宅的附件和语音标记仍disabled。需排查同类营销页，复用当前Genie入口与文件/语音机制修复；本轮保持开放。截图 residential-question-lost-before.jpg。先前当地/线上首屏render通过没有覆盖这个状态。

住宅页首个规划演示视频已实际点击播放：readyState4，currentTime推进，时长71.125333秒；正常显示封面与原生控制。仅此媒体状态通过，不据此标记整页视觉通过。

## 测试工具事件

曾以后台身份调用REST而携带访客Woo cookie，Woo原生将访客购物会话迁移至管理员，造成测试中的空草稿。已证明为验收工具会话混用，撤销本次后台session并清理4个本次cookie；用户1的完整购物车元数据和会话行与事前基线一致，无需恢复生产数据。纯访客重走正常。证据见 ../component-states/harness.md 与 staff-session-readback.json，不能把本事件计为网站跨语言购物车bug。

## 捕获工具独立复核后的边界

初步捕获不校验最终路径/HTML语言，且以currentSrc为空跳过未请求图的就绪判断，因此全部既有render pass已降为preliminary-pass，visual/interaction继续pending。初版快速滚动产品批被中断时碰到非原子JSON写入，所谓first-fast-scroll-partial实际为0字节（现保留为.incomplete），不能当成已保存的原始JSON；其stdout日志与会话工具输出只能作重建诊断。营销页原始失败JSON还在，但重试截图与原始采用同名文件，原失败截图帧已无法提供，不作为原帧视觉证据。后续工具必须使用唯一runID/时间/版本、JSON原子写入、严格就绪与URL/语言核验，已捕获画面只作初步发现，不据此宣告网站bug或最终通过。

初步全量系列现已完成704视图（100页面+424产品+40文章+140唯一归档），仍只有发现用途。新版helper的4个样例与随后20篇文章的40个视图已校验最终路径/语言/可见媒体/字体/资产状态/溢出，并以9个native live路径身份、1135个发布包文件完整bytes及编译CSS的前后读回括定版本；记录为version-20261021T191321912Z-78ddc27d-page-46-2.json与version-20261021T191808788Z-d88d10cc-post-0-20.json，分别绑定run/result/screens的SHA。尚未做浏览器response body与native资产的hash映射，不把这项也说成通过。page-matrix目前44个render pass、660个preliminary-pass，704个interaction仍pending；40张博客原图已人工复核，发现的问题见blog-visual-review.md，未据此将带缺陷的页面标成视觉通过。

## FAQ与下载中心实际操作发现

线上运行版本4f722c26，页面EN /faq-download/、DE /de/faq-dokumente/。本轮先完成EN桌面搜索、建议、清空、无结果、FAQ展开、品牌导航，以及手机部分同类状态；德语与完整状态仍待实走。记录见library/live-review.md。已实际下载并以pdfinfo读取AIO3英文数据手册1页，SHA与原托管文件一致；不把此一文件扩展为159份文件均已验证。

- 搜索生成的文档克隆有有效且已加载的图片，但opacity仍为0，原缩略图监听器没有被cloneNode复制。手机三个AIO3结果中两个稳定空白，desktop最初三个均空白；不是文件404或未完成加载。本地已以共享hydrate函数修复原始及克隆节点，并验证load/error/cached图片分支。
- 产品FAQ收起时只显示问题和品牌，重复的“these inverters”/“IOT dongle”无法识别具体型号；型号仅藏在展开后的来源链接。本地已呈现既有product字段，也在搜索建议中补足型号，不改产品事实或回答正文。
- 手机文档卡保留三窄列，标题/型号被挤成多行，Download实际高度34px。本地已改为缩略图与正文两列、动作独立一行，并将适用动作热区补至44px。
- 键盘从搜索建议Enter可定位并展开真实答案，但焦点仍在已离开画面的搜索框，Tab先进入sticky FAQ tab；分页重建后焦点落body。本地已将焦点放在实际summary或文档动作，验证后续Tab路径及sticky遮挡。

上述Library修复已有Spec/Standards独立本地通过：28个JS夹具、8个PHP测试61断言、8个英德双视口视觉用例、10个既有原生浏览器用例及4个无JS原生页面用例。独立查看8张原图，另在真实本地德语390页面确认三个原始缩略图均已加载且opacity为1。证据见library/repair-verification.md；尚未合并、CI或发布，不能写成线上修复。所有文档、分类与其余组合仍须逐项覆盖。

没有把以下行为误报为bug：品牌平滑滚动的首帧尚未到达最终位置；无匹配时Escape按既有语义清掉查询；普通Ask Genie链接目前只承诺打开助手，不能凭推测认定应自动发送查询。

## 产品比较实际操作发现

德语390在真实产品列表选择两件产品后，比较页正常显示两列；但视觉入口是裸加号且选中仍为加号，含义在点击后才由浮动“Vergleichen”显示。比较表的分类值是英文accessories。比较页切到英语时未携带/映射ids，实际清空列表；切回德语与返回产品页仍为0。证据与准确页面、商品ID、工具视口边界见products/live-review.md。本轮待修，尚未计为比较链路通过。

## 品牌归档语言跳转实际发现

实际线上Chint品牌页的页头与页脚均提供/de/brand/chint/作为德语目标。通过页头原生DE链接进入后，渲染德语“Seite nicht gefunden”及404恢复界面，商品卡为空；英语源页有Chint DTSU666一个产品族。原图与范围见taxonomy/chint-live-review.md。这证明lang=false归档需要沿实际语言入口核验，不能把单个初始URL的render成功当作两语言覆盖。其余34个独立品牌/系列入口与别名resolver仍待测，没有将这个样本泛化为所有品牌均有同一缺陷。

2026-10-28只读证据收敛：34个独立URL均已包含在既有local9290的80个EN/DE共享根原生记录中，34对全部200、locale/queried term/canonical/hreflang/切语言目标正确；三个404仅为Chint越界page2控制，不能计作缺根页面。当前相关i18n与ArchiveAssignments源码同构，且与已核验1917生产备份字节相同；一次只读本地WPCLI确认五组brand别名仍由product_brand原生规则承接，无pa_brand-only不可达slug。page-matrix的EcoFlow基线id45实际路由owner194、GoodWe基线id70实际owner191，已仅为对应4行补current_route_owner并保留原id；68行补本地路由具名机制证据。EcoFlow已退出当前销售范围、当前本地计数0，旧产品集合与数量不复用。原Chint线上404是修复前历史观察，不能据此认定当前仍失败；本次没有当前34路由线上执行或全页/视觉/分页通过声明，原总体状态保持。证据：taxonomy/20261022T033539154643Z-98b3e51b/native-http-results.json及taxonomy/rebased-local-readback-summary.json。

## 普通Genie失败恢复的身份缺陷

当前状态（2026-10-26按已接受记录核对）：身份归属、A2/语音/草稿保留及Hero迟到FileReader由654上线；独立页附件入口与completed-history真实UI由655闭合；正常加载反馈及德语词包归属由657闭合，不再列为待修或待发布。唯一记录分别为`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-genie-recovery.json`、`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-workspace-faq.json`、`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-genie-loading.json`。655的workspace_checks.de390_completed/de390_restored是本地真实WP/Cua消费者证据，生产已实走附件选择/移除及ready/pending反馈；这些结果不冒充生产真实模型turn、邮件或询盘提交验收，完整全站具名状态仍开放。下方诊断及旧失败保留为修复前历史。

当前营销入口的entryScope合同只覆盖entry派生草稿；共享failure helper对没有entryId的既有普通Genie失败记录保留legacy路径。独立评审已从实际普通输入与附件prepare生成失败记录，再在B账号或退出后的访客消费者中验证：200空历史与403历史均可恢复A的文字，重试还会使用原PDF字节；工作区有时没有显示附件chip却仍发送该文件。12个诊断组合确认了风险，不能把这些断言通过写成安全验收通过。

此问题已列为同一全站目标中的高优先修复，原因、证据和待评审的修复合同见genie-failure-isolation-discovery.md。使用的是隔离本地身份、HTTP与模型夹具，没有读取真实客户内容，也没有证明线上已经发生数据泄露。营销入口A不能据此宣告所有失败记录已隔离；未知归属旧记录不得直接绑定给当前账号或偷偷重发附件。

Hero排版首轮新增4夹具沿用了旧spec截图名，覆盖了genie-history-locale内相应hero的live/restored/transcript截图；这些文件现为新本地样式，不能再当作517发布前原帧。当前副本保存在hero-rhythm/first-local-20261021T1920Z（目录为复制批次标签，不是截图时间），后续spec按唯一运行时间目录写入，原始采集时间以文件metadata/对应run日志为准。

## 本轮线上细节增量（2026-10-21 22:28–22:33 UTC，待修项）

- 住宅与商用 hero 的源 textarea 没有明确的关联 label；实际 AX 只读到无名称的 text entry。安装商手机输入框有自己的关联名称，不能由 aria-label=null 一概判为无名称。需给住宅/商用源输入补充准确英德名称，沿 LC/语义层处理。
- 商用页1440实际截图中，顶部 eyebrow 与导航处于同一垂直区，照片页头的 EN/DE 深色文字在照片上对比不足。需以初始 scrollY=0 和滚动后分别复核共享页头/hero 间距，不能把浮动 Genie 的遮挡当作该缺陷证据。营销入口交接的10个线上状态已单独留原图，尚非全页视觉 PASS。
- 德语文档库加载后很早点击原生“Dokumente”标签，地址变为 `#linker-library-panel-documents`；增强启动后实际选中仍为 FAQ，随后搜索显示 FAQ。增强完成后再次点击文档标签则正常写入 `?tab=documents`。实际 `library-de-1440-early-tab-race.json` 保留此不一致；这是待复现与修复的渐进增强状态问题，不能以重点击后的正常状态覆盖。原图和读回在独立 marketing-library-release 工作树的 `marketing-library-online/`，这些是 d27f3dc3 线上观测。

## 文档库导航与空归档原生验收增量（2026-10-21 23:23 UTC）

文档库后续真实操作发现并修复：native Documents 提前点击被增强覆盖；隐藏面板零尺寸目标参与 spy；深 FAQ 切三份文档仍停在页脚；reduced-motion 的 auto 继承 CSS smooth；显式目录 click 的 spyLock 挡住自己，已到 SAJ 却仍把 trade 标为当前；紧接搜索建议时旧 lock 又阻止当前项更新。最终 d611a977… 源、40 Node、24 EN/DE×1440/390 实际浏览器用例及双评审通过，PR「Fix Library navigation continuity and current-category feedback」已合并，当前正在部署/线上读回，尚不能写线上关闭。完整原始失败/当前源码读回在 marketing-library-release 树 marketing-library-online/；旧39/24与中间20pass/4fail均保留版本边界。

空归档原因已沿实际 LC matcher 证明：原生仅 post_type fallback 依赖 get_post_type，empty loop 无 post 时失去模板。现有英德模板增加原生 taxonomy assignments 的候选已完成真实 WordPress Exception/Error 写后故障恢复与官方 present→rollback→present：31LC posts完整HTML/元数据、51共享terms与原local数据可精确还原，0新模板、只改231/6905、22generic keys。after/restored十真实HTTP请求都由现有英德LC渲染；rollback再次出现八个裸页，因果链闭合。还须完成最终toolbar细节、编译后ComputerUse、route/cache全矩阵、完整检查/CI/生产备份与读回，当前不关闭。

实际看空页仍有无意义0-0/0和sort下拉，正沿 LC 原生条件补细节：非空保留原toolbar，空页保留可清除筛选chips、隐藏无结果排序与范围；正文状态与浏览出口留在新空态卡内。不要把隐藏整个toolbar导致Clear消失的方案当修复。

共享header在文档库深阅读时透出浅色底层文字，当前chrome.css使用95%白底+blur，已留原图；属于本轮全局视觉待修，并未把带该问题的整页算视觉PASS。

## 线上导航读回与商城空态增量（2026-10-21 23:50–00:08 UTC）

Library PR528 的 a33a0bce 已完成生产发布、官方 WindPress Generate、41项原生收尾、浏览器前后9个部署身份与1151个打包文件一致。缓存mtime1792626156，CSS正文hash保持4d6074dd…；英德隐私全文SHA未变、各29个反斜杠。实际线上EN/DE×1440/390已走native hash优先、目录后键盘建议、深处AIO3 FAQ→3份文档，原帧与每状态几何在 marketing-library-release 树 navigation-cua-online-20261022T0752；同页hash/back/forward另有EN390实测。正常动画中的瞬时帧、整页历史导航重置搜索的观测均与真正PASS帧分开。这只关闭该导航修复的线上门，不关闭Library整页和共享页头缺陷。部署读回证据本地提交d7f7d1d5，尚未进入后续PR。

共享分类最终hide-policy源码已实跑原生cache升级/回滚/再升级：flush为0/1/0/1/0，德语Chint为200/404/404/200/200，normal source symlink恢复、观察fixture删除、terms不变。随后90个原生HTTP请求中80个共享根地址全200，含16个empty roots，当前英德canonical/hreflang/switch均保持同一共享term；10个feed/paged控制单独保留原生结果，不能把SAJ page2重复展示当通过。

商城与英德归档空状态现沿LC条件、WindPress布局和native lc_label呈现；已实走EN/DE手机与桌面，空页保留All products/Alle Produkte及44px可清除chips，隐藏无意义0–0和sort。英文桌面实际hover变深底白字，键盘2px轮廓+3pxoffset；手机两语实际移除brand保留q、Clear全部恢复24families/72productlinks。这里只是本地独立状态证据；未部署 taxonomy batch。

继续点击实际联系入口发现新的承接缺口：products_contact承诺“问题包含本页背景”，href包含kind/title/search/source，但Contact/Form只消费intent。德语390真实落地表单没有来源/搜索可见区，也无可移除context，message为空；brand=chint也未纳入href来源地址。原状态与实际landing见 shared-archive-routes 树 taxonomy/browser-empty-final-20261021T232740731Z/de-390-shop-contact-consumer。当前只证明本地消费者缺口；没有提交表单或发邮件，修复仍开放，不能仅凭URL里有参数宣告承接成功。

实际商城header/footer切语言会丢q/brand/product-page等选择；LanguageLinks白名单只保留s/orderby/step/key/admin-access。与family pager丢filters/sort、越界25–13计数、native /page/2重复13张卡属于同一选择/分页连续性问题，已形成taxonomy/pagination-source-diagnosis.md，尚未实现，不能通过隐藏pager或直接按16个产品切片破坏family合同来关闭。

## 选择连续性与表单细节增量（2026-10-22 05:18 UTC）

共享归档基础修复已合并至主线，后续产品族分页与Contact选择摘要候选仍在独立 shared-archive-routes 工作树，本地15源聚合14cb7f74。最终原生36次只读请求与26跳转均到200，102项语义检查通过；英德各24/24/17家庭、union65。原生Woo排序提交、分页/语言保留筛选、来源选择经编码进入Contact、未勾选不入业务记录等已完成源码双审和本地真实消费者8例458断言；不是生产验收。完整证据在该树 full-site/product-selection-continuity/ACCEPTANCE.md。

最终官方WindPress编译mtime1792645324、705664字节后，CUA已实走英德1440/390的摘要勾选/键盘排除/无效来源/焦点与来源链接。SAJ短名称来源链接44×44，实际hover变色，正常文字对比度由4.3037升至6.0305。手机特殊查询 `SAJ & GoodWe "quoted" \\ Rückfrage + 100%` 实际从第2页Search回到首结果状态，原样进入Contact并经DE链接保留原字符；客户问题仍为空且与来源摘要分离。只认定该组件和路径本地通过，不认定整页通过。

继续真实编辑发现：Contact中输入未提交问题、取消来源勾选后再切DE，文字变空、来源又勾选。当前语言链接只传GET选择，既有failed-POST recovery不承载编辑态；本轮必须补上安全的同浏览会话编辑恢复，不能通过扩大URL传私密文字或偷偷提交询盘来弥补。诊断在该树 product-selection-continuity/form-language-diagnosis.md，尚未实现。

Contact德语hero大标题自动断词，将“gemeinsam”拆出很短的尾行；滚动表单时共享sticky页头还透出底层标题。已留真实原图，与上述摘要组件的局部通过分开，仍待本轮修复。先前父线描述的EHA/ETA德语标题混淆经保存手机原图、当前原生PLL/post/Woo/family输出及本地托管英德ETA手册复核，当前均正确区分单相/三相；这是截图描述误读，撤销产品数据错误疑点，没有改产品事实。

Genie普通编辑恢复还发现已识别语音在身份复核等待期间触发pagehide并真实卸载后永久丢失。9d2e589c候选在相关224测试通过之外，独立新反例0/1红，两轴均BLOCKED；本轮正复用原owner/attempt journal修复。pagehide不是明确Close/Stop取消，不能把旧测试通过或源码存在写成已关闭。所有普通Genie恢复/构建/发布门仍开放。


## 2026-10-25 注册控件与步骤反馈——已实际交付

原PR589的六项问题已由18c85c31集成并上线：业务类型label伪元素占位、无hover反馈、旧认证字体、姓名47%窄宽、网站有效后VAT旧错误、返回标题被页头遮住。生产版20261025T053138Z-auth-18c85c31已archive；英德1440/390与两条client步骤读回通过。证据与回滚在外部既有production589.json；旧页脚不稳定记录保留，未经本批修复的权限/注册提交/完整链路不因此关闭。


## 2026-10-25 博客导航／目录已交付；手机动作热区仍开放

PR606已实际部署归档（8427609d，native20261025T074924Z-blog-8427609d）。两LC模板/blog.css提供原生相邻整卡、手机堆叠、边界空caption消除及长德语目录换行；6个正交ENDE1440/390消费者、实际Enter与卡片8px留白点击/hover完成，不重跑原41/44矩阵。31LCmetadata/pairs、20article对象、26营销/隐私对象保留。

开放 `blog-mobile-touch-and-action-affordance`：DE6883/390真实目录短链接35.796875px，文章报价/返回链接19.5px且主动作无按钮面。下一批沿现有tokens完善主次按钮与手机点击区，保留文字/目的地。本项不能由606目录换行通过关闭。唯一现行记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production606.json。


## 2026-10-25 博客动作热区与交互提示——649 已交付

`blog-mobile-touch-and-action-affordance` 已由 PR649（5b16bd70）修复并部署归档：20261025T090725Z-blog-controls-5b16bd70。主次CTA44.195px、Back/All posts44px、手机目录44px；目录展开、相关标题hover/focus、键盘回博客、章节落点与联系页落地均有线上结果。EN552/DE6885×1440/390仅关闭该控件范围；整页和其余博客状态保持开放。31LC、20文章和26营销/隐私对象保持一致。唯一现行记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-blog-controls.json。


## 2026-10-25 联系来源语言模块——650 已交付

已补齐过去未交付的LinkLocalizer，保留当前Contact/REST/营销正文与样式。源26ddba2a，native 20261025T095929Z-contact-source-26ddba2a已archive；真实JSON marker控制旧线上0/4→本地与新线上4/4。四语言视口消费者与实际Utility资料入口通过，26保护对象/cache和其余runtime保持；未提交表单。记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-contact-source.json。

新开放 `contact-source-only-legend`：Services来源卡片没有所选产品，仍显示 Product selection / Produktauswahl。源转换和传输通过不关闭这个引导问题；原图 contact-source-online-de390.png / contact-source-online-en1440.png 在同证据目录。应在同一目标的下一Contact界面批次改用符合内容的标题，保留真正产品选择的标题与包含/排除行为。


## 2026-10-25 联系来源标题及德语产品入口——651 已上线

`contact-source-only-legend` 与新确认的 `contact-german-product-source` 已解决。公开德语 SAJ ATS1-T63-A 原生 URL 解析误指英文配对，使 canonical 校验丢弃整张来源卡；现在只从同类型、公开无密码的 Polylang 配对中按既有 same-origin/path 校验匹配，保留私有和伪路径拒绝。172 个当前已发布产品原生来源身份均通过；这不是172页的视觉或点击验收。来源页、筛选条件与真实产品分别使用准确标题，包含/排除/无法载入提示英德同步。

PR651/source1bd0b761，native 20261025T113928Z-contact-guidance-1bd0b761 已归档。四个正交桌面/手机英德消费者、实际德语产品询盘入口和英语切换、排除状态保留、错误恢复均通过；没有提交表单、发邮件或调用模型。4个Contact页面及4个空表单状态只关闭该组件，1个产品页只记录入口。其余未验整页、提交与通知状态继续开放。唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-contact-guidance.json。


## 2026-10-25 营销来源误认——开放

`marketing-copy-source-misattribution`：本线将历史仓库稿误认成业主原稿，并据此替换24页。业主明确否认Utility末段购物车标题来自其原文。先前copy接受结论撤销，技术读回仅证明已部署，不能证明内容得到认可。当前授权为新拟候选并由业主选择；正文写入保持停止。已保留所有原前像与回滚记录，不再次盲目换成另一份历史稿。

## 2026-10-26 · 已接受发布与剩余边界

以下是原有发现的当前状态，前文保留事故与当时边界；已接受范围不重新进入整批验证。

- 营销纠正已经发布：业主选择 Utility 第 1 版并授权同语气跨页修改；11 组英德营销页及英德 FAQ 模板完成。是新授权文案，不能称为找回业主原稿。证据：Q/production-marketing-correction.json（accepted-authorized-new-copy）、production-faq-copy-correction.json（accepted）；隐私正文和授权评价保留。
- 普通 Genie 恢复已按 654 的具名范围接受；655 独立页附件、芯片/移除和 startup 禁用/ready 已接受。生产德语390实际选择及移除保持输入/旧附件，英语1440为44px可用按钮；恢复/PDF/Restore沿用。证据：Q/production-genie-recovery.json、production-workspace-faq.json。没有真实模型、邮件、询盘提交的新增通过声明。
- 656 已发布：FAQ 两栏共享一次 fresh authority 装配；实际英德七片段逐字不变，202个FAQ/142份文档保留。一次正常请求配对首字节13.11→8.88秒，HTML请求14.49→10.21秒；仍慢，性能保持开放。原数据/权限/文件字节绑定没有加入TTL。
- 657 正常等待/i18n：已合并并在线上归档接受（Tools ff83e3e3）。沿用一次 CI40227164717；本地 App/Hero 英德中性等待及真实失败→Retry→ready通过。线上德语1440首页自然等待显示 Einen Moment …、status及中性外观；德语390独立页ready/44px附件，实际Hero词包14项与等待词齐全，六个公开产物200/MIME/字节一致。30个CMS完整哨兵、Search、global CSS/cache和Commerce656保持。旧恢复链不重跑。证据：Q/production-genie-loading.json。
- 589 六项注册控件/布局已上线接受，旧集成/CI/发布 remaining 已清除；注册提交、审批权限和完整账号链仍依原全站清单，不被控件修复替代。

Q 为既有 initial-render-media-current-main-20261024 证据目录；page-matrix 已补本批8行、template-matrix补2行有界结论，整体 pending 状态保持。下一性能修复沿现有 Manifest 查询证据推进，不追加全站采样或完整截图矩阵。

## 2026-10-26 · 原始 PDF 下载性能

原 URL 下载也构造完整工程 manifest。一次原生边界计时约4159ms，其中解析/校验文件3087ms；单独合并媒体查找只改善约2%，候选未单独上线，其旧CI已取消。最终候选658/2cd96ff6让下载每次新读当前产品/资料关联，只校验请求文件相关的主文件及别名；完整manifest保留。

本地真实PDF HEAD响应3098→102ms/609→2SQL，线上只读候选3724→194ms/3180→792SQL，状态、响应头、长度和SHA一致。原URL独立Range32发布前首字节7.974s、206且no-store，避免把并行诊断样本当正常客户端基线。最终CI40233023515通过并以43dc56e9合并；2cd源已上线原生归档接受。相同原URL Range32实际首字节7.974→3.667s（单次配对约54%），206/PDF/no-store/ContentRange及32字节保持。访客从德语文档搜索STS点击真实链接，原PDF在新tab显示两页；390站点入口44px、无横向溢出。桌面PDF阅读器保留状态下的手机仿真不算原生手机初始阅读通过。Q/production-document-gate.json为本批状态；FAQ整页和其他全站未覆盖状态继续开放。

## 2026-10-26 · FAQ 按实际用途读取（659）

659（3c8651e1，native 20261025T221718Z-library-read-3c8651e1）已归档接受。FAQ投影沿同一原生发布/资料关联/路径/媒体许可，仅为潜在问答引用组读取真实字节；完整manifest与原PDF下载门保持。真实CLI对照86产品144资料、ENDE各七片段和完整manifest逐字不变；装配3802→1768ms、2714→943SQL。一次同客户端/地址/请求头的公开DE请求TTFB8.649→6.433s、HTML请求9.114→6.959s，非全站或固定速度承诺。

实际DE390公开页仍202问答/142文档；CLI144与公开142属于不同调用上下文，不据此宣称资料丢失。型号搜索可展开原回答，并保留产品、手册及页281链接；字体就绪、docW390。原STS PDF同一32字节Range返回206、PDF MIME/no-store/范围正确。未变ENDE×1440/390样式/交互沿用；本次不将整页visual/interaction pending改成PASS。30个CMS正文/meta/语言配对/反斜杠及Search/globalCSS/Tools保持；7份SQL保留、淘汰190840旧SQL约7.1MB，无新增本地服务，生产lease已释放。唯一当前发布记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-library-read.json。

### 同一目标内的新发现：型号关联文档未进入搜索

`library-document-model-search`保持开放：实际搜索GW10K-EHA-G20得到3个FAQ、0份文档，但展开答案存在本站手册及页281链接。源码已定位：LibraryPage::covers()把多产品关联压成数量，library-ui索引仅使用row.textContent，关联型号因此没有进入文档检索文本。这是既有查找体验缺口；659没有改模板/JS或该行为。下一批在保留紧凑呈现的同时让实际Woo关联型号可用于查找；不把它绑回已经接受的659，不改写文案或增加资料权威。唯一实际观察沿用/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/faq-focused-read-live-de390.png及659 browser记录。

## 2026-10-26 · 型号关联文档查找已修复（660）

`library-document-model-search`已由660（d63318d3，native 20261025T225706Z-library-model-search-d63318d3）修复并归档。当前公开Woo产品关联名进入既有索引；命中结果和建议复用原有covers/gilt für说明，冷态仍保留数量摘要。实际线上EN1440/DE390同一GW10K-EHA-G20由3FAQ/0文档变为3FAQ/4文档；混合型号+manual建议显示关联产品，清空恢复202FAQ/142文档。真实点击数据手册原URL，原PDF正常渲染、原生阅读器显示三页。

本地ENDE1440/390的长型号换行、44px下载目标和无横向溢出通过；线上对应EN1440/DE390读回一致。属性由原生WordPress输出并经DOM/JSON解析，142行/93共享资料均有效；没有从纯文本单测伪造escaping证明。源码和交付双审、CI40241341883均通过，main258ebd1e已含来源。runtime精确2文件，其他1339文件及30个CMS正文/meta/语言/反斜杠哨兵、Search、Tools/globalCSS保持。上一批加载性能与未变交互复用，未新采样。7SQL保留，淘汰195655旧SQL约7.1MB，本地服务和三个临时页已回收，生产lease释放。唯一当前记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-library-model-search.json。全站其他未结项与整页pending保持。


## 2026-10-26 · 661 产品比较的选择连续性与控件已交付

来源f9350430，PR661、CI40245218983已全成功并合并；native `20261025T234410Z-compare-continuity-f9350430` 已发布并归档接受。当前收据 `production-compare-continuity.json`（与既有同目录）保留原线上失败、源码/评审、本地及线上消费者、恢复点与清理结果。

线上真实访客 EN/DE×1440/390：比较页手机页头与桌面页脚切语言保留同两型号及有序原生商品配对；DE自身slug正确运行脚本，类别显示Zubehör。Clear/Remove由16.5/20px变为44px；实际移除留一项、清空恢复原空态；手机实际横向滚动且行标题固定，桌面无溢出时提示隐藏。DE390列表明确Vergleichen及勾选，重新选两款后chip与表格一致；进入PDP后64px控件同步并实际取消/重选。空比较由带抛错装配源的既有用例证明不读取完整manifest；不虚构线上速度提升百分比。

45相关PHP用例144断言、WPCS/PHPStan/build源一致、Spec/新增英德提示与Standards及发布增量评审通过；其他有效结果复用。官方WindPress生成一次，原生读回精确9runtime差异、其余1332文件及30CMS/meta/pair/反斜杠哨兵保持；仅两样式卷更新，main.css/.bak不变。7SQL保留、旧211747冗余SQL已删（7127343B，观测可用空间增加7122944B），own8888停止、lease释放。

本批关闭比较页语言切换、裸加号与类别/触摸/横向提示缺陷。并不声称其他页面的全部独有状态已通过；产品列表直接切换语言时已有选择的状态不在本批实走范围。未覆盖/未解决继续沿原全站台账，完整目标ACTIVE，不重跑本批已通过路径。


## 2026-10-26 · 当前产品覆盖范围已核实

一次原生Woo来源读取与既有Visibility/EngineeringReference规则核对完成：原212条产品记录中42条已退出客户公开范围，原证据与原状态保留并标记历史；新增8349/8350为Trina工程参考，英德客户PDP均实际HEAD404及浏览器error404、无产品UI，继续保留Woo发布供工程使用。当前172条发布配对对应170条客户产品页面，矩阵708条保留记录中620条属于当前客户检查范围（88条历史/工程参考明确排除）。原inventory-baseline的posts/terms/templates保留，current_product_scope单独记录新读取；page-matrix按current_publication.active区分。此结果是范围核实，不是未走页面的视觉/交互通过；工程工具与报告验收保持原范围。 2026-10-28公开产品视觉适用性收敛：2026-10-27T23:03:29.567653+00:00原生WPCLI只读直接SELECT原214产品ID的post_type/status，全部返回product，其中42draft、172publish，与既有撤回范围相符。仅42draft对应的84个EN/DE双视口原行新增current_public_visual_applicability=not-applicable，限定当前匿名公开PDP视觉；基线ID/URL、历史失败、render/visual/interaction及总体状态全部保留。172publish对应344视图（含8349/8350工程参考）本次不强关，不由catalog_hidden推断PDP不可访问；原404/历史重用/Genie/feed/选型保护仍需各自验收，不把下架适用性当保护功能通过。原始查询已成功但本地空行解析未保存stdout；经root明确允许一次相同SELECT纠正补读，跳过空行后安全结果已完整保留，这是唯一有效保存结果，不是站点失败。只读结果行SHA256=ab5f4b38cd8903b6bf3868735bf6bc2aba9db272945c07c2e80919da6b74bcce。


## 2026-10-26 · 比较跨页身份与旧脚本缓存（662/663）

PR662/e11624eb和PR663/1b76c61c已完成本轮功能交付；最终main ff6cce37、native20261026T011105Z-family-cache-1b76c61c已归档。列表实际ENDE1440/390直接切语言保留及取消选择，混合英德ID共享链接归为同两款，移除和PDP语言同步通过。家族首次线上仍执行?ver=1旧缓存，失败原样保留；只改Module一行filemtime，实际同浏览器URL变为?ver=1792972768，6kWh模型规范身份3611、德语Vergleichen、未选false/返回已选true/取消重选均即时正确。未改JS/样式或重测其他页面来补救缓存。

已保持1341精确文件、30CMS/meta/pair/反斜杠及全站CSS；原生当前上一版回滚和661五文件Git恢复范围明确，不声称永久多级服务器回滚。一次已有渲染夹具补配对模拟，原57断言不放宽，原失败CI日志保留。两份超期SQL已删除14254358B，观测free增加14241792B，保留7SQL。

**原始视觉失败（已由664线上修复）：mobile-compare-chip-covers-account。** 最终DE390画面中，Konto erstellen入口矩形(33,705.078125,102.6640625,44)，浮动Vergleichen胶囊(20,700,151.75,48)，真实相交并遮住该入口。证据compare-family-cache-live-de390.png及当前receipt.new_findings；此图同时是唯一该遮挡失败证据，后续不得覆盖。保留在同一完整目标下一批共享手机卡片/浮动入口优化，本批功能通过不代表该整页视觉通过。

## 2026-10-26 · 手机比较入口遮挡已解决（664）

原始失败截图与几何保留。单一入口在折叠导航宽度下改为独立实底栏，留出52px；PDP旧bottom补偿移除，Genie补偿未改。线上同一DE卡片账户y705.078125可直接点击，EN390本地化正常，PDP章节目标在吸顶栏下方，EN/DE1440原位置保持。当前唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-mobile-compare-header.json。不宣称全页视觉已完成。

性能观察待诊断：`pdp-navigation-delay`，该DE电池PDP一次工具导航等待超时，下一次只读同标签页确认已到达。尚无TTFB/服务耗时测量，未认定站点bug，下一批只定位该请求。

## 2026-10-26 · 产品文档读取性能已交付（665）

PR665/source f81b7a18，CI40261492218、Spec/Standards、原生备份/原子切换/OPCache及真实读回已完成。只改ProductView默认下载列表读取，复用当前library元数据投影；完整事实/revision/readiness和原PDF门禁不改。172个当前发布语言记录、144份文档的下载投影全部相同；本地EN/DE各28个实际注册片段逐字相同，线上DE28片段与原版完全一致。

线上原生资料组装：首片段3874.10→1541.39ms，查询2787→1017；全部片段4049.06→1675.42ms。同客户端同URL匿名GET首字节15.412475→12.598695s、总耗时16.480793→13.636167s，两次HTML均348390B。这是单次配对并存在网络波动，不宣称全站速度已达标；首字节仍高，实际HTTP处理中的余下耗时继续待定位。

当前唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-pdp-read.json。其余1340runtime文件、32CMS正文/meta/配对/反斜杠、编译CSS及卷保持原值。无新增测试、实例、工作树或运行服务。8份SQL在保留范围内；已核保留点后淘汰004026旧SQL7127476B，实际可用空间增加7114752B。

浮层观察（业主2026-10-26已接受，不再待修）：`pdp-genie-launcher-covers-download`。EN3611/390文档区，第四个PDF卡片右侧下载点(346,638.418)实际命中Ask Genie；按钮矩形(320,637.609,50,50)，根为linker-genie--peek。唯一原图pdp-read-live-en390.png，不能覆盖。第五卡片位于明确的底部操作栏后方，不据此另外报错。原几何观察保留；业主确认可通过正常滚动避让，不作为待修阻断项，不改Genie入口。整页其他visual/interaction继续按实际范围记录。

下一步：优先定位该页实际HTTP链路剩余耗时和真实失效功能；可正常滚动避让的浮层覆盖按业主裁定接受，不再追加样式候选或覆盖测试。复用本批通过的投影/片段/语种/原文件门禁证据，不重跑已闭合矩阵。

## 2026-10-26 · 产品 FAQ 读取性能已交付（666）

已上线并原生归档接受：来源`f713ca00420ab279bd780f1c2fddd6195977c9f6`，部署`20261026T042714Z-pdp-faq-read-f713ca00`。FAQ展示读取沿用当前发布权限、产品/文档关联与真实引用字节门，省去与展示无关的产品修订和准备状态计算；无答案商品直接返回。线上EN/DE条件和HTML与原版逐字节一致；DE条件+答案处理7.323→3.270秒。普通匿名同一DE产品URL首字节12.599→9.074秒、完整响应13.636→10.207秒，均200、348390字节、0跳转；每版一次、网络条件仍可波动，不能外推全站或CWV。

EN390原生FAQ已实际点开展示原答案，无横向溢出；既有原生172语言记录FAQ投影一致证据复用，仅给共同API结论，不把整页visual/interaction改为PASS。源码与发布增量双审通过，CI40266631155第二次通过、第一次100ms测试失败保留且未改断言；实际runtime仅Publication.php变化，其他1340文件、34CMS哨兵、全局CSS和WindPress卷保持。当前记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-pdp-faq-read.json。

恢复点为本批原生完整SQL及上一原子Commerce代码；8份SQL在保留窗口内，淘汰011046旧SQL7127225字节（实测可用空间增加7122944字节）。临时页23/视口和成功日志已回收，无新增本地实例或测试脚本。可正常滚动避让的Genie覆盖按业主接受保留；全站目标继续ACTIVE，实际加载仍偏慢及其余未结功能/页面保持开放。

## 2026-10-26 · 当前商品资料与FAQ的读取范围已收窄（667）

已发布并原生归档接受，source`89c208798b999e39e56bad23f90619b63278ecd3`、main`863f5304d210b9817833796143188a096a829102`、deploy`20261026T050910Z-product-library-scope-89c20879`。默认PDP下载和FAQ只检查当前商品关联的primary文件以及其FAQ潜在引用；原candidate/source顺序继续决定共享文件标题、角色、语言与别名。独立读取仍刷新原生商品/源权限，实际引用字节和存储绑定仍校验；全量manifest/library及显式snapshot、原PDF门禁合同保持。无内容、模板、CSS、价格门或模型路由改动。

原生172语言记录的下载五项元数据/顺序和FAQ发布结果旧新全部相同。部署后实际EN默认下载/条件/renderer为203.47/219.13/210.67ms，DE为214.71/210.04/228.62ms；EN474B、DE482B FAQ与原版SHA一致。先前每次约1.6s的完整资料读取证据复用。批量86scope投影5312ms仅用于同一当前快照差分，不当作独立冷读性能。

同一普通匿名DE产品URL，单次同参数首字节9.074→4.755s（缩短47.60%）、完整响应10.207→5.915s；两版均200/348390B/0跳转，TLS2.566→2.403s，存在网络波动、不外推全站/CWV。实际DE390显示6个原PDF入口、原德语FAQ点击展开，字体loaded、docW390；其他未变英德/视口及原PDF门禁证据复用，整页visual/interaction pending保持。

完整4文件Spec/Standards和发布增量评审PASS；最终CI40271421599一次成功，原测试与必要静态检查通过。只在既有suite新增1个可检测无关文档/共享首条记录的用例，并给withdrawal旧用例补1断言；回换全库reader会失败，精确候选恢复后复用已有结果。两行PHPDoc纠正没有重跑业务或性能；替代的40271227314与合并后同Git树的重复40272550488 CI已取消，最终源码绿CI保留。

实际runtime精确两PHP变化，其余1339文件、34CMS正文/meta/配对/反斜杠、全局CSS/卷/cache保持。必要完整SQL流到本机，当前8份保留；淘汰022146旧SQL7127589B，实际可用空间增加7118848B。唯一状态/回滚证据：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-product-library-scope.json。临时页24、视口及成功日志/PR正文已回收，无新运行实例、工作树或辅助测试脚本。全站目标ACTIVE，其他未覆盖具名状态和完整提交链继续保留。


## 2026-10-26 · 普通询盘不再混入旧对话（668）

已实际发布并原生归档接受：PR668，source `7f974d64f1ec1d072e7f41f268de70aa48623714`，main `bf2c3e9077448813d13f49f0a5670bfc4d432b0e`，deploy `20261026T064031Z-inquiry-message-context-7f974d64`。普通表单原先会读取上一段Genie摘要、把旧问题放进留言，普通Handler又会静默附上旧摘要；现表单仅使用客户本次输入／失败POST保留值，普通提交显式不带对话摘要。客户在Genie确认卡看过并选择的显式摘要能力保留。既有fallback保留身份、owner、TTL与迟到编辑保护，失败后特意留空也不再被回填。

两个既有原生用例先真实失败，再与显式Sender摘要用例一起通过；相关32个既有handoff／实际App和Hero消费者用例通过。真实本地WP四ENDE1440/390新表单为空；DE390实际无产品／无留言提交后保留姓名、邮箱、consent和空留言，提示德语正确，订单ID哈希和捕获邮件均未变。线上EN1440／DE390字体loaded、表单为空、无横向溢出；线上native过程内旧摘要回调调用数0，公开handoff实际200／JS MIME／3398B及SHA精确。无真实生产表单提交、模型调用或邮件／收件箱完成声明。

最终完整差异及增量Spec／Standards通过，CI40279608735全绿；首轮40278521021的变量声明位置lint失败原日志保留，修正仅把retained取值移到空snapshot早返回之后、仍在await之前。只补查该增量及相应构建，不重跑原生／UI矩阵。合并树与finalhead完全一致，已取消同树重复main CI40281094547。发布实际十文件变化，其余1331文件、34CMS正文／meta／语言配对／反斜杠、编译CSS和WindPress卷保持。无Generate或营销文案改写。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/inquiry-message-context.json。按保留窗口留下8份已验证SQL，淘汰031012旧版7127347B，实测空闲增加7122944B；8个本轮临时成功日志／PR正文／merge元数据删除。复用既有实例，own8888已停止、9411/9412未启动，临时25/26标签与视口清理，原用户9保留，writer释放。只回填4page／4state的具名检查，原整页和未覆盖业务状态不冒充通过。完整全站目标继续ACTIVE，其余真实缺陷与首次覆盖按原清单推进；可正常滚动避让的叠层按业主已接受标准处理，不再增测。


## 2026-10-26 · 账户询盘资料读取性能已交付（669）

上一目标轮为progress（668已上线收尾）；本轮亦为实际交付。PR669/source `3877c708933e118b12963fc5650714c9e06c9f49`、main `fab9ab28539a18487551de842ad4f20b66e6b305`、native `20261026T072902Z-account-datasheet-read-3877c708` 已发布并归档接受。询盘每行资料链接原先调用product()+manifest()两次全站装配，现沿既有当前商品reader读取；只把旧选择URL加入其别名所需字节检查。默认reader／完整manifest／共享首条规则／原PDF门禁保持，未加入TTL、CSS或客户文案改写。

真实本地native单行同输入5918.99→148.78ms、371→8查询；线上同一原生过程7489.31→241.59ms、5431→803查询，完整HTML一致。只代表该链接生成过程，一版一次配对，不外推整页HTTP/CWV。线上真实DE商品6650显示Datenblatt (PDF)并指同一原英文资料；原PDF实际Range 206、application/pdf，Content-Range总长626889B并有有效PDF签名前缀。原始别名替换拒绝、无关文件不读的回归在既有共享用例扩展，旧调用先真实RED；51Publication用例／428断言、10相关用例／82断言及必要静态检查通过。最终完整4文件和publisher增量双审PASS；CI40284145325一次全绿，同Git树重复main CI40285847426取消。

真实本地普通pending客户正常登录→自己询盘→英德四视口→键盘Enter打开原2页PDF已实走，价格仍隐藏。未创建生产测试账号／询盘或发邮件，不把native回调或本地UI说成生产客户整页通过。只回填4条account详情状态的该项检查，其他状态和整页pending保留。新发现account-datasheet-touch-target已记在findings表与同receipt：EN/DE390链接仅22.5px高，actual截图保留，同一全站目标后续账户控件批修复，本批不签视觉关闭。

runtime仅两PHP变化，其他1339文件、34CMS正文/meta/配对/反斜杠、Tools与全局CSS/卷不变，无Generate。必要完整SQL及上一nativeCommerce可回滚；按窗口保留8份验证SQL，042652旧版7127032B已删除，实测空闲增加7114752B。未新建实例、工作树、测试文件或辅助脚本；本地fixture用户44／询盘8175／凭据删除，原67询盘ID完整恢复，捕获邮件0，8888停止、9411/9412未启动。临时27/28页关闭、视口恢复、用户9保留，writer释放。唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/account-datasheet-read.json。完整目标保持ACTIVE；下一步直接沿已有22.5px原图修账户资料控件，复用本批正确性与性能结果。


## 2026-10-26 · 账户资料控件已上线（670）

资料链接由22.5px文字热区改为44px描边控件，补齐悬停变色和键盘焦点；英文与德文沿用原标签、原PDF和权限机制。普通pending客户本地英德1440/390已实走，线上已有询盘实际EN1440/DE390读回；新增留白内4px点击打开原PDF窗口。只回填4条账户详情状态的具名检查，其他状态及整页pending保留。

source `e47e07401102cbdce475a7a354ca1f3e57006af8`，main `99606462be9c5e4c598f12706f3f4dca85c5e8a9`，native `20261026T084545Z-account-datasheet-controls-e47e0740` 已归档接受。源码与发布增量双审、最终CI通过；同树重复main CI取消。运行时仅account.css改变，其余1340文件及34CMS正文/meta/配对/反斜杠保持。官方Generate后按有序CSS规则核实：本地与线上压缩字节不同仅源于互不影响的焦点规则排序，除3条预期控件规则外均保持。没有重复Generate或全站重测。

必要SQL、上一Commerce与原WindPress卷/编译CSS可恢复；当前8份SQL在保留窗内，超窗050847旧SQL7122717B已清理。一次性用户45/询盘8176/凭据和临时页面均回收，原67询盘恢复，8888停止。唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/account-datasheet-controls.json。全站目标继续ACTIVE；按业主裁定，正常滚动可避让的局部覆盖不作为阻断，继续优先处理真实功能失效、阅读/操作困难及加载瓶颈。


## 2026-10-26 · Hybrid文章阅读间距已上线（671）

B4已修复：英德551/6883的嵌套首标题取消重复48px外边距，提示框顶部72→24px；相邻两组正文沿既有token保留24px间距。首个候选实图暴露组间0间距，已纠正，原DE390失败图保留，3张同因重复帧淘汰。最终四个本地来宾阅读区与线上EN1440/DE390均通过；原目录仍到达原heading（DE390 y104.203），可见正文一致，DE390正文区域比前版短216px。只关闭这处阅读区，不把整页/其他文章交互pending改为通过。

source `e6095e442a817bff5418ae0da1a2ce7f9aa8b58e`，main `90b56a3cad3ce9cd8a7d87b7839a8831c4f340c7`，native `20261026T094532Z-blog-reading-rhythm-e6095e44` 已归档接受。源码与发布双审/增量、最终CI40299778272通过；初候选与同树main重复CI取消。运行时仅blog.css改变，其余1340文件和54CMS对象含全部20文章的正文/meta/配对/反斜杠保持；官方编译后仅两条预期规则改变，未变CSS及不冲突的焦点规则排序已核实。

原34个正文内部链接的源检查没有发现缺失媒体或未发布目标；10处源码shop/旧分类路径不能直接按404计错，实际德语6885→Heimspeicher分类保持德语且展示电池，既有RenderLinks/LinkLocalizer承载，未改href。此项不是逐一实走全部链接。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/blog-reading-rhythm.json。保留8份SQL及当前原子前版/原blog卷/编译CSS；超窗064007 SQL与被接替的670旧CSS恢复文件已淘汰。复用本地实例且已停止，无新账号/询盘/测试脚本/工作树；后台会话、临时凭据与35/36页清理，原9保留。全站目标继续ACTIVE；正常滚动可避让的叠层沿业主判定接受。


## 2026-10-26 · 已保存方案移除与撤销（672）

PR672已合并，source baafc9100649792017780f26539a321eb858a502，main9f5cda922279c7a79d9eb514394f3a30b675c3cc，CI40314709093成功，原生20261026T114851Z-account-saved-removal-baafc910已归档接受。原LC卡片只有加入草稿，没有移除；现为明确移除入口→原生确认/保留→可恢复移除→Undo，英德同步，44px及hover/keyfocus沿账号设计体系。PHP只处理数据/原生动作，LC/WindPress负责呈现。

本地EN/DE×1440/390与原生权限/Trash/私有恢复/报告保留及按方案清理已通过；线上现有8207仅开合确认，EN1440/DE390控件/换行/焦点实走，原post及meta指纹相同。没有新建生产测试数据、没有对真实方案执行移除，实际写入行为依据同一部署源的本地/native结果。仅回填4个具名状态检查；其他账号状态及Save/design/draft/报告渲染不冒充完成。未变部分复用，不扩展已通过矩阵。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/account-saved-controls.json。SQL滚动保留8份，超窗072840旧SQL和被接替的671CSS恢复文件已淘汰，连同2个临时文件实测释放7921664B；当前SQL、原子前版、原account卷和官方CSS恢复点有效。本地用户46/方案8177及凭据已回收，原15用户/0方案/67询盘恢复，8888停止、其他端口保留，临时37/38关闭，原9保留，writer释放。完整目标ACTIVE；普通滚动可避让的叠层按业主裁定接受，后续继续优先处理实际功能失效、阅读/操作困难与加载瓶颈。


## 2026-10-26 · 已保存方案名称与操作引导已上线（673）

旧记录没有快照时，卡片现在沿当前Woo发布权限显示真实产品名和对应语言产品链接；已有快照原样保留。缺少原有计算凭据的记录显示重算说明和配置器入口，避免提供必败的加入动作；服务端失败留在已保存方案页，成功仍走原草稿链路。移除/撤销沿用672，不重复验收。未迁移历史记录、放宽工程凭据或改写营销正文。

PR673/source a0f781ada153249121fc7c59688e8e96a5159de6，main44109dcceef7ddbcd03f356c856e2f463ce92c4b，最终CI40330311286及源码/增量双审通过；原生20261026T133641Z-account-saved-guidance-a0f781ad已归档接受。官方Generate一次后，线上EN1440/DE390实际8207卡片通过，DE产品和已挂载配置器实际抵达；原post/meta指纹不变。其余运行时及54CMS正文/meta/配对/反斜杠保持，编译CSS与本地仅一条相同且不冲突的焦点规则排序不同。全4本地视图复用，不扩大生产矩阵；仅回填4条saved-solutions-populated具名检查，fresh Save→design→Add/报告PDF及其他未验状态继续开放。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/account-saved-guidance.json。本地用户49/方案8180、8181及凭据已删除，原15用户/0方案/67询盘恢复，8888停止。滚动保留8份验证SQL，淘汰084523旧SQL与被接替的672CSS恢复文件，连同2个临时文件实测空闲增加8093696B；新SQL/前版代码/原卷/CSS恢复点有效。线上已退出、39关闭、原9保留，writer释放。完整目标保持ACTIVE；业主再次确认正常滚动可避让的层叠可接受，下一步沿既有PDP HTTP性能证据定位实际瓶颈，已通过部分不重测。


## 2026-10-26 · 博客搜索关键词保留（待修）与公开清单校正

`blog-search-retained-query`：线上EN1440从博客搜索backup，实际GET返回4篇相关文章且H1显示backup，但journal-search.value为空。客户无法直接在现有词上修改查询。LC搜索input没有当前query值，唯一失败图journal-search-keyword-missing-before.png保留；下一博客搜索批次修复，不阻塞674性能发布。EN桌面首页、DE手机首页和真实主题→Batteriespeicher列表的初始排版/语言/字体/横向宽度已具名记录，其他视口、完整交互及整页仍待覆盖，没有宣称博客完成。

生产原生Woo/Polylang当前许可校核原214个商品记录：170个对客户公开，42个EcoFlow草稿，2个仅供工程引用的Trina记录；未发现清单漏掉的新增公开商品。88个宽度组合增加current_publication及非公开原因，不删除旧证据，也不免除撤权/历史消费者的义务。该字段只确定公开页清单适用性，不冒充逐URL HTTP验收。当前证据：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/publication-native-batch.json，first_coverage_during_ci / inventory_reconciliation。


## 2026-10-26 · 产品资料的原生批量读取已交付（674）

PR674/source215f38ee3aa7261580214beacc396630d03bea3c、main dece20908e61239950752410dad897b819e980ba、native20261026T143307Z-publication-native-batch-215f38ee已归档接受。每次独立刷新当前权限并查询原生候选后，沿WordPress原生_prime_post_caches批量取同一批post/meta/terms，减少逐产品查询；顺序、原文件/别名/版本/语言与事实源权限均保持，不加TTL。原生完整manifest、全站资料及英德单商品四组完整数组完全相同。单商品配对244.97→144.29ms、799→292SQL；线上安装后仍292/293SQL。

单次相同客户端/URL/flags HTTP首字节5.316634→8.545789s，同时TLS2.907314→6.435270s；握手后至首字节2.409173→2.110401s。不宣称本批整页提速、不追加好看采样。两份348390B HTML仅同一Genie根节点的请求时间和签名不同，其余字节一致；实际DE390六PDF列表/FAQ展开与原答案/字体及宽度通过。其余1343runtime文件、54CMS正文/meta/语言配对/反斜杠与CSS/卷保持；不运行Generate，不改营销文案。

最终CI40338226113及完整/夹具增量双审通过。初轮19个EngineeringFeed缺原生helper的夹具失败已定位：同一默认登记移入共用ManagedDocumentFixture，删除原处重复，运行实现不变；新失败20用例通过，其余有效结果复用。只回填8条具名状态/4商品视图的机制检查，整页和未覆盖状态不冒充通过。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/publication-native-batch.json。按窗口保留8份验证SQL，删除094510旧SQL和被接替的673CSS恢复文件，连同3个临时文件实测空闲增加8101888B；当前回滚只需原子前版673，CSS从未变动。未新建实例/工作树/测试文件或运行本地服务，40标签/视口清理、原9保留，writer释放。完整目标ACTIVE；下一批直接修既有B1/B2共享页脚9px文字/28.5px语言控件，复用原40视图审查和当前现场；博客搜索关键词保留仍在本目标内待修。普通滚动可避让叠层沿业主裁定接受。


## 2026-10-26 · 共享页脚可读性与联系控件已上线（675）

原B1/B2已关闭：法律/信任文字9→12px，语言按钮28.5→44px；相邻联系面板的标签9→12px、邮箱主地址10→14px，邮箱热区36.34→47.89px、复制28→44px、电话39→44px，联系标题链接也达44px。手机邮箱单列，复制按钮独立留白；保留玻璃配色、胶囊/面板结构、文字、目的地址及原生脚本。改动仅WindPress control-details.css和spec12，没有PHP/LC或营销正文改写。

source a3ff1d87365f1ac8471e6a58ac3aa37550e3102e、main b9c1aa922a5284205b9966e6120e0c996e1303d7、native20261026T153617Z-footer-readable-a3ff1d87已归档接受。访客本地EN/DE1440/390四个联系/页脚视图及实际语言切换、联系落地、hover和键盘焦点通过；线上EN1440/DE390同样通过，无横向溢出或复制/邮箱重叠。官方Generate本地一次、线上一次；编译新增仅11条预期页脚规则，其余有序CSS保持（同一条不冲突focus规则位置差已核实），其余1343runtime文件和54CMS正文/meta/语言配对/反斜杠保持。只回填四条globalfooter具名检查与四个承载页的共享检查，其余页面/面板/链路不冒充通过。

最终CI40346772636、源码与发布检查通过。唯一一轮CI依赖安装等待较长，未重启；REST进行中日志404、网页日志需登录，未绕过，公开进度已确认进入justtest后完成。发布检查发现归档重试阶段缺一合法状态，已单行修正并补审；不重跑原CSS/浏览器矩阵。相同Git树的main重复CI40350849310首次取消502，读回仍运行后一次重试成功，现已cancelled。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/footer-readable-controls.json。当前8份已验证SQL和一份当前CSS恢复点；超窗114829旧SQL及2临时文件淘汰，实测空闲增加8011776B。本地未新建账号/实例/测试文件，15用户/0方案保持，8888停止；本地/线上管理会话退出、41/42关闭、原9保留，writer释放。完整目标继续ACTIVE，下一批沿已经确认的博客搜索关键词保留缺陷，直接复用原生LC搜索词标签，不追加全站/性能采样；正常滚动可避让叠层按业主裁定接受。


## 2026-10-27 · 博客搜索关键词保留已上线（676）

`blog-search-retained-query`已关闭。英德journal输入框使用LC原生`lc_the_search_query`（原生esc_attr），保留既有正文、搜索/权限/分页与一般站内搜索。四本地视图可编辑重搜，德语引号及与号完整；线上EN1440实搜backup为4篇且输入保留，DE390空结果→Notstrom4篇→原德语文章通过。原失败图与失败观察继续保留，当前状态仅回填具名通过项。

PR676 source f7a9c8c34aa81f40b85247e3612625e6d6655287、main 0ae1e6dd0cbc2328bf2c4ad09d3dfe42a8cf09dc、native 20261026T162443Z-journal-query-f7a9c8c3已归档；CI40356241952与源码/发布增量双审通过。1344文件读回，52CMS正文/meta/配对/反斜杠不变；26LC仅2search正文变化，metadata/语言配对保持；官方Generate后CSS字节与675相同。重复main CI整棵Git树相同，已取消并读回cancelled。唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/search-query-retention.json。

等待CI时仅补既有未覆盖的EN1440/EN390/DE1440 Batteriespeicher分类主体与实际文章消费者，DE390旧证明复用；其余分类、整页和交互未冒充通过。8SQL保留，新SQL完整EOF核实，过期SQL/上一CSS恢复文件/PR临时正文共3件已淘汰，实测空闲增加7344128B；实例已停、临时43/44关闭、管理会话退出、原业主9保留。全站目标ACTIVE；普通滚动可避让的层叠继续接受，不重复覆盖测试。


## 2026-10-27 · 询盘草稿状态与输入保留已上线（677）

本批确认并关闭`inquiry-unsaved-quantity-send`与`inquiry-entry-navigation-loss`：旧脚本只拦正在更新，数量尚未保存仍能发送旧清单；真实Edit→Cart→Send及语言切换会清空4字段。现按Woo原始数量/processing共同阻止发送并显示英德提示，原生更新/失败/重试/还原继续沿既有机制。两编辑入口和原生语言入口用同一标签页一次性保留姓名、邮箱、公司、留言与同意状态；稳定原生认证上下文替代轮转nonce，服务器验证保留优先，回复信息摘要与恢复值一致。浏览器存储不可用时停留并说明；不新增服务接口、询盘或邮件。空草稿Edit隐藏，普通留言继续可用。

4本地布局、原生更新/0/移除/44pxUndo、当前最终Edit往返及英德返回通过，双引号/换行/反斜杠完整。线上EN1440/DE390为真实访客空草稿，输入保留与空入口通过；邮箱的DOM比较被隐藏，采用原始页面图核对，不把false比较计为通过。没有生产草稿写入或真实提交。原2个产品失败图保留，3个不合格工具截图明确排除后回收，没有以删真实失败换通过。

PR677 source c53011da225efb593f2989bb52b13c46e52ae7c7、main 33a1b13e242a4a791f0eceddffe93bfba53ef854、native 20261026T172528Z-inquiry-draft-c53011da已归档；CI40365732713、最终源码与发布增量双审、英德提示对抗评审通过。1344运行文件精确，54CMS与26LC正文/meta/配对/反斜杠保持；官方Generate一次，CSS完整有序规范化比较只增加提示规则，原生相邻等值选择器合并差异已解释。相同整树的main重复CI已取消。唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/draft-inquiry-flow.json。

仅回填19条inquiry具名检查与4page局部观察，未验真实提交/收件/完整页仍开放。8SQL和当前CSS恢复点有效，淘汰旧SQL/临时/无效截图7件，实测空闲增加6508544B。own8888停止，15用户/67询盘/0保存方案保持；未新建账号/实例/测试框架。全站目标ACTIVE；配置器c9825f23/schema5为另一线报告的交接，不等待、不复测或冒充其最终验收。


## 2026-10-27 · 登录必填引导与复选框间距已交付（678）

完整目标保持ACTIVE。确认并关闭`login-empty-wrong-credentials`与`remember-label-gap-overridden`：原生Woo登录表单带novalidate，旧增强脚本只return仍会提交空字段并显示账号密码错误；现用原生reportValidity并取消无效提交。Woo选择器覆盖原有flex使视觉间距约2.28px，现只提高原规则选择器优先级，原10px间距和44px点击行恢复。未新增或改写客户文案，营销、隐私正文均未动。

四本地EN/DE1440/390视图与必填用户名/密码、原生密码显隐、空找回密码及语言保留端点通过；线上EN1440/DE390实点空登录就地聚焦，无错误凭据提示、无busy，记住我为flex/10px/44px，德语手机无横向溢出。未实际登录客户账号、注册、重设密码、发询盘或邮件。既有注册和未影响布局结果复用，只回填11条authentication与4条page的具名局部检查；完整账号/邮件/重置链不冒充通过。

PR678 source15e6443ce694a10b255901fb07d78ef155eefc1f、main18e79d5be98c89c625ea1395cfdfcb8b3f23ff43、native20261026T182654Z-auth-required-15e6443c已归档；CI40374622131与完整最终源码/发布Spec及Standards通过。修改原有测试的真实novalidate夹具并先红后绿，仍为原29项，未增测试文件。1344运行文件精确，54CMS正文/meta/配对/反斜杠及26LC冻结；官方Generate一次，完整有序CSS只变记住我两个选择器、声明保持。对比工具首次将原源码声明顺序与编译顺序混比，已按唯一属性和值核对源码、编译前后仍严格保序；没有重编或重拍。相同完整Git树的main重复CI40377702762已取消并读回cancelled。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/auth-required-guidance.json。8SQL及当前CSS恢复点完整，旧SQL/上一CSS恢复点/临时文件4件已直接淘汰，实测空闲增加7340032B；本地8888已停、管理退出、临时46关闭、原业主9保留，无新增实例或账号。普通滚动可避让的叠放按业主裁定接受；后续以真实操作误导、状态、文案可读性和加载缺陷为重点，不为几何交叠重开重复验证。


## 2026-10-27 · 原生分页与手机搜索顺序已交付（679）

完整目标ACTIVE。关闭`native-pagination-current-unboxed`、`native-pagination-heading-visible-untranslated`和`site-search-mobile-sections-after-results`。真实404→站内搜索SAJ→第二页→切德语发现当前项只有9.6×20px、辅助标题直接露出且DE仍英文，以及手机分区入口因缺journal-content容器排到结果末尾并贴住分页。现补齐LC原生span.page-link的既有44px样式，在分页内保留隐藏标题的辅助阅读语义，6模板用原生screen_reader_text参数传Page navigation/Seitennavigation，2全站搜索分支恢复既有容器及手机顺序。不改PHP、查询、链接规则、营销或隐私正文。

初稿Standards发现真实specificity冲突，改为:where使.current状态胜出；记录初始失败和最终双审，不重跑未变PHP测试。四本地视图44px/深青白字/隐藏本地化标题/正确手机顺序/无横向溢出通过，原生键盘焦点、next→产品消费者通过；博客和英德System Design分类当前一页，确认无空导航；DE全站搜索无结果保留词且无多余分页。线上EN1440第二页→下一页→DE第三页/390→原DE产品通过，保持SAJ与页码。下一页首次DOM读太早只见URL，未把空数组当失败/通过；最终DE第三页10条实际结果和消费者已确认。

PR679 sourcefc85c1cc2d71b94a41f9c64f46d4b34513760d03、main5eae5f3a71ac30417e35f1315df5d372458d81ee、native20261026T192247Z-native-pagination-fc85c1cc已归档。CI40383991079、最终9文件及发布Spec/Standards、两标签对抗评审通过。既有TemplatesTest53项通过，未新增测试或框架。1344运行文件精确，52非LC CMS正文/meta/配对/反斜杠保持；26LC只有6正文目标变化，全部metadata/配对和其余20正文保持。官方Generate线上一次，完整有序CSS仅基础选择器与隐藏标题规则改变，current声明保持。比较器最初未规范化编译器逗号空白，已由不可变CSS诊断修正，没有重编或假通过；临时89KB缓冲已清理。相同完整Git树的main重复CI40386060135已取消并读回cancelled。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/search-pagination.json。只补20条state、实际承载page和6template的具名范围，不把站内搜索当全博客/全页/所有动态路径通过。8SQL及当前CSS恢复点完整，过期SQL/前版CSS/临时文件4件已淘汰，实测空闲增加7516160B；own8888停止，原15用户/67询盘保持，无新实例/账号/邮件，管理会话退出、临时47/48/49/50回收、原业主9保留。普通滚动可避让叠层继续接受。

产品页余下慢点有一次有界诊断：当前同URL客户端首字节4.36s、TLS2.46s；服务器自身请求首字节1.73s，原生产品正文0.63s。两次前端启动包装工具无有效结果后停止，不推导站点缺陷，不据此继续删缓存或造性能候选。保留有效数据和边界，既有性能修复不重复采样。后续按剩余实际覆盖和交付价值集中推进，避免围着已通过组件循环。

产品文档关系读取已由 PR715（source959d10e5、mainc98cf562）上线，native20261027T224730Z-pdp-read-959d10e5已归档并释放发布窗口。同一次读取只解析一次当前产品身份，下一次仍重新读取权威；已有18tests/125assertions和双审、完整PR CI及精确同tree的main复用均通过。同条件本地正文与文档输出hash保持，canonical调用1357→924、646→430；不宣称单次耗时证明稳定提速。线上PHP hash/语法/opcode刷新、当前原生文档读取与匿名英德PDP读回通过，共享Tools和CSS保持。当前数据库快照224641与上一版PHP保留；并行713的唯一上一版Tools已核319文件后存本机，过期201844快照已淘汰。cold页面真正耗时归因仍开放，未把该局部交付冒充全站性能完成。详见既有pdp-render-cost.json/read_cost_followup。

另一配置器线报告a706bde5已合入主线截至18e79d5b，p548原生模板/缓存已装入；共享Woo/材料/草稿/冻结报告合同未新增变化，仍是另一线负责的本地候选，不作为本批生产验收或等待条件。


## 执行收敛当前结论（2026-10-27，680）

反复完整检查与同树main重跑已由680的CI选择/证明复用机制收敛。真实main运行40398551168选择reuse并成功，63秒完成；原完整检查及未知变化的full回退保留。该结论只关闭重复CI缺陷，不关闭客户页面/功能未验项。当前视觉判断继续接受正常滚动可避让的层叠，优先处理真实阅读与操作困难。交付、失败修正和复用证明沿唯一ci-change-scope.json记录。


## 法律页纸面结果与旧交易流程表述（2026-10-27）

Imprint/Terms/Returns英德A4首次输出已验，Privacy有效结果复用；完整文本与14纸页已核，四条1440等价输出状态关闭，手机系统预览未由当前工具证明。证据：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/legal-print-coverage.json。其余法律页面状态不因纸面结果通过而关闭。

**P2 legal-online-ordering-stale，已于2026-10-27按业主报价约定事实纠正并上线（当前结论见末节）。** 实际EN/DE销售及退款正文仍称审批后开放线上下单、checkout为binding offer、结账显示VAT/运费和账号内正式发票，偏离当前仅询盘/Proforma、后续线下处理。已询问合同实际在何时成立，尚未收到，不猜测改写法律条款。原始现文已绑定六份PDF与DOM，不因打印技术通过忽略此引导缺陷。章节复制入口在窄桌面窗口为hover隐藏；真实touch媒体已有opacity规则，本次不将视口测试条件误判为手机产品缺陷。


## 2026-10-27 · 文档语言维护修复已上线，公开原件首次覆盖完成（681）

后台文档编辑器原先只提供空/en/de，保存现有DE/MUL/MULTI/EN/DE等记录时会把语言提交为空；类型列表也缺少证书、兼容清单和宣传册。已复用公共文档类型和语言词汇，保留实际存值与大小写，并由真实编辑器发现并修正原生选择框裁字。当前已上线：source5eec41126470ca4b1f1055b5c3a417bf8996fec6，mainbaa776bccd6406ee3ba4b7cfae5d72f1a7c84826，native20261026T222748Z-document-editor-5eec4112。一个运行PHP文件改变；其余运行文件、CSS缓存/卷、54处CMS正文/meta/配对/反斜杠及完整文档发布清单保持。真实线上5个产品的38条文档行读回全部正确，覆盖8种原存语言值，无生产产品保存或测试数据。

最终完整Spec/Standards与显示属性增量评审、原有六个测试和真实本地核心保存/原生控件验收通过，CI40410510248及main40412548610成功；同一连续独占写入期间直接沿用刚完成的读回归档，没有再次整站检查。新增SQL快照先由原生流完整性验证并核实哈希，超保留且无依赖的旧SQL已淘汰；目前8份SQL满足最近3份/每日7天/基线规则。临时发布器已回收，local实例已停止、临时产品/账号已删除，无新环境或测试套件。

公开下载页EN/DE的实际文件与页码引用集合相同。142份当前公开原件完整匿名读取均为正确PDF并匹配原件哈希，186条章节页码均存在，临时下载已删除；不是只测Range32，也未冒充全部PDF内容/规格、每页视觉、私有账号文档或整站已验。既有page/state只增记这一具名范围，不关闭其他pending项。新发现6份原件仍以Document泛名呈现，P2 document-generic-source-labels继续由本目标负责，后续需在保护工程引用/准备状态的前提下修正源元数据。法律页旧线上下单表述仍等待已提出的合同成立事实，未擅改条款。普通滚动可避让的层叠继续接受，不作为扩测理由。

唯一记录：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json。完整目标保持ACTIVE。


## 2026-10-27 · 原生文档消费者、型号权限性能与法律流程纠正已交付（682/684）

682 source099ef25ea8550991912960c9f4a6e9cbd9259387、mainae442a040fb9ddf8d12cbfb7f6211b0035feaf5c、native20261027T010723Z-document-source-099ef25e已归档。PDP现在沿用当前授权原件，同时保留各产品维护的标题、语言与排列；明确维护的类型优先，角色只在泛类/缺省时回退；移除未使用的竞争资料读取器。最终完整/增量Spec与Standards、原有34/10/6项相关测试及当前真实资料行对照通过，CI40429008805成功。原生文件、CSS、CMS和完整资料发布清单精确读回；空状态英德提示完成文案对抗评审。当前EN1440 PDP源码表现已实际复核。15份标签/类型修正曾在59产品写入后因知识库准备失败而准确回滚；不能把短暂候选图当作当前线上结果。document-generic-source-labels等源元数据问题仍开放，由本目标继续负责。

684 sourcea74c4200da35d923f27297ee758e660bffa03fcd、main522ca08974dbe61e3c0ab62fa4808c8df8ef8165、native20261027T025330Z-model-permission-a74c4200已归档。当前Woo型号权限改用原生批量关系读取和缓存预取，生产249标签有序/排序映射哈希完全相同，方法内查询2210→809；一次实际16KB识别请求200、3.81秒。该结果不是整站速度提升或完整知识库准备完成的证明。完整Spec/Standards与原有5+10项真实语义回归、CI40437111660通过，1344运行文件精确，源清单/文案/CSS保持。源码临时分支与执行器已回收，新增成功SQL后淘汰超保留1份，8SQL保留；当前实测空闲增加7262208B。

legal-online-ordering-stale现已关闭线上具名范围：业主确认“按每份报价中的具体约定”后，销售条款/退款政策1674/6825/1038/6698共18处旧交易流程描述已纠正，合同不再被写成网站结账即成立。其他权利、期限、责任、隐私及营销正文保持。完整原始HTML差异双审与文案初稿→对抗→定稿通过；复用既有原生配对事务保存和翻译基线，两组线上fresh readback与18处实际DOM文字/日期均通过。新文字本地EN1440/DE390及Returns交叉视图、线上四页对应视图无横向溢出/转义SVG裸文本；图标/章节/CSS及日期字串外JS保持，打印机制复用未变的有效结果，不声称手机系统打印预览已验。51其他受保护CMS正文/meta/配对/反斜杠及CSS均保持。已有完整备份+最新完整SQL经验证精确含四页前态，未再复制整站。

唯一记录仍为 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json 与 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/legal-print-coverage.json。原生字段精确回滚保留，own8888停止、临时浏览器关闭、视口还原；没有新增实例/测试套件/客户账号/询盘/邮件。全站目标保持ACTIVE；只关闭上述具名缺陷，不以本批局部通过关闭其他页面、首次视觉与全链未验项。正常滚动可避让层叠继续接受。


## 2026-10-27 · 索引发布门已实走，资料源更新仍须交付

15份元数据修正再次原生保存后，142PDF/解析缓存复用，实际New7263完整构建成功（12718chunks，662向量写入缓存），但原生activate返回CPE；失败清理删除了已完成候选，原stderr没有保留。已精确回退这批59产品的文档字段，fresh native manifest恢复Old61f（86products/144document identities），工程回执Old86ready，实际知识库Old85保持；英德法律页和682/684代码交付保留。

为直接隔离发布门而不再重算，已双审并执行当前有效Old61f索引的同源重绑定：只APFS克隆、更新version/epoch两条meta，保留全部资料及85准备产品，原生新lease/激活/实际loaded/ack均通过。当前版本20261027T042427Z-activation-12，epoch12，源/recipe/serving不变；原生两代保留生效。该结果只证明同源发布门实走，不能解释此前New失败，也不把未交付标签算完成。另一Old自动尝试14958已终止但阶段无记录，不推断成第二次构建或激活失败。

业主再次要求索引必须修好，回退不算完成。下一步先用此前实际native认证New7263快照离线准备epoch0候选，保持Old在线；开始/结束核Old源和型号映射，保留完成物及脱敏错误。候选完成后才保存同一批源字段，取真实New lease并严格核源码/recipe/serving/五字段，再原生激活/loaded/ack。仅具名必要准备和读回，不重跑全站、142原件或打印矩阵。仍沿/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json记录，不新增票或报告。完整目标继续，源标签与New知识库交付未关闭。


## 2026-10-27 · 资料源与新版知识索引已实际交付

当前结论替代上节“源更新仍须交付”：15项资料名称/类型/语言修正已通过59个产品的原生编辑保存，资料源726308c3…、知识库20261027T052229Z-candidate-13（epoch13）已真实激活、loaded并获原生ACK；原85个知识产品ID保留，工程服务实际200同源且86个产品ready。新版先复用142原件/解析和全部既有向量离线备妥，再提交同一源并取得真实lease发布；没有重复下载原件或追加全站矩阵。此前失败及首因未保留的边界仍保留，不将这次成功倒写成旧失败已查明。

当前线上EN1440 SAJ HS3产品页七份资料、DE390资料库保修筛选七结果已经DOM和原图复核，名称、类型、语言、图标、44px下载与无横溢出通过。营销/隐私/CSS未改；只给两个实际页面增加具名检查，其余待验项保持。三个临时操作器精确源码/SHA已在原记录保留后删除，实测可用空间增加720896B；原生只留当前/上一索引，无pending，生产writer已释放。另一Planner线的sync-feed权限修补保留，不以旧版本覆盖；对方将复用原生增量全备发布规划配置，本线不重复创建。

索引仍有与旧版完全相同的376条no_proven_passage关联，materialization_complete=true、preparation_complete=false；这不是本批新增，也不据此宣称全部可回答。当前继续用已有索引/manifest做窄诊断，区分共享资料按型号证明的合理排除与真实消费者缺口；不先重新构建。唯一记录仍为public-file-coverage.json，完整目标保持ACTIVE。


## 2026-10-27 · PDF型号证明缺口修复已实际发布（686）

已修：ESA原件的物理换行型号恢复、错合并行排除及min/dB数量误判；真实全量索引新增11型号scope且2323既有scope逐字保留。Genie运行时与索引15成对切换/loaded/ACK，新自动worker首轮exit0；EN1440客户回答10kW+原PDFp2实际通过。DE390人工验证码边界保留未验，没有用后台结果冒充。其余365 no_proven_passage关联继续开放，不能把本批成功写成全部资料可回答。完整证据沿用public-file-coverage.json/index_scope_correction；未重跑整站、原件下载或未变UI矩阵。


## 2026-10-27 · About 独有入口与德语手机标题

EN1440实际商业/大型储能章节及第三条原生FAQ可切换，末段报价进入Contact后保留Related page=About及Price & availability，未提交。DE390实际宽390/doc375，商业章节键盘选中与德语内容通过；H1 scene-title43px、宽339px，hyphens:auto把Speicherprojekte和einfacher拆成跨行片段，登记P2 about-mobile-heading-auto-hyphenation，原图about-de390-heading-before.png。此为既有独立问题，继续由同一目标后续修复，不绑入已冻结并通过CI的Capability689批次；未改正文、未把整页标通过。


## 2026-10-27 · 独立草稿未保存数量仍可离开

本地真实访客从现有商品6530进入独立/cart/，原数量1改为2后Update已可用，但右侧Send inquiry链接没有阻断；点击进入/proforma-request/后实际数量仍为1，页面未提示丢弃未保存修改。登记P1 standalone-draft-unsaved-quantity-continue；这是677询盘内组件保护之外的独立消费者缺口，不重开已经通过的内嵌原生数量旅程。现有guest空草稿用UI加入一个真实商品作夹具，生产用户的3件草稿未触动，未提交询盘或邮件；修复沿同一目标，原图和前后路由/数值保存在既有draft-inquiry-flow.json.standalone_draft_followup。


Capability controls — online accepted 2026-10-27 (PR689): existing two-story EN/DE control pair and scoped WindPress style published; actual EN1440/DE390 keyboard/rapid selection/next consumer agrees, targets≥44px, loaded images, no page overflow. Local four-view proof reused. Official Generate changed only six intended compiled rules; unrelated AST identical. Native rollback archived; privacy prose and29 backslashes preserved. Evidence: /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-marketing-correction.json capability_followup. This closes this bounded finding only; overall page/goal coverage is unchanged.


standalone-draft-last-remove-blank (P1,2026-10-27): deleting the final owned local item via native Woo UI completed the server removal, but returned cart composition contained only hidden pending hint and no empty guidance; header retained prior3. A normal reload showed the proper empty heading and0 quantities. Product cause not inferred from test tooling; compare base native conditional/shortcode timing next. Same evidence record draft-inquiry-flow.json.standalone_draft_followup.new_failure; not folded into unrelated690 release gate.


standalone-draft-unsaved-quantity-continue — accepted online 2026-10-27 (PR690/source493b9fa2,deploy20261027T111003Z-draft-quantity-493b9fa2). Final reviews/CI pass; native LC cart updated only, official WindPress generated, unrelated compiled rules identical. Actual EN1440/DE390 dirty continuation stays with update guidance; native activation focuses update. Existing server draft2/1 preserved after reload. Local owned native update→inquiry consumer EN2/DE3 and message bridge evidence reused. No production update/inquiry/mail. Native rollback archived; SQL retention and temp cleanup complete. Independent last-item empty-state issue remains #692. Evidence /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/draft-inquiry-flow.json standalone_draft_followup.


standalone-draft-last-remove-blank — source/LC/native-cache published and read back (PR692/source5bef4f51), ONLINE VISUAL PENDING: Work disabled browser before Generate and online visual. Existing WindPress official store published only the reviewed,locally compiled grid-column declaration into accepted production cache; all unrelated ordered AST equal,old source-map comment removed. No production Generate claim. Actual local ENlastRemove→empty+Undo→qty1 and DEzeroUpdate→empty reused. Native rollback files privately retained; priorCSS recovery protected until this gate closes. Scope remains in same goal.


2026-10-27 · Empty draft action spacing (695) accepted online: source15194fa7, nativeWindPressGenerate, EN/DE1440/390 all47px actions,primary/secondary12px16px padding,gap12px,nooverflow. UnrelatedorderedAST identical except reordering2unchangedindependent grid/textalign declarations from prior692store. AllCMS/templates andprivacy29backslashes unchanged. Rollbackarchived;1144fullcontains exactoldsource/cache so2duplicate temporaryCSS retired1768720B. Evidence remains draft-inquiry-flow.json.empty_native_followup.spacing_followup; native lastRemove/Undo online transition stillblocked byguestverification, notclosed byemptylayoutpass.

2026-10-27 · Document purpose metadata(693) delivered:57nativeproducts/466rows,90reviewedtype/roleedits,14unchangedPDFhashes,exactrawafter+othermeta/body/pairsguards passed;actualsource46172e73,index20261027T132159Z-730994000 epoch16 loaded/ACK85sales,engineering86ready.142parsecache reused/0parsed;12392vectorsreused/352new.positivechunkrows2349→2382,no_proven365→363. TwoGoodWe warranty originals still46no_proven associations because physicalpolicy names Series, notGW SKU. Manufacturerdatasheet/model/series↔policy series evidencechain proven forGW5K-ETA-G20; boundedconditionalclaimsprocedure capability staysOPEN. Do not treat purposemaintenance as warrantyentitlement or allindexcoverage. Full1144recovery39336files verified; interruptedpoint reused,pluginremainingincremental leg20.8s,10completefullbackups withinretention. Current record public-file-coverage.json.index_scope_correction.warranty_purpose_followup.


2026-10-27 · about-mobile-heading-auto-hyphenation — accepted online (PR697/source9f47424e,deploy20261027T135221Z-about-heading-9f47424e). Existing German manual-hyphen/balanced-wrap policy now applies to About scene titles. Actual DE390 font43px/width339px and DE1440 font68px/width790px show complete-word wrapping without overflow; all EN/DE body hashes unchanged. Native Generate, source/volume hashes, unrelated ordered CSS AST unchanged, privacy29backslashes intact. Both final reviews/CI pass; rollback archived and shared writer released. Before archive retirement,319 prior Tools files verified against complete1144 recovery. Unique pre697 compiledCSS retained; rebuildable afterCSS retired. Evidence production-marketing-correction.json.about_heading_followup. This closes this finding only, not every About state.


2026-10-28 · Conditional warranty claims procedure (699) delivered: main f58ebd2021aae78b8e892dfba13fed062ce761ef, index20261027T150851Z-candidate-17/epoch17 paired with runtime and native loaded ACK; actual worker41c8ee92cb39 first run exit0 retained the same index without a new generation. Actual EN1440 Genie answer identifies the original policy's first-contact distributor/installer and conditional service-portal escalation, citing original policy page2; no warranty duration or individual entitlement inferred. This closes the bounded semantic-answer delivery only. German filename citation label was open under704 at this read; it is now closed by the bounded704 acceptance below;339 no_proven_passage associations remain, materialization_complete=true/preparation_complete=false. Other language/UI states and full-page/full-goal acceptance remain unchanged. Evidence: [public-file-coverage.json](/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json), index_scope_correction.warranty_purpose_followup.conditional_procedure_candidate (delivery, actual_loaded, worker_rollout.first_run_readback, online_consumer).

2026-10-28 · Tested merge-tree CI reuse (700) accepted: main fbdbbf5762ea158dee57e9c9fc4a1ddac26b6900 actual push run40533598067 completed successfully, reusing successful PR check40529744469 after complete Git-tree identity verification; workflow/scope/success/marker gates remain. Native instance/full checks were skipped by that accepted reuse decision, not newly rerun. Owned sparse worktree retired and absence verified; observed free-space delta2301952B is not exclusively attributed to that removal. Evidence: [public-file-coverage.json](/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json), index_scope_correction.warranty_purpose_followup.conditional_procedure_candidate.ci_reuse_followup (actual_main_push, retirement). Existing coverage rows/counters and the ACTIVE whole-site goal are unchanged.

2026-10-28 · Existing DE390 numerical-answer gate closed: actual native New conversation, automatic verification and one submission returned GW5K-ETA-G20 maximum PV input power10kW in German, with original ESA datasheet page2 citation. Citation333.54×44px, document client/scroll widths390/390; final consumer frame inspected. Prior human-CAPTCHA failure remains preserved in public-file-coverage.json.index_scope_correction.consumer_acceptance.de390.prior_captcha_boundary. Existing staff browser context only; no guest-permission, all-model, all-document or whole-page acceptance. No inquiry/email/repeated submission. Current339 no_proven associations and704 warranty generic-label gate remain open.


2026-10-28 · Marketing audience/tool/topic controls (701) accepted online: main c8e5126c9233cc4de4511842f77fd7f0e28dce9a, source CSS7497b0c6…, CI40542287319 all pass, deploy20261027T165917Z-marketing-controls-def9896a. Official WindPress Generate1793120509/cachea62fcf59 and ordered CSS AST confirm only four reviewed insertions; other rules,8 protected bodies/meta/pairs,31 templates and privacy29 backslashes exact. Existing online receipt covers Services/Installer/EPC/Residential EN/DE1440/390: visible affected controls use14px, native selection/focus and corresponding consumers retained; Services targets≥44px, phone Residential choices stack and EPC ordinals remain together. Desktop Installer/EPC mobile controls are hidden and their font check is INAPPLICABLE; actual visible desktop tool cards/Configurator consumer and FAQ details keyboard/focus were verified instead. The16 page-context rows gain only this named bounded check; existing status/counters, other pending work and whole-page/whole-goal acceptance remain unchanged. Native rollback archive completed and production writer released; exact pre701 CSS recovery9c41 retained, superseded pre697 recovery4ab retired after hash/open-handle checks. Sole evidence: [production-marketing-correction.json](/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-marketing-correction.json), services_controls_followup.online_visual.root/related and compiled_style_comparison.


2026-10-28 · Genie original-document citation labels (704) accepted online and archived: deploy20261027T172810Z-genie-document-labels-0ae43574, integrated main fc29c661ec2092241466b4be1e8b7be693767805 preserves705 Planner/language changes. Source CI405404 and combined main CI40548403004 succeeded. Native319-file before/after guard and three public assets200/exact hashes/browser execution passed. Existing saved answer shows original document titles and page2 links without overflow in EN/DE1440/390; actual native EN1440/DE390 photos reviewed, known product/model label unchanged. This closes the generic filename citation-label gate only; four Genie page rows gain its named check. No new model request, form submission or email; remaining339 no_proven associations and other page/state acceptance remain open. Sole evidence: [public-file-coverage.json](/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json), index_scope_correction.warranty_purpose_followup.conditional_procedure_candidate.citation_label_followup (online_consumer, public_assets, native_archive).

2026-10-28 · P2 workspace-rail-close-hit-occlusion — RESOLVED in affected online scope by707. Original failure retained: native390/scrollY57.5 close toggle36×36 at x214/y39.5 hit NAV.lc-block.tv-nav-frame; keyboard Enter closure did not prove pointer closure, and704 had not changed the app/rail source. Merged6ec9ec0d5761e4eb99b30b2546e7e24f732ecde7 publishes only reviewed chrome.css091cb988eb9ed50992de1961e70a150b79c232450b034f093d06da5e235208f1; official WindPress Generate2026-10-28 02:57:03 was read back. Existing W.online_native proves EN/DE390 pointer open/close and reachable44px reopen; DEclose still works at scrollY892.5 and backdrop closes; EN/DE1440 admin/header/workspace flow retains existing36px controls. Real guestDE390 separately proves44px close/reopen, hosttop81/margin0px, expandedfalse/maskabsent after close and successful reopen. Only this defect and four named workspace checks close; all overall page/state counts/statuses and other pending Genie consumers stay unchanged. No workspace Escape promise or whole-Genie completion. Native archive is independently tracked by root in the parent receipt, not asserted by this online-check update. Evidence: [public-file-coverage.json](/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json), index_scope_correction.warranty_purpose_followup.conditional_procedure_candidate.citation_label_followup.workspace_rail_clearance_candidate.online_native (checks, official_generate, screenshot); existing workspace-rail-online-de390.jpg reused, no new tests/HTTP/UI/report.

### 2026-10-28 · General-search product link names —708 affected scope accepted

`search-product-thumbnail-accessible-name` is resolved for the affected server-rendered product links. The shared attachment's English description previously preceded the German product heading in the link name. PR708/source `d85c276901f1fa8fe4e36888b7ae548f878ce02f`, merge `a6cf057335265bf587372a7b2d8b919df82e6e36`, makes only product thumbnails decorative (`alt=""`) inside the existing titled anchor in LC619/6875. Local EN1440/DE390 each showed ten localized link names once, one image per product link and no overflow; the last-page nonproduct fallback and untouched nonproduct/journal alt branches retain their existing proof. Spec/Standards including the empty-alt delta and CI40566624007 passed.

Native publication `20261027T195157Z-search-product-alt-d85c2769` is accepted and archived: only the two HTML exports and corresponding LC bodies changed; all31 template metadata/pairs/titles/types, Privacy bodies/slashes, WindPress volume and compiled cache hashes remain unchanged. Actual online EN and DE AX each name ten products once; DE390 also proves single-image/empty-alt and no horizontal overflow, with `search-product-alt-online-de390.jpg`. The online EN exact viewport was not freshly confirmed, so this does not claim onlineEN1440; localEN1440 and unchanged679 layout/consumer proof are reused. Only four dynamic public-search rows and two search templates gain the named a11y check; their overall statuses remain unchanged. Whole search/page/query/permission/edge-state acceptance remains open. Evidence: /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/search-pagination.json → `product_thumbnail_alt_followup` (`local_browser`, `online_native`, `production_after`, `native_archive`).


2026-10-28 · PR709 确认页账号按钮颜色已发布，完整确认页仍未闭合。既有桌面按钮被 checkout anchor 规则覆盖为暗字；source310562e77908949add3441b34d4d4ef2527efe99仅将已有手机文字色覆盖移到共同作用域。最终Spec/Standards与CI40570160333通过；本地EN1440原生normal/hover/keyfocus均4.65:1，原生Enter到既有注册地址，未提交新询盘。生产官方Generate30.6s成功，公开CSS200/text-css/885843B/ee4f0cea5fb8832ebab13a48213373118760215f4eb89e66f097d120ea6da200；只含预期规则移动与等价display:none合并。31LC正文/语言配对、卷源文件、两隐私正文/各29反斜杠和员工草稿保持；原生20261027T201900Z-receipt-cta-310562e7已归档、writer释放。因没有存活且授权的生产合成确认URL，生产确认页最终原生视觉仍未证，不以公开CSS冒充此门。真实纯留言确认页的空表头/Notes对齐另在同一目标PR712处理；邮箱预填仅DOM布尔读数且有既有同类反证，分类为未验而非确认产品缺陷。精确记录：draft-inquiry-flow.json#newlocal_success_consumer.visual_findings.receipt_cta_contrast；不改任何整页pass状态。


2026-10-28 · 原生saved-design-report真实HTTP与账户下载已完成本地有界验收。复用既有真实EN/DE原件，不新生成；同一原生URL在所属pending/restricted客户下各200/原SHA/PDF MIME/private no-store，other与guest各403且无PDF，共6真实GET；另从普通pending账户Documents实际激活一次链接，原EN PDF下载SHA正确。不是CLI调用、生产或四视口账户视觉验收。8211/53/54及所有私有/下载临时副本已删除，15users/67orders/jobs0/164ASIDs/原options/cart/stock/sequence保持，无外部邮件/模型派发。四条design-report-pdf行只增加具名server权限检查并保留partially-verified；旧原件三页内容审阅仅复用其原范围，未宣称其他报告通道或打印完成。精确证据：draft-inquiry-flow.json#private_document_consumer_followup.design_report_gate。

2026-10-28 · PR712 Notes局部交付已发布并原生归档，完整确认页仍未闭合。最终source59204c66300bae6727ca17e50828a4bf7d18b495、main83419073e8ed62a62572a6913759d2b3347b199a，storefront.css974168d13cccf215a7f821ab48591c01f1708931f5857d9a44e7f90993490495；Spec/Standards及PR CI40587890562通过，main40588229641复用相同tested tree成功。原f378只证明机制/无溢出，root实看发现Notes粗体右对齐、label居中后未放行；最终974将原生Notes值恢复400/start/anywhere，label顶部对齐/25%/16px间距，仅空产品表隐藏thead，金额及actions排除。最终本地EN1440/DE390的空表/产品对照通过，root亲看三张原图PASS；其他既有视图只复用未变机制，不冒充本轮全矩阵视觉。原生20261027T214038Z-receipt-notes-59204c66已归档；官方Generate一次，生产公开CSS200/text-css/886413B/3c97ad2454d3917339f0dfd25d35e49393919eb0f2d08b5b935a24c99d676db7，仅三条预期Notes规则；匿名HTML实际链接同SHA字节，native browser CSSOM解析三规则。31LC正文/meta/语言配对、隐私、Tools及员工草稿保持。上述生产证据只关闭样式发布/加载/执行门，没有存活且授权的生产keyed确认URL，故不声称生产确认页实际视觉或整页PASS。仅四条inquiry:success-confirmation及共享模板6963增加712_native_receipt_notes具名检查，原总体状态保持。唯一证据：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/draft-inquiry-flow.json → newlocal_success_consumer.visual_findings.message_only_order_table。

2026-10-28 · 法律证据按当前版本收敛：44条legal状态保留各自实际消费者和来源指纹，不把Privacy单页交互推为全部8页。当前8篇WordPress正文/配对已只读核对，与已验1917完整备份字节一致；Privacy两篇完整hash仍与早期修复相同，Imprint脚本与既有实际paper记录相同，外部legal-navigation两源未变。Privacy英德双视口真实章节/复制反馈/本地化链接/保留章节切语，以及两条真实返回顶部、DEPrivacy系统预览、German writer三次完整字节保存均作为具名有界证据保留。Terms/Returns四篇10/27正文/日期更新后的当前PDF已完成：IAB3原生Page.printToPDF输出EN/DE Terms各3页、Returns各2页，110个当前正文阅读单元全匹配，10张实际纸页全审通过，无缺文/空白/越界文字/后台控件。首EN调用返回字节未落盘，已记录try局部作用域原因；一次必要的同调用导出并保存纠正后，每篇只保留1份有效当前PDF。已核旧新hash及无打开FD，滚动替换4份旧PDF和4张旧分页图，保留旧指纹/来源/正文更正证据，无额外全量备份。Privacy/Imprint纸面结果复用，因此pdf-complete-text与each-document-print-and-complete-text的EN/DE1440四条paper范围恢复passed；390四条仍partial，仅更新其当前A4正文具名检查，手机打印入口未验。新输出只证明实际A4 renderer内容/分页，不冒充OS系统打印预览；当时 TOC active-highlight 和完整文档集系统预览未验；2026-10-29 已对八篇英德正文逐篇在1440/390实际选择章节并读回当前标记，三种脚本族在桌面/手机视口另以真实滚轮核目录跟随；各篇两个视口均打开已加载 Chrome 原生打印预览后取消，纸面正文与分页沿用既有实际 PDF。仅接受具名交互，不作真机、访客或整页通过。证据 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/legal-print-coverage.json#legal_interaction_followup。另两处德语销售条款缺字已在 WordPress 原文证实并按核定范围精确恢复：`B2Bäufen`→`B2B-Käufen`、`B2Bährleistungsrechte`→`B2B-Gewährleistungsrechte`。PR755 source ae1157e9、merge e9e5667c、CI 40805906032 已通过；native pair 保持英文、其他正文和无关 meta，德语 baseline current。匿名线上页面与实际 Chrome DE390 显示两处正确字词，当前三页系统打印预览也含两处并已取消。先前完整 A4 PDF 保留为修正前历史证据，其余正文原字节不变；按裁定不重新导出。见 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/legal-print-coverage.json#terms_spelling_followup。未改源码/法律正文/生产数据，未新增实例/脚本/测试/浏览器截图；自有隐藏IAB页已关闭，Chrome未触碰。证据：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/legal-print-coverage.json（current_pdf_refresh）及docs/acceptance/2026-10-21/privacy-visual现有原始记录。


## 2026-10-28 · 覆盖归并与下一整批交付边界

已复用既有证据归并，未新开浏览器、实例、测试、截图或备份：C&I 三产品（EN6321/4106/3595、DE6599/6629/6654）的12个真实默认正文上下文已全挂到对应行，补齐此前漏挂的6个互补视口。原有“其他视口待看”是历史捕获时的边界，由后来互补记录补足；隐藏FAQ、图库、价格/角色与消费者仍独立保留。ESA的两处article用词、ETR兼容来源标识仍保持原失败记录，不因布局通过关闭。

88行已有具名默认正文或文章独有内容审阅从visual_review=pending归并为partially-verified，并逐行保留来源检查与实际范围；没有一行因本次归并变成全页PASS。其余交互/角色/隐藏状态、未观察区域及像素对照未由这些默认正文结果证明。40篇文章视口的旧独有内容阅读直接复用，不重拍。

博客新原生记录归入13个状态行，其中9个动作自身完成：4个英德双视口分享控件绑定正确当前canonical/本地化标题、44px与键盘焦点；3个实际空搜索结果上下文；2个桌面越界页本地化404与恢复。分享检查不包含第三方发送，站内没有文章复制按钮；不得把页脚邮箱复制误算作文章复制。EN390手机菜单、两语390的四个专题及DE1440页脚四面板加入具名部分结果；其余实际入口与分支仍保留。

下一批应按完整工作线组织，不按单个矩阵格重启验证：

1. 先完成当前已合并731整批的生产读回/归档；随后将已评审的账号错误输入保留与产品来源提示候选、ESA两处精确术语纠正集成下一候选。复用已有单测、原生输入结果和四视口兼容卡证据，只补真实变更缺口。
2. 将普通账号、注册/登录/重置、草稿/询盘/确认与文件权限作为一条客户链路收口。复用已验证的数量、删除/撤销、隔离Outbox及实际文件结果；生产访客Cloudflare300030和缺少授权存活keyed确认URL是具体未闭合门，不以本地/样式证据冒充线上消费者。
3. 工具、Genie、配置器、屋顶、项目备注、保存/报告/真实草稿消费者按已有独立负责人/共享接口交付；当前状态表仍有大量pending，先归并对方有效证据，再仅执行真实缺口。不能从源码存在、模型回答或一个工具截图推全链。
4. 产品与归档剩余首次覆盖按真实在售型号/模板族批量推进，复用共享机制与文件原件。84个无具名检查的产品视图全部属于42个已下架EcoFlow的历史EN/DE记录；这些是下架/旧入口否定消费者范围，不应当作在售产品正文重新检查。下架现值与实际公开入口证据未在本次读回，故未将其擅自标不适用。其余SKU的独有正文、未观察默认区块/隐藏答案和当前taxonomy解析仍需实际结论。
5. 导航/搜索/资料库/比较/法律打印与联系表单按实际消费者合并余项；31模板必须补真实绑定证据，已证明某条source/SSR不能使全部template PASS。法律当前A4正文与隐私保存/反斜杠结果已有效，不重导全部PDF；剩余手机触发/系统预览、未覆盖法律独立动作仍如实开放。性能按已有真实瓶颈前后结果复用，只有新瓶颈才追加采样，CI缩域候选独立并行，不用全站重测支付每次发布成本。

本次归并是证据台账纠正，不是新增产品修复或全站完成。完整目标继续进行中。实时计数（仅管理覆盖、不是完成量）：{"page_views": 708, "visual_review": {"partially-verified": 98, "pending": 609, "partial-with-finding": 1}, "state_rows": 1044, "state_status": {"pending": 851, "not-applicable": 2, "partially-verified": 163, "pass": 24, "passed": 4}, "templates": 31, "template_status": {"pending": 29, "partially-verified": 2}}


2026-10-28 · EcoFlow历史入口当前范围已核清：一次原生Woo批读确认68原对象全部draft且Publication允许0；当前EN/DE匿名StoreAPI搜索各200/0产品。对G的42个独立旧URL仅各一次匿名HTTP，41直接获得最终404；DE6591首次在本机代理CONNECT阶段503，保留该失败，仅补这个缺失路由一次即404。42最终均404，无鉴权Cookie/preview参数，不把staff预览200当公开泄露。对应84视口行的当前产品正文/交互不适用，旧捕获/原记录完整保留；不重复阅读已撤商品营销正文。

真实新发现仍开放：21个EN旧URL先301到DE草稿query，最后德国404。生产原生Core旧slug候选=6691/de/draft，过滤链只有GermanUrlMigration::old_post，原分支只修DE请求的外语候选而直接放过EN请求及同语draft。两文件候选现已在该原生filter统一要求published+请求语言，否则用同一_wp_old_slug限定重查；无目标留当前语404，不建立URL硬映射、不改产品状态。8888无任何数据/fixture写入前后：EN301→DEdraft改为直接404/en-US，DE保持404/de-DE；既有GoodWe DE历史301及opaque query完整，EN当前商品200/en-US。窄Unit8/8、WPCS2、PHPStan2通过；尚待root整批独立评审/CI/生产读回，不能将本地修复写成线上已解决。当前事实与原失败、各URL最终地址/SHA、钩子诊断、候选指纹沿用ecoflow-withdrawal-20261023/public-product-verification.json#current_historical_route_followup_20261028。既有Genie生产691无EcoFlow产品/资料链接及本地四视口拒绝引导只按其日期范围复用，本次没有模型调用。


## 2026-10-29 · EcoFlow 历史入口：后续交付更正

以上 2026-10-28 “两文件候选尚待交付”的结论已被后续证据替代，原始 EN 301→DE 草稿失败与早期本地修复记录保留。加强后的同一工作线已随 PR #734 合入主线：提交 `72d1bcf1be4cc1d47efb8c6bae14b00d78f3fda4` 是当前主线 `39e9d2f091c720a7d881c8829b82925041a666a9` 的祖先；当前主线两文件 SHA-256 分别为 `bc05daddc598e6c7bf50540f79ccc32f7ba75e35070af9d6dda765984a6f1169`（`GermanUrlMigration.php`）和 `842ebf7b0975520c11cf89b86036fcec787a7ea6b5903c95a328dee2aa4e7a9d`（`GermanUrlMigrationTest.php`），与既有 `spec_regression_followup` 候选完全一致。PR #734 的 plan、check 和 mu-smoke 均成功，CI 运行 `40661866024`。既有加强候选的 16 单测/68 断言、WPCS、PHPStan 和本地只读 Core 日期查询结果沿用；前一候选的本地 EN/DE HTTP 结果仍仅属于当时文件指纹，不冒充加强候选的重新运行。

后续生产具名读回记录于 2026-10-28 11:21 UTC：21/21 个先前受影响的 EN 旧地址匿名直接返回 404，均无 Location，未再跳往 DE 草稿查询。没有可用的线上已发布 DE 历史 slug 夹具，因此不能声称该有效重定向已获生产实证；既有本地结果及其版本边界保留。未新增测试、生产写入或全站扫描。证据：`/Users/chesterjohn/de-linker-data/ecoflow-withdrawal-20261023/public-product-verification.json#current_historical_route_followup_20261028` 的 `spec_regression_followup` 与 `production_readback_20261028`。


## 2026-10-29 · 产品参数图标和电压单位已上线

共享参数组件已随 PR740（446e5052；合并82dc43e5）通过完整CI与双评审并发布，原生部署20261028T174519Z-pdp740-446e5052已归档。4个展示文件更新，20种参数键沿WindPress样式映射；手机图标区分功率、容量、相位、重量、电压和化学体系，桌面保持隐藏。CHS2真实相位/电压文本补V，仅在同一产品原相位与额定电压完全一致且本地化展示未改写时应用。生产Staff Chrome中CHS2英德1440/390及真实语言切换、DE390单值电池对照均无参数行溢出；4组重量/容量仍分行，20px手机图标有实际mask，两张生产照片已由root审阅。Woo source36c5未变，5个保护文件未变，官方WindPress仅生成一次。该证据只覆盖具名共享组件，不升格为全部产品、访客或完整链路通过。

现有记录 integrated-736-production.json#next_shared_pdp_polish.production740 保存发布、数据库恢复点、当前编译缓存、5个浏览器上下文和回滚。复用1456完整备份中的原编译CSS/map，无新增全量副本。原字面未加引号选择器匹配检查不适应编译格式，保留其失败原JSON；20选择器及实际手机computed mask证明产物正确，未重新编译或重跑页面。工作树受pinned保护不能归档，保留源码并清理4553个可重建依赖文件，实际可用空间增加140181504字节（并发索引写入，非严格归因）。

CI计划任务稀疏检出提速独立随PR741完整CI通过并合入；实际计划检出约3秒，对比前轮约879秒，下游检查不减。知识索引受控发布仍在实际运行，未据此标记全站完成。


## 2026-10-29 · 知识版本已加载、恢复正常定时；语义覆盖仍未完成

受控发布实际终态 acknowledged/exit0：epoch28，index20261028T175850Z-103874000，source36c5，recipe8aed，serving0864。当前VPS路径与进程cwd均为/opt/linker-genie/20261028T153126000000Z，PID237154，service active；Woo/current manifest、native ACK与实际服务的85个产品ID及修订完全一致，142/142文档indexed，materialization_complete=true。正常Mac定时已改指向e328源码并复用1418锁定依赖；显式candidate root/src/ops导入与recipe/serving核对通过，首次launchd运行exit0，不强制重建相同来源。原plist和实际旧运行版本/索引恢复点保留，private writer已释放。

preparation_complete=false；324条no_proven_passage是文档×产品关联，覆盖62份文档和78个产品，不是324份未解析PDF。源角色归一后certificate141、manual77、warranty53、compatibility38、datasheet15；没有document_unparsed。下一合批并行推进受限证书证明和持久化发布韧性，不通过删除未知或扩大作用域制造全绿。

一次Chrome Staff EN Genie工作区新对话操作未通过保护验证，原会话保留，显示history与verification失败；控制台唯一相关警告为Cloudflare Turnstile Error300030，验证容器无iframe。未输入问题、未调用模型、未发询盘/邮件，未重试相同动作或绕过保护。因此本次只验收实际运行/原生来源一致性，不把它等同于客户完整回答链路通过。失败照片与具体范围沿integrated-739-production.json#post_release_browser_attempt保留。


## 2026-10-29 EPC FAQ 手机专题排版——744 已交付

德语第三专题在173px双列中被拆成短尾行，源为既有手机两列布局。744只在WindPress既有760px断点内把整个五专题组改为单列，正文、标签、原生选择与桌面保持原实现。已实际发布归档 `20261028T203121Z-epc-faq-777f26cf`；source/volume均6266278b，官方Generate一次后cache70778346（901482B）。线上Staff Chrome EN/DE 390各五项339px宽、49.59–52px高，无横向溢出；DE第三/End第五/Home第一的真实选择、对应答案和2px键盘焦点通过，EN实际语言链接落地后第三项通过。根已看两张线上原图。只关闭这一组件，整页/其余消费者状态不外推通过。既有记录 `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/marketing-copy-rendered.json#epc_faq_responsive_delivery`；浏览器读回 `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/744-epc-online-browser.json`。


## 2026-10-29 · 客户恢复体验 751 已上线归档

搜索词被误当筛选的空态和筛选清除丢失搜索词已修复；已登录找回密码重新使用既有认证卡，失败输入按单次恢复处理，正常请求不残留新的标识。PR751（b0cfd33；合并1ef69c11）完整CI通过，11个运行文件原生发布已归档，无CSS变更或Generate。实际线上英德1440/390分别检查两组件，Clearall去brand但保留q/sort，找回密码字段/按钮52px、间距12px和键盘焦点通过；无表单提交、邮件或重置密钥。原失败证据保留，生产303/有效key/访客/邮件不在此结论内。证据：/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/751-online-consumers.json 与 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/751-navigation-consumers.json#customer_recovery_delivery。

比较链路已确认产品链接到正确PDP，但一次加入动作被验证保护拒绝，原两商品数量2/1不变，未把该动作标通过。同名规格被覆盖及稀疏规格错列是保留在原记录中的真实失败；PR753（ad787565，合并3cd8788e，CI 40800839719）已修复、上线并原生归档。实际线上英德1440/390中，1832的3072 W与6530的60 kW、30 kW及原注释各在正确列；手机键盘横滚有效，德语滚至末列；德语1440移除首项后6530两条功率行保留，清空后回到空比较。只接受上述具名比较组件，不扩大为整页或加入草稿通过。线上证据 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/753-online-consumers.json；发布及恢复记录 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/comparison-integrity-browser.json#production_delivery。Genie保修配对epoch32已生效且正常定时noop通过；STS六个关联的完整生产源缺口仍在PR752修复，不以旧小夹具冒充线上通过。完整目标继续进行中。

## 2026-11-03 · 全站验收基线还原与 10-31～11-03 已交付状态归并

PR #862 清理工作树时误删的 `docs/acceptance/2026-10-22/full-site/` 下 8 个基线文件（`GOAL.md`、`findings.md`、`coverage-contract.md`、`blog-visual-review.md`、`inventory-baseline.json`、`template-matrix.json`、`state-matrix.json`、`page-matrix.json`）已从历史会话日志与本地数据快照无损还原，并将 `2026-10-31` 至 `2026-11-03` 已完成交付与生产读回的增量同步归入矩阵：

- **共享品牌/系列归档 34 根路径 × EN/DE = 68 物理 URL 已核实**（`docs/acceptance/2026-10-31/548/INDEX.md:1229-1242`）：`inventory-baseline.json` 中 39 条 `lang=false` term 记录对应的 34 个独立归档根路径（68 个 `page-matrix.json` 视口条目、5 对 `product_brand`/`pa_brand` 同 canonical 别名及 8 个筛选/排序/分页/空搜索状态）已完成生产匿名 HTTP 200 与 Chrome 1440/390 共享模板视觉/交互验证；`coverage-contract.md` 末尾 34 行清单、`page-matrix.json` 68 条记录及 `state-matrix.json` 的 `taxonomy-routing` 16 条记录已同步更新为 `partially-verified`。
- **GoodWe ET 与工商储电池 9 对 EN/DE 产品详情页（18 个商品 ID × 1440/390 = 36 视口条目）首轮覆盖**（`docs/acceptance/2026-10-31/548/INDEX.md:2537-2541`）：`1946/6799`、`1947/6800`、`1948/6801`、`6506/6589` 及 `1954–1958`（配对 `6802/6803/6809/6810/6811`）在 1440/390 下均返回 200、canonical 与语言正确、H1 匹配型号、6–13 份文档链接齐全、`scrollWidth == viewport`、懒加载后 0 破图；德语兼容标签英文回退已在 `a7440872` 补齐原生德语 PO/MO。
- **Thank You（`623/6873`）与德语 VNB 证书条款（`826/6869`、`749/6923`）成对内容发布与生产读回**（`docs/acceptance/2026-10-31/548/INDEX.md:2303-2348`）：基于共享完整恢复点 `cutover-20261101-2033` 完成成对事务写入与 LiteSpeed URL 刷新，匿名公开 GET 200 读回确认英德询盘链接及 `/de/blog/` 指向正确。
- **2026-11-03 生产客户全链路只读巡检及 `D1` / `O2` / `#868` / `#871` 生产修复读回**（`docs/acceptance/2026-11-03/customer-chain/README.md`、`docs/acceptance/2026-11-03/548/INDEX.md`）：
  - **D1 已修并线上读回通过（PR #874）**：DE 390 `/de/mein-konto/unternehmen/` 因隐藏 CookieYes `.cky-modal` 导致的横向溢出已由 `body .cky-modal { overflow: hidden }` 修复，生产部署（`main 7e2f6502`）并执行 WindPress Generate（`ver=1793704734`）后实测 `innerWidth=390, scrollWidth=390`。
  - **O2 已修并线上读回通过（PR #874）**：产品详情页切换 tab 时 `role="tab"` 按钮 `aria-selected` 恒为 `"false"` 的问题已修复，生产实测点击 `"PV input"` tab 后当前按钮 `aria-selected="true"`、其余兄弟按钮为 `"false"`。
  - **配置器 / Planner 状态门、表单回填与 ETR 导体对比全链打通（PR #868、PR #871、#548）**：`products/current` 顶层 `"prepared": true` 已随 planner release `08256b93...` 上线读回 200；PR #871 解决了搜索完成后残留 spinner 及刷新后 Equipment 表单未回填已存需求（`200 kWp / 61.4 kWh / 100 kW`）的问题；ETR 四机型（`6508–6511`）安装事实已落库并在生产配置器 UI 完整渲染 `Manufacturer conductor cross-section comparisons`（`50–70 mm²`）。
- **Genie 知识索引 `epoch 77` 只读取证审计与跨行表头型号解析修复（PR #876）**（`docs/acceptance/2026-11-03/genie/audit.md`、`span-fix-report.md`）：VPS 生产索引 `epoch 77`（`20261103T071623Z-963760000`）实测确认历史 `epoch 62` 的 20 条缺证关联已 100% 补证放行（`609/610` 条关联有证，4 条英德生产真问 Turn `723/725/727/729` 读回通过）；唯一新增缺证项 `1954 × doc-0ee8a88e...`（GoodWe BAT-C 手册第 80–83 页跨行表头 `0.0841 pt` 行距截断）已由 PR #876 在 `extract.py` 与 `table_projection.py` 修复并通过 2,945 条单测。
- **当前矩阵实时统计**：`{"page_views": 708, "visual_review": {"partially-verified": 236, "pending": 387, "not-applicable": 84, "partial-with-finding": 1}, "by_kind": {"page": {"partially-verified": 59, "pending": 40, "partial-with-finding": 1}, "post": {"partially-verified": 40}, "product": {"partially-verified": 67, "pending": 277, "not-applicable": 84}, "term": {"pending": 70, "partially-verified": 70}}, "state_rows": 1044, "state_status": {"partially-verified": 235, "not-applicable": 2, "pending": 771, "pass": 20, "passed": 16}, "templates": 31, "template_status": {"pending": 29, "partially-verified": 2}}`
