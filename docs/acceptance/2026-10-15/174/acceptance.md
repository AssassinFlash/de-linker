# #174 验收记录（2026-10-15）

## 验收三件套

### 1. Spec + Standards 双评审（全量 diff e6a3221a → 返工后 d17d190d）

评审员结论（独立子代理，真跑全部门禁）：
- **首轮**：8 条验收条目 PASS ×7 + PARTIAL ×1（chip 条款）；发现阻断项 S-1（无 claim 商品技术数据段塌列空洞）、S-2（compare-chip 死选择器）、文档 NIT ×3。
- **返工后**：S-1/S-2 全修（技术数据区按原型合同改为三卡并排、空洞两条规则重写、死选择器修正+同族死规则清理）、NIT 全落。门禁：phpunit 1030 tests / phpcs / phpstan L8 / JS 18 / e2e 16 全绿；CI pass（3m48s）。

### 2. 夹具测试（改动层）

- 新增 `PdpStylesTest.php`（根因回归）+ `TemplatesTest` 结构断言 + `WindPressCacheTest`/`PresentCommandTest` 锚类 + `pdp-ui.test.mjs` 灯箱/deck/scrollspy + `tests/e2e/specs/products.spec.ts` 16 例（1440/390 × EN/DE 遮挡回归 + 三卡铺满断言 + chip 间距）。

### 3. Computer Use 视觉验收（基准=原型变体 A，分支 prototype/pdp-redesign）

主线同机同浏览器截图对照（shots/ 内）：proto-en-1440 vs impl-en-1440、proto-de-390 vs impl-de-390、返工后 impl2-en-1440（三卡+横幅）等。

**首轮发现并已修**：技术数据区 tab deck 偏离合同（原型=三卡并排）→ 返工改齐；特性横幅空态零占位（评审 PASS），有图态用本地夹具（gw60k feature_card 挂附件 6504）验证深色横幅按原型呈现。

**记录的既有偏差**（数据驱动，非设计）：特性带 kicker（ESA Series）无数据字段不带；库存圆点恒 accent 绿（短代码恒输出 is-wait，PHP 本票禁改）；FAQ 无侧图（短代码不出图）。规格 `docs/specs/174-pdp.md` 已知偏差节收录。

**变更台账条目**：PDP 重设计 · 业主裁定 2026-10-15 · A3 像素债务作废（基准改为本票原型）；A3 登记行已交叉引用（docs/debt/REGISTRY-CLOSEOUT-2026-10-15.md）。

## 结论

通过。合并 PR #185。
