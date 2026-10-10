# #12 机制项证据（2026-10-10，t12 实例 http://127.0.0.1:8900，快照 20261010-0033）

边界注记：业主 2026-10-10 呈现层方法论裁定后，本票**视觉实现与 parity
视觉验收挂起**（见 suspended.md）；本文只记机制项证据。产品页模板的
机制部分（Woo 原生字段生效）在前任提交 bde0272 已验，摘录于下。

## ① /design-canvas/ 跳转（规格②）

    $ for u in /design-canvas/ /de/design-canvas/ /quote-configurator/ /de/angebots-konfigurator/ /de/entwurfsflache/; do curl -so /dev/null -w "%{http_code} %{redirect_url}\n" "http://127.0.0.1:8900$u"; done
    301 http://127.0.0.1:8900/linker-planner/?step=roof
    301 http://127.0.0.1:8900/de/linker-planer/?step=roof
    301 http://127.0.0.1:8900/linker-planner/
    301 http://127.0.0.1:8900/linker-planner/
    301 http://127.0.0.1:8900/linker-planner/
    $ curl -so /dev/null -w "%{http_code}" "http://127.0.0.1:8900/linker-planner/?step=roof"
    200

## ② LiveCanvas（规格③）

实例运行 **4.9.5**（规格目标 4.9.4 的后继，前任会话自
`~/de-linker-data/livecanvas-4.9.5/` 安装；快照与线上是 4.9.3——升级是
本地先行验证）。JSON 前缀 bug 的修复在 4.9.5 验证：

    $ curl -sI "http://127.0.0.1:8900/wp-json/wp/v2/pages?page=2" | grep -i content-type
    Content-Type: application/json; charset=UTF-8
    $ curl -s "http://127.0.0.1:8900/wp-json/wp/v2/pages?page=2" | head -c 120
    [{"id":1035,"date":"2026-06-16T21:01:09",...   ← 纯 JSON，无 HTML 前缀
    $ wp plugin get livecanvas --field=version   → 4.9.5

复现性（评审必改③后）：LIVECANVAS_VERSION=4.9.5 已钉进
tools/local wordpress.py 的 PINNED，versions() 读
livecanvas/livecanvas-plugin-index.php 头；来源注释记档（本机
de-linker-data 归档、快照仍 4.9.3、reset 后漂移由 up 的警告可见是
预期——升级步骤待线上升级后由快照承载）。

## ③ 页头菜单大图懒加载（规格⑧，Playwright 实测，2026-10-10 评审修正后）

    范围按文件口径：页头 partial 共 13 张 img —— 12 张转为 data-src
    （桌面菜单 7 张原带 loading="lazy" + 移动 rail 卡 5 张 webp≈1.4MB，
    原选择器只命中前者，评审 F2 后迁移改为"除 eager logo 外全部转
    data-src"），1 张 eager（品牌 logo）。

    首页（EN/DE 同）菜单关：页头 12 张 img 标签自身发起的请求 = 0；
    网络面板出现的 uploads 请求全部来自页面正文自己的 <img>（含与页头
    共用同一文件的 utility-scale-bess.webp —— 文件级请求是正文的，非
    菜单泄漏）。
    移动 390：点开 rail 的 summary → 该 details.tv-mobile-section 内
    3 张图水合（src 写回、文件加载）；未开的 section 保持 data-src。
    桌面：鼠标移到导航 → 对应菜单水合。水合目标已含
    details.tv-mobile-section 与 summary→details 的上溯（评审 F2 的
    JS 半边）。

## ④ 营销页悬停脚本只入队模块页（规格⑦机制侧）

    /solution/   marketing-hover.js enqueued: true（注：slug 是单数；
                 早前记录的 /solutions/ 是 302→首页，首页也有模块，
                 故当时读数也真，但地址写错了）
    /faq-download/ marketing-hover.js enqueued: false
    /            marketing-hover.js enqueued: true
    触发器选择器单源于 PHP（SiteChrome::MODULE_TRIGGERS）经
    wp_add_inline_script 以 window.linkerHoverTriggers 传入（评审建议：
    消除 PHP/JS 双写）；实例渲染核对：inline 变量含全部 9 个选择器。
    脚本自身门控 matchMedia('(hover:hover) and (pointer:fine)')，
    触摸/键盘路径不经过它；切换走各页自己的 click()。

## ⑤ 分类筛选接 #7（规格⑤，前任 a2c6666 已验，摘录）

filter-consistency.md：?phase=1→16、?application=home→38、
?brand=goodwe→27、?power=top→10 与线上逐项一致（phase/家庭数为 #7
产品化修正）。本票后续又修德语侧两个缺口（见下）。

## ⑥ 承接 #9：120 德语 URL

de-urls-verify.txt（归档完整）：150 条线上德语 URL 中 148 条 200 且
lang=de-DE；2 条为本票 301 退役地址（/de/entwurfsflache/、
/de/angebots-konfigurator/，规格②的预期行为）。

## ⑦ 本会话补的两个机制缺口

1. **门店德语**（linker-commerce storefront）：德语分类/单品页原漏
   英文（无 de_DE_formal 译文 + SelectionFacts 只认英文术语 slug）。
   修：languages/linker-commerce-de_DE_formal.po/.mo（63 条，措辞照
   线上德语页，评审 copy-review.md §11）；SelectionFacts 经
   `linker_commerce_facts_product_id` 过滤器由 linker-i18n 的
   Languages::source_post 解析到英文孪生（一条事实一个实现）。
   验证：/de/produkte/ 七 facet 与线上德语页同名同序、1/3-phasig、
   四功率桶全德语；/de/produkt/saj-hs3-6k-t2-w-p/ 门店串英文零残留
   （grep 'Item number:|In stock|Sign in for|…' = 0）。
2. **Twins 配对 bug（W2，#11 移交）**：源 partial 无语言时
   pll_save_post_translations 静默不配对。修：Twins::post/term 经
   ensure_post_pair/ensure_term_pair 在配对前保证两侧语言（新建与更新
   两分支都走，重放即修复）；新 CLI `wp linker-i18n repair-partials`
   按角色元数据（is_header/is_footer，低 ID=快照源）修复既有实例；
   9-i18n apply 在 import 前先跑修复（先修后导，避免重复铸造孪生）。
   t12 实测：17(en)+6909(de)、18(en)+6911(de) 组 912/913 健康，
   repair-partials 报 0 repairs（早前"6909=en"为我 SQL 别名笔误）。

## ⑧ W1：快照插件按线上 active 表激活（#11 移交）

tools/local snapshot.install 读快照 site/plugins.json，只激活线上
active 的插件（无该文件回退全激活，测试夹具不变）；配 2 个单测 +
1 个栈测（真实实例 up --snapshot：fixture-live active、
fixture-retired inactive）。
