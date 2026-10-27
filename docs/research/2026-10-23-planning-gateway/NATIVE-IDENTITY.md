# WP → planner：本机原生身份与 session 证据

调查日期：2026-10-23，Asia/Shanghai。只读研究，未修改产品、配置、用户、账号或会话存储；未注册、登录、退出、发邮件或运行浏览器流程。只新增本文件，未提交。证据来自 p548 实际安装源码和 just wp p548 的独立 CLI 请求，不以旧设计记录替代现行行为。本文给出可复用路线及其条件，不代替最终产品裁定。

## 1. 核实的实例与范围

实际 WordPress **7.1.3**，WooCommerce **11.2.0**；有效 session handler filter 返回 **WC_Session_Handler**。CLI 只输出版本、class 名和布尔值，未读出真实 cookie、session ID、用户信息、wp-config 或密钥。安装目录（本地 home 已只读核为 http://127.0.0.1:9347）：

[WordPress 根目录](/Users/chesterjohn/de-linker-local/p548/wordpress)；命令入口 [justfile:100](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/justfile:100)。

实测没有 wc_session_expiring、wc_session_expiration、auth_cookie_expiration 的运行时 filter；WC logout destroy 与 guest nonce filter 均已注册，优先级 10；没有已注册的 woocommerce_guest_session_to_user_id listener；destroy-empty-sessions feature 当前为 false。后两项不是永久产品约定。

本任务不重新审查已有 quota identity 或现有 Gate；不以已有 POST gate 推断私有读取已经受保护。

## 2. 访客：可以复用哪部分，不能把哪部分误当证明

| 原生入口 | 实际职责与边界 | 本机源码 |
| --- | --- | --- |
| WC()->initialize_session() | 建立经 filter 选择的 handler，调用 init()；应使用实例已有对象，避免重复挂 hook。 | [class-woocommerce.php:1245](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-woocommerce.php:1245) |
| WC_Session_Handler::get_session_cookie() | 解析四段 cookie，验证 customer ID 非空、完整性 tag；**没有在这个 public 方法中检查过期时间**。返回数组不等于完成身份生命周期验证。 | [session-handler:490](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:490) |
| init_session_cookie() | 无有效签名 cookie 时生成新 ID；有 cookie 时恢复数据，然后执行生命周期校验；非法则 destroy，再处理登录迁移与滑动续期。 | [session-handler:164](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:164) |
| is_session_cookie_valid() | private：过期则 false；退出登录后 numeric user session 不再有效；已登录用户与 numeric session ID 不同也 false。 | [session-handler:279](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:279) |
| get_customer_id() / has_session() | 前者只返回内存字段；后者可因收到 cookie、当前请求已设置 cookie或用户登录而 true；两者都不是独立的签名、期限或权限验证 API。 | [abstract-wc-session.php:139](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/abstracts/abstract-wc-session.php:139)、[session-handler:375](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:375) |
| set_customer_session_cookie(true) | 首次真正持久化浏览器凭据的入口；要求 headers 未发送，签名绑定 customer ID 与 expiration，HttpOnly=true，secure 由 HTTPS 判断/filter 决定。 | [session-handler:340](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:340) |

签名算法由原生 private hash/verify_hash 执行，使用 WordPress 的哈希机制，比较使用 hash_equals；网关无需复制签名算法或读取盐值。[session-handler:316](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:316)

未登录的 ID 为 **t_ + 随机串**，登录后为 WP user ID 的字符串；不能将请求 body/query 中的相似字符串当成 native session。[session-handler:450](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:450)

本机默认 guest 生命周期是：24 小时后进入 expiring，48 小时 expiration；已登录的 WC session 默认一周。接近过期的有效请求会重设到期时间并更新存储。这个生命周期与 WP 账号登录 token 不同，也没有证明 guest 项目在 cookie 清除/过期后还能恢复。[session-handler:391](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:391)、[session-handler:194](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:194)

