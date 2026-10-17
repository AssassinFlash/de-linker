<!-- source: https://wordpress.org/plugins/knocket-live-chat-widget/ | fetched (UTC): 2026-10-17T08:28:39.565Z | via Apify -->

# Knocket — Live Chat Widget – WordPress plugin

**Knocket** is a lightweight, 100% free contact widget built for indie developers and early-stage teams who need to catch every visitor who wants to reach them.

One `<script>` tag. No seat fees. No ads. No paid tier hiding the useful features.

#### What the Web Widget does

After installing this plugin, a floating chat button appears on your site. When a visitor clicks it, they can send you a message instantly — no email form, no waiting. You get notified in real time via Telegram or browser push, and you can reply from the [Knocket console](https://knocket.trtc.io/) or directly from Telegram by quote-replying.

**Everything works out of the box:**

*   Fully customizable — theme color, welcome message, avatar, language, offline message
*   Real-time live chat for your site visitors
*   Notifications via Telegram or browser push — reply without opening a dashboard
*   Telegram quote-reply message goes straight back to the visitor
*   Unified inbox: all messages from live chat, Telegram, and email in one place
*   Lightweight loading — the script is enqueued in the footer through WordPress
*   100% free, no seat limits, no ads, forever

#### Who it’s for

Knocket is for people still looking for their first 100 users. If you’re shipping a SaaS, an open-source tool, or an indie product and you want to talk to every person who lands on your site — this is for you. Not a helpdesk. Not an enterprise ticketing system. Just real, fast, lightweight connection.

#### Coming soon

*   **AI Agent** — build a knowledge base from your FAQ, a URL, or uploaded files. Knocket AI automatically answers visitor questions using LLM-powered semantic understanding. Supports multiple languages and complex questions. Falls back to a human agent when confidence is low or the visitor asks for one.
*   **AI-generated Contact Page** — pick a template (Creator / Business / Developer) and let AI generate your shareable contact page from a one-sentence description. All content editable after generation.

#### Full Knocket feature set

Beyond this WordPress plugin, Knocket also offers:

*   **Contact Page** — a shareable link that works as a personal contact hub (live chat + social links + email). No website required. Works as a link-in-bio, a waitlist page, or a standalone contact entry point.
*   **Mobile Widget** — embed Knocket into iOS, Android, React Native, or Flutter apps via WebView.
*   **Unified Inbox** — all channels (web widget, contact page, Telegram, email) feed into one inbox. Reply from any channel and the message goes back through the original channel.

#### Data & Privacy

This plugin loads a script from `trtc.io` (powered by Tencent RTC infrastructure). Chat messages are processed by Knocket’s servers. See the [Knocket Privacy Policy](https://knocket.trtc.io/legal/privacy/) for details.

#### External Services

This plugin connects to the following external service:

*   **Knocket / trtc.io** — the widget script is loaded from `https://trtc.io/knocket-sdk/sdk.js`. When a visitor uses the chat widget, messages are sent to Knocket’s servers for delivery and storage.
    *   Service URL: https://knocket.trtc.io/
    *   Privacy Policy: https://knocket.trtc.io/legal/privacy/
    *   Terms of Service: https://knocket.trtc.io/legal/terms/

No data is sent to this service until you configure your script URL in the plugin settings.

1.  In your WordPress admin, go to **Plugins Add New Plugin Upload Plugin**
2.  Upload `knocket-live-chat-widget.zip` and click **Install Now**, then **Activate**
3.  Go to **Settings Knocket Widget**
4.  Open the [Knocket console](https://knocket.trtc.io/), sign up for free, then go to **Installation Web Widget**
5.  Copy the `src` URL from the `<script>` tag shown there (or copy the entire tag)
6.  Paste it into the **Script Source URL** field and click **Save Settings**

The chat widget appears on your site immediately.

Yes — 100% free forever. No seat limits, no ads, no paid tier. See [knocket.trtc.io](https://knocket.trtc.io/).

Sign up at [knocket.trtc.io](https://knocket.trtc.io/), then go to **Installation Web Widget**. Copy the `src` URL (or the full `<script>` tag) and paste it into the plugin settings.

Yes — theme color, welcome message, avatar, language, and button style are all configurable in the [Knocket console](https://knocket.trtc.io/). Changes apply instantly without updating the plugin.

No. The script is loaded in the footer through WordPress’s standard script enqueue system.

Connect Telegram or enable browser push in the Knocket console. With Telegram, you can quote-reply a notification and the reply goes straight back to your visitor.

Enable the “Only on front page” toggle under **Settings Knocket Widget**.

There are no reviews for this plugin.

“Knocket — Live Chat Widget” is open source software. The following people have contributed to this plugin.

Contributors

*    [ivory](https://profiles.wordpress.org/rrivory/)

#### 1.0.2

*   Match the WordPress.org plugin slug and text domain.
*   Escape settings output at render time.
*   Remove direct script-tag filtering and rely entirely on the WordPress enqueue system.

#### 1.0.1

*   Load the Knocket SDK through the WordPress script enqueue system.
*   Restrict configuration to the official HTTPS Knocket SDK endpoint.
*   Correct the privacy policy and terms of service links.

#### 1.0.0

*   Initial release.
