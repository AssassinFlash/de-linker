# 登录、注册与表单移动端验收

参照图 `ref-realestate-app.png` 由业主于 2026-10-13 提供，来源缓存：`/Users/chesterjohn/.zcode/cli/image-cache/sess_50c37a2f-a6f4-4a91-9177-f4b95a84b6fd/image-9cb4afe230afcd98ea7fea2041ba2a1e.png`。采用其极简单列、标签在上、全宽圆角控件、单个主按钮、下沉小号链接、成功卡与就近错误语言；不采用手机号登录、第三方登录或数字键盘。

## 范围与桌面最小调整

- 新样式只在 `content/windpress/auth.css`，由既有 `WindPressVolume::files()` 自动扫描并经 `main.css` 编译。
- 移动端断点沿用既有 639px。登录、注册、忘记密码、联系和 Proforma 申请的输入、选择、主按钮及触控目标在 390/430 的 EN/DE 实测均不低于 44px；德语条款链接本身为 44px，不再依赖文本换行。
- 桌面保留原卡片、双列注册与申请摘要栏。联系表单桌面按钮由短代码旧的硬编码色改读 token，尺寸保持 44px。桌面另有实际变化两处（复核实测）：联系成功页在 1440 下不再渲染表单（只显示成功卡与「再发一条」）；注册卡新增 Terms of Sale / Privacy 法律行。
- 注册字段、校验、VIES、审批拦截和端点名未改。新词条走 `.pot/.po/.mo`。

## 状态

- 联系成功：真实本地提交一次，返回 `?contact=sent`，保留 `woocommerce-message`，单一“再发送”动作。
- Proforma 成功：Woo 确认钩子渲染对勾卡，保留原生确认详情，并链接既有 inquiries 端点。
- 错误：登录/注册通知就近置于对应表单；申请页把 Woo 原生 `.woocommerce-error` 移到无效字段旁，不改校验，且实测 `scrollY 1775 -> 1775`，不再弹跳。

## 实测

390/1440/430 的 EN/DE 截图在 `ours-*`。EN/DE 数值见 `metrics.md` 与 `metrics.json`。