**关键操作条件：** native Woo 前端初始化会 load cart/session，但普通 REST 请求不属于该 frontend 分支。因此私有 REST 适配器应在正确认证时点显式确保 session 初始化，不能从本次 CLI 已初始化推断 HTTP 自动具备 session。[class-woocommerce.php:1012](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-woocommerce.php:1012)、[class-woocommerce.php:714](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-woocommerce.php:714)、[wc-core-functions.php:2539](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/wc-core-functions.php:2539)

**研究判断：** WC 可以提供短期、可续期、浏览器持有的签名 guest session 证明。private GET 不能仅接受 has_session() 或刚自动生成的 ID；需要区分“已收到并验证现有 guest 凭据”和“首次引导新 guest”。如产品要求跨清 cookie/长期过期恢复，需要另行定义持久恢复能力，原生 48 小时 cookie 本身没有该保证。

## 3. 登录迁移：成熟的精确 hook，以及会影响 owner 的克隆路径

### 3.1 专门的 guest → user 迁移 hook

在 session cookie 完成生命周期判断后，已登录的 WP user 与当前 session ID 不同，会进入 migrate_guest_session_to_user_session()。它：

1. 保留旧 guest_session_id，取 get_current_user_id() 为新 user_session_id；
2. 读取旧 guest 数据，切换当前 customer ID；
3. save_data(oldGuest) 写入 user session，并删除旧 guest 存储；
4. 发出 **woocommerce_guest_session_to_user_id(oldGuest, newUser)**；
5. 重设过期时间并发出 user session cookie。

代码及 hook 参数均是当前已装版本的一手证据。[session-handler:189](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:189)、[session-handler:218](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:218)、[session-handler:551](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:551)

因此这是比从浏览器传 old_guest_id 更可靠的认领触发点：适配器直接接收原生迁移给出的旧 guest + 新 WP user 组合，planner 再检查待认领项目确属这个旧 guest，并使用幂等命令迁移。hook 监听必须早于 session 初始化注册：WC init 在 WP init 的优先级 0 执行，woocommerce_init 是初始化之后；仅在后者才挂迁移 listener 可能漏掉本次事件。[class-woocommerce.php:341](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-woocommerce.php:341)、[class-woocommerce.php:1022](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-woocommerce.php:1022)

WP 常规登录通过 wp_signon() 设置 auth cookie 后发 wp_login(user_login, WP_User)。但它不提供旧 guest ID，也不代表 Woo session 此刻已经完成切换；不能只监听该通用 hook 就假定认领完整。[user.php:115](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/user.php:115)

Woo 新注册自动登录另走 **wc_set_customer_auth_cookie()**：先 wp_set_current_user，再 wp_set_auth_cookie，主动 init_session_cookie；该函数不发 wp_login，因此只靠 wp_login 会漏掉这一条实际账号路径。[wc-user-functions.php:312](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/wc-user-functions.php:312)、[class-wc-form-handler.php:1386](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-form-handler.php:1386)

**尚缺的可靠性环节：** 原生 hook 是进程内事件，不是 planner 已确认认领的 durable receipt。它发出时旧 guest session 已被删除；若 WP→planner 请求失败，不能假定下一请求会重发同一旧 guest→user 事件。需要为这对已验证身份保存可重试、幂等的服务端交接记录，或给出等价可恢复机制；这是实施建议，尚未实作或验证。

### 3.2 CartToken 克隆不能顺带授予 planner owner

当前 Woo 支持 query 参数 **session=CartToken**。token 经原生签名与存储存在性检查后，可替换当前登录用户的 session 数据，或为未登录者生成新 guest ID 后 clone 数据。clone_session_data 只排除了 customer 键，其他 session 键连同 previous_customer_id 都会被复制。[session-handler:121](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:121)、[session-handler:206](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:206)、[CartTokenUtils.php:52](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/src/StoreApi/Utilities/CartTokenUtils.php:52)

**由源码得出的约束：** 不能把可授予 planner 项目权限的 owner secret/长期恢复凭据当成任意 WC session data，继而信任克隆过来的值；previous_customer_id 也不是“本人旧 guest”的证明。按经过验证的“当前 native guest session ID”在服务器映射 owner，可使新 clone ID 不自动等于旧 owner。若将扩展身份凭据放入 session data，必须单独证明它不会被 cart sharing 复制为项目权限。本次没有实际运行 CartToken 分享或账号写入。

