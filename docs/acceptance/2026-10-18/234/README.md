# #234 Genie 读当前页面 · 验收记录（2026-10-18）

分支 `feat/234-page-context`；实例 `g234`：`just sync g234`（线上快照 20261018-0218）+ `just serve g234`（真实 Genie：Jev 经 OpenRouter `/api/v1/systemone`、deepseek-flash 官方 API、gemini-embedding-2 经 OpenRouter；索引 20261016T072222Z）。
规格：`docs/specs/13-genie.md`"页面感知"一节。

夹具：已登录行用业主测试账号 857558227@qq.com；它在本地实例上的 Lösungsentwurf 为 GoodWe GW110K-ETR-G10 ×2、GoodWe ESA GW10K-EHA-G20、GoodWe GW8.3-BAT-D-G20（本地数据，线上未动）。

## 1. 页面评测（八类页面 × 两问 × EN/DE，32 轮）

- 题目：`services/genie/eval/page/questions.json`；跑法：`services/genie/eval/page/pages.py`。什么都不钉：页面上下文与 dock 发出的相同（类型、地址、标题、ID），Jev 判断是否问本页，路由从实例读页面（或已登录账户的询盘），deepseek-flash 写回答。已登录行每轮用 `UserContext` 现签令牌。
- 自动判：落地、非兜底、非转人工；`reads` 指定的调用确实由路由发出（Jev 判为问本页）；`cites_page` 行引用 `page`；`shows` 行的商品被引用或出卡片；正文命中期望。
- **最终运行 `eval/run-20261018T033006.json`：32/32 通过。** 上一次 `eval/run-20261018T032531.json` 31/32：唯一失分是 DE "Meinen Entwurf prüfen" 的回答以卡片列出两件商品、正文只写品类（模型不写带数字的型号），判据只读正文——判据改为"引用或出卡片"（`shows`），回答本身正确。

逐题读答案（对照页面原文）：

| 页面 | 问题（EN / DE） | Jev 问本页 | 读了什么 | EN | DE |
|---|---|---|---|---|---|
| 首页 | 这页说的 peak shaving / Lastspitzenkappung 是什么意思 | 0.85 / 0.83 | read-page | ✓ 出自工商业储能一节：降需量电费 | ✓ |
| 首页 | 这页说 Linker 供哪几种规模 | 0.87 / 0.84 | read-page | ✓ 住宅、工商业、大型储能，带页面上的功率与容量数 | ✓ |
| 产品（GW10K-EHA-G20） | **这款**有几个 MPPT（没打型号） | 0.97 / 0.98 | read-page + search-knowledge + get-product（本页商品） | ✓ 4 个，手册与本页一致 | ✓ 4 个，每路一串 |
| 产品 | 这页说的 internal bypass 是什么意思 | 0.96 / 0.94 | read-page（+文档） | ✓ 机内 63 A 直通、整屋备电 | ✓ |
| 产品分类（逆变器） | 这页的 MPPT trackers 是什么意思 | 0.93 / 0.93 | read-page | ✓ 独立 MPP 跟踪输入数 | ✓ |
| 产品分类 | 这页列了哪些品牌 | 0.95 / 0.93 | read-page | ✓ EcoFlow、GoodWe、SAJ（筛选器） | ✓ |
| 解决方案（工商业储能） | 这页说的 peak shaving 是什么意思 | 0.91 / 0.91 | read-page | ✓ 峰时放电、守住合同容量 | ✓ |
| 解决方案 | 这页给工商业储能哪些品牌 | 0.93 / 0.92 | read-page | ✓ GoodWe、SAJ、Pylontech 三种架构 | ✓ |
| 博文 | 这篇说的 AC coupling 是什么意思 | 0.93 / 0.95 | read-page | ✓ 独立电池逆变器、改造路线 | ✓ |
| 博文 | 按这篇，什么时候选混合逆变器 | 0.95 / 0.95 | read-page | ✓ 新装 | ✓ |
| FAQ 与文档 | 这页关于兼容清单说了什么 | 0.93 / 0.90 | read-page（118 000 字中选段） | ✓ 跨品牌下单前按清单核对 | ✓ |
| FAQ 与文档 | 按这页能否不同品牌一起下单 | 0.81 / 0.89 | read-page | ✓ 能，统一发票 | ✓ |
| Lösungsentwurf | Check my draft / Meinen Entwurf prüfen | 0.66 / 0.56 | read-page（草稿商品）+ check-compatibility | ✓ 两件商品，配对 released，条件与文档链接 | ✓ freigegeben |
| Lösungsentwurf | What happens next? / Wie geht es weiter? | 0.23 / 0.27 | 模型自己调 `linker_read_page` | ✓ Proforma 请求 → 一个工作日内回复、开 Proforma → 四个状态 | ✓ Arbeitstag |
| 账户（已登录） | 这页上我询盘的状态是什么意思 | 0.91 / 0.92 | inquiry-status（本人询盘） | ✓ | ✓ Storniert |
| 账户（访客） | 我在这页能做什么 | 0.95 / 0.93 | read-page（登录页） | ✓ 登录、忘记密码、注册企业账户 | ✓ |

