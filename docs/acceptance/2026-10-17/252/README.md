# #252 本地与线上同步 + 后台杂项提示 · 验收记录

## 根因

本地认证 / 门禁 / 待审页成了无样式纯文字。根因按时间顺序如下：

1. 2026-10-16 08:18，线上数据库新建了知识库表 `wp_genie_*`。其中 `wp_genie_chunks` 有 33,172 行，用 MariaDB 的 `VECTOR(3072)` 列和 `VECTOR KEY … DISTANCE='cosine'` 子句。
2. 本机 MySQL 9.6 不认识那句子句（1064），装入因此整体失败。之后拉的快照都装不进本地，最新能装的一份停在 2026-10-15。
3. 那份快照里的 WindPress 编译缓存是 10-15 07:30 的。线上 10-16 13:58 重新编译后才有 `.linker-gate-col` 等类，所以本地这些页面缺样式。
4. 只去掉那句子句还不够：MySQL 能收下 VECTOR 列，但 PHP 8.3 的 mysqlnd 读不了这个类型。对该表执行一次 `SELECT *`，整条连接就会失步（"Commands out of sync"）。`wp search-replace` 因此把它之后的表全部标成 skipped，报告"0 replacements"，本地地址一处都没改写。

修法见 `tools/pull/src/linker_pull/load.py` 的 `mysql_compatible`：去掉向量索引子句，VECTOR 列改存同字节数的 VARBINARY。本地 MySQL 本来也没有向量距离函数，检索在本地走 FULLTEXT。

## 一条命令

```
just sync <实例>     # just up → just pull → just pull load <实例> latest
```

`g252s` 是新建的实例，2026-10-17 实测从零到装好用时 10:01。结果 `ok: true`：已发布商品 212/212，附件 2,755/2,755，缺失文件 0，线上地址残留 0，`licences: {seopress-pro: applied, livecanvas: applied}`，快照 `20261017-2018`（taken 2026-10-17T12:26:13Z）。`just status` 的 snapshot 列显示快照时间。

装入现在会带上线上的第三方插件，版本与线上一致：User Switching 1.12.2、Polylang 3.8.11、ACF Pro、Classic Editor、Site Kit、Redis Object Cache。`linker-*` 插件仍来自检出。

## 本地 = 线上（1440，像素）

工具：`shoot.mjs`（同一台机器、每张截图单独启动 Chromium、软件光栅化、sRGB、关掉动画、先把视口撑到整页高度再等图片和字体加载完），比对用 `pixdiff.py`。对象是线上 `https://de-linker.com` 和本地 `g252s`。

| 页面 | 差异像素 |
|---|---|
| 首页 `/` | 0 |
| 产品分类 `/products/` | 0 |
| 产品 `/product/saj-h2-25k-t3/` | 0 |
| 账户（登录）`/my-account/` | 0 |
| 注册 `/my-account/register/` | 0 |
| Proforma 门禁（访客）`/proforma-request/` | 0 |
| `/de/` | 0 |
| `/de/produkt/saj-h2-25k-t3/` | 0 |
| `/de/mein-konto/` | 0 |

缩小后的左右对照图（左线上、右本地）在 `parity/`。

拍摄方法的两处陷阱，实测见 `shoot.mjs` 的注释：

- GPU 光栅化会让同一个本地页面在两次截图里差出 24,117 个像素（渐变抖动，±1–4 级）。
- `sizes="auto"` 的懒加载图片会在整页截图时重新选尺寸、重新请求；本地 PHP 服务器回得慢，截图时图还没到。

这两处修正前，几张页面的"差异"都来自拍摄方法，不是站点本身。

待审页需要一个待审账号的会话，本票没有单独拍；它和门禁页用的是同一组 `linker-gate-*` 类与同一份编译缓存。

## 后台提示

| 提示 | 来源 | 处理 |
|---|---|---|
| LiveCanvas "Please activate your product" | 站点选项 `lc_apikey` 为空（快照会剥离它） | 本地：装入后照线上写入站点 apikey（`licenses.py`）。线上本来就已激活 |
| SEOPress PRO 未激活 | `seopress_pro_license_*` 被快照剥离 | 本地：密钥取自业主文件，状态与到期日照线上写入。线上本来就是 valid |
| SEOPress "81 redirections that needs your attention" | 选项 `seopress_can_post_redirect` | 逐条判断见 `redirects.md`。经业主同意，线上已删除该选项（2026-10-17，备份 `~/backups/2026-10-17-252-admin-notices/`，读回确认已不存在）；6 条新 301 随本 PR 合并后部署 |
| Polylang 设置向导 / Polylang for WooCommerce 推荐 | 选项 `pll_dismissed_notices`（线上原本没有） | 经业主同意，线上设为 `["wizard","pllwc"]`，读回一致 |
| Redis 的 Object Cache Pro 广告 | 员工账号的用户元数据 `roc_dismissed_*` | 经业主同意，线上 ID 1 两项设为 1，读回一致 |

| Site Kit "Congratulations, the Site Kit plugin is now activated"（插件页） | 选项 `googlesitekit_show_activation_notice`，线上值为 1，并随每次快照带到本地 | 经业主同意，线上已删除，读回确认已不存在 |
| SEOPress 重定向里的测试残留 | 文章类型 `seopress_404` 的 ID 3983–3989、3994、3996（测试探针）和 2019–2023（未启用，对应地址已由 linker-tools 的旧地址表 301） | 经业主同意，移到回收站（`post_status=trash`，可恢复；行备份在 `seopress_404_posts.tsv` / `_postmeta.tsv`）。前后对这 10 个来源地址各请求一次，只有测试探针 `/linker-move-probe/` 从 301 变为 404，其余响应不变 |

本地（`g252`，2026-10-17 13:05 UTC 快照，线上清理之后）：后台首页、商品列表、页面列表、插件页顶部都没有任何提示（`admin/local-*.png`）。插件页那条 Site Kit 提示是在线上删除该选项之前带进快照的，第一次显示后就自己清掉了；下一份快照里不会再有。

线上（2026-10-17，清理之后，业主的 Chrome 会话）：后台首页、商品列表、页面列表顶部都没有任何提示；插件页也没有页面顶部的提示，LiveCanvas 横幅和 SEOPress 的"needs your attention"都不在（`admin/live-*.jpg`）。插件页里能看到 5 条"有新版本可用"（Hostinger Reach、LiveCanvas、SEOPress PRO、WindPress、WooCommerce），它们是插件列表行内的更新行，不属于页面顶部的提示，本票不处理。后台首页的"欢迎使用 WordPress"是 WordPress 自带的仪表盘欢迎面板，按用户关闭，也不属于提示条。
