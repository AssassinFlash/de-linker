# 账户视觉同步 · 证据覆盖核对

核对日期：2026-10-12。只记录本工作树这次读到的代码、本地实例查询和已有验收文件。不补造截图。

## 已有验收文件

- `after.json`：32 组合（EN/DE × 1440/390 × 8 页），`status` 全是 200，`overflow` 全是 false。
- `guest-result.json`：4 页，`logged` 全是 false，`privateContent` 全是 0，`login` 全是 1。
- `behavior-result.json`：EN/DE 各一条 open-tab 与一条 other-owner（他人询盘 `hasDetails`/`hasSummary` 为 0）。
- `after.json` 的页面正文摘录没有导航菜单文本。菜单七项不从这些摘录推断。

## 菜单七项

本地实例 `acctsync`（`http://127.0.0.1:8987`，工作树即本目录）上执行：

```text
just wp acctsync eval '… wc_get_account_menu_items() …'
```

输出：

```text
COUNT=7
dashboard	Overview
orders	Inquiries
saved-solutions	Saved solutions
documents	Documents
edit-address	Company
edit-account	Account details
customer-logout	Log out
```

来源是 Woo 的 `wc_get_account_menu_items()`，过滤器挂在 `plugins/linker-commerce/includes/Account/Menu.php` 的 `items()`（`woocommerce_account_menu_items`，priority 20）。七项里没有 Downloads、Payment methods。线上九项没有在这次核对里重新抓取；本次没有线上对照截图。

## 询盘四状态

分组与阶段条的状态键写在 `plugins/linker-commerce/includes/Presentation/AccountTemplates.php`：`Statuses::RECEIVED`、`Statuses::PROFORMA`、`completed`、`cancelled`。显示名走 `wc_get_order_status_name()`。计数来自 `wc_get_orders()`，按 `customer_id` 与这些状态过滤，不是写死的数字。

同一本地库的 HPOS 表（`just wp acctsync db query`）：

```text
SELECT status, COUNT(*) c FROM wp_wc_orders GROUP BY status
wc-cancelled        53
wc-on-hold           5
wc-checkout-draft    2

SELECT status, COUNT(*) c FROM wp_wc_orders WHERE customer_id=3 GROUP BY status
wc-cancelled        49
wc-checkout-draft    1

SELECT id, status, customer_id FROM wp_wc_orders WHERE id=5432
5432  wc-cancelled  3
```

`wp_wc_orders` 里没有 `wc-inquiry-received`、`wc-proforma-issued`、`wc-completed`。登录账户（customer 3）的已存储询盘全是 `cancelled`。所以 `after.json` 里 Inquiry received / Proforma invoice issued / Completed 的计数为 0、Cancelled 为 49，与存储一致。询盘 #5432 的阶段条只有 Cancelled 为当前步，也与 `wp_wc_orders.status = wc-cancelled` 一致。

缺的证据：received、proforma、completed 三态没有对应的已存储订单，因此没有这三态的页面截图。不补造。

## 无支付、无发货、无发信

本次新增与改动的账户呈现文件（`AccountTemplates.php`、`templates/myaccount/livecanvas.php`、`content/livecanvas/account/`）没有 `wp_mail`、没有支付或发货动作。菜单过滤器显式丢掉 `downloads` 与 `payment-methods`。账户页仍是询盘列表、公司资料、账户资料、文档与已存方案；不新增菜单项。

这次核对没有重放邮件队列，也没有在生产发信。无发信的结论限于：这些改动文件不含发信调用。
