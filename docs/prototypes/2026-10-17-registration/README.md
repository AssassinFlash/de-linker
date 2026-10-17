# 原型：注册表单按研究结论改（#225，地图 #220）

**一次性原型，不进生产。** 依据：#224 的结论（`docs/research/2026-10-17-registration-fields/DOSSIER.md`）与业主 2026-10-17 的回答：不收电话；业主按注册信息自己查证，属实即批；全部国家开放，欧洲为重点；批准后发邮件通知客户。

## 表单内容（三个变体相同）

9 个输入，7 个必填，另加"网站或 VAT ID 至少填一项"：

| 组 | 字段 | 说明 |
|---|---|---|
| Your company | Company name * | |
| | Business type * | 三个单选块：Installer / EPC contractor / Distributor（`linker_customer_role` 现有三个值） |
| | Country * | 默认 Germany；列表分 Europe（Germany 置顶，其余按字母）和 Other countries；可输入搜索；数据是 Woo 自己的国家表和 `EU` 大洲 |
| | Company website / VAT ID | 放在同一个浅底框里，上方一句"We use one of these to verify your company. Fill in at least one."。VAT 下方保留现有 VIES 说明 |
| You and your sign-in | First name * / Last name * | 同一行 |
| | Email address * | "You sign in with it, and we send the approval here." |
| | Password * | 现有密码提示照旧 |

从注册里拿掉的：街道、邮编、城市，由 Proforma 请求页（Woo 结账页）的原生账单字段收；电话不收，需要时由结账页的原生电话字段收。分组不编号（线上 10-15 验收版有 1/2/3，去掉编号属于裁定变更，进变更台账）。

防机器人：隐藏的蜜罐字段 + 最短填写时间。原型里阈值先写 3 秒，正式值上线后按真实填写时长定。被拦时不建号、不发信，计一次数。底部黄色调试框显示判定结果和"会保存的字段"，仅原型有。

成功页：说明是人工审核，批准后发邮件到客户填的地址；审核期间可以以访客身份浏览和发询盘（#246）。不承诺审核时长，业主没有给过。

## 三个变体（`/my-account/register/?reg=A|B|C`，底部切换条或 ← → 键）

| 变体 | 做法 |
|---|---|
| **A · 单页两组**（研究推荐） | 先公司，后您和登录，一页填完 |
| **B · 两步** | 第 1 步公司（Continue 时先校验），第 2 步您和登录；顶部两段进度条 |
| **C · 单页，先您和登录** | 字段同 A，顺序反过来 |

外观照线上认证卡：桌面端左侧绿色渐变面板（文案照旧）+ 右侧白卡；手机端照线上 390 px 的样子隐藏绿色面板，白卡圆角、两侧留边。输入框、按钮、字号都是在线上量出来的值（Inter，52 px 高，`#EEF1F1` 底，药丸按钮 `#0C7F73`）。

## 怎么看

1. `just up m4check`，退出登录（注册页只对访客显示）。
2. 打开 `http://127.0.0.1:9033/my-account/register/?reg=A`。
3. 想看拦截效果：点切换条上的 **Bot**（相当于机器人填了蜜罐），再点 Register。

截图在 `screens/`：每个变体 1440 和 390 各一张；A 另有错误态（`-errors`）和国家搜索（`-country-view`，输入 "ös"）。

## 文案

原型里的英文是初稿。按 AGENTS.md，实现票里 EN 先定稿，DE 独立撰写，两种语言都走文案对抗评审，评审记录入库。

## 选定之后

在 #225 记下选了哪个、为什么。实现票照选定变体改 `plugins/linker-commerce/includes/Registration/Fields.php`，新增网站字段（通知邮件和后台账户页显示同一套字段，#226）。防机器人挂 `woocommerce_register_form` 和 `woocommerce_process_registration_errors`，在建号之前拦截。
