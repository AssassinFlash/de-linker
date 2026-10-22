# 新选型架构的数据准备度研究

2026-10-22。问题：新架构需要的实际设备能力是否已经进入可计算的数据链？研究对象是当天线上快照建立的隔离实例r549，不是宣称已读回生产Python进程的内存状态。只读取产品工程数据和在研究工作树中计算，没有改商品、feed或业务实现。

## 方法与输入

1. 保存实际服务使用的feed文件为[source-feed.json](source-feed.json)，生成于2026-10-22 17:19:41（Asia/Shanghai），SHA256 `010337f4591403d2b7d4153798bb140163f29be0bd06257e47e59618c49767a5`。
2. 用[capture-meta.php](capture-meta.php)只读导出相同106件商品在Woo中的原始图值，保存为[source-meta.json](source-meta.json)。全部是英文事实源；实例212件已发布商品包含语言配对，不能将106与212的差直接认定为漏商品。
3. 从当前匿名只读工程接口重新读取，排除生成时间后的内容hash与已加载文件相同，见[fresh-feed-readback.json](fresh-feed-readback.json)。因此下列字段差异不能归因于本轮缓存未刷新。
4. [analyze.py](analyze.py)比较源图值、实际feed和现有测试夹具；结果在[coverage.json](coverage.json)。统计是数据存在性研究，不是证明所有图值正确、同义或适用于所有设备。

## 实际结果

| 范围 | 商品数 | Woo源图值条目 | 实际feed图值条目 |
| --- | ---: | ---: | ---: |
| 全部英文事实源 | 106 | 2,482 | 610 |
| 逆变器 | 59 | 1,702 | 475 |
| 家用储能 | 16 | 254 | 69 |
| 电池系统 | 9 | 195 | 19 |
| 一体系统 | 5 | 160 | 32 |

不在feed的1,872条里，1,137条只有文档名引用，518条只有证据引用串，217条没有此类引用。总数包含展示字段，**不能解释为“缺失了75%的必要计算参数”**。有些字段通过别名归一化存在，例如MPPT电流；逐键比较时已保留这种区别。

真正影响选型的缺口很明确：

- 59件逆变器中，Woo有40件带`backup_power_kw`、另6件带`backup_power_va`，运行feed均没有这两个字段。16件有电池最大充电功率、9件有最大放电功率，运行feed也均没有这些键。
- 电池系统中，充放电功率、电流和往返效率原始值存在于若干商品，但运行feed没有相应值；具体型号的准确含义仍由原始手册核实。
- `GW125/261-ESA-LCN-G10`和`L260-OMNI`的运行图值为空；它们仍有部分顶层功率/能量事实，**空图值不等于完全没有任何参数，也不证明产品本身不可用**。
- 4条带运行条件的源图值没有进入运行结果。例如GW61.4的顶层可用量仍是60kWh，原始值附带的温度、倍率、寿命阶段条件却没有随顶层标量交接。

## 为什么测试数据比运行数据完整

关键对照：

| 型号 | 测试夹具图值数 | 实际feed图值数 | 本轮发现的关键差异 |
| --- | ---: | ---: | --- |
| GW5K-ETA-G20 | 25 | 10 | 备电输出、效率等不在实际feed |
| GW80K-ET-G10 | 31 | 10 | 电池侧功率、视在功率等不在实际feed |
| GW61.4-BAT-AC-G10 | 27 | 5 | 充放电功率/电流/效率不在实际feed |
| GW125/261-ESA-LCN-G10 | 15 | 0 | 全部夹具图值都未进入实际feed |

当前[`EngineeringFeed::figures()`](https://github.com/AssassinFlash/de-linker/blob/123aea571e80b5b1ba756816914ba86408866ba5/plugins/linker-commerce/includes/Products/EngineeringFeed.php#L132)要求明确托管URL，文档名或证据串不会自动解析成URL；输出只带value、unit、citation。源数据里关键功率字段仍是文档名形式，少数迁移后的字段是URL形式。当前[`build_fixtures.py`](https://github.com/AssassinFlash/de-linker/blob/123aea571e80b5b1ba756816914ba86408866ba5/services/engine/scripts/build_fixtures.py)则用额外的只读证据映射解析文档名，产生更完整的测试输入。

这是两条数据生产路径的实质差异。引用校验拒绝没有可追溯URL的值本身合理；直接取消这一条件会降低证据质量。重建时应统一事实来源与编译/验证管线，并把条件一起结构化；不沿用“测试有字段就代表运行有字段”的假设，也不将现有19键范围当成新系统需求。

## 在真实feed上再跑选型

使用本轮当前代码直接加载保存的实际feed及其内嵌兼容合同，不调用天气服务，复跑程序为[runtime_probe.py](runtime_probe.py)，使用现有引擎虚拟环境执行，结果在[runtime-feed-design-probes.json](runtime-feed-design-probes.json)：

- 75kW/60kWh仍首推GW80K + GW61.4，并给80kW系统功率。
- 100kW/600kWh仍给3个GW125/261柜、375kW/783.8kWh。

这将原先基于测试夹具的程序反例，推进到了相同快照的实际数据输入；仍不声称线上用户已触发。硬件原表研究进一步确认前一组合的电池功率限制和模式边界，后一组合的并联条件随控制器、拓扑和模式变化，详见[原件研究](https://github.com/AssassinFlash/de-linker/blob/74aa66b921dfad70af92fe909663dfcf62978f92/docs/research/2026-10-22-roof-experience/hardware-study/README.md)。

## 新架构需要的合同

1. **产品身份和手工事实仍以Woo为权威。** 新规划应用存储发布后的派生能力快照，不建另一份可独立手工维护的产品表；型号、SKU及语言映射随同一事实源生成。
2. **工程事实必须有语义。** 名义/可用能量、连续/最大/限时峰值功率，AC/DC与具体端口、串栈/柜单位、SOC/温度/寿命条件分别表达。原始PDF、内容hash、物理页、型号适用与条件可追溯。
3. **能力是带条件的配置。** 并网、离网、旁路、备电切换，以及拓扑、控制器/固件和附件共同决定可用配置，不是一个`released`枚举。
4. **事实编译只做一次。** 实际运行、独立参考计算与验收夹具都从同一发布快照建立；故障注入另行明确标记。结构通过、来源可达、语义核实及模型适用是不同验证阶段。
5. **条件和缺项进入输出。** 无证据的关键能力不能悄悄变成0或标为通过。已成立的局部成果保留，相关任务则需要补证或返回不可行。

这些是对新领域模型和数据管线的要求。本研究没有给现有feed做字段补丁，没有将原始图值不经核实直接补进选型。

## 复跑

从本研究工作树根目录执行，既有引擎虚拟环境提供依赖；程序只读保存的源数据，重写本目录研究结果：

```sh
python3 docs/research/2026-10-22-roof-system-rebuild/data-readiness/analyze.py
/Users/chesterjohn/Documents/de-linker/services/engine/.venv/bin/python docs/research/2026-10-22-roof-system-rebuild/data-readiness/runtime_probe.py
```

新环境需按引擎锁文件建立依赖。`runtime_probe.py --engine-src`可指定相同记录基线的代码位置；代码版本不同不应覆盖并冒充本次运行记录。
