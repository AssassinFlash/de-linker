<!-- source: https://openai.com/index/buy-it-in-chatgpt/
     loadedTime(UTC): 2026-10-17T05:42:24.265Z
     httpStatus: 200
     apifyRun: nhYEE2N8zACk3aduc (wcc-b3) -->

# Buy it in ChatGPT: Instant Checkout and the Agentic Commerce Protocol

More than 700 million people turn to ChatGPT each week for help with everyday tasks, including finding products they love. Starting today, we’re taking the first steps toward ChatGPT helping people buy them too—beginning with Instant Checkout, powered by the Agentic Commerce Protocol, built with Stripe.

U.S. ChatGPT Plus, Pro, and Free users can now buy directly from U.S. Etsy sellers right in chat, with over a million Shopify merchants, like Glossier, SKIMS, Spanx and Vuori, coming soon. Today, Instant Checkout supports single-item purchases. Next, we’ll add multi-item carts and expand merchants and regions.

We’re also [open-sourcing⁠(opens in a new window)](https://agenticcommerce.dev/) the technology that powers Instant Checkout, the Agentic Commerce Protocol, so that more merchants and developers can begin building their integrations. The Agentic Commerce Protocol is an open standard for AI commerce that lets AI agents, people, and businesses work together to complete purchases. We co-developed it with [Stripe⁠(opens in a new window)](https://docs.stripe.com/agentic-commerce) and leading merchant partners to be powerful, secure, and easy to adopt.

This marks the next step in agentic commerce, where ChatGPT doesn’t just help you find what to buy, it also helps you buy it. For shoppers, it’s seamless: go from chat to checkout in just a few taps. For sellers, it’s a new way to reach hundreds of millions of people while keeping full control of their payments, systems, and customer relationships.

We’re making this protocol and [our documentation⁠(opens in a new window)](https://developers.openai.com/commerce) available today so interested merchants and developers can begin building integrations. When you’re ready to make your products available for purchase through ChatGPT, you can [apply here⁠(opens in a new window)](https://chatgpt.com/merchants).

## How Instant Checkout works

When someone asks a shopping question—“best running shoes under $100” or “gifts for a ceramics lover” — ChatGPT shows the most relevant products from across the web. Product results are organic and unsponsored, ranked purely on relevance to the user.

If a product supports Instant Checkout, users can tap “Buy,” confirm their order, shipping, and payment details, and complete the purchase without ever leaving the chat. Existing ChatGPT subscribers can pay with their card on file, or other card and express payment options.

Orders, payments, and fulfillment are handled by the merchant using their existing systems. ChatGPT simply acts as the user’s AI agent—securely passing information between user and merchant, just like a digital personal shopper would.

Merchants pay a small fee on completed purchases, but the service is free for users, doesn’t affect their prices, and doesn’t influence ChatGPT’s product results. Instant Checkout items are not preferred in product results. When ranking multiple merchants that sell the same product, ChatGPT considers factors like availability, price, quality, whether a merchant is the primary seller, and whether Instant Checkout is enabled, to optimize the user experience.

## The Agentic Commerce Protocol

At the core of this experience is the [Agentic Commerce Protocol⁠(opens in a new window)](https://developers.openai.com/commerce) which provides the language that lets AI agents and businesses work together to complete a purchase for a user.

We built the Agentic Commerce Protocol with Stripe and leading merchants to:

*   Work across platforms, payment processors, and business types. 
    
*   Integrate quickly without changing their backend systems.
    
*   Keep merchants in control of the customer relationship as the merchant of record across the purchase journey–from fulfillment and returns to support and communication.
    

When someone places an order, ChatGPT sends the necessary details to the merchant’s backend using Agentic Commerce Protocol. The merchant accepts or declines the order, processes the payment via their existing provider, and handles fulfillment and customer support exactly as they do today.

If a merchant already processes payments with [Stripe⁠(opens in a new window)](https://docs.stripe.com/agentic-commerce), they can enable agentic payments in as little as one line of code. If they use another payment processor, they can still participate in Instant Checkout and accept agentic payments either by using Stripe’s new [Shared Payment Token API⁠(opens in a new window)](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens) or adopting the Delegated Payments Spec in the Agentic Commerce Protocol—all without changing their existing payment processor.

## Built for trust

We believe agentic commerce should be built for trust. In this early stage of the AI commerce future:

*   Users stay in control — they explicitly confirm each step before any action is taken.
    
*   Payment is secure — encrypted payment tokens are only authorized for specific amounts and specific merchants with the user’s permission.
    
*   Data sharing is minimal — only the information required to complete the order is shared with the merchant, with the user’s permission.
    

### Partner perspectives

> "Stripe is building the economic infrastructure for AI. That means re-architecting today’s commerce systems and creating new AI-powered experiences for billions of people. We’re proud to power Instant Checkout in ChatGPT and co-develop the Agentic Commerce Protocol to help businesses and AI platforms build the future of commerce."

– Will Gaybrick, President, Technology and Business, Stripe

## Just the start

This launch is just the beginning. As AI becomes a key interface for how people discover, decide, and buy, the Agentic Commerce Protocol provides a foundation that connects people and businesses for the next era of commerce.