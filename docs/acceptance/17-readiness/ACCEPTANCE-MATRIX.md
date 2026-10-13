# #17 就绪验收矩阵（2026-10-13 枚举）

枚举来源：t110 sitemap（page 49 / post 22 / product 210 / product_cat 20）、`wc_get_account_menu_items()` 七项、`Inquiry/Statuses.php` 四态、livecanvas 模板清单、docs/specs/11/13/14/19 旅程与状态、交互态探测（`/de/mein-konto/*` 端点 200、德语别名 404、双语 404 探针）。

规则：每格四重门——与基准并排视觉证据（live=像素零差异+申报掩膜；prototype=对照原型）＋功能证据＋deepseek 评审＋主会话终门。**没有证据 = 未验证**。

状态图例：`verified`（差异像素=0 且页高差=0）/ `FAIL`（本轮成对截图，未过像素门）/ `in-flight`（在途线产出中）/ `unverified`（无证据=欠账）。

## 状态汇总

- verified: 0
- FAIL: 静态 132 态维持 2026-10-13 测量（`docs/debt/FRESH-DIFF-STATIC-2026-10-13.md`，数字 `docs/debt/analysis/freshdiff-full-summary.json`）。覆盖 Solution 四页、9 个子分类、FAQ/EPC/capability/Imprint/Privacy/Terms/Refund/Thank-you 静态/Footer closed、Compare 空态+芯片+ids、Shop/Archive filtered+sort 与 390 筛选抽屉、mega×5 开态与 closed、移动抽屉开合、账户 guest 登录表单。没有一格差异像素=0
- 功能面 E2E（2026-10-13 复跑，t110）：**56 过 / 1 败 / 5 跳**（`docs/acceptance/2026-10-13/e2e-and-fixes/README.md`）。配置器 17/17、商务链 EN/DE 全程、访客/批准态价格门、i18n 150 地址、Genie 各 spec 通过；唯一红灯 = DE 商城过滤（旧 LC 模板截流，见"在途项"）
- 已修复待重拍（不写成 PASS）: PDP 静态与指派（present 装配已并，证据 `docs/acceptance/2026-10-13/pdp-present/`）、Genie 工作区/坞开启/页面芯片（#139 已并）、配置器 resident/commercial/utility 全态（引擎数据补迁 + E2E 17/17 过；C 还原已并，证据 `docs/acceptance/2026-10-13/configurator-c-fidelity/`）；配置器页地址已迁 `/solution-configurator/`（`docs/acceptance/2026-10-13/slug-move/`）
- in-flight: 静态 14 页型×EN/DE×两视口（EN 对拍重测/DE 实例对拍）
- unverified: 其余全部（见下）

## 未验证格子（按面分组；基准 / 状态 / 语言 / 视口）

### 账号（登录后）
| 面 | 状态 | 基准 |
|---|---|---|
| Overview | logged-in dashboard | live |
| Inquiries · list with rows | 列表有行 | live |
| Inquiries · empty | 空态 | live |
| Inquiry detail · cancelled / completed / inquiry-received / proforma-issued+PI下载 | 四态各一格（completed/received/proforma 为 functional） | live / functional |
| Saved solutions · empty / with saved solution | functional 为基准的是有数据态 | live / functional |
| Documents · empty / with rows | live |
| Company · address form | live |
| Account details · logged-in form | live |
| Lost password · request / validation error | live / functional |
| Guest login form | live | FAIL。EN/DE × 1440/390。线上居中 Sign in，t110 左右两栏带 Register。EN 1440：1,931,248 px / 91.23% / Δh +506。证据 `docs/debt/FRESH-DIFF-STATIC-2026-10-13.md` |

### 商务功能态
| 面 | 状态 | 基准 |
|---|---|---|
| Registration | 五态：step1 空 / step2 公司 / step3 账户 / 提交待审 / 校验错误 | functional |
| Commerce approval admin | approve / restrict / reject（后台，EN 1440） | functional |
| Commerce price gate | guest 隐价 / pending+restricted / rejected 登录拦截 | functional |
| Proforma request | approved filled / 校验错误（guest 态在对拍内） | functional / live |
| Thank-you | order-received with key / 静态页 | functional / live |
| Solution draft | with lines（有行态；空态在对拍内） | functional |
| Contact | sent / throttled / validation error（空表单在对拍内） | functional |
| Configurator · utility | submitted | functional |
| Configurator · design report | PDF 下载 EN/DE | functional |

### 商品与目录
| 面 | 状态 | 基准 |
|---|---|---|
| PDP | gallery thumb selected / viewer open / spec tab / family picker | live |
| Product archive | filtered / sort changed | live | FAIL。`?brand=goodwe&sort=name`，EN/DE × 1440/390。EN 1440：4,165,749 / 33.89% / Δh +728。DE 落到旧产品家族页（19028 / 45867） |
| Product archive (390) | filter drawer open | live | FAIL。EN 抽屉两侧打开，2,624,038 / 54.84% / Δh −52。DE t110 无 `#catalog-filter-open`（家族页） |
| Shop (390) | filter drawer open | live | FAIL。EN 2,624,191 / 54.92% / Δh −52。DE 同上，点不开抽屉 |
| Shop | filtered | live | FAIL。`?brand=goodwe&sort=name`。EN 1440 同高仍 4,238,325 / 31.86%。DE 落到家族页，Δh +9791 |

