# Installation Routing 代码审计（#548）

## 1. 设备实例（`instances`）来源、`disabled` 确切条件与 `0 / disabled` 根因分析

### 1.1 `instances` 从哪里来？Equipment 采纳（Adopt/Apply）写了什么？

- **`InstallationEditor` 读取的 `instances` 来源**：
  - `apps/planner/src/components/installation/InstallationEditor.tsx:112`：`const plan = readInstallation(inputs.installation);`
  - `apps/planner/src/domain/installation.ts:240-247, 299-300`：当项目的 `inputs.installation` 为 `undefined` 时，`readInstallation(undefined)` 返回 `emptyInstallation()`，其初始值为 `{ schema_version: 1, geometry_sha256: null, instances: [], circuits: [], routes: [], cable_runs: [] }`。
  - `instances` 仅在用户在 Installation routing 步骤打开 `<InstanceForm>`（`apps/planner/src/components/installation/InstallationEditor.tsx:525-535, 699`）并提交时，通过 `edit("instances", v)`（`apps/planner/src/components/installation/InstallationEditor.tsx:239-260`）写入 `inputs.installation.instances`（再经 `apps/planner/src/components/ProjectEditor.tsx:933-941` 的 `change` 写回 `draft.history.current.installation`）。
- **Equipment 步骤点 `"Use this combination in the project"` 写了什么**：
  - 按钮位于 `apps/planner/src/components/equipment/EquipmentSearchResult.tsx:224-238`，点击触发 `applySelected()`（`EquipmentSearchResult.tsx:99-116`），调用父组件传入的 `apply={applyEquipment}`（`apps/planner/src/components/energy/EnergyWorkspace.tsx:1994`）。
  - `applyEquipment(candidate)`（`apps/planner/src/components/energy/EnergyWorkspace.tsx:777-866`）：
    - 单系统候选（`!isPlantCandidate(candidate)`，`EnergyWorkspace.tsx:818-855`）：将候选的 `inverter_product_id`、`battery_product_id`、`modules_per_stack`、`parallel_stacks`、`accessory_product_ids` 通过 `changeEquipment(snapshot, patch)`（`apps/planner/src/domain/equipment.ts:122-133`）写入 `equipment_setup`，再通过 `compileEquipment(...)`（`apps/planner/src/domain/equipment.ts:134-153`）写入 `equipment_selection`（含 `product_revisions`）与 `equipment_candidate`（`{ run_id, candidate_id, assessment_sha256 }`，`EnergyWorkspace.tsx:805-809, 845-851`）。
    - 多系统候选（`isPlantCandidate(candidate)`，`EnergyWorkspace.tsx:811-817`）：调用 `adoptPlantCandidate`（`apps/planner/src/domain/plantSearch.ts:115-161`），写入 `equipment_plant_setup`、`equipment_plant` 及可选的 `equipment_candidate`。
  - 随后 `applyEquipment` 调用 `equipmentContext(next)` 与 `applyEquipmentContext(inputs, replacement)`（`EnergyWorkspace.tsx:856-861`）。在 `apps/planner/src/domain/equipmentPlant.ts:88-122` 中，`equipmentFields` 仅包含：
    `["equipment_plant", "equipment_plant_setup", "equipment_plant_requirements", "equipment_selection", "equipment_candidate", "equipment_setup", "equipment_requirements", "equipment_condition_inputs", "pv_string_plan", "pv_plant_string_plan"]`。
  - **结论**：采纳设备组合（如 `6508+1958`）**完全不触碰 `inputs.installation`**，不会向 `inputs.installation.instances` 自动生成任何物理设备实例。

### 1.2 `"Add device or site connection"` 按钮 `disabled` 的确切条件（`file:line`）

1. **外层 `<fieldset>` 禁用条件**（`apps/planner/src/components/ProjectEditor.tsx:913-919`）：
   ```tsx
   disabled={
     busy ||
     Boolean(draft.pending) ||
     Boolean(draft.conflict) ||
     recoveries.length > 0
   }
   ```