## 4. 注册用户、退出与过期：应消费哪个原生结果

注册用户应来自 **WP 完成认证后的 get_current_user_id()/WP_User**，不来自请求 JSON 的 Actor/owner/role，也不来自一个看起来是数字的 WC session ID。WP determine_current_user 注册了 cookie、logged-in cookie 和 application password 的验证器；cookie 校验包含 HMAC、期限、用户存在性与服务器 session token。[default-filters.php:520](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/default-filters.php:520)、[pluggable.php:782](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:782)、[pluggable.php:888](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:888)

WP 登录 cookie 默认 remember 14 天、非 remember 两天/浏览器 session；本机无 auth_cookie_expiration filter。它与 WC session 七天是不同层次。不要自行重写 WP 的期限验证：原生还存在 POST/Ajax grace 逻辑及服务器 token 校验。[pluggable.php:1071](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:1071)、[pluggable.php:804](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:804)、[WP session tokens:97](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/class-wp-session-tokens.php:97)

**wp_logout()** 先销毁当前 WP session token、清 auth cookie、将当前 user 置 0，然后发 wp_logout(oldUserID)。Woo 已监听该 hook，destroy_session() 删除当前 WC 存储，forget_session() 清 cookie/数据，按现在的 logged-out 状态生成新 guest ID。[pluggable.php:744](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:744)、[user.php:3712](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/user.php:3712)、[session-handler:95](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:95)、[session-handler:583](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:583)

即使客户端保留了数字 user session cookie，未登录状态下 native lifecycle 也会将它判为 invalid。planner gateway 不能把最后一次已认证的 user 缓存为退出后的访客 owner；每次私有方法必须重新建立当前身份。退出清浏览器 UI 缓存仍是待实测的消费层要求，原生 logout hook 不会自动清理我们未来的 React 内存或本地存储。

## 5. REST nonce、guest CSRF、Origin 的具体消费条件

### 注册用户

REST server 在路由执行前做 check_authentication，原生 cookie auth 位于 rest_authentication_errors 优先级 100。**没有 X-WP-Nonce/_wpnonce 时，即使浏览器有 WP 登录 cookie，core 也会 wp_set_current_user(0)**；错误 wp_rest nonce 返回 403；通过后刷新 X-WP-Nonce。route permission_callback 必须使用这个认证后的身份，不能提前抓取一个 user ID 后绕过认证结果。[rest-server.php:172](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/rest-api/class-wp-rest-server.php:172)、[rest-server.php:438](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/rest-api/class-wp-rest-server.php:438)、[rest-api.php:1130](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/rest-api.php:1130)、[default-filters.php:346](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/default-filters.php:346)、[rest-server.php:1259](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/rest-api/class-wp-rest-server.php:1259)

上述降级不能变成“把 WC 的 numeric user session 当 guest 项目权限”：registered actor 以 REST 认证结果为准，guest actor 只接受经过原生校验的 guest 命名空间。

### 访客

WP nonce 默认 guest subject 为 0。Woo 的 nonce_user_logged_out filter **只针对 action 以 woocommerce 开头的 nonce**，并且要求 has_session 与 customer ID；它不会把 wp_rest action 变为每个 guest 独立。[pluggable.php:2474](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:2474)、[pluggable.php:2537](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/pluggable.php:2537)、[session-handler:615](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:615)

可复用的具体形状：在已建立并发出 native guest cookie 的受控 bootstrap 中生成一个独立 action（例如 woocommerce_linker_planner_v1）的 nonce；后续 guest 私有请求将它放入专用 header，由 WP wp_verify_nonce 校验，另行解析并验证 native session。该 action prefix 直接利用 Woo 现成的 guest subject filter。无 session 时这个 filter 仍回到 0，故 nonce 不能代替 session 证明；不能把缓存页上的公共 guest wp_rest nonce 当成个人 CSRF 防线。注册用户的 X-WP-Nonce 使用 wp_rest action，两种语境应明确分开。