### 配置器状态（原型基准，C 还原未覆盖）
| 面 | 状态 |
|---|---|
| residential | calculating / no qualified candidate / solution+swap alternative / validation error |
| commercial | calculating / no qualified candidate / solution with CSV / without CSV→range+inquiry / validation error |
| utility | validation error |
| roof step | map + outline |

### Genie 状态（原型基准）
| 面 | 状态 |
|---|---|
| dock | history failed / pending question |
| product card | pending / added / unverified / retry；saving / saved / failed |
| page chips | account / draft / PDP / catalog search 四入口 |

### 页头
| 面 | 状态 |
|---|---|
| mega × 5（Products/Solutions/Plan/Partners/About） | open（1440，both 语言） | FAIL。EN 点桌面按钮，`aria-expanded=true`。DE 1440 桌面按钮盒 0×0，改点汉堡再展开对应段（两侧都开了；不是桌面 mega）。Products EN 886,691 / 7.45% / Δh 0。Plan DE Δh −74，struct10 5,019,916 |
| mega | closed | FAIL。EN 1,299,525 / 10.92% / Δh 0。DE 1,317,435 / 10.67% / Δh 0。页头带 + 合成差，struct10 仍非 0 |
| mobile drawer × 390 | closed / open+section expanded | FAIL。closed EN 206,658 / 6.00% / Δh 0。open 两侧面板都开；Solutions 缩略图 t110 为空盒。open EN 234,725 / 6.35% |
| account menu | guest / logged-in open |
| 外点/Escape 关闭 | both |

### 静态与内容页（不在 28 态清单的）

全部 FAIL，EN/DE × 1440/390。数字与归因：`docs/debt/FRESH-DIFF-STATIC-2026-10-13.md`。

| 面 | status | evidence |
|---|---|---|
| Solution index | FAIL | 四态页高差 0。EN 1440：762,950 / 9.95%，mag1 93.2%，header10 421，struct10 11,530 |
| Solution residential | FAIL | EN 1440 同高 1,097,401 / 7.95%。其余三态 Δh +25 至 +66 |
| Solution commercial | FAIL | 四态 Δh +41 至 +63。EN 1440：6,536,380 / 42.78% |
| Solution utility | FAIL | EN 1440 Δh +318，8,012,044 / 63.38%。390 本地宽 444/412，不是 390 |
| 9 个子分类 | FAIL | EN 有同高也有 Δh。DE 全部落到旧 “TerraVolt Produktfamilien” 页（1440 高 19028，390 高 45867） |
| FAQ & documents | FAIL | t110 展开全部 details。EN 1440：7,290,825 / 97.99%，Δh +23120 |
| For EPC | FAIL | t110 更短 312–522 px。EN 1440：6,706,588 / 51.22%，Δh −375 |
| About capability | FAIL | 四态页高差 0，mag1 93–99%，页头带仍在。EN 1440 struct10 144，不是 0 |
| Imprint | FAIL | 页高差 0。EN 1440 仅 1,338 px（0.043%），其中 header10 441，正文 y≥90 仍有 540。不记 verified |
| Privacy | FAIL | EN Δh +8，DE Δh −20/−18，另有 struct10 39 万–54 万 |
| Terms | FAIL | 四态 t110 都正好高 8 px，struct10 仍有 6 万–9 万 |
| Refund | FAIL | 同 Terms：Δh +8，不是舍入可抹 |
| Thank-you 静态页 | FAIL | 四态页高差 0，mag1 94–99%。EN 1440 struct10 14。不记 verified |
| Footer closed | FAIL | 四态页高差 0。EN 1440：1,036,178 / 8.71%，header10 441，struct10 12,041 |
| Compare empty | FAIL | EN 1440：1,357,831 / 89.38%，Δh −59 |
| Compare chip | FAIL | EN 两侧芯片可见（线上 “Compare 1”，t110 “Compare 1/4”）。DE t110 无比较控件 |
| Compare table with ids | FAIL | `?ids=6530,6529`。EN 1440：2,156,807 / 94.14%，Δh +451 |

## 已知影响判定的在途项
- **旧 LC 模板族截流（DE 商城/分类档案）**：旧项目遗留 `is_archive_for_post_type_product`（#231/#6915）等 7 对模板仍发布，LC 在 `is_shop_page` 未命中后先解析它们 → `/de/produkte/` 渲染旧家族页（E2E 唯一红灯）。独立工作包：先定分类档案的模板归属，再退役旧族（`docs/acceptance/2026-10-13/e2e-and-fixes/README.md` §3）
- 页头带差异：PR119 后重测（EN 对拍重测覆盖）
- DE 24 空壳：DE 实例补内容后重测（DE 实例对拍覆盖）
- 配置器 C 视觉：已并，重拍后判定
- PDP 结构：present 装配已并并实测，重拍后判定
- ±1 合成差与轮播动态区：掩膜申报单待呈（按规则申报，不擅自施加）
