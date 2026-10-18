# deepseek-flash reading a nameplate: thinking on or off (#236)

Measured 2026-10-18 on the 11 photos of `services/genie/eval/attachments/photos/`, one
call each, official API (`https://api.deepseek.com/chat/completions`, model
`deepseek-flash`), the service's own `PHOTO` instruction, `response_format:
json_object`. "on" is the API's default (thinking enabled, effort high); "off" sends
`"thinking": {"type": "disabled"}` (research S16). Columns: seconds, brand, model read,
ratings read, output tokens (of them reasoning).

| photo | on | off |
|---|---|---|
| ecoflow-powerocean-bd-5.1-s1 | 17.7 s · EcoFlow · EF BD-5.1-S1 · 7 · 4206 (3809) | 2.2 s · EcoFlow · EF BD-5.1-S1 · 7 · 395 |
| goodwe-bat-c-label (five models, none ticked) | 8.0 s · GOODWE · GW61.4-BAT-AC-JP-G10 · 10 · 2165 (1433) | 4.0 s · GOODWE · null · 24 · 1037 |
| goodwe-gw10k-et | 12.6 s · GW10K-ET · 22 | 3.4 s · GW10K-ET · 22 |
| goodwe-gw3648-em (sideways) | 20.6 s · GW3648-EM · 21 | 3.6 s · GW3648-EM · 21 |
| goodwe-gw5048-em | 15.0 s · GW5048-EM · 17 | 3.5 s · GW5048-EM · 17 |
| goodwe-gw5048d-es | 6.9 s · GW5048D-ES · 17 | 3.8 s · GW5048D-ES · 17 |
| goodwe-gw7600a-es | 16.9 s · GW7600A-ES · 21 | 4.0 s · GW7600A-ES · 21 |
| pylontech-us3000c-thumbnail | 2.9 s · null · null | 0.9 s · PYLON · null |
| pylontech-us3000c (pen across the model) | 31.4 s · PYLONTECH · US3000 · 5 · 7303 (7026) | 3.5 s · PYLONTECH · null · 5 |
| saj-r5-6k-s2-15 | 26.3 s · null · R5-6K-S2-15 · 17 | 2.7 s · null · R5-6K-S2-15 · 17 |
| saj-sununo-plus-4k-m | 11.7 s · SAJ · Sununo Plus 4K-M · 15 | 3.7 s · SAJ · Sununo Plus 4K-M · 15 |

Earlier the same day, with thinking on inside the evaluation, `pylontech-us3000c` timed
out twice at 30 s (the client's timeout) and the reading failed.

**品牌猜测（评审第 1 轮第 11 条）**：关思考后，`saj-r5-6k-s2-15` 的标签不印厂商，同一张照片在不同运行里读出过 INVS、SOLIS、HVS（上表这一次读到 null；开思考时为 null）。读到的品牌因此只在本站产品词表内才保留（`nameplate.with_known_brand`），词表外按未读出处理：`none`/`partial` 路由不会把猜出的品牌当作我们的品牌。

**Decision**: off. Every model read with thinking on is read the same with it off, or
left null (US3000C under the pen line, the unticked multi-model label), and a null
model is graded `unreadable`, which asks the customer for a sharper photo or the model
typed in. With thinking on, the US3000C under the pen line came back as "US3000"; with it off, no model was read wrongly. With it on, a photo alone could take
half of the shell's 60 s before the turn's agent starts. The agent that writes the
answer keeps thinking on.
