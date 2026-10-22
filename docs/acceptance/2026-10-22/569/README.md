# #569 本地原生验收

本票工作树 `codex/569-registration-capacity`；本地 `r569` 使用完整线上主题/uploads/内容快照，WordPress9338、engine9339、Genie9340。此次验收没有部署、合并、生产写入、真实模型调用或外部邮件投递。四模型路由和原生权限边界未改。完整全量 diff 的 Spec / Standards 评审由协调者在固定 head 上安排。

实现合同见 [spec](../../../specs/569-registration-capacity.md)，客户及员工文案的初稿→对抗意见→定稿见 [copy review](copy-review.md)。原始 Message、邮箱路由、nonce、operation/receipt、trace、SQL故障输出和本地HTTP fixture 均仅保留在本机私密 `incident-20261022/registration-capacity-569`，不进仓库。

## 故障的红绿证据

| 原生层问题 | 反馈门与结果 |
|---|---|
| 公开入口原先只有 subject/connection，没有 site 注册窗口 | 原生 Ledger/Proof/Operation 站级断言先红；现在16/hour、32/UTCday跨廉价身份共享，UUID异body不借用准入 |
| 未接通 pre-create count/bytes + 两 notice | 真实 Woo validation → native wc_create_new_customer → metadata/user_register → VAT → Outbox，容量满在第一笔 user/VIES/mail 前拒绝；原生 slots 与最终账户替换读回 |
| 猜测邮件256KiB界值、ID0预览不足 | 完整配置 Message 冻结，EN/DE × 两 producer × 3个ID × 5个VAT label逐项核完整JSON；长业务值完整保存，override破坏受控洞明确拒收 |
| Woo billing handler 不捕获 customer->save 异常 | 真实 WC_Form_Handler::save_address 红门→原生 validation seam正常 notice，输入保留且原生公司资料未变 |
| Woo account details 先 wp_update_user 后 customer->save | 真实 handler 锁住 partial core first_name 红门；跨两个 native writer 的原事务范围后通过 |
| account details 错误页面只重读原用户，丢失拒绝输入 | 实际 account WP_Query + AuthTemplates 选中项目模板，撤四 value 供给时红；恢复后同次 owner/nonce/action 的 canonical四字段保留，密码和跨用户不借用 |
| skipped notice 取消容量后 source ACK 失败留下悬挂引用 | 原生写失败红门→取消与 source ACK 同事务，恢复只取消未进入 JobStore 的本 notice，两个 count1 独立 |
| privacy 删 job 成功而 source ACK 失败 | 真实 source写失败红门→两个原 job/AS/容量/source同事务回滚；另一连接持有任一 job 时两者均保留 |
| 原 tx 中的 rollback 可以误伤外层无关修改 | native第二连接确认：失败仅回滚原 savepoint，外层数据仍未提交、对第二连接不可见，由原调用者决定提交 |
| wpdb2006断线重连 replay 导致部分 autocommit | 两个实际跨hook writer，首写前/第一写后各 KILL：撤本票 guard 的控制红复现用户、profile部分保存；追加断言捕获 user回滚但孤儿metadata重放。恢复 NativeTransaction 后四门通过 |
| 员工 audit→slot CAS、privacy job删除→source ACK 中途断线 | 实际独立连接 KILL；原生 audit/slot与两个job/source均保持原状态，不把新连接的COMMIT/ROLLBACK当成功 |
| source accepted已清payload，进程在即时dispatch前退出 | 复用中央 JobStore：同事务 original-job AS+readback；实际注册 producer 无自定义AS补丁，native Outbox hook合成transport只消费原job一次，重复hook和source恢复不再建job |
| COMMIT 已执行而 ACK 丢失 | native实际COMMIT后返回合成错误：注册账户保留且独立 minute recovery可接两notice；profile真实新值读回且用unknown文案，不假称未创建/未保存 |
| 创建进程被SIGKILL | 真正子进程暂停在native pre-create范围后被杀；未提交user/source/reservations回滚，已发生的public attempt不退款 |
| 最后一个 count / byte资源的竞争 | 两个真实原生进程争同一资源只一方建户/VIES/两job；待处理profile增长与新注册也共享同一串行点，失败方不等长锁 |

已有用户、默认 subscriber、无员工审计的 approved、限制、已登录、邮件送达、时间经过和模型结果均不释放待处理账户。真实员工 approved/rejected、原生删除重新核读释放。off/observe 路径保持原生行为。verified-email privacy 原始地址、改邮箱、native删除、busy/read/write失败与已擦除source不复活均有原生夹具。

注册满额的买家回归包含真实 WC_Cart 的产品125×2：拒绝后 hash保持，**同一browser**通过原生 Inquiry Handler 仍创建guest inquiry并包含两件产品。普通登录/重置/询盘不使用注册额度，没有让客户切身份或MFA。

一条历史 OpenInquiryTest 夹具原本期待 `/cart/` 的无class form；固定 `origin/main a0edc136` 已于 `a44a2a9f1` 使用 `Form::draft-action = wc_get_checkout_url()`。本地实际为带 `woocommerce-cart-form` 的 POST `/proforma-request/` 与隐藏 `proceed=1`。先保留失败输出，再将夹具改为解析唯一该form并断言 exact native checkout action/method/proceed；保留真实 inquiry admin-post transport，不放宽成任意路由。

## Computer Use 与图像真值

使用自有 Chrome tab329395461，未触碰根生产tab、MFA tab329395436或#568 tab。视口设置 desktop1440×1000、mobile390×844；read-only DOM逐图记录 innerWidth/innerHeight/clientWidth/scrollWidth/lang/url。滚动条占15px，截图内容区域实际宽1425/375。**字节实际是 JPEG/JFIF，扩展名为 `.jpg`、MIME image/jpeg；没有称作1440/390像素宽PNG，也未重编码原字节。** [四张公开图的原始尺寸、SHA256与viewport记录](screenshots.json)。