2. **按钮自身 `disabled` 条件**（按钮文案定义于 `apps/planner/src/components/installation/InstallationEditor.tsx:351`，按钮渲染于 `apps/planner/src/components/installation/InstallationEditor.tsx:684-702`）：
   ```tsx
   disabled={
     !linksValid ||
     !materialsValid ||
     !protectionValid ||
     !geometry.sources.length ||
     (kind === "instances"
       ? products.isFetching || !products.data?.prepared
       : kind === "circuits"
         ? plan.instances.length === 0
         : kind === "routes"
           ? plan.circuits.length === 0
           : !plan.circuits.length || !plan.routes.length)
   }
   ```
   对于 `"Add device or site connection"`（`kind === "instances"`），确切布尔条件为：
   - `!linksValid`（`<PvStringLinks>` 表单未处于有效闭合态，默认 `true`，`InstallationEditor.tsx:148, 736`）
   - `|| !materialsValid`（`<InstallationMaterials>` 正在编辑未提交，默认 `true`，`InstallationEditor.tsx:149, 717`）
   - `|| !protectionValid`（`<InstallationProtection>` 正在编辑未提交，默认 `true`，`InstallationEditor.tsx:150, 725`）
   - `|| !geometry.sources.length`（**项目几何文档 `geometry.sources` 为空**，`InstallationEditor.tsx:690`）
   - `|| products.isFetching`（`products/current` 正在请求中，`InstallationEditor.tsx:135, 692`）
   - `|| !products.data?.prepared`（`products/current` 未就绪，要求 `row.figure_projection_version === 2 && row.compatibility_origin === "woocommerce"`，`apps/planner/src/data/equipmentProducts.ts:98-100`，`InstallationEditor.tsx:692`）

### 1.3 为什么已采纳组合后仍是 `0 / disabled`——是缺陷还是缺前置步骤？

- **并非代码执行异常，而是契约设计与前置步骤缺失**：
  1. **计数为 `0` 是因为物理实例需带现场坐标与测量来源手动声明**：`DeviceInstance`（`apps/planner/src/domain/installation.ts:46-53`）要求每个物理设备绑定测量/图纸来源 `source_id` 以及至少 1 个带三维坐标（`east_m`、`north_m`、`height_m`）的连接点 `ports`（见 `apps/planner/src/components/installation/NetworkForms.tsx:260-265` 说明文案）。Equipment 步骤的选型（`equipment_selection`）没有空间坐标与测量来源，因此不会自动转为 `installation.instances`。
  2. **按钮 `disabled` 是因为缺少前置步骤——尚未添加 `geometry.sources`（测量或图纸来源）**：
     - 若用户跳过 Roof design 或未在项目中添加任何测量/图纸来源，则 `geometry.sources` 为 `[]`（`apps/planner/src/domain/geometryCommands.ts` 中 `emptyGeometry()` 初始化 `sources: []`）。
     - 此时 `InstallationEditor.tsx:396-403` 会显示提示：`"Add the source of your site measurements or drawing before recording positions. A roof layout is optional."`，同时 `InstallationEditor.tsx:690` 因 `!geometry.sources.length === true` 将 `"Add device or site connection"` 置为 `disabled`。
     - **解除方法**：先点击同页上方的 `"Add measurement or drawing source"` 按钮（`InstallationEditor.tsx:567-574`），在 `<GeometryForm>`（`InstallationEditor.tsx:442-523`）中填写 `"Source reference"`、选择 `"Source type"`、填写 `"Permission or licence basis"`、勾选 `"I may save, use and export these project measurements or drawing data."` 并提交，向 `geometry.sources` 写入一条来源后，`"Add device or site connection"` 即刻变为可用。

---

## 2. 手动添加设备时的产品目录来源（`file:line`）

- **结论**：**全部当前 Woo 产品目录原样平铺（按后端 `canonical_product_id` 顺序），不优先、不置顶、也不过滤已采纳组合（`6508+1958`）**。
- **代码链路**：
  1. `apps/planner/src/components/installation/InstallationEditor.tsx:135`：调用 `const products = useEquipmentProducts(client, session.query_scope, true);`。
  2. `apps/planner/src/data/equipmentProducts.ts:103-112` 与 `apps/planner/src/data/currentProductQuery.ts:5-28`：调用 `client.query("products/current", { schema_version: 1 }, scope, signal)`，经 `readEquipmentProducts`（`equipmentProducts.ts:25-102`）校验并返回全量 `products: EquipmentProduct[]`。
  3. `apps/planner/src/components/installation/InstallationEditor.tsx:526-535`：渲染 `<InstanceForm>` 时传入 `products={products.isError || products.isFetching ? [] : (products.data?.products ?? [])}`，未传入 `inputs.equipment_selection` 或 `inputs.equipment_candidate`。
  4. `apps/planner/src/components/installation/NetworkForms.tsx:231-255`：`<InstanceForm>` 的 `"Device or site connection"` 下拉框（`<select name="product">`）依次渲染：
     - 空选项 `"Choose a product or site connection"`（`NetworkForms.tsx:239-241`）
     - `"Site connection"`（`value="site"`，对应 `product_id: null`，`NetworkForms.tsx:242`）
     - （仅当编辑已保存实例且该 `product_id` 不在当前 `products` 中时）`"Saved device · current data unavailable"`（`NetworkForms.tsx:243-248`）
     - 全量产品列表 `products.map((p) => <option key={p.id} value={p.id}>{p.brand} {p.model}</option>)`（`NetworkForms.tsx:249-253`）。

