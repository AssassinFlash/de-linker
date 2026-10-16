# #176 验收记录（2026-10-15/16）

## 验收三件套

### 1. Spec + Standards 双评审（merge-base 08997063 → 返工后 da1d2491）

独立评审子代理首轮结论：Standards 3 项硬违规（351MB PDF 缓存未被 gitignore、thumbs.py 无测试、两个新类无测试）+ 真 bug（aria-pressed 写满所有行）+ 6 判断项；Spec 3 项 FAIL（无缩略图行图标块落点偏离原型、文案评审记录不实、e2e 缺 spec）+ 7 PASS。
返工逐项落地（详见 PR #186 与 spec §9）：全部 FAIL 修复、11 条 thumbs.py 测试 + 两个读者类测试 + faq-download.spec.ts 10 条 e2e（顺手抓到并修复"搜索中切 tab 不刷新列表"的真回归）、文案记录改实（含 Vor der Bestellung 变更登记）。

### 2. 夹具测试

PHPUnit 1045/5109 绿、JS 38/38、tools/faq pytest 20、e2e faq-download 10/10、CI pass。

### 3. Computer Use 视觉验收（基准=原型变体 5，分支 prototype/faq-download-redesign）

- 首轮对照（shots 见本目录）：tab 框架/目录/毛玻璃卡片/品牌锁up/搜索建议下拉分组+分流计数/点外部关闭（业主此前投诉的坑已验证修复）/20 条分页全部对齐原型。
- 缩略图：147/159 真实 PDF 首页渲染进左槽（984KB webp 入插件资源，构建期生成），12 份超大手册回退类型图标块；S1 返修后实测两类行同槽同高（101-102px）。
- 返工后复核：impl2-* 对照（本目录）。

**数据缺口（记录不修）**：德语文档类型字段几乎全为 document（类型芯片在 DE 无区分度）——spec §8 记录在案。
（2026-10-16 追记：该归因已被复核推翻并修复——数据本不缺，是目录的类型解析缺德语别名表；DE 与 EN 修复后同分布。详见 `docs/specs/176-faq-download.md` §8 与当日修复 PR。）

**变更台账条目**：FAQ+Download 页重设计 · 业主裁定 2026-10-15（dashboard 式组织 + 变体 5 框架）· 缩略图构建期入插件资源。

## 结论

通过。合并 PR #186。
