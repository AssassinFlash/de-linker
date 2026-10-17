<!-- source: https://www.intercom.com/help/en/articles/8205718-fin-ai-agent-outcomes
     loadedTime(UTC): 2026-10-17T05:37:05.446Z
     httpStatus: 200
     apifyRun: RprqhMkO9aiKCS8l1 (wcc-b1) -->

# Fin AI Agent outcomes | Intercom Help

What Fin AI Agent outcomes are and how they will be measured and charged.

Written by Beth-Ann Sher

Updated over 3 weeks ago

All plans include access to [Fin AI Agent](https://www.intercom.com/help/en/articles/7120684-fin-intercom-s-latest-generation-of-ai-agent). An outcome is counted when Fin successfully delivers value. We'll go into what this means and how it's measured below.

## Outcome pricing

You're only charged for **one outcome per conversation**, even if Fin takes multiple actions.

|     |     |     |
| --- | --- | --- |
| **Price per outcome** | **Type of outcome** | **Definition of outcome** |
| **$0.99** | Resolution | No further help is requested after the last Al answer. |
| **$0.99** | Procedure handoff | Fin successfully executes a Procedure that you've configured to end in a handoff to a human or a workflow. |
| **$0.99** | Disqualification | Fin determines that a prospect doesn't match your qualification criteria and disqualifies them accordingly. |
| **$9.99** | Qualification | Fin matches a prospect to the qualification criteria you defined and routes them accordingly. |
| **$0.99** | Self-serve routing | Fin matches a prospect to a routing outcome marked as Self-serve — for example, directing them to sign up for a trial. Billed at the lower rate, separate from full-rate qualifications. |

Fin is available on every plan, but you won't be billed for Fin if you’re not using it. You can also [set usage reminders and hard limits](https://www.intercom.com/help/en/articles/8991894-how-to-make-the-most-of-your-usage-dashboard#h_36badc7757) to ensure you’re happy with how many resolutions Fin is able to provide.

## Resolution definition

A resolution is a type of outcome that is counted when, following Fin’s last answer in a conversation, the customer either confirms the answer was satisfactory (confirmed resolution), or exits the conversation without requesting further assistance (assumed resolution).

Customers can confirm a resolution by:

Customers can request further assistance by:

## Procedure handoff definition

A Procedure handoff is a type of outcome where Fin successfully executes a Procedure that you've configured to end in a handoff to a human or a workflow.

You'll only be charged **once per conversation**, even if Fin resolves multiple questions or runs multiple Procedures.

## Disqualification definition

A disqualification can happen only when you've [configured Fin for Sales](https://intercom.help/intercom/en/articles/13927072-fin-for-sales-explained) and it determines that a prospect doesn't match your qualification criteria and disqualifies them accordingly.

## Qualification definition

A qualification can happen only when you've [configured Fin for Sales](https://intercom.help/intercom/en/articles/13927072-fin-for-sales-explained) and it matches a prospect to the qualification criteria you defined and routes them accordingly.

## Self-serve routing definition

A self-serve routing outcome is counted when Fin matches a prospect to a routing outcome marked as **Self-serve** using the Outcome type toggle in your playbook.

A qualification is counted when:

These qualification conditions are set up within your routing outcomes, such as:

## Outcomes billing

This is how you will be charged for outcomes:

## How billable outcomes are determined

To understand what you will be charged for it helps to look at what caused the conversation to be passed over to a teammate:

The table below outlines common conversation scenarios with Fin and whether they are billed as Fin outcomes:

|     |     |     |
| --- | --- | --- |
| **Scenario** | **Status** | **Billed** |
| Fin gives an AI answer and no further help is requested. | Resolution | Yes |
| A customer asks "What running shoes do you have under $100?" Fin recommends products from your synced Shopify catalogue. The customer browses the suggestions and doesn't express dissatisfaction. | Resolution | Yes |
| A customer asks for help finding a gift. Fin recommends products, the customer clicks through product cards, adds items to their cart, and proceeds to checkout. The downstream actions (product card clicks, cart creation, checkout) don't incur extra charges — it's still one resolution. | Resolution | Yes |
| Fin handoffs to a human because of instructions you added in [Procedure-specific guidance](https://www.intercom.com/help/en/articles/13449439-building-fin-procedures#h_29d51837fb). | Procedure Handoff | Yes |
| Fin uses a configured @handoff to a workflow. | Procedure Handoff | Yes |
| Fin uses a configured @handoff to a team or teammate. | Procedure Handoff | Yes |
| Fin matches a prospect to the qualification criteria you defined and routes them to a team or teammate. | Qualification | Yes |
| Fin determines that a prospect doesn't match your qualification criteria. | Disqualification | Yes |
| Fin qualifies a lead and escalates it to a support team or teammate. | Qualification | Yes |
| Fin escalates due to workspace level guidance or escalation rules. | Escalated | No  |
| Procedure Failure: A technical error or logic issue prevents a Procedure from finishing. | Escalated | No  |
| Standard workflow: Fin will hand over if it's unable to resolve the customer's question, a customer asks for human support, or an escalation rule or guidance applies. | Escalated | No  |
| Fin determines a conversation is spam and routes it to the Spam view in your Inbox. | Spam | No  |
| Fin sends an outbound message and the customer clicks/opens it but does not respond. | Pending | No  |
| Fin did not give an AI Answer or has not qualified the customer and the customer abandons the conversation. | Abandoned | No  |
| Fin asks a clarifying question, the customer doesn't respond, and the conversation auto-closes due to inactivity. No resolution state is recorded. | Abandoned — Not an outcome | No  |

## FAQs

* * *

💡**Tip**

**Need more help?** Get support from our [Community Forum](https://community.intercom.com/?utm_source=ii-help-center&utm_medium=internal)  
Find answers and get help from Intercom Support and Community Experts

* * *

## Related Articles

*   [Fin AI Agent reporting](https://www.intercom.com/help/en/articles/7837533-fin-ai-agent-reporting)
*   [Deploy Fin AI Agent over chat](https://www.intercom.com/help/en/articles/8286630-deploy-fin-ai-agent-over-chat)
*   [Deploy Fin AI Agent over email](https://www.intercom.com/help/en/articles/9356221-deploy-fin-ai-agent-over-email)
*   [Fin AI Agent Automation Rate](https://www.intercom.com/help/en/articles/13533623-fin-ai-agent-automation-rate)
*   [How to train Fin for Sales](https://www.intercom.com/help/en/articles/13927077-how-to-train-fin-for-sales)