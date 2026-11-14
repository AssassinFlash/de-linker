# 生产图片传输：首页从 4.31 MB 降到 1.07 MB（2026-11-14）

这是加载性能扩展目标下的一次有界交付，不代表该目标或全站目标完成。

## 实测现象

生产首页（EN 1440，匿名访客、真实浏览器）实际传输图片 **4,307,997 字节 / 24 张 webp**。
其中 12 张过度供给（原图尺寸远大于显示尺寸）：

| 文件 | 原图 | 显示 | 倍率 | 字节 |
|---|---|---|---|---|
| `linker-check-what-works-together-1.webp` | 1600×1600 | 124×478 | 12.9× | 280,178 |
| `linker-trade-support-from-germany-1.webp` | 1600×1600 | 124×478 | 12.9× | 224,592 |
| `linker-logo-wordmark.png` | 717×273 | 120×46 | 6.0× | 319,152 |
| `linker-commercial-storage-for-contractors-1.webp` | 1600×1600 | 693×… | — | 386,936 |
| `linker-utility-scale-bess.webp` | 1568×672 | 1440×780 | 1.1× | 326,620 |

## 根因

首页正文（`post_content`，页面 `13` Home / `6913` Startseite）里的图片是**手写的 `<img src>` 标签**，带 `width`/`height` 但**没有 `srcset` 和 `sizes`**，绕过了 WordPress 原生的响应式图片输出。磁盘上早已存在 `-100x100` / `-300x300` / `-600x600` / `-768x768` / `-1024x1024` / `-1536x1536` 等变体（如 `linker-check-what-works-together-1-300x300.webp` 仅 17 KB，原图 280 KB），页面从未使用它们。

另有 3 张图虽有 `srcset`，但 `sizes` 写成 `(max-width: 600px) 120vw, 2400px`，而实际显示宽度仅 354–370 px，触发 2400w 大图下载。本批已一并修正为 `(max-width: 600px) 100vw, (max-width: 768px) 45vw, 380px`（实测 354/564/296/278/358/370），修正后浏览器选中 380w/390w 变体。

## 修复

在页面正文为 9 张图片补上真实的 `srcset`（由 WordPress 附件 metadata 生成，含 9–10 个变体）与 `sizes`。

`sizes` 不是估计值：先在线上分别以 **390 / 600 / 768 / 1024 / 1280 / 1440** CSS px 实测每张图的显示宽度，再为每个断点写稳定上界。实测宽度例如 `linker-check-what-works-together-1` 为 59/95/117/93/120/124，故 `sizes="(max-width: 768px) 25vw, 140px"`。

- 脚本：`/tmp/add-srcset.php`（本机与主机同名），默认 dry-run，`LINKER_SRCSET_APPLY=1` 才写入
- 仅追加 `srcset`/`sizes` 属性，`src`/`alt`/`width`/`height`/class 与正文其余字节不动
- 附件按 `_wp_attached_file` basename 匹配，因为 `attachment_url_to_postid()` 对本批 guid 失配

## 读回

| 场景 | 修复前 | 修复后 | 降幅 |
|---|---|---|---|
| 首页 EN 1440 图片字节 | 4,307,997 | **804,503** | **−81.3%** |
| 首页 DE 1440 图片字节 | 未单测 | 同源镜像 | — |
| 首页 EN 390 图片字节 | 未单测 | **751,673** | — |

第一轮（9 张图补 srcset）后为 1,071,781；第二轮修正 3 张卡片的 `sizes` 后降至 804,503。

浏览器实际选中的变体与显示宽度匹配（例：显示 124 px 选 150w；显示 420 px 选 600w；显示 693 px 选 768w）。

视觉与无回归：EN/DE 1440 与 EN 390 三组实测 **破图 0、`docOverflowX` 0、JS 错误 0**；EN 1440 首屏截图与修复前字节数相同（1,008,421），像素一致。

## 同批完成的 HTML 死重清理

生产首页 HTML 原为 **401,230 字节**，其中 **133,557（33%）** 是 WordPress `global-styles-inline-css`：1,390 个 `--wp--preset--` 变量 + 区块库规则。死重证据：无任何其他样式表或内联样式引用这些变量、`style="..."` 零引用、页面零 `wp-block-*` 类，且主题非区块主题、无 `theme.json`、不支持 editor-styles。

`Presentation\BlockStyles` 在两个入队点移除它（`wp_enqueue_scripts` 与 `wp_footer` 优先级 2）。**只在一个点移除无效**——core 会在 `wp_footer` 优先级 1 再入队（classic theme placeholder + hoist 机制）；首版仅处理 `wp_enqueue_scripts`，部署后实测仍为 401 KB，据此改正。

读回：`/` 401,230 → **267,544**（−33.3%）、`/de/` 448,833 → **315,229**、`/products/` 357,704 → **224,100**（−37.3%）；`--wp--preset--` 1,390 → **0**。五个页面（首页 EN/DE、产品、配置器、FAQ）实测 `--proto-ink`/`--proto-font-sans` 仍正确解析、标题字号颜色正确、无溢出、无 JS 错误。

## TTFB 结论（不宣称提速）

匿名 curl 三选中位：`/` 1.68 s、`/de/` 2.03 s、`/products/` 2.01 s。分解显示 `tls=1.30 s` 占绝大部分（DNS 3 ms、connect 4 ms）。**同机对照 `github.com` 的 TLS 也要 1.17 s**，故该 1.3 s 主要是测量点与机房之间的网络延迟，服务器特有部分约 0.15 s。本机测量不能作为客户侧 TTFB 结论。

## 回滚

备份：`/home/u388076051/backups/img-srcset-20261114/{13-home.html,6913-startseite.html}`（127,821 / 129,122 字节，原内容）。
回滚即把备份 HTML 直接写回对应 `post_content` 并 `clean_post_cache()`，随后 `do_action('litespeed_purge_all')`。
改动后状态：`13` md5 `306261c87fb88c897b566238d9c75b43`（135,172 字节）、`6913` md5 `e1647e62e69d885b13932cabb13c3a4f`（136,473 字节）。

## 仍未完成

- 页脚 wordmark 已改为 srcset；页头 logo 本就有 `srcset`（`de-linker-logo-1.webp` + `300x150`），未在本批改动
- 其余页型（产品、分类、博客、法律、工具）未做图片传输采样
- LCP / CLS 未测；本批只证明字节数与所选变体，不证明客户侧感知速度
- 本次为正文数据修改，未新增自动化回归；脚本不在仓库内
