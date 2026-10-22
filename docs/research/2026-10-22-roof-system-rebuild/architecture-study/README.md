# 架构研究：依据与运行实验

本目录用于检验[新架构](../ARCHITECTURE.md)的技术取舍。研究程序不引入生产代码，不是可部署的项目服务；它没有替代真实工程、用户或运维验收。

## 一、已执行的生命周期实验

运行：

```sh
python3 docs/research/2026-10-22-roof-system-rebuild/architecture-study/lifecycle_reference.py
```

[程序](lifecycle_reference.py)以临时SQLite WAL库和两个实际连接验证6组场景，结束删除临时库。固定观察在[lifecycle-results.json](lifecycle-results.json)：重复提交；计算期间编辑与旧标签页冲突；过期worker重新领取及迟到发布；任务成功但工程缺证据；取消后迟到完成；两个连接并发领取。实验使用本机SQLite 3.54.1，没有调用现有引擎、外部API、生产库或真实用户资料。

结论限于所试状态合同可在该研究模型实现。尚未实现/验证权限、跨项目隔离、真实物理计算、产物/数据库一致恢复、断电、持续吞吐与外部交接，不把研究程序当作生产骨架直接移植。

## 二、只读基础设施样本

[runtime-resources.json](raw/runtime-resources.json)保存2026-10-22的现有服务主机观测：1CPU、约4GB内存，Python 3.12.3，Python SQLite库3.45.1。读取CPU/内存、二进制可用性和有限systemd状态；未安装、写测试库或做负载实验。没有SQLite命令行不意味着Python缺SQLite。

此样本支持先减少独立运行设施的设计选择，不能推出全年15分钟、多候选或复杂3D场景的资源保证。生产库版本与本机实验版本不同，部署前还需要同版本合同及故障测试。

## 三、官方文档依据

全部外部读取通过Apify，run `I4j9WdgWaxh2XCy1f` / dataset `xehL64heb1pvhM7hO`；5项HTTP 200，最终SUCCEEDED。完整请求、启动/最终状态与响应保存在`raw/`；[source-index.json](raw/source-index.json)记录URL、时间、状态和hash。

| 官方材料 | 支持的设计事实及限制 |
| --- | --- |
| [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | 小任务与重计算执行场景需分别考虑；本文的持久任务、租约及发布合同由本项目设计和实验验证，不能说该文档已经替我们保证持久性 |
| [SQLite何时适用](https://www.sqlite.org/whentouse.html) / [WAL](https://www.sqlite.org/wal.html) | 同机应用服务可采用、单写者及同机共享内存要求；需短写事务和适当备份，不支持无限并发或网络文件系统部署的结论 |
| [PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.html) | 官方存在锁定扩展；本次正文提取未完整取得详细锁定段，不据此声称已核完队列锁行为，也未运行Postgres |
| [React reducer](https://react.dev/learn/extracting-state-logic-into-a-reducer) | 集中表达状态动作；不能替代项目保存、服务权威、可访问性和真实浏览器验收 |

三种架构方案的独立挑战在[架构对照](https://github.com/AssassinFlash/de-linker/blob/4e43a3332e9a15024ae3a58658d437a58c48dc59/docs/research/2026-10-22-roof-experience/hardware-study/architecture-challenge.md)。数值方法和工程证据由主架构分别链接，没有用技术框架文档证明工程精度。
