<!-- source: https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages
     loadedTime(UTC): 2026-10-17T05:45:01.590Z
     httpStatus: 200
     apifyRun: OMFaxlpG6yfbQwyQN (wcc-b5) -->

About proactive messages – Zendesk help

Recent searches

* * *

No recent searches

## Account details

Sign in to see your account details at a glance

[Sign inSign in](https://support.zendesk.com/hc/en-us/signin?return_to=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5381304334234-About-proactive-messages)

* * *

FollowFollow

Related articlesRelated articles

* * *

*   [](https://www.facebook.com/share.php?title=About+proactive+messages&u=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5381304334234-About-proactive-messages)
*   [](https://twitter.com/share?lang=en&text=About+proactive+messages&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5381304334234-About-proactive-messages)
*   [](https://www.linkedin.com/shareArticle?mini=true&source=Zendesk+Support&title=About+proactive+messages&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5381304334234-About-proactive-messages)

* * *

# About proactive messages

[](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

[Aimee Spanier](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

Zendesk Documentation Team

Edited Apr 29, 2026

With proactive messaging, you can deliver targeted messages to your customers through your Web Widget or mobile SDK channel without waiting for them to start the conversation.

[What's my plan?](https://support.zendesk.com/hc/en-us/articles/5411234991258-plan)

|     |     |
| --- | --- |
| **All Suites** | Team, Growth, Professional, Enterprise, or Enterprise Plus |

Verified AI summary ◀▼

Proactive messaging lets you initiate conversations with customers through your Web Widget or mobile SDK based on set conditions. Use it to offer support, engage customers, and boost sales. Configure messages by adding content, setting rules, and choosing timing. Manage messages via the admin page, and choose between agent or AI agent responses to enhance customer interactions.

With proactive messaging, you can deliver targeted messages to your customers through your Web Widget or mobile SDK channel without waiting for them to start the conversation.

This article includes the following topics:

*   [Overview of proactive messaging](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_tsn_shy_wwb)
*   [The Proactive messages admin page](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_yl5_shy_wwb)
*   [Agent response types](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_sgz_shy_wwb)
*   [Requirements and limitations](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_gcf_thy_wwb)
*   [The customer experience](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_e5j_thy_wwb)

Related articles:

*   [Creating proactive messages for the Web Widget](https://support.zendesk.com/hc/en-us/articles/5511266103834)
*   [Creating proactive messages for mobile SDK channels](https://support.zendesk.com/hc/en-us/articles/5511216991898)

## Overview of proactive messaging

Proactive messaging lets you automatically initiate conversations with customers based on specified conditions that you define. Your customers can then choose whether or not to respond.

This can be useful in a number of ways, including:

*   Providing proactive support, such as offering automated self-service based on user behavior and interaction history, as well as show delays on product delivery and scheduled maintenance.
*   Driving customer engagement, acquisition and retention with custom greetings, guided onboarding and announcements.
*   Increasing sales and conversion rates with targeted messages based on user events and past interactions.

Setting up a proactive message includes the following tasks:

*   **Adding the proactive message**. This creates a framework for the message and adds it to the Proactive messages list.
*   **Composing the message**. Write and format a message for your customers using text and emojis, capture customer data if needed, select a messaging channel, and choose whether to have an AI agent initially manage the conversation or to pass responding customers to a human agent instead. See [Agent response types](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_sgz_shy_wwb) for more information.
*   **Setting the rules**. This is where you define the conditions a customer must meet to receive the message, and optionally create tags to add to any tickets generated from the conversation.
*   **Choosing when to send the message**. Here, you’ll indicate when a proactive message can be sent: During or outside business hours, or any time of the day. You’ll also select how often a message can be sent to a customer: One time only, once per customer visit, or every time the customer meets the defined conditions for receiving the message.
*   **Publishing the message**. This simple click of a button makes the message live, meaning any customers who meet the message’s conditions will immediately begin receiving those messages.

For more information, see the following articles:

*   [Creating proactive messages for the Web Widget](https://support.zendesk.com/hc/en-us/articles/5511266103834)
*   [Creating proactive messages for mobile SDK channels](https://support.zendesk.com/hc/en-us/articles/5511216991898)

## The Proactive messages admin page

The Proactive messages page in Admin Center is your starting point for the tasks described above, as well as a list of existing messages. You can click the message to view its configuration page.

The list of existing messages includes columns displaying the following information:

*   **Name**: A short, descriptive name for the message.
*   **Status**: The current state of the message. You can sort the list by this column.
    
    *   **Live**: The proactive message has been published and the message is being sent to customers who meet the conditions.
    *   **Draft**: Message creation is in progress, and the message has not been previously published.
    *   **Paused**: The proactive message campaign has been temporarily halted. This can happen when:
        
        *   An admin has manually paused a previously live proactive message.
        *   The proactive message uses AI agent capability (such as generative replies) and your account is configured to pause AI agent functionality when it [reaches its automated resolution limit](https://support.zendesk.com/hc/en-us/articles/6958358659226#topic_iw3_b2h_bdc). These campaigns will [resume](https://support.zendesk.com/hc/en-us/articles/5511266103834#topic_szk_tjd_42c) when automated resolutions are available. Proactive messages paused for this reason are indicated by a warning icon in the Proactive messages list:
            
        
    *   **Contains errors**: Previously published message is no longer active due to errors. Most often this status appears when the connected messaging channel is deleted or altered in a way that makes it incompatible with the proactive message, such as deleting the connected AI agent. You can view the message for information on missing or inadequate information.
    
*   **Channel**: The channel on which you want to run your proactive message.
*   **Sent**: The number of customers who have been sent the proactive message. You can sort the list by this column.
*   **Opened**: The number of customers who have viewed the proactive message and clicked on the message. You can sort the list by this column.
*   **Replied to**: The number of customers who have interacted with the proactive message, which means engaged with the AI agent or shared details when the agent response type was configured. You can sort the list by this column.
*   **Updated**: The date of the most recent update to the proactive message. You can sort the list by this column.

Each message in the list has an options menu ( ), visible when you hover over the message. The following options may be available from this menu, depending on the message’s current status:

*   **Edit**: Opens the message’s configuration page. Option appears on all messages regardless of status.
*   **Clone**: Creates a copy of the message and adds a draft of it to the message list. Option appears when message status is _Live_, _Draft,_ or _Paused_.
*   **Publish**: Activates the proactive message. Option appears when message status is _Draft_.
*   **Pause**: Temporarily stops a published proactive message. Option appears when message status is _Live_.
*   **Resume**: Restarts a proactive message. Option appears when message status is _Paused_.
*   **Delete**: Permanently deletes the message. Option appears on all messages regardless of status.

When you first visit the Proactive messages admin page, there are three partially-configured messages in draft form. Each one is configured to address a common use case for proactive messages. You can use these messages as a starting point for creating your own messages by cloning or editing them.

## Agent response types

There are two agent response types you can choose to use in your proactive messages:

*   **Agent**: This is the simpler response type, which requires you to compose a short text-only message for the customer (no emojis) and optionally request the customer’s name and/or email address before handing off the conversation to a live agent.
*   **AI agent**: AI agent responses allow you to create your message by referring to an answer in an active, published AI agent _within the same brand_. After the initial message appears, the connected [AI agent](https://support.zendesk.com/hc/en-us/articles/6970583409690) manages the conversation.

See [The customer experience](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_e5j_thy_wwb)for more information and examples of these message response types.

## Requirements and limitations

Consider the following requirements and limitations before getting started with proactive messaging.

### Requirements

Your account must meet the following requirements to use proactive messaging:

*   Agent Workspace must be activated.
*   Messaging must be activated.
*   At least one messaging Web Widget OR one mobile SDK channel must exist to publish a proactive message.
*   To use an AI agent response, the connected channel must have one active, successfully published AI agent .
*   (Legacy AI agents) When using an [AI agent response](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages#topic_sgz_shy_wwb), you can only choose from successfully published answers in the connected AI agent as your follow-up message.

### Limitations

The following limitations apply to the current version of proactive messaging:

*   You can create up to 140 proactive messages.
*   Proactive messages aren't sent to customers in currently active messaging conversations.
*   Proactive messages are only available for the Web Widget and Mobile SDK messaging channels.
*   Proactive messages aren't supported for third-party bots and social messaging channels.
*   Proactive messages can't be used with [AI agents - Advanced](https://support.zendesk.com/hc/en-us/articles/6970583409690).
*   Proactive messages can only be used on one channel at a time. Channels, however, can have multiple proactive messages running simultaneously.
*   Proactive conditions with two conditions or less can't use nested conditions.

## The customer experience

The customer experience with proactive messages varies – not only with your specific settings and messages, but depending on whether you’re using a live or AI Agent response.

### Customer experience: Agent response

When the customer meets the defined criteria for activating a proactive message using the Agent reply type:

*   A message appears above the messaging launcher button, displaying the text defined in the message configuration.
    
    This message is sent from the default sender defined in the channel settings, and overrides previously-configured launcher text.
    

If the customer chooses to click the message text to open the messaging window, any data capture requests are displayed. The customer can then choose to:

*   Enter the requested information. The follow-up message is displayed, and the conversation is handed off to a live agent.
*   Close the messaging window using the close launcher button. The message disappears. It may appear at another time, depending on the configured frequency settings.
*   Ignore the message.

If the customer chooses to click the **X** to hide the message without opening it:

*   The message disappears. It may appear at another time, depending on the configured frequency settings.

### Customer experience: AI agent response

When the customer meets the defined criteria for activating a proactive message using the AI agent reply type:

*   A message appears above the messaging launcher button, displaying the text defined in the message configuration.
    
    This message is sent from the conversation AI agent.
    

If the customer chooses to click the message text to open the messaging window, the answer selected in the message configuration appears. The customer can then choose to:

*   Interact with the answer.
*   Close the messaging window using the close launcher button. The message disappears. It may appear at another time, depending on the configured frequency settings.
*   Ignore the message.

If the customer chooses to click the **X** to hide the message without opening it:

*   The message disappears. It may appear at another time, depending on the configured frequency settings.

* * *

0

30

* * *

## 31 comments

Date

Newest

[](https://support.zendesk.com/hc/en-us/profiles/5935813700634)

[Viachaslau Skorbezh](https://support.zendesk.com/hc/en-us/profiles/5935813700634)

Sep 11, 2025

Hi [Hugo Richard](https://support.zendesk.com/hc/en-us/profiles/8318173554202-Hugo%20Richard) ,

It looks like the native proactive messaging feature doesn't support Advanced AI agents. But when we send a productive message using SunCo APIs, it works with Advanced AI agents really well.

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/8318173554202)

[Hugo](https://support.zendesk.com/hc/en-us/profiles/8318173554202)

Sep 10, 2025

Hello team,  
  
Is proactive messaging compatible with AI Agent Advanced?  
  
If it's not, is there something similar available for AI Agent Advanced messaging bot?

1

* * *

[](https://support.zendesk.com/hc/en-us/profiles/7827097647898)

[Paula Caetano](https://support.zendesk.com/hc/en-us/profiles/7827097647898)

Sep 09, 2025

We've encountered a critical challenge in our Zendesk implementation concerning the platform's proactive messaging capabilities.  
 

Currently, our operation requires the ability to send proactive in-app chat messages that also trigger a push notification. However, we've been unable to achieve this for two essential use cases:

1.  **Manual Outreach:** Agents cannot seem to initiate a chat with a user proactively.
2.  **Automated Workflows:** We cannot find a way to trigger these messages via system integrations or automated rules.  
      
    Could you please confirm if this capability is natively supported under this ‘proactive messages’ feature? 

1

* * *

[](https://support.zendesk.com/hc/en-us/profiles/5935813700634)

[Viachaslau Skorbezh](https://support.zendesk.com/hc/en-us/profiles/5935813700634)

Mar 17, 2025

Please upvote [my post to fix the problem of proactive messages not working with multi-conversations](https://support.zendesk.com/hc/en-us/community/posts/9033023173658-The-Proactive-messages-feature-does-not-work-with-Multi-conversations). 

2

* * *

[](https://support.zendesk.com/hc/en-us/profiles/6926680362906)

[Chris Gast](https://support.zendesk.com/hc/en-us/profiles/6926680362906)

Aug 15, 2024

How do I  build a report on Sent, Opened, Replied To in Explore? I see the data in the admin panel, but I want to also add it to my CX dashboard.  

3

* * *

[](https://support.zendesk.com/hc/en-us/profiles/5895537231642)

[Shawna James](https://support.zendesk.com/hc/en-us/profiles/5895537231642)

May 30, 2024

Hey Thomas, thank you so much for taking the time to provide us with your feedback here. I wanted to point you in the direction of our product feedback forum for [**Messaging**](https://support.zendesk.com/hc/en-us/community/topics/1260801308710-Feedback-Chat-and-Messaging-Chat-) where we collect product feedback and where our PM’s review feedback from our customers. We would greatly appreciate you using this forum to share your feedback with us for better visibility.  Here is our [product feedback template](https://support.zendesk.com/hc/en-us/community/posts/6207781802138-Product-Feedback-Feature-Request-Post-Template) to get you started. Thank you!  

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1265190212649)

[Toshikazu Asaka](https://support.zendesk.com/hc/en-us/profiles/1265190212649)

May 30, 2024

Hello Zendesk team,  
  
I would like to share a couple of feedback and request.  
 

1\. I would like to request Dynamic content being applicable to Proactive messages. I read in thread above that it is currently not supported as of April 2023. When will it be enabled?  
2\. When I clone a proactive message, message copy in original one won't be carried over to cloned one. It is automatically reverted to default message copy.  
  
Hope these could be improved in the near future. Thank you.

2

* * *

[](https://support.zendesk.com/hc/en-us/profiles/4529324729882)

[Guido](https://support.zendesk.com/hc/en-us/profiles/4529324729882)

Jan 18, 2024

Hi [Kris](https://support.zendesk.com/hc/en-us/profiles/1263213533049-Kris),

No, proactive messages are not meant to be used this way. They act based on the conditions configured and send a message to users in your website. 

What you are looking for sounds more like a proactive ticket campaign, we you can achieve with an app like this - [Proactive Tickets App](https://www.zendesk.com/marketplace/apps/support/37932/proactive-tickets/)

Thank you!

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263797810549)

[Kris](https://support.zendesk.com/hc/en-us/profiles/1263797810549)

Jan 18, 2024

Hi   
  
Can I use proactive messages to a specific segment? Lets say I have 50 special customers I would like to send a specific message - is that possible?  
  
Thanks  
Kris

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/4529324729882)

[Guido](https://support.zendesk.com/hc/en-us/profiles/4529324729882)

Jan 15, 2024

Hi [Nikki Goodson](https://support.zendesk.com/hc/en-us/profiles/5264685608602-Nikki%20Goodson)!

I will create a ticket to look into this matter with you.

Thank you! 

0

* * *

[Sign in](https://support.zendesk.com/hc/en-us/signin?return_to=/hc/en-us) to leave a comment.

*   [Previous](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages?page=0)
*   [1](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages?page=1)
*   [2](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages?page=2)
*   [3](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages?page=3)
*   …
*   [4](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages?page=4)
*   [Next](https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages?page=2)