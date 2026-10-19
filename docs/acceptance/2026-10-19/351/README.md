# #351 · 注册表单业务类型单选钮可点性 · 验收记录

日期：2026-10-19 · 实例：c351（线上快照，`just present c351` + `just windpress-compile c351` 后的编译缓存）

## 缺陷与修复

`/my-account/register/` 第 1 步的业务类型三个单选钮（`input[name=linker_customer_role]`）被
auth.css 的旧规则（`position:absolute; width:1px; height:1px; opacity:0; pointer-events:none`）
夺走了本体可点性与可聚焦性，只剩外层 label 可点（#351；Playwright 的动作性检查直接拒绝
`page.check('#linker_customer_role_epc')`）。

修复按既有先例复刻：

- **标记**（`plugins/linker-commerce/includes/Registration/RoleField.php`，经
  `woocommerce_form_field_linker_role` 挂载，同 `CountryField` 的扩展示例）：每个原生 input
  嵌进自己的 option label——配置器选择卡的既有嵌套模式
  （`plugins/linker-tools/src/configurator/residential/ResidentialForm.tsx`、
  `configurator.css` 的 `.linker-form__choice label` / `label:has(input:checked)`）。
- **样式**（`plugins/linker-commerce/content/windpress/auth.css`）：input 以
  `position:absolute; inset:0; width/height:100%; opacity:0` 覆盖整个药丸——只用 opacity 隐藏，
  不再碰 pointer-events/display；选中态与焦点环改挂
  `label.radio:has(input:checked)` / `label.radio:has(input:focus-visible)`，焦点环外观与原先一致。

## 证据

- `screens/{en,de}-{1440,390}-step-1-resting.png`：未交互状态，药丸外观与修复前一致。
- `screens/{en,de}-{1440,390}-step-1-focus-ring.png`：对 input 本体 `check()`（门票复现动作）
  后从公司名 Tab 进组——浏览器以选中项为制表位，焦点落在 input 上，药丸带焦点环（EN 1440
  两态像素差全部落在选中且聚焦的 Installer 药丸框内，其余像素零差异）。
- e2e：`tests/e2e/specs/registration-two-step.spec.ts`
  “the business-type radios answer on the input itself, in English and German”——EN/DE 两语言
  走 `page.check('#linker_customer_role_epc')`、Tab 落焦 input、方向键移动选中与焦点、
  焦点环 computed outline 断言。修复前该测试在实例上超时失败（红），修复后通过（绿）。
- 单元/集成：`RoleFieldTest`（标记契约：input 嵌套、checked、required 语义）、
  `RegistrationFormTest::test_the_business_type_inputs_are_nested_native_radios`（真实渲染，
  DOM 断言嵌套）、`tests/js/register-radios.test.mjs`（加载真实 auth.css，pointer-events 守卫）。

## 重跑

```bash
just up c351 && just present c351 && just windpress-compile c351
LINKER_E2E_SKIP_SERVICES=1 just e2e c351 specs/registration-two-step.spec.ts
node docs/acceptance/2026-10-19/351/capture.mjs   # 默认 http://127.0.0.1:9153
```
