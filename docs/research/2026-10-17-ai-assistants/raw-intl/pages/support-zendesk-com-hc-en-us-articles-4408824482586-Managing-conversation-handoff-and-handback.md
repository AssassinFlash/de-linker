<!-- source: https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback
     loadedTime(UTC): 2026-10-17T05:44:00.117Z
     httpStatus: 200
     apifyRun: 441FEIMGdGRPUOGLw (wcc-b4-lists) -->

Managing conversation handoff and handback – Zendesk help

Recent searches

* * *

No recent searches

## Account details

Sign in to see your account details at a glance

[Sign inSign in](https://support.zendesk.com/hc/en-us/signin?return_to=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408824482586-Managing-conversation-handoff-and-handback)

* * *

FollowFollow

Related articlesRelated articles

* * *

*   [](https://www.facebook.com/share.php?title=Managing+conversation+handoff+and+handback&u=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408824482586-Managing-conversation-handoff-and-handback)
*   [](https://twitter.com/share?lang=en&text=Managing+conversation+handoff+and+handback&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408824482586-Managing-conversation-handoff-and-handback)
*   [](https://www.linkedin.com/shareArticle?mini=true&source=Zendesk+Support&title=Managing+conversation+handoff+and+handback&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F4408824482586-Managing-conversation-handoff-and-handback)

* * *

# Managing conversation handoff and handback

[](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

[Aimee Spanier](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

Zendesk Documentation Team

Edited May 01, 2026

[What's my plan?](https://support.zendesk.com/hc/en-us/articles/5411234991258-plan)

|     |     |
| --- | --- |
| **All Suites** | Team, Growth, Professional, Enterprise, or Enterprise Plus |

In this article, we’ll explain messaging conversation handoff and handback, the actions that can change the first responder in a conversation from an AI agent to a live agent, and back again.

*   **Handoff** is removing the AI agent as the conversation’s first responder and making an agent the first responder.
*   **Handback** is removing a live agent as the first responder in a conversation, clearing the way for the AI agent to be the first responder when the customer starts a new conversation. Handing a conversation back to the AI agent is, effectively, ending one conversation, clearing the way for a new conversation to address a new problem or support request.

This article includes the following topics:

*   [Understanding handoff events](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback#topic_azj_cqq_5pb)
*   [Understanding and managing handback events](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback#topic_ux4_cqq_5pb)
*   [Additional settings to consider](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback#topic_mvs_cqq_5pb)

## Understanding handoff events

When the conversation is handed off to a live agent, those agents are notified of the pending support request based on the account’s [established routing flow](https://support.zendesk.com/hc/en-us/articles/4408829019162), and the AI agent can no longer respond to the conversation.

An agent remains the first responder until the ticket associated with the conversation is closed.

## Understanding and managing handback events

Conversation handback is initiated when the status of the ticket associated with the conversation is changed from _Solved_ to _Closed_. Then, when the customer begins a new conversation, the AI agent becomes the first responder again. It’s important to note, however, that the AI agent does not automatically send the first message in a subsequent conversation. The returning customer must send a message to initiate a response from the AI agent, which will then attempt to find a conversational shortcut. If no shortcut is found, the AI agent will respond according to normal free-text entry behavior. See [Conversational shortcuts and article suggestions](https://support.zendesk.com/hc/en-us/articles/4408824263578#topic_mgq_d4n_jnb) for more information.

Until the status of the ticket is changed to _Closed_, a customer returning to the messaging channel while the ticket is still marked Solved would find the previous conversation still active, and the agent would still be the first responder. The customer would be unable to start a new conversation to address a new support request. By default the time between a solving and closing a ticket is four days, which can cause some confusion for customers returning to your messaging channel.

You can avoid this scenario in two ways:

*   [Adjusting your default automation](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback#topic_dgn_3sq_5pb)
*   [Creating a trigger to manage handback timing](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback#topic_xbt_3sq_5pb)

### Adjusting your default automation

Automatically updating a Solved ticket status to Closed is managed through a default Support automation, _Close ticket 4 days after status is set to solved_.

You can [edit this automation](https://support.zendesk.com/hc/en-us/articles/4408883801626#topic_rsh_miv_ub) to manage how much time passes before the ticket status changes to Closed. You may want to change the time frame to close the ticket within the following hour or you can extend the time to up to 28 days after the ticket is Solved. To close a ticket immediately, see the trigger recipe in the following section.

### Creating a trigger to manage handback timing

You can also [create a trigger](https://support.zendesk.com/hc/en-us/articles/4408886797466#topic_tpw_gay_tb) to automatically close solved tickets, essentially overriding the default automation.

To do this, you’ll need to add a tag (such as _close_ ) to any ticket that has its status changed to _Solved._

Then, create a trigger that fires on any ticket with the added tag and closes the ticket. The trigger should have the following properties:

*   **Condition**: Tags | Contains at least one of the following | close
*   **Action**: Status | Closed

If you are using CSAT to gauge customer satisfaction in messaging, it’s important to note that the survey is sent immediately when the ticket status is set to Solved. If you are using CSAT surveys, we recommend that you keep at least a small time buffer between solving and closing a ticket, to avoid any conflicts. See [About the CSAT (customer satisfaction) user experience for email and messaging](https://support.zendesk.com/hc/en-us/articles/4408886173338) for more information.

## Additional settings to consider

There are a number of settings that, while not directly related to messaging handoff or handback actions, can impact how they perform, and how your end users experience them.

*   **Out-of-office triggers** can set a customer’s expectations for when a live agent might engage them in the conversation. See [Creating an out-of-office message in a Web Widget or mobile SDK](https://support.zendesk.com/hc/en-us/articles/4408842866074) for more information. _Out of office triggers only fire after handoff occurs_.
*   **Continuous conversations** let you automatically send email notifications to end users who have left a conversation in a Web Widget before it was concluded. See [Enabling customers to continue their conversation over email](https://support.zendesk.com/hc/en-us/articles/4408829095706-Enabling-customers-to-continue-their-conversation-over-email) for more information.
*   **Routing settings** manage how a messaging conversation and its associated ticket are passed from the AI agent to a live agent or group, after a handoff event occurs. See [About routing in messaging](https://support.zendesk.com/hc/en-us/articles/4408829019162) for more information.

* * *

0

13

* * *

## 13 comments

Date

Newest

[](https://support.zendesk.com/hc/en-us/profiles/1264837569290)

[Naina Mathur](https://support.zendesk.com/hc/en-us/profiles/1264837569290)

Mar 20, 2024

Hi there,

Thank you for taking the time to provide us with this feedback. 

 This feature request has been accepted and is on our roadmap in 2024. Per our [Community Guidelines](https://support.zendesk.com/hc/en-us/community/posts/6207767532442-Product-feedback-guidelines-how-to-write-a-good-feedback-post) that we do not provide specific timelines around releases for our product and any discussion of planning is always subject to change. Specifically, definitive closure on Agent Workspace Messaging tickets and more flexibility with ticket statuses (beyond Closed), as well as handling a transfer to Agent use case. Queue behavior remains unchanged, and you will be able to re-enage the bot.

To stay on top of product releases please visit our [What’s New](https://support.zendesk.com/hc/en-us/sections/4405298877338) page in the Help Center. We are going to leave this post open for comment to allow others to provide their feedback and use cases.

Thank you again for your feedback and for being a valuable customer with Zendesk.

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082305969)

[Remi](https://support.zendesk.com/hc/en-us/profiles/1263082305969)

Jan 25, 2024

[Jacques Abecassis](https://support.zendesk.com/hc/en-us/profiles/1265026478630-Jacques-Abecassis)

Thanks for your message, hope you are doing well today!

To answer this : 

*   _**Is Zendesk able to handoff an answer bot conversation into another bot solution?**_
    

Yes, this is feasible as Messaging is running on Sunshine Conversation "engine" and thus through Smooch API, you may have a look here : [Handover with the switchboard](https://docs.smooch.io/guide/switchboard/#handover-with-the-switchboard), to learn more about it and in depth. 

*   _**If so, is it able to do the handoff on basic messaging or do you require Advanced messaging with SunCo. to execute?**_

Even as Zendesk "licensed" user you can still access and use Smooch APIs,  although the endpoint might differ, feel free to check here as well : 

*   [https://docs.smooch.io/rest/#section/Introduction/Regions](https://docs.smooch.io/rest/#section/Introduction/Regions) 
*   [https://docs.smooch.io/guide/regions/](https://docs.smooch.io/guide/regions/)

> If you are a licensed Zendesk customer, use the following API host:
> 
> `https://<subdomain>.zendesk.com/sc`

Hope this helps / clarifies it! Have a lovely rest of your day.

Best regards,

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1265026478630)

[Jacques Abecassis](https://support.zendesk.com/hc/en-us/profiles/1265026478630)

Jan 24, 2024

**Two part question:**

\- Is Zendesk able to handoff an answer bot conversation into another bot solution?

\- If so, is it able to do the handoff on basic messaging or do you require Advanced messaging with SunCo. to execute?

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1264158216949)

[Dane](https://support.zendesk.com/hc/en-us/profiles/1264158216949)

Dec 28, 2023

Hi Maxim,  
  
You can refer to this [comment](https://support.zendesk.com/hc/en-us/community/posts/4411236395674/comments/6135875275034) by our Product Manager.  

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/5260679401626)

[Maxim Nikolenko](https://support.zendesk.com/hc/en-us/profiles/5260679401626)

Dec 27, 2023

I would appreciate if you could suggest some workaround for the following scenario

1\. Customers uses a messaging widget for a self-service - the bot suggests some quick hints and solutions, they search for articles in KB.   
2\. They encounter a problem and report it. Bot tries to pass the problem to a live agent. The agent notifies the user that the problem is being under investigation and there is an open/pending ticket. Such ticket can stay in this status for a several days  
3\. All this time the user can neither search for data in the KB (through widget), nor communicate with the bot, nor report a new problem, because all new messages will be sent to the same ticket. But the second problem may have a different context, it may be handled by a different department. 

It turns out that for the Messaging channel you can only have one unclosed ticket at a time. 

Is there any way to "unlink" a ticket from the messaging channel so that it would be linked, for example, to an Email. For example via API/Macros/Triggers

1

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082274789)

[Neil](https://support.zendesk.com/hc/en-us/profiles/1263082274789)

Oct 08, 2023

Hi John,  
   
Once the status is closed and when the customer begins a new conversation, Answer Bot becomes the first responder again.  
   
Note, as mentioned in this [article](https://support.zendesk.com/hc/en-us/articles/4408824482586#topic_xbt_3sq_5pb:~:text=conversation%20is%20closed.-,Understanding%20and%20managing%20handback%20events,-Conversation%20handback%20is).  The Answer Bot does not automatically send the first message in a subsequent conversation. The returning customer must send a message to initiate a response from Answer Bot and Answer Bot will attempt to find a conversational shortcut. respond according to normal free-text entry behavior  

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1265070130069)

[John Polanek](https://support.zendesk.com/hc/en-us/profiles/1265070130069)

Jun 27, 2023

I have the same question as someone above, that was not answered. I will copy what they wrote below.

> After the ticket is marked as closed, How do we prompt the bot again for the customer. 
> 
> Basically when the customer comes back again for second time, how do we give him the same experience as the first time. We want the bot greeting message with start options to come again for the customer after the ticket is marked as closed. 

1

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082072929)

[Arianne Batiles](https://support.zendesk.com/hc/en-us/profiles/1263082072929)

May 21, 2023

Hi Ben,

Yes, your trigger should work as well considering you're not waiting for a CSAT score from your customer.

Using the trigger that is based on a tag allows you to add a tag anytime you want the ticket to be Closed. This trigger comes in handy if you are utilizing CSAT for your Messaging channel and you want to wait for the survey response before closing out the ticket. 

> If you are using CSAT to gauge customer satisfaction in messaging, it’s important to note that the survey is sent immediately when the ticket status is set to Solved. If you are using CSAT surveys, we recommend that you keep at least a small time buffer between solving and closing a ticket, to avoid any conflicts. 

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263828184069)

[Ben](https://support.zendesk.com/hc/en-us/profiles/1263828184069)

May 17, 2023

I have a question about the trigger to close the ticket. 

What is the reason to first assign a tag and then have the trigger fire when the ticket is tagged?

My current solution is a trigger that fires on Messaging and WhatsApp tickets when the ticket status is set to "Solved". It then sets the status to "Closed". So far it seems to work just fine, but would there be any reason to not do it like this?

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082301289)

[Rad](https://support.zendesk.com/hc/en-us/profiles/1263082301289)

Feb 02, 2023

Hi Tushar,  
   
I saw the ticket you created with the same question and already responded to it. We can continue working on the initial ticket. Please check your email!   

0

* * *

[Sign in](https://support.zendesk.com/hc/en-us/signin?return_to=/hc/en-us) to leave a comment.

*   [Previous](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback?page=0)
*   [1](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback?page=1)
*   [2](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback?page=2)
*   [Next](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback?page=2)