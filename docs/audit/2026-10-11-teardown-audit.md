# 全拆审计：新仓库旧代码存活检查（2026-10-11）

审计对象：新仓库 main（代理审 `d3b1052`，独立复现在 `2eb8da4`，工作树干净）vs 旧仓库链尖 `refs/landed/chain-tip`（`f007a9dd`，经 `git archive` 导出至 `/tmp/audit-old`，只读）。
背景裁定：业主 2026-10-11 全面否定旧项目，一行旧代码都不许作为代码存活；白名单只有内容/数据/裁定记录/证据文档/经验证的规格结论（AGENTS.md §5，PR #63）。

## 总判定

**有且仅有 1 个文件存在旧代码形式存活——`plugins/linker-commerce/assets/storefront.css`（已知项，删除已排入 #16）；其余全部干净。**

| 旧资产 | 新宿主中的最长连续归一化行（独立复现） | 代理原报 |
|---|---|---|
| 旧 `terravolt-b2b-core/assets/storefront.css` PDP 块 | **404 行**（old[989:1393] → new[231:635]） | 401 行 |
| 旧 `terravolt-b2b-core/assets/catalogue.css` 目录块 | **206 行**（old[8:214] → new[22:228]，96%） | 203/212 行 |
| 新文件整体 | **96.9%** 的归一化行存在于旧两资产（1279/1320） | 84.5% |

两段抄录宿主同一个新文件；删除路径 = #16 的 Storefront 接管移除（AGENTS.md 已把"PHP_INT_MAX 模板抢占/四通道 CSS"登记为待清偿债务）。**#16 落地后必须重跑本文附录脚本**，确认该两行回落到平凡量级。

除该文件外：旧四大代码体（b2b-core 96 PHP + 32 资产、ai-assistant 19 PHP + 15 资产含 3 个 esbuild bundle、i18n 18 PHP、design-engine 22 Python）与旧 snippets、旧 tools/scripts（222 Python）对新语料的最长连续归一化片段 **≤7 行**，且全是闭合括号序列或 stdlib 导入块，无一达到 30 行抄录阈值。

## A. 旧标识符全文扫描

在新仓库代码面（工作树遍历，排除 vendor/node_modules/build/docs/.venv/.scratch；共 512 文件 65,849 归一行）grep：

| 模式 | 命中 | 性质 |
|---|---|---|
| `tv_b2b_` | 250 行/19 文件 | 数据引用。生产 PHP 仅 4 处，全是 meta key 常量：`includes/Catalog/SelectionFacts.php:24`（`FIGURES_META_KEY='_tv_b2b_figures'`）、`includes/Gating/CommerceState.php:26`（`MODE_META='tv_b2b_product_mode'`）、`includes/Storefront/ProductView.php:355`、`FiguresMetaBox.php:16` 注释。其余在 tests/fixtures（live 快照数据）与 `tools/migrate/`、`tools/pull/`。无一处旧函数定义或调用 |
| `tv_woo_b2b_` | 0 | 干净（DOM id `tv-woo-b2b-catalog` 见 C 节） |
| `Linker_AI_` | 0 | 干净 |
| `Linker_I18n_` | 1 | 数据。`tools/pull/src/linker_pull/load.py:334` 对 live 站探测 `class_exists('Linker_I18n_Router')`——live 仍在跑旧 i18n，属拉取工具的环境探测 |
| `terravolt` | 25 行/13 文件 | 数据。`~/.config/terravolt-builder/*.env` 本机凭据路径、pull 工具的 live 插件路径、`TokensTest.php:32` 的反向护栏（断言 CSS 不含 `terravolt-b2b-core`） |
| `dlk-` / `dlk_` | 9/11 | 数据。SKU 前缀、CSS 变量 `--dlk-radius`、pull 工具的 live DB option 名 |

旧特有函数名 8 个全部 **0 命中**：`resolve_class`、`family_evidence`、`families_in_sales_range`、`tv_b2b_product_commerce_state`、`build_linker_ai_knowledge`、`extract_design_inputs`、`model_task_proposals`、`without_reference_classes`。
JS/Python 键：`design-canvas.bundle`、`lit-html`、`linker_engine.design`、`valid_until: 2027-01-31` 全 0（旧 tariffs.yaml 未携带，新引擎无此文件）。`quote-configurator` 11 行 = URL 重定向映射（`Redirects.php:37`）+ 迁移脚本，属数据。

## B. 结构性抄录检测（独立复现数字）

