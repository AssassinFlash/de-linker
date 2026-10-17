<!-- source: https://help.shopify.com/en/manual/inbox/agent-persona
     loadedTime(UTC): 2026-10-17T05:45:58.178Z
     httpStatus: 200
     apifyRun: OMFaxlpG6yfbQwyQN (wcc-b5) -->

Shopify Help Center | Configuring your Inbox agent persona

[

Help

](https://help.shopify.com/en)

[

Log in

](https://help.shopify.com/en/user/login?returnTo=%2Fen%2Fmanual%2Finbox%2Fagent-persona)

Contents

[Home](https://help.shopify.com/en)

[Shopify Inbox](https://help.shopify.com/en/manual/inbox)

# Configuring your Inbox agent persona

Activating the Inbox agent creates a default persona profile based on your store content. You can review, edit, and test this persona before or after you start using the Inbox agent.

Use the persona to define how your Inbox agent communicates, including its tone, wording, personality, and service style. Add facts to your product catalog, store policies, published storefront content, or the [Shopify Knowledge Base](https://help.shopify.com/en/manual/promoting-marketing/knowledge-base/managing-faqs) app so that the Inbox agent can use them in answers.

## On this page

*   [Choose where to add information](https://help.shopify.com/en/manual/inbox/agent-persona#where-to-add-information)
*   [Inbox agent persona settings](https://help.shopify.com/en/manual/inbox/agent-persona#persona-settings)
*   [Data sources](https://help.shopify.com/en/manual/inbox/agent-persona#data-sources)
*   [Chat greeting](https://help.shopify.com/en/manual/inbox/agent-persona#greeting)
*   [Safety limits](https://help.shopify.com/en/manual/inbox/agent-persona#safety-limits)
*   [Edit your Inbox agent persona](https://help.shopify.com/en/manual/inbox/agent-persona#edit-persona)

## Choose where to add information

Add information in the place that matches how the Inbox agent should use it:

*   **Persona**: Define how the agent communicates. For example, ask it to use a warm and concise tone, acknowledge frustration before offering a solution, or avoid pressuring customers to buy.
*   **Store content and Knowledge Base**: Add facts that the agent should use in answers. This includes return terms, shipping rates and thresholds, discounts, support contact details, business hours, response times, sizing information, and product specifications. Update the relevant store source when one already exists. Otherwise, [add a Knowledge Base FAQ](https://help.shopify.com/en/manual/promoting-marketing/knowledge-base/managing-faqs#add-new-faq).
*   **Inbox settings**: Configure staff handoff, staff availability, customer sign-in, and the chat greeting in the relevant Inbox settings. A persona can't override Inbox settings or built-in safety behavior.

Don't use the persona to force Inbox behavior, such as preventing all staff handoffs, requiring a product recommendation in every reply, or routing every conversation to one contact. Instructions that conflict with Inbox settings or built-in safety behavior might not be followed.

## Inbox agent persona settings

Your Inbox agent persona can include the following types of guidance:

*   **Tone and personality**: Describe how your Inbox agent should sound and interact with customers, such as casual, professional, enthusiastic, warm, or concise.
*   **Service style**: Describe how your Inbox agent should handle customer requests, such as acknowledging frustration before offering a solution or avoiding pressure to buy. Service-style preferences don't replace store facts or override Inbox settings and built-in safety behavior.

## Data sources

The Inbox agent answers customer questions by using your product catalog, store policies, Knowledge Base facts and files, and published storefront content such as pages, blog posts, sizing guides, and product care guides. For a specific product in your store catalog, the Inbox agent can also use cited web search for qualitative reviews, feedback, ratings, or social proof. It uses your store sources, not web search, for product facts, care instructions, usage ideas, and styling guidance. The Inbox agent bases product recommendations on your store catalog only.

Store facts added only to the persona aren't treated as source information and might not be used consistently. Add or update the fact in the relevant store source so that the Inbox agent can use current information in its answers.

Customers can chat with the Inbox agent without signing in, because your [customer sign-in setting](https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/settings#customer-sign-in) applies only to messages sent to your staff. Features that use a customer's own account data are separate from that setting. Order lookup always requires the customer to sign in.

If a customer asks the Inbox agent to review an order, then they're prompted to sign in first. The **Track my order** option, which uses an order number and email, is available as an instant answer regardless of whether your Inbox agent is active.

## Chat greeting

Your chat greeting isn't set as part of the Inbox agent persona. For online store chat, you manage the greeting message in the theme editor. If you leave it blank, then an automatic greeting is displayed based on your store name and whether the customer is signed in.

## Safety limits

The Inbox agent includes safety limits that help keep conversations on topic, within appropriate boundaries, and protected against misuse.

### Conversation limits

The Inbox agent has the following conversation limits:

*   In a single conversation, the Inbox agent responds to up to 100 messages for customers who aren't signed in and up to 1,000 messages for signed-in customers.
*   Each customer can start up to 50 conversations per day with your store.

When the Inbox agent reaches a limit, it stops responding and hands off that conversation to your staff if staff handoff is available. If staff handoff isn't available, then the customer receives your store's sender email address and can contact you by email. Your Inbox isn't affected by the Inbox agent's limits, and your staff can continue the conversation directly.

### Built-in safety features

The Inbox agent includes built-in safety features that don't require any configuration:

*   **Rate limiting**: Rapid-fire messages from the same visitor are throttled to deter misuse.
*   **Bot and spam detection**: Automated checks help filter out bot traffic and spam.
*   **Blocked senders and IP addresses**: Conversations detected as spam or from blocked senders are automatically filtered.

### Staff handoff

If the Inbox agent can't answer a question, or a customer asks to speak with a person, then the conversation can be handed off to your staff. To learn more, refer to [Managing customer conversations](https://help.shopify.com/en/manual/inbox/conversations#handoff).

## Edit your Inbox agent persona

You can update your Inbox agent persona at any time.

#### Steps:

1.  From your Shopify admin, go to **Sales channels** > [**Inbox**](https://admin.shopify.com/apps/shopify-inbox).
    
2.  In the **Persona** section, click **Edit**.
    
3.  Edit the Inbox agent persona. Add store facts to the relevant store source or a [Knowledge Base FAQ](https://help.shopify.com/en/manual/promoting-marketing/knowledge-base/managing-faqs#add-new-faq) rather than to the persona.
    
4.  Click **Save**.
    

#### Sidekick

You can [ask Sidekick](https://admin.shopify.com/sidekick) to refine your persona: click **Refine with Sidekick** beside it, then describe the tone, wording, or service style that you want. Sidekick drafts the change for you to review and save.

When you [train your Inbox agent](https://help.shopify.com/en/manual/inbox/training-your-agent) by rating responses, the training system can generate updated persona suggestions. You can review and compare these suggestions with your current persona before accepting them.

Leave feedback

Chat with a human

Reject allAccept cookies

We and our partners use cookies and other technologies to personalize your experience, show you ads, and perform analytics. See Our [Cookie Policy](https://www.shopify.com/legal/cookies).