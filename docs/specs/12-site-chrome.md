# #12 站点外壳

## 改动清单
1. **页头与页脚**（LiveCanvas 页眉页脚模板，经 WP 后台或迁移脚本改）："Plan with Linker" 区块只剩两张卡：Genie（"Genie - Linker's AI assistant"，一句功能描述）与 Solution Configurator / Lösungskonfigurator（功能描述里包含 "Roof detail / Dachdetails" 一句）；移除 Site Detail 卡与链接；"Products" 菜单文案照旧。
2. **跳转**：`/design-canvas/` 与 `/de/design-canvas/`（及其德语别名）301 → 配置器页屋顶步（`/solution-configurator/?step=roof`）；配置器页自身地址依据业主 2026-10-12 裁定改为 `/solution-configurator/`、德语 `/de/loesungskonfigurator/`（不保留旧 slug；标题 Solution Configurator / Lösungskonfigurator），旧地址 `/linker-planner/`、`/de/linker-planer/` 一并 301。**2026-10-16（欠账 N14）**：页与工具两条重定向带原请求的查询串（此前丢弃——部署窗口实测 `/de/solution-configurator/?step=roof` 的 301 落到了配置器第一步）；map 自己的目标带查询（屋顶步）时以 map 为准，checkout 规则本就携带。落点 `plugins/linker-tools/includes/Redirects.php`。
3. **LiveCanvas 升级** 4.9.3 → 4.9.4（本地验证 `wp/v2/pages?page=2` 返回纯 JSON）。
4. **工具相关文案重写**：工具页标题、副标题、空态、按钮、提示、工具卡——每处单独写 EN/DE，对抗评审记录附 PR（AGENTS.md 文案规则）；营销十页正文不改。
5. **产品分类页筛选**接 #7 契约（相数、功率、用途、容量的 data-* 来自 SelectionFacts）。
6. **产品页模板**（新插件的 Woo 单品模板覆写，LiveCanvas 不参与。**2026-10-10 方向反转（PR #55）**：产品页与商城/购物车/结账/账户页改走 LiveCanvas 动态模板（lc_dynamic_template + is_shop_page 等 meta，官方 starter 底稿），归 #54——本项"LiveCanvas 不参与"与模板覆写的呈现本体已废止；#12 交付的机制（分类筛选、原生字段优先、门店文案）由 #54 的模板继续消费）：图库、简介、正文只来自 Woo 原生字段（维护人员在标准编辑器改了就生效）；关键数字来自 #7 契约；参数表来自产品属性与图值（`_tv_legacy_acf_json` 里的参数表/卖点在 #8 迁移时写入产品属性与一个 `linker_specs` 元框，之后只在标准编辑器维护）；FAQ 来自 #15 的字段；文档列表来自产品文档；按钮与价格按 #11；Genie 产品页芯片按 #13。EN/DE 由 #9 的德语对象提供。
7. **营销页交互**：五页内容模块增加桌面悬停切换，点击、键盘、触屏行为不变，不改文案。
8. **页头菜单图片**（契约 2026-10-14 修订，依据族 12 fixNote「缩略图空盒按 C8 缺图方向修线上菜单图片引用」，台账 `docs/debt/ADJUDICATION-2026-10-14.md` 修复队列）：面板与抽屉的缩略图**一律由自己的 `src` 解析**，没有水合契约——照片不得依赖脚本恰好在打开事件上把 data-src 换成 src（缺陷形态即 data-src 无 src，探针与一切非水合打开路径下都是空盒）。加载时机交给浏览器自身：桌面 mega 卡随 `loading="lazy"`、抽屉 rail 不带该属性，比例与清晰度不变、框体几何不动——这就是线上自身的标记形态（旧线上 DOM 检查点 2026-10-12，`.scratch/t16-lc-port/live/archive.html`：7 张 `src=… loading="lazy"`、5 张纯 `src`、全文档 0 个 data-src）。**2026-10-15 收口（清账决策 8）**：水合脚本 `menu-images.js` 与其 enqueue 已删除——评审 harness 实证 `src` 直解析在加载期即取图（13/13 loaded），脚本在无 data-src 时 inert，「移除旧通道前先证明新通道对等承载」已满足；`12-site-chrome.py` 的 `unresolved_menu_images` 守卫改为引号无关的 `src` 值正则（单双引号同判）。

