# H11 · storefront.css 第二族死规则 `sf-checkout-*` · 验收记录（2026-10-16）

清理 `plugins/linker-commerce/content/windpress/storefront.css` 里 `sf-checkout-*`
一族的死规则（#198 评审发现项，debt-sweep 台账 H11）。与 H1 同形：**删除票**——
没有新增行为，验收的全部内容是①证明这些规则真的死了 ②证明删掉后没有任何东西变样。
H1 未定论的部分（「有询盘草稿的结账态」没有构造过，所以 `sf-checkout-*` 是否活着
留了个尾巴）在这里补上：**先把那个状态构造出来实跑，再删**。

## 1. 死亡取证（产出端为零）

选择器要命中，必须有一个元素带 `sf-checkout-*` 类。按下列顺序证明产出端为零：

| 检查 | 命令 | 结果 |
|---|---|---|
| 仓库里的产出者 | `grep -rn "sf-checkout" --include=… plugins/ mu-plugins/ themes/ tools/ services/ tests/` | **22 行，全部在 storefront.css 自己**（即规则本体）；代码零生产者 |
| LC 模板产出端 | `grep -rn "sf-checkout" plugins/linker-commerce/content/livecanvas/` | 零命中（`checkout_page.html` 是 `[linker_checkout]` 短代码壳） |
| 旧实现的产出者 | 快照 `~/de-linker-data/20261010-0027/live/plugins/terravolt-b2b-core/includes/commerce-pages.php:380` | 旧世界确实产过这一族（`<div id="tv-woo-b2b-checkout" class="sf-checkout…">`）；#184 已把 gate markup 换成 `linker-gate-*`，这类只存在于被移除的旧插件里 |
| 实例数据库（四表） | `wp db query` 于 `wp_posts` / `wp_postmeta` / `wp_options` / `wp_usermeta` | **各 0 行** |
| 实例 uploads | 卷内只有 `storefront.css`（含 `.bak`）与编译缓存带载体，其余文件 0 | 见 §3 |
| 运行时（真实页面） | 实例 `nfinal` 335 URL 全量抓取（匿名 + 登录各一遍） | **各 0 命中**（335/335 均 200） |
| 构造态实跑（H1 欠的那一步） | 见 §2 | **16 个构造页面（7 类状态）全部 0 命中** |

### 台账「22 处」的口径

22 = 整个 CSS 文件里含 `sf-checkout` 的**行数**（`grep -c`；字样出现次数是 25，
因为有 1 行出现 3 处、1 行出现 2 处）。家族里 19 条是**整条选择器清单全为死载体**的独立规则（可整块删）；
余下 3 处落在 2 条**混合规则**里——选择器清单里既有死载体又有活选择器
（`form.checkout`、`.form-row`、`.woocommerce-*` 系列），按 H1 同款判定拆开保留活的那几段。

## 2. 构造态实跑（H1 未定论处的补票）

H1 的记录里写着「未构造『有询盘草稿的结账态』实跑」——那正是这一族唯一可能还活着
的状态（旧 receipt markup 只在有草稿时渲染）。本轮把每个状态都构造出来：

| 构造的状态 | 怎么构造 | 会话 | 缓存编译后 `sf-checkout` 命中 |
|---|---|---|---|
| guest + 空草稿结账（EN/DE） | 直接 GET `/proforma-request/`、`/de/proforma-anfrage/` | 匿名 | 0 |
| guest + 有草稿结账（EN/DE） | `/?add-to-cart=6565` 后 GET 请求页 | 匿名 | 0 |
| 已批准客户 + 有草稿（Woo 自己的 checkout 表单；EN/DE） | 真登录（`h11-customer`，approved）+ 加车 | 登录 | 0 |
| 收据 `order-received`（EN/DE） | `wc_create_order()` + `pending` 状态 + `get_checkout_order_received_url()` | 登录 | 0 |
| `order-pay`（EN） | 同上 `get_checkout_payment_url()` | 登录 | 0 |
| 审批门 pending（结账页 + 账号页，EN/DE） | 夹具账号 `h11-pending` | 登录 | 0 |
| 审批门 restricted（结账页 + 账号页，EN/DE） | 夹具账号 `h11-restricted` | 登录 | 0 |

每个状态都做了实际抓取并断言渲染 HTML 里 17 个家族类名 token 零命中；同时确认
收据页渲染的是 WooCommerce 自己的 `Thank you. Your inquiry has been received.`
区块、表单页渲染的是 Woo 的 `form.checkout`，gate 页面渲染的是 `linker-gate-*`
卡片——即「状态本身确实到位了，只是不再有这一族元素」。

## 3. 删除范围与数字

判定按「整条规则的逗号分隔选择器清单全部为死载体」；混合规则**拆开保留**（2 条），
变量块只摘孤儿变量（1 个）：

