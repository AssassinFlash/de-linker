# #339 回归用例图

战役 #329 已合并修复的通过条件，收成 `services/genie/tests/test_campaign_339.py` 一次跑完。断言仍在原来的测试里，这个文件只加载夹具并调用它们。不改产品代码，不调用模型。

CI 入口（`just test` 的 `py-test` 会收集这个文件）：

```bash
cd services/genie && uv run --locked pytest tests/test_campaign_339.py
```

计数（每次调用算一条）：产品词 18，语言 17，填充词 81，重复卡片 1，预填 81，短码 4，降级 2，极值 1，价格门 8，注入 1。

## CI 里跑的

| 票 | 缺陷 | 夹具 | 断言 | 命令 |
|---|---|---|---|---|
| #363 #364 #367 | 产品词冲突、一句多型号、缺席断言、故障句 | `services/genie/eval/regression/339-product-words.jsonl` | `tests/test_regression_339.py::test_339_product_word_case` | 上面的套件。`339-6` / `339-7-*` 是缺席断言失败；`339-9-*` 是故障降级句，不说不在范围内 |
| #365 | 预填只带客户明说的参数 | 句子在 `tests/test_prefill.py`（战役句 `DE` / `EN`、否定、后句否认、前导零邮编） | 该文件里 #339 登记的 18 个测试 | 套件 `test_prefill_keeps_only_what_the_customer_stated` |
| #366 | 检索重试耗尽是可见降级，不出不相干卡 | 无单独 json；行为在 `tests/test_cycle.py` | `tests/test_cycle.py::test_a_tool_that_always_fails_validation_is_a_visible_degradation` 与 `test_a_products_route_with_nothing_qualified_shows_no_unrelated_cards` | 套件 `test_retry_exhaustion_is_a_visible_degradation` |
| #368 | 极值问题聚合成一个型号 | 无单独 json | `tests/test_ground_understanding.py::test_the_extreme_fallback_names_one_product_in_both_languages` | 套件 `test_an_extreme_fallback_names_one_product` |
| #369 | 三字符型号 `BD-8` 入词表 | `services/genie/eval/understanding/bare_words.json` 里 `note` 为 `#369` 的两条 | `tests/test_lexicon.py::test_the_bd8_question_searches_that_battery` | 套件 `test_short_body_questions_search_bd8` |
| #374 | 问什么语言就答什么语言 | `services/genie/eval/language/cases.json` | `tests/test_language.py::test_339_language_cases_hold`。整段回答（水合后的正文、价格行、兼容条件、交接句、登录句）仍由 `test_the_hydrated_answer_follows_the_question_on_either_page` 覆盖，套件不复制它 | 套件 `test_language_cases_follow_the_question` |
| #375 | 填充词不打断重复提议 | `services/genie/eval/contact/repeats.json`（81 对） | `tests/test_contact.py::test_339_filler_corpus_holds_for_every_cut_from_0_to_0_75` | 套件 `test_filler_pairs_hold_across_the_cut` |
| #376 | 同一配对集合的卡片不漂移 | `services/genie/tests/fixtures/339/manifest.json` 的 `s4-repeat-h2-10k-t3` | `tests/test_pairing_cards.py::test_s4_repeat_h2_10k_t3_four_rounds_de_and_en` | 套件 `test_repeat_cards_keep_the_released_set` |
| #242 | 价格门：卡片行等于该账号在商品页上看到的那一行 | `services/genie/tests/fixtures/prices.json` | `tests/test_prices.py::test_a_search_card_shows_what_the_product_page_shows`，加上未获批账号不出价、无工具价被标出 | 套件 `test_the_account_price_gate_is_the_page_line` |
| #412 | 注入旁边的合法数据要引用，指令不执行 | `services/genie/tests/fixtures/412/i8-persist.json`，登记在 `fixtures/339/manifest.json` 的 `i8-persist` | 套件 `test_injection_data_is_quoted_and_the_instruction_is_not`：读入文本含 `ZEPHYR-C334`；问句不构成询盘，指令句构成；引用口令的回答通过接地；`{fact:…}` 打出文件里的 `1 EUR` 被拒绝。提示词里「引用口令」那几句在 PR #416，未进 main，这里不断言 | 同上 |