---

## 3. `ConductorManufacturerResults` 渲染的完整前置条件链与 `fact.source` 引用格式

### 3.1 完整前置条件链（逐环 `file:line`）

1. **前置环 A：`geometry.sources`（测量/图纸来源）**
   - `geometry.sources.length > 0`（解除按钮禁用：`apps/planner/src/components/installation/InstallationEditor.tsx:690`）。
   - 被实例与路由引用的 `source_id` 必须存在于 `geometry.sources`，且 `permissions.export === "permitted"`（前端新建来源固定写入 `export: "permitted"`：`InstallationEditor.tsx:463-467`；后端复核校核：`services/engine/src/linker_engine/planning/installation_takeoff.py:421-428`）。

2. **前置环 B：`plan.instances`（物理设备实例与连接点）**
   - `plan.instances` 中存在至少一个绑定了目标 Woo 产品的实例（例如 `product_id = 6508` GoodWe `GW99.99K-ETR-G10` 或 `product_id = 1958` GoodWe `GW261.2-BAT-LCD-G10`），其 `product_id` 与 `product_revision` 与当前 `products/current` 一致（表单写入：`apps/planner/src/components/installation/NetworkForms.tsx:196-223`；候选提取匹配：`apps/planner/src/domain/installationConductorComparison.ts:27-33`；后端校核：`services/engine/src/linker_engine/planning/installation_conductor_comparison.py:55-71`）。
   - `plan.instances` 中存在至少两个不同的连接点 `(instance_id, port_id)` 供回路连接（可在同一实例点 `"Add connection point"` 建第 2 个端口，或新建第 2 个设备/站点连接实例；校验见 `apps/planner/src/domain/installation.ts:331-347` 与 `services/engine/src/linker_engine/planning/installation_inputs.py:445-450`）。

3. **前置环 C：`plan.circuits`（回路及类型匹配）**
   - `plan.instances.length > 0` 解除 `"Add circuit"` 禁用（`InstallationEditor.tsx:693-694`）。
   - 在 `<CircuitForm>`（`apps/planner/src/components/installation/NetworkForms.tsx:452-632`）创建回路，`start` 与 `end` 指向两个不同连接点，且其中一端必须是上述含手册导体事实的设备实例（`NetworkForms.tsx:829-831`；`installation_conductor_comparison.py:26-35`）。
   - 回路的 `kind`（`Connection type`）必须与产品 `installation_facts` 条目的 `(basis, specification.terminal_domain)` 严格对应，且该条目 `conditions` 为空数组 `[]`（前端提取：`apps/planner/src/domain/installationConductorComparison.ts:44-70`；前端按回路过滤：`apps/planner/src/components/installation/NetworkForms.tsx:825-833`；后端核对：`services/engine/src/linker_engine/planning/installation_conductor_comparison.py:97-114`；前端响应核对：`apps/planner/src/domain/installation.ts:767-778`）：
     - `circuit.kind === "ac"` ⇔ `fact.basis === "manufacturer_recommended_ac_conductor"` 且 `spec.terminal_domain === "ac"`（如 `6508` 的 `fact_id: "ac-conductor"`，推荐范围 `50–70 mm²`，ETR 手册 p.61，`tools/migrate/548-installation-facts.json:2442-2475`）；
     - `circuit.kind === "protective_earth"` ⇔ `fact.basis === "manufacturer_recommended_pe_conductor"` 且 `spec.terminal_domain === "pe"`（如 `6508` 的 `fact_id: "protective-earth-conductor"`，推荐范围 `25–35 mm²`，ETR 手册 p.60，`tools/migrate/548-installation-facts.json:2477-2506`）；
     - `circuit.kind === "battery_dc"` ⇔ `fact.basis === "manufacturer_model_specific_conductor"`、`fact.id === "battery-cluster-conductor"` 且 `spec.terminal_domain === "battery_dc"`（如 `6508` 的 `fact_id: "battery-cluster-conductor"`，推荐范围 `70–70 mm²`，ETR 手册 p.60，`tools/migrate/548-installation-facts.json:2508-2541`；或 `1958` 的 `fact_id: "battery-cluster-conductor"`，推荐范围 `50–50 mm²`，BAT-C 手册 p.50，`tools/migrate/548-installation-facts.json:2371-2403`）。

