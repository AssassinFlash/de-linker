# 德语自动翻译：Claude 第二轮修复

依据：[Claude 第二轮评审](https://github.com/AssassinFlash/de-linker/pull/277#issuecomment-6234863431)。本记录取代第一轮“插入/删除即结构异常”的行为与截图等待说明；已有人工德语保留、不做全站重译的裁定继续生效。

## 句子增删

- LCS 的 equal 段通过旧/新索引映射保留，位置平移不触发异常。
- 有相邻、唯一的 equal 句段定位：新增只发送新句，按位置插入德语；删除移除对应德语句，不调用模型。
- 同时被移除又在别处出现的旧句判为重排，保留整对象及旧基线，零调用。无可靠锚点、无法分离或不兼容的 HTML 上下文继续显式 `structure_mismatch`。
- 拼接在德语自己的原始 parts 上执行，不重建整页。保留人工双空格、属性引号、德语 title、未变链接、段落包装和无关图片。完整新增列表保留外层 ul/ol；局部 li 插入须与目标父上下文一致。

`ManualGermanTest` 使用线上快照 About 的英文及人工德语 HTML：

1. 无基线采用与重复运行，德语逐字节不变，零调用。
2. 只改一句，请求 segments 仅该句；整页结果精确相等，已有空 SEO 保留。
3. 在既有段落的两个未改句之间插入 `We offer technical guidance for every project.`，请求仅这句，全文只增加 `Wir bieten technische Unterstützung für jedes Projekt.`。
4. 删除 `You handle everything through Linker.`，只移除人工德语 `Sie wickeln alles über Linker ab.`；其余全文精确相等，无新增请求。
5. 交换另一段的两句，状态为结构不同，德语和旧基线不变，零新增调用。
6. 无 equal 锚点的结构替换，连续旧 force/重试不绕过保护；后台和异常清单可见。

## 验证

- i18n 单元：**190 tests / 432 assertions**。
- 保存/词项/模板/自动同步/人工德语真实 WordPress 夹具：**23 tests / 288 assertions**，同集连续两次通过，不手工清表。
- 摘要真实 WordPress 夹具：**1 test / 25 assertions**，连续重复及最终清理修复后均通过。正文 EN/DE，包含数量、失败/结构异常、词项、源链接；排除已同步、排队、德语副本、模板；To/Bcc 按现有 Options，**0 次实际投递**。
- 本地 `just check`、全仓 `just test` 通过；随后 PHP 增量重新执行 `just php-test`，i18n 190/432、commerce 125/1802、mu-plugin 6/23。新 digest 清理修复另跑真实夹具与 PHPCS；最终全量检查以 PR 的 CI 为准。
- 测试 PHP 在翻译命名空间隔离真实 HOME 凭据，仅使用假客户端。新增句的 stand-in 返回正常德语句首，确保下一次编辑可以重新分句。
- Native 夹具删除会触发 SEOPress 重定向提示，测试的 finally 现保存并还原该选项；本轮遗留的自有测试提示也已清除。

## 双评审与文案

固定全量基线 `ad6de8b7a234677c8726da984e4b1b844158c6bf`，第二轮代码至 `4a101d4`；摘要增量至 `93f1ce6a`。Spec 独立复核指出并已关闭：媒体夹带删除、带属性段落误拦、丢失 ul 上下文、安全 br/wbr 被拦。Standards 指出的数字坐标元组已改为具名范围，摘要测试的 post/term 重号清理也已修正。

最终 **Spec：0 项未解决；Standards：0 硬违规 / 0 待处理气味**。新增摘要三组 EN/DE 文案见 [初稿、意见与定稿](copy-review.md#第二轮补齐每日摘要异常块)。德语空态采纳 `gemeldet`，准确限定已记录异常的范围。

## 后台截图

先执行已合并的 `just sync i253`，装入 **20261017-2214**，14:28:07 UTC 完成；本地 LiveCanvas/SEOPress 许可已施加。

CUA 原生浏览器，桌面视口 1440×1000，移动视口 390×844。全页 JPG 按浏览器原生接口保存；有滚动条时图像省略 15px 滚动条，移动端内容宽 375px，实际 `window.innerWidth=390`，未缩放或编辑图像。移动列表逐行展开，并滚到顶部后拍摄，避免工具栏遮住状态。

每张状态图包含同步、排队、失败、结构不同四行。桌面聚焦失败行的同步链接；移动端展开四行并展示同步动作。

| 列表 | EN 1440 | EN 390 | DE 1440 | DE 390 |
|---|---|---|---|---|
| 页面 | [截图](screenshots/admin-page-en-1440.jpg) | [截图](screenshots/admin-page-en-390.jpg) | [截图](screenshots/admin-page-de-1440.jpg) | [截图](screenshots/admin-page-de-390.jpg) |
| 产品 | [截图](screenshots/admin-product-en-1440.jpg) | [截图](screenshots/admin-product-en-390.jpg) | [截图](screenshots/admin-product-de-1440.jpg) | [截图](screenshots/admin-product-de-390.jpg) |
| 博客 | [截图](screenshots/admin-post-en-1440.jpg) | [截图](screenshots/admin-post-en-390.jpg) | [截图](screenshots/admin-post-de-1440.jpg) | [截图](screenshots/admin-post-de-390.jpg) |

实际点击 EN 产品行及 DE 博客行的同步动作，返回成功提示，英文源状态变 pending，Action Scheduler 中该源各有一条 pending：

- [英文重试](screenshots/admin-retry-en-390.jpg)
- [德语重试](screenshots/admin-retry-de-390.jpg)
- [视口、快照、队列及清理读回](review-round-2.json)

截图使用 24 个私有临时对象，通过原生 Screen Options 偏好只保留相关列。拍摄期间临时暂停 i253 的 AS 自动 runner，让四种示例状态稳定；重试仍经真实 nonce/权限入口排队。此控制只用于视觉夹具，不作为自动翻译完成证据。拍完移除全部夹具及自有任务、还原员工 locale/列表偏好和 SEOPress 提示，并移除 runner 控制、还原浏览器视口。

## 摘要消费者已接入

最终核验确认[内部通知与每日摘要的 PR](https://github.com/AssassinFlash/de-linker/pull/274)已合并。因此按原批准计划，由 i18n 本票直接通过 `linker_commerce_digest_blocks` / `Digest\Block` 接入，原留言交接不再是完成状态。

`Translation\DigestBlock` 在邮件 locale 下读取共享 `StatusReport`；标题带数量，逐条包含名字、原因与英文源编辑链接，空态也显示。commerce 不存在时守卫接口；i18n 未启用则没有此过滤器。没有新增收件、调度或发信通道。

## 仍需后续许可的生产项

等 Claude PR 评审、合并和业主另行批准上线及生产密钥写入，再执行备份、部署/读回、退休 14 模板任务与错误状态、处理 6 页面、只补缺失/pending、线上网页保存英文产品与异步官方翻译实走、前台与模板选择验证、cutover verify。此次未写生产密钥、未改线上积压，也未自行合并。