### Origin / Cookie 属性

Core rest_send_cors_headers 会反射收到的 Origin，允许 credentials 及多种方法；这里没有 planner 的同源 allowlist。CORS 输出不是本项目的授权或 CSRF 校验。[rest-api.php:805](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/rest-api.php:805)

WC session cookie 设置调用 HttpOnly=true，secure 依赖 HTTPS；默认 options 未显式设置 SameSite，且存在 woocommerce_set_cookie_options filter。不能凭源码假定实际浏览器永远以某个 SameSite 策略隔离所有跨站请求。[session-handler:340](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:340)、[session-handler:359](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:359)、[wc-core-functions.php:950](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/wc-core-functions.php:950)

**实施所需但尚未裁定的边界：** bootstrap 和所有私有方法的 Origin/同源消费策略应在路由权限层明确；同源 GET 可能没有 Origin，不能未经实测就用“缺 Origin 必拒”破坏合法读取，也不能因此允许任意跨站来源。应按真实浏览器可发送的 Origin/Referer/Fetch Metadata 行为核实，同时保留独立 session/nonce 证明；这些 header 不生成 owner。本文不声称现有站点已经实现这层策略。

## 6. 少量只读执行证据

执行方式：just wp p548 eval；CLI 本身未带用户浏览器 cookie。第一个请求只输出安装版本与 hook/filter 布尔状态；结果见 §1。第二个请求只构造独立、未 init 的 WC_Session_Handler，并用 Reflection 在本进程内设置 **合成测试 cookie 名/guest ID/过期时间**；调用 native hash/get_session_cookie/private lifecycle 与 guest nonce 方法。没有使用真实 cookie，没有调用 save_data、登录、退出、setcookie 或修改 settings；合成 tag 仅驻留内存、不输出。

结果：

    {
      "synthetic_expired_cookie_signature_accepted": true,
      "synthetic_expired_cookie_lifecycle_accepted": false,
      "synthetic_forged_tag_accepted": false,
      "guest_wp_rest_action_stays_default_zero": true,
      "guest_woocommerce_action_is_session_bound": true,
      "no_session_nonce_is_default_zero": true
    }

这直接证实 get_session_cookie 单独不足以检查期限，以及 Woo guest nonce 的 action/session 前提。Reflection 仅用于本次只读探针，**不建议在生产网关依赖 private 方法**。生产应消费 native 初始化后的状态和 public 验签结果，并显式核期限、guest 类型及身份分支；精确调用顺序仍须实现后 HTTP 验证。

## 7. 可供下一步实施的成熟路线与必须保留的验证缺口

### 最窄 public 调用路径（接口形状，尚未实现）

在 REST 已完成 check_authentication 之后，permission_callback 里的服务端 resolver 先取得 get_current_user_id()：

- 非零：只使用该已认证 WP user 构造 registered principal。WC 的 numeric customer ID、客户端 Actor/owner、session data 中的用户字段均不能替代它。
- 零：调用 WC()->initialize_session() 确保原生对象存在；从该对象的 public get_session_cookie() 取验签结果。要求它确为数组、签名通过、expiration 未过期、customer ID 是当前 t_ guest 形态，且 cookie ID 与 handler 当前 get_customer_id() 一致；否则本次私有访问 fail closed。**这条路径不调用 private 方法，也不复制签名算法。**
- cookie 证明和 active ID 的一致性很关键：没有 cookie、伪造 cookie、过期后 native 产生的新 ID、numeric user cookie，以及 CartToken 创建的新 clone 与原 cookie 不匹配时，都不能凭“对象有一个 customer ID”继承旧 owner。首次 bootstrap 另行建立并发出新凭据，浏览器下一次持有它才能证明该 guest 的访问。
- 不要为了“修正状态”无条件再调用 init_session_cookie()。native 迁移已经删除旧 guest，而发出新 cookie 不会在当前函数中覆盖本请求的旧 $_COOKIE；重复走相同迁移分支可能重新读取已经删除的旧数据。初始化时点未稳定时宁可拒绝/重新引导，具体 HTTP 顺序必须实测。
- public get_session_cookie() 证明签名，**不证明 SQL session 行一定仍存在**；get_session() 的实现会在查不到行时返回 default。若后续方案还要求服务端 guest 撤销或强制行存在性，必须明确 bootstrap 的存储契约再验证，不能假定原生 signed cookie 已包含该保证。[session-handler:656](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content/plugins/woocommerce/includes/class-wc-session-handler.php:656)

