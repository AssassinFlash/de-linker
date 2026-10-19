# #353 · 后台账户页视觉语言移植（原型变体 C）

功能契约不动（`wp_add_dashboard_widget`、顶栏节点、`WP_List_Table` 历史、REST 决定端点、focus 深链、三态+原因、撤销全部保留），只把业主选定的原型视觉语言（`docs/prototypes/2026-10-17-accounts/accounts-prototype.css`，变体 C，`screens/accounts-C-drawer.png`）移植进 #227 已有的 admin 样式文件（`plugins/linker-commerce/src/accounts/style.css`，构建为 `build/style-accounts.css`）。无新样式表、无内联样式；选择器全部 admin 域（`.linker-*`、`#linker-*`、`#wpadminbar …`），零前台选择器。

改动面：

- `src/accounts/style.css` — token 移植（下表）。
- `src/accounts/AccountCard.tsx` — 仅加视觉类钩子：状态 pill（`linker-status linker-status-<status>`）、三态按钮 `linker-decide-approve|-restrict|-reject`、确认按钮随决定着色。
- `src/accounts/AccountsApp.tsx` — 决定后同步历史表状态 pill 的类名（原只更新文字）。
- `includes/Registration/AccountsAdmin.php` — 小工具标题里数量从 `(N)` 括号文字改为徽章 span（`linker-count-badge`；计数 span 与 `data-linker-account-count` 属性不变，e2e/集成断言不受影响）。
- `includes/Registration/AccountsTable.php` — 历史表状态列加 `linker-status linker-status-<status>` 类（`linker-account-status-label` 保留，REST 保存后的实时更新兼容）。
- `build/*` — 随 `npm run build` 重建（含 RTL 与 manifest）。

## 原型 → 实现 token 表

| 元素 | 原型值（accounts-prototype.css） | 移植后 |
|---|---|---|
| 信号胶囊基型 `.lap-chip` | 11px/1.4，padding 2px 8px，radius 999px，margin 0 4px 4px 0，1px 边 | `.linker-account-signals .notice` 同值 |
| 胶囊 ok | 字 #00661b / 底 #edfaef / 边 #9ad3a8 | `.notice-success` 同值 |
| 胶囊 warn | 字 #7a5200 / 底 #fcf9e8 / 边 #f0c33c | `.notice-warning` 同值 |
| 胶囊 bad | 字 #8a2424 / 底 #fcf0f1 / 边 #e6a6a8 | `.notice-error` 同值（数据层当前不产 error tone，规则齐备） |
| 胶囊 info | 字 #1d4f7c / 底 #f0f6fc / 边 #a7c6e6 | `.notice-info` 同值 |
| 卡片 `.lap-c` | 边 1px #dcdcde，radius 6px，padding 12px，列间距 6px，h3 14px/margin 0 | `.linker-account-card` 同值；操作行 `margin-top:auto` 沉底 |
| 卡片区 `.lap-cards` | `repeat(auto-fill, minmax(300px,1fr))`，gap 12px | `.linker-account-cards` 同值 |
| 焦点卡 `.lap-focus-card` | 边 #2271b1 + `box-shadow: 0 0 0 1px #2271b1` | `.is-focused` 同值（替换旧 4px 左蓝边） |
| 小工具 `.lap-widget` | 左边 4px #d63638（整框 1px #c3c4c7），h2 16px | `#linker-accounts-widget`（原生 postbox 边框即 #c3c4c7） |
| 数量徽章 `.lap-badge` | 底 #d63638 白字，radius 999px，padding 1px 8px，12px，左距 6px | `.linker-count-badge` 同值 |
| 顶栏红旗 `.lap-flag` | 底 #d63638 白字胶囊，padding 3px 10px，600 | `.linker-review-label` / `.linker-review-compact`（替换旧“整节点红底 #b32d2e”做法） |
| 抽屉 `.lap-drawer` | 面 #f0f0f1，叠距 10px，阴影 `-8px 0 24px rgba(0,0,0,.2)`，遮罩 35% | `#linker-accounts-dialog` 同值；宽 520px/边距 20px 维持 #227 文档化阅读布局（accounts-admin.md） |
| 状态 pill `.lap-status` | 12px/600，padding 2px 8px，radius 3px；pending/restricted 琥珀 #fcf9e8/#7a5200，approved 绿 #edfaef/#00661b，rejected 红 #fcf0f1/#8a2424 | `.linker-status-*` 同值（卡片 + 历史表 + 实时更新） |
| 查证链接 | #353 裁定为胶囊按钮（原型 B 屏是 `.button` 小按钮） | `.linker-account-links a`：1px #2271b1 边、#f0f6fc 底、#2271b1 字、radius 999px、hover 反白 |
| 三态按钮 | #353：APPROVE 绿 / RESTRICT 琥珀 / REJECT 红；原型锚点：绿 `.lap-pill--done` #00a32a、琥珀 `.lap-check--warn` #dba617、红 `.lap-danger-solid` #b32d2e | `linker-decide-*` 底/边取锚点同值；琥珀上用 #1d2327 文字（白字对比不足，暗字 ≈7:1）；hover 按加深惯例：#008a20 / #c79512 / #8f2425（后两个为基色加深派生） |
| 详情表 `.lap-dl` | 110px/1fr，gap 4px 12px，dt #646970 不加粗 | `.linker-account-fields` 同值（去旧行分隔线） |

