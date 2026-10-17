# 异步翻译期间保存的真实并发回归

## 红

固定提交 b968d83a，真实 i253 + Redis + Action Scheduler + loopback 假 DeepSeek：

1. 非层级属性 pa_phase 在模型调用期间由第二个 PHP 进程保存。旧任务记录 synced，德语仍是旧描述，没有后继任务。父进程持旧 WP_Term；Redis 被另一进程删除不清父进程运行时缓存。
2. 页面在本插件翻译回调返回后、Action Scheduler 标完成前保存。AS unique 把当前 in-progress 当重复，后继任务数量为 0。

加入真实回归后，在 b968d83a 上重跑：2 tests，2 failures，均为预期后继 1、实际 0。测试进程会在结束后删除语言对和测试任务。

## 绿

- 正常保存只对 pending 同参数任务去重，允许 in-progress 后有一个待运行后继；最终检查补排也使用同一入口。
- 最终指纹比较前清源对象缓存，读回最新英文。词项显式传 taxonomy 给 clean_term_cache；WordPress 不带 taxonomy 时把数字当 term_taxonomy_id，不能用于这里的 term_id。
- 两条原样回归：2 tests / 27 assertions，通过；非层级属性最终为最新描述且 synced，晚保存页面也正确追平。

这些修复来自可复现失败，没有增加重试次数或时间阈值，没有刷新全站缓存。
