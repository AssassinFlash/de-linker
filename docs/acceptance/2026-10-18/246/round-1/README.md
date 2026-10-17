# #246 / PR #290：评审第 1 轮交回证据

评审：[2026-10-18 的已裁定意见](https://github.com/AssassinFlash/de-linker/pull/290#issuecomment-6238713717)。本轮保留并修正原实现；没有丢弃接续会话的改动。唯一工作树及实例为 `c246`（`http://127.0.0.1:9087`）。`just sync c246` 成功装入快照 `20261018-0238`，采集时间 `2026-10-17T18:49:26+00:00`，并施加本地许可。最终应用代码为 `32cc6f67`，已重放到 main `97f6fc14`；之后只补语言构建产物、浏览器测试清理和本记录。LC present 和 WindPress 管理端编译均成功，缓存 683605 bytes。没有部署、合并或写生产。

## 逐条落实

| 评审项 | 结果 | 实现和证据 |
|---|---|---|
| Standards hard 1，共享限流 | 完成 | `PublicGuard` 共用 contact 原来的每连接 3 次/小时及同一个 transient；两个 Handler 都先检查，接受后记数。`PublicSubmissionTest` 在第 4 次分别走两扇门，均断言新增 Outbox 行为空。[先红](limiter-red.txt) / [后绿](limiter-green.txt) |
| Hard 2，删除死通道 | 完成 | 删除 Checkout feedback/review_language/language_field/reply_promise、LoginGate html 和其私有 gates；移除 ProductView Approval/旧 login_url 分支；gateways 和 PendingGate 注释更新。restricted 独立保留 reason_notice |
| Hard 3，WindPress token 与数字来源 | 完成 | #246 block 的颜色、间距、边框使用 `--proto-*`；剩余列比和 breakpoint 注明原型 CSS 的来源行。没有新增插件 CSS |
| Hard 4，蜜罐 i18n | 完成 | guard 用 `esc_attr__('Website')` 输出可翻译标签，EN/DE catalog 覆盖；LC 不再硬编码 |
| Judgement 1，语言 twin | 完成 | `PageUrls::twin()` 供 Sender、Checkout、AccountLink、Contact Form 共用；不再散布五处 lookup |
| Judgement 2，命名入口 | 完成 | `Sender::request(Submission, array $billing = [])` / `message(Submission)` 共用 receive 核心；只有 request 读地址/VAT/草稿。#250 可以直接调 request |
| Judgement 3，布尔命名 | 完成 | OrderAdmin 用 `$is_contact` |
| Judgement 4，单一 guard 合同 | 完成 | fields 同时输出陷阱和签名起始时间，两个 Handler 共用 allows；contact TRAP_FIELD 删除。[先红](guard-red.txt) / [后绿](guard-green.txt) |
| Judgement 5，单次 flash | 完成 | Form 取出并立即清除 WC session 的字段、错误、locale；本次渲染后也清除对象 flash。真实夹具检查第一次回填、第二次没有 PII、短代码字面量转义 |
| Judgement 6，格式噪声 | 完成 | 撤销无语义改动文件的空行、构造器和 docblock 重排；全量 diff 复核 |
| Spec 1，受限原因仍能发询盘 | 完成 | LC restricted 片段在可用表单上方输出 reason_notice；EN/DE 初稿→独立评审→定稿见 [copy-review](../copy-review.md)。`test_restricted_reason_does_not_close_the_request_form` 与 restricted 四张截图 |
| Spec 2，Change 展开原生账单字段 | 完成 | `BillingFields` 使用 Woo 字段定义和 renderer，预填地址、国家、电话和 VAT，均可选；访客不读、不显示、不接受它们。真实 Handler 断言编辑后的地址落询盘；账号原 VAT 数据不变 |
| Spec 3，两扇门、一份记录 | 完成 | 删除 Contact 的三类旧邮件及模板/注册/测试，规格 §联系更新。NotificationRoutingTest 从真正 Contact Handler 走起，断言一份 Woo 记录、同一回执/团队类及 To/Bcc。[先红](routing-red.txt) / [后绿](routing-green.txt) |
| EN1440 联系表单复拍 | 完成 | 最终 `diagnostic-live-second-en-1440.png` / `diagnostic-feature-second-en-1440.png`，表单区域 **0**，客户页面 **0**，未掩膜。main 对应客户页面 **0**。下方保留其他拍摄的残差，不用零样本推断全矩阵稳定通过 |
| main-local 对照与照片归因 | 已补对照，归因有边界 | main d27d1a3e 无 #246 Sender；原图字节相同，几何一致；同一个线上页面重复拍摄也出现相同照片带差异。可确定不是 #246 新增可见内容/错图或缺失 uploads。更底层栅格差异来源尚不能精确证明，见下方 |
| 四组严格全页像素门 | **未完成** | 某些重复拍摄仍有照片/抗锯齿残差；没有把容差、裁图或工具栏排除当成全页 PASS |

## 测试与独立复核

完整命令、返回值、计数见 [checks.txt](checks.txt)。`just check`、`just test` 均成功；WPCS、PHPStan level 8、i18n 与构建检查通过。真实 c246 集成连续运行两次，各为 **88 tests / 1003 assertions / 9 skipped**；既有 9 个 ProductSearch HTTP 夹具测试需要另行指定夹具 URL，本票所有新增测试都实际运行。

限流、guard、路由使用 tdd，失败输出与绿色输出已随本目录保留。额外发现的 VAT 副作用同样先失败：[vat-red.txt](vat-red.txt) → [vat-green-proforma.txt](vat-green-proforma.txt)。VAT 清空或改成新号只影响本次询盘快照，不会改掉账号的五个审核 meta，也不产生账号 VAT 变更通知。

全量 diff 双评审：Standards 对 main→本票实现未发现剩余硬项；Spec 发现 VAT 编辑会改账号审核状态，已修复并独立复核通过。最后一次 focused Standards 复核发现浏览器清理删掉邮件 job 却未撤销 AS retry，现已在删除前调用 `as_unschedule_all_actions`；实际浏览器两个 job 的重试也已清理。没有恢复旧代码、旧联系邮件、模板抢占或第二条 Tailwind 管线。

测试纪律：集成基类保存/恢复 TestMode、quota、连接限流窗口；邮件投递文件只到合成 tester，去除 Bcc，收件路由正确性单独断言 Outbox 原始数据。浏览器客人提交时先填满本地 quota，两封邮件只排队，未投递。`NotificationRoutingTest` 明确设置 notify_to 与 Bcc `chester@de-linker.com`，检查团队通知只到内部 To/Bcc、客户回执只到提交邮箱；还覆盖默认和自定义内部 From，保留 #286 行为。文件传输层没有外发真实邮件。

## 浏览器矩阵

以下各前缀均有 1440 与 390 的 JPG。均由 Computer Use 操作实际 c246 页面，合成用户资料；没有静态预览或实际客户资料。

| 状态 | EN | DE |
|---|---|---|
| 访客带产品，不显示国家/VAT | `guest-en-*` | `guest-de-*` |
| 批准账号，资料折叠一行 | `approved-en-*` | `approved-de-*` |
| 展开 Woo 地址和 VAT | `approved-expanded-en-*` | `approved-expanded-de-*` |
| 受限原因，表单可发送 | `restricted-en-*` | `restricted-de-*` |

[DE390 真实访客成功页](received-de-390.jpg) 及 [读回](browser-readback.json)：customer_id=0、inquiry-received、产品 1959 ×2、德语、无国家；队列回执到合成提交邮箱，团队到 sunriver。该读回的源为修 VAT 后、修邮件姓名末尾空格前的提交；最终 subject trim 另由集成检查，未修改历史读回。pending、空态、错误、所有账号发送后的截图与原证据仍在 [上级目录](../README.md)。受限原因是团队储存的自由文本；DE 夹具直接提供德语，不声称自动翻译团队原因。

## 像素方法与归因

同机、同一 Chrome 会话，1440×1000 和 390×844、DPR=1。所有比较使用完全相同的 [capture-session.js](capture-session.js)：滚过全页加载可见图片、等待字体/可见图片 decode、禁动画/过渡/光标、原生 select 打开后 Escape 关闭、点击可见表单标题安全失焦、回到顶部，再用 CDP 截取全页 PNG。此前诊断中用坐标点击“空白处”在移动端可能触发 hero 控件，已弃用；最终矩阵全部使用语义标题失焦。没有提交线上表单。

[compare.py](compare.py) 逐 RGB 精确比较，无容差、无掩膜。原始全图数和后台工具栏数均见 [pixel-comparison.json](pixel-comparison.json)。下表“客户页”排除管理员工具栏（桌面32、移动46像素高），因为两个站的管理员 UI 不同；这项排除不计作全图通过，也不隐藏原始计数。表单列比较整个表单侧区域，包含其所有字段；区域几何记录在 [capture-geometry.json](capture-geometry.json)，最终 EN 的内表单及照片另见 [final-en-geometry.json](final-en-geometry.json)。

| 语言/宽度 | live vs main 客户页 / 表单 | live vs #246 最终客户页 / 表单 |
|---|---:|---:|
| EN1440 最终复拍 | 0 / 0 | **0 / 0** |
| EN390 矩阵拍摄 | 13122 / 0 | 2569 / 0 |
| DE1440 矩阵拍摄 | 366109 / 13 | 136480 / 15 |
| DE390 矩阵拍摄 | 13759 / 0 | 20795 / 0 |

main 来自实际切换到 `origin/main` d27d1a3e，present/编译后拍摄，[readback](main-readback.json) 中 Sender 不存在。之后 fetch 又带入 #245（97f6fc14）；只增加后台说明页及 `.linker-admin-access` scoped 样式，不作用于 contact。本票已重放保留 #245 并重新 present/编译。

原 129712 像素照片带的调查结果：

1. [photo-assets.json](photo-assets.json) 中三个浏览器实际加载资源的 live/main SHA-256 和字节数完全相同；没有缺图、错图、不同 webp 变体。DOM 的 natural dimensions、图像矩形、object-position 和 filter 相同。无需修 uploads 同步；为像素计数替换图像反而会改动正确内容。
2. 仅比较矩阵内两次 **live** 截图，同一 URL、同一视口、没有站点写入，仍有照片和抗锯齿差异。原始计数在 JSON 的 `live_repeat_control`。因此相同的差异确实可以在无 #246 的 main 和线上重复拍摄中出现。
3. 最终 EN 控制对（`diagnostic-*-en-1440`）第一次与紧接着第二次捕获分别完全相同，live 与 #246 的客户页也完全相同，表单 **0**。更早同方法 EN 矩阵样本仍为372576/90，未删掉；原先独立取得的零样本 `*-form-contact-en-1440` 也保留。零与非零样本共存，不能把早先照片带判为确定的源代码回归。
4. **证据边界：**变化发生在浏览器渲染/捕获结果，资源和布局相同是实证；具体是滤镜栅格、合成缓存还是底层驱动因素，尚不能由这些证据单独确定。没有以“已确认 GPU bug”结案，也未把非零像素豁免。四组全页严格像素门仍为未完成，交回评审如实决定。

重新计算：`python3 docs/acceptance/2026-10-18/246/round-1/compare.py`（本机已有 Pillow、NumPy）。本轮不引入依赖。

#244 的对话摘要与 #250 的确认卡不在本票实现，二者可调用这里的 `request()`；#237 的上线实走由管理会话负责。没有新增 follow-up 票。所有浏览器测试用户、询盘、队列和待重试动作均已清理；最终保留 c246 的 tester 收件人重写开关（tester246@example.test），本地文件传输仍有效。只修改 c246。
