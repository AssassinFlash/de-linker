# 静态面 fresh-diff 扩展（2026-10-13）

**不是像素门通过。** 132 对全部 FAIL，PASS 0。verified 只留给差异像素 = 0 且页高差 = 0 的格，本轮没有这样的格。不合并。

## 1. 范围

补拍 `docs/acceptance/17-readiness/ACCEPTANCE-MATRIX.md` 里基准 = live、且不在 28 态清单里的静态格。

拍了：

- Solution index / residential / commercial / utility
- 9 个产品子分类（accessories、all-in-one、backup-power、battery-systems、commercial-storage、ems、ev-chargers、inverters、meters）
- FAQ & documents、For EPC、About capability、Imprint、Privacy、Terms、Refund、Thank-you 静态页、Footer closed
- Compare 空态、芯片、带 ids 的表
- Shop / Archive 的 `brand=goodwe&sort=name`，以及 390 筛选抽屉开态
- 页头 mega × 5 开态与 closed（1440），移动抽屉 closed / open+section（390）
- 账户 guest 登录表单

每面 EN/DE × 有该面的视口。筛选抽屉只有 390。mega 与 closed 只有 1440。移动抽屉只有 390。

没拍（其它线在途，矩阵格不动）：PDP 全部、Genie 工作区/坞/芯片、配置器、账户登录后各页、28 态已含的 14 页型。

## 2. 条件

| 项 | 实测 |
|---|---|
| worktree / 源码 | `/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2debt`，分支 `research/freshdiff-full`，从 `origin/main` `c51cb2d34c64a181cd79bb43bba0119e4ec9b76e` 拉出。截图对应的是 **t110 上已装的实例**，不是本分支刚构建的产物。本轮没有 `just up`、没有重装 snapshot、没有改产品 |
| 实例 | t110 / `http://127.0.0.1:8975`，开拍前 `curl -sI` 首页 200。线上 `https://de-linker.com` 同次 200 |
| 浏览器 | 树内 `plugins/linker-tools` 的 Playwright，`channel: 'chromium'`，启动读到 `156.0.8078.4`。一次 launch，两侧独立匿名 context，`deviceScaleFactor: 1` |
| 协议 | 视口 1440×900 / 390×844。URL 带 `cbq`。注入禁动画 CSS。`document.fonts.ready`。滚动触发 lazy 后回顶。图片 decode，或已 complete 则直接 resolve，15 秒上限。全页 PNG。无掩膜、无平移、无阈值 |
| 数字 | `python3 .scratch/freshdiff-full/freshdiff.py`，RGB 任一通道差 > 0 即不同。重叠矩形是两侧共有的宽高。页高差 = t110 − live。摘要在 `docs/debt/analysis/freshdiff-full-summary.json` |
| 原图 | `.scratch/freshdiff-full/captures/`，132 对 PNG，不进本 PR |

PASS 的定义与 2026-10-12 续跑相同：原始差异像素 = 0 且页高差 = 0。1 级合成差仍然算 FAIL，不掩。

## 3. 账本

132 = 132 FAIL + 0 PASS。

