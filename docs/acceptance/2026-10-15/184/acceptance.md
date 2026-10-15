# #184 验收记录（2026-10-15/16）

## 验收三件套

### 1. Spec + Standards 双评审（merge-base 3ef8fcd0 → 返工后 eabd5cb5）

独立评审子代理首轮结论：Spec 轴 FAIL ×3（文案评审记录与实交不符、重置表单无真实夹具测试、spec 计数过期）+ Standards FAIL ×1（.pot 缺 22 条新 msgid）+ 判断项 5；其余 PASS（Woo 覆写字段/nonce/hook 逐字保留、映射 guest/登录态条件、登出 nonce URL 安全、页头 guest 单条、.po/.mo 一致、禁词零命中、is-loading 提交语义有测试守）。
返工逐项落地：记录改实（站上既有 Partner-Konto 形态）、重置标签改 linker-commerce 域使定稿生效、计数统一 26 条、重置链真实 e2e（WP-CLI 取 key→重置表单→弱密码拦截→不一致提示→真保存→新密码登录成功）、.pot 用 make-pot --merge 重生成、PageUrls 抽统一、PendingGate DI 修正、mailto 改 %s 占位、data-count 删、logo 换 webp（319KB→10KB）。
评审+返工顺带抓到并修掉两个真缺陷：Woo notice 图标压首词（flex 化修正）；Woo 自带 lost-password.js 禁用按钮后不一致提交会卡死（account-ui.js 清回，有测试）。

### 2. 夹具测试

PHPUnit 999 unit、JS 45、e2e account 12（含 2 条新重置链 + 德语 restricted 门禁）+ empty-draft 4 + commerce 2 全绿；phpcs/phpstan L8/i18n 双门/banned-words 全绿；CI pass（5m23s，eabd5cb5）。

### 3. Computer Use 视觉验收（基准=原型分支 prototype/account-redesign，16 页）

主线同机同浏览器对照 128 张（shots/ 内收关键对）：登录/注册/忘记密码/重置/四门禁/工作台八页 × EN/DE × 1440/390。
首轮发现并已修：品牌面板跨双卡撑出大空洞 → 拆成每卡各自品牌面板单元（面板与各自的卡等高，实测 heightDelta=0）；联系人卡丢框 → 恢复 .panel 卡框；restricted 原因块裸文本 → 恢复 notice-info 着色卡。
复核：impl3-login-en-1440（双单元）、impl4-gate-restricted-de-1440（着色原因卡）、impl4-overview-en-1440（联系人卡框）全部对齐原型。

**记录的既有偏差**：chrome.spec.ts 两项德语工具页重定向在未跑迁移的实例上 404（与本票无关，验收实例前置条件问题）；storefront.css 存量 329 处 body.sf-account-page 死规则归后续专门清理（spec §九 记录在案）。

**变更台账条目**：登录注册全链重设计 · 业主裁定 2026-10-15 · 方向=浅色卡片+App 感（#179）· 登出改一键（去 Woo 二次确认）。

## 结论

通过。合并 PR #187。
