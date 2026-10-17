# #249 Genie 主动预览卡 · 验收 A3

实例 `g249`：`just sync g249`（线上快照 2026-10-17 16:42 UTC）+ `just serve g249`（真实 Genie）。
截图由 `tests/e2e/specs/genie-preview.spec.ts` 拍（Playwright Chromium，1440×900 与 390×844），
可重跑：

```sh
LINKER_E2E_SHOTS=$PWD/docs/acceptance/2026-10-18/249/screens just e2e g249 specs/genie-preview.spec.ts
```

结果：29 项全过（EN 12、DE 12、无卡页面 5）。8 秒停留与 30 天记忆跑在 Playwright 控制的页面时钟上
（`page.clock`）：测试快进时间，不靠睡眠；"30 天后"是页面读到的真实日期。

| A3 规则 | 测试 | 截图（EN / DE 同名，前缀 `en-` / `de-`） |
|---|---|---|
| 不在页面加载时出现 | appears only after … | `1440-product-1-arrival`（加载后 24 秒仍无卡） |
| 滚过主内容 + 停留约 8 秒 | appears only after … | `1440-product-2-scrolled-7s`（滚过后 7 秒无卡）→ `1440-product-3-card`（8 秒出现） |
| 首页在滚过 hero 之后 | the home card waits until the hero is passed | `1440-home-0-in-hero`（hero 内停 16 秒无卡）→ `1440-home-card` |
| 只在白名单页面，卡片点名当前页面 | names the … page；pages without the card | `1440-product-3-card`、`1440-category-card`、`1440-solution-card`、`1440-home-card`；购物车 / Proforma 请求 / 账户与登录 / 联系 / 配置器页无卡元素 |
| 2–4 条建议 + AI 提示 | names the … page | 同上（断言 2 ≤ 建议数 ≤ 4、AI 行存在） |
| 每次访问最多一次 | once per visit | `1440-category-once-per-visit`（同一访问的下一页无卡） |
| 关掉后 30 天不再出现 | closed: away for 30 days | `1440-category-closed` → `1440-product-closed-29-days`（新访问，29 天后无卡）→ `1440-product-back-after-31-days`（31 天后再现） |
| 对话进行中不出现 | never during a conversation | `1440-product-conversation-open` |
| 不抢焦点（含输入中不出现） | appears only after …（焦点仍在 body）；waits while the visitor types | `1440-category-typing`（输入框保有焦点、无卡；离开输入框后出现） |
| 点建议走 dock 加载器的 `linker-genie-ask` | a suggestion asks Genie through the dock | `1440-product-suggestion-answered`（真实 Genie 回答） |
| 手机端只在圆钮上出标记 | on a phone (product / home) | `390-product-mark`、`390-home-mark`（无卡，圆钮带红点；焦点不动）→ `390-…-mark-opened`（点圆钮打开 Genie，标记随之消失） |
| 不遮挡主按钮 | — | 产品页的锚点是图库与购买框（`.pdp-layout`），卡出现时购买框已滚出视口（`1440-product-3-card`）；390 宽产品页圆钮在底部价格条之上（`390-product-mark`） |

单元层：`plugins/linker-tools/src/preview/*.test.ts`（规则与控制器，21 项，含存储被禁用时不出现、Esc 关闭）、
`plugins/linker-tools/tests/php/Unit/PreviewTest.php`（哪些页面有卡、名字、文案、标记，20 项）。

文案对抗评审：`copy-review.md`。