以上依据是 §2/§5 所列实际方法体与 lifecycle；它是可采用路线的建议，不是已有 planner 路由已经实现的声明。


从已核原生能力可复用的路线是：

1. WP 作为浏览器身份终止点，REST authentication 之后由服务端构造 registered/guest principal；浏览器不能指定 Actor、owner 或旧 guest。
2. 注册用户复用 WP 当前用户与 session token；访客复用已验签、未过期、guest 类型的 native WC session。首次 bootstrap 与已有 owner 私有读取是不同情况；仅生成了一个新 guest ID 不证明拥有旧项目。
3. 服务端把当前已验证 native identity 映射成 planner owner；只将它经私有服务鉴权交给 planner。所有读取/写入都由同一 resolver 提供身份，不从 body/query 回填。
4. 早注册专门迁移 hook，消费 native 给出的 oldGuest/newUser；planner 仍检查 old owner、目标 user、项目范围及幂等性，并有失败后可恢复的交接记录。
5. 登录/退出后重新 bootstrap nonce 与当前 principal；退出不能继承账号 owner；CartToken 克隆不能迁移 planner 权限。guest 过期后的长期恢复需求需要独立产品决定。

尚缺的真实证据，应在适配器建成后按具体路径补齐：

- 新 guest 首次引导、刷新、开新标签页后恢复同一项目；失效/伪造/已过期 cookie 的私有 GET/HEAD/写入拒绝。
- 标准 Woo 登录与新注册自动登录各自触发正确 oldGuest→user；另一个浏览器的 guest 项目和客户端伪造 old guest 均不能被认领。
- planner 暂不可达时登录迁移仍可重试，旧 guest 存储被 Woo 删除后仍可完成原来那次合法交接。
- logout 与登录 token 过期后，账号私有项目/资产/trace 不能继续以缓存 principal 读取；WP REST 缺 nonce 的降级不能混入 numeric WC session。
- 实际 REST 初始化顺序、nonce 更新、同源/跨源及缺 Origin 的合法 GET 行为、GET/HEAD/OPTIONS/写入的 fail-closed 边界。
- CartToken clone、两账号切换、guest 续期/过期、cookie 禁用，以及浏览器缓存/服务 worker（若实际存在）的私有结果行为。
- p548 是 HTTP 开发站；生产 HTTPS 下 Secure/HttpOnly/实际 SameSite 与反向代理同源判断要读回。未把 CLI 反射探针当作这些浏览器路径已经通过。

## 8. 一手源码版本指纹

以下为本次实际读到文件的 SHA-256，可用于确认后续安装升级后行证据是否漂移；不含任何配置/密钥文件。

| 安装源码（相对 WordPress 根） | SHA-256 |
| --- | --- |
| wp-includes/pluggable.php | 3a2482a65b50d62ebae75a728be98b78985d3a3f5a3e007cb2d0c1338bf05777 |
| wp-includes/rest-api.php | 9c4af1341e37de253323cf7c28da1424f41decc2154904e2b71a4e71c9cdd70c |
| wp-content/plugins/woocommerce/includes/class-wc-session-handler.php | 93020272fe06b6e24624c4288d915b00a3fbc3447e3a324b7d200840c47f059b |
| wp-content/plugins/woocommerce/includes/class-woocommerce.php | 29238678b77ff36c7aa0c30bf92f08039496d594fddca9e77a334b4327df7cb0 |
| wp-content/plugins/woocommerce/includes/wc-user-functions.php | 123d157d214fd618700f4dc95866fe61da71b907eb198fbcf9989f93c1dcf72b |