共34张本地截图：以下8个状态均EN/DE × desktop/mobile，另2张EN员工实际处置历史：

1. 注册第二步的原有表单；
2. 正常原生注册后保持登录、账户待审；
3. 业务字节容量满时注册拒绝，非密码值保留、密码空且有重新输入提示；
4. billing业务资料增长拒绝，输入保留；
5. account details增长拒绝，实际姓名输入保留而native DB原值不变；
6. 创建成功但通知pending，与独立receipt-policy skipped；
7. 原生员工恢复按钮后notification queue accepted；
8. native verified-email eraser注册的callback实际擦除source/job后后台erased状态。

下方公开图只有合成账户；完整员工屏和native回读保留在私密证据目录。

| | Desktop（内容1425px） | Mobile（内容375px） |
|---|---|---|
| EN account details拒绝 | [原图](en-1440-account-details-capacity-refusal.jpg) | [原图](en-390-account-details-capacity-refusal.jpg) |
| DE account details拒绝 | [原图](de-1440-account-details-capacity-refusal.jpg) | [原图](de-390-account-details-capacity-refusal.jpg) |

![EN mobile: refused account details retain the synthetic name](en-390-account-details-capacity-refusal.jpg)

DE后台长恢复按钮最初出现横溢；独立copy审后只沿WP原生按钮缩短标签，最终两语言390的scrollWidth=clientWidth=375，没有CSS或PHP布局改动。客户页面同样无横溢。

本地HTTP fixture仅限精确r569 ABSPATH，siteverify/VIES/SDK使用合成返回，原生 prepare/verify/Proof/Ledger/Operation、users/meta、两邮件capture、JobStore及Action Scheduler不拦整route。五次公开注册operation来自同一browser：两个正常建户、两个容量拒收、一个receipt disabled建户。没有重置窗口或轮换身份追加注册。最后一个账户创建时发现的旧取消ACK缺口保留为真实红门；修法由新原生夹具验证，不把旧悬挂引用场景说成修后取消已完成。

擦除画面证明真实注册的native eraser callback及后续UI读回；没有发隐私确认邮件或伪称实走收件箱验证。UI状态图拍摄后收窄的是DB-only原连接与中央任务交接，定稿文案、模板value、布局和CSS未再变化；这些故障边界由最终原生夹具重跑。

## 本地清理与可复跑检查

自有tab已关闭、viewport reset；精确本地MU HTTP fixture已移除；receipt选项及原管理员locale已恢复。三名合成账户及其owned notices通过原生删除/隐私门清理，15个原有用户、13个pending、4029业务bytes恢复，interrupted/reserved bytes为0；public operation ledger保留原有五次消耗，没有额度reset。旧38条任务status+全部metadata SHA256逐一一致，未给它们补动作或清历史。

扩大原生套件曾出现第193ordinary被接受：新中央AS真实完成了本地填池fixture中的部分job，原生占用已减少，属于验收后台消费者竞争。Action Scheduler完成时间和原job ID已保存，独立容量门1test/156assertions通过；关闭自有admin心跳并隔离test-only async wake后复跑，绝不把合法消费误判成生产容量突破或放宽192/193断言。本地出现的EML均为本地capture，不是外部SMTP/收件箱投递；原38任务未变化。

检查命令：

```sh
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/r569/wordpress \
php -c /Users/chesterjohn/de-linker-local/r569/php.ini \
plugins/linker-commerce/vendor/bin/phpunit \
-c plugins/linker-commerce/phpunit.integration.xml.dist \
--filter 'RegistrationCapacityTest|MailCapacityTest|MailDispatchCapacityTest|ProtectionAccountsTest|RegistrationTest|ApprovalTest|PrivacyTest|BusinessAdmissionTest|ConnectionFenceTest|OpenInquiryTest|AtomicMailConnectionTest'

# plugins/linker-commerce
vendor/bin/phpunit
vendor/bin/phpstan analyse --no-progress --memory-limit=1G
# WPCS：本票18个PHP文件；共享API固定提交另有原生/静态证据。

# repo
just i18n-coverage
just i18n-validity

# plugins/linker-tools
npm ci --ignore-scripts
npm run build
npm run build:check
npm run lint:types
```

功能固定提交：`ca1b46901dc57e26ff4e0eacb3cebe59c961ac48`。下列检查与此功能版本对应，后续本段链接修正仅文档变更。

最终检查：

| 检查 | 结果 |
|---|---|
| 上述11组原生相关套件 | **121 tests / 2321 assertions，PASS** |
| commerce完整unit命令 | **1584 tests / 6139 assertions，353 native-only skips，无错误** |
| commerce全量PHPStan level8 | PASS，未加ignore或baseline |
| 本票18个PHP文件WPCS | PASS |
| i18n coverage / validity | gap0；8 catalogs PASS |
| tools build / build:check / TypeScript | PASS；工具源码/构建产物无diff |
| diff whitespace / 新文件旧标识符检查 | PASS |

本地build有既有bundle-size/performance建议，构建成功且build/source匹配，未改工具源码或构建产物。代码可回滚，持久pending source不应通过旧代码回滚而被遗忘：发布/回退时保留这些原生元数据、capacity及AS原job，先检查pending并由协调者决定兼容恢复版本；不能清空队列、历史、用户或额度作回滚。生产安装后的原生入站/组合/读回仍归协调者，本地验收不代表已上线。