| 面 | EN 1440 | EN 390 | DE 1440 | DE 390 |
|---|---|---|---|---|
| Solution index | 762,950 / 9.946056% / Δh +0<br>1440x5327 → 1440x5327<br>mag1 93.2% · header10 421 · struct10 11530 | 173,820 / 6.568789% / Δh +0<br>390x6785 → 390x6785<br>mag1 83.05% · header10 402 · struct10 15290 | 666,129 / 8.550639% / Δh +0<br>1440x5410 → 1440x5410<br>mag1 90.17% · header10 436 · struct10 25874 | 186,009 / 6.664051% / Δh +0<br>390x7157 → 390x7157<br>mag1 81.71% · header10 413 · struct10 19828 |
| Solution residential | 1,097,401 / 7.946653% / Δh +0<br>1440x9590 → 1440x9590<br>mag1 92.75% · header10 412 · struct10 47951 | 1,788,280 / 38.760214% / Δh +66<br>390x11830 → 390x11896<br>mag1 22.69% · header10 427 · struct10 967002 | 3,126,630 / 21.743149% / Δh +25<br>1440x9986 → 1440x10011<br>mag1 44.19% · header10 407 · struct10 931011 | 1,839,224 / 37.107239% / Δh +42<br>390x12709 → 390x12751<br>mag1 24.02% · header10 417 · struct10 963700 |
| Solution commercial | 6,536,380 / 42.777804% / Δh +63<br>1440x10611 → 1440x10674<br>mag1 38.39% · header10 424 · struct10 2940957 | 1,926,236 / 40.617325% / Δh +41<br>390x12160 → 390x12201<br>mag1 29.1% · header10 429 · struct10 1015919 | 5,972,962 / 38.377963% / Δh +63<br>1440x10808 → 1440x10871<br>mag1 31.87% · header10 439 · struct10 2993370 | 1,896,618 / 38.184069% / Δh +41<br>390x12736 → 390x12777<br>mag1 25.86% · header10 431 · struct10 1055255 |
| Solution utility | 8,012,044 / 63.384819% / Δh +318<br>1440x8778 → 1440x9096<br>mag1 2.42% · header10 62923 · struct10 6196747 | 2,687,144 / 83.892765% / Δh +3505<br>390x8213 → 444x11718<br>mag1 0.7% · header10 17537 · struct10 2408230 | 8,291,146 / 64.224655% / Δh +366<br>1440x8965 → 1440x9331<br>mag1 1.7% · header10 63009 · struct10 6616421 | 2,748,809 / 82.793706% / Δh +4195<br>390x8513 → 412x12708<br>mag1 0.83% · header10 17534 · struct10 2420990 |
| Category accessories | 914,675 / 16.413203% / Δh +0<br>1440x3870 → 1440x3870<br>mag1 25.24% · header10 450 · struct10 530678 | 946,673 / 52.426926% / Δh -52<br>390x4682 → 390x4630<br>mag1 3.64% · header10 448 · struct10 690632 | 5,063,212 / 90.8558% / Δh +15159<br>1440x3870 → 1440x19029<br>mag1 2.37% · header10 447 · struct10 4775771 | 1,537,245 / 82.066497% / Δh +41064<br>390x4803 → 390x45867<br>mag1 2.0% · header10 439 · struct10 1443052 |
| Category all-in-one | 454,721 / 11.925169% / Δh +0<br>1440x2648 → 1440x2648<br>mag1 15.28% · header10 450 · struct10 323623 | 660,813 / 58.609212% / Δh -66<br>390x2957 → 390x2891<br>mag1 3.19% · header10 448 · struct10 449997 | 3,545,723 / 92.987449% / Δh +16381<br>1440x2648 → 1440x19029<br>mag1 3.37% · header10 447 · struct10 3323230 | 1,086,396 / 91.003945% / Δh +42806<br>390x3061 → 390x45867<br>mag1 2.65% · header10 439 · struct10 1026098 |
| Category backup-power | 561,020 / 14.881483% / Δh +0<br>1440x2618 → 1440x2618<br>mag1 17.37% · header10 450 · struct10 363384 | 689,556 / 53.529891% / Δh -52<br>390x3355 → 390x3303<br>mag1 4.63% · header10 448 · struct10 459942 | 3,421,738 / 90.764207% / Δh +16411<br>1440x2618 → 1440x19029<br>mag1 3.47% · header10 447 · struct10 3190614 | 1,191,574 / 88.329516% / Δh +42408<br>390x3459 → 390x45867<br>mag1 2.46% · header10 439 · struct10 1120484 |
| Category battery-systems | 614,785 / 16.282762% / Δh +0<br>1440x2622 → 1440x2622<br>mag1 21.14% · header10 450 · struct10 410974 | 715,478 / 55.98288% / Δh -72<br>390x3349 → 390x3277<br>mag1 3.01% · header10 448 · struct10 496314 | 3,429,974 / 90.843874% / Δh +16407<br>1440x2622 → 1440x19029<br>mag1 3.47% · header10 447 · struct10 3182529 | 1,202,026 / 88.898701% / Δh +42400<br>390x3467 → 390x45867<br>mag1 2.41% · header10 439 · struct10 1133517 |
| Category commercial-storage | 934,438 / 16.621805% / Δh +0<br>1440x3904 → 1440x3904<br>mag1 22.36% · header10 450 · struct10 609053 | 985,731 / 54.39026% / Δh -72<br>390x4719 → 390x4647<br>mag1 2.34% · header10 448 · struct10 748491 | 5,103,037 / 90.772943% / Δh +15125<br>1440x3904 → 1440x19029<br>mag1 2.37% · header10 447 · struct10 4778601 | 1,558,271 / 82.844011% / Δh +41044<br>390x4823 → 390x45867<br>mag1 1.96% · header10 439 · struct10 1469020 |
| Category ems | 2,180,017 / 47.383433% / Δh -75<br>1440x3270 → 1440x3195<br>mag1 7.31% · header10 450 · struct10 1244968 | 851,003 / 59.619098% / Δh -132<br>390x3792 → 390x3660<br>mag1 1.36% · header10 448 · struct10 670357 | 4,281,851 / 90.932955% / Δh +15759<br>1440x3270 → 1440x19029<br>mag1 2.9% · header10 447 · struct10 4029476 | 1,312,365 / 85.930502% / Δh +41951<br>390x3916 → 390x45867<br>mag1 2.24% · header10 439 · struct10 1234849 |
| Category ev-chargers | 1,044,629 / 36.344529% / Δh -171<br>1440x2167 → 1440x1996<br>mag1 2.97% · header10 450 · struct10 725703 | 425,144 / 55.561306% / Δh -52<br>390x2014 → 390x1962<br>mag1 6.99% · header10 448 · struct10 223993 | 3,016,614 / 96.671474% / Δh +16862<br>1440x2167 → 1440x19029<br>mag1 3.9% · header10 447 · struct10 2797461 | 774,840 / 93.804024% / Δh +43749<br>390x2118 → 390x45867<br>mag1 3.72% · header10 439 · struct10 697907 |
| Category inverters | 2,751,789 / 20.627856% / Δh +0<br>1440x9264 → 1440x9264<br>mag1 29.09% · header10 450 · struct10 1553356 | 2,483,729 / 51.903308% / Δh -52<br>390x12322 → 390x12270<br>mag1 1.75% · header10 448 · struct10 2097182 | 11,377,964 / 85.291061% / Δh +9765<br>1440x9264 → 1440x19029<br>mag1 1.12% · header10 447 · struct10 10356481 | 3,888,171 / 78.680998% / Δh +33196<br>390x12671 → 390x45867<br>mag1 0.85% · header10 439 · struct10 3706681 |
| Category meters | 427,015 / 11.326898% / Δh +0<br>1440x2618 → 1440x2618<br>mag1 19.72% · header10 450 · struct10 271476 | 660,184 / 58.736276% / Δh -66<br>390x2948 → 390x2882<br>mag1 3.4% · header10 448 · struct10 440923 | 3,526,290 / 93.537529% / Δh +16411<br>1440x2618 → 1440x19029<br>mag1 3.35% · header10 447 · struct10 3295272 | 1,090,957 / 91.147789% / Δh +42798<br>390x3069 → 390x45867<br>mag1 2.6% · header10 439 · struct10 1029709 |
| FAQ & documents | 7,290,825 / 97.988638% / Δh +23120<br>1440x5167 → 1440x28287<br>mag1 0.24% · header10 441 · struct10 2007398 | 3,624,718 / 98.737371% / Δh +41993<br>390x9413 → 390x51406<br>mag1 0.23% · header10 448 · struct10 1079770 | 7,598,630 / 98.027613% / Δh +23145<br>1440x5383 → 1440x28528<br>mag1 0.2% · header10 447 · struct10 2075525 | 3,764,435 / 98.897515% / Δh +42673<br>390x9760 → 390x52433<br>mag1 0.2% · header10 439 · struct10 1170786 |
| For EPC | 6,706,588 / 51.224734% / Δh -375<br>1440x9467 → 1440x9092<br>mag1 7.16% · header10 421 · struct10 5778914 | 2,516,729 / 53.807648% / Δh -499<br>390x12492 → 390x11993<br>mag1 6.5% · header10 418 · struct10 2229645 | 6,886,301 / 51.053202% / Δh -312<br>1440x9679 → 1440x9367<br>mag1 7.97% · header10 436 · struct10 5884544 | 2,554,522 / 52.695546% / Δh -522<br>390x12952 → 390x12430<br>mag1 4.76% · header10 417 · struct10 2287115 |
| About capability | 1,037,542 / 8.779277% / Δh +0<br>1440x8207 → 1440x8207<br>mag1 99.04% · header10 441 · struct10 144 | 116,136 / 2.43308% / Δh +0<br>390x12239 → 390x12239<br>mag1 93.67% · header10 448 · struct10 2032 | 563,669 / 4.522144% / Δh +0<br>1440x8656 → 1440x8656<br>mag1 98.41% · header10 447 · struct10 6 | 149,136 / 2.939729% / Δh +0<br>390x13008 → 390x13008<br>mag1 94.65% · header10 439 · struct10 2100 |
| Imprint | 1,338 / 0.043137% / Δh +0<br>1440x2154 → 1440x2154<br>mag1 41.78% · header10 441 · struct10 1 | 9,399 / 0.811995% / Δh +0<br>390x2968 → 390x2968<br>mag1 18.49% · header10 448 · struct10 4117 | 1,337 / 0.042012% / Δh +0<br>1440x2210 → 1440x2210<br>mag1 41.74% · header10 447 · struct10 1 | 9,347 / 0.771128% / Δh +0<br>390x3108 → 390x3108<br>mag1 18.09% · header10 439 · struct10 4116 |
| Privacy | 887,452 / 13.993781% / Δh +8<br>1440x4404 → 1440x4412<br>mag1 35.9% · header10 441 · struct10 409458 | 554,734 / 22.319078% / Δh +8<br>390x6373 → 390x6381<br>mag1 15.77% · header10 448 · struct10 391185 | 1,171,133 / 15.628109% / Δh -20<br>1440x5224 → 1440x5204<br>mag1 19.28% · header10 447 · struct10 543788 | 721,679 / 26.760072% / Δh -18<br>390x6933 → 390x6915<br>mag1 13.0% · header10 439 · struct10 493820 |
| Terms | 518,502 / 8.857831% / Δh +8<br>1440x4065 → 1440x4073<br>mag1 60.82% · header10 441 · struct10 86868 | 200,860 / 9.975317% / Δh +8<br>390x5163 → 390x5171<br>mag1 40.76% · header10 448 · struct10 66140 | 519,789 / 8.307585% / Δh +8<br>1440x4345 → 1440x4353<br>mag1 60.29% · header10 447 · struct10 90568 | 214,332 / 9.646643% / Δh +8<br>390x5697 → 390x5705<br>mag1 41.86% · header10 439 · struct10 71744 |
| Refund | 518,373 / 11.860997% / Δh +8<br>1440x3035 → 1440x3043<br>mag1 60.8% · header10 441 · struct10 86921 | 200,910 / 12.840325% / Δh +8<br>390x4012 → 390x4020<br>mag1 40.77% · header10 448 · struct10 66174 | 519,812 / 10.781976% / Δh +8<br>1440x3348 → 1440x3356<br>mag1 60.3% · header10 447 · struct10 90553 | 214,110 / 12.243533% / Δh +8<br>390x4484 → 390x4492<br>mag1 41.78% · header10 439 · struct10 71827 |
| Thank-you static | 88,992 / 1.289111% / Δh +0<br>1440x4794 → 1440x4794<br>mag1 97.09% · header10 441 · struct10 14 | 169,578 / 6.757038% / Δh +0<br>390x6435 → 390x6435<br>mag1 94.0% · header10 448 · struct10 4003 | 471,510 / 6.57373% / Δh +0<br>1440x4981 → 1440x4981<br>mag1 98.72% · header10 447 · struct10 14 | 262,039 / 9.717889% / Δh +0<br>390x6914 → 390x6914<br>mag1 94.95% · header10 439 · struct10 4011 |
| Footer closed | 1,036,178 / 8.707261% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 94.63% · header10 441 · struct10 12041 | 206,659 / 6.003114% / Δh +0<br>390x8827 → 390x8827<br>mag1 90.4% · header10 448 · struct10 8940 | 1,247,830 / 10.103167% / Δh +0<br>1440x8577 → 1440x8577<br>mag1 95.91% · header10 447 · struct10 8393 | 216,093 / 5.96881% / Δh +0<br>390x9283 → 390x9283<br>mag1 91.4% · header10 439 · struct10 7926 |
| Compare empty | 1,357,831 / 89.378028% / Δh -59<br>1440x1114 → 1440x1055<br>mag1 3.81% · header10 441 · struct10 625039 | 412,565 / 88.597904% / Δh -33<br>390x1227 → 390x1194<br>mag1 11.53% · header10 448 · struct10 204838 | 1,342,265 / 86.148657% / Δh -32<br>1440x1114 → 1440x1082<br>mag1 10.33% · header10 447 · struct10 595170 | 418,740 / 83.231962% / Δh +20<br>390x1290 → 390x1310<br>mag1 18.57% · header10 439 · struct10 210366 |
| Compare chip | 2,717,416 / 20.427522% / Δh +0<br>1440x9238 → 1440x9238<br>mag1 27.66% · header10 450 · struct10 1553035 | 2,498,112 / 52.28057% / Δh -52<br>390x12304 → 390x12252<br>mag1 1.87% · header10 448 · struct10 2090003 | 11,308,100 / 85.005924% / Δh +9791<br>1440x9238 → 1440x19029<br>mag1 1.13% · header10 447 · struct10 10255023 | 3,894,339 / 78.986589% / Δh +33225<br>390x12642 → 390x45867<br>mag1 0.91% · header10 439 · struct10 3690136 |
| Compare with ids | 2,156,807 / 94.140958% / Δh +451<br>1440x1591 → 1440x2042<br>mag1 0.24% · header10 441 · struct10 1503827 | 682,091 / 94.794107% / Δh +695<br>390x1845 → 390x2540<br>mag1 0.29% · header10 448 · struct10 443868 | 2,157,063 / 94.152132% / Δh +497<br>1440x1591 → 1440x2088<br>mag1 0.26% · header10 447 · struct10 1515790 | 714,593 / 94.986508% / Δh +681<br>390x1929 → 390x2610<br>mag1 0.27% · header10 439 · struct10 468185 |
| Shop filtered+sort | 4,238,325 / 31.860589% / Δh +0<br>1440x9238 → 1440x9238<br>mag1 16.62% · header10 450 · struct10 3085732 | 2,575,918 / 53.908896% / Δh -136<br>390x12388 → 390x12252<br>mag1 0.78% · header10 448 · struct10 2274821 | 11,318,534 / 85.084359% / Δh +9791<br>1440x9238 → 1440x19029<br>mag1 1.13% · header10 1437 · struct10 10239336 | 3,890,670 / 78.570347% / Δh +33170<br>390x12697 → 390x45867<br>mag1 0.87% · header10 439 · struct10 3705408 |
| Archive filtered+sort | 4,165,749 / 33.890361% / Δh +728<br>1440x8536 → 1440x9264<br>mag1 15.49% · header10 450 · struct10 2911008 | 2,459,270 / 57.52961% / Δh +1309<br>390x10961 → 390x12270<br>mag1 0.7% · header10 448 · struct10 2281916 | 10,550,464 / 85.833073% / Δh +10493<br>1440x8536 → 1440x19029<br>mag1 1.19% · header10 447 · struct10 9677670 | 3,566,760 / 81.156611% / Δh +34598<br>390x11269 → 390x45867<br>mag1 0.92% · header10 439 · struct10 3427406 |
| Shop filter drawer | — | 2,624,191 / 54.919155% / Δh -52<br>390x12304 → 390x12252<br>mag1 1.74% · header10 17352 · struct10 2184110 | — | 3,919,156 / 79.489938% / Δh +33225<br>390x12642 → 390x45867<br>mag1 0.17% · header10 17391 · struct10 3741326 |
| Archive filter drawer | — | 2,624,038 / 54.835392% / Δh -52<br>390x12322 → 390x12270<br>mag1 1.72% · header10 17352 · struct10 2198703 | — | 3,931,538 / 79.558572% / Δh +33196<br>390x12671 → 390x45867<br>mag1 0.17% · header10 17391 · struct10 3753778 |
| Account guest form | 1,931,248 / 91.234316% / Δh +506<br>1440x1470 → 1440x1976<br>mag1 5.73% · header10 450 · struct10 1710668 | 543,025 / 91.243237% / Δh +931<br>390x1526 → 390x2457<br>mag1 4.8% · header10 449 · struct10 487660 | 1,938,126 / 91.55924% / Δh +506<br>1440x1470 → 1440x1976<br>mag1 6.05% · header10 447 · struct10 1710158 | 579,601 / 91.794713% / Δh +901<br>390x1619 → 390x2520<br>mag1 4.5% · header10 439 · struct10 526332 |
| Mega Products open | 886,691 / 7.451085% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 92.21% · header10 439 · struct10 13102 | — | 1,000,027 / 7.383194% / Δh +0<br>1440x9406 → 1440x9406<br>mag1 92.72% · header10 447 · struct10 30288 | — |
| Mega Solutions open | 1,199,663 / 10.081066% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 95.27% · header10 439 · struct10 12095 | — | 1,010,149 / 7.610028% / Δh +0<br>1440x9218 → 1440x9218<br>mag1 91.67% · header10 447 · struct10 41881 | — |
| Mega Plan open | 999,108 / 8.395753% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 91.74% · header10 439 · struct10 40313 | — | 7,424,762 / 56.240017% / Δh -74<br>1440x9242 → 1440x9168<br>mag1 2.46% · header10 447 · struct10 5019916 | — |
| Mega Partners open | 1,026,116 / 8.622708% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 94.6% · header10 439 · struct10 12041 | — | 961,763 / 7.285024% / Δh +0<br>1440x9168 → 1440x9168<br>mag1 94.73% · header10 447 · struct10 8586 | — |
| Mega About open | 1,278,357 / 10.742351% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 95.62% · header10 439 · struct10 12055 | — | 961,609 / 7.225536% / Δh +0<br>1440x9242 → 1440x9242<br>mag1 94.74% · header10 447 · struct10 8585 | — |
| Mega closed | 1,299,525 / 10.920231% / Δh +0<br>1440x8264 → 1440x8264<br>mag1 95.6% · header10 441 · struct10 12054 | — | 1,317,435 / 10.66673% / Δh +0<br>1440x8577 → 1440x8577<br>mag1 96.05% · header10 447 · struct10 8402 | — |
| Mobile drawer closed | — | 206,658 / 6.003085% / Δh +0<br>390x8827 → 390x8827<br>mag1 90.43% · header10 448 · struct10 8937 | — | 268,380 / 7.413054% / Δh +0<br>390x9283 → 390x9283<br>mag1 92.78% · header10 439 · struct10 7948 |
| Mobile drawer open+section | — | 234,725 / 6.345377% / Δh +0<br>390x9485 → 390x9485<br>mag1 79.36% · header10 448 · struct10 36764 | — | 244,520 / 6.317759% / Δh +0<br>390x9924 → 390x9924<br>mag1 80.57% · header10 439 · struct10 35174 |

