# 公开入口与资源边界：阶段性只读核查

基准源码：003cedd399fc4781f8fe31f9896ea9d2a9c87282。私密source目录为该commit的git archive，未借用他人可变工作树。未改任何源码/配置/生产数据，未发模型/邮件/浏览器请求。此报告按root要求先收口，不将未测项写成通过。

## 已证明 P1：verified 通用业务缺独立全站通量和持久积压边界

真实reader：`plugins/linker-commerce/includes/Protection/BusinessPolicy.php:31–47`。五个业务入口共用浏览器10/h、20/day（登录20/h、100/day）、账号20/h、100/day和直连100/h，没有业务site维度。没有读取员工审批状态；新注册pending和approved在本策略中都是account。

真实分流：`Protection/Business.php:97–103`。valid proof且不命中特定活动时lane为空，绕过IntakeStore；随后reserve→dispatch→work。`IntakeStore.php:33–37`的128 verification、3 campaign、16 individual只保护三个复核通道。`docs/specs/542-safe-intake.md`明确verified path never consults review capacity。

最后writer：`Inquiry/Sender.php:181–207`首次save前Queue.prepare冻结业务快照/CustomerEvidence，之后原生received状态触发内部通知；`Inquiry/Assessment/Queue.php:248–278`逐条JobStore.create；`Mail/JobStore.php:96`无待发任务总数/总字节限制，`Mail/Outbox.php:193–205`额度不足只排程/创建job。provider200/2000和邮件SMTP400/PHP80的预算只限制实际dispatch，不限制已存Woo、快照、Action Scheduler和Outbox堆积。Queue.recover还以limit=-1遍历所有pending，积压会放大恢复扫描。

**严格限定：不是数学意义无限入口。** Siteverify已有5000/site/day、browser1/site2验证并发，shared Ledger有10000 live receipts、8MiB和24h保留限制；它们不是正常业务持久存储/通知流入信封，清理之后仍可累计更多记录，耗尽共享账本还会影响其他客户入口。换落地域或文案不命中fredmer规则，不意味着绕过proof，但足够把旧87条活动的廉价身份轮换模式再次落到完整verified writer。

离线执行当前原生BusinessPolicy，两个不同browser+connection生成的bucket交集为0；五门均无site维度。`policy-probe.php --require-site-dimension`返回1，为可重复红门；无WP bootstrap、DB写、provider、mail。当前已有BusinessPolicyTest只锁跨门共享、carry、NAT/autofill；BusinessAdmissionTest锁原生幂等与别名；这些正确测试没有“跨browser+connection全站正常占用/任务积压”断言。542测试刻意证明verified不受review满额影响，不构成这个缺口的反证。

## 最小实施合同，未改源码/未定阈值

1. 在现有业务policy加独立站级通量，跨contact/inquiry/Genie业务门共享；在最后原生首次save前以持久registry原子预留未处理条数/字节。优先复用IntakeStore/Ledger/BusinessRecord的锁、CAS、UUID和原生状态，不更换Woo writer。
2. “已由员工批准”的真实客户独立预留：必须基于现有审批记录及员工决策来源，不因is_user_logged_in、注册成功、VAT字段或Jev标签立即进入可信池。匿名/pending/restricted与已批准池隔离，普通池耗尽不占已批准预留；审批变化不能制造新的免费额度。
3. 在JobStore.create/Queue.queue_notice实际任务创建处再次检查持久待发条数和消息字节信封；保留critical业务预留，不能只靠发送节流。已存询盘若暂时无法建job，保留明确的durable pending状态供既有独立恢复处理，不能静默漏通知或假装sent。重复恢复/UUID重试不重建job、不重复占用；崩溃与擦除不自动退款可疑dispatch。
4. 若首次接收前容量满：准确返回未保存，不给新询盘号；保留原字段、产品草稿与logical UUID的可重试状态，沿用现有FormRecovery和原生提示/联系邮箱替代。不得删除已有询盘、截掉客户正文、按Jev拒收，或把日清理当持久占用释放。
5. 释放占用须绑定明确原生业务处理/员工处置或可靠通知交接的既有状态，定义读回、幂等、擦除和历史记录迁移；不允许仅时间经过释放仍未处理的记录。旧记录不重写正文，不全量重构，不新增页面设计。
6. 红绿证据：不同browser/IP/proof及变体域名跨五门用尽普通站级/持久池后，下一次在首save前拒绝且0模型/0mail/0job；同一场景已审批池仍正常。双DB连接竞争不超额，失联/ack丢失恢复同order/job，pending新账号不能借可信预留，任务创建高并发不越界，满额EN/DE输入和草稿保持。客户正常生产提交/通知/SMTP/收件分开验收。

阈值不在本轮拍板。用真实字段最大UTF-8字节、已生成snapshot/CustomerEvidence/line items/job实际编码长度和明确积压预算推导；针对更大的合法上下文可按字节单位占用，不能简单套review20行/32KiB到正常客户而删信息。现有32MiB/256KiB=128复核信封是运营选择，不是整个Woo物理库真值或可直接照抄的verified容量。

