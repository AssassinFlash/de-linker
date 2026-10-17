<!-- source: https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference
     loadedTime(UTC): 2026-10-17T05:45:01.459Z
     httpStatus: 200
     apifyRun: OMFaxlpG6yfbQwyQN (wcc-b5) -->

Proactive messaging conditions and events reference – Zendesk help

Recent searches

* * *

No recent searches

## Account details

Sign in to see your account details at a glance

[Sign inSign in](https://support.zendesk.com/hc/en-us/signin?return_to=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5511218058650-Proactive-messaging-conditions-and-events-reference)

* * *

FollowFollow

Related articlesRelated articles

* * *

*   [](https://www.facebook.com/share.php?title=Proactive+messaging+conditions+and+events+reference&u=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5511218058650-Proactive-messaging-conditions-and-events-reference)
*   [](https://twitter.com/share?lang=en&text=Proactive+messaging+conditions+and+events+reference&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5511218058650-Proactive-messaging-conditions-and-events-reference)
*   [](https://www.linkedin.com/shareArticle?mini=true&source=Zendesk+Support&title=Proactive+messaging+conditions+and+events+reference&url=https%3A%2F%2Fsupport.zendesk.com%2Fhc%2Fen-us%2Farticles%2F5511218058650-Proactive-messaging-conditions-and-events-reference)

* * *

# Proactive messaging conditions and events reference

[](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

[Aimee Spanier](https://support.zendesk.com/hc/en-us/profiles/1263082050629)

Zendesk Documentation Team

Edited Aug 27, 2026

Conditional statements define the actions that trigger a proactive message for a user, and when those actions should be evaluated.

[What's my plan?](https://support.zendesk.com/hc/en-us/articles/5411234991258-plan)

|     |     |
| --- | --- |
| **All Suites** | Team, Growth, Professional, Enterprise, or Enterprise Plus |

Conditional statements define the actions that trigger a proactive message for a user, and when those actions should be evaluated.

Conditional statements for proactive messaging follow this basic configuration:

*   An **object** is selected for evaluation.
*   A **condition** is created for that object. The condition consists of a condition field, an operator, and a value.
*   An **event** is created that defines when the conditonal statement is checked.

This article includes the following sections:

*   [Objects](https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference#topic_ad3_n15_wwb)
*   [Conditions](https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference#topic_vvc_hk5_wwb)
*   [Events](https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference#topic_sws_bp5_wwb)
*   [Key points](https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference#topic_avf_rgy_wwb)

## Objects

Choose from the objects in the table below to begin building a condition. The type of object you select determines what [condition fields](https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference#topic_vvc_hk5_wwb) you can choose.

 
| Object | Description |
| --- | --- |
| Visitor | A customer, or end user, visiting your channel. Selecting this object allows you to look at the customer's location or visit history. |
| Device | The computer or mobile device used to access your channel. Selecting this object allows you to evaluate the device's language settings in the condition. |
| Metadata | Information about the customer's business. Business metadata is currently only available for the Web Widget channel. |

## Conditions

Choose from the condition fields in the table below to complete your condition.

    
| Condition field | Object | Description | Operators | Value |
| --- | --- | --- | --- | --- |
| Page URL | Visitor | The URL of a web page, or screen name on a mobile device, the customer is currently on.<br><br>The Page URL string is case insensitive. | Contains at least one of<br><br>Doesn't contain<br><br>Is<br><br>Is not | `String`<br><br>Enter all or part of the page or screen URL to be matched. |
| Page title | Visitor | The title of the web page or mobile device screen the customer is currently on.<br><br>The Page title string is case insensitive. | Contains at least one of<br><br>Doesn't contain<br><br>Is<br><br>Is not | `String`<br><br>Enter all or part of the page or screen title to be matched. |
| Visit history | Visitor | Customer visit history – are they coming to the website or app for the first time, or have they visited before? | Is  | `Drop-down`<br><br>Select **New user** or **Returning user**. |
| Language | Device | Language or locale of the customer, as determined by the device's language settings. | Is<br><br>Is not | `Drop-down`<br><br>Select the language being matched or skipped. |

## Events

Choose from the events in the table below to define when the conditions should be checked.

 
| Event | Description |
| --- | --- |
| Visitor loads the page | Checks for the conditions on page load. |
| Visitor is on the page | Checks for the conditions when a customer spends a set amount of time on the page. |

## Key points

*   Admins can create proactive messages with multiple conditions using AND or OR operators, and can create nested conditions.
*   As an admin, if you plan to use two or fewer conditions, you cannot use nested conditions.

* * *

0

6

* * *

## 6 comments

Date

Newest

[](https://support.zendesk.com/hc/en-us/profiles/7760344663322)

[Robbie Murdoch](https://support.zendesk.com/hc/en-us/profiles/7760344663322)

Jan 28, 2025

I am also having trouble with the page URL, where the full URL doesn't seem to trigger a message but the _contains at least one of_ does trigger a message.   
  
It feels as though i'm not entering the full URL correctly, but have tried this multiple times. It also seems like using the _contains_ for multiple parts of the URL doesn't work either :/   
  
Can you explain if you've had issues with full URLs before and the proactive message not firing?

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263169187390)

[Revant Admin](https://support.zendesk.com/hc/en-us/profiles/1263169187390)

Aug 08, 2024

I want to create a proactive trigger that fires when a customer is on our help center or on our contact us page.  I can't seem to get either trigger to work.  Is that because I can't place a trigger on a page that is connected to our Zendesk Support?  Is there a work around here?

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082165129)

[Ivan Miquiabas](https://support.zendesk.com/hc/en-us/profiles/1263082165129)

Nov 24, 2023

Hi John,   
   
Thanks for reaching out!   
   
To best address the scenario that you stated, You would need to create multiple proactive message for each specific URL using the "is" as an operator for each page URL so that it can be defined as that specific URL only.   
   
  
   
Hope that helps!   

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/5875275546650)

[Sean](https://support.zendesk.com/hc/en-us/profiles/5875275546650)

Nov 06, 2023

One question. If you want to apply to all URLs containing certain address with variable values after a certain point, which option should i slect?

For example, the addresses are,  
[www.abc.com/abc/(address](http://www.abc.com/abc/\(address) changes here for different products)

i.e.  
[www.abc.com/abc/aaaa7](http://www.abc.com/abc/aaaa7)  
[www.abc.com/abc/bbbb6](http://www.abc.com/abc/bbbb6)  
[www.abc.com/abc/cccc9](http://www.abc.com/abc/cccc9)

How do I make it so that any address that contains exactly "[www.abc.com/abc/](http://www.abc.com/abc/)" to show a particular proactive message? I'm trying to implement a different message for different pages. These proactive messages are bringing a good load of traffic into our bot, so we are customizing to page-level.

Thank you in advance.

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1263082315789)

[Ronie Ranoy](https://support.zendesk.com/hc/en-us/profiles/1263082315789)

Sep 05, 2023

Hi Corey,  
  
For 'Contains at least one of, the value can either be single or multi value. If you would want to enter more than one value, it will be separated by comma. An example of multiple value is account1, account2.   

0

* * *

[](https://support.zendesk.com/hc/en-us/profiles/1265067540530)

[Corey Saksik](https://support.zendesk.com/hc/en-us/profiles/1265067540530)

Jul 24, 2023

For multiple 'Contains at least one of' is that meant to be a comma-separated list?  Can you enter multiple possible criteria in the entry field or does it need to be individual line-items?

0

* * *

[Sign in](https://support.zendesk.com/hc/en-us/signin?return_to=/hc/en-us) to leave a comment.