方法：行归一化（按扩展名去注释、压缩空白、小写、去空行）→ 旧文件序列对新语料求最长连续相同行（后缀自动机；文件间哨兵隔断，串不跨文件）。阈值 ≥30 行 = 抄录。完整比对器见附录。

**B1 配置器引擎（新 `services/engine/src/` vs 旧 `services/design-engine/linker_engine/`）——干净**
最长 5 行（`components.py` 的 stdlib 导入块）。物理链换架构：旧引擎自实现 Perez/Martin-Ruiz/Faiman/Huld，新引擎经 `pvlib` 调 `get_pvgis_hourly`（`pvgis.py:69`）；旧 `design.py` 的 `_knee_point`/`quick_design`/`_pick_battery` 在新引擎 0 命中（与 #14 评审"HTW 三规则硬上限、无 knee"一致）。HTW 数据表旧仓库不存在，是新取的公共表。

**B2 i18n 翻译器（新 `plugins/linker-i18n/includes/Translation/` vs 旧 `translator.php` 926 行）——干净**
最长 7 行（闭合括号 + 导入样板）。词表：旧 `glossary-de.json` 65 条 vs 新 4 条，0 对同键同值——连数据都没搬。新 i18n 未定义任何 `Linker_I18n_*` 旧类。

**B3 账号/商务链（新 `plugins/linker-commerce/includes/` vs 旧 terravolt-b2b-core）——PHP 干净，CSS 违规**
旧 96 个 PHP（含 1,689 行 `admin-operations.php`、1,947 行 `reference-and-display.php`、2,405 行 `project-portal.php` 运营台）对新语料最长 6 行；旧 4,000 行运营台无任何转世。唯一违规即总判定表的两段 CSS（宿主 `storefront.css`）。佐证重写侧：新 `templates/storefront-single-product.php`（246 行）vs 旧 `product-page-storefront.php`（1,121 行）最长 5 行；新 `storefront.js`（63 行）最长 2 行——模板与 JS 是带着旧 DOM id 的重写，CSS 是搬字节。

**B4 Genie（新 `plugins/linker-tools` + `services/genie` vs 旧 linker-ai-assistant）——干净**
旧 19 PHP（含 8,783 归一化行 validator、4,635 行 resolver、3,940 行 planner、3,057 行 products）最长 6 行。旧 15 个 JS/CSS 资产（含 6,610 行 assistant bundle、6,418 行 configurator bundle、3,725 行 design-canvas bundle）最长 4 行；NLU 正则链无行级残留。旧数据文件（components-db.json/knowledge-index.json/spec-labels.json/tool-frame-copy.json）与 vendor 库（maplibre/terra-draw）未进入新仓库。

**补充**：旧 `snippets/live`+`snippets/retired` 全部 10 文件 ≤5 行；旧 `tools/`+`scripts/` 222 Python ≤7 行。

## C. 携带物合法性清单

| 携带物 | 位置 | 判定 |
|---|---|---|
| live 数据快照（产品/目录/SQL dump、`dlk_*` option 名） | `tests/fixtures/`、`tools/pull/` | 白名单：数据 |
| 旧 meta key 名 `_tv_b2b_figures`/`tv_b2b_product_mode`（新代码读 live DB 既有数据位置） | `SelectionFacts.php` 等、`tools/migrate/7-facts.py` | 白名单：数据（key 即数据所在） |
| URL 重定向映射（`/quote-configurator/`→`/linker-planner/` 等） | `linker-tools/includes/Redirects.php`、`tools/migrate/12-site-chrome.py` | 白名单：内容/SEO 数据 |
| `docs/{specs,research,acceptance,faq}`、`docs/old-repo-tickets.md` | docs/ | 白名单：裁定、证据、规格、内容（FAQ 为 #15 逐产品独立重撰） |
| 字体 Plus Jakarta Sans 500/700 字节相同（另新增 400/600、DM Serif） | `linker-commerce/assets/fonts/` | 白名单：第三方 OFL 资产 |
| `content/tokens.css`（纯设计 token 值表，无选择器行为） | `linker-commerce/content/tokens.css` | 可辩护的规格携带（2026-10-10 业主裁定明令移植设计层）；备案不判违规 |
| 旧 DOM id/类名词汇表：`tv-woo-b2b-catalog`、`tv-storefront-pdp`、`pdp-*`/`sf-*`/`wb-*`、`--dlk-radius` | 新模板与 tokens.css | 标识符复用（非代码行），服务于"复刻线上现有设计"裁定；随 #16 呈现层正规化自然消解 |
| 命名延续：包名 `linker_engine`、插件 slug `linker-i18n` | services/engine、plugins | 标识符备案；"代码一行不留"针对代码行 |
| `~/.config/terravolt-builder/*.env` 路径 | 若干工具 | 本机环境路径，非旧仓库代码 |