#373（并发轮次不丢）的单元测试不在 Genie pytest 里。`just test` 已经收集 `plugins/linker-tools/tests/php/Unit/ThreadTest.php` 和 `plugins/linker-tools/tests/php/Integration/ConversationConcurrencyTest.php`。套件不重写它们。

#330 清单 `docs/research/2026-10-20-campaign-330/harness/fixtures/339/manifest.json` 有 20 行。D1–D7 对上表里的单元断言。D8–D12、第三轮 A8-DE 和四条 parity 没有合并过的修复，套件只核对它们仍被登记，不当成已通过。

## 留在本地 harness 的

这些要一台装好快照的实例，多数还要模型。`tests/e2e` 的 Playwright 同样要 `just up` 之后的实例，而且 `just test` 不跑 `tests/e2e`。把它们再抄一份进 e2e 不会在 CI 里变成绿，也会和现有规格重复。所以它们留在各自的 harness。

| 票 | 夹具 | 为什么不进 CI pytest | 命令 |
|---|---|---|---|
| #330 | `docs/research/2026-10-20-campaign-330/harness/fixtures/339/manifest.json` | 每一行是 c330 上的真实回合。清单形状的测试已经在 `just test` 里（harness 是 `py_projects` 的一项） | `cd docs/research/2026-10-20-campaign-330/harness && uv run --locked pytest tests/test_manifest.py`。全电池要实例和模型：`uv run --locked python run_battery.py` |
| #331 | `docs/research/2026-10-20-campaign-331/harness` | 话题、指代、reload、并发要实例。语言、填充词、重复卡片的通过条件已在上表 | `cd docs/research/2026-10-20-campaign-331/harness && node scenarios-direct.mjs`。浏览器：`npx playwright test browser.spec.ts`。先 `just up c331 && just pull load c331 latest && just serve c331` |
| #332 | PR #409 的 `docs/research/2026-10-20-campaign-332/` | 未合并，本分支没有这棵目录。合入后仍是对本地 Genie 注入 5xx、断流、宕机，不是页面流程，不适合 Playwright | 合入后：`cd docs/research/2026-10-20-campaign-332/harness && uv run --locked pytest && uv run --locked python run_faults.py` |
| #333 | `docs/research/2026-10-20-campaign-333/harness/run_battery.py` | 四个账号、页面、库存推送、询盘卡要实例 c333。单元测试够得到的价格门在上表。待审/受限询盘金额（#414）、缺货回答（#415）、德语永久链接（#413）仍是开着的缺陷，不在本套件里写成通过 | `python3 docs/research/2026-10-20-campaign-333/harness/run_battery.py --self-test` 只跑金额正则。全电池要实例 |
| #334 | `docs/research/2026-10-20-campaign-334/harness/run_battery.py` | 附件和注入的真实回合要模型和实例。评分器单测在 harness 里，该目录不在 `py_projects`，所以不进 `just test`。I8 的数据侧通过条件在上表 | `cd docs/research/2026-10-20-campaign-334/harness && uv run --locked pytest && uv run --locked python run_battery.py` |
| #335 | `docs/research/2026-10-20-campaign-335/harness` | 页面漂移和孪生页要实例。评分器单测已经在 `just test` 里（harness 是 `py_projects` 的一项）。语言规则的离线部分是 #374 | `cd docs/research/2026-10-20-campaign-335/harness && uv run --locked pytest`。全电池：`uv run --locked python run_battery.py ~/de-linker-data/campaign-335` |
| #242 页面 | `tests/e2e/specs/genie-prices.spec.ts` | 四个账号在商品页上问 Genie 价格，要实例和模型。CI 跑的是单元测试里的同一条价格门 | `just e2e <instance> genie-prices` |

不调用模型的是上表「CI 里跑的」全部，加上 #330 / #335 harness 里已进 `just test` 的评分器测试。标成 harness 的命令会打到本地 Genie 或生产问句冒烟，不放进默认 pytest。