## 逐元素目检（基准 `prototype-reference.png` = 原型 `screens/accounts-C-drawer.png`）

夹具：实例 `c353`（本工作树干净安装，端口 9159）。两个虚构待审客户——`c353-huber`（Huber Solartechnik GmbH，公司域邮箱、VIES 有效、 Installer、DE，覆盖 绿/蓝 胶囊与 GOOGLE/NORTH DATA/WEBSITE/VIES 四个查证胶囊）与 `c353-quickshop`（Example What is SEO Services，虚构 gmail 地址、无 VAT，覆盖 琥珀×2/蓝 胶囊）。邮箱均为虚构地址（gmail.com 仅作免费邮箱信号夹具，本地实例不外发）。

| 元素 | 判定 | 证据 |
|---|---|---|
| 信号胶囊（彩色、999px、11px） | 通过 | `dashboard-widget-1440.png`、`drawer-1440.png`；info 淡蓝（#f0f6fc 系）在截图里近似浅灰，计算样式核实为 #1d4f7c/#f0f6fc/#a7c6e6 |
| 查证胶囊按钮 GOOGLE ↗ / NORTH DATA ↗ / WEBSITE ↗ / VIES ↗ | 通过 | 同上；卡片一四枚齐全，卡片二按数据层规则只有 GOOGLE/NORTH DATA |
| 三态强色按钮 APPROVE 绿 #00a32a / RESTRICT 琥珀 #dba617 / REJECT 红 #b32d2e | 通过 | `dashboard-widget-1440.png`、`drawer-1440.png`；计算样式核实琥珀按钮文字 #1d2327 |
| 确认按钮随决定着色（限制=琥珀、拒绝=红） | 通过 | `drawer-restrict-1440.png`、`drawer-reject-1440.png` |
| 卡片形状：1px 边、6px 圆角、12px 内距、h3 14px、列距 6px | 通过 | `dashboard-widget-1440.png` |
| 小工具：红色 4px 左边 + 红胶囊数量徽章 + 16px 标题 | 通过 | `dashboard-widget-1440.png`（标题的 `(N)` 括号文字已移除） |
| 抽屉同款视觉：#f0f0f1 面、左缘阴影、35% 遮罩、白卡堆叠 | 通过 | `drawer-1440.png` |
| 顶栏红旗：红色胶囊（不再整节点红底） | 通过 | `adminbar-flag-1440.png`、`history-1440.png` |
| 历史表状态 pill（Approval 列琥珀“Pending review”） | 通过 | `history-1440.png` |
| 390：抽屉全宽、无横向溢出、胶囊/按钮完整 | 通过 | `drawer-390.png`、`dashboard-390.png` |

说明两点：

- **小工具内单列**：1440 视口下 WP 仪表盘“normal”列约 575px，原型的 `minmax(300px,1fr)` auto-fill 规则在此宽度就是一列（规则原样移植）；全宽挂载点（Accounts 页的 focus/限制区）同一规则呈现多列。
- **移植中发现并修掉一个回归**：给 `#linker-accounts-dialog` 直接写 author `display` 会盖过 UA 的 `dialog:not([open]) { display: none }`，导致关闭后抽屉仍可见（截图流程实测发现；现 flex 布局加 `[open]` 限定，关闭行为经 `drawer-390.png` 流程验证）。

## 验证

| 检查 | 结果 |
|---|---|
| `just check`（PHPCS、PHPStan、eslint/tsc/prettier、Ruff/mypy、翻译、构建清单） | 通过 |
| `just test`（commerce PHPUnit 1027、commerce/tools React 286、工具浏览器 9、engine 112、local 98、pull 147、cutover 20 等） | 全部通过 |
| admin 域选择器 | 手工核对：样式表内仅 `.linker-*` / `#linker-*` / `#wpadminbar …` / `#linker-accounts-widget`，零前台选择器（无既有自动化门槛读该文件） |
| e2e `accounts-admin.spec.ts` 相关断言 | 类名/角色定位不受影响（按钮按 accessible name、计数按 `data-linker-account-count`、徽章 span 保留原属性）；`#353` 分支未跑实例 e2e，主干 CI 与评审站覆盖 |

截图：`screens/`（1440：`dashboard-1440`、`dashboard-widget-1440`、`drawer-1440`、`drawer-restrict-1440`、`drawer-reject-1440`、`history-1440`、`adminbar-flag-1440`；390：`dashboard-390`、`drawer-390`）。
