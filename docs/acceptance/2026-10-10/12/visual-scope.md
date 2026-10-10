# #12 视觉项归类（2026-10-10，两次方向裁定后）

业主两步裁定：先挂起呈现层（先调研），后批准方案（AGENTS.md PR #55：
现状栈正规化 + WindPress 真用起来）并**反转产品页方向**——产品页与
商城/购物车/结账/账户页走 LiveCanvas 动态模板（lc_dynamic_template +
is_shop_page/is_cart_page/… meta；官方 starter 底稿 modules/templates/），
**#54 的范围**。本文替代此前的 suspended.md 归类。

## 归 #54（本票规格第⑥项的呈现本体）

- 门店模板文件（storefront-single-product.php、
  storefront-archive-product.php、storefront.css/js、ProductView 渲染）
  ——本分支已含前任按旧方向（"LiveCanvas 不参与"）实现的版本，规格⑤
  分类筛选与验收行曾在其上验证通过；#54 以 LC 动态模板 + 短代码重建
  呈现层时**替换**这批文件（顺序交接，非并行撞文件）。分类筛选的
  机制（CatalogFilters pre_get_posts + facet_counts + SelectionFacts
  #7 契约）是数据层，#54 的模板照常消费。
- 门店德语译文（linker-commerce-de_DE_formal.po/.mo）的 msgid 集随
  #54 模板重建同步更新；线上措辞照抄的部分（Kategorie/AC-Leistung/
  Zurücksetzen/Übernehmen 等）直接迁移。

## 本票已完成的视觉项（方向反转后仍然成立）

- **页头页脚两卡 = LC partial 编辑**（官方通道，e3871cf 的迁移走的就是
  partial 内容改写）；德语 = Twins 每语言 partial（W2 修复保证配对，
  /de/ 路由页头页脚德语已验证）。
- **补充二**（logo 两档宽度 104/80、390/1440 无左缘裁切）：实测与线上
  一致，见下。
- **parity 对照对**（20 对 JPEG，本目录 parity/）：五种页型——产品/
  分类/询盘（cart/warenkorb）/账户/home，各 × EN/DE × 1440/390，local
  vs live 并列。判读基线：产品/分类/
  商务页的呈现本体等 #54 落地后重拍；当前对照对记录的是旧方向模板
  的现状（其中分类页卡片网格 760×409、色板字号与线上一致——探针
  数据见下）。

## 探针事实（Playwright getComputedStyle，live vs local，1440）

- logo：两档与线上完全一致——1440 时 104×52（x=49）、390 时 80×40
  （x=16）；工具页 headerLeft=0、无横向溢出（补充二通过）。
- PDP：网格 453×3 三列、购买内盒 413 两侧一致；线上基准值 h1
  30px/600 #15352f、价格 16px/400、SKU 12px/400 #596e67、CTA 44px
  高 12px 圆角 #15352f、区段标题 32px/600。本分支 storefront.css 的
  --sf-* 令牌原只挂在分类页根上（PDP 解析为空的 CSS bug）——已修
  （令牌上移 :root 一处定义）；字号对齐等其余呈现工作归 #54。
- 分类页（已探明、修复归 #54）：缺 H1（线上 Products/Produkte
  46px/600）；rail-help 文案色应 muted 13px、卡宽应侧栏宽；rail-help-btn
  应白字 500 高 40（现掉 Tailwind 链接蓝）；wbcount 应 muted、格式
  "1-24 / 65 product families/Produktfamilien"；桌面 apply 按钮应隐藏；
  线上卡片动作行两钮（View + Add to cart），本地一钮。
- 商务页骨架层（tokens/site-base/footer + lc-header/footer）本地与
  线上一致；内容区设计层（commerce-ui/storefront/contact-*.css）的
  移植归 #11（PR #52 裁定），页型通道归 #54。
