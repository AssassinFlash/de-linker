<!-- source: https://knocket.trtc.io/tutorials/ai_agent_handoff_phrases/ | fetched (UTC): 2026-10-17T08:29:04.933Z | via Apify -->

# Default Handoff Phrases — AI Agent Reference

## Why a built-in phrase library — the deterministic fast lane

The Knocket AI Agent uses a two-layer intent stack. The **outer layer** is the phrase library described on this page — a curated set of exact and near-exact triggers that transfer the chat **immediately**, without ever calling the model. The **inner layer** is the LLM's own intent classifier, which handles long-tail, emotional, or multi-turn "give up and escalate" cases that the phrase library intentionally does not cover.

This split is deliberate: when a user has already typed the exact words "transfer to human", we don't want to burn a model call, add latency, and risk a wrong classification. The phrase library is the safety net that guarantees the obvious cases always route correctly.

◈ TL;DR

Knocket ships 218+ phrases across 50 languages. Match one → the chat transfers to a human. No setup, no prompt tuning, no extra tokens.

## One trigger tier — explicit transfer only

The phrase library is intentionally strict: it contains only **explicit transfer** phrases — messages where the user unambiguously asks to reach a real person. When a message matches, the transfer fires in the same turn without ever calling the model.

Loose or ambiguous wording — bare nouns like "agent" or "customer service", role titles, or vague phrases like "find someone" — is deliberately **kept out** of the library, because it too easily fires on harmless questions ("do you have customer service?"). Those cases are left to the LLM's intent classifier downstream.

Priority 1

### Explicit Transfer

Unambiguous "please connect me to a human" phrasing. Firing action:

`action: transfer_immediately`

The model is not consulted. The AI Agent stops answering and the chat is placed in the human queue in the same turn.

Examples across languages

*   `talk to a human` 🇬🇧
*   `转人工` 🇨🇳
*   `parler à un humain` 🇫🇷
*   `オペレーターに繋いで` 🇯🇵
*   `상담원 연결` 🇰🇷
*   `соединить с оператором` 🇷🇺

## How the matching engine actually works

The library is not a fuzzy search — it's a deterministic four-step pipeline. Same input, same match, every time.

1.  **Normalize.** User input and every phrase in the library are passed through the same normalizer: Unicode NFKC, lowercase (for cased scripts), strip punctuation and emoji, collapse whitespace. For CJK text, all whitespace is also removed so `转 人 工` and `转人工` both match.
2.  **Match by script.** Word-delimited languages (English, Spanish, French, Arabic, Hindi, and 39 more) use **token-boundary matching** — the phrase must sit on word boundaries, so `agent` does not falsely fire on `urgent`, and `human` does not match inside `humanity`. Non-delimited languages (Chinese, Japanese, Korean, Thai) use **substring containment** instead, because those scripts don't use spaces between words.
3.  **Match & fire.** Every phrase in the library is an Explicit Transfer trigger. Any hit → `transfer_immediately`, and the chat is routed to a human in the same turn. No second tier, no scoring — one match is enough.
4.  **Language scoping.** If the session language is known, only that language's list is checked (fewer false positives, faster match). English is always included as a fallback — mixing English words like "human" or "agent" into any language is extremely common.

If nothing matches, the message is passed downstream to the LLM's intent classifier, which handles nuance the phrase library can't cover.

## Language coverage — 50 out of the box

Every language ships with a curated set of explicit-transfer triggers. The table below summarizes coverage; jump straight to the full library in the next section.

50

Languages

218

Curated Phrases

1

Trigger Tier

0ms

Model Latency

## The full phrase library

Every language below is what actually ships in the AI Agent runtime — no dummy rows, no placeholders. Expand a language to see both tiers side-by-side.

## Add your own phrases

The built-in library is the floor, not the ceiling. If your product uses domain-specific vocabulary — "escalate to billing", "get me a specialist", "刀哥来一下" — you can add your own explicit-transfer triggers from the AI Agent console.

1.  Open the **AI Agent** tab in the Knocket console.
2.  Scroll to **Handoff Rules → Phrase Library**.
3.  Click **Add phrase**, pick the language, then type or paste the trigger.
4.  Save. New phrases take effect on the next incoming message — no redeploy required.

Deleted a built-in phrase by mistake? Every entry on this page can be re-added; the reference above is stable and versioned.

**Back to the AI Agent tutorial**

See how the phrase library fits inside the wider AI Agent setup — persona, tools, knowledge, and human handoff policy.

[Open the tutorial →](https://knocket.trtc.io/tutorials/ai-agent/)
