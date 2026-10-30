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
| 报告 BOM（英文，仅引擎层） | 同一模型产出，未逐行读回英文报告 | 同上 |
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
| Turnstile 后的真实询盘与 Genie | 生产验证拦截 | 外部条件；未尝试绕过 |

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
