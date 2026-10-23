# 公开注册的站级与待处理账号容量

状态：本地实现及验收，等待固定 head 的全量 Spec / Standards 复审；未合并、未部署。

依据：[公开注册容量 #569](https://github.com/AssassinFlash/de-linker/issues/569)、[全站安全地图 #533](https://github.com/AssassinFlash/de-linker/issues/533)及本票中业主授权的 pending profile、完整通知预留和数据库断线收窄。未发现公开注册攻击已经发生，本票不计入已确认联系表单攻击规模。

## 资源合同

| 资源 | 本站初始运营分配 | 权威与释放 |
|---|---|---|
| 公开注册通量 | 站级16/UTC小时、32/UTC日，保留 subject5/日及直连100/小时 | 原生 Admission/Ledger；换邮箱、浏览器、IP或 Woo/core 门不重开站级窗口，创建/登录/审批/邮件不退款 |
| 待处理账户 | 128 | 原生 customer 或可信公开注册 core marker；待审及限制均占用，只在带员工审计的通过/拒绝或原生删除后重新核读释放 |
| 业务资料 | 8MiB逻辑字节 | users 中5个公开字段及完整 billing/业务 meta 的 OCTET_LENGTH；包括已有历史债务和正在创建占位，不是物理 MySQL 磁盘上限 |
| 初始通知 | 团队与可选客户回执分别 count1 | 复用 #568 共享 critical64项/16MiB，完整 Message JSON 和暂存的冻结 source 都须在同一字节预留内；不新建邮件队列 |

这些值是本站授权的资源分配，不是厂商安全阈值或测得的真实客户峰值。32个注册的两封初始通知与之后独立审批通知的规划值，不是 SMTP 即时投递或收件箱保证。正常登录、密码重置、浏览、产品草稿及访客询盘不共用注册通量和账户容量。

历史数据只读聚合。没有为迁移复制、裁剪、删除旧账户或给旧通知补恢复动作。历史超额阻止新增与正增长；等大或缩小的待处理业务资料仍可保存。默认 subscriber、缺审计的 approved 标签、登录状态、模型/Jev 结论、邮件结果、年龄和定时器不能释放占用。

## 原生创建与通知顺序

```text
Woo/core 原生校验 + nonce
  verifiedOperation / 原生站级通量
  NativeTransaction（原连接、原 savepoint）
    RegistrationSlots：预留 count + 业务 bytes
    原生邮件 prospective capture：两份 count1 的完整冻结通知
    第一笔原生 users 写入前绑定精确 email/login
    insert_custom_user_meta：实际 user ID、业务资料、pending source 和关联
    user_register：原生资料/关联/source/bound 重新读回
    bind 原生账户替换占位；完成 operation；确认原 transaction 提交
  原生 VAT / notice producer
    完整 Message ≤ 对应预留
    原生 JobStore + source accepted/清 payload + original-job AS 同事务
```

创建不接受密码进入 fingerprint、slot、preview、source、日志或恢复。`Accounts::text` 原来的190字符截取仅属于旧保护 fingerprint，原生 Fields 并无该业务上限；本票改为完整 sanitized 值。合并姓名超过250字符在第一笔写入前明确拒绝且保留非密码输入，来源是本机原生 users.display_name 的 varchar(250)，不裁剪。

冻结通知使用现有 NewCustomerEmail / RegistrationReceivedEmail、Prepared capture、同一 RegistrationInformation 字段源以及完整现有 routing/headers/locale/设置/filter。仅模板自有的 account URL 和 VAT label 允许 preview 参数：随机256-bit标记必须恰好出现在解析确认的链接 href 与 VAT 单元格中，正文其它部分或 Message 其它字段不得含该标记。验证后丢弃 token，只存有类型的结构洞。模板 override 若删改或无法保全该原生链接/单元格，预创建明确拒绝；不以 ID0 样本猜测任意 filter 的界，也不对客户文本做普通全局替换。

界值逐项计算合法正 PHP integer ID 的最大19位、所有5个真实本地化 VAT label、完整最终 Message JSON，以及包含 reservation/max_bytes 元数据的完整 pending source JSON。实际替换后再次核完整 JSON 不超过原预留；无 unresolved token。超过容量或模板不符合可证明结构时，账户尚未创建，表单保留输入且提示重新输入密码。

已创建但通知 ACK 失败时保留账户及可见 pending，不能谎称未创建。两 notice 独立接受、跳过及取消；明确 disabled 或 ReceiptBudget 决策先 durable skipped，只有从未进入原生 JobStore 的本 notice 预留可以取消。取消与 source ACK 同事务，失败两者回滚。未知状态不退款、不超时删除、不重复创建或重放 accepted source。

恢复复用既有 minute RecoverySchedule 与 hourly maintenance；员工原生 Users → Registration capacity 的按钮和 `wp linker-commerce registration-notices` 调用同一 bounded pending source（每次最多128）。JobStore 中央交接在 source accepted 清 payload 的同一次事务内创建并读回唯一 original-job Action Scheduler 动作；提交后进程在即时 dispatch 前退出，已有原任务可以消费。queued、SMTP accepted、inbox received 是三个不同结果；本票只证明前者与合成 transport 的原生消费，不实发邮件。

## 待处理资料写入

公开注册后保持登录的待处理账户仍是公开写入口。Woo account details、billing、实际开放的 core self-profile 与原生 Users REST controller 的公开业务字段使用同一个 RegistrationSlots mutex：权威旧字节 → 完整新字节，正差额才需余量。native before/after hooks 保留原有权限、nonce、校验、writer 和错误机制，不改鉴权。已审计通过/拒绝账户及有 edit_users 的员工维护沿原路径；不按“已登录”或 Jev 判 trust。

Woo account details 在 customer->save 前先 wp_update_user，本票在原生 save_account_details_errors seam 持有范围跨两段写入；billing 的 save_address 不捕获 customer->save 异常，因此在原生 after_save_address_validation 提前返回正常 notice。core profile 早期扩展 meta、REST 在真正 controller callback 前的窄 seam 同样受控；不扩成任意全站数据库框架，不改变密码本身的流。

拒绝/未知的 account details 只对本次 native nonce+owner+action 通过的四个 canonical 非密码字段做 request-local 回填，经原模板 esc_attr 输出；不进 option/transient，不跨用户、不跨 reload，不读任意后续 POST 猜测结果。重新读取页面显示原生已确认数据。password-only 保存保持原生路径；密码框不回填。

## 原连接和未知结果

WordPress 的数据库客户端可能在2006断线后重连并重放原 UPDATE，导致新连接 autocommit。仅核 BEGIN/COMMIT 的返回值不能证明原子性。本票四个 writer（创建、pending profile、员工中断处置、notice ACK/erase）复用 #568 的 NativeTransaction / ConnectionFence：短 SQL 范围内保存并恢复该客户端的 reconnect policy 和 mysqli report mode，禁重放，逐 query 核原 client/handle/thread，提交前确认原 savepoint 及原连接，结束时恢复政策。不是全局配置变更，范围不包 SMTP/模型/VIES 网络工作。

跨 before/after hook 的 native scope 持续覆盖实际 writer；abort/shutdown 只尝试回滚仍存活的原 owner，不在新连接作补偿。外层调用者通过 savepoint 接入，既不提交也不回滚其无关修改。COMMIT 已执行但 ACK 丢失仍是 unknown：账户或资料可能已保存，应重新读取/尝试登录后再操作，不声称未保存，不自动退款或补发新业务。

## 员工、历史与隐私

原生 Users 子页只呈现聚合数、真实 notice 状态、有限中断占位和最近128条员工 decision。中断占位只有 operation HMAC、原始 recipient HMAC、时间及 bytes，不复制业务正文；当前创建连接仍持锁时不能处置，GET_LOCK 同连接可重入也不构成许可。员工必须具备 edit_users、提交 nonce 和非空理由；原生关联不存在、审计与 slot CAS 同事务且读回后才称已处理，动作不建户。

所有原始 Message/source 均在 WordPress 的 verified-email exporter/eraser 中覆盖，原始 recipient HMAC 与当前地址分别核读，改邮箱不使旧通知逃出隐私范围。erase 在至多两个原 job 的 native connection locks 下二次核归属，AS/job/capacity/source 一起提交；任一 ACK 写失败或 job 被另一个消费者占用则保留真实原状态，未知不能称已擦除。原生 user deletion 复用此门；只有本次原 job 删除与未开始预留取消均确认后才写 erased；取消失败或未知保留原 source/owner 并返回未完成，不能复活 payload、漏掉新 job 或伪造时间退款。

## 原生机制与自定义范围

Woo/WordPress 原生 validation、users/meta、账户 writer、审批审计、privacy callbacks 和 Action Scheduler 已复用。它们没有本站的跨公开入口 site/window、pending count/bytes 或冻结通知 capacity 合同，因此增加窄 Accounts/Slots/Notices adapter；LC tag 与 WindPress 不能承担业务 admission/事务。客户页面沿现有 LC/Woo/WindPress，只有现有账户表单四个 value 的数据供给变化，无新布局、CSS或 snippet。

验收与回滚边界见 [本票记录](../acceptance/2026-10-22/569/README.md)，文案初稿、意见与定稿见 [copy review](../acceptance/2026-10-22/569/copy-review.md)。生产发布由协调者在完整复审与组合验收之后执行，本票执行者没有部署、合并、生产写入、真实模型调用或邮件投递。


## 全量评审收窄的身份与失败合同

客户回执的ReceiptBudget绑定冻结Message实际To，不从当前user_email重新推导。对冻结To解析原生Name <address>、去重并稳定排序，一次Ledger reserve原子包含全部目标hour/day与site/day一次；不逐目标扣款。单To与既有string接口的operation ID/fingerprint保持字节兼容，邮箱更改不重定向已冻结通知。保留既有Ledger16维界，最多7个唯一目标；无法证明或超出时通知保留pending，不裁剪目标、不放宽额度、不拒绝注册。

创建提交前必须核实最后Admission completion的返回值，非抛异常WP_Error也不能被void适配器吞掉。REST业务字节门以实际matched Users controller写回调和原生parsed target为准，覆盖原生大小写匹配及body/JSON参数优先级，仍保留原鉴权和schema校验。

通知policy/provider阶段可以先读状态；真正写skip、accepted、取消预留或erase时必须在原owner锁和原NativeTransaction内重读完全一致的source。已擦除、已变化或无法确认的source不能被旧快照覆盖。verified-email原owner查询失败不是空集：export原生错误、erase retained/done=false，拒绝失败空结果缓存，也不借当前邮箱fallback伪称完成。健康重试仍使用原有owner关联，不复制新的隐私队列。

后续完整复审确认：erase的第一次source读取也必须在原连接范围内。整个owner GET_LOCK、首读、既有job锁、原事务中的fresh比较/删除/取消/ACK、解锁现在共用同一ConnectionFence；首读2006不能重连后借新连接继续。原始staff audit也使用带owner核验的cache-free native读取，真实读取失败不是空列表。owner audit与interrupted owner关联的擦除使用同一NativeTransaction/savepoint，任一最后ACK失败都回滚本轮，其他owner记录与调用者无关事务不变。原生staff追加审计复用相同权威读回；不改共享API或建立新的通用数据层。


## 当前保护基线移植（2026-10-23）

完整基线是生产 tracking `1949064118a8744a27427595d2aadab788a7ed9a`，邮件/容量运行源为 `a50751df`；此注册候选尚未发布。沿用当前强制发送前授权，不将 critical、category、preview 或 accepted job ID 当作可消费许可，不重签旧38条任务。

注册 preview 的 NativeOrigin 仅证明捕获来自真实原生 producer；typed holes 完成后不能沿用该旧 seal。冻结 source 使用 `registration-native-plan-v1` 域分离的本机 auth-salt HMAC，覆盖完整 parts/Message 路由、附件内容摘要、locale、operation UUID、原始 recipient HMAC、team/received 用途、reservation、实际 account/slot 和完整 bytes 界。第一笔原生 account 插入后、第一笔 meta 前，由可信 producer 将真实 account ID 与 slot 绑定并重新认证此 source。恢复只消费该账号当前持久 source，不能凭临时 caller 数据补造身份/计划。

最终原生 Message 仅在 HMAC、真实账号、原始 owner、当前 slot、用途对应的 exact stored plan 和附件摘要全部相符后，由该 producer 生成最终 NativeOrigin seal；`Message::from_array` 不重新签名。跨账号/operation/reservation/purpose、修改正文/收件人/bytes/witness 均不可获得许可。完整最终 JSON 包括最终 origin/account/seal；完整 pending source 包括所有 HMAC/binding 元数据。边界来自 `PHP_INT_MAX` 的原生 ID 字长、固定 SHA256 字长、实际所有 VAT label 和实际 JSON，不加猜测固定余量。disabled source 同样按完整身份绑定与 reservation 的最大 JSON 计字节，不视为1字节。

在任何 ReceiptBudget 或取消 critical reservation 前，pending 和 disabled/policy-skipped source 都先通过完整认证；合法 policy skip 保留认证见证到 cancellation/source ACK 同事务完成，之后只保留终态 reason。损坏或改写的 skipped 标记不能触发退款。unknown 不发信、也不默认变成 skip。

所有本票新增容量和资料入口从首条 SQL 起保护原连接；profile 的跨 hooks 范围延续至原生 writer 完成与同连接 mutex 释放。notices 外层 mutex 只保护 acquire/release 的 SQL 及其原身份，回调中的 VIES 不置于数据库事务。实际 DB-only ACK、erase、slot/audit 写入继续使用现有 NativeTransaction/ConnectionFence。native read 的非空损坏 source 是显性失败，不当成无资料/已擦除。

verified-email exporter 除 pending source 外，还核实 accepted job 的 `_linker_registration_user` 归属并导出其完整 immutable Message；已消费删除的 job 不重建副本，读失败/归属不明返回可重试错误。当前 MU 基线对普通客户 Users REST 路径返回403；本票保留该守卫。底层 self-controller 字节门使用仅有原生 list_users 能力且无 edit_users 的受限合成账号验证，没有开放默认客户路由。

历史候选的截图与测试仍保留其原 head/实例说明，不能冒充此移植候选的新验收。当前原生结果和剩余门见 [2026-10-23 移植记录](../acceptance/2026-10-23/569-current/README.md)。


当前消费者复核进一步收窄：eraser必须在删除任何一个原job或取消任何scope前，验证本用户所有pending/reserved plans，不能用A的verified-email请求取消B的reservation。accepted source只允许正int job，erased/最终skip仅允许定义的shape；损坏指针是unknown，不清source。健康连接上NativeTransaction构造失败时只释放这次已取得且原identity仍可确认的mutex；断线不在替代连接补偿。Woo account/billing首读失败返回既有正常unknown notice；account只保留本次native owner/nonce验证后的canonical非密码字段，不把底层mysqli异常当成功或fatal页面。