4. **前置环 D：`plan.routes`（物理路径）**
   - `plan.circuits.length > 0` 解除 `"Add route"` 禁用（`InstallationEditor.tsx:695-696`）。
   - 在 `<RouteForm>`（`apps/planner/src/components/installation/NetworkForms.tsx:633-796`）创建至少含 2 个路径点的路径（`submitDisabled={points.length < 2}`，`NetworkForms.tsx:681`；可通过 `"Use current circuit endpoints"` 下拉框一键填入回路起止点坐标，`NetworkForms.tsx:652-664, 692-704`）。

5. **前置环 E：`plan.cable_runs`、`conductor`、`binding.conditions_confirmed` 与 `confirmation_context`**
   - `plan.circuits.length > 0 && plan.routes.length > 0` 解除 `"Add cable or conductor"` 禁用（`InstallationEditor.tsx:697`）。
   - 在 `<CableForm>`（`apps/planner/src/components/installation/NetworkForms.tsx:798-1376`）中：
     1. 选择上述 `circuit`（`:1036-1054`）、`route`（`:1055-1070`）和 `construction`（`:1071-1090`）。
     2. 填写配对必填的 `"Declared cross-section"`（`cross_section` > 0）与 `"Basis for the declared cross-section"`（`conductor_note` 非空），经 `v.paired("cross_section", "conductor_note", { positive: true })` 生成 `next.conductor`（`NetworkForms.tsx:910-912, 947-955, 1112-1141`）；未填 `conductor` 时选择厂家导体对比提交会抛 `"manufacturer_comparison_requires_conductor"`（`:970-971, 991-992`）。
     3. 在 `"Equipment manufacturer cross-section instruction (optional)"` 下拉框（`<select name="manufacturer_conductor">`，`NetworkForms.tsx:1202-1246`）中选择匹配的候选条目 `candidate:...`（此时 `activeManufacturer` 解析成功，`manufacturerAvailable === true`，`:834-855`）。
     4. **在所有上述字段填定之后**，勾选确认框 `<input type="checkbox" name="manufacturer_confirmed">`（`"I confirm that this manufacturer instruction applies to this conductor and circuit."`，`NetworkForms.tsx:1280-1295`），使 `manufacturerConfirmed = true` 且 `manufacturerConfirmedHere = true`。注意：修改 `circuit`、`route`、`construction`、`cross_section`、`conductor_note`、`cable_reference`、`core_roles` 任一字段都会触发 `invalidateCurrentConfirmation()` 或重置 `manufacturerConfirmed = false`（`NetworkForms.tsx:881-887, 1044, 1061, 1077, 1104, 1126-1129, 1155, 1333, 1350, 1363`）。
     5. 提交 `<CableForm>` 时构造 `next.manufacturer_comparison`（`NetworkForms.tsx:981-1013`）：
        - 绑定标识：`{ instance_id, product_id, product_revision, fact_id, document_id, document_revision }`（`:981-988`）
        - 确认标志：`conditions_confirmed: manufacturerConfirmed && manufacturerAvailable`（`:1010-1011`）
        - 上下文快照 `confirmation_context`（`:993-1006`，类型定义于 `apps/planner/src/domain/installation.ts:151-158`）：
          ```ts
          {
            circuit: { id: circuit.id, kind: circuit.kind, start: circuit.start, end: circuit.end },
            construction: next.construction,
            conductor: { ...next.conductor, cable_reference: next.conductor.cable_reference ?? null },
            core_roles: next.core_roles ?? [],
          }
          ```

