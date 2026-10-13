# PDP 与 FAQ 移动设计 · 2026-10-13

本线 `lane/pdp-faq-mobile`，从活跃仓库 `/Users/chesterjohn/Documents/de-linker` 的 `bbd5744` 切出；工作树 `de-linker-worktrees/lane-pdp-faq-mobile`。只操作 t109（8969），没有碰 t110、账户文件、Genie 文件、e2e spec 或页面/产品内容。**尚未达到完整交付门：products spec 4 passed / 2 failed，DE 商品仍为 draft；详见阻塞。**

## 1. 参照与对应

`ref-travel-app.png` 来源：业主 2026-10-13 晚提供的出行 App 12 屏设计稿（原图完整留存，未二次设计）。以下按三行四列标识，不引入旅游数据、评分或评价系统：

| 参照屏 | 我们的面 | 实现与证据 |
|---|---|---|
| R1C4 / R3C4 Details：头图、横向分段、底部左信息右按钮 | PDP | 全幅 300px 商品相册、44px 指示点目标、滑动与左右键；62px pill行；88px底部价格门+原 CTA。`pdp-en-ours-390.png`、`pdp-en-ours-390/` 每屏 |
| R2C1 / R3C2 Booking detail：图标+信息行 | PDP规格 | 主参数重排为 icon / label / value 三列卡，保留原参数值；`pdp-en-ours-390/02.png`。技术表同语言轻量行标，不新造参数 |
| R2C4 Help & Support：问询卡、搜索、联系两键 | FAQ | 本地过滤实际问题/答案/型号/文档；`faq-en-ours-390.png`、`faq-de-ours-390.png`；Contact Linker 使用现有页面解析器，Ask Genie 使用现有 `data-linker-genie-open` |
| R2C4 Frequent Question：chevron原生开合 | FAQ商贸/产品问答 | 全部默认收起，品牌组保留；`faq-en-expanded-ours-390.png`、`faq-product-answer-ours-390.png` |
| R2C2紧凑行卡与全局卡片分节 | FAQ文档 | 品牌分组下文件卡、类型/覆盖型号/语言/下载保留；`faq-documents-ours-390.png` |

390×844为主，430×932抽查；1440×1000桌面截图及 full 图分别在根目录。每屏序列按720px步进（844−124）保留重叠，非抽样几张代替整页。数值表与完整控制几何在 `metrics.md` / `metrics.json`。

## 2. 实际 FAQ 管线（不是猜测）

- `tools/faq/export.py:1–8` 只读每件产品旧问题；`generate.py:1–5,419–483` 调独立生成/复核并写 `docs/faq/<slug>.{json,md}`；`recover.py:3–21` 修复这些产品文案记录；`import.py:1–8,59–73` 把通过项写 `_linker_faqs`。**这四个脚本不生成 FAQ 页面 HTML。** 本线阅读并执行 `test_generate.py`，不重新生成冻结内容/不导入任何产品数据。
- FAQ 页为直接维护的 LC 导出 `content/livecanvas/faq_page.html` 与 `de/faq_page.html`；`Presentation/Templates.php:105–110` 分配到 `linker-faq` / `linker-faq-de`；`just present t109` 装呈现，不改 page post_content。
- 页面商贸问题是导出内现有16条，五个分类、问题与答案文本逐字保留（只换硬编码颜色类为 token）。产品问题与文档分别由 `LibraryPage.php:84–146`（现行行号见文件）调用 `DocumentLibrary`，现有class / data-brand保留。
- 新 `faq.css` 被 `WindPressVolume.php:127–130` 的**既有 glob 自动发现**，`present` 写入卷并导入 `main.css`，后台 compile产出。**注册文件零修改、没有新增注册条目，因此不与其它线共享注册处冲突。**
- FAQ唯一行为资产 `assets/faq-ui.js`；仅 `[linker_faq_help]` 渲染时入队，footer + defer + filemtime。无JS搜索框 hidden，内容/原生details不依赖JS。搜索为AND词匹配，大小写/音调折叠，清空恢复搜索前用户开合态；文档单独命中也计入 Matching entries，避免“无问题”掩盖文档结果。

## 3. PDP范围与桌面保护

- 两个语言模板只补同一 `[linker_pdp_price]` / `[linker_pdp_cta]` 的移动wrapper与FAQ锚点，没有改权限推导、SKU、价格或描述。原桌面CTA/价格位置不动，移动副本只在≤860显示，桌面副本只在桌面显示；两个短代码是纯a/span数据片段、无ID，复用同一缓存ProductView，非复制门规则。
- `pdp.css:1563–1618` 的新布局只在≤860；全幅头图、点选/滑动、参数卡、pill与固定条。已有PDP硬编码色值改为现有token别名，使本卷跟随站点palette而不再自立颜色权威；这会使少数桌面背景色随tokens变化，**未改1440几何**（主图仍813×640；页面边距40）。其余桌面内容布局、文案、展示顺序保持。
- `assets/pdp-ui.js:15–87` 选图同步主图/viewer，手机单指横滑（40px阈值避开纵向滚动）、保留点按钮和左右键；350ms时间窗只抑制拖动后的合成点击。实际bar高度经ResizeObserver写 `--pdp-action-height`，底部预留/坞偏移消费同一值；不改Genie内部。
- 最后发现真实实例只加载快照旧PDP脚本，其同名handle覆盖本线。`ProductShortcodes::pdp_gallery_pair()` 最小重新注册既有handle为本插件版本，依赖仍沿用handle、不留双事件读者。实测DOM只有一个 `linker-commerce/assets/pdp-ui.js`；`--pdp-action-height=88px`，ArrowRight实际选择Product image2。未动旧插件文件。

## 4. 检查与真实结果