9. **页头 EN/DE 同构（#229，2026-10-18 Claude 裁定及 PR #294 第 3 轮评审）**：德语保留完整导航与联系按钮，逐宽度折叠状态与英语一致，仅下述 Firefox 裁定边界除外。先改 WindPress 布局；只有布局放不下才经文案对抗评审缩短德语。英语与线上 1280/1440/1920/390 全页掩膜外差异数须为 0。Chromium、WebKit、Firefox 同跑 1276–1300 每 1px、1300–1940 每 10px、390 的 90 宽度扫描；分别断言运行时折叠属性、实际可见性、全部入口、CTA 和无重叠。
   - **CSS 路线**：既有 LC partial 已含全部入口，Woo 数据装配无需更改。边界区 1280–1287 保留第 1 轮规则；其上从容器可用宽度中减去三引擎最宽的零留白部分与有来源的安全余量，再分给六链接的 12 个 padding 面，向下取 1/64px，封顶英语 14px。无 PHP 布局、LC 标记或 `fit()` 语言分支。
   - **安全余量来源**：零留白四块宽度 Chromium/WebKit=1156.5625px，Firefox=1156.9166717529297px，实测 spread=0.3541717529296875px。预算 `ceil(最宽 + spread + 6 × 2 × 1px) = 1170px`，包含每个 padding 面 1px 的布局压力及向上取整余量。真实浏览器测试实际追加这 12px 压力，仍须完整展开；第 1 轮“加 1/64px 即折叠”测试由此取代。
   - **第 3 轮裁定边界**：[Claude 裁定](https://github.com/AssassinFlash/de-linker/pull/294#issuecomment-6244186438) 接受仅 Firefox 1283–1287 的 EN 展开、DE 折叠，原因是 Firefox 德语文字度量约宽 0.35px；消除这五个宽度的差异需要给 `fit()` 加语言耦合或削减更宽视口的德语余量。测试分别严格断言折叠属性与实际可见性的差异宽度集合等于 `{1283, 1284, 1285, 1286, 1287}`，集合增加或减少均失败，且验证上述方向；Chromium/WebKit 的集合必须为空。全部测试正常通过，无失败行、无 `xfail`。1288–1940 的扫描仍要求三引擎都一致。
   - **键盘修复保留**：关闭菜单的延迟焦点不得抢回焦点，每次打开只完成一次初始焦点；局部 `isOpen()` 统一读取展开状态。
   - 原始三引擎测量、安全计算、扫描表、截图及裁定变更台账：`docs/acceptance/2026-10-18/229/`；精确像素入口：`tests/visual/pixel-parity.mjs`。

## 验收
- [ ] 页头/页脚 EN/DE 对照截图（1440/390）；跳转 301 → 200。
- [ ] 配置器旧地址 `/linker-planner/`、`/de/linker-planer/` 301 → `/solution-configurator/`、`/de/loesungskonfigurator/`；旧工具入口（`retired_tools` 五条）直达新址（屋顶步带 `?step=roof`，一跳到 200）。
- [ ] 分类页筛选结果与旧实现一致或仅因 #7 的修正而变，逐件列出。
- [ ] 文案评审记录（每处：初稿、评审意见、定稿）。
- [ ] 产品页：在标准编辑器改图库顺序、简介、正文并保存 → 前台与 `wc/store/v1/products/<id>` 立即采用；只改价格不影响图文。
- [ ] 五页内容模块：悬停切换生效，键盘与触屏回归通过。
- [ ] 页头菜单图（EN/DE）：每张菜单缩略图有解析的 `src`、无 `data-src`（`12-site-chrome.py verify` 对页头两步校验同一形态）；关闭态与打开各面板/抽屉后照片均可见（无空盒），`loading` 属性分布与旧线上检查点一致（桌面 mega 卡 lazy、抽屉 rail 无）；页面不再装载 `menu-images.js`（脚本已随其 enqueue 删除）。

## 共享页脚可读性与操作尺寸

沿既有页脚设计，在 WindPress 的 control-details.css 收敛共享控件：法律、信任、语言与联系说明采用既有页脚导航的 12px 字级，邮箱主地址采用站点控件的 14px 字级；语言、联系、邮箱、复制和电话入口采用既有 control-height。手机邮箱卡片单列，并给复制按钮保留独立空间。原文案、目的地址、标签面板、复制脚本及法律/Cookie行为保持；现有焦点样式继续承载键盘提示，语言链接补齐悬停提示。不向 LC partial 或 PHP 增加样式通道。

## 产品文档列表的读取范围

产品页下载区只展示当前文档的标题、链接、类型、角色和语言，默认复用 Publication::library_read 的即时元数据投影，不为链接列表生成全部产品版本与准备状态。产品与源语言的发布检查保留，原 PDF 在打开时仍由现有门禁独立核验实际文件；引用事实与准备状态继续使用其原有完整读取。已提供的当前调用方快照与测试文档读取器不受影响。此变更保留列表内容、排序及页面呈现，不引入 TTL 或跨请求缓存。
