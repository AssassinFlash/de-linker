<!-- source: https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents
     loadedTime(UTC): 2026-10-17T05:44:03.359Z
     httpStatus: 200
     apifyRun: 441FEIMGdGRPUOGLw (wcc-b4-lists) -->

Routing messaging tickets and notifying agents – Zendesk help

Recent searches

* * *

No recent searches

## Account details

Sign in to see your account details at a glance

[Sign inSign in](https://support.zendesk.com/hc/en-us/signin?return_to=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408829019162-Routing-messaging-tickets-and-notifying-agents)

* * *

FollowFollow

Related articlesRelated articles

* * *

*   [](https://www.facebook.com/share.php?title=Routing+messaging+tickets+and+notifying+agents&u=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408829019162-Routing-messaging-tickets-and-notifying-agents)
*   [](https://twitter.com/share?lang=en&text=Routing+messaging+tickets+and+notifying+agents&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408829019162-Routing-messaging-tickets-and-notifying-agents)
*   [](https://www.linkedin.com/shareArticle?mini=true&source=Zendesk+Support&title=Routing+messaging+tickets+and+notifying+agents&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408829019162-Routing-messaging-tickets-and-notifying-agents)

* * *

# Routing messaging tickets and notifying agents

[](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

[Aimee Spanier](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

Zendesk Documentation Team

Edited Jul 30, 2026

In Zendesk's messaging for Web Widget, mobile SDKs, and social channels, when a customer requests assistance from a live agent during a conversation, a ticket is created, and agents are notified that a request has been received.

[What's my plan?](https://support.zendesk.com/hc/en-us/articles/5411234991258-plan)

|     |     |
| --- | --- |
| **All Suites** | Team, Growth, Professional, Enterprise, or Enterprise Plus |

Verified AI summary ◀▼

Learn how to route messaging tickets and notify agents effectively. Use ticket triggers and chat routing rules to direct tickets to specific agents or groups. Alternatively, employ omnichannel routing for a more comprehensive approach. Customize views to organize messaging tickets, ensuring agents can easily locate and manage them. Note that skills-based routing isn't available for messaging tickets.

In Zendesk's messaging for Web Widget, mobile SDKs, and social channels, when a customer requests assistance from a live agent during a conversation, a ticket is created, and agents are notified that a request has been received.

You can use ticket triggers to route the associated ticket to specific agents or groups, then use the chat routing rules defined in your Chat dashboard to determine which of those agents or groups are notified that a new conversation is waiting in the queue. You can create views to organize tickets submitted through a messaging channel.

You can also route messaging tickets using omnichannel routing, instead of using ticket triggers and chat routing rules as described in this article. See [About omnichannel routing](https://support.zendesk.com/hc/en-us/articles/4409149119514).

Note: Currently, skills-based routing is not available for messaging conversations or tickets.

This article includes the following topics:

*   [Overview of the routing flow in messaging](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents#topic_jsz_qbq_mpb)
*   [Understanding what happens to messaging requests by default](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents#topic_lg5_qbq_mpb)
*   [Using ticket triggers to route messaging tickets](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents#topic_tn4_qbq_mpb)
*   [Using Chat routing rules to notify agents](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents#topic_d33_qbq_mpb)
*   [Using omnichannel routing to route messaging tickets](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents#topic_yhw_s4y_bvb)
*   [Routing messaging tickets to a view](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents#topic_j41_gr2_npb)

Related articles:

*   [Recipe: Replicating pre-chat group routing in the messaging Web Widget](https://support.zendesk.com/hc/en-us/articles/11072737869850)

## Overview of the routing flow in messaging

Before jumping into a discussion about routing incoming messaging requests, it’s important to understand the elements involved and where they fall in a messaging flow.

### Elements directly (and indirectly) controlling messaging ticket routing

There are three elements that directly control how a messaging ticket is routed:

*   **Ticket triggers** are applied to the tickets created when a messaging conversation is passed to an agent. They perform much like triggers applied to tickets created via other channels, but you may need to use them in other ways for messaging tickets.
*   **Chat routing rules** define how agents are informed that there is a messaging ticket waiting in the queue. Specific agents or groups can be notified, or all agents can see a broadcast notification. If a Support trigger has routed the ticket to a specific agent or group of agents, only agents assigned to the ticket will receive a notification. Agents must click the notification to enter the conversation. See [Setting up notification routing for live chat and messaging](https://support.zendesk.com/hc/en-us/articles/5020833543450) for more information.
*   **Omnichannel routing** allows you to direct tickets from multiple channels, including messaging, to team members based on their availability and capacity. On Professional and Enterprise plans, you can also route tickets based on priority and skills. See [About omnichannel routing](https://support.zendesk.com/hc/en-us/articles/4409149119514) for more information.

Additionally, there are elements that do not directly control ticket routing, but can be referenced by ticket triggers, or can otherwise impact how a ticket is received by agents:

*   **Default messaging responses** can include the collection of customer details, which also uses custom ticket fields that can then be referenced in ticket triggers. See [Working with the default messaging response](https://support.zendesk.com/hc/en-us/articles/4500737327258#topic_kzg_ync_gnb).
*   **Messaging triggers** can fire when a conversation is passed to a live agent (via an agent transfer event), or when the customer enters a comment in a messaging conversation with a live agent. An agent does not have to be _actively_ participating in the conversation for these triggers to fire, but the conversation must have been passed from the AI agent to live agent control. Messaging triggers are often used for auto responders, which can inform your customers that live agent assistance is not currently available. See [Understanding messaging triggers](https://support.zendesk.com/hc/en-us/articles/5973077601562).
*   **Transfer to agent events (for customers who had any drafted or published AI agents as of February 2, 2025)** (Web Widget and mobile SDKs only) in any AI agent configuration will hand off the conversation to a live agent. This creates a ticket associated with that conversation. These events can be preceded by the Ask for details step, which uses custom ticket fields to collect information from customers that can be used when creating ticket triggers. For more information on these events, see [Understanding the step types for AI agent answers (Legacy)](https://support.zendesk.com/hc/en-us/articles/4408836323738).

### Sample messaging flow

The elements described above influence the routing workflow at different points in the life cycle of a messaging conversation. It's important to know when they come into play so you can configure your routing workflow with confidence. In the example below, a messaging conversation goes through a basic messaging workflow, and the elements influencing the routing are highlighted in bold.

1.  Customer begins a messaging conversation via your messaging channel. For Web Widget and mobile SDKs, the AI agent is the first responder for the conversation and interacts with the customer based on the [AI agent's standard responses](https://support.zendesk.com/hc/en-us/articles/8774095741466).
2.  The customer indicates they are unable to self-solve their issue in an **agent transfer event** and requests help from a live agent. The AI agent is removed as the first responder for the conversation.
3.  A ticket associated with the conversation is created. **Any chat messaging triggers for _when a visitor requests a chat_ fire, and triggers with the condition_Ticket | is | Created_ fire**.
4.  An agent becomes the first responder for the conversation.
5.  Customer adds a comment to the conversation. **Any messaging triggers for _when a message is sent_ fire**.
6.  The associated ticket is added to the queue. **Messaging routing rules fire, alerting agents to the presence of a new conversation.**
7.  An available agent accepts the ticket and enters the conversation based on your selected routing method OR, if no agent is available, the ticket remains unassigned and can be found in the ticket views according to your view configurations.
8.  Once the customer’s issue is resolved, the ticket is marked Solved.
9.  After a set period of time, an automation updates the ticket status from Solved to Closed, which ends the associated conversation as well. See [Solving a ticket and understanding how it is closed](https://support.zendesk.com/hc/en-us/articles/4408832151834#topic_myd_gdx_qf) for more information.

## Understanding what happens to messaging requests by default

Using the out-of-the-box configurations for your [AI agent](https://support.zendesk.com/hc/en-us/articles/4408824263578#topic_hmy_2yr_2nb), [ticket triggers](https://support.zendesk.com/hc/en-us/articles/4408828984346), [messaging triggers](https://support.zendesk.com/hc/en-us/articles/5973077601562), and [messaging notification routing](https://support.zendesk.com/hc/en-us/articles/5020833543450), incoming requests for agent assistance from the messaging channel have a simple, functional routing process.

*   Customers are handed off from the AI agent to the live agent, who picks up the conversation in the Agent Workspace. No information is collected through custom ticket fields.
*   Tickets are not assigned to any agent or group, and appear in two default views, **Unassigned tickets** and **All unsolved tickets**.
*   A notification is broadcast to all agents, informing them that a request has been received.
*   If a ticket request remains unassigned in the queue for more than 10 minutes, it is moved to the **Unassigned tickets** view.

## Using ticket triggers to route messaging tickets

Ticket triggers allow you to automatically route tickets to specific agents or groups. In messaging, you can use the following data as trigger conditions to automatically route messaging tickets to specific agents or groups:

*   **Channel | is | Messaging** set as the ticket submission channel, to create routing rules that apply only to messaging tickets. If you do not specify messaging as the channel, all incoming tickets will have this trigger applied. Any triggers with other channels specified (email, for example) that do not include messaging will not fire.
*   **Data collected via custom ticket fields (for customers who had any drafted or published AI agents as of February 2, 2025)** as part of an [Ask for details event](https://support.zendesk.com/hc/en-us/articles/4408836323738#topic_i5r_grz_n5b) created in the legacy bot builder, or as part of the [default messaging response](https://support.zendesk.com/hc/en-us/articles/4500737327258#topic_kzg_ync_gnb). This data can include customer location, the nature of their issue, or any information you want to gather.

There are three main parts to setting up this routing flow:

*   Creating a custom ticket field
*   Adding the custom ticket field to your conversation flow
*   Building a trigger to route your ticket

## Using Chat routing rules to notify agents

Chat routing rules determine which agents, or groups of agents, are notified that a messaging conversation has been received. Routing rules are set at the account level, and applied to all brands associated with your account.

Important: Messaging users _must_ make sure all Chat departments are enabled for Chat for notification routing rules to work. See [Creating and editing a Chat department](https://support.zendesk.com/hc/en-us/articles/4408894143898#topic_mfr_wyk_4fb) for information on updating department settings.

There are two basic methods for notifying agents of incoming messaging requests:

*   **Broadcast**, where all agents are notified of all incoming requests, and agents self-assign these requests through the Agent Workspace. _This routing option is enabled by default_.
*   **Assigned**, where conversations are passed to specific online agents or groups.

One of these routing rules is applied at all times -- you cannot opt out of routing rule selection.

Chat routing rules are applied _after_ any ticket triggers fire. If you are using a support trigger to route incoming messaging tickets to specific agents, notifications are only sent to agents that are eligible to accept the ticket.

*   **If no specific agent or group is assigned the ticket**, a broadcast notification will be received by all messaging agents, and an assigned notification will be received by the next eligible agent, [according to the assigned routing rules](https://support.zendesk.com/hc/en-us/articles/5020833543450#topic_u3c_rrn_mpb).
*   **If a specific agent or group is assigned the ticket**, a broadcast notification will be received by all messaging agents specified in the trigger, and an assigned notification will be received for the specified agent, or the next eligible agent in the group, [according to the assigned routing rules](https://support.zendesk.com/hc/en-us/articles/5020833543450#topic_u3c_rrn_mpb).

Note: Any chat routing settings configured _before_ enabling messaging are automatically applied to messaging routing.

Other chat routing settings such as hybrid assignment and reassignment are _supported_.

Skills-based routing is _not supported_ for messaging conversations.

For information on configuring basic routing options, see [Setting up automatic notification routing](https://support.zendesk.com/hc/en-us/articles/5020833543450).

## Using omnichannel routing to route messaging tickets

With omnichannel routing, you can direct tickets from email, calls, and messaging to agents based on their availability and capacity. On Professional and Enterprise plans, tickets can also be routed based on priority and skills. This means your most important tickets are assigned to the agents who are best equipped and available to work on them.

Before using omnichannel routing for messaging, consider the following:

*   You can't activate omnichannel routing if you're using live chat.
*   The Zendesk Agent Workspace must be activated to use omnichannel routing.
*   When using omnichannel routing, tickets originating from a [variety of native and social messaging channels](https://support.zendesk.com/hc/en-us/articles/4409149119514#topic_psx_hxk_3yb) are routed as "messaging" tickets.
*   Omnichannel routing can be used in combination with ticket triggers to route messaging tickets.
*   Broadcast and hybrid modes for messaging aren't supported.
*   On Professional and Enterprise plans, you can [configure how inactive messages are evaluated](https://support.zendesk.com/hc/en-us/articles/4828787357210) for [agent capacity](https://support.zendesk.com/hc/en-us/articles/4776409839770).
*   See [Requirements and limitations of omnichannel routing](https://support.zendesk.com/hc/en-us/articles/4409149119514#topic_zlk_c3p_m5b) for a complete list of requirements and limitations.

## Routing messaging tickets to a view

You can also route messaging tickets to a view, allowing admins and agents to easily locate tickets submitted through the messaging channel. The Chat routing rules will still apply to tickets routed to views. In the example screenshot below, the view is also restricted to a messaging-specific agent group.

* * *

1

20

* * *

## 20 comments

Date

Newest

[](https://support.zendesk.com/hc/en-us/profiles/6222110467994)

[Evan Woodbury](https://support.zendesk.com/hc/en-us/profiles/6222110467994)

Feb 23, 2026

Two product enhancement recommendations for messaging assignment:  

*   Enable broadcast assignment for messaging within Omnichannel routing so that customers don't need to wait while tickets try to assign to different agents who may not be available at that exact moment (but are stilled “available”). 
*   Provide a “Decline” button on messaging assignment notifications to quickly send the message to the next person before timeout

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/5305839195802)

[API Zendesk Wplay.co](https://support.zendesk.com/hc/en-us/profiles/5305839195802)

Aug 08, 2024

Is there a way to redirect users to a department from the API zendesk ?

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263169230770)

[Terry Hessey](https://support.zendesk.com/hc/en-us/profiles/1263169230770)

Jul 30, 2024

Hi there, I am looking for an answer to Shot Scope Support's [question](https://support.zendesk.com/hc/en-us/articles/4408829019162/comments/4408850181658) as I am in the same kind of situation. Our product does not have quick answers conducive to the use of Chat and I would like a ticket created from the  customer's message if they don't find the answer with the help of the bot.

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082110149)

[Dainne Kiara Lucena-Laxamana](https://support.zendesk.com/hc/en-us/profiles/1263082110149)

Jul 03, 2024

Hi [Christina](https://support.zendesk.com/hc/en-us/profiles/1900285603124-Christina)   
  
Not at the moment. But we do have a function wherein it would still get routed to your agents even if it's inactive along with your active tickets. Please see [Messaging activity routing](https://support.zendesk.com/hc/en-us/articles/4828787357210-Managing-your-omnichannel-routing-configuration#topic_glj_pmr_wbc)

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1900285603124)

[Christina](https://support.zendesk.com/hc/en-us/profiles/1900285603124)

Jul 01, 2024

Is there an answer to Haley's question?  
[https://support.zendesk.com/hc/en-us/articles/4408829019162/comments/5995860912026](https://support.zendesk.com/hc/en-us/articles/4408829019162/comments/5995860912026) 

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082316169)

[Rosie](https://support.zendesk.com/hc/en-us/profiles/1263082316169)

Jan 20, 2024

Hi Bobby,  
   
If you enabled your Omnichannel routing, you'll manage notification settings in the Admin Center. If no, then the messaging notification will be managed in your Chat dashboard and configure the notification based on your preferred option and routing rules. To learn more of the set up, see [Setting up notification routing for messaging](https://support.zendesk.com/hc/en-us/articles/5020833543450-Setting-up-notification-routing-for-messaging).  
   
Hope this helps. Thank you!   
   

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1265844704610)

[Bobby Koch](https://support.zendesk.com/hc/en-us/profiles/1265844704610)

Jan 19, 2024

I am still pretty confused here. I want to send notifications when a new messaging ticket is created. Do I have the option to use chat routing rules or omni-channel routing? Or do I use both?

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/4775886017946)

[Hayley Johnson](https://support.zendesk.com/hc/en-us/profiles/4775886017946)

Aug 03, 2023

Is it possible to turn this functionality off when using Omnichannel? 

### Inactive messages in omnichannel routing

An inactive messaging ticket (more than 10 minutes without a reply) is automatically assigned to an agent with spare capacity on a round robin basis. It won’t use up any of that capacity.

Once an agent comes online, assuming they are not at max capacity, they will be automatically assigned an inactive message from the queue without needing to accept it. If there are several inactive messages in the queue, then the first agent online in the group will be assigned them all. If more than one agent comes online at the same time, the inactive tickets are assigned starting with the agent who’s gone the longest without any messages.

2

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082195189)

[Joyce](https://support.zendesk.com/hc/en-us/profiles/1263082195189)

Jun 29, 2023

Hello Bobby,  
   
You can create a trigger and use the Organization name or Organization custom field as the condition to route messages from a specific organization to the respective group.   
   
Here's an example of trigger conditions and action:  
  
   
For more information, you can also visit the article [Recipe: Routing messaging tickets using Support triggers](https://support.zendesk.com/hc/en-us/articles/4408819011354#topic_urk_r2d_npb).  
   
Hope this helps!  

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1265844704610)

[Bobby Koch](https://support.zendesk.com/hc/en-us/profiles/1265844704610)

Jun 28, 2023

How can we utilize organizaiton data to route messages?

0

* * *

[Sign in](https://support.zendesk.com/hc/en-us/signin?return_to=/hc/en-us) to leave a comment.

*   [Previous](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents?page=0)
*   [1](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents?page=1)
*   [2](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents?page=2)
*   [Next](https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents?page=2)