**白名单外的携带物（违规）**：仅 `plugins/linker-commerce/assets/storefront.css` 两段（见总判定）。

## D. 分区判定

- configurator（引擎）：**干净**——物理链换架构（自实现→pvlib）。
- genie：**干净**——validator/resolver/planner 与三个 bundle 均无行级存活，数据文件未携带。
- 账号/商务链：**PHP 干净**（旧运营台无转世）；**站点外壳违规**——`storefront.css` 唯一存活点，#16 修复注入中；#16 落地后重跑附录脚本验证。
- i18n：**干净**——翻译器重写，词表未同值携带。
- 站点外壳其余（模板/JS/tokens/重定向）：重写或白名单携带。

## 方法局限

1. 行级只检"逐行连续存活"；跨语言改写（旧 PHP NLU 正则改写为 Python/TS）不命中——属重写而非"以代码形式留下"，逻辑同构需人工判定。
2. 行内标识符改名会打断匹配：实际携带量可能被低估；但已命中的 404/206 行是字节级实锤，不会误报。
3. docs/、vendor/、build/ 按裁定排除（docs 中作为证据出现的旧代码摘录属白名单）。
4. 旧树仅审链尖 `f007a9dd`；旧仓库其他分支未比对（新仓库携带物无一路径指向它们）。
5. 30 行阈值针对连续行；<30 行多段拼接式搬运理论上可躲过，但结合 A 类标识符全零与各文件最长片段分布（≤7 行全是样板），无证据支持。
6. 两轮数字差异说明：代理原报（401/203/84.5%，语料 249,608 行含更广目录）与本复现（404/206/96.9%，语料 65,849 行纯代码面）来自两个独立实现的归一化器；方向与量级一致，违规判定不受影响；以附录脚本数字为基准。

## 复现

```bash
# 旧树导出
git -C ~/Documents/de-linker-project archive refs/landed/chain-tip | tar -x -C /tmp/audit-old
# 比对器（附录全文 = /tmp 脚本；须从新仓库根运行，语料走工作树遍历）
cd ~/Documents/de-linker && python3 <附录脚本>
# A 区标识符（示例，其余模式同）
git grep -n -F 'tv_b2b_' -- ':!vendor' ':!docs'
```

## 附录：比对器全文

