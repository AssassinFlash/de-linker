# #339 回归用例图

战役 #329 已合并修复的通过条件，收成 `services/genie/tests/test_campaign_339.py`。断言仍在原来的测试里。套件把那些测试重导出到本模块：parametrize、skip、xfail、indirect 和 fixture 仍由 pytest 展开，套件自己不展开参数、也不调用被跳过的行。同一次 pytest 既收集本模块又收集原来的文件时，`tests/conftest.py` 去掉原来的那一份，每条通过条件跑一次。不改产品代码，不调用模型。

CI 入口（`just test` 的 `py-test` 会收集这个文件）：

```bash
cd services/genie && uv run --locked pytest tests/test_campaign_339.py
```

计数（夹具长度或本模块 pytest 条目，跳过的不计）：产品词 41，语言 17，填充词 81，重复卡片 1，预填 81，短码 4，降级 2，极值 1，价格门 6，注入 7。

语言条数是 `services/genie/eval/language/cases.json` 的 `cases`。填充词条数是 `services/genie/eval/contact/repeats.json` 的 `pairs`。产品词是 `test_339_product_word_case` 的条目，等于夹具行数，含 #415 的 `339-11-*` 九行。`test_the_goodwe_model_without_a_stored_brand_is_still_named` 另计，不进这个数字。预填、短码、降级、极值、价格门和注入是本模块收集到的对应 pytest 条目。极值只计回退模板；`test_route.py` 与 `SearchProductsTest` 的聚合不进这个数字，它们由 `just test` 收集。重复卡片是 `test_s4_repeat_h2_10k_t3_four_rounds_de_and_en` 的条目。注入是 `tests/test_injection.py` 的 7 个测试，即 #416 的通过条件；套件重导出它们，计数以本模块收集到的条目为准。

## CI 里跑的

| 票 | 缺陷 | 夹具 | 断言 | 命令 |
|---|---|---|---|---|
| #363 #364 #367 | 产品词冲突、一句多型号、缺席断言、故障句。#367 的 F4-DE 是 `EcoFlow GW5K-ETA-G20 - lieferbar?` | `services/genie/eval/regression/339-product-words.jsonl`（含 `339-f4-de` 与 #415 的 `339-11-*`） | `tests/test_regression_339.py::test_339_product_word_case` 与 `tests/test_product_words.py::test_the_goodwe_model_without_a_stored_brand_is_still_named` | 套件重导出这两个测试。`339-6` / `339-7-*` 是缺席断言失败；`339-9-*` 是故障降级句，不说不在范围内 |
| #365 | 预填只带客户明说的参数 | 句子在 `tests/test_prefill.py`（战役句 `DE` / `EN`、否定、后句否认、前导零邮编） | 该文件里 #339 登记的 18 个测试 | 套件重导出这 18 个测试 |
| #366 | 检索重试耗尽是可见降级，不出不相干卡 | 无单独 json；行为在 `tests/test_cycle.py` | `tests/test_cycle.py::test_a_tool_that_always_fails_validation_is_a_visible_degradation` 与 `test_a_products_route_with_nothing_qualified_shows_no_unrelated_cards` | 套件重导出这两个测试 |
| #368 | 极值问题聚合成一个型号。75 kW 问句的聚合不是回退模板 | 无单独 json | 回退模板：`tests/test_ground_understanding.py::test_the_extreme_fallback_names_one_product_in_both_languages`。聚合：`tests/test_route.py::test_smallest_inverter_at_least_30_kw_aggregates` 与 `test_a_matched_model_does_not_narrow_the_extreme`（问句里的 GW75K 不收窄）；`plugins/linker-commerce/tests/php/Unit/Abilities/SearchProductsTest.php::test_smallest_inverter_at_least_30_kw_is_gw30k_eta_g20` | 套件只重导出回退模板。路由测试在 Genie pytest，SearchProductsTest 在 commerce 的 PHPUnit unit，两者都由 `just test` 收集，不重导出 |
| #369 | 三字符型号 `BD-8` 入词表 | `services/genie/eval/understanding/bare_words.json` 里 `note` 为 `#369` 的两条 | `tests/test_lexicon.py::test_the_bd8_question_searches_that_battery` | 套件重导出该测试 |
| #374 | 问什么语言就答什么语言 | `services/genie/eval/language/cases.json`（17 条） | `tests/test_language.py::test_339_language_cases_hold`。整段回答（水合后的正文、价格行、兼容条件、交接句、登录句）仍由 `test_the_hydrated_answer_follows_the_question_on_either_page` 覆盖，套件不复制它 | 套件重导出 `test_339_language_cases_hold` |
| #375 | 填充词不打断重复提议 | `services/genie/eval/contact/repeats.json`（81 对） | `tests/test_contact.py::test_339_filler_corpus_holds_for_every_cut_from_0_to_0_75` | 套件重导出该测试 |
| #376 | 同一配对集合的卡片不漂移 | `services/genie/tests/fixtures/339/manifest.json` 的 `s4-repeat-h2-10k-t3` | `tests/test_pairing_cards.py::test_s4_repeat_h2_10k_t3_four_rounds_de_and_en` | 套件重导出该测试 |
| #242 | 价格门：卡片行等于该账号在商品页上看到的那一行 | `services/genie/tests/fixtures/prices.json` | `tests/test_prices.py::test_a_search_card_shows_what_the_product_page_shows`，`test_a_card_price_for_an_account_not_approved_is_flagged`，`test_a_card_price_no_tool_returned_is_flagged` | 套件重导出这三个测试 |

