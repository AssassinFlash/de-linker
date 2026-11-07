# 分类/品牌/属性页机械视觉与计数验收（term 批次）

35 个 term URL（product_cat/product_brand/pa_ 属性归档/category 博客分类，EN/DE）× 1440/390，生产只读。证据：`term-visual-selfcheck-20261107.json`（r2 签收批次，最终探针）、`term-counts-20261107.json`（35 页卡片计数提取）。

## 探针批次

- 首跑暴露 11 defect，全部定性：9 个为探针规则 8 盲区（换行 inline 元素的 bounding rect 是多行并集，面包屑加粗尾段盖住同行锚点，overlapRatio 1.0——修复：规则 8 排除 `display:inline`，fixture 增加 near-miss 控件，4 个受影响页修复后 0 defect）；2 个为瞬时加载态（复测不可复现，页面终态全部 0×0/隐藏）；3 个 ERR_TIMED_OUT 重试后全净。
- r2 签收（最终探针）：70 检查、0 defect、0 失败加载、234 review（232 small-target + 2 overflow 轮播态）。

## 计数对账

- 12 对 product_cat/brand 商品分类页 EN/DE 卡片数完全对称（如 inverters/wechselrichter 24/24、home-storage/heimspeicher 9/9、commercial-storage/gewerbespeicher 7/7）；3 对 pa_ 属性归档对称（7/7、24/24、8/8）；9 个博客分类页 article 数=WP-CLI term count（各 2）且 EN/DE 对称。
- WP term count 与页内卡片数的差（如 inverters wp=42 vs 页面 24）是**分阶段发布机制的设计结果**：term count 统计全部 publish 状态 post（含未放行的 staged 商品与工程参考件），页面按 `published_in_current_read` 过滤为客户可见集——与产品数据级核对发现的 Nexans/Trina 行为一致，非缺陷。

## 矩阵更新

70 条 term 视图条目 pending → partially-verified（`term_layout_count_20261107` verified_check）。矩阵剩余 pending = page 40（20 URL）。
