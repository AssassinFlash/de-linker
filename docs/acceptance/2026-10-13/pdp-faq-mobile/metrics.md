# 实测数值（t109）

来自 `measure.mjs` 的浏览器 DOM 几何；单位 CSS px。390×844、430×932、1440×1000。

| 面 | 宽 | 头图高 | sticky高 | pill高 | 问题行高 | 侧边距 | 溢出 |
|---|---:|---:|---:|---:|---:|---:|---|
| pdp-en | 390 | 300 | 88 | 62 | — | 16 | false |
| pdp-en | 430 | 300 | 88 | 62 | — | 16 | false |
| pdp-en | 1440 | 640 | 0 | 71 | — | 40 | false |
| faq-en | 390 | — | — | — | 76.78125 | 16 | false |
| faq-en | 430 | — | — | — | 76.78125 | 16 | false |
| faq-en | 1440 | — | — | — | 56 | 340 | false |
| faq-de | 390 | — | — | — | 76.78125 | 16 | false |
| faq-de | 430 | — | — | — | 76.78125 | 16 | false |
| faq-de | 1440 | — | — | — | 56 | 340 | false |

## 触控目标（390）
- pdp-en: 15 个目标；小于44px：0。
- faq-en: 33 个目标；小于44px：0。
- faq-de: 23 个目标；小于44px：0。

## 实际行为
- faq-en: 272 product answers / 16 trade questions / 159 documents; default 0 open; search match/empty/reset + keyboard Enter PASS
- faq-en no JS: same 272/16/159; search hidden; native accordion PASS
- faq-de: 0 product answers / 16 trade questions / 0 documents; default 0 open; search match/empty/reset + keyboard Enter PASS
- faq-de no JS: same 0/16/0; search hidden; native accordion PASS
- PDP pending: Prices after approval | Prices after approval UI-state PASS (amount/add operation separate)
- PDP restricted: Not available for your account | Not available for your account UI-state PASS (amount/add operation separate)
- GAP: approved PDP amount is intercepted by the active snapshot plugin price hook (tv_b2b_filter_price_html); Woo edit price is present.
- PDP approved: Net prices after account review | Add to solution draft UI-state PASS (amount/add operation separate)
- PDP approved action: existing Woo add-to-cart -> draft items 0 GAP: snapshot price/cart gate conflicts with new approval state
- DE PDP public response: 404 (instance product twin is draft; not edited)

## sticky 遮挡
移动条本身有意固定覆盖视口底部；每屏拍摄步长为视口高−124，保留上下屏重叠。PDP 底部 padding=实际行动条高度+52px，body scroll-padding-bottom=实际高度+36px（当前88px分别得140/124），为最后内容留出空间。需要展开 Genie 的浮层按其既有覆盖行为处理；PDP 仅上移现有关闭态坞，不改其实现。
