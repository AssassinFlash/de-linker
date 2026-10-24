# TableItem 整组拒绝的组合回归

本记录补充 `ab5c609c` 的共享资料适用性修复。Spec 复审在实际 BAT-C Docling
夹具上发现：同一 TableItem 的后段使 `_table_columns` 提前 `continue` 时，函数没有
把该组写入 `conflicts`。首块若含完整、当前的型号轴，`scope_proofs` 仍能经
`matched → passage` 路径授权。缺少列继承与明确整组拒绝被混成了同一个结果。

固定夹具为原件 SHA
`027415a66a00234f03d1268e180129fa016e601aaf1ecb7cda643a24aecb7d38`，p.2
`#/tables/0`。仅在内存中作以下组合，不改缓存、原件或 Woo：

1. 在开头加入完整反序 `Model | GW261.2-BAT-LCD-G10 | GW208.9-BAT-LC-G10`，
   最后加入 `Model | Z999 |`，保留全部原生行号。错误获权首块为
   `027415a66a00-p2-6e03c2ca`，basis 为 `passage`。
2. 开头加入完整正常型号轴，随后移除该组所有片段的行来源。错误获权首块为
   `027415a66a00-p2-21ad33cf`，同样为 `passage`。

先分别建立 scope 与实际 FTS5 SQLite 检索回归，四项均红，0.93 秒。继续验证同类
硬失败出口，确认正常显式型号首块叠加后段缺列、未知前置型号轴、同表某片缺前置
来源、非空但重复的原生行号，也存在相同漏放。六种组合共十二项回归均先红，
1.32 秒。未知行放在最后，确保不会因与首块型号轴挤在同一块而掩盖漏洞。

修复沿用现有 `columns, conflicts` 接口，不新增授权渠道：

- 按原生 `source_table` 收齐 TableItem 的全部片段，不能先排除缺少 `preceding_text`
  的片段，再只验证剩余组。
- 不一致的前置来源、非 Pack 未知行、Pack 例外所需原生行来源缺失/无效、明确
  未知或已撤的列轴、已证明多列轴下的缺列，均记为完整组 `conflicts`。
- Pack 例外要求每片原生行号非空、非负、严格递增，且数量与原文行对应。未知
  Pack 行本身继续拒绝；它不能掩盖另一条系统型号轴冲突。
- 仅缺少多列继承证据、且没有上述负面证据时，仍按原有直接适用性规则判断。
  正常单型号原文不会因为不需要多列继承而被新规则一概封禁。

已有局部型号轴反序、不同当前型号、部分轴与未知型号的整组拒绝保持。实际 BAT-C
当前系统 180/180 A 正例、未知 Pack 行拒绝、CHS2 原文外设角色正反例，以及 HCA
原始列顺序正例仍在同轮检查。focused `roles + columns + publication` 为
**120 passed，17.58 秒**。最终 Genie 全量为 **2,182 passed、1 skipped、195 deselected、
6 xfailed，67.31 秒**；完整 `mypy .` 194 files、Ruff 全树检查与格式检查 199 files 均绿。

本次仅修改原 Genie 工作树中的 scope 算法、组合回归与本文。未改 facade、模型
通道、Woo、原 PDF、解析缓存、共享 SQLite 或已加载索引；未运行 worker、OCR 或
embedding。主线需以正常 worker 产生并核对新的实际 scope / loaded / ack，不能
把修复源码或临时夹具当作已经生效的发布版本。