合计 32 个答案：✓ 32，✗ 0。"What happens next?" 两轮 Jev 判为不问本页（0.23 / 0.27），模型仍自行调用了 read-page 工具（`linker_read_page`）——这是 Jev 不确定时交给 deepseek-flash 决定的既定路径。

## 2. 开场建议随页面变化（浏览器，1440 与 390 × EN/DE）

`tests/e2e/specs/genie-page.spec.ts`，可重跑：

```sh
LINKER_E2E_SHOTS=$PWD/docs/acceptance/2026-10-18/234/screens just e2e g234 specs/genie-page.spec.ts --workers=2
```

结果 **48/48 通过**（八类页面 × EN/DE × {1440 打开、390 打开、1440 真实回答}）。每个"打开"用例断言：mount 的 `data-page` 类型与地址对、开场建议 2–3 条、产品页与分类页的第一条点名本产品 / 本分类。截图 `screens/`：

| 状态 | 文件（EN / DE 同名，前缀 `en-` / `de-`） |
|---|---|
| dock 打开，本页建议（1440） | `1440-{home,product,category,solution,blog,faq,draft,account}-open.png` |
| dock 打开，本页建议（390） | `390-{…}-open.png` |
| 问本页，真实 Genie 回答（1440） | `1440-{…}-answered.png` |

预览卡（#249）改从页面上下文取类型与名字：`PreviewTest` 的页面表（首页、产品 EN/DE、分类、解决方案 EN/DE 有卡；枢纽、About、商城、博文、FAQ、草稿、Proforma、账户、后台无卡）全部通过，卡的文案与锚点不变。静止页面的外观不变：本票只在隐藏的 dock mount 上加了 `data-page` 属性，预览卡与 dock 样式未改。

## 3. 测试

- 服务：`tests/test_page.py`（真实页面夹具：FAQ 选段、博文整读、德语页数字标注、产品页、只读路径、非页面地址、同站重定向、失败显式、缓存、隐藏元素、草稿商品、已登录账户不匿名读）、`tests/test_page_turn.py`（理解层：问本页才读、"这款"＝本页商品、账户＝询盘、草稿＝商品 + 配对、读失败记日志、转人工不读、引用页面数字的回答落地并水合、未读到的页面数字被拒）。
- 壳：`PageContextTest`（八类页面 EN/DE 与 other 的类型、标题、地址、ID；清洗；草稿取访客自己的、英文商品）、`EntriesTest`（每类页面的开场建议、mount 带页面上下文）、`ProxyTest`（代理清洗页面上下文并自己填草稿）、`PreviewTest`、`config.test.ts`（应用读 `data-page`，旧 mount 回落）。
- 文案对抗评审：`copy-review.md`；新建议的实测记录 `eval/chips-20261018.json`。
