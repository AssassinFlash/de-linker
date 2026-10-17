# 验证记录

PHP 8.3，独立 worktree `de-linker-253`，实例 `i253`。未对生产写入，也未实发测试邮件。

## 改动层真实夹具

本地 WordPress + WooCommerce + Polylang + Redis + Action Scheduler，循环地址的假 DeepSeek 服务；凭据测试使用假 key，夹具禁止回退到本机私有配置。

```sh
LINKER_I18N_SITE=http://127.0.0.1:9075 \
LINKER_I18N_WP=/tmp/i253-wp \
LINKER_I18N_STUB=http://127.0.0.1:9175/ \
/opt/homebrew/opt/php@8.3/bin/php plugins/linker-i18n/vendor/bin/phpunit \
  -c plugins/linker-i18n/phpunit.xml.dist --testsuite integration \
  --filter 'TranslateOnSaveTest|TermTranslationTest|TemplateSafetyTest|AutomaticContentTest'
```

`/tmp/i253-wp` 只把参数转给本 worktree 的 `linker-local wp i253`；假服务脚本是 `tests/php/Integration/stub/deepseek.php`。

结果：**17 tests / 252 assertions 通过**。其中模板安全 **4 / 39**；两条并发回归 **2 / 27**，见 [红绿证据](race-regression.md)。

本机私有配置文件读取与真实官方模型调用另在独立 CLI 进程完成一次，见 [结果](official-api.json)。该请求是本地私有测试产品，夹具已清除。

## 全仓测试

`just check` 退出码 0：PHP/WPCS/PHPStan、JS、Python、禁词、翻译覆盖/有效性与构建一致性检查均通过。

全量 `just test` 已通过。i18n 单元 **162 tests / 348 assertions**；pull **104 passed**；cutover **78 passed**。仓库原有的环境相关跳过仍保留，未为本票增加跳过。

首跑因其他会话同时使用快照测试固定数据库名，出现连接断开和缺表。重跑使用一次性 pytest 插件，只改两项夹具名称：

```python
def pytest_collection_modifyitems(items):
    for item in items:
        module = item.module
        if str(getattr(module, "__file__", "")).endswith("/tools/pull/tests/test_load.py"):
            module.SOURCE_DB = "linker_i253_pytest_source"
            module.NAME = "i253_pullpytest"
```

```sh
PYTHONPATH=/tmp/i253-test-support \
PYTEST_ADDOPTS='-p i253_fixture_isolation' just test
```

插件仅存在 `/tmp/i253-test-support/i253_fixture_isolation.py`，未改仓库工具、断言或测试集合。重跑退出码 0。

## 待完成的验收

- 正式 EN/DE × 1440/390 截图：等待「本地与线上同步」合并后按正式管线刷新 i253。
- 每日摘要消费者：「内部通知改投 sunriver，恢复每日摘要」尚未合并；已按约定提供并留言只读接口，由该票接入。
- 生产模板遗留任务、6 页面补译、全量扫漏、网页保存实测及 cutover verify：等评审、合并和业主单独批准上线与密钥写入。
