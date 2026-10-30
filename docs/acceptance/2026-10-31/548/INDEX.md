# #548 安装事实线 · 验收索引（2026-10-31）

这份索引只做一件事：让人一眼看出每项**验证到什么程度**、证据在哪、还有什么没验证。
详细记录在两份文档里，这里不重复内容，只给判断。

状态用词是固定的：

- **已读回** —— 在生产上取到了实际数据或报告内容，不是推断。
- **已隔离** —— 失败被定位到具体代码路径，且证明了这是正确行为或已知缺口。
- **未验证** —— 没有证据，附解除条件。

## 生产状态

| 项 | 值 | 状态 |
| --- | --- | --- |
| `knowledge` / `engineering` 消费者 | 均 `ready` | 已读回 |
| 带 `_linker_installation_facts` 的商品 | 534 中 9 个，79 条 | 已读回 |
| `source_revision` | `dc2b9fa7d994…` | 已读回 |
| `preview --production` | `{"changes": 0}` | 已读回 |

## 功能项

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 事实写入商品元数据 | 9 商品 79 条，`verify` 无待办 | `installation-facts-apply.md` |
| 工程 feed 携带事实 | `EngineeringFeed::item()` 含 `installation_facts` | 同上 |
| 引擎物料投影 | `status: documented`，字段与计划一致 | 同上 |
| `project_materials` 消费 | 真实 feed 产 17 条带页码行 | 同上 |
| 报告 BOM（德文，生产读回） | 13 行，德语标签与 `p.152–155` | `installation-facts-apply.md` 德文报告读回 |
| 报告 BOM（英文，生产读回） | 13 行，英文标签与 `p.153–155` | `installation-facts-apply.md` 英文报告读回 |
| 设备检查 | `succeeded`，5 项检查 3 satisfied | 同上 |
| 路由报告 | `succeeded`，含 `installation-routing` 与免责声明 | 同上 |
| 已保存方案读取（作者） | 返回原始输入，不含旧价格 | `saved-solution-readback.md` |
| 已保存方案权限边界 | 他人读取得 404，不泄露 | 同上 |

## 已隔离的两处"看起来像缺陷"

| 现象 | 结论 | 依据 |
| --- | --- | --- |
| `Installation routing` 显示 0 | 正确行为 | 该字段来自兼容合同的 `meter`/`backup`，不读安装事实；路由报告另需 `installation.cable_runs` |
| `product_evidence_changed` 拒绝设备检查 | 准备状态的时间差，非数据不一致 | `engineering` 未 `ready` 时 `prepared_view` 不含该商品；恢复后同一项目成功 |

## 未验证（附解除条件）

| 项 | 缺什么 | 解除条件 |
| --- | --- | --- |
| 界面读回 `?saved_solution=8207` | 一个能登录 user 1 的浏览器会话 | 提供凭据，或授权临时启用一次性登录后移除 |
| 多台逆变器的安装方案出报告 | 模型不支持：`EquipmentSelection` 只有单个 `inverter_product_id`，BOM 写死 `quantity: 1` | 设备检查支持多台并机（属 #548 未完成范围，非本轮可修） |
| 真实询盘与 Genie 提交 | 保护**正常工作**，自动化客户端不给 token 时被拒 | 见下方「Turnstile 的准确状态」 |

## 已合并的修复

| PR | 内容 |
| --- | --- |
| #794 | 引擎拒因码在网关原样透传；文档哈希请求内复用；计划重冻 |
| #795 | 主线计划重冻（原计划 `preview` 直接拒绝） |
| #796 | `refresh` 命令，重 pin 不再靠手改 |

拒因码透传已验证在生产生效：错误码从 `linker_planner_upstream` 变为
`linker_planner_not_found`。哈希复用实测同请求第二次 `manifest()`
从 4.8 s 降到 0.67 s，内容一致。

## 方法注记

`ProductEvidenceChanged` 的 12 个 raise 点共用一个错误码，引擎又丢弃 message。
本轮据此连续做出 6 个错误推断（主机负载 → manifest 重建 → 旧 manifest →
LiteSpeed 缓存 → 兼容合同 → 平台夹具）。正确顺序是**先复现、再读代码**。

另需注意：`sources/saved-solution` 是**网关层路径**（`Gateway.php:302`），
经 `Transport` 直连引擎会得到 `not_found`，看起来像功能坏了，实际不是。

## Turnstile 的准确状态（更正早前的描述）

早前记录写作「Turnstile 拦截询盘」，这个说法**不准确**。实测后的事实：

| 项 | 实测值 |
| --- | --- |
| `Configuration::active_mode()` | `enforce` |
| `ready()` / `configured()` | `true` / `true` |
| `test_keys` | `false`（真实密钥，非测试密钥） |
| `/proforma-request/` 页面 | `200`，**页面内没有 Turnstile 脚本** |
| 验证发生的位置 | 提交时，服务端调 `Protection/Turnstile.php` 的 siteverify |

也就是说：

- **页面不被拦截**。询盘页正常渲染。
- **保护在提交时生效**，且配置正确、使用真实密钥。
- 我的自动化验收拿不到有效客户端 token，因此**提交被正确拒绝**。

这属于「保护按设计工作，自动化客户端不被允许」，不是功能缺陷，也不是「外部条件导致功能未完成」。

真实询盘与 Genie 提交需要**人工在浏览器中完成**——这正是该保护的用途。用自动化绕过它去换取验收通过，是错误的做法，本线没有这样做。

### 一处自我更正

排查过程中我 grep 到两个 `pow`，一度认为存在 proof-of-work 机制。实际是
`/product-category/accessories/backup-power/` 里的子串，属误匹配，已推翻。

### 完整机制（从 `protection.js` 与生产页面读出）

我早先 grep「`/proforma-request/` 页面里没有 Turnstile 脚本」，这句本身没错，
但据此得出的「被拦截」结论是错的。真实设计是**交互触发、异步加载**：

1. 页面加载时**不**注入 `challenges.cloudflare.com/turnstile/v0/api.js`；
2. 用户第一次 `focusin` 或 `pointerdown` 表单时，`warm()` 才异步加载脚本并渲染 widget；
3. 提交时走两步：服务端 `POST /wp-json/linker/v1/protection/prepare` 换取 sitekey，
   客户端取得 token，再 `POST …/verify` 换取有时效的 proof；
4. `linker_proof` 隐藏字段由此填充，服务端再调 Cloudflare siteverify。

生产实测确认这套链路已注入：

```
linkerPublicProtectionConfig = {
  "api": "https://de-linker.com/wp-json/linker/v1/protection",
  "nonce": "754057849d",
  "mode": "enforce",
  "businessVerification": "required",
  "language": "en"
}
```

`protection.js` 在页面中出现 3 次（不同区块各挂一次）。

因此：**自动化客户端不触发交互、拿不到 token，提交被正确拒绝。**
这不是缺陷，也不需要「修复」。人工在浏览器中打开询盘页、聚焦表单，widget 会正常出现。
