<!-- source: https://help.shopify.com/en/manual/inbox/assigning-your-ai-staff-member
     loadedTime(UTC): 2026-10-17T05:31:01.420Z
     httpStatus: 200
     apifyRun: TrRwuJPIOXuAAY33r (wcc-known-1) -->

# Shopify Help Center | Assigning your Inbox agent to conversations

Shopify Inbox includes an Inbox agent that can chat with customers who visit your online store. You can choose whether to activate the Inbox agent and which types of conversations it handles. Until you turn on the Inbox agent, your conversations stay with your staff. You can switch between assignment modes at any time.

The Inbox agent uses your store's product catalog, store policies, and page content to respond to customer questions in real time through the chat widget on your online store. The Inbox agent can answer product questions, make personalized recommendations, help with order lookups, and add items to a customer's cart.

Review the following details about how the Inbox agent works:

*   It uses information from your store, including product catalog, policies, pages, and Knowledge Base. It can also cite web search results as a secondary source for product-adjacent content, but doesn't represent generic web results as if they were your store's knowledge.
*   It handles customer data independently for each store and doesn't share customer information between stores.
*   It only operates within your online store's chat widget.

Review the following considerations before you activate the Inbox agent:

*   The Inbox agent generates responses using information from your products, store policies, and pages. Keeping this content accurate and complete improves the quality of responses.
*   The Inbox agent handles common shopping questions. For complex or sensitive inquiries, the conversation can be handed off to your staff. When a customer asks to speak with a person, or a conversation needs staff attention, the following happens:
    *   If staff handoff is available, then the conversation moves to your staff. The AI's prior context carries over to your staff.
    *   If staff aren't available, then the Inbox agent shares your store's sender email address so the customer can email you. To learn more, refer to [Managing customer conversations](https://help.shopify.com/en/manual/inbox/conversations#handoff).

You can choose when the Inbox agent handles conversations by selecting one of three assignment modes. Your store's assignment mode determines whether the Inbox agent responds to customers automatically, only during specific hours, or not at all.

The following assignment modes are available:

|     |     |
| --- | --- |Inbox agent assignment modes, and how each one decides whether the agent or your staff answers a customer.
| Assignment mode | Description |
| --- | --- |
| **All conversations** | The Inbox agent is automatically assigned to all new conversations. |
| **Only when your staff is unavailable** | The Inbox agent handles conversations only outside your set [availability hours](https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/availability-and-first-reply). During your availability hours, customers can chat with your staff. |
| **Never** | The Inbox agent is turned off and isn't assigned to any conversations. Only your staff respond to customers. This is the default setting for stores that had Inbox installed before the Inbox agent was available. |

You can switch between assignment modes at any time, and the assignment switch doesn't require reconfiguring your Inbox agent.

When a customer opens the chat widget on your online store and the Inbox agent is assigned, the Inbox agent is available to help answer their questions.

The Inbox agent can help customers with the following tasks:

*   **Product questions**: Answer questions about product details, availability, and pricing.
*   **Product recommendations**: Suggest products based on what the customer is looking for, and on preferences such as sizes and purchase history when those details are available. Customers with an active Shop session can get personalized recommendations, even if they haven't signed in to your store.
*   **Order lookups**: Help customers check the status of an existing order. The customer is prompted to sign in before the Inbox agent shares order information.
*   **Add to cart**: Add recommended products directly to the customer's cart.
*   **Replies in the customer's language**: The Inbox agent replies in the language that the customer uses in the chat. Product titles and other catalog details might be displayed in your store's language.

Customers can start and continue chatting with the Inbox agent without signing in. If the conversation moves to your staff, and you require customer sign-in, then the customer must sign in first. For details, refer to the [customer sign-in setting](https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/settings#customer-sign-in).

When you activate the Inbox agent, it uses your store's product data, policies, and pages to respond to customer questions. Customer chat communications are processed to generate responses and to improve the quality of the Inbox agent over time.

Customers receive a notice that the chat is powered by Shopify and that they're chatting with AI. This notice is displayed automatically and can't be removed or customized.

### How data is handled

Review these details about how the Inbox agent handles data:

*   The Inbox agent uses your store's existing product catalog, policies, and page content to answer customer questions. No additional data sharing is required to activate the feature.
*   The Inbox agent can use customer signals such as preferences, sizes, and purchase history to personalize product recommendations when those signals are available. It might mention the detail that shaped a recommendation, such as a saved size or a product that the customer bought from your store.
*   The Inbox agent can use preferences that customers share during a chat to improve responses in that conversation.
*   Customer chat communications are processed in real time to generate responses. Conversation history is accessible from your Inbox conversations.
*   The Inbox agent handles customer data independently for each store and doesn't share customer information or conversation data across different stores.

### Updating your privacy policy

If you use the latest version of the Shopify template privacy policy, then the Shopify template includes disclosures about Shopify's role in processing customer data for AI-assisted chat. Review your privacy policy to confirm that it accurately describes your business, data practices, and legal obligations.

If you use a custom privacy policy, then review it before you activate the Inbox agent. Your custom privacy policy should include the following information:

*   A disclosure that you use Shopify to power AI-assisted chat on your online store.
*   A disclosure that Shopify processes customer data, including chat communications, to generate responses and to improve the quality of the Inbox agent over time.

You can change when the Inbox agent is assigned to conversations from your Inbox settings.

#### Steps:

1.  From your Shopify admin, go to **Sales channels** > [**Inbox**](https://admin.shopify.com/apps/shopify-inbox).
    
2.  In the **Inbox agent** section, turn the Inbox agent on or off:
    
    *   To stop the Inbox agent from handling any conversations, turn it off. Only your staff respond to customers.
    *   To have the Inbox agent handle conversations, turn it on.
3.  If you turned the Inbox agent on, then choose an assignment option:
    
    *   **All conversations**: The Inbox agent handles all new conversations.
    *   **Only when your staff is unavailable**: The Inbox agent handles conversations only outside the availability hours that you set.

Your assignment change takes effect immediately for new conversations.