# #330 逐例判定

本文件是判定索引。完整请求、meta、blocks 和数字复核在同目录
`verdicts.jsonl`（一行一例，不含原始 SSE）。`evidence` 指向本机
`final.jsonl` 里该 case 的那一行。

已评分 111 例：pass 92，defect 15，parity 4。
第三轮另记在 `round3-runs.jsonl`：A6、A7、A8（系列错拼）、I7，
以及现行 G4 的 NEX- 措辞。那些行不并进这 111 例。

| class | EN | DE | pass | defect | parity | obs |
|---|---|---|---|---|---|---|
| 错拼/模糊拼写 | 5 | 5 | 8 | 2 | 0 | 0 |
| emoji | 5 | 5 | 10 | 0 | 0 | 0 |
| 超长输入 | 5 | 5 | 8 | 2 | 0 | 0 |
| 混合语言 | 5 | 5 | 10 | 0 | 0 | 0 |
| 大小写/连字符/空格 | 6 | 5 | 11 | 0 | 0 | 0 |
| 品牌+型号冲突 | 5 | 5 | 6 | 3 | 1 | 0 |
| 不存在的型号 | 5 | 5 | 5 | 4 | 1 | 0 |
| 多产品同句 | 5 | 5 | 8 | 1 | 1 | 0 |
| 数量/单位 | 6 | 6 | 10 | 2 | 0 | 0 |
| 矛盾条件 | 5 | 5 | 8 | 1 | 1 | 0 |
| 零件清单边界 | 7 | 1 | 8 | 0 | 0 | 0 |

111 turns; duration p50 8.2s, p95 22.5s, max 28.5s
graded: {'pass': 92, 'defect': 15, 'parity': 4, 'obs': 0, 'review': 0}

