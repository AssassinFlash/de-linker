# 博客静态视觉独立复核

2026-10-22，Spec 只读复核。已逐张打开 **20 个文章 URL × 1440 / 390 = 40 张原始截图**，检查整页的页头、封面、标题与正文、段落分隔、文章末尾、侧栏与页脚；没有以 `overflow=false` 或共同模板替代逐页看图。产品源码、矩阵与 findings 未修改。本文件是本次唯一新增输出。

结论：这批截图未见隐私页式代码泄漏、文字与图形重叠、正文裁切、封面缺图或明显拉伸。文章主体的衬线标题、无衬线正文、章节层级与阅读列基本成立；仍有 **2 项 P2、2 项 P3** 细节需要处理，因此不能把整批标为视觉全部通过。静态图不能证明交互通过。

## 当前处理状态（2026-10-26，675）

B1/B2由675共享页脚修复关闭；当前真实本地四视图与线上EN桌面/DE手机、字号/热区/跳转及编译CSS范围证据见 /Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/footer-readable-controls.json。下文40张原图与原始失败结论保留；本增量只关闭共同页脚缺陷，不把旧静态截图或其他文章交互扩大为当前全页通过。

## 证据身份与边界

- 输入：[render-20261021T191808788Z-d88d10cc-post-0-20.json](render-20261021T191808788Z-d88d10cc-post-0-20.json)，40 个视图，20 个 URL，EN / DE 各 10 篇、各 20 个视图。
- 版本证明：[version-20261021T191808788Z-d88d10cc-post-0-20.json](version-20261021T191808788Z-d88d10cc-post-0-20.json)。采集窗口为 `2026-10-21T19:18:08.289808+00:00` 至 `19:20:07.727896+00:00`；前后 release 均为 `20261021T183520720401Z-4f722c26`，`sameRelease=true`、`sameRuntimeBytes=true`。
- 版本证明记录的原生 WindPress CSS 为 691925 字节，SHA-256 `194535313d6f678d121d96107e8402ebba9e766f78b6887355b23617f3f4ac7b`。本次独立重算 render JSON 与 40 张图片的 SHA-256，**41 / 41 与该版本证明的绑定摘要吻合**。
- 该证明将实际线上包、原生 CSS 与采集时间夹定；它自己明确未逐一记录浏览器收到的 inline / external asset response bodies。本复核不扩大它的证明范围。
- 以下结论针对上述固定采集版本，不是当前未提交 Genie header 修复或后续构建的上线读回。没有开启浏览器、执行点击、提交表单或写生产。
- 本批正文未出现实际可见的表格、嵌套列表或正文内图文对照表；仅有标题、段落、链接、封面，以及 Hybrid 页的分节和检查提示框。**表格与列表的真实阅读状态没有被这 40 张图覆盖，仍需针对真实内容补证，不能以 CSS 存在判为通过。**

## 可操作发现

### B1 · P2：手机页脚法律与信任入口仍缩为 9px

**适用：20 / 20 个 URL 的 390 视图；1440 视图同组文字为 10px。** 文章正文 16px、主导航 12px，而页脚的 Imprint / Privacy Policy / Cookie settings、德语对应词以及 Product fit / 产品适用性等入口变成很小的一排灰字。390 原图在正常比例下明显难读。德语虽然正确分为多行，没有被裁掉，但字号仍然过小。

截图证据：[EN C&I 390](screens/20261021T191808788Z-d88d10cc-post-0-20/6f85d40dcdbc-390.png)、[DE 备用电池选型 390](screens/20261021T191808788Z-d88d10cc-post-0-20/d65f497b8fa8-390.png)；其余逐页页脚也已看过，同样成立。

对应源码：`plugins/linker-commerce/content/livecanvas/partials/footer.html:93`、`:97`，德语 partial 同行；桌面来源为 `:55`、`:59`。建议在 WindPress 中给这组客户入口复用至少 12px 的既有页脚正文尺度，允许自然换行并保留间距。**法律与 Cookie 入口已经在 `control-details.css:87` 获得 44px 最小高度，本项是可读性问题，不是“链接热区仍不足”的结论。** 对比度数值未测，不将灰色观感报告成对比度标准失败。

验收：EN / DE × 390 / 1440 正常缩放原图可读；德语长词不拆成碎片；不依赖缩小字号挤进一行。实际热区、键盘焦点与目的页另行验证。

### B2 · P2：页脚语言切换未跟随 44px 控件尺度