从本线根目录执行，未改任何e2e spec：

- `just up t109`：成功重锚本worktree；版本提示本实例LC4.9.3（pin4.9.5），未reset。
- `just present t109`：初次拒绝 stale；按既有工具 `just wp t109 linker-commerce present --allow-stale --user=1` 写卷，再 `just windpress-compile t109` 成功。最终原样 `just present t109`：`templates: created 0, updated 0, unchanged 14`；`windpress: cache is newer than the templates/tokens and contains the template classes`；`Success: Presentation installed.`
- `just serve t109`：起engine8970与Genie8971（仅本实例）。
- `node --test plugins/linker-commerce/tests/js/{faq-ui,pdp-ui}.test.mjs`：5 tests / pass5 / fail0。覆盖纯过滤、空/多词、文档单独匹配、清空状态、缩略图/viewer一致、横滑不弹viewer、纵滑不选图、无合成点击后下一次激活。
- `/opt/homebrew/opt/php@8.3/bin/php plugins/linker-commerce/vendor/bin/phpunit -c plugins/linker-commerce/phpunit.xml.dist --filter 'LibraryPageTest|ProductShortcodesTest|ProductViewTest|CommerceStateTest'`：`OK (18 tests, 59 assertions)`。
- 同PHP执行 `vendor/bin/phpcs -q --standard=plugins/linker-commerce/phpcs.xml.dist` 指定两个改动类和LibraryPageTest：无输出exit0；PHPStan指定ProductShortcodes/LibraryPage：`[OK] No errors`。
- `uv run --locked --project tools/faq pytest tools/faq/test_generate.py`：`9 passed in 0.03s`。
- `msgfmt --check ...de_DE_formal.po -o ...de_DE_formal.mo`：exit0，新增5个UI字符串在 `.pot/.po/.mo` 同步。
- `rg -n '#[[:xdigit:]]{3,8}\b|rgba?\(|hsla?\('` 指定改动HTML/PDP/FAQ卷：无匹配（rg1）。“透明”/currentColor与color-mix引用token，不新增硬编码色值。
- `node docs/acceptance/2026-10-13/pdp-faq-mobile/measure.mjs`：exit0，全部9面无横向溢出；可见指定触控目标PDP15/FAQ-EN33/FAQ-DE23，≥44px；EN库272产品答案+16商贸问题+159文档，初始0 open；关闭JS同数且搜索hidden，键盘Enter开合通过。
- PDP真实浏览器触控事件：`actual browser swipe: Product image 2 viewer=false`；`pdp-swipe-ours-390.png`。不是仅用单元测试替代滑动。
- FAQ入口独立浏览器：`FAQ contract count=1`；点击后 `entryExpanded:true / mount:true / visibleMount:true / loader:true / error:undefined`，`faq-genie-ours-390.png`。Browser Use两个角色定位click超时，随后独立真实浏览器同契约按钮验证成功，不把前两次误报PASS。
- `just e2e t109 specs/products.spec.ts` 最终：**`2 failed / 4 passed (22.6s)`**。EN三项全过；DE访客一项过（但目标页404，不能算DE产品页已验收）；DE列表缺Anwendung、0产品；DE批准目标Page not found。

## 5. 文案与完整差异复核

新增功能文案走 `__()/esc_html__/esc_attr__`，既有商贸问题及营销长文不改事实。DeepSeek官方flash独立首轮文案反对“on file”歧义与重复Contact CTA，已改为 `Find answers and product documents.`、简洁空态；EN先行、DE自然Sie措辞。

第二轮文案审稿给出“English没有Sie”“Search是noun而德文verb”“Contact可能是noun”等阻断：这些是语法误读（英语Search/Contact均可为祈使动词，英语没有Sie区分），未据此改坏既有标签。完整Spec/Standards复核同时核过实际EN/DE全文；有效意见修复：文档计数、滑动点击时间窗、选图aria-label、行动条动态高度。误读“help位于About闭合区”“存在双h1/重复ID”经全文、DOM、短代码证明不成立。后续全量复核两审均pass，未用轮数代替清债。最后PDP脚本接线后再次全量复核：Spec `verdict:pass, findings:[]`，Standards `verdict:pass, findings:[]`（官方DeepSeek flash两个独立调用；本轮工具实际输出）。

## 6. 环境阻塞（未越界改数据）

1. 主会话已通过既有9-i18n补孪生，但 `just wp t109 eval` 实读6530的DE6606是 **draft**，4107的DE6669也是draft。公开DE PDP404；DE列表0产品；真实DE FAQ只有16商贸问答、0产品答案/0文档。因此没有合格的DE PDP截图，也不能宣称DE产品内容未丢已实页验证。EN全量保留与DE模板/i18n已施工；DE真实动态内容缺失仍需主会话处理，**本线没发布/造页面**。
2. 全105件发布在售商品 `Faqs::of()` 都为空， `_linker_faqs` 尚未导入；PDP FAQ段无法真实取证。FAQ独立页272答案是DocumentLibrary现有旧字段回退，不新造。
3. 本线用户 `pdp-faq-pending/restricted/approved` 按指定meta创建，待审/受限UI不漏价；批准CTA显示原“Add to solution draft”，但旧快照 **terravolt-b2b-core** 的 `woocommerce_get_price_html` hook（WP-CLI实读priority20 `tv_b2b_filter_price_html`）把批准用户价格替成“Net prices after account review”。Woo edit值真实存在（GW60K635、SAJ1680），**不是价格字段为空**。批准点击草稿实际0项。因此四态完整价/加草稿门未通过，未改业务规则或旧插件。
4. 不推送、不生产部署、不合并；本线提交仅供主会话整合复核。`metrics.md` 是诚实量测并含上述GAP，不代表整体验收绿灯。
