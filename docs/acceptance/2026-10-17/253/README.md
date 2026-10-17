# 德语自动翻译：自动生效

当前交付阶段：独立分支实现与本地验证。生产部署尚未获准，线上验收未完成。

## 已确认范围

业主本轮明确取消人工译文审阅和营销冻结：页面、产品、博客、既有可翻译词项均自动跟随英文；机器校验成功即同步。LC partial/dynamic template 内容继续由 present 发布，语言配对保留。

## 证据

- 模板安全：`TemplateSafetyTest` 保存 header/footer/dynamic、CLI force/now、执行遗留及重试任务；德语内容与配对保留。清理命令只移除模板的任务及状态，第二次运行零变更，不影响其他内容任务。4 tests / 39 assertions。
- 内容管线：`TranslateOnSaveTest` / `TermTranslationTest` / `AutomaticContentTest` 覆盖产品、页面（含营销内容）、博客、词项、增量、历史人工锁及冲突、源在运行中再次保存、失败保留旧译文、后台德语行与英文行同状态、异常报告筛选。与模板安全测试一起，最终 **17 tests / 252 assertions 通过**；另见 [并发红绿回归](race-regression.md)。
- 单元：**162 tests / 348 assertions 通过**，包括 Credentials 的进程/$_ENV/私有文件优先级、不可读文件；官方端点固定；后台 nonce 与源编辑权限；模板所有入口保护。
- 真实官方 API：`official-api.json`。私有产品夹具，当前进程没有注入 API key，由私有配置文件读取；一次 deepseek-flash 官方请求，描述返回“Der dreiphasige Hybrid-Wechselrichter unterstützt Batteriespeicher.”，状态 synced。夹具已删除；凭据与请求头未输出。测试只在本地 CLI 的该请求放行官方端点，进程结束即撤除，无永久放行配置。
- 摘要接口已[留言交接给每日摘要票](https://github.com/AssassinFlash/de-linker/issues/221#issuecomment-6233639416)：`StatusReport::issues()` 只列最终 failed 的英文源对象；本票不改收件人、调度、发信。
- `just check` 与全仓 `just test` 通过；测试用的临时数据库隔离、命令和原有环境跳过见 [验证记录](validation.md)。

## 双评审

固定基线 `00363e699c959a7d4224753dd360da2c54358473`，全量实现至 `b968d83a`；并发修复增量 `b968d83a..8f83e76` 再复核。

提交 PR 前已 rebase 最新主分支 `613b526e`；主分支仅新增 kickoff 两条工作规则，代码无变化。重写后的实现/修复提交分别为 `e0bbc2d8` / `862a4cb2`。

- Standards：全量与增量均通过，0 个硬规则违反、0 个值得处理的代码异味；包含旧代码缺失检查。
- Spec：全量发现跨进程词项保存丢失后继任务的问题。真实夹具复现后修复，同时覆盖回调尾部保存窗口；增量复核确认 **0 项未解决 finding**。
- 后台 8 组 EN/DE 文案独立评审通过，见 [文案记录](copy-review.md)。

上述代理双评审不替代 PR 的 Claude 评审，也不构成合并或上线许可。

## 本地环境与剩余门槛

`i253`，127.0.0.1:9075，独立分支 `feat/253-i18n-auto-translate`。
最新快照 20261017-1920 原始装入失败于 MariaDB VECTOR 索引；为继续真实夹具，临时运行了本地同步分支的 SQL 兼容转换，仅用于 i253，未复制进本票代码。此事已留言同步票。

正式 EN/DE × 1440/390 后台及代表性前台截图尚未完成：依 kickoff，等本地同步票合并后重新装入并截图。不能用当前临时装入结果宣称视觉验收通过。

生产项仍未完成：评审合并、业主同意上线与生产密钥写入后，先备份后部署/读回，清理 14 模板遗留状态，补跑 6 页面和全内容扫漏，网页后台保存英文产品、异步官方翻译、德语前台及模板选择实走，并执行 cutover verify。回滚旧代码前先撤除新密钥。
