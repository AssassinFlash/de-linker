# #190 PDP 三条欠账 · 本地实例视觉抽查（2026-10-16）

实例 `pdpfix`（快照 2026-10-15-1852，http://127.0.0.1:9030）+ 本分支 `present` + `just windpress-compile pdpfix`
（cache recompiled、anchor classes present）。参考产品 GoodWe GW60K-STS-G10（EN 6530 / DE 6565）。

## 截图（同一浏览器、1440×900 与 390×844，EN 与 DE）

| 文件 | 内容 |
|---|---|
| `{en,de}-{1440,390}-rail-instock.png` | 库存「有货」态：圆点 accent 绿 `rgb(12,127,115)`（`class="pdp-dot"`）+ In stock / Auf Lager |
| `{en,de}-{1440,390}-rail-outofstock.png` | 库存「无货」态：圆点 warn 橙 `rgb(249,115,22)`（`class="pdp-dot is-wait"`）+ Currently unavailable / Derzeit nicht verfügbar |
| `{en,de}-{1440,390}-choices.png` | Plan with… 展开后的三个规划阶段按钮（无 nameplate 芯片） |
| `{en,de}-{1440,390}-band.png` | 特性带：navy 底 + 白色大标题 + 浅色 `STS Series` kicker |
| `{en,de}-{1440,390}-faq.png` | FAQ 块：左 mist 图片面板（gallery 最后一张 `…product-20261007-02.png`）+ 右手风琴 |

## 数据夹具（只留本地实例，快照重装即还原；仓库无此改动）

- `_linker_faqs` 两行（英文 + `question_de`/`answer_de`，带 citation）写在 6530 与 6565 上——
  快照里没有任何 FAQ 数据，FAQ 块默认不渲染（`linker_commerce_pdp_has_faqs`）。
- 6530 的 `_tv_legacy_acf_json.feature_cards[0].feature_image` 与 6530 的
  `_linker_de_acf_json.feature_cards[0].feature_image` 临时挂上 6504——这是 #174 返工轮记录过的同一做法，
  无图商品（gw30k）的 band 为 0 高不占位不受影响。
- 库存状态由 WP-CLI 翻转（`set_stock_status`），抽查结束后留在 `instock`。

## 实测读数（浏览器计算样式，非截图肉眼）

| 项 | 有货 | 无货 |
|---|---|---|
| `class` | `pdp-dot` | `pdp-dot is-wait` |
| `background-color` | `rgb(12, 127, 115)` | `rgb(249, 115, 22)` |
| 文案 EN / DE | In stock / Auf Lager | Currently unavailable / Derzeit nicht verfügbar |

- 项目入口按钮（EN / DE）：`New system` · `Extend an existing system` · `Replace an existing unit` /
  `Neues System` · `Bestehendes System erweitern` · `Gerät ersetzen`；`[data-linker-assistant-open]` 与
  `.pdp-project-choice--nameplate` 在 DOM 中均为 0 个。
- 特性带 kicker：文本 `STS Series`，`color: rgba(255, 255, 255, 0.75)`（两语言同，来自同一 `product_series` 字段）。
- FAQ 侧图：`goodwe-sts-30-60kw-g10-product-20261007-02.png`（gallery 最后一张 6505）；
  1440 下侧栏 489px、正文栏 733px（原型 2fr:3fr 比例成立）。