`—` 不是漏拍。筛选抽屉矩阵只要求 390。mega 与 mega closed 矩阵只要求 1440。移动抽屉只要求 390。

## 4. 归因

口径沿用 `docs/debt/FRESH-DIFF-2026-10-12.md` §7.3，不新发明阈值：

- `mag1`：通道差正好是 1。上次对拍量过，这是 Chromium 把页面合成进 PNG 的差，不是换文件、不是 srcset、不是裁切框。本轮没有重做那次 WebP 字节比对。
- `header10`：1440 的 y=21–66、390 的 y=17–62 里，通道差 ≥ 10 的像素。上次对拍把这条带记为页头控件差。
- `struct10`：通道差 ≥ 10、且不在那条页头带里。这是版面差，1 级合成差解释不了。

没有一格的 `struct10` 是 0。最近的是 Imprint 1440（struct10 = 1，落在 y=1964）和 capability DE 1440（struct10 = 6）。页头带在 1440 上重复出现，大约 410–450 px。所以同高、mag1 占 90% 以上的页，仍然 FAIL：剩下的是页头带，加上正文里没有归零的结构像素。

### 4.1 同高、以合成差为主，外加页头带

Solution index 两侧 1440、residential EN 1440、capability 四态、Thank-you 四态、Footer 四态、mega closed 两侧、多数 mega 开态、抽屉 closed 两侧。