**适用：所有 40 个视图中的页脚语言分段控件，手机更明显。** 英德标签在小胶囊中仍明显小于相邻的产品与主导航入口；手机 English / Deutsch 或 Englisch / Deutsch 使用 10px 字，源码最小高度 28px，桌面为 32px。新修过的其他页脚控件并未覆盖这组入口。

截图证据：[EN 交付文档 390](screens/20261021T191808788Z-d88d10cc-post-0-20/108ace62c437-390.png)、[DE 远程监控 390](screens/20261021T191808788Z-d88d10cc-post-0-20/b7285910a766-390.png)。对应源码：两个语言 footer partial 的 `:16`、`:70`；当前 WindPress 没有这组选择器的 44px 覆盖。

建议仅扩大 `.tv-footer-lang-seg a` 的语言入口高度和字级，沿既有胶囊样式处理，并复核手机首行 Logo 与语言组的排布。截图和源码足以提出这个漏项；**实际边界框、切换后是否保留同篇文章及当前语言状态仍 pending**，本次没有将切换功能判为失败或通过。

### B3 · P3：首尾文章展示了没有目标的相邻文章栏目

**适用：C&I EN / DE 的“Previous post / Vorheriger Beitrag”为空；Hybrid EN / DE 的“Next post / Nächster Beitrag”为空，两个宽度均可见，共 8 张图。** 仍保留栏目标题和半幅空白，使读者看到一个似乎尚未装载完成的导航位。没有目标本身正常，空栏目无需继续显示。

截图证据：[C&I EN 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/6f85d40dcdbc-1440.png)、[C&I DE 390](screens/20261021T191808788Z-d88d10cc-post-0-20/2dd66b9a9546-390.png)、[Hybrid EN 390](screens/20261021T191808788Z-d88d10cc-post-0-20/df27f2596657-390.png)、[Hybrid DE 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/5a8c1d604c81-1440.png)。

对应源码：`plugins/linker-commerce/content/livecanvas/blog_single.html:20` 与 `de/blog_single.html:20` 无条件输出两个标签，原生相邻链接为空时标签仍在。建议保留原生相邻文章数据与语言规则，仅隐藏无 `<a>` 的那一组，并让剩余组自然占位。没有从截图推断任何现有链接指向错误。

验收：EN / DE 第一篇、最后一篇与中间篇都看图；零目标时无空标签，一个目标时布局完整，两个目标时原样可读。点击目的文章、返回和语言保持另验。

### B4 · P3：Hybrid 两篇的嵌套首标题叠加留白

**适用：Hybrid EN / DE × 1440 / 390，共 4 张图。** 这两篇的首节与分隔线后的标题明显比其余文章疏离；青色检查提示框上方留出约 72px 空带，而其内容左右内距约 24px。手机中提示框因此像是先出现一块空面板，随后才出现标题，并增加了重复滚动。

截图证据：[Hybrid EN 390](screens/20261021T191808788Z-d88d10cc-post-0-20/df27f2596657-390.png)、[Hybrid DE 390](screens/20261021T191808788Z-d88d10cc-post-0-20/5a8c1d604c81-390.png)，桌面相同结构也已查看。像素距离为目视约数，不冒充 DOM 实测。

对应源码：`plugins/linker-commerce/content/windpress/blog.css:36` 给全部 `h2` 48px 上边距；`:45` 的 comparison grid 另有 24px gap，`:47` 的 check 容器有 24px padding。`:35` 只清理正文直属第一个子元素，无法清除 `.linker-article-topic` / `.linker-article-check` 内部第一个 `h2` 的上边距。建议只收敛这两个语义容器首标题的上边距，保留现有段落、分隔线和青色检查框；不改正文，不扩为全站文章改版。

验收：这两篇英德桌面手机的首节与检查框从顶边到文字的距离与其余既有阅读节奏一致；普通文章的章节间隔与段落节奏不变。

## 逐页看图记录

每一行的 1440、390 链接都已实际打开原图查看整页。**B1 / B2 为共同页脚发现，逐行均适用；“未见个别缺陷”仅指该篇正文、封面与文章导航，不会抵销共同问题。** 所有行的 hover / focus / 点击 / 文件 / 搜索及分页行为均为未验。