6. **前置环 F：执行 `"Review installation"` 与前后端对称校核及渲染门控**
   - 点击 `"Review installation"` 按钮（因 `hasTerminalFeature(plan)` 在 `apps/planner/src/domain/installationTerminals.ts:44-50` 对含 `manufacturer_comparison` 的计划返回 `true`，按钮文案为 `"Review installation"`，`InstallationEditor.tsx:738-773`），触发 `check()`（`InstallationEditor.tsx:274-325`）请求 `POST /installation/review`（`services/engine/src/linker_engine/planning/http_app.py:591-632`）。
   - 注意：`http_app.py:598-602` 检查 `expected_revision != project.revision`；`InstallationEditor.tsx:294` 传的是 `savedRevision`（即 `draft.baseline.revision`），因此无需在点 `"Review installation"` 前先点 `"Save project"`（只要远端项目版本未被其他会话推进即可直接复核）。
   - 后端 `route_takeoff`（`services/engine/src/linker_engine/planning/installation_takeoff.py:466-472`）调用 `conductor_comparison(plan, cable, selected)`（`services/engine/src/linker_engine/planning/installation_conductor_comparison.py:16-129`）：
     - 校验 `binding.conditions_confirmed` 为 `True`（`:37-39`）；
     - 校验 `binding.confirmation_context` 与当前 `{ circuit: {id, kind, start, end}, construction, conductor, core_roles }` 深度相等（`:40-54`）；
     - 校验实例、产品版本、文档版本与 `_source_is_current`（`:55-96`）；
     - 计算 `status` 为 `"within_recommendation"` 或 `"outside_recommendation"` 并写入 `fact`（`:115-128`）。
   - 前端 `readInstallationReview`（`apps/planner/src/domain/installation.ts:727-821`）复验返回的 `manufacturer_comparison` 与 `confirmation_context`（`:789-802`），`check()` 将 `result.prepared_inputs` 写回 `plan` 并保存 `review`（`InstallationEditor.tsx:317-325`）。
   - `shown` 门控（`InstallationEditor.tsx:201-214`）成立后，`InstallationEditor.tsx:791-796` 渲染 `<ConductorManufacturerResults cables={shown.cables} locale={locale} />`，其中 `ConductorManufacturerResults.tsx:13-14` 过滤 `cables.filter((cable) => cable.manufacturer_comparison)` 并渲染结果卡片（`:30-91`）。

### 3.2 `ConductorManufacturerResults` 显示的 `fact.source` 引用格式

在 `apps/planner/src/components/installation/ConductorManufacturerResults.tsx:47-53, 73-88` 中，当 `comparison.fact !== null`（即 `within_recommendation` 或 `outside_recommendation`）时：
- 从 `comparison.fact` 读取 `source = readObject(fact.source)`、`specification = readObject(fact.specification)`、`range = readObject(specification.recommended_conductor_mm2)`（`:47-53`）。
- 推荐截面范围显示格式（`:63-71`）：
  - 英文：`Manufacturer range: {formatDecimal(range.low, locale)}–{formatDecimal(range.high, locale)} mm²`
  - 德文：`Herstellerbereich: {formatDecimal(range.low, locale)}–{formatDecimal(range.high, locale)} mm²`
- `fact.source` 折叠块 DOM 与文本格式（`:73-88`）：
  ```tsx
  <details>
    <summary>{t("Manufacturer source", "Herstellerquelle")}</summary>
    <a
      href={`${source.url}#page=${source.page}`}
      target="_blank"
      rel="noreferrer"
    >
      {t("Document · page", "Dokument · Seite")} {String(source.page)}
    </a>
    <blockquote>{String(source.quote)}</blockquote>
  </details>
  ```
  - 折叠标题：`Manufacturer source`（DE：`Herstellerquelle`）
  - 外部链接：`href="{source.url}#page={source.page}"`，锚文本为 `Document · page {source.page}`（DE：`Dokument · Seite {source.page}`），例如指向 ETR 手册第 61 页 `https://de-linker.com/.../GW_ETR-50-125kW_User-Manual-EN_V1.0.pdf#page=61`，显示 `Document · page 61`
  - 原文摘录：`<blockquote>{source.quote}</blockquote>`（例如 `"Inverter AC Cable | Multi-core outdoor copper cable Conductor cross-sectional area: 50mm²-70mm² • Cable outer diameter: 22-43mm • SPE ≥ 1/2×SAC • | User-provided"`）

