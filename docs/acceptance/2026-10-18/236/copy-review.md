# #236 附件与铭牌文案对抗评审记录

规则：AGENTS.md §3 用词（产品、型号、系列；不说 catalogue / article / cart；Produkt / Modell / Serie；Sie 体）、
禁 "不是…而是…" 与三连排比；linker-copywriting Hard Stops 1–9（尤其 6 与 9 Actor：正文不给读者布置任务）。
EN 先定稿，DE 独立撰写（Sie 体），不逐字翻译。

评审方式：初稿由实现会话写（内容见下表"初稿"列）；评审由一个独立的评审代理执行
（只读，不改文件），对照上面的规则、#249 的评审记录、现有 `.po` 术语（"Unterlagen"、"%s: Unterlagen anzeigen"、
"Was passt dazu?"、"Anhang: %s"、"Datei auswählen"、"Wird gesendet …"、"unserem Sortiment"），并把 `%s` 逐个代入
真实取值（逆变器、电池、电池柜、无品牌的 "H2-15K-T3"）找语法断点，同时检查 390 px 宽的按钮长度。
定稿即 `src/genie/components/AttachmentCard.tsx`、`AttachmentChips.tsx`、`App.tsx`、`includes/Genie/Preview.php`
的 msgid 与 `languages/linker-tools-de_DE_formal.po` 的 msgstr。

确认按钮把一句话作为客户自己的消息发进对话（"客户确认 → 走产品或兼容性"）。

## 贯穿全稿的意见

1. **按钮与它发出的消息必须一致**（#249 先例）：初稿按钮 "Yes, show its documents" 发出 "My device is the %s. Show me its documents."，
   客户在对话里看到的不是自己点的那句。→ 消息以按钮原话开头再加型号。**采纳**（A12、A14；A15 与 A16 完全相同）。
2. **"Read %s" 放在句首读像命令**（"Read report.pdf."）。→ 照 "Attached: %s" 的标签式写 "Read: %s" / "Gelesen: %s"。**采纳**。
3. **页数要复数处理**："1 of 1 pages"。→ `_n()`。**采纳**（B6 同样）。
4. **德语省略号前留空格**（.po 惯例 "Wird gesendet …"）。**采纳**。
5. **"find" 过度承诺并撞名**：C1、D1 说"找到产品"，但 A9 正是我们没有的情形；"Find my device" / "Mein Gerät finden" 是 Apple 与
   Google 的找手机服务。→ 两行重写。**采纳**。
6. **Actor 与报错**：只有客户能做的恢复动作（换一个文件）可以说；能用"Genie 读什么"陈述的就陈述（B2）。**采纳**。
7. **德语 "Typ" 与 "Modell" 冲突**：德国铭牌上 "Typ" 就是型号本身。→ 设备类别用 "Device" / "Geräteart"。**采纳**。
8. **代入检查**：EN "the %s" 对所有样例成立；DE "das Modell %s" 以同位语避开词性；A7 去掉冠词。通过。
9. **德语确认消息要对真实 Genie 实测**（#233：德语理解随措辞变化）。→ 已测，见下文"实测"。
10. **390 px**：候选按钮可达约 26 字符，改为整宽纵排（`genie.css` `.linker-genie-attachment__actions` 767 px 以下）。**采纳**。

无 "不是…而是…"、无三连排比（格式列表是数据）、无禁用词。

## 逐条