| case | class | lang | grade | defect | s | evidence |
|---|---|---|---|---|---|---|
| A1-EN | misspelling | en | pass |  | 6.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A1-EN |
| A2-EN | misspelling | en | pass |  | 12.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A2-EN |
| A3-EN | misspelling | en | defect | D7 | 22.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A3-EN |
| A4-EN | misspelling | en | defect | D12 | 12.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A4-EN |
| A5-EN | misspelling | en | pass |  | 5.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A5-EN |
| A1-DE | misspelling | de | pass |  | 8.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A1-DE |
| A2-DE | misspelling | de | pass |  | 7.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A2-DE |
| A3-DE | misspelling | de | pass |  | 5.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A3-DE |
| A4-DE | misspelling | de | pass |  | 20.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A4-DE |
| A5-DE | misspelling | de | pass |  | 3.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#A5-DE |
| B1-EN | emoji | en | pass |  | 9.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B1-EN |
| B2-EN | emoji | en | pass |  | 4.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B2-EN |
| B3-EN | emoji | en | pass |  | 12.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B3-EN |
| B4-EN | emoji | en | pass |  | 13.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B4-EN |
| B5-EN | emoji | en | pass |  | 9.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B5-EN |
| B1-DE | emoji | de | pass |  | 11.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B1-DE |
| B2-DE | emoji | de | pass |  | 3.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B2-DE |
| B3-DE | emoji | de | pass |  | 9.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B3-DE |
| B4-DE | emoji | de | pass |  | 11.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B4-DE |
| B5-DE | emoji | de | pass |  | 23.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#B5-DE |
| C1-EN | overlong | en | defect | D11 | 0.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C1-EN |
| C2-EN | overlong | en | pass |  | 11.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C2-EN |
| C3-EN | overlong | en | pass |  | 19.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C3-EN |
| C4-EN | overlong | en | pass |  | 4.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C4-EN |
| C5-EN | overlong | en | pass |  | 0.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C5-EN |
| C1-DE | overlong | de | defect | D11 | 0.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C1-DE |
| C2-DE | overlong | de | pass |  | 8.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C2-DE |
| C3-DE | overlong | de | pass |  | 4.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C3-DE |
| C4-DE | overlong | de | pass |  | 6.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C4-DE |
| C5-DE | overlong | de | pass |  | 0.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#C5-DE |
| D1-EN | mixed | en | pass |  | 9.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D1-EN |
| D2-EN | mixed | en | pass |  | 3.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D2-EN |
| D3-EN | mixed | en | pass |  | 6.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D3-EN |
| D4-EN | mixed | en | pass |  | 17.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D4-EN |
| D5-EN | mixed | en | pass |  | 6.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D5-EN |
| D1-DE | mixed | de | pass |  | 18.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D1-DE |
| D2-DE | mixed | de | pass |  | 8.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D2-DE |
| D3-DE | mixed | de | pass |  | 19.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D3-DE |
| D4-DE | mixed | de | pass |  | 11.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D4-DE |
| D5-DE | mixed | de | pass |  | 10.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#D5-DE |
| E1-EN | case-variants | en | pass |  | 8.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E1-EN |
| E2-EN | case-variants | en | pass |  | 9.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E2-EN |
| E3-EN | case-variants | en | pass |  | 16.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E3-EN |
| E4-EN | case-variants | en | pass |  | 9.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E4-EN |
| E5-EN | case-variants | en | pass |  | 14.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E5-EN |
| E6-EN | case-variants | en | pass |  | 3.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E6-EN |
| E1-DE | case-variants | de | pass |  | 6.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E1-DE |
| E2-DE | case-variants | de | pass |  | 8.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E2-DE |
| E3-DE | case-variants | de | pass |  | 10.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E3-DE |
| E4-DE | case-variants | de | pass |  | 10.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E4-DE |
| E5-DE | case-variants | de | pass |  | 3.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#E5-DE |
| F1-EN | brand-conflict | en | defect | D1 | 5.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F1-EN |
| F2-EN | brand-conflict | en | pass |  | 4.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F2-EN |
| F3-EN | brand-conflict | en | pass |  | 10.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F3-EN |
| F4-EN | brand-conflict | en | pass |  | 13.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F4-EN |
| F5-EN | brand-conflict | en | pass |  | 4.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F5-EN |
| F1-DE | brand-conflict | de | parity | parity | 7.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F1-DE |
| F2-DE | brand-conflict | de | pass |  | 4.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F2-DE |
| F3-DE | brand-conflict | de | defect | D8 | 8.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F3-DE |
| F4-DE | brand-conflict | de | defect | D5 | 11.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F4-DE |
| F5-DE | brand-conflict | de | pass |  | 10.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#F5-DE |
| G1-EN | fake-model | en | defect | D1 | 7.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G1-EN |
| G2-EN | fake-model | en | pass |  | 6.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G2-EN |
| G3-EN | fake-model | en | pass |  | 9.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G3-EN |
| G4-EN | fake-model | en | pass |  | 16.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G4-EN |
| G5-EN | fake-model | en | defect | D4 | 17.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G5-EN |
| G1-DE | fake-model | de | defect | D1 | 4.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G1-DE |
| G2-DE | fake-model | de | pass |  | 9.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G2-DE |
| G3-DE | fake-model | de | pass |  | 11.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G3-DE |
| G4-DE | fake-model | de | defect | D9 | 6.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G4-DE |
| G5-DE | fake-model | de | parity | parity | 28.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#G5-DE |
| H1-EN | multi-product | en | pass |  | 5.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H1-EN |
| H2-EN | multi-product | en | pass |  | 8.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H2-EN |
| H3-EN | multi-product | en | pass |  | 3.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H3-EN |
| H4-EN | multi-product | en | defect | D2 | 8.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H4-EN |
| H5-EN | multi-product | en | pass |  | 8.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H5-EN |
| H1-DE | multi-product | de | pass |  | 6.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H1-DE |
| H2-DE | multi-product | de | pass |  | 9.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H2-DE |
| H3-DE | multi-product | de | pass |  | 3.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H3-DE |
| H4-DE | multi-product | de | parity | parity | 12.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H4-DE |
| H5-DE | multi-product | de | pass |  | 6.8 | ~/de-linker-data/campaign-330/evidence/final.jsonl#H5-DE |
| I1-EN | units | en | pass |  | 10.2 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I1-EN |
| I2-EN | units | en | pass |  | 14.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I2-EN |
| I3-EN | units | en | pass |  | 4.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I3-EN |
| I4-EN | units | en | pass |  | 7.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I4-EN |
| I5-EN | units | en | pass |  | 3.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I5-EN |
| I6-EN | units | en | pass |  | 9.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I6-EN |
| I1-DE | units | de | defect | D10 | 11.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I1-DE |
| I2-DE | units | de | pass |  | 9.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I2-DE |
| I3-DE | units | de | pass |  | 2.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I3-DE |
| I4-DE | units | de | pass |  | 23.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I4-DE |
| I5-DE | units | de | defect | D3 | 7.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I5-DE |
| I6-DE | units | de | pass |  | 27.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#I6-DE |
| J1-EN | contradiction | en | pass |  | 8.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J1-EN |
| J2-EN | contradiction | en | pass |  | 5.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J2-EN |
| J3-EN | contradiction | en | pass |  | 5.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J3-EN |
| J4-EN | contradiction | en | pass |  | 15.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J4-EN |
| J5-EN | contradiction | en | defect | D6 | 11.6 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J5-EN |
| J1-DE | contradiction | de | pass |  | 23.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J1-DE |
| J2-DE | contradiction | de | pass |  | 7.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J2-DE |
| J3-DE | contradiction | de | pass |  | 9.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J3-DE |
| J4-DE | contradiction | de | pass |  | 7.7 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J4-DE |
| J5-DE | contradiction | de | parity | parity | 8.3 | ~/de-linker-data/campaign-330/evidence/final.jsonl#J5-DE |
| K1-EN | parts-boundary | en | pass |  | 1.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K1-EN |
| K2-EN | parts-boundary | en | pass |  | 6.1 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K2-EN |
| K3-EN | parts-boundary | en | pass |  | 1.5 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K3-EN |
| K4-EN | parts-boundary | en | pass |  | 0.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K4-EN |
| K5-EN | parts-boundary | en | pass |  | 0.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K5-EN |
| K6-EN | parts-boundary | en | pass |  | 5.4 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K6-EN |
| K7-EN | parts-boundary | en | pass |  | 5.9 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K7-EN |
| K8-DE | parts-boundary | de | pass |  | 0.0 | ~/de-linker-data/campaign-330/evidence/final.jsonl#K8-DE |