#373（并发轮次不丢）不在 Genie pytest 里，套件不重写它。`plugins/linker-tools/phpunit.xml.dist` 的 `defaultTestSuite="unit"`，所以 `just test` 的 PHPUnit collects the unit suite, ThreadTest.php among it（`plugins/linker-tools/tests/php/Unit` 下的 `*Test.php`，含 `plugins/linker-tools/tests/php/Unit/ThreadTest.php`）。#373 的 `plugins/linker-tools/tests/php/Integration/ConversationConcurrencyTest.php` 在这套之外；Integration 目录里还有别的测试（`GenieCardLinksTest`、`ConversationListTest`、`GeniePricesTest` 等），它们也不是这个 unit 套件的一部分，各有各的入口。#373 这份由 CI 的 `mu-smoke` job 运行：`just genie-concurrency smoke`（`phpunit -c phpunit.integration.xml.dist --filter ConversationConcurrencyTest`，要一台实例）。

#330 清单有 20 行（`regrade.KEPT_DEFECTS`、`regrade.OVERTURNS`，加上 `round3-runs.jsonl` 里 grade 为 defect 或 parity 的行）。这 20 行没有逐题自动断言，缺口在 #431。D1–D7 对上表里的类级别单元测试，那个测试不断言该行自己的问句。D8–D12、第三轮 A8-DE 和四条 parity 没有合并过的修复。套件只核对这些行仍被登记。

## 待验收

| 票 | 状态 | 夹具 | 本套件做什么 |
|---|---|---|---|
| #412 | 只为线上验收开着。PR #416 已合并（a74116d8）：`prompts/en/system.md` 与 `prompts/de/system.md` 的「引用口令」条款、`agent.py` 的提醒豁免都在本分支 | `services/genie/tests/fixtures/412/i8-persist.json`（`followup` / `defect` 键），登记在 `fixtures/339/manifest.json` 的 `i8-persist` | 套件重导出 `tests/test_injection.py` 的 7 个测试，这就是 #416 的通过条件：清单指向真实 I8 回合、两份提示词同条款、提醒不把文件口令当数字、pre-fix 答案判 defect、抓到的回合判 pass、文件里的 `1 EUR` 仍被拒、PDF 哈希与记录一致。这些不断言模型活回合；活回合留在 #334 harness |

## 留在本地 harness 的

这些要一台装好快照的实例，多数还要模型。`tests/e2e` 的 Playwright 同样要 `just up` 之后的实例，而且 `just test` 不跑 `tests/e2e`。把它们再抄一份进 e2e 不会在 CI 里变成绿，也会和现有规格重复。所以它们留在各自的 harness。