这些页页高差 = 0，mag1 占差异的 90%–99%。页头带仍有约 400 px 的 ≥10 差。Imprint 四态页高也对齐，但 mag1 占比低（1440 为 41.7%），因为总差异只有 1,337 / 1,338 px，页头带就占了 447 / 441。正文 y=90 以下还剩 540 px，其中 537 是 1 级差，1 px 在 y=1964。390 的 Imprint 正文还有 4,117 个 ≥10 的像素，不把 1440 的结论扩过去。

不把这些叫通过。不掩页头带。

### 4.2 德语目录落在旧产品家族页

t110 的 `/de/produkte/`、`/de/produkt-kategorie/…` 最终 URL 停在所请求的地址，`lang=de-DE`，但正文是 “TerraVolt Produktfamilien”，`data-compare-article` = 0。线上对应页是目录，商品数 > 0。页高因此成对地落在 19028（1440）或 45866（390）。

这条盖住 26 态：9 个子分类的 DE × 两视口，加上 shop/archive 的 DE filtered、DE 筛选抽屉、DE 芯片。芯片动作在 t110 上报 `no compare control`，因为那页没有 `[data-compare-article]`。筛选抽屉同样点不到 `#catalog-filter-open`。这是页面落错，不是点击脚本没等到。

英文目录没有这条。英文 shop `?brand=goodwe&sort=name` 页高相同（9238），但仍有 4,238,325 px / 31.86% 差异，struct10 = 3,085,732。筛选结果的版面差，不是合成差。