- 死载体出现次数：**25 处、分布在 22 行**（box-sizing 规则头一行带 3 段、
  860px media 规则头一行带 2 段，其余 20 行各 1 处）
- 删除的规则块：**19**（整块删除数。删除区间整体数的话有 20 个 `{`——第 20 个
  是被拆分改写的那条混合规则尾段的开括号，不属整块删除）
- 删除的选择器部分：**19**（全部在被整块删除的规则里）
- 删除的注释：**0**；随之清空的 at-rule 空壳：**0**（区域里本就没有注释与 at-rule 帧）
- 拆分改写：**2 条混合规则**里共 **3 个死载体部分**被拆掉——
  `#tv-woo-b2b-checkout .sf-checkout-intro,` /
  `#tv-woo-b2b-checkout .sf-checkout-body,`（同一条 `box-sizing` 规则的头两段）
  与 860px media query 里 `… .woocommerce-customer-details .col2-set,` 之后的
  `#tv-woo-b2b-checkout .sf-checkout-facts { grid-template-columns: 1fr; }`
- 附带清理：`--sf-action: #0c7f73` 变量的唯一消费者是删掉的
  `… .sf-checkout-facts dd[data-tv-status-tone="action"]` 规则，随之删除
  （`--sf-action-text` 仍被 `#place_order` 规则使用，保留）
- 字节：**60 080 → 57 738**，净删 **2 342 字节**（文件行数 2148 → 2073）。
  字符口径 60 078 → 57 736（删除区间是纯 ASCII，字符数=字节数，差同为 2 342；
  文件唯一的多字节字符 `—` 存活于两版第 1071 行，不在删除区）
- 存活规则（评审轮复核口径）：删前 375 条简单规则 → 删后 **356** 条，其中
  **353 条逐字节一致**，另 3 条是上面的设计内改写（1 变量块 + 2 混合规则）；
  逐字节幸存的唯一选择器清单 **323** 个（脚本不变量 `missing 0 / changed 0 /
  extra 0` 的含义即此：任何存活规则的文本与原文完全相同）
- 存活注释 12 条逐一相同（`identical content: True`）

### 那几条"看起来像 checkout 却必须留"的规则

- `#tv-woo-b2b-checkout form.checkout, #tv-woo-b2b-checkout .form-row`（`box-sizing`）：
  载体是 WooCommerce 原生类，表单实跑里在场。
- `#tv-woo-b2b-checkout #place_order`、`.woocommerce-notices-wrapper`、
  `.woocommerce-error/-info/-message`、`.woocommerce-billing-fields__field-wrapper`…：
  全部是 WooCommerce 原生类，表单态实测渲染，**承重**。
- `#tv-woo-b2b-checkout .tv-b2b-stagebar`、`#tv-woo-b2b-checkout.tv-woo-status-complete`：
  本条分支的 receipt/stagebar 标记来自**当前实现**（`linker_checkout` 短代码壳 +
  Woo 渲染），实测表单态与收据态均在场。它们和 `sf-checkout-*` 是**不同族**，
  本轮不动。
- `body.woocommerce-checkout .entry-title`、`body.woocommerce-order-* #container-content-page`：
  载体是 WooCommerce 的 body 类，实测在场。

## 4. 像素回归（验收基准 = #184/H1 原型）

删除前后各拍一轮，同一浏览器、同机、同视口、禁动画、等字体图片：

- 轮 A（删前）：`just up nfinal` + `just pull load nfinal 20261015-1852` +
  `just present` + `just windpress-compile`（缓存 678 035 字节，21 处载体）
- 轮 A2（同一份删前代码重拍）用于测量噪声底噪
- 轮 B（删后）：同一实例换装本分支 CSS（`just present` 卷更新）+
  `just windpress-compile`（缓存 **675 677** 字节，−2 358；**载体 0**）

**噪声底噪 = 0**：轮 A vs A2（代码逐字节相同、两次独立拍摄）40 张全部 0 差异像素。

**A vs B = 0 差异像素**，40 个配对，无掩膜（即全页逐字节 RGB 相等）：

| 面 | 视口 | 语言 | 尺寸 | 差异像素 |
|---|---|---|---|---|
| 登录卡 | 1440 / 390 | EN / DE | 1440×1419 / 780×2782、2908 | 0 |
| 注册卡 | 1440 / 390 | EN / DE | 1440×2268 / 780×5052、5224 | 0 |
| 空草稿门（guest） | 1440 / 390 | EN / DE | 1229–1277 / 2630–2852 | 0 |
| 有草稿门（guest） | 1440 / 390 | EN / DE | 1223–1282 / 2604–2834 | 0 |
| 客户结账表单（approved + 草稿） | 1440 / 390 | EN / DE | 1440×2300 / 5788、6066 | 0 |
| 收据（order-received） | 1440 / 390 | EN / DE | 1440×1237 / 2550–2676 | 0 |
| restricted 门（结账页） | 1440 / 390 | EN / DE | 1440×1318 / 2680–2806 | 0 |
| restricted 门（账号页） | 1440 / 390 | EN / DE | 1440×2059 / 4500–4722 | 0 |
| pending 门（结账页） | 1440 / 390 | EN / DE | 1440×1256 / 2556–2682 | 0 |
| pending 门（账号页） | 1440 / 390 | EN / DE | 1440×1436 / 3114–3182 | 0 |

