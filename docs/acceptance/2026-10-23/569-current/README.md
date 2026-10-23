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


## 3852 后的消费者与 fixture 收口

独立 Spec 对固定 `3852f490` 补审发现：erase遗漏 pending reservation 认证、健康连接上NativeTransaction构造失败后未释放本次mutex、两个Woo真实handler首读断线逃出正常错误边界。实际 native **4 tests/33 assertions 全红 → 4/48 全绿**，包含两个真实注册的不同 reservation、独立连接 mutex 竞争和真正 WC_Form_Handler。修后 canonical账户四字段保留，billing返回正常notice，原native数据不写入；unknown使用已有approved文案，没有新增步骤或客户文案。

随后 accepted坏job指针的真实原生控制先红；现在 read精确核 accepted正int及已定义的终态shape，export错误/erase retained，原有两job完整保留。最终相邻门 **5 tests/65 assertions PASS**，完整commerce PHPStan8与本轮5个PHP文件WPCS PASS。强缓存的81项checkpoint中仅此新增坏指针控制失败，日志原样保留；连接helper之后的新完整结果另行记录，不重标旧失败。

最终副作用点已逐一核对：prepare仅取消刚取得的可信本地scope；cancel_uncreated先验HMAC及未建户stage；bind先验完整plan；deliver在ReceiptBudget前核exact current owned source；policy skip和cancel_skipped保留认证直到同事务ACK；erase在任何job删除或容量取消前先验证所有pending/reserved source，accepted再按原job/user归属；JobStore create继续与exact-source ACK/原AS同事务。未知、损坏或跨账号reservation保持原资料及容量，不因隐私请求退款另一账号。

本机故障测试曾留下mail ledger缺行和admission合成state。已保留原raw现场，既有私密 `owned-ui-options-before.serialized` 的两项字节SHA均先核到原 `rehearsal-before.json`，再仅恢复本机这两项到原字节，原38job/postmeta聚合始终与local rehearsal完全相同。已确认旧fixture存在缓存get_option快照且缺raw readback的隔离缺口；具体最后写入来源尚未唯一归因，原raw及进程退出后的独立读回均保留。本类现在在parent setUp前保存确切原生option presence/value/autoload，在所有native清理之后短事务精确恢复4个本票option、失效对应options/alloptions/notoptions cache并核SQL逐字节。没有生产操作、清空真实quota、全库恢复或新快照；最初失败不删除。


## 原生交接 ACK 与隐私完整性

独立 Spec 的 accepted alias、缺 kind、跨 purpose 与伪造 erased 反例已加真正原生 RED：4 tests/32 assertions 全失败，旧源误称隐私完成。新源要求完整两种用途，各自持久 HMAC 绑定 account/kind/真实 job 与完整 Message SHA256；合法 disabled/policy skip及擦除终态也持有认证见证。实际 transport 后的源仍仅表示曾被队列接受，不冒称 delivered；post 与全部 meta 的健康 SQL 双 absence 才允许清理指针。原生扩展包含跨账号、实际 body 改写、合法消费后擦除、孤立 meta 和真正 SELECT 故障。最终测试计数以本轮固定头原始输出为准，不把早期 disabled 旧 shape 断言失败或原 228/3861 的健康重试失败改标绿色。


本次 ACK 收口的实际结果：注册全类 **90 tests/2033 assertions PASS**（MySQL9.6、HPOS、原生订单/商品两cache及Redis均开启）；完整 Commerce unit **1856 tests/6368 assertions/479 native-only skips PASS**；完整 Commerce PHPStan8、4个相关PHP文件WPCS及diff check PASS。此前组合237/4024仅一个旧daily_cap终态数组断言未包含认证witness，已保留该失败并改为断言原reason与真实ACK认证；原228中的健康erase重试在该组合与注册全类均通过，但旧一次失败尚未唯一归因，不倒推为已证明缓存是唯一原因。最终精确提交的强组合、CI、双评审和CUA另行读回。两条现有CI native filter均加入本注册全类，原classic及HPOS强缓存门全部保留。
