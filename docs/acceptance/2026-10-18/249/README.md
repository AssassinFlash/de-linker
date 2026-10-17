# #249 Genie 主动预览卡 · 验收 A3

实例 `g249`：`just sync g249`（线上快照 2026-10-17 16:42 UTC）+ `just serve g249`（真实 Genie）。
截图由 `tests/e2e/specs/genie-preview.spec.ts` 拍（Playwright Chromium，1440×900 与 390×844），
可重跑：

```sh
LINKER_E2E_SHOTS=$PWD/docs/acceptance/2026-10-18/249/screens just e2e g249 specs/genie-preview.spec.ts
```

结果：31 项全过（EN 13、DE 13、无卡页面 5；评审第 1 轮后重拍）。8 秒停留与 30 天记忆跑在 Playwright 控制的页面时钟上
（`page.clock`）：测试快进时间，不靠睡眠；"30 天后"是页面读到的真实日期。

| A3 规则 | 测试 | 截图（EN / DE 同名，前缀 `en-` / `de-`） |
|---|---|---|
| 不在页面加载时出现 | appears only after … | `1440-product-1-arrival`（加载后 24 秒仍无卡） |
| 滚过主内容 + 停留约 8 秒 | appears only after … | `1440-product-2-scrolled-7s`（滚过后 7 秒无卡）→ `1440-product-3-card`（8 秒出现） |
| 首页在滚过 hero 之后 | the home card waits until the hero is passed | `1440-home-0-in-hero`（hero 内停 16 秒无卡）→ `1440-home-card` |
| 只在白名单页面，卡片点名当前页面 | names the … page；pages without the card | `1440-product-3-card`、`1440-category-card`、`1440-solution-card`、`1440-home-card`；购物车 / Proforma 请求 / 账户与登录 / 联系 / 配置器页无卡元素 |
| 2–4 条建议 + AI 提示 | names the … page | 同上（断言 2 ≤ 建议数 ≤ 4、AI 行存在） |
| 每次访问最多一次（跨标签页；30 分钟无活动为新访问） | once per visit, across tabs | `1440-category-once-per-visit`（同一标签的下一页无卡）→ `1440-solution-other-tab-same-visit`（10 分钟后另开标签，无卡）→ `1440-solution-new-visit-after-idle`（45 分钟后另开标签，新访问，出现） |
| 解决方案页：只滚过 hero 不算 | a solution page waits past the hero for its first section | `1440-solution-0-past-hero-only`（hero 已滚出，停 16 秒无卡）→ `1440-solution-card` |
| 关掉后 30 天不再出现 | closed: away for 30 days | `1440-category-closed` → `1440-product-closed-29-days`（新访问，29 天后无卡）→ `1440-product-back-after-31-days`（31 天后再现） |
| 对话进行中不出现 | never during a conversation | `1440-product-conversation-open` |
| 不抢焦点（含输入中不出现） | appears only after …（焦点仍在 body）；waits while the visitor types | `1440-category-typing`（输入框保有焦点、无卡；离开输入框后出现） |
| 点建议走 dock 加载器的 `linker-genie-ask` | a suggestion asks Genie through the dock | `1440-product-suggestion-answered`（真实 Genie 回答） |
| 手机端只在圆钮上出标记（红点＝`--proto-sem-danger`） | on a phone (product / home) | `390-product-mark`、`390-home-mark`（无卡，圆钮带红点；焦点不动）→ `390-…-mark-opened`（点圆钮打开 Genie，标记随之消失） |
| 不遮挡主按钮 | — | 产品页的锚点是图库与购买框（`.pdp-layout`），卡出现时购买框已滚出视口（`1440-product-3-card`）；390 宽产品页圆钮在底部价格条之上（`390-product-mark`） |

单元层：`plugins/linker-tools/src/preview/*.test.ts`（规则、访问记忆与控制器，22 项，含跨标签同一访问、活动续期、30 分钟后新访问、存储被禁用时不出现、Esc 关闭）、
`plugins/linker-tools/tests/php/Unit/PreviewTest.php`（哪些页面有卡、名字、文案、锚点、标记，22 项）。

e2e 的 `scrollPast` 断言每类页面都带着卡点名的锚点，选择器对不上线上模板时测试失败，不会悄悄落到"滚过四分之三屏"的回落。

像素门（页面静止时 live = local，首页、产品、分类、解决方案 × EN/DE × 1440/390，16 组全部 0 差异）：`pixel/README.md`。

文案对抗评审：`copy-review.md`（第 1 轮全稿；第 2 轮首页建议改为取当前商品数据）。