比对是**逐字节 RGB 相等**（无容差阈值），`compare.py` 对尺寸不一致也会失败。

### 拍摄管线的三处工程修正（本轮发现的问题本轮修）

1. **持久购物车**：WooCommerce 把客户的购物车存在 user meta
   (`_woocommerce_persistent_cart_1`)，每轮的 `preVisit` `?add-to-cart=` 都累加数量。
   不重置就会让 A/B 因「数量不同」而不是「CSS 不同」产生像素差。`capture.sh` 在每轮
   开始前先 `delete_user_meta` + 销毁会话。
2. **结算区 AJAX 换装**：Woo 的表单页会在页面加载后再用 AJAX 重写 review 列
   （`update_checkout`），旧 `shoot.mjs` 的 `waitForTimeout(400)` 有时在换装中间按下
   快门——抓到比真值多一个空行的状态。给 `shoot.mjs` 加「review 列 DOM 两次相隔 200ms
   读取一致才拍摄」的等待门（最多 5 秒），A/A2 噪声归零。
3. **`compare.py` 的静默 PASS**：H1 脚本对尺寸不一致的配对只打一行 `SIZE` 就继续，
   末行仍可能显示 `PASS`。修成 mismatch 一旦出现即 FAIL（本轮实测触发了它）。

这三处都在 `.scratch/archive/h11-tools/`（原 hfinal worktree 的 `.scratch/h11-dead-css/`，worktree 收口时归档）的脚本里，随机器留在工作区（按仓库约定
`.scratch/` 不进版本库）；`shoot.mjs` 与 `compare.py` 是从 H1 的会话目录复制的。

## 5. WindPress 编译验证

- `just present nfinal` 把卷内 `storefront.css` 更新为分支版本（md5 与仓库一致：
  `7e0220ddaab6c09d82cc4a206e88bd83`；删前为 `6e7027f2a87334a7620ab7f5394d5fbb`）；
  卷内与仓库同名的样式文件共 16 个，**除 storefront.css 之外的 15 个逐一 md5 相等**。
  卷内 `.bak` 保留删前副本（22 处载体），是回滚的一个 rename。
- `just windpress-compile nfinal`：`{"compiled":true,…,"file_size":675677}`，
  缓存 mtime 更新，anchor classes 检查通过。
- 编译产物 `tailwind.css` 里 `sf-checkout` 出现次数：删前 **21** → 删后 **0**。
- 存活规则确实进了产物（抽查 `#place_order` 3 命中、`.tv-b2b-stagebar` 7、
  `.tv-woo-payment-box` 10、`form.checkout` 16），不是"整块没编进去"。

## 6. 静态与测试

- `just php-check`：五个 PHP 项目 PHPCS + PHPStan level 8 全 `No errors`
- `just php-test`：commerce 1074 / 152 / 113 / 6 通过（commerce 净增 6 条 H9 测试，
  含评审轮补的标题漂移用例），跳过 54（与 main 基线逐项相同）
- `just check` 全绿（含 e2e-check、banned-words、i18n-coverage、build::check）
- `just e2e nfinal specs/empty-draft.spec.ts`（结账门层）：**4 passed**；
  `just e2e nfinal specs/commerce.spec.ts`（**完整商业链**：注册 → 价格 → 草稿 →
  询盘 → Proforma → 下载，EN 与 DE 各 26s/20s）：**2 passed**——这条链真的把一个
  询盘发出去过，是「有草稿的结账态」最强的一次真实走查；
  `just e2e nfinal specs/account.spec.ts`（账号链层，H10 输出路径同轮验证）：**13 passed**——
  被删 CSS 所在层的真实夹具测试

## 7. 结论

产出端为零已由静态（仓库零生产者 + 旧世界生产者随旧插件移除）+ 运行时
（670 次页面抓取 0 命中 + 7 类构造状态 0 命中）双向证实；删除是纯删除（0 条
新增规则，2 条混合规则拆分保留 + 1 个变量块只摘孤儿变量）；除 19 条整块删除
与这 3 处设计内改写外，存活规则逐字节未动；
40 个配对像素差异 0、底噪 0、无掩膜；编译产物无残留类。

H1 留下的那条尾巴（"有询盘草稿的结账态"从未构造）在这里闭合：状态构造过了，
这一族在那里面也不存在。