```python
#!/usr/bin/env python3
"""Teardown-audit re-verification: longest contiguous normalized-line run of each
old-repo source file against the new-repo corpus (and pairwise CSS checks).

Reproduction of docs/audit/2026-10-11-teardown-audit.md numbers.
Old tree export: git -C ~/Documents/de-linker-project archive refs/landed/chain-tip | tar -x -C /tmp/audit-old
"""
import difflib
import sys
from pathlib import Path

OLD = Path("/tmp/audit-old")
NEW = Path(".")

# ---------- normalization ----------
def _strip_js_comments(text: str) -> str:
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j])
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)

def _strip_hash_comments(text: str) -> str:
    return "\n".join(l.split("#", 1)[0] for l in text.split("\n"))

def norm_lines(path: Path) -> list[str]:
    if path.suffix in (".php", ".js", ".css", ".scss", ".mjs", ".json"):
        text = _strip_js_comments(path.read_text(errors="replace"))
    elif path.suffix == ".py":
        text = _strip_hash_comments(path.read_text(errors="replace"))
    else:
        text = path.read_text(errors="replace")
    lines = []
    for raw in text.split("\n"):
        s = " ".join(raw.split()).lower()
        if s:
            lines.append(s)
    return lines

# ---------- suffix automaton ----------
class SAM:
    __slots__ = ("nexts", "link", "len_")

    def __init__(self, seq):
        self.nexts = [{}]
        self.link = [-1]
        self.len_ = [0]
        last = 0
        for ch in seq:
            cur = len(self.nexts)
            self.nexts.append({})
            self.link.append(-1)
            self.len_.append(self.len_[last] + 1)
            p = last
            while p != -1 and ch not in self.nexts[p]:
                self.nexts[p][ch] = cur
                p = self.link[p]
            if p == -1:
                self.link[cur] = 0
            else:
                q = self.nexts[p][ch]
                if self.len_[p] + 1 == self.len_[q]:
                    self.link[cur] = q
                else:
                    clone = len(self.nexts)
                    self.nexts.append(dict(self.nexts[q]))
                    self.link.append(self.link[q])
                    self.len_.append(self.len_[p] + 1)
                    while p != -1 and self.nexts[p].get(ch) == q:
                        self.nexts[p][ch] = clone
                        p = self.link[p]
                    self.link[q] = clone
                    self.link[cur] = clone
            last = cur

def longest_run(sam, seq):
    v = l = best = 0
    for ch in seq:
        if ch in sam.nexts[v]:
            v = sam.nexts[v][ch]
            l += 1
        else:
            while v != -1 and ch not in sam.nexts[v]:
                v = sam.link[v]
            if v == -1:
                v, l = 0, 0
            else:
                l = sam.len_[v] + 1
                v = sam.nexts[v][ch]
        best = max(best, l)
    return best

# ---------- corpus ----------
def corpus_files():
    skip_dirs = {"vendor", "node_modules", "build", "docs", ".venv", ".git",
                 ".zcode", ".scratch", "dist", "out"}
    exts = (".php", ".js", ".css", ".scss", ".mjs", ".py")
    stack = [NEW]
    while stack:
        d = stack.pop()
        for p in sorted(d.iterdir()):
            if p.is_dir():
                if p.name not in skip_dirs:
                    stack.append(p)
            elif p.suffix in exts:
                yield p

def old_files():
    roots = [
        OLD / "plugins/terravolt-b2b-core", OLD / "plugins/linker-ai-assistant",
        OLD / "plugins/linker-i18n", OLD / "services/design-engine",
        OLD / "snippets", OLD / "tools", OLD / "scripts",
    ]
    exts = (".php", ".js", ".css", ".scss", ".mjs", ".py")
    for root in roots:
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix in exts and "node_modules" not in p.parts and "vendor" not in p.parts:
                yield p

def main():
    # --- self-test ---
    t = SAM("abcabcd")
    assert longest_run(t, "abc") == 3 and longest_run(t, "cd") == 2 and longest_run(t, "z") == 0
    assert longest_run(SAM("abXcd"), "bc") == 1  # boundary blocks crossing

    ids: dict[str, int] = {}
    def tid(line):
        if line not in ids:
            ids[line] = len(ids)
        return ids[line]

    corpus_seq = []
    for p in corpus_files():
        corpus_seq.append(-len(corpus_seq) - 1)  # sentinel: runs cannot cross files
        corpus_seq.extend(tid(l) for l in norm_lines(p))
    sam = SAM(corpus_seq)
    print(f"corpus files: {sum(1 for _ in corpus_files())}, corpus lines: {len(corpus_seq)}")

    report = []
    for p in old_files():
        r = longest_run(sam, [tid(l) for l in norm_lines(p)])
        report.append((r, p))
    report.sort(reverse=True)
    print("\n== old files by longest run vs NEW corpus ==")
    for r, p in list(report):
        flag = "  <-- >=30 VIOLATION" if r >= 30 else ""
        print(f"{r:5d}  {p.relative_to(OLD)}{flag}")

    # --- pairwise CSS violation checks ---
    print("\n== pairwise: old CSS vs new linker-commerce/assets/storefront.css ==")
    new_css = NEW / "plugins/linker-commerce/assets/storefront.css"
    new_lines = norm_lines(new_css)
    for old_rel in ["plugins/terravolt-b2b-core/assets/storefront.css",
                    "plugins/terravolt-b2b-core/assets/catalogue.css"]:
        old_lines = norm_lines(OLD / old_rel)
        m = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
        mb = max(m.get_matching_blocks(), key=lambda b: b.size)
        print(f"{old_rel}: old_norm_lines={len(old_lines)} longest_block={mb.size} "
              f"(old[{mb.a}:{mb.a+mb.size}] -> new[{mb.b}:{mb.b+mb.size}]) ratio={m.ratio():.3f}")
    old_union = set(norm_lines(OLD / "plugins/terravolt-b2b-core/assets/storefront.css"))
    old_union |= set(norm_lines(OLD / "plugins/terravolt-b2b-core/assets/catalogue.css"))
    hit = sum(1 for l in new_lines if l in old_union)
    print(f"new storefront.css: {len(new_lines)} norm lines, {hit} present in old assets = {hit/len(new_lines)*100:.1f}%")

if __name__ == "__main__":
    main()
```