| id | 位置 | 初稿 EN / DE | 评审意见 | 定稿 EN / DE |
|---|---|---|---|---|
| A1 | 文件读不出 | %s could not be read. / %s konnte nicht gelesen werden. | 保留 | 同初稿 |
| A2 | 按钮，开文件选择框 | Send another photo / Anderes Foto senden | 按钮只开选择框、不发送；与 C2 一致 | **Choose another photo / Anderes Foto auswählen** |
| A3 | PDF 已读 | Read %1$s: %2$d of %3$d pages. / %1$s gelesen: … | 祈使读法；复数 | **Read: %1$s (%2$d of %3$d page[s])** / **Gelesen: %1$s (%2$d von %3$d Seite[n])**（`_n`） |
| A4 | 照片已读（非铭牌） | Read %s. / %s gelesen. | 同上 | **Read: %s / Gelesen: %s** |
| A5 | 铭牌卡标题 | Read from your nameplate photo / Vom Foto Ihres Typenschilds gelesen | 保留（"Read" 如实表明是机器读取） | 同初稿 |
| A6 | 字段名 | Brand / Model / Type · Marke / Modell / Typ | 德语 "Typ" 即型号 | **Brand / Model / Device · Marke / Modell / Geräteart** |
| A7 | 精确命中 | This matches our %s. Is this your device? / Das entspricht unserem Modell %s. Ist das Ihr Gerät? | 两个 "this" 指不同东西；"matches" 在照片可能读错时过度确定，疑问交给后半句 | **In our range: %s. Is this your device? / In unserem Sortiment: %s. Ist das Ihr Gerät?** |
| A8 | 部分命中 | No exact match. Is it one of these? / Kein genauer Treffer. Ist es eines dieser Modelle? | 保留（"es" = Gerät，中性） | 同初稿 |
| A9 | 不在范围 | This model is not in our product range. / Dieses Modell führen wir nicht. | 保留 | 同初稿 |
| A10 | 读不出 | The brand and model could not be read. / Marke und Modell waren nicht lesbar. | DE 与 A1 同句式 | 评审定稿 "…konnten nicht gelesen werden."；**评审后改**：分级规则改为"没读到型号即 unreadable"（只有品牌不足以判断我们有没有，评测里 PYLON 只读出品牌时回答曾说"我们不经营"），句子随之改为 **The model could not be read. / Das Modell konnte nicht gelesen werden.** |
| A11 | 按钮 | Yes, show its documents / Ja, Unterlagen zeigen | DE 用现有动词 anzeigen | EN 同初稿 / **Ja, Unterlagen anzeigen** |
| A12 | A11 发出的消息 | My device is the %s. Show me its documents. / Mein Gerät ist das Modell %s. Zeigen Sie mir die Unterlagen dazu. | 以按钮原话开头 | **Yes, it's the %s. Show me its documents. / Ja, es ist das Modell %s. Bitte zeigen Sie mir die Unterlagen dazu.** |
| A13 | 按钮 | Yes, what works with it? / Ja, was passt dazu? | 保留（现有 "Was passt dazu?"） | 同初稿 |
| A14 | A13 发出的消息 | My device is the %s. Which products work with it? / … Welche Produkte passen dazu? | 消息 = 按钮 + 型号 | **Yes, it's the %s. What works with it? / Ja, es ist das Modell %s. Was passt dazu?** |
| A15 | 候选按钮 | It is the %s / Es ist das Modell %s | 读起来像聊天 | **It's the %s** / 同初稿 |
| A16 | A15 发出的消息 | My device is the %s. / Mein Gerät ist das Modell %s. | 与按钮一致 | **It's the %s. / Es ist das Modell %s.** |
| A17 | 按钮（否认） | No, type the model / Nein, Modell eingeben | 客户自己的选择，不是作业 | 同初稿 |
| A18 | 按钮 | Type the model / Modell eingeben | 保留 | 同初稿 |
| A19 | 放进输入框的开头 | "My device is the " / "Mein Gerät ist das Modell " | 保留 | 同初稿（实现为 msgid "My device is the %s"，%s 为空：i18n 规则不许首尾空格） |
| B1 | 准备中 | Preparing… / Wird vorbereitet… | 说清准备什么；DE 省略号前空格 | 评审定稿 "Preparing photo…"；**实现时改为 Preparing file… / Datei wird vorbereitet …**：PDF 也经过这一态 |
| B2 | 类型不对 | This file cannot be sent. Attach a photo (…) or a PDF. | 命令改为陈述 Genie 读什么 | **This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC) and PDFs. / Dieser Dateityp kann nicht gesendet werden. Genie liest Fotos (JPEG, PNG, WebP oder HEIC) und PDFs.** |
| B3 | 太大 | This file is too large. A PDF can be up to %d MB. / … | 保留；若只对 PDF 可写 "This PDF…" | 同初稿（图片也可能触发：浏览器之外的客户端） |
| B4 | HEIC 打不开 | … Save the photo as JPEG and attach it again. | 只留一个客户能做的动作 | **This browser cannot open HEIC photos. Please attach the photo as a JPEG. / … Bitte hängen Sie das Foto als JPEG an.** |
| B5 | 照片打不开 | … Please try another one. / … Bitte versuchen Sie ein anderes. | DE 口语；与 A1/C2 一致 | **This photo could not be opened. Please choose another one. / Dieses Foto konnte nicht geöffnet werden. Bitte wählen Sie ein anderes.** |
| B6 | 超过 3 个 | You can attach up to %d files at a time. | `_n` | 同初稿 + `_n` |
| B7 | 每小时额度用完 | You have sent many files in the last hour. Please try again later. | "many" 含糊且像指责；说明是哪个限额、文字提问照常 | **You have reached the hourly limit for files. Please try again later; typed questions still work. / Sie haben das stündliche Limit für Dateien erreicht. Bitte versuchen Sie es später erneut. Fragen per Text beantwortet Genie weiterhin.** |
| C1 | 预览卡打开后的说明 | Genie reads the brand and model from a photo of the nameplate and finds the product. | "finds" 过度承诺 | **Genie reads the brand and model from a nameplate photo and checks them against our range. / Genie liest Marke und Modell vom Foto des Typenschilds und gleicht sie mit unserem Sortiment ab.** |
| C2 | 按钮 | Choose a photo / Foto auswählen | 保留 | 同初稿 |
| D1 | 首页预览卡第四条 | Find my device from a nameplate photo / Mein Gerät per Typenschild-Foto finden | 撞名找手机服务；DE 改问句（#249 先例） | **Look up my device from a nameplate photo / Welches Modell steht auf meinem Typenschild?** |

## 实测（2026-10-18，g236，真实 Genie：deepseek-flash 官方通道，`just serve g236`）

确认按钮发出的六句（`eval/confirmations.json`）：

| 消息 | 路由（Jev 意图） | 结果 |
|---|---|---|
| Yes, it's the SAJ H2-10K-T3. Show me its documents. | documents（documents_specs） | 产品卡 + 数据表与手册三个文档链接 |
| Yes, it's the SAJ H2-10K-T3. What works with it? | pairing（pairing_compatibility） | 产品卡与放行的 B2 电池卡、配置说明与电池文档 |
| It's the SAJ H2-15K-T3. | products（find_products） | H2-15K-T3 产品卡与两份文档 |
| Ja, es ist das Modell SAJ H2-10K-T3. Bitte zeigen Sie mir die Unterlagen dazu. | documents（documents_specs） | 德语回答，产品卡 + 文档链接 |
| Ja, es ist das Modell SAJ H2-10K-T3. Was passt dazu? | pairing（pairing_compatibility） | 德语回答，B2 电池卡与配置说明 |
| Es ist das Modell SAJ H2-15K-T3. | products（find_products） | 德语回答，H2-15K-T3 产品卡 |

e2e `tests/e2e/specs/genie-attachments.spec.ts` 在浏览器里点 "Yes, what works with it?" / "Ja, was passt dazu?"，
EN/DE × 1440/390 均得到回答（截图 `shots/*-5-confirmed.png`）。
