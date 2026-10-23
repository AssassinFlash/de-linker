# #569 当前保护基线移植

完整基线 `1949064118a8744a27427595d2aadab788a7ed9a`（已接受的 #568 与库存访问守卫）；原注册候选7个 owned commits逐提交重基，未复制旧共享邮件/事务实现。分支 `codex/533-registration-current`。本候选未合并、未部署，没有生产数据写入、真实 provider 请求或邮件投递。

复用已释放的 `c533review` 快照实例，9416/9417/9418，完整主题/uploads保持。Oracle MySQL 原生9.6.0，未重启全局服务、未创建实例或数据库副本。CLI原生 fixture 使用环境模式；HTTP仍为私有 enforce；这项本地配置修改和小型原配置备份仅保留私密。旧原87仍处于本地原始未处理状态，不冒充生产已处置的15条债务。

## 当前原生反证与修复

| 具体问题 | 真正执行结果 |
| --- | --- |
| preview seal 与实际 account URL/VAT 完成后的 Message 不一致 | 原生2 tests/18 assertions，两失败：最终 seal无效、实际consumer0。修后2/368通过：投影ID只证界不授权；真实创建的两份原job各synthetic消费一次，重复hook0新增 |
| 首GET_LOCK/首profile读取/首IS_USED_LOCK在 fence之前 | 真实第二连接KILL，原caller未提交marker消失，旧writer仍接受：3/16失败。修后原连接从首SQL受控，source/账号/审计不借新连接完成；新增notice首mutex也有原生故障+健康恢复 |
| 未认证 pending plan 在最终校验前进入 ReceiptBudget | 原生红门实际新增payload_changed事件，未新增bucket扣量；不将此例说成新发信计费。修后先认证完整source，新增COMMIT真实成功/ACK未知、尚无receipt政策的To/parts/witness/state/reservation五项篡改控制，Ledger/source/容量均不变 |
| disabled source预留1字节、实际JSON更大 | disabled与普通计划共同按真实完整 JSON、HMAC/account/slot/reservation最大shape预留；实际投影/绑定源均不超过预留 |
| accepted隐私只导出job指针、非空损坏source误判不存在 | 原生export对两原job完整Message逐字段相等；损坏source export错误/erase retained，健康无source可完成；原owner与改邮箱范围沿原合同 |

当前完整 `RegistrationCapacityTest` **76 tests / 1798 assertions PASS**，含真实创建、容量满、并发、跨hook/外层savepoint、COMMIT ACK未知、隐私、原任务恢复及无外部投递。原生输出与失败历史保留在私密 `incident-20261022/registration-current-533`，不复制凭证、客户数据或原Message到仓库。

已有普通客户 Users REST 的403是当前 MU 基线的真实行为，未删除守卫以使旧测试变绿；底层 self-controller 最后字节控制仅给合成用户增加原生 list_users 能力、不加 edit_users。off/observe原生控制由本地CLI动态配置执行，HTTP强制模式保持。

完整 commerce unit：**1842 tests / 6368 assertions / 473 native-only skips，PASS**。完整 commerce PHPStan8通过；当前变更PHP文件 WPCS仅最后无行为文档收口。强缓存/Redis相关组合原生、精确head CI、独立Spec与Standards以及当前EN/DE×1440/390逐状态CUA尚待完成；不以历史截图或当前绿项替代。

## 复跑

```sh
PHPRC=/Users/chesterjohn/de-linker-local/c533review/php.ini \
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c533review/wordpress \
LINKER_COMMERCE_TEST_SITE=http://127.0.0.1:9416 \
/opt/homebrew/opt/php@8.3/bin/php plugins/linker-commerce/vendor/bin/phpunit \
-c plugins/linker-commerce/phpunit.integration.xml.dist --filter RegistrationCapacityTest
```

测试使用原生JobStore/ActionScheduler和final permit，transport仅本机pre_wp_mail合成捕获；正常注册不增加步骤、密码不入恢复/日志/队列/指纹。原38held不重签、不解锁、不补任务，不重置生产或历史额度。源码/数据回退由协调者另行守备份与读回，本候选执行者不部署。