| 票 | 夹具 | 为什么不进 CI pytest | 命令 |
|---|---|---|---|
| #330 | `docs/research/2026-10-20-campaign-330/harness/fixtures/339/manifest.json` | 每一行是 c330 上的真实回合。清单形状的测试已经在 `just test` 里（harness 是 `py_projects` 的一项）。那不是逐题通过条件，逐题断言在 #431 | `cd docs/research/2026-10-20-campaign-330/harness && uv run --locked pytest tests/test_manifest.py`。全电池要实例和模型：`uv run --locked python run_battery.py` |
| #331 | `docs/research/2026-10-20-campaign-331/harness` | 话题、指代、reload、并发要实例。语言、填充词、重复卡片的通过条件已在上表 | `cd docs/research/2026-10-20-campaign-331/harness && node scenarios-direct.mjs`。浏览器：`npx playwright test browser.spec.ts`。先 `just up c331 && just pull load c331 latest && just serve c331` |
| #332 | `docs/research/2026-10-20-campaign-332/harness` | PR #409 已合并（28a42b3a）。该目录在 `py_projects` 里，`just test` 会跑 harness 的 pytest。`run_faults.py` 对本地 Genie 注入 5xx、断流、宕机，不是页面流程，不在默认 pytest 里，也不适合 Playwright | `cd docs/research/2026-10-20-campaign-332/harness && uv run --locked pytest`。故障注入：`uv run --locked python run_faults.py` |
| #333 | `docs/research/2026-10-20-campaign-333/harness/run_battery.py` | 全电池要实例 c333：四个账号、页面、库存推送、询盘卡。该目录在 `py_projects` 里，`just test` 会跑评分器单测（`tests/test_grade.py`，20 条）；全电池本身不在默认 pytest 里。单元测试够得到的价格门在上表，那是 #242，不是本票的通过条件。#414 已由 #418（e2e24389）关闭，集成测试 `InquiryStatusRestTest` 在 CI 的 mu-smoke job（`.github/workflows/check.yml`，`phpunit -c phpunit.integration.xml.dist --filter InquiryStatusRestTest`）。#413 已由 #419（c88c52f1）关闭：`StorefrontTest::test_german_store_products_link_to_the_german_page` 在 `just test` 的 PHPUnit，`CardLinks.test.tsx` 在 `just test` 的 JS；`GenieCardLinksTest` 要实例，不在默认 PHPUnit。缺货回答（#415）已由 #429（8c147c6b）关闭：`339-11-*` 九行在产品词夹具里，套件经 `test_339_product_word_case` 重导出。 | `cd docs/research/2026-10-20-campaign-333/harness && uv run --locked pytest`。自检：`uv run --locked python run_battery.py --self-test` 跑金额与数量正则，并核对已记录日志的计入行。全电池要实例 |
| #334 | `docs/research/2026-10-20-campaign-334/harness/run_battery.py` | 附件和注入的真实回合要模型和实例。评分器单测在 harness 里，该目录在 `py_projects` 里，`just test` 会跑这些 pytest。#412 的离线通过条件在上表（#416 已合并），线上验收仍开着 | `cd docs/research/2026-10-20-campaign-334/harness && uv run --locked pytest && uv run --locked python run_battery.py` |
| #335 | `docs/research/2026-10-20-campaign-335/harness` | 仅 harness。页面漂移和孪生页要实例。该目录在 `py_projects` 里，`just test` 会跑评分器单测；那是 harness 自己的测试，不是本套件的通过条件。语言规则的离线部分是 #374 | `cd docs/research/2026-10-20-campaign-335/harness && uv run --locked pytest`。全电池：`uv run --locked python run_battery.py ~/de-linker-data/campaign-335` |
| #242 页面 | `tests/e2e/specs/genie-prices.spec.ts` | 四个账号在商品页上问 Genie 价格，要实例和模型。CI 跑的是单元测试里的同一条价格门 | `just e2e <instance> genie-prices` |

不调用模型的是上表「CI 里跑的」全部，再加上 `py_projects` 里的 harness pytest。#330、#332、#333、#334、#335 的评分器单测由 `just test` 收集。`run_faults.py`、各战役的全电池、生产问句冒烟和 Playwright 要本地实例或模型，不在默认 pytest 里。
