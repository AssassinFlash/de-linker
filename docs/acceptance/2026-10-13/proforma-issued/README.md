# Proforma 号与客户侧下载（2026-10-13）

实例是 `t82`（http://127.0.0.1:8993/），`just up t82` 把插件链到本分支。`t109` 当时挂在别人的 worktree 上并且服务在跑，没有占用。

## 线上基准（只读，de-linker.com）

号由 `tv_b2b_document_reference()` 生成：`DLK-PF-{订单创建年}-{订单 ID}`，修订为 `…-R2`。下单时写入账本（`woocommerce_checkout_order_created` → `tv_b2b_document_ensure_proforma`），不是后台按钮才编。抽查：订单 6559 = `DLK-PF-2026-6559`，订单 3803 = `DLK-PF-2026-3803`。收款账户来自 WooCommerce BACS `woocommerce_bacs_accounts`（线上有一条，含 IBAN）。客户侧详情有 “Open Proforma”，Documents 有 “View / PDF”；作废的文档留在列表里但不给链接。

本站不搬旧账本。号用同一前缀 `DLK-PF`，序号按年递增（`DLK-PF-YYYY-NNNN`），空前缀走默认。已保存的自定义前缀不动。

## 配置要求（不伪造生产账户）

签发门槛只有 IBAN。四项都在 WooCommerce → Settings → Inquiries，没有默认账户：

| 字段 | 选项键 | 签发门槛 |
|---|---|---|
| Account holder | `linker_commerce_bank_holder` | 否 |
| Bank | `linker_commerce_bank_name` | 否 |
| IBAN | `linker_commerce_bank_iban` | 是 |
| BIC | `linker_commerce_bank_bic` | 否 |

IBAN 为空时订单页不显示 Issue Proforma。把状态改成 `wc-proforma-issued` 也不写号、不写 PDF，订单备注记下原因。本次在 t82 上对询盘 #23 实证：备注为 “Enter the bank account under WooCommerce → Settings → Inquiries before issuing a Proforma invoice.”，`_linker_proforma_number` 为空。验收用的测试账户（IBAN `DE02120300000000202051`）用完已删，`iban_after=[]`。

## 本次走通

配置测试账户后：

- Issue 询盘 #27 → `DLK-PF-2026-0003`，状态 `proforma-issued`。后台框：`admin-issued-box.png`。
- 状态路径询盘 #31 → `DLK-PF-2026-0004`，再标 Completed，号仍在。
- 同一次运行里 #24 = `0001`、#25 = `0002`，号按年递增。
- 客户侧详情 #27：`DLK-PF-2026-0003` 与 `?linker-document=proforma&id=27`（`detail-en-1440.png`）。
- Documents：四条都带号和 “Download (PDF)”（`documents-en-1440.png`）。
- Completed #31 详情仍有下载（`completed-en-1440.png`）。

t82 没有德语站（隔离拦截 wordpress.org，账户页也没有 `/de/` 孪生）。把用户 locale 设成 `de_DE_formal` 后页面仍是 `lang=en-US`，所以客户侧截图是英语。德语证据是同一张询盘按 `de_DE_formal` 渲染的 PDF：`proforma-de.html` / `proforma-de.pdf` / `proforma-de-preview.png`。正文含 “Proformarechnung”、“Proforma-Nr. DLK-PF-2026-0003”、“Gültig bis 11. November 2026”、IBAN 四位一组。正式德语标签（同一实例 `switch_to_locale('de_DE_formal')`）：“Proformarechnung (PDF)”、“Herunterladen (PDF)”、“Proformarechnung ausgestellt”。