### 4.3 版面差，不是合成差

| 面 | 看到的 | 数字 |
|---|---|---|
| FAQ 四态 | 线上是搜索框 + 折叠文档。t110 把问答 `<details>` 展开成一长列，页高 5166→28286（EN 1440），差异 97.99% | struct10 两百万级，mag1 < 0.3% |
| 账户 guest 四态 | 线上是居中的 Sign in（用户名、密码、Remember me、Create account）。t110 是左右两栏，右侧 Register 带公司名、VAT、地址。DE 同样 | EN 1440 差异 1,931,248 / 91.23%，Δh +506 |
| Compare 空态 | 线上一句 “Choose products…” + Browse products。t110 多一段说明 + Continue browsing | EN 1440 1,357,831 / 89.38%，Δh −59 |
| Compare `?ids=6530,6529` | 两侧都打开了这两个 id（id 在两边商品上相同，开拍前查过）。表的高度不同 | EN 1440 Δh +451，差异 94.14% |
| Compare 芯片 EN | 两侧芯片都可见。线上 “Compare 1”（`#compare-chip.sf-compare-chip`）。t110 “Compare 1/4” | EN 1440 同高，struct10 1,553,035 |
| For EPC 四态 | 页高 t110 更短 312–522 px，struct10 占绝大多数 | EN 1440 51.22% |
| Utility | 1440 页高 +318 / +366，页头带本身就有 6 万 px 的 ≥10 差。390 本地宽 444 / 412，不是 390，内容横向溢出 | EN 390 差异 83.89%，Δh +3505 |
| Commercial / residential 子页 | 页高差 +25 到 +66，struct10 几十万到三百万 | 不是 1 级差能解释的 |
| Privacy / Terms / Refund | Terms 与 Refund 的 EN/DE × 两视口，t110 都正好高 8 px。Privacy EN +8，DE −20 / −18。8 px 之外仍有 struct10 6 万–54 万 | 不把 +8 当成舍入 |
| Shop/Archive EN 390 抽屉 | 两侧 `#catalog-filter-open` 都点开了。页高差 −52。抽屉带（y=17–62 放不下，header10 记了 17,352）加上筛选面板本身 | struct10 约 220 万 |
| Plan mega DE 开态 | 其它四个 DE mega 走汉堡后页高相同。Plan 这一对 Δh −74，struct10 5,019,916 | 单独记，不并进“菜单只差合成” |

