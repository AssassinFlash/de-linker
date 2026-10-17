# #286 · 内部通知发件人

实现实例：`c286`，`http://127.0.0.1:9090/`；分支 `feat/286-internal-sender`。

## 行为与复核入口

- 内部 From：`Linker <sales@sunriverinverter.com>`，或设置页独立配置的内部地址。覆盖新注册、VAT 复核、新询盘、联系留言、每日摘要及 Genie / engine 两种健康告警。
- 设置：WooCommerce → Settings → Inquiries → Internal notifications → Sender email；选项 `linker_commerce_notify_from`，紧邻 Recipient。空值、无效值、非字符串值回到票据默认地址。
- 客户 From：继续由 WooCommerce → Settings → Emails 管理。内部 From 与收件人、客户邮箱均独立；相关内部通知的 Reply-To 保持客户或访客地址。
- 原生机制：`WC_Email` 的发件人 getter 在发送时由 Woo 临时装入 `wp_mail` 过滤器；Outbox 当场解析并保存 From，重试读取已存消息。健康告警的普通 `wp_mail()` 显式带内部 From 头。

## 测试边界与红绿证据

票和开工提示已指定单元与 Outbox 边界。测试先行用于设置读取、后台字段、内部发件人和客户发件人公开 getter；真实实例的队列数据验证 Woo 原生发送过滤器与 Outbox 的衔接。

| 边界 | 改动前的红 | 改动后的绿 |
|---|---|---|
| Options | 新的默认/配置/空值/无效值/非字符串用例共 5 个因 `notify_from()` 不存在而失败 | `OptionsTest` 10 tests / 22 assertions |
| 设置页 | Recipient 后仍是 Blind copies，新字段断言失败 | `SettingsTabTest::test_internal_sender_setting` 通过 |
| TeamEmail | 新注册信没有内部 sender getter，断言报错 | `NewCustomerEmailTest` 验证固定名称与自定义内部地址；原 Reply-To 断言仍通过 |
| 联系留言与健康告警 | 联系信两个用例缺 getter，健康告警仍 From de-linker；共 3 个失败 | `TeamMessageEmailTest` 和 `MonitorTest` 覆盖默认/自定义内部 From |
| 客户邮件 | 客户 getter 边界的 3 个用例因外部 WC_Email double 未提供 getter 而报错 | `CustomerSenderTest` 3 tests / 12 assertions：默认/自定义内部设置不改变客户 From，修改 Woo 设置后客户跟随 Woo |

聚焦单元命令（在 `plugins/linker-commerce`）：

```sh
/opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit --testsuite unit \
  --filter 'OptionsTest|SettingsTabTest|NewCustomerEmailTest|TeamMessageEmailTest|MonitorTest|MessageTest|CustomerSenderTest'
```

结果：**47 tests / 147 assertions，全过**。客户测试使用外部 Woo double 的最小选项读取契约；原生过滤器的实际行为由下述实例测试验证。

## 双评审

- Standards：全量 `origin/main...HEAD`，初版 `03945f21` 与客户单元补充 `3923cf7b`，均 PASS；新增行旧标识符扫描零命中；没有改引擎、翻译器或账号架构。
- Spec：初版指出“客户邮件需独立单元断言”的 P2；`3923cf7b` 补齐后复核 PASS，剩余 0 项。发件人、Reply-To、独立设置、六类内部通知和客户 Outbox 断言均符合 #286。
- 文案：见 [copy-review.md](copy-review.md)，含 EN 初稿→评审→定稿、DE 独立稿及评审；Standards 独立子代理另行检查定稿，无新增意见。

## 上线验证与回滚

本会话只实现、验证并提交 PR。#286 第三条标准由 Claude 上线后触发**一封**内部通知，在 sunriver 网页邮箱确认进入收件箱，并将截图记录在 #285；此项在本会话为**未完成，按分工留给 Claude**。本地证据证明邮件身份与路由，收件箱分类以该线上观察为准。

上线不需要数据迁移：不存在该选项时直接读票据默认值。回滚插件提交即可恢复原有发件人行为；新选项可保留（旧版不读），需要清除时删除 `linker_commerce_notify_from`。不修改 Woo 客户发件人设置，不改 DNS。