## 现有本机恢复快照的只读聚合

`restored-history-aggregate.json`来自root已恢复的独立local schema linker_restore533_20261022，事务READ ONLY，未启动WP；仅SQL长度/计数，不读客户文本到Python。

- HPOS162条（classic0），事发前74条、事发窗口88条；后者与已知攻击窗口相合，不能从此给每条新真值标签。
- 2026-10-19/20/21 inquiry-received为5/1/3；10月22日93（其中88在05:45后）。这些包含历史验收/未知来源，**不是独立确认真实客户需求分母**，不能据此伪称正常峰值或误拒率。
- 事发前order meta＋customer_note逻辑字节：sum617113、max83087、p9539553，单order最多11 items；不含InnoDB页/索引/地址和所有itemmeta。事发窗口88条对应sum306900、max4311、p953969。
- 当前38个private mail jobs，meta合计449472 bytes、max11858 bytes。发送cap没有限制这些记录的数量。
- 新的业务/快照/任务最坏形状及物理空间上限未测；不能把这些局部长度当完整记录最大值。下一实现票需继续定量。

## 当前入口矩阵

所有源码/测试链接均以003cedd3固定；旧分支验收和此前生产读回明确区分。

| 入口/最终consumer | 当前保护与预留位置 | 已有精确测试/证据 | 当前缺口/未验证 |
|---|---|---|---|
| contact/inquiry/admin-post→Sender首save | nonce/字段/草稿preflight；Business reserve/dispatch；542复核分池/活动聚合；正常proof不等Jev | [BusinessAdmissionTest](https://github.com/AssassinFlash/de-linker/blob/003cedd3/plugins/linker-commerce/tests/php/Integration/BusinessAdmissionTest.php#L234)、[542合同](https://github.com/AssassinFlash/de-linker/blob/003cedd3/docs/specs/542-safe-intake.md)、533 release-003cedd3已存读回 | 上述P1通用verified全站持久/通量；当前发布正常新询盘/通知/收件待验，不以没新询盘判代码失败 |
| Genie contact/inquiry/conversation_mail | Resources对实际REST回调reserve/dispatch，trusted context共享BusinessPolicy；原生ownership/consent不变；目标回执2/h5/day＋site10/day | ResourceAdmissionTest::test_business_seam_single_use_and_legacy_scope、test_conversation_receipt_gate_runs_once_inside_trusted_context；BusinessPolicyTest两项 | 同一通用P1；confirm GET的原生一次性链接并发消费未在本轮重新验证，不声称并发恰一次 |
| Woo/core registration→user/VIES/mail | Accounts注册errors钩子priority30在创建前；Operation注册5/day、connection100/h、singleproof；created hook完成 | BusinessAdmissionTest432–530中的两注册测试；520/checks原生HPOS/classic；当前source仍有测试 | 当前发布真实注册/审批流程与VIES拒绝0调用读回未重做；注册即pending不可自动可信；MFA另564 |
| Woo/core login→password check | 新正常登录不挑战；3/browser或100/connection/10min失败升级，site1000 hint；verified20/h | BusinessAdmissionTest::test_progressive_login_preserves_normal_success_and_gates_failed_use | 当前发布真实反复登录/正确密码恢复未重做；XMLRPC认证/应用密码实际消费者未穷尽 |
| Woo/core lost password→key/mail | lostpassword_post beforekey；extra nonce；5/h、target2/h5/day，独立于business；profile_update ack | BusinessAdmissionTest::test_both_native_password_reset_paths_require_proof_before_key_and_mail；522 native-de-reset历史证据 | 不改变现有密码；当前发布实际reset收件未重做；邮件transport预留与目标cap不同口径 |
| draft GET/POST/wc-ajax/reorder→session/cart | wp_loaded19 beforeWoo；reorder更早session hook；所有列出的命令/nonce/cap；draft120/h＋connection100/h；只读product_id不扣 | BusinessAdmissionTest::test_native_draft_transport_and_store_api_require_scoped_proof；本文件642起 | current发布各native正常UI别名未逐一重走；无付费模型出口 |
| Store API cart collection/item/coupon alias＋batch | rest_dispatch_request在权限/参数后；case-insensitive覆盖全部/wc/store/vN/cart mutating；batch子请求各自门控 | BusinessAdmissionTest::test_store_api_cart_aliases_cannot_bypass_the_actual_mutation_gate（691–758，含真实/batch/v1 207子拒绝和201有效写） | 当前发布未重新发真实cart写；未把普通REST read禁掉 |
| comments/REST/XMLRPC→insert/methodmap | preprocess_comment及REST wrapper；comment10/day、native nonce；staff moderation不拦；enforce仅移除pingback.ping | BusinessAdmissionTest::test_comments_and_xmlrpc_do_not_offer_an_unprotected_public_write、test_valid_native_rest_comment_does_not_require_a_second_form_proof | 评论现状native关闭；未为验收重开生产评论；本次只读未独立枚举所有XMLRPC插件方法 |
| Genie turn/attachments/voice→解析＋供应商 | Resources先reserve/validate parent再base64/magic，3files、20MiB总，6MiB image/16MiB PDF/1MiB CSV/6MiB XLSX；30MiB raw；turn30/120/day、burst10/30、site500/day，file10/40＋site100；private actualwork subject1/site2 | ResourceAdmissionTest153,194,236,734；test_provider_budget/test_work/test_attachments；539实际28匿名POST401/边界、严格CA读回 | 当前EN成功、DE正常fallback/Retry缺陷由563处理；原HTTP错误未知。本轮新测试72PASS、3缺非代码归档fixture，见下；真实附件/全语言UI由563/组合验收 |
| conversation/thread/select/delete/vote/solution-save→nativepost | storage500/subject/day、site2000；ownership、private receipts24h；读取已有thread不创建 | ResourceAdmissionTest::test_policy_reads_writes_and_native_budget_exhaustion、privacy两项；Thread原生并发tests | 当前发布未逐项走实际UI；累计历史业务存储的长期容量/保留策略不由24h receipt cap证明 |
| Configurator/roof/report→engine及PVGIS/LoD2 | Resources/NativeEngine actualversion readback＋input/subject/day语义幂等；design/roof30/120/h；PDF10/day、site100/day；subject1/site4；6MiB body；native saved recomputation同池 | ResourceAdmissionTest290,504,524,765,840,888,953；engine test_resource_gate/test_version；521真实本地engine/PDF＋PVGISfixture；539TLS/gate读回 | 当前发布完整真实屋顶/报告供应商成功未验；geo/plz为bundled只读，不是付费遗漏；地图浏览器第三方读取与其供应商额度本轮未测 |
| provider outlets→真实HTTP attempt | private BEGIN IMMEDIATE before eachsend：DeepSeek2000、Jev200、runtimeembedding2000/UTCday；所有SDK retry/toolloop、vision/summary/quality/assessment/de translation分别guard；失败显性不换模型 | test_provider_budget各实际transport/worker/deadline；test_inquiry_assessment；ResourceAdmissionTest::test_private_provider_filter_requires_positive_native_debit | quota不是欧元/token精确费用；Jev耗尽为未能判断且正常通知，不限DB；离线indexbuild排除runtimeembedding额度不等公共绕过 |
| cron/async/recovery/directVPS | 已有独立分钟wp-cron＋native lock；AsyncRunner nonce/cookie/order-boundwake；NotificationHold各process/expire/retry前检查；所有privatePOST token beforeparse；engineloopback＋subjectslots；docs404 | 522/production timer/heartbeat；533 release-003cedd3真实38held回调0HTTP0mail；deploy-539/acceptance-539 runtime-readback/guards/nativeTLS | 当前发布正常新询盘LiteSpeed queue/model延迟待验；webcron匿名可触发due事件但不应重复业务；大量HTTP的边缘/OS耗尽不由本门证明 |

## 本轮执行与未覆盖

1. `policy-probe.php`真实当前BusinessPolicy离线执行成功；跨两个不同browser+connection无共享bucket；`--require-site-dimension`红门exit1。此夹具只证policy，不声称真实Woo写入并发通过。
2. 从固定003cedd3归档，复用已锁定解释器，隔离pytest临时目录并用sitecustomize禁止所有非loopback网络，运行provider_budget/work/inquiry_assessment/attachments四文件：**72 passed，3 failed，5.61s**。三个失败均FileNotFoundError：归档未包括docs/research/.../datasheet-probe.pdf；不是断言到生产失败，未skip/放宽测试。完整输出genie-native-tests.txt。本轮按root要求阶段收口，未继续补资源/重跑。
3. 本轮未搭新WordPress实例/DB执行既有PHP integration，不借用他人实例。它们的真实HPOS/classic证据见520/checks、521/README、522/production，当前生产003cedd3精确CI已成功；当前没有逐消费者最新生产成功证据，不能把旧PASS自动升级为当前UI验收。
4. 未重做边缘/SSH/插件/管理员审计，使用root已保留事实；没有生产新提交、真实邮件、客户密码或凭证动作。无全站“已安全”结论。

## 产物

- source/：003cedd3固定源码/规格/原生测试归档。
- policy-probe.php / policy-probe.json：真实业务策略读取与跨身份红门。
- restored-history-aggregate.json / aggregate_restore.py：独立恢复库只读计数与字节聚合。
- genie-native-tests.txt：72PASS及3个缺归档fixture的完整错误。
- sitecustomize.py：仅本次子进程禁止外网。

不提交PR；539已审工作树未修改。已在[已验证业务的站级接收与通知积压上限](https://github.com/AssassinFlash/de-linker/issues/568)继续定量与实现，独立工作树、双评审和原生并发夹具；本只读报告没有修改阈值。
