# #249 像素门（AGENTS.md §5）：页面静止时 live = local

预览卡与它的样式只在首页、产品、分类、解决方案页加载。静止时卡是 `hidden`，`preview.css` 只作用于 `.linker-genie-peek` 和触发后才加的 `.linker-genie--peek`。按 §5，这些页面的整页截图要与线上逐像素一致。

- **线上**：`https://de-linker.com`
- **本地**：`g249` = `http://127.0.0.1:9084`，本分支，快照 2026-10-17 16:42 UTC，构建含 token 化后的 `preview.css`
- **拍摄日期**：2026-10-18
- **工具**：`shoot.mjs`，即 #252 的拍摄工具加一步：每次拍摄前在浏览器自己的 localStorage 里预设 `linker-genie-peek-dismissed-until`（30 天后）
  - 原因：拍摄会滚过整页，等待时间也超过 8 秒停留；不预设的话，卡会在本地截图里正常出现。
  - 线上没有这个键，预设对线上无影响。
  - 比对用 `pixdiff.py`。
- **重跑**：`docs/acceptance/2026-10-18/249/pixel/run.sh <输出目录> http://127.0.0.1:<端口>`

## 结果：掩膜外差异 0，没有掩膜

| 页面 | 1440 | 390 |
|---|---|---|
| `/` | 0 | 0 |
| `/de/` | 0 | 0 |
| `/product/saj-h2-10k-t3/` | 0 | 0 |
| `/de/produkt/saj-h2-10k-t3/` | 0（重拍，见下） | 0 |
| `/product-category/inverters/` | 0 | 0 |
| `/de/produkt-kategorie/wechselrichter/` | 0 | 0 |
| `/solution/residential-storage/` | 0 | 0 |
| `/de/loesung/heimspeicher/` | 0 | 0 |

缩小的左右对照图（左线上、右本地）在 `parity/`。

### `/de/produkt/saj-h2-10k-t3/` 1440 的第一次拍摄

第一次拍摄差 8,711 像素，全部落在页面底部"兼容产品"卡片的缩略图里。对照裁切图：`first-capture-de-product-1440-{live,local}-crop.png`。

差异只出在图片像素：文字、边框、布局都一致。这正是 #252 记录的拍摄陷阱，图片在截图那一刻还没解码完。

同一页面用同一工具立刻重拍一次，差异为 0；表中记的是重拍结果。这一项和预览卡无关：预览卡不在这个区域输出任何东西，样式也不作用于它。