---

## 4. 从“候选已采纳”到“看到 ETR 手册导体推荐表”的最短 UI 操作序列

前提：已在 Equipment 步骤点击 `"Use this combination in the project"` 采纳组合 `6508+1958`（`GoodWe GW99.99K-ETR-G10` + `GoodWe GW261.2-BAT-LCD-G10`）并已保存项目。

1. **切换到 Installation routing**：在左侧导航（或顶部截面下拉框）点击 **`"Installation routing"`**（`ProjectEditor.tsx:550-559`）。
2. **添加测量/图纸来源（解除按钮 disabled）**：点击 **`"Add measurement or drawing source"`**（`InstallationEditor.tsx:567-574`）→ 填 `"Source reference"`（如 `Site plan`）、选 `"Source type"`（如 `Site measurement`）、填 `"Permission or licence basis"`（如 `Owner`）、勾选 **`"I may save, use and export these project measurements or drawing data."`** → 点击 **`"Apply"`**（`GeometryForm.tsx:168`）。
3. **添加 ETR 逆变器实例及两个连接点**：点击 **`"Add device or site connection"`**（`InstallationEditor.tsx:684-702`）→ 填 `"Name"`（如 `ETR`）、在 `"Device or site connection"` 下拉框选 **`"GoodWe GW99.99K-ETR-G10"`**（即 6508）、在 `"Source reference"` 选刚建的来源 → 填第 1 个连接点的 `"Connection point name"`（如 `AC Grid`）及 `"East"` / `"North"`（如 `0`、`0`）→ 点击 **`"Add connection point"`**（`NetworkForms.tsx:401-412`，或单独再建一个 `Site connection` 实例）填第 2 个连接点的 `"Connection point name"`（如 `Grid Point`）及 `"East"` / `"North"`（如 `10`、`0`）→ 点击 **`"Apply"`**。
4. **添加回路（匹配 ETR 导体域）**：点击 **`"Add circuit"`**（`InstallationEditor.tsx:684-702`）→ 填 `"Name"`（如 `AC Circuit`）、在 `"Connection type"` 下拉框选 **`"AC"`**（若看 PE 或电池簇导体则选 `"Protective earthing"` 或 `"Battery DC"`）、在 `"From connection point"` 与 `"To connection point"` 分别选上述两个连接点 → 点击 **`"Apply"`**。
5. **添加路径**：点击 **`"Add route"`**（`InstallationEditor.tsx:684-702`）→ 填 `"Name"`（如 `Route 1`）、选 `"Source reference"`、在 `"Use current circuit endpoints"` 下拉框选刚建的 **`"AC Circuit"`**（自动带入 2 个端点坐标，`NetworkForms.tsx:692-704`）→ 点击 **`"Apply"`**。
6. **添加导体并绑定确认 ETR 手册推荐项**：点击 **`"Add cable or conductor"`**（`InstallationEditor.tsx:684-702`）→ 填 `"Name"`（如 `AC Cable`）、选 `"Circuit"`（`AC Circuit`）、选 `"Recorded route"`（`Route 1`）、选 `"Physical construction"`（如 `One multicore cable`）→ 填 `"Declared cross-section"`（如 `50`）与 `"Basis for the declared cross-section"`（如 `Installer cable schedule`）→ 在 **`"Equipment manufacturer cross-section instruction (optional)"`** 下拉框选 **`"GoodWe GW99.99K-ETR-G10 · AC conductor · p. 61"`**（此时表单内即展开 `<details open>` 显示 ETR 手册引用与原文，见 `NetworkForms.tsx:1250-1265`）→ 勾选 **`"I confirm that this manufacturer instruction applies to this conductor and circuit."`** → 点击 **`"Apply"`**。
7. **运行复核渲染结果卡片**：点击 **`"Review installation"`** 按钮（`InstallationEditor.tsx:738-773`），复核完成后页面下方即渲染 **`"Manufacturer conductor cross-section comparisons"`**（`<ConductorManufacturerResults>`），显示 `"Declared cross-section: 50 mm²"`、`"Manufacturer range: 50–70 mm²"`、`"Within the recommended cross-section range"` 及可展开的 `"Manufacturer source"`（`Document · page 61` 与 ETR 手册原文引用）。
