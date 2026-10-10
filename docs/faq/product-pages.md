# 产品页 FAQ 展示验证（快照实例 t15，2026-10-10）

实例：`just up t15` + `just pull load t15 20261010-0033`（快照 106 已发布商品、附件 2755、`ok:true`；插件链接本检出）。模板：`just wp t15 linker-commerce present --user=857558227@qq.com` → `templates: created 4, updated 2`；`plugin activate livecanvas windpress`（快照 load 后这两个许可插件未激活）。

## EN 展示（3 个产品，全部通过）

| 产品 | EN URL | FAQ 行 | data-faq-count | 引文页 |
|---|---|---|---|---|
| SAJ ATS1-T63-A (1178) | `/product/saj-ats1-t63-a/` → 200 | 3 | 3 | 10, 21, 31 |
| GoodWe GW125/261-ESA-LCN-G10 (6321) | `/product/goodwe-esa-gw125-261-esa-lcn-g10/` → 200 | 5 | 5 | 3, 14, 26, 35, 46 |
| EcoFlow OCEAN 2 LFP Battery Base (3608) | `/product/ecoflow-ocean-2-lfp-battery-base/` → 200 | 2 | 2 | 11, 17 |

每个 FAQ 行带 `<summary>`（问题）、答案正文、`文档 URL#page=N` 链接（`linker-faqs` 区块，`docs/faq/*.json` 的 citation 一致）。

## 德语同步

- 字段级：`_linker_faqs` 同一 JSON 携带 `question_de`/`answer_de`（106 行、168 条，`import.py` 写入；`wordpress.php` 在 Polylang 孪生存在时把同一 JSON 镜像到德语商品）。
- 展示逻辑：`ShortcodesTest::test_faqs_uses_german_on_a_german_request`（`pll_current_language()='de'` → 渲染德语问题/答案、不渲染英文）通过。
- 路由级：**未验证**。快照实例上 Polylang 尚无语言（`pll_languages_list()` 空），`wp linker-i18n setup` 建语言后，手工用 `Twins::post` 给 3 个产品建德语孪生时结对失败（`pll_get_post(1178,'de')` 返回 0、同 slug 被改写为 `-2`、`/de/produkt/` 404）。德语孪生与同 slug 路由由 #9 的迁移路径（`tools/migrate/9-i18n.py`，切换时执行）提供；本票不修 #9 插件。验证用的 3 个孪生已删除。
