<!-- source: https://tencentrtc.medium.com/how-i-added-ai-auto-reply-to-a-free-website-chat-widget-in-openclaw-aa99789f2aae | fetched (UTC): 2026-10-17T08:30:18.999Z | via Apify -->

# How I Added AI Auto-Reply to a Free Website Chat Widget in OpenClaw | by Shuoxin Wang

Member-only story

## How I Added AI Auto-Reply to a Free Website Chat Widget in OpenClaw

[





](https://tencentrtc.medium.com/?source=post_page---byline--aa99789f2aae-----------------------------------------)

8 min read

Mar 19, 2026

I’m a non-technical product person. Our team built Knocket, a 100% free website contact widget. It works great for live chat, but it had no AI features. I wanted to add smart auto-reply — so I used [OpenClaw](https://openclaw.ai/) and vibe coding to build it myself. This is the full story: what I did, what broke, and what I shipped.

## What Is Knocket?

Knocket is a free-forever website contact widget that combines live chat, offline forms, social links, and meeting scheduling in one embed. You paste one line of code before your `</body>` tag and your site gets a branded chat bubble in the bottom-right corner.

Press enter or click to view image in full size



*   **1-minute deploy** — copy one `<script>` tag, paste it into your HTML, done
*   **Live chat** — visitors message you on your site, you reply from the Inbox dashboard
*   **Offline forms** — automatically collect visitor contact info when you’re away
*   **Social link aggregation** — WhatsApp, Instagram, Telegram in one tap
*   **Zero-code customization** — colors, icons, greetings, all configurable from the dashboard

It’s built on Tencent Cloud IM infrastructure. Our engineering team built the console, SDK, and frontend widget from scratch. And it’s completely free — no $39/month Intercom bill, no…