| 页面与语言 | 1440 原图与实际观察 | 390 原图与实际观察 | 该篇发现 |
| --- | --- | --- | --- |
| EN · [C&I storage planning](https://de-linker.com/ci-storage-peak-shaving-backup-scalability/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/6f85d40dcdbc-1440.png)：两行大标题完整，现场照片居中保留纵横比；四节标题与正文层级清楚，左右 rail 未侵入阅读列。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/6f85d40dcdbc-390.png)：标题三行、章节自然换行，CTA 全宽且文本完整；封面位于标题前，白色阅读面板接缝完整。末尾左侧仅有空 Previous 标签。 | B1、B2、B3；正文未见个别裁切或堆叠。 |
| DE · [Heimspeicher für Notstrom auslegen](https://de-linker.com/de/batteriegroesse-heimspeicher-notstrom/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/d65f497b8fa8-1440.png)：标题长词完整，白色电池封面边缘可辨；四节对齐，相关缩略图与文章列分开。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/d65f497b8fa8-390.png)：Notstromversorgung、Autonomiefaktor、Nutzungskapazität 均完整，无中间硬断；两条下载/项目文字链接换行可读，前后篇均有正文标题。 | B1、B2；未见个别正文或标题缺陷。 |
| DE · [Fernüberwachung nach Installation](https://de-linker.com/de/fernueberwachung-nach-installation/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/b7285910a766-1440.png)：两行标题完整，黑色设备封面居中；四节内容与长正文链接留白一致。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/b7285910a766-390.png)：Systemoptimierung 自然落到下一行；正文 RS / 连字符词组可读，CTA、相关文章、页脚顺序完整。 | B1、B2；未见个别正文或封面缺陷。 |
| DE · [Gewerbespeicher planen](https://de-linker.com/de/gewerbespeicher-lastspitzenkappung-notstrom-skalierbarkeit/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/2dd66b9a9546-1440.png)：Lastspitzenkappung 大标题完整，最长正文仍保留独立章节；纵向封面采用 contain，没有拉宽。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/2dd66b9a9546-390.png)：四行标题中的长词完整；Geschäftskontinuität 章节完整，链接第二项自然换行。Previous 栏为空。 | B1、B2、B3；未见单词碎裂或正文遮挡。 |
| DE · [Heimspeicher: Notstrom und Eigenverbrauch](https://de-linker.com/de/heimspeicher-notstrom-eigenverbrauch/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/37778289c476-1440.png)：长标题两行，现场电池图保留完整比例；四节标题没有与段落相贴。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/37778289c476-390.png)：Systemerweiterung 在标题行内完整，正文多段不重叠；两列相邻文章链接均可读。 | B1、B2；未见个别正文或导航显示缺陷。 |
| DE · [Hybrid vs. AC-Speicher](https://de-linker.com/de/hybridwechselrichter-vs-ac-speicher/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/5a8c1d604c81-1440.png)：三行标题完整；分节与检查框层级明确，但首节、分隔线后及检查框顶部空白突出。Next 栏为空。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/5a8c1d604c81-390.png)：五行标题在真实连字符处分行，未将 Wechselrichter 硬拆；检查框文本可读但上方空带明显，Next 仍为空。 | B1、B2、B3、B4。 |
| DE · [Innen- vs. Außenbatteriespeicher](https://de-linker.com/de/innen-vs-aussen-akku-planung/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/f1340b71ed38-1440.png)：室外场景封面保留原比例；长二级标题未截断，文章列与侧栏分隔明确。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/f1340b71ed38-390.png)：Außenbatteriespeicher 整词落在标题单行；正文温度负号可见。下一篇末尾 » 单独落行，内容未缺失，记录为低影响的换行观感。 | B1、B2；» 孤行作为 B3 同组相邻导航的验收细节，不另列缺陷。 |
| DE · [Wechselrichter und Batterie kombinieren](https://de-linker.com/de/installateur-checkliste-wechselrichter-akku/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/ef714dbde255-1440.png)：三行标题与 byline 分开；产品图未拉伸，正文两段的上下节奏成立。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/ef714dbde255-390.png)：五行标题完整；Kommunikationsprotokoll 和 Inbetriebnahmereihenfolge 两个最长小标题仍为完整单行，未越过正文列；末尾两条文字入口清楚。 | B1、B2；未见个别标题或正文缺陷。 |
| DE · [Dokumentation vor Projektübergabe](https://de-linker.com/de/installateur-uebergabe-dokumentation-checkliste/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/e16972ff9c9e-1440.png)：大标题两行，纵向产品封面居中；长章节名与正文完整，相关文档文章缩略图已见。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/e16972ff9c9e-390.png)：四行标题、两行最长章节标题都完整；Download-Center 链接分行可辨，不与 CTA 混在一起。 | B1、B2；未见个别正文或封面缺陷；文件行为未验。 |
| DE · [Gateway, Zähler und Cloud-Überwachung](https://de-linker.com/de/kommunikationsschnittstelle-zaehler-fernueberwachung-datenebene/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/7bc15a162038-1440.png)：两行长标题完整，四件设备拼图未拉伸；三层架构分节与正文对齐。下一篇文字后的 » 单独落行，未缺文字。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/7bc15a162038-390.png)：四行标题自然分行，Überwachungsarchitektur 整词位于第二行；长正文词组可读，Genie fragen 链接在词间分行，分享与相关入口完整。 | B1、B2；» 孤行作为 B3 同组相邻导航的验收细节，不另列缺陷；Genie 消费者未验。 |
| DE · [Solar-Speicher in Betrieb nehmen](https://de-linker.com/de/solar-speicher-inbetriebnahme-checkliste/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/ffd3bbc214c0-1440.png)：标题与五节正文层级清楚，系统场景图完整；最长章节条目无重叠。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/ffd3bbc214c0-390.png)：标题在已有连字符处分行；Übergabedokumentation 小标题完整，安装手册下载文字自然分两行，CTA 与元信息分隔明确。 | B1、B2；未见个别正文或导航显示缺陷；手册未打开。 |
| EN · [Gateway, meter and cloud monitoring](https://de-linker.com/gateway-meter-cloud-monitoring-data-layer/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/b51a56203396-1440.png)：两行标题、三层架构的四节层级清楚；四件设备拼图保留全图，未裁掉下排主体。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/b51a56203396-390.png)：三行标题完整，封面拼图与白色标题面板接缝无破损；两条正文链接没有挤成假按钮。 | B1、B2；未见个别图文显示缺陷；Ask Genie 行为未验。 |
| EN · [Hybrid inverter vs. AC-coupled storage](https://de-linker.com/hybrid-inverter-vs-ac-coupled-storage/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/df27f2596657-1440.png)：标题与封面完整；分节比较和青色检查框清楚，但首标题与框顶部出现重复留白，Next 栏为空。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/df27f2596657-390.png)：三行主标题可读；四节间隔明显大于同批其他文章，检查框顶部空白突出；Next 栏仍保留无链接标签。 | B1、B2、B3、B4。 |
| EN · [Indoor vs. outdoor storage](https://de-linker.com/indoor-vs-outdoor-battery-storage-planning/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/3f47c3a346f1-1440.png)：两行标题完整，室外电池场景图不拉伸；四节留白有层级，侧栏未覆盖文章。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/3f47c3a346f1-390.png)：三行标题、二级标题的两行组合可读；-20 C / +50 C 的符号可见，长文字链接自然分行。 | B1、B2；未见个别正文或图片缺陷；技术事实不在本静态评审范围。 |
| EN · [Inverter and battery pairing checklist](https://de-linker.com/installer-checklist-inverter-battery-pairing/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/dde084fcc1ee-1440.png)：两行长标题完整，逆变器图比例正常；章节、补充段与后续入口分开。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/dde084fcc1ee-390.png)：四行标题不截断，四节小标题完整；补充段与两条文字链接留白可读，前后篇均显示标题。 | B1、B2；未见个别正文或导航显示缺陷。 |
| EN · [Installer handover documentation](https://de-linker.com/installer-handover-documentation-checklist/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/108ace62c437-1440.png)：两行标题，电池封面居中；四节正文短段与相关缩略图完整。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/108ace62c437-390.png)：三行主标题，文档包与调试报告小标题自然分两行；下载中心文字链接未遮挡邻接入口。 | B1、B2；未见个别正文或封面缺陷；下载未执行。 |
| EN · [Remote monitoring after installation](https://de-linker.com/remote-monitoring-after-installation/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/f31b7a3ca75f-1440.png)：两行主标题，黑色设备图片没有溢出；四节正文对齐，相关文章卡显示完整名称。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/f31b7a3ca75f-390.png)：标题两行；Data-driven system optimization 分行自然，正文和项目 CTA 未叠在一起。 | B1、B2；未见个别正文或章节缺陷。 |
| EN · [Residential backup and self-consumption](https://de-linker.com/residential-storage-backup-self-consumption/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/7d935b821177-1440.png)：长标题在 Self- 的真实连字符处分行；现场图居中，正文四节层级和阅读列完整。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/7d935b821177-390.png)：四行主标题，Maximum self-consumption 小标题完整；两条正文入口在本宽度同一行，互不覆盖。 | B1、B2；未见个别正文或导航显示缺陷。 |
| EN · [Size storage for residential backup](https://de-linker.com/size-battery-storage-residential-backup/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/be145ceeab76-1440.png)：两行主标题，白色电池轮廓完整；四节文本与章节间距一致，旁栏相关图片已加载。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/be145ceeab76-390.png)：三行主标题，Depth of discharge / usable capacity 两行小标题可读；项目/数据表入口自然换行。 | B1、B2；未见个别正文或图片缺陷；数据表未下载。 |
| EN · [Solar-plus-storage commissioning](https://de-linker.com/solar-plus-storage-commissioning-checklist/) | [已看 1440](screens/20261021T191808788Z-d88d10cc-post-0-20/19601acaf5f4-1440.png)：两行标题与系统场景图完整；五节正文和 TOC 标签均可读，文章末尾两个相邻目标均有名称。 | [已看 390](screens/20261021T191808788Z-d88d10cc-post-0-20/19601acaf5f4-390.png)：三行主标题在现有连字符处分行；五节标题完整，手册链接两行，分享图标与相关文章没有堆叠。 | B1、B2；未见个别正文或导航显示缺陷；文件未打开。 |

## 尚未被这批静态图证明的状态

- TOC：手机截图仅显示收起状态。展开后的条目、长德语目录、章节跳转的真实位置、固定页头遮挡、URL hash、返回行为与当前章节提示均未验。
- 阅读与响应式：只覆盖 1440 / 390 的默认字体尺度；320、768、999/1000、1279/1280、横屏、200% 字体放大和键盘缩放未验。没有从两个端点推断中间断点已完整。
- 文章导航与语言切换：上/下一篇、相关文章、分类、Back to blog 的实际目的页及当前语言保持未验；不能把“链接文字完整”写成“导航通过”。
- 搜索：桌面文章内搜索表单只看过默认状态，手机该表单隐藏但页头搜索图标可见；输入、结果、无结果、分页、历史返回和英德保持均未验。
- 页头与页脚：只看过默认页头和 Solutions 页脚面板，所有下拉菜单、移动菜单、其他页脚面板、按钮 hover / focus / active、Cookie 面板和真实点击均 pending。
- 分享与咨询：静态图证明四个分享图标可见，不能证明 URL、可访问名称或分享结果；项目 CTA、Ask Genie、邮箱、询盘的消费者与未发送输入保持均未验，不提交真实询盘或邮件。
- 文件：文章里的安装手册、数据表与下载中心仅看过文字入口，未打开 PDF、检查语言/页码/字节/响应头或下载结果。打印、分页断页、浏览器打印和任何 PDF 导出亦未验。
- 动态浮层：桌面默认 Genie launcher 可见，未展开；手机默认未出现浮层。打开、关闭、恢复、加载、失败、遮挡与触控可达性不在这些截图的已证范围。

本文件只给出固定证据上的静态视觉发现和未覆盖边界；不把 40 张图、20 个 URL 或 render pass 计为全站、全部模板或全链路完成。


## B4当前关闭状态（2026-10-26）

原B4已由671上线关闭，原图和当时结论保留。嵌套标题额外48px移除，提示框顶距72→24px，相邻comparison组按既有24px token分开；英德四本地阅读区看图、线上EN1440/DE390与原目录跳转通过，正文原样。初候选组间距0的真实失败已纠正并保留DE390原图。当前受影响记录及恢复点见外部blog-reading-rhythm.json；其余未验状态不因本项关闭而改变。

## 既有逐篇静态阅读证据归位（2026-10-28）

- 证据文件：
  - `docs/acceptance/2026-10-22/full-site/blog-reading-rhythm.json`
  - `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/blog-reading-rhythm-audit.json`
  - `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/production-compare-current-main.json`
- 已回写矩阵范围：
  - `docs/acceptance/2026-10-22/full-site/page-matrix.json` 中全部 `20` 篇博客文章 × `1440/390` = `40` 条 `post` 记录已从 `pending` 更新为 `partially-verified`，并挂接各自对应的静态阅读节奏检查与生产只读对照引用。
  - `docs/acceptance/2026-10-22/full-site/state-matrix.json` 中 `blog-single-template-8221` 及其 `5` 个家族（正文节奏、目录/小标题、表格/图片/图注、上/下一篇与相关文章、移动端长文阅读）的 `en/de × 1440/390` 共 `24` 条记录已更新为 `partially-verified`。
- 边界说明：该归位只记入已完成的本地与生产静态 HTML/HTTP/正文节奏证据；真实视口滚动、锚点跳转、窄屏表格横向滚动、相关文章点击与生产部署后的最终客户入口读回仍保留待验，因此不标 `pass`。
- 2026-10-28 补充：代表篇 `8278 / 8282` 的桌面/移动视口与文内相关文章跳转已在本地实例实测并记入 `state-matrix.json`；其余 `18` 篇博客单篇与博客归档分页仍保留待逐篇视口复核。
