# #246 Spec 与 Standards 全量评审

基准：`origin/main`，范围：本票全部 source/test/template/i18n/spec diff（含延续会话保留的改动）。按 code-review 技能由两个独立子代理并行只读评审，修复后复核最终差异。

| 维度 | 初审发现 | 修复与验证 | 最终结论 |
|---|---|---|---|
| Standards | 新增 LC inquiry HTML 未进入 WindPress provider 扫描 | provider 纳入片段并测试全部内容；实际 `windpress-compile c246` 完成 | 无未解决的 source-level 问题 |
| Standards | 集成测试覆盖 REMOTE_ADDR 后直接 unset，未还原运行器值 | 原值存在时精确恢复，不存在时才 unset；清理在测试退出执行 | 已解决 |
| Standards | 原生优先说明错误暗示原生 checkout 字段不可简化 | 改为原生字段可简化；自定义缝隙是空草稿留言与共享发送入口 | 已解决 |
| Spec/文案 | 待审、限制与登录说明仍暗示审批后才可询盘 | EN/DE 独立定稿；真实邮件夹具断言同步，[完整文案记录](copy-review.md) | PASS，无额外措辞修订 |
| 两维交叉 | 原生 AJAX checkout 与 Store API checkout 可绕过公共 Sender | 旧原生路径在验证/REST 分派阶段拒绝，GET/POST 均有真实断言 | 已解决 |
| 视觉门 | 最新联系表单区域 EN1440 有 57 个残差像素，其他三组为 0；全页有残差 | 原图、差异图、计数逐项保留，不把 crop 当全页 PASS | **未完成，须评审处理** |

后续实走还发现并在本轮修复：Woo 数量更新应 POST 到草稿地址，再以原生 referer 返回询盘页；跨语言保留的错误不能继续显示上一语言；无产品留言不能显示 €0 金额。后两项均先补失败断言再修复，数量问题以真实浏览器更新并继续发送验证。最终独立复核确认这些修复符合规格。

全拆检查：本票新增 diff 检索 `tv_b2b_|Linker_AI_|dlk-|Law` 等旧实现标识，未新增旧代码；没有恢复旧 handler、模型路由或第二套订单/联系表。视觉使用原站既有 class/data 标识作为内容证据，未带入旧代码实现。代码只在仓库插件，LC 模板与 WindPress 卷确实在 c246 渲染生效。

本记录是实现会话的独立双评审证据；Claude 的合并评审尚未发生，未以此代替管理会话的批准。

## 最新 main 合入后的复核

`fa4f323a` 带入 #227 后台账号审核。Standards 独立复核 Plugin.php 构造与注册、规格合并及语言文件，结论 PASS：上游 Accounts/Fields/Admin/Controller 保留，#246 的参数为空 Checkout 与 Shortcodes 保留；全部 793 个上游翻译未改，新增本票 25 个词条。

重跑真实集成时发现上游后台测试设置 dashboard 后未恢复，后续 SearchScopeTest 的 `is_admin()` 因而为 true。仅在 AccountsAdminTest 中注册 `later()` 恢复 current_screen/taxnow/typenow/wp_meta_boxes 原始存在性与值；独立复核通过，目标 PHPCS 通过，应用代码未改。另一次账号数量偏差来自执行器同时创建浏览器夹具，已通过清理后串行执行修正，无产品代码修改。

摘要测试还暴露秒级 filemtime 并列导致误读询盘回执：仅将 DigestTest 改为本次运行前后文件名差集，断言恰有一封新邮件，再核对 To/Bcc。独立复核无问题。修复后集成套件在最新 main 上连续两次通过：81 tests / 874 assertions / 9 既有跳过；目标 PHPCS、最终 just check、just test 均通过。
