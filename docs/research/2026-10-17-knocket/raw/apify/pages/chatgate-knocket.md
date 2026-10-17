<!-- source: https://chatgate.ai/de/post/knocket | fetched (UTC): 2026-10-17T08:28:46.621Z | via Apify -->

# Knocket: Chat with visitors from your website or link

Knocket is a free live-chat contact layer that lets visitors message you from any website, mobile app, or shareable link, with every conversation landing in one inbox you can answer from Telegram or hand to an AI agent. Built on Tencent RTC infrastructure for solo makers, it is documented on the [official homepage](https://knocket.trtc.io/) and listed in its [Product Hunt launch](https://www.producthunt.com/products/knocket-2).

## How does Knocket turn a visit into a conversation?

The main surface is a Web Widget installed with one script tag pasted before `</body>`, carrying an identifier that connects the bubble to your inbox. Per the [widget documentation](https://knocket.trtc.io/products/web-widget/), it loads asynchronously and runs on WordPress, Shopify, Webflow, Next.js, React, Vue, Wix, Squarespace, and plain HTML, with colors, welcome text, online status, and offline fields editable live without redeploying.

Visitors need no account: they tap and type, and can send images, videos, and files that sync to the inbox and Telegram. Two-way read receipts, two-sided message recall, and visitor identity via `user_id`, email, and tags keep threads consistent across pages. Offline, the bubble becomes a lead form that collects email plus message in the same thread. A Contact Page adds a `knocket.ai` link-in-bio with pinned chat, while a Mobile Widget embeds the same history in iOS and Android apps via WebView.

## What can the AI agent actually answer?

The agent handles routine questions from your own knowledge and hands off when a human is needed. The [official homepage](https://knocket.trtc.io/) describes uploading docs and FAQs so the agent answers from that material and escalates at the right moment.

A detailed [Woshipm review](https://www.woshipm.com/ai/6473812.html) shows console controls for which surfaces the AI covers, always-on versus offline-only duty, plus name, avatar, welcome text, and prompt tone. Knowledge comes from written FAQs, page URLs, and uploads including PDF, TXT, DOC, DOCX, HTML, MD, CSV, and XLSX up to 10MB each. An [AI-Bot overview](https://ai-bot.cn/sites/87389.html) confirms the same three sources plus usage stats for model calls. Setup is bring-your-own-key through an OpenAI-compatible endpoint, and handoff uses 218-plus preset phrases across dozens of languages before the model judges harder cases.

## Who is it best for, and where does it fall short?

Knocket suits solo founders, creators, and small teams with modest traffic who cannot justify seat-priced support. Landing-page questions, trial activation, cart rescue, portfolio inquiries, and bookings fit well: no visitor registration, phone replies, and AI coverage after hours. The [AI-Bot overview](https://ai-bot.cn/sites/87389.html) highlights zero-friction contact and unified web, app, and link messages on low-latency Tencent RTC messaging.

Limits matter as teams grow. Independent testing at [Toolradar](https://toolradar.com/tools/knocket) finds no native reply app, so mobile answers depend on Telegram, and contact pages are limited to `knocket.ai` paths with no custom domains. There is no team roles setup, so sharing means one inbox or Telegram thread, and the mobile embed is WebView rather than a full native SDK. Complex queues, SLAs, and reporting belong elsewhere.

## How much does it cost and how does it fit your stack?

Everything current is free forever with no message caps, visitor limits, or card required, explained in the team's [why-free letter](https://knocket.trtc.io/why-free/). Messaging rides existing Tencent RTC scale, while AI calls use your own model key, so the widget, contact page, inbox, and AI receptionist cost nothing. Future paid work is framed as team, integration, and automation features for larger firms.

Setup takes minutes: paste the snippet, share the contact link in bios and signatures, and connect Telegram plus email alerts. The [widget documentation](https://knocket.trtc.io/products/web-widget/) covers plain HTML through React and Next.js patterns, and the [Woshipm review](https://www.woshipm.com/ai/6473812.html) notes about 50 interface languages picked from page and browser locale.

In short, Knocket trades depth for availability: one script, one link, one inbox, and AI backup so no willing visitor is missed. If that fits your stage, start free on the [official Knocket site](https://knocket.trtc.io/).

## Sources

*   [official homepage](https://knocket.trtc.io/)
*   [widget documentation](https://knocket.trtc.io/products/web-widget/)
*   [why-free letter](https://knocket.trtc.io/why-free/)
*   [Product Hunt launch](https://www.producthunt.com/products/knocket-2)
*   [Toolradar](https://toolradar.com/tools/knocket)
*   [AI-Bot overview](https://ai-bot.cn/sites/87389.html)
*   [Woshipm review](https://www.woshipm.com/ai/6473812.html)
