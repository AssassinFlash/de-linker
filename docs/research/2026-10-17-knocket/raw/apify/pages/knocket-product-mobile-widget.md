<!-- source: https://knocket.trtc.io/products/mobile-widget/ | fetched (UTC): 2026-10-17T08:17:51.906Z | via Apify -->

# Mobile Widget — In-app chat via WebView SDK · Knocket

◐ MOBILE WIDGET

## Every conversation.  
Inside your app.

Ship the Knocket **WebView SDK** into your **iOS, Android, React Native or Flutter** app. Open a direct chat line to every user. When something breaks or confuses them, they message you — **not the App Store review section**.



◈ iOS

◐ Android

▸ React Native

✦ Flutter

Mobile Widget. WebView SDK. iOS · Android · RN · Flutter. In-app chat. One inbox. Mobile Widget. WebView SDK. iOS · Android · RN · Flutter. In-app chat. One inbox.

◈ IN-APP CHAT VIA WEBVIEW SDK

## Zero backend. One SDK.

Load the Knocket chat into a WebView — same URL on iOS, Android, React Native, and Flutter. Register a `closeWebView` channel so the page can dismiss itself. No native chat UI to maintain.

**iOS · Swift · WebView** ChatViewController.swift

// The Knocket chat lives in a WKWebView.  
// Copy your URL from the console — the  
// path is your Contact Page handle.

_import_ **WebKit**

_let_ config = **WKWebViewConfiguration**()  
// Channel name must be "closeWebView"  
config.userContentController._add_(self,  
name: "closeWebView")

_let_ webView = **WKWebView**(frame: view.bounds,  
configuration: config)  
_let_ url = _URL_(string:  
"https://knocket.ai/**yourname**?platform=mobile")!  
webView.load(**URLRequest**(url: url))  
view.addSubview(webView)

◈ WHAT THE WIDGET GIVES YOU

## Real chat.  
Real attachments.

All mobile conversations flow into your unified Knocket inbox — same as your web widget and contact page.

### Custom theme & welcome

Match your app — **colors, radius, welcome text**. No app-store re-release.

### Reply from Telegram

Every message pings **Telegram**. Quote-reply lands in the user's in-app chat.

### Images, videos, files

Screenshots, screen recordings, logs — **synced into your inbox**.

### Online status & offline form

Online: live chat. Offline: **lead form** — same thread resumes on return.

### Custom user tags

Pass **user\_id, email, tags** — same user across sessions and devices.

### Read receipts + recall

Two-way **read receipts**. **Recall** mistyped messages either side.

◈ CATCH THEM EARLY

### Catch users before they uninstall.

A star rating says **something's wrong** — not what. Knocket lets users tap Help and talk to a real human in 5 seconds. Retention grows because someone actually replied.

◈ WebView SDK

One integration · every platform

✓

◈ Attachments

Images · videos · files

✓

◈ user\_id passed through

Same user · same thread across devices

✓

◈ PLATFORM COVERAGE

## Four platforms.  
One WebView.

The Knocket chat runs in any WebView container — no extra native chat UI to maintain per platform.

PLATFORM CLOSE CHANNEL UNIFIED INBOX

**iOS _· WKWebView_** WKScriptMessageHandler ✓

**Android _· WebView_** addJavascriptInterface ✓

**React Native _· react-native-webview_** onMessage ✓

**Flutter _· webview\_flutter_** addJavaScriptChannel ✓

? MOBILE FAQS

## Frequently asked questions

Is this a native SDK or WebView?

It's a **WebView SDK** — the Knocket chat runs inside a `WKWebView` (iOS) / `WebView` (Android) / `react-native-webview` / `webview_flutter`. One integration, every platform.

Can I customize the look?

Yes — colors, corner radius, welcome message, and online-status style are all configured from the Knocket console. Changes apply live — no app-store re-release needed.

How do users send screenshots or logs?

The widget supports **image, video, and file attachments**. Users can attach anything from their device. Attachments sync to your unified inbox and to the Telegram side.

Can I identify who's writing in?

Yes. Pass `userId`, email, and custom tags in the WebView URL. Every message in your inbox is tied to that identity, and continues across sessions and devices.

What happens when I'm offline?

Users see an **offline form** — they leave a message + email or phone. When you're back, you reply and the thread continues where it left off.

Read receipts and message recall?

Yes. Two-way **read receipts** — you see when the user has read your reply, and vice versa. Message **recall** works both directions — mistyped a reply? Recall it before they read it.

Data residency / compliance?

Powered by Tencent Cloud RTC — ISO 27001, ISO 27018, CSA STAR, DNV certified. Data region controls in the console.

◐ SHIP IT · IN-APP CHAT

## Talk to your users  
inside the app.

Ship an update. Catch feedback before churn.

[Start Free](https://knocket.trtc.io/register/)

Free · No card · WebView on any platform

KNOCK KNOCK