### 4.4 开态怎么开的

英文 1440 的五个 mega：点 `[data-tv-nav-primary]` 里有布局的 `button.tv-nav-link`，`aria-expanded` 两侧都变成 `true`。冒烟截图顶部能看到 Products 面板。

德语 1440 没有可见的桌面 nav 项。五个 `button.tv-nav-link` 的 `getBoundingClientRect` 都是 0×0，汉堡 `#tv-mobile-toggle` 是 44×44，在 x=1372。英文首页同一视口下五个文字按钮有尺寸、汉堡是 0×0。所以德语开态改为：点汉堡，再把对应的 `details[data-tv-mobile-primary]` 设为 open。两侧 `panelH` 都 > 0。截图顶部是展开的 Produkte 段，不是桌面 mega。矩阵写的是 1440 开态；1440 上德语没有桌面 mega 可开，这一步记在这里，不把它说成桌面 mega 已对齐。

移动抽屉 390：点 `#tv-mobile-toggle`，展开第一个 `details.tv-mobile-section`。两侧面板都打开。Solutions 段的缩略图，线上有照片，t110 是空盒。这落在 drawer-open 的 struct10（EN 36,764）里。

## 5. 没做

- 没有掩膜，没有把 1 级差修进浏览器。
- 没有登录、没有提交、没有发信。
- 没有重建 t110，没有补德语目录模板。
- 原图不进 PR。可复核的数字是 `docs/debt/analysis/freshdiff-full-summary.json`。
- 像素门未通过。本 PR 的 CI 绿也不改变这一点。

## 复测（2026-10-13 晚，配置器/目录/账户修复之后）

同日第二次全量采集（132 对，live × t110，同协议）：**0 PASS 维持**；中位差异 28.5%；最好的一对 `imprint-en-1440` 0.043%（1,336 px，全部为 header10 441 带 + struct10），最差 ~63%（utility/faq 页）。64 对页高差 |Δ|≤8px。归因与前次一致（头带 + mag1 合成），目录/配置器/账户面上的修复不在这 132 对的覆盖面内。

数字：`docs/debt/analysis/freshdiff-rerun-2026-10-13.json`（pairs=132；PASS 定义同前：差异像素=0 且页高差=0）。原图在 `de-linker-worktrees/de-linker-r2debt/.scratch/freshdiff-full/captures-b/`（同前例，不进 git）。
