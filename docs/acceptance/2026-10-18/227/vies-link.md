# VIES 号码直达查证

2026-10-18，通过 Apify website-content-crawler 读取[欧盟官方 VIES 表单](https://ec.europa.eu/taxation_customs/vies/#/vat-validation)及其 `main.357206a88a995527.js`（版本 7.3.0-HF1）。表单组件初始化 country=null、vatNumber 为空，未读取路由/URL 参数；仅增加 query string 不能实现预填。

同一官方客户端的 checkVatNumber 使用 `ms/{msCode}/vat/{vatNumber}` GET 地址。因此卡片使用 `https://ec.europa.eu/taxation_customs/vies/rest-api/ms/<国家前缀>/vat/<号码>`，从已存 VAT 解析，不采用账单国家覆盖号码前缀。只对可解析且 VIES 支持的国家显示。

Computer Use 使用虚构 `DE000000000` 打开该地址，官方响应的 originalVatNumber 与 vatNumber 都为 000000000，userError 为 INVALID。未用客户 VAT 做外部测试；没有写入本站。该直达查询显示欧盟原始结果，卡片中原有检查线索仍只读 VatProfile 已保存结论